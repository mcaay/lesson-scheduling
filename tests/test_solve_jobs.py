import os
import subprocess
from uuid import uuid4

import pytest

from scheduler.examples import EXAMPLE_SPEC
from scheduler.solve_jobs import (
    SolveQueueFull,
    _write_job,
    read_solve_job,
    start_solve_job,
)
from scheduler.spec_limits import MAX_ACTIVE_SOLVE_JOBS


class HoldingExecutor:
    def __init__(self):
        self.submissions = []

    def submit(self, function, *args):
        self.submissions.append((function, args))


class ImmediateExecutor:
    def submit(self, function, *args):
        function(*args)


def test_job_queue_has_a_global_active_job_limit(settings, tmp_path, monkeypatch):
    executor = HoldingExecutor()
    settings.SOLVER_JOB_DIRECTORY = tmp_path
    monkeypatch.setattr("scheduler.solve_jobs._executor", executor)

    for _index in range(MAX_ACTIVE_SOLVE_JOBS):
        start_solve_job(EXAMPLE_SPEC)

    with pytest.raises(SolveQueueFull):
        start_solve_job(EXAMPLE_SPEC)
    assert len(executor.submissions) == MAX_ACTIVE_SOLVE_JOBS


def test_job_files_are_private_from_creation(settings, tmp_path, monkeypatch):
    settings.SOLVER_JOB_DIRECTORY = tmp_path
    monkeypatch.setattr("scheduler.solve_jobs._executor", HoldingExecutor())

    job_id = start_solve_job(EXAMPLE_SPEC)

    assert (tmp_path.stat().st_mode & 0o777) == 0o700
    assert ((tmp_path / f"{job_id}.json").stat().st_mode & 0o777) == 0o600


def test_polling_a_queued_job_does_not_duplicate_local_submissions(
    settings,
    tmp_path,
    monkeypatch,
):
    executor = HoldingExecutor()
    settings.SOLVER_JOB_DIRECTORY = tmp_path
    monkeypatch.setattr("scheduler.solve_jobs._executor", executor)

    job_id = start_solve_job(EXAMPLE_SPEC)
    read_solve_job(job_id)
    read_solve_job(job_id)

    assert len(executor.submissions) == 1


def test_reading_a_job_recovers_it_after_its_worker_dies(
    settings,
    tmp_path,
    monkeypatch,
):
    executor = HoldingExecutor()
    settings.SOLVER_JOB_DIRECTORY = tmp_path
    monkeypatch.setattr("scheduler.solve_jobs._executor", executor)
    monkeypatch.setattr("scheduler.solve_jobs._pid_is_alive", lambda _pid: False)
    job_id = uuid4()
    _write_job(
        job_id,
        {
            "status": "running",
            "created_at": 1,
            "started_at": 2,
            "worker_pid": os.getpid() + 100000,
            "raw_spec": EXAMPLE_SPEC,
        },
    )

    job = read_solve_job(job_id)

    assert job["status"] == "queued"
    assert len(executor.submissions) == 1


def test_total_job_timeout_becomes_a_terminal_error(
    settings,
    tmp_path,
    monkeypatch,
):
    settings.SOLVER_JOB_DIRECTORY = tmp_path
    monkeypatch.setattr("scheduler.solve_jobs._executor", ImmediateExecutor())

    def time_out(*_args, **_kwargs):
        raise subprocess.TimeoutExpired("worker", 130)

    monkeypatch.setattr("scheduler.solve_jobs.subprocess.run", time_out)

    job_id = start_solve_job(EXAMPLE_SPEC)
    job = read_solve_job(job_id)

    assert job["status"] == "error"
    assert "total time limit" in job["message"]
