import fcntl
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from uuid import UUID, uuid4

from django.conf import settings

from .spec_limits import (
    MAX_ACTIVE_SOLVE_JOBS,
    MAX_RAW_SPEC_BYTES,
    MAX_STORED_SOLVE_JOBS,
    TOTAL_SOLVE_JOB_LIMIT_SECONDS,
)
from .spec_models import SpecError
from .spec_parser import parse_spec
from .spec_validation import validate_spec


JOB_EXPIRY_SECONDS = 24 * 60 * 60
TERMINAL_STATUSES = {"complete", "invalid", "error"}

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="schedule-solver")
_submission_lock = Lock()
_submitted_job_ids = set()


class SolveQueueFull(Exception):
    pass


def start_solve_job(raw_spec):
    job_id = uuid4()
    created_at = time.time()
    errors = _spec_errors(raw_spec)
    with _jobs_lock():
        cleanup_expired_jobs()
        _trim_terminal_jobs(MAX_STORED_SOLVE_JOBS - 1)
        if errors:
            _write_job(
                job_id,
                {
                    "status": "invalid",
                    "created_at": created_at,
                    "raw_spec": raw_spec,
                    "errors": _serialize_errors(errors),
                },
            )
            return job_id
        if _active_job_count() >= MAX_ACTIVE_SOLVE_JOBS:
            raise SolveQueueFull
        _write_job(
            job_id,
            {
                "status": "queued",
                "created_at": created_at,
                "raw_spec": raw_spec,
            },
        )
    _submit_job(job_id)
    return job_id


def read_solve_job(job_id):
    job = _read_job(job_id)
    if job is None:
        return None

    if job["status"] == "running" and not _pid_is_alive(job.get("worker_pid")):
        # A surviving web process can reclaim a job after another worker exits.
        with _jobs_lock():
            current = _read_job(job_id)
            if current and current["status"] == "running" and not _pid_is_alive(
                current.get("worker_pid")
            ):
                current["status"] = "queued"
                current.pop("worker_pid", None)
                current.pop("started_at", None)
                _write_job(job_id, current)
                job = current
    if job["status"] == "queued":
        _submit_job(job_id)
    return job


def cleanup_expired_jobs():
    cutoff = time.time() - JOB_EXPIRY_SECONDS
    directory = _job_directory()
    if not directory.exists():
        return

    for pattern in ("*.json", ".*.tmp"):
        for path in directory.glob(pattern):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
            except FileNotFoundError:
                continue


def _run_solve_job(job_id):
    with _jobs_lock():
        job = _read_job(job_id)
        if job is None or job["status"] != "queued":
            return
        job["status"] = "running"
        job["worker_pid"] = os.getpid()
        job["started_at"] = time.time()
        _write_job(job_id, job)

    try:
        completed = subprocess.run(
            [sys.executable, "-m", "scheduler.solve_worker"],
            input=job["raw_spec"],
            text=True,
            capture_output=True,
            timeout=TOTAL_SOLVE_JOB_LIMIT_SECONDS,
            check=False,
        )
        if completed.returncode != 0:
            logger.error(
                "Schedule worker for %s exited with %s: %s",
                job_id,
                completed.returncode,
                completed.stderr[-2000:],
            )
            raise RuntimeError("Schedule worker failed")
        payload = json.loads(completed.stdout)
        _write_job(
            job_id,
            {
                **job,
                **payload,
                "status": "complete",
                "finished_at": time.time(),
            },
        )
    except subprocess.TimeoutExpired:
        _finish_with_error(
            job_id,
            job,
            "Scheduling exceeded the total time limit. Try a smaller project.",
        )
    except Exception:
        logger.exception("Schedule job %s failed", job_id)
        _finish_with_error(
            job_id,
            job,
            "Scheduling failed unexpectedly. Please try again.",
        )


def _submit_job(job_id):
    # Polling must not add the same queued job to this process repeatedly.
    normalized_id = str(job_id)
    with _submission_lock:
        if normalized_id in _submitted_job_ids:
            return
        _submitted_job_ids.add(normalized_id)
    try:
        _executor.submit(_run_and_release_job, job_id, normalized_id)
    except BaseException:
        with _submission_lock:
            _submitted_job_ids.discard(normalized_id)
        raise


def _run_and_release_job(job_id, normalized_id):
    try:
        _run_solve_job(job_id)
    finally:
        with _submission_lock:
            _submitted_job_ids.discard(normalized_id)


def _finish_with_error(job_id, job, message):
    _write_job(
        job_id,
        {
            **job,
            "status": "error",
            "message": message,
            "finished_at": time.time(),
        },
    )


def _spec_errors(raw_spec):
    if len(raw_spec.encode("utf-8")) > MAX_RAW_SPEC_BYTES:
        return (
            SpecError(
                None,
                f"The specification cannot exceed {MAX_RAW_SPEC_BYTES // 1000} KB.",
            ),
        )
    parsed = parse_spec(raw_spec)
    if parsed.errors:
        return parsed.errors
    return tuple(validate_spec(parsed.spec))


def _serialize_errors(errors):
    return [
        {"line": getattr(error, "line", None), "message": str(error.message)}
        for error in errors
    ]


def _active_job_count():
    count = 0
    for path in _job_directory().glob("*.json"):
        try:
            job = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        if job.get("status") not in TERMINAL_STATUSES:
            count += 1
    return count


def _trim_terminal_jobs(maximum_file_count):
    paths = sorted(
        _job_directory().glob("*.json"),
        key=lambda path: path.stat().st_mtime,
    )
    files_to_remove = max(0, len(paths) - maximum_file_count)
    for path in paths:
        if files_to_remove == 0:
            break
        try:
            job = json.loads(path.read_text(encoding="utf-8"))
            if job.get("status") in TERMINAL_STATUSES:
                path.unlink()
                files_to_remove -= 1
        except (FileNotFoundError, json.JSONDecodeError):
            continue


def _read_job(job_id):
    try:
        return json.loads(_job_path(job_id).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return None


def _write_job(job_id, data):
    path = _job_path(job_id)
    directory = path.parent
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    temporary_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    descriptor = os.open(
        temporary_path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as temporary_file:
            json.dump(data, temporary_file, ensure_ascii=False)
        temporary_path.replace(path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


@contextmanager
def _jobs_lock():
    directory = _job_directory()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    lock_path = directory / ".jobs.lock"
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _pid_is_alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def _job_path(job_id):
    normalized_id = UUID(str(job_id))
    return _job_directory() / f"{normalized_id}.json"


def _job_directory():
    configured = getattr(settings, "SOLVER_JOB_DIRECTORY", None)
    if configured:
        return Path(configured)
    return Path(tempfile.gettempdir()) / f"lesson-scheduling-jobs-{os.getuid()}"
