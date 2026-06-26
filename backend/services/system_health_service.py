import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable

from config import (
    AUDIO_FOLDER,
    DATA_FOLDER,
    GENERATED_CODE_FOLDER,
    GENERATED_MARKDOWN_FOLDER,
    INDEX_FOLDER,
    UPLOAD_FOLDER,
    FlaskConfig,
)


class SystemHealthService:
    """Dependency and capacity snapshot for health/readiness endpoints."""

    def __init__(
        self,
        db,
        embedding_engine,
        job_manager,
        rate_limiter,
        gemini_provider: Callable[[], Any],
        runtime_warnings_provider: Callable[[], Iterable[str]],
    ):
        self.db = db
        self.embedding_engine = embedding_engine
        self.job_manager = job_manager
        self.rate_limiter = rate_limiter
        self.gemini_provider = gemini_provider
        self.runtime_warnings_provider = runtime_warnings_provider

    def snapshot(self) -> Dict[str, Any]:
        warnings = list(self.runtime_warnings_provider())
        checks = {
            "database": self._database_check(),
            "storage": self._storage_check(),
            "retrieval": self._retrieval_check(),
            "llm": self._llm_check(),
            "jobs": self._jobs_check(),
            "configuration": {
                "status": "warn" if warnings else "ok",
                "warnings": warnings,
            },
        }
        return {
            "service": FlaskConfig.APP_NAME,
            "version": FlaskConfig.APP_VERSION,
            "environment": FlaskConfig.ENVIRONMENT,
            "status": self._rollup_status(checks.values()),
            "timestamp": int(time.time()),
            "checks": checks,
            "slo": {
                "api_p95_latency_ms_target": 1500,
                "async_upload_p95_accept_ms_target": 500,
                "availability_target": "99.9% for API process in single-node deployment",
            },
            "scale_limits": {
                "max_upload_mb": FlaskConfig.MAX_UPLOAD_MB,
                "max_analysis_chars": FlaskConfig.MAX_ANALYSIS_CHARS,
                "max_qa_context_chars": FlaskConfig.MAX_QA_CONTEXT_CHARS,
                "job_workers": FlaskConfig.JOB_WORKERS,
                "job_max_in_flight": FlaskConfig.JOB_MAX_IN_FLIGHT,
            },
        }

    def metrics(self) -> Dict[str, Any]:
        return {
            "service": FlaskConfig.APP_NAME,
            "version": FlaskConfig.APP_VERSION,
            "timestamp": int(time.time()),
            "jobs": self.job_manager.stats(),
            "rate_limiter": self.rate_limiter.stats(),
            "retrieval": {
                "mode": "semantic" if self.embedding_engine.use_semantic else "lexical",
                "has_active_index": bool(self.embedding_engine.has_index),
                "active_chunks": len(getattr(self.embedding_engine, "_chunks", [])),
            },
        }

    def readiness(self) -> Dict[str, Any]:
        snapshot = self.snapshot()
        blocking = [
            name for name, check in snapshot["checks"].items()
            if name in {"database", "storage"} and check.get("status") != "ok"
        ]
        snapshot["ready"] = not blocking
        snapshot["blocking_dependencies"] = blocking
        if blocking:
            snapshot["status"] = "down"
        return snapshot

    def _database_check(self) -> Dict[str, Any]:
        started = time.perf_counter()
        try:
            with self.db.get_connection() as conn:
                conn.execute("SELECT 1").fetchone()
            return {
                "status": "ok",
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                "engine": "sqlite",
            }
        except Exception as exc:
            return {"status": "down", "error": str(exc), "engine": "sqlite"}

    def _storage_check(self) -> Dict[str, Any]:
        folders = {
            "data": DATA_FOLDER,
            "uploads": UPLOAD_FOLDER,
            "index": INDEX_FOLDER,
            "audio": AUDIO_FOLDER,
            "generated_code": GENERATED_CODE_FOLDER,
            "generated_markdown": GENERATED_MARKDOWN_FOLDER,
        }
        details = {}
        missing = []
        for name, folder in folders.items():
            path = Path(folder)
            exists = path.exists() and path.is_dir()
            details[name] = {"path": str(path), "exists": exists}
            if not exists:
                missing.append(name)
        return {
            "status": "ok" if not missing else "down",
            "folders": details,
            "missing": missing,
        }

    def _retrieval_check(self) -> Dict[str, Any]:
        return {
            "status": "ok",
            "mode": "semantic" if self.embedding_engine.use_semantic else "lexical",
            "has_active_index": bool(self.embedding_engine.has_index),
            "active_chunks": len(getattr(self.embedding_engine, "_chunks", [])),
        }

    def _llm_check(self) -> Dict[str, Any]:
        try:
            gemini = self.gemini_provider()
            if gemini and gemini.is_available:
                return {"status": "ok", "provider": "gemini", "mode": "cloud"}
            return {"status": "fallback", "provider": "local", "mode": "extractive"}
        except Exception as exc:
            return {"status": "fallback", "provider": "local", "mode": "extractive", "error": str(exc)}

    def _jobs_check(self) -> Dict[str, Any]:
        stats = self.job_manager.stats()
        saturated = stats["in_flight"] >= stats["max_in_flight"]
        return {
            "status": "degraded" if saturated else "ok",
            **stats,
        }

    @staticmethod
    def _rollup_status(checks: Iterable[Dict[str, Any]]) -> str:
        statuses = {check.get("status") for check in checks}
        if "down" in statuses:
            return "down"
        if "degraded" in statuses:
            return "degraded"
        return "ok"