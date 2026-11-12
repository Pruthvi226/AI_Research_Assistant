"""Backend verification entrypoint for local development and CI."""

from __future__ import annotations

import argparse
import ast
import os
import pathlib
import secrets
import sys
import unittest
import uuid
from typing import Iterable, List

ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
EXCLUDED_PARTS = {"venv", "__pycache__", ".pytest_cache"}


def iter_python_files() -> Iterable[pathlib.Path]:
    for path in BACKEND.rglob("*.py"):
        if EXCLUDED_PARTS.intersection(path.parts):
            continue
        yield path


def check_syntax() -> int:
    files = list(iter_python_files())
    for path in files:
        source = path.read_text(encoding="utf-8-sig")
        ast.parse(source, filename=str(path))
    print(f"syntax ok: {len(files)} python files", flush=True)
    return len(files)


def run_unit_tests() -> unittest.result.TestResult:
    sys.path.insert(0, str(BACKEND))
    suite = unittest.defaultTestLoader.discover(str(BACKEND / "tests"))
    result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)
    return result


def smoke_flask_endpoints() -> None:
    sys.path.insert(0, str(BACKEND))
    from app import app, job_manager

    endpoints = [
        "/api/health",
        "/api/system/health",
        "/api/system/readiness",
        "/api/system/metrics",
    ]
    client = app.test_client()
    session = client.post(
        "/api/auth/register",
        json={
            "email": f"verify-{uuid.uuid4()}@example.test",
            "password": secrets.token_urlsafe(24),
        },
    )
    if session.status_code != 201:
        raise AssertionError(f"/api/auth/register returned {session.status_code}")
    token = session.get_json()["token"]
    for endpoint in endpoints:
        headers = {"X-Request-ID": "verify-backend"}
        if endpoint == "/api/system/metrics":
            headers["Authorization"] = f"Bearer {token}"
        response = client.get(endpoint, headers=headers)
        if response.status_code != 200:
            raise AssertionError(f"{endpoint} returned {response.status_code}")
        request_id = response.headers.get("X-Request-ID")
        if request_id != "verify-backend":
            raise AssertionError(f"{endpoint} did not preserve X-Request-ID")
        print(f"smoke ok: {endpoint} {response.status_code}", flush=True)
    job_manager.shutdown(wait=False)


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run backend syntax, unit, and optional smoke checks.")
    parser.add_argument("--smoke", action="store_true", help="Import Flask app and hit health/metrics endpoints.")
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    args = parse_args(argv or sys.argv[1:])
    check_syntax()
    run_unit_tests()
    if args.smoke:
        smoke_flask_endpoints()
    print("backend verification complete", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())