import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Optional


class JobQueueFull(RuntimeError):
    """Raised when the in-process job manager reaches its configured capacity."""


class JobManager:
    """Bounded in-process job runner for local/Docker deployments.

    This keeps the default app dependency-light while making the queue behavior
    explicit. For multi-instance production, swap this boundary for Redis/Celery
    or a managed queue without changing route-level contracts.
    """

    TERMINAL_STATUSES = {"done", "failed"}

    def __init__(self, max_workers: int = 3, max_retained_jobs: int = 500, max_in_flight: int = 50):
        self.max_workers = max(1, int(max_workers))
        self.max_retained_jobs = max(1, int(max_retained_jobs))
        self.max_in_flight = max(1, int(max_in_flight))
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._submitted_count = 0
        self._completed_count = 0
        self._failed_count = 0
        self._rejected_count = 0
        self._lock = threading.Lock()

    def submit(self, name: str, fn: Callable[..., Any], *args, **kwargs) -> str:
        job_id = str(uuid.uuid4())
        now = time.time()
        with self._lock:
            in_flight = self._count_in_flight_locked()
            if in_flight >= self.max_in_flight:
                self._rejected_count += 1
                raise JobQueueFull(f"Job queue is full ({in_flight}/{self.max_in_flight} in flight).")

            self._jobs[job_id] = {
                "id": job_id,
                "name": name,
                "status": "queued",
                "progress": 0,
                "message": "Queued",
                "result": None,
                "error": None,
                "traceback": None,
                "created_at": now,
                "updated_at": now,
                "started_at": None,
                "finished_at": None,
            }
            self._submitted_count += 1
            self._prune_locked()
        self.executor.submit(self._run, job_id, fn, *args, **kwargs)
        return job_id

    def _run(self, job_id: str, fn: Callable[..., Any], *args, **kwargs) -> None:
        self.update(job_id, status="processing", progress=5, message="Processing", started_at=time.time())
        try:
            result = fn(*args, job_id=job_id, **kwargs)
            self.update(
                job_id,
                status="done",
                progress=100,
                message="Complete",
                result=result,
                finished_at=time.time(),
            )
            with self._lock:
                self._completed_count += 1
        except Exception as exc:
            self.update(
                job_id,
                status="failed",
                progress=100,
                message="Failed",
                error=str(exc),
                traceback=traceback.format_exc(),
                finished_at=time.time(),
            )
            with self._lock:
                self._failed_count += 1

    def update(self, job_id: str, **fields) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.update(fields)
            job["updated_at"] = time.time()
            self._prune_locked()

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None

    def list(self, limit: int = 50) -> list:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda item: item["created_at"], reverse=True)
            return [dict(job) for job in jobs[:limit]]

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            status_counts: Dict[str, int] = {}
            for job in self._jobs.values():
                status = job.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1
            in_flight = sum(status_counts.get(status, 0) for status in ("queued", "processing"))
            return {
                "max_workers": self.max_workers,
                "max_in_flight": self.max_in_flight,
                "max_retained_jobs": self.max_retained_jobs,
                "retained_jobs": len(self._jobs),
                "in_flight": in_flight,
                "status_counts": status_counts,
                "submitted": self._submitted_count,
                "completed": self._completed_count,
                "failed": self._failed_count,
                "rejected": self._rejected_count,
            }

    def shutdown(self, wait: bool = True) -> None:
        """Stop worker threads cleanly during tests or graceful shutdown."""
        self.executor.shutdown(wait=wait, cancel_futures=False)

    def _count_in_flight_locked(self) -> int:
        return sum(1 for job in self._jobs.values() if job.get("status") in {"queued", "processing"})

    def _prune_locked(self) -> None:
        if len(self._jobs) <= self.max_retained_jobs:
            return
        terminal_jobs = [
            job for job in self._jobs.values()
            if job.get("status") in self.TERMINAL_STATUSES
        ]
        terminal_jobs.sort(key=lambda item: item.get("finished_at") or item.get("updated_at") or 0)
        removable = len(self._jobs) - self.max_retained_jobs
        for job in terminal_jobs[:removable]:
            self._jobs.pop(job["id"], None)