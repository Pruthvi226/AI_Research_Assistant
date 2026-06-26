import unittest

from utils.api import SlidingWindowRateLimiter


class SlidingWindowRateLimiterTest(unittest.TestCase):
    def test_limiter_rejects_after_limit_and_reports_stats(self):
        limiter = SlidingWindowRateLimiter(limit=2, window_seconds=60)

        self.assertTrue(limiter.check("client-a"))
        self.assertTrue(limiter.check("client-a"))
        self.assertFalse(limiter.check("client-a"))

        stats = limiter.stats()
        self.assertEqual(2, stats["accepted"])
        self.assertEqual(1, stats["rejected"])
        self.assertEqual(1, stats["tracked_keys"])


if __name__ == "__main__":
    unittest.main()