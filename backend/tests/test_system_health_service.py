import unittest

from services.system_health_service import SystemHealthService


class FakeConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, query):
        return self

    def fetchone(self):
        return (1,)


class FakeDB:
    def __init__(self, fail=False):
        self.fail = fail

    def get_connection(self):
        if self.fail:
            raise RuntimeError("database unavailable")
        return FakeConnection()


class FakeEmbeddingEngine:
    use_semantic = False
    has_index = True
    _chunks = ["chunk one", "chunk two"]


class FakeJobManager:
    def stats(self):
        return {
            "max_workers": 2,
            "max_in_flight": 5,
            "max_retained_jobs": 50,
            "retained_jobs": 1,
            "in_flight": 1,
            "status_counts": {"queued": 1},
            "submitted": 1,
            "completed": 0,
            "failed": 0,
            "rejected": 0,
        }


class FakeRateLimiter:
    def stats(self):
        return {"accepted": 3, "rejected": 1, "tracked_keys": 1}


class FakeGemini:
    is_available = False


class SystemHealthServiceTest(unittest.TestCase):
    def build_service(self, db=None):
        return SystemHealthService(
            db=db or FakeDB(),
            embedding_engine=FakeEmbeddingEngine(),
            job_manager=FakeJobManager(),
            rate_limiter=FakeRateLimiter(),
            gemini_provider=lambda: FakeGemini(),
            runtime_warnings_provider=lambda: ["optional warning"],
        )

    def test_snapshot_reports_core_dependencies_and_fallback_llm(self):
        snapshot = self.build_service().snapshot()

        self.assertEqual("ok", snapshot["status"])
        self.assertEqual("ok", snapshot["checks"]["database"]["status"])
        self.assertEqual("fallback", snapshot["checks"]["llm"]["status"])
        self.assertEqual(2, snapshot["checks"]["retrieval"]["active_chunks"])

    def test_readiness_fails_when_database_is_down(self):
        readiness = self.build_service(db=FakeDB(fail=True)).readiness()

        self.assertFalse(readiness["ready"])
        self.assertEqual("down", readiness["status"])
        self.assertIn("database", readiness["blocking_dependencies"])

    def test_metrics_include_queue_rate_limit_and_retrieval(self):
        metrics = self.build_service().metrics()

        self.assertEqual(1, metrics["jobs"]["in_flight"])
        self.assertEqual(3, metrics["rate_limiter"]["accepted"])
        self.assertEqual("lexical", metrics["retrieval"]["mode"])


if __name__ == "__main__":
    unittest.main()