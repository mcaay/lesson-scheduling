import json
import logging
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from pathlib import Path
from uuid import UUID, uuid4

from django.conf import settings

from .solver import solve_schedule
from .spec_parser import parse_spec
from .spec_validation import validate_spec


JOB_EXPIRY_SECONDS = 24 * 60 * 60

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="schedule-solver")


def start_solve_job(raw_spec):
    cleanup_expired_jobs()
    job_id = uuid4()
    _write_job(
        job_id,
        {
            "status": "pending",
            "created_at": time.time(),
            "raw_spec": raw_spec,
        },
    )
    _executor.submit(_run_solve_job, job_id)
    return job_id


def read_solve_job(job_id):
    try:
        return json.loads(_job_path(job_id).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def cleanup_expired_jobs():
    cutoff = time.time() - JOB_EXPIRY_SECONDS
    directory = _job_directory()
    if not directory.exists():
        return

    for path in directory.glob("*.json"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except FileNotFoundError:
            continue


def _run_solve_job(job_id):
    job = read_solve_job(job_id)
    if job is None:
        return

    raw_spec = job["raw_spec"]
    try:
        parsed = parse_spec(raw_spec)
        if parsed.errors:
            _finish_with_errors(job_id, job, parsed.errors)
            return

        validation_errors = validate_spec(parsed.spec)
        if validation_errors:
            _finish_with_errors(job_id, job, validation_errors)
            return

        result = solve_schedule(parsed.spec)
        _write_job(
            job_id,
            {
                **job,
                "status": "complete",
                "solved": result.solved,
                "message": result.message,
                "lessons": [asdict(lesson) for lesson in result.lessons],
            },
        )
    except Exception:
        logger.exception("Schedule job %s failed", job_id)
        _write_job(
            job_id,
            {
                **job,
                "status": "error",
                "message": "Scheduling failed unexpectedly. Please try again.",
            },
        )


def _finish_with_errors(job_id, job, errors):
    _write_job(
        job_id,
        {
            **job,
            "status": "invalid",
            "errors": [
                {"line": getattr(error, "line", None), "message": str(error.message)}
                for error in errors
            ],
        },
    )


def _write_job(job_id, data):
    path = _job_path(job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary_path.write_text(
        json.dumps(data, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary_path.chmod(0o600)
    temporary_path.replace(path)


def _job_path(job_id):
    normalized_id = UUID(str(job_id))
    return _job_directory() / f"{normalized_id}.json"


def _job_directory():
    configured = getattr(settings, "SOLVER_JOB_DIRECTORY", None)
    if configured:
        return Path(configured)
    return Path(tempfile.gettempdir()) / f"lesson-scheduling-jobs-{os.getuid()}"
