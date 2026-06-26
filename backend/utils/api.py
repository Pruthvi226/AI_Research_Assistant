import threading
import time
from functools import wraps
from typing import Any, Dict, Tuple

from flask import jsonify, request


def api_error(message: str, status: int = 400, code: str = "bad_request", details: Dict[str, Any] | None = None):
    return jsonify({
        "error": message,
        "code": code,
        "details": details or {},
        "status": status,
    }), status


def require_json_fields(data: Dict[str, Any], *fields: str) -> Tuple[bool, str]:
    for field in fields:
        value = data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            return False, f"Missing required field: {field}"
    return True, ""


class SlidingWindowRateLimiter:
    """Thread-safe in-memory sliding-window limiter for single-node deployments."""

    def __init__(self, limit: int = 90, window_seconds: int = 60):
        self.limit = max(1, int(limit))
        self.window_seconds = max(1, int(window_seconds))
        self._hits: Dict[str, list] = {}
        self._accepted = 0
        self._rejected = 0
        self._lock = threading.Lock()

    def check(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.window_seconds
        with self._lock:
            hits = [ts for ts in self._hits.get(key, []) if ts >= cutoff]
            if len(hits) >= self.limit:
                self._hits[key] = hits
                self._rejected += 1
                self._prune_locked(cutoff)
                return False
            hits.append(now)
            self._hits[key] = hits
            self._accepted += 1
            self._prune_locked(cutoff)
            return True

    def stats(self) -> Dict[str, Any]:
        cutoff = time.time() - self.window_seconds
        with self._lock:
            self._prune_locked(cutoff)
            active_hits = sum(len(hits) for hits in self._hits.values())
            return {
                "limit": self.limit,
                "window_seconds": self.window_seconds,
                "tracked_keys": len(self._hits),
                "active_hits": active_hits,
                "accepted": self._accepted,
                "rejected": self._rejected,
            }

    def _prune_locked(self, cutoff: float) -> None:
        stale = []
        for key, hits in self._hits.items():
            fresh_hits = [ts for ts in hits if ts >= cutoff]
            if fresh_hits:
                self._hits[key] = fresh_hits
            else:
                stale.append(key)
        for key in stale:
            self._hits.pop(key, None)


def rate_limited(limiter: SlidingWindowRateLimiter):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = request.headers.get("X-Forwarded-For", request.remote_addr or "local")
            key = key.split(",", 1)[0].strip()
            if not limiter.check(key):
                return api_error("Too many requests. Please wait a moment and retry.", 429, "rate_limited")
            return fn(*args, **kwargs)
        return wrapper
    return decorator