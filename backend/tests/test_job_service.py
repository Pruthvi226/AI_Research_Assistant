import threading
import time
import unittest

from services.job_service import JobManager, JobQueueFull


class JobManagerTest(unittest.TestCase):
    def test_queue_full_raises_before_accepting_more_work(self):
        started = threading.Event()
        release = threading.Event()
        manager = JobManager(max_workers=1, max_retained_jobs=5, max_in_flight=1)

        def blocking_job(job_id=None):
            started.set()
            release.wait(timeout=2)
            return {"job_id": job_id}

        try:
            job_id = manager.submit("blocking", blocking_job)
            self.assertTrue(started.wait(timeout=1))

            with self.assertRaises(JobQueueFull):
                manager.submit("overflow", lambda job_id=None: None)

            stats = manager.stats()
            self.assertEqual(1, stats["rejected"])
            self.assertEqual(1, stats["in_flight"])
        finally:
            release.set()
            deadline = time.time() + 2
            while time.time() < deadline:
                job = manager.get(job_id)
                if job and job["status"] == "done":
                    break
                time.sleep(0.02)
            manager.shutdown(wait=True)


if __name__ == "__main__":
    unittest.main()