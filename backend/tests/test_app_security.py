import gc
import tempfile
import time
import unittest
from pathlib import Path

import app as app_module
from database import DBManager


class AppSecurityTest(unittest.TestCase):
    def setUp(self):
        test_root = Path(__file__).resolve().parents[2] / ".codex-test" / "backend-tests"
        test_root.mkdir(parents=True, exist_ok=True)
        self.workspace = tempfile.TemporaryDirectory(dir=test_root)
        self.root = Path(self.workspace.name)
        self.db = DBManager(str(self.root / "security.db"))
        self.original_db = app_module.db
        self.original_auth_db = app_module.auth_service.database
        self.original_rag_db = app_module.rag_agent.db
        self.original_orchestrator_db = app_module.orchestrator_agent.db
        app_module.db = self.db
        app_module.auth_service.database = self.db
        app_module.rag_agent.db = self.db
        app_module.orchestrator_agent.db = self.db
        with app_module.auth_rate_limiter._lock:
            app_module.auth_rate_limiter._hits.clear()
        self.client = app_module.app.test_client()
        self.owner = self.create_account("owner@example.test")
        self.owner_client = self.authorized_client(self.owner["token"])

    def tearDown(self):
        app_module.db = self.original_db
        app_module.auth_service.database = self.original_auth_db
        app_module.rag_agent.db = self.original_rag_db
        app_module.orchestrator_agent.db = self.original_orchestrator_db
        gc.collect()
        expected = Path(__file__).resolve().parents[2] / ".codex-test" / "backend-tests"
        assert self.root.resolve().is_relative_to(expected.resolve())
        self.workspace.cleanup()

    def create_account(self, email):
        response = self.client.post(
            "/api/auth/register",
            json={"email": email, "password": "research-password-42"},
        )
        self.assertEqual(201, response.status_code, response.get_json())
        return response.get_json()

    @staticmethod
    def authorized_client(token):
        client = app_module.app.test_client()
        client.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        return client

    def test_security_headers_are_attached_to_public_health_responses(self):
        response = self.client.get("/api/health")
        self.assertEqual("nosniff", response.headers.get("X-Content-Type-Options"))
        self.assertEqual("DENY", response.headers.get("X-Frame-Options"))
        self.assertIn("frame-ancestors 'none'", response.headers.get("Content-Security-Policy", ""))

    def test_authentication_rejects_anonymous_and_legacy_admin_key_requests(self):
        for path in ("/api/documents", "/api/history", "/api/generated-outputs", "/api/jobs", "/api/settings"):
            anonymous = self.client.get(path)
            self.assertEqual(401, anonymous.status_code, path)
            self.assertEqual("authentication_required", anonymous.get_json()["code"])

        admin_only = self.client.get("/api/documents", headers={"X-Admin-Key": "legacy-shared-key"})
        self.assertEqual(401, admin_only.status_code)
        self.assertEqual(200, self.owner_client.get("/api/settings").status_code)
        denied_setting_change = self.owner_client.post(
            "/api/settings", json={"gemini_api_key": "must-not-be-saved"}
        )
        self.assertEqual(403, denied_setting_change.status_code)
        self.assertNotIn("must-not-be-saved", denied_setting_change.get_data(as_text=True))

    def test_user_ownership_is_enforced_for_documents_chats_outputs_and_jobs(self):
        other = self.create_account("other@example.test")
        other_client = self.authorized_client(other["token"])
        doc_id = "private-document"
        self.db.save_document(
            doc_id,
            "private.pdf",
            "",
            {"summary": {"abstract": "private evidence"}},
            owner_id=self.owner["user"]["id"],
            full_text="private document evidence",
            chunks=["[Source 1 | private.pdf | page 1 | chunk 1] private document evidence"],
        )
        self.db.add_chat_msg(doc_id, "user", "private question", self.owner["user"]["id"])
        output_id = self.db.save_generated_output(
            doc_id,
            "markdown",
            "private.md",
            owner_id=self.owner["user"]["id"],
            content="private output",
        )
        job_id = app_module.job_manager.submit(
            "owned_test_job",
            lambda job_id=None: {"finished": True},
            owner_id=self.owner["user"]["id"],
        )
        deadline = time.time() + 2
        while time.time() < deadline:
            job = app_module.job_manager.get(job_id, owner_id=self.owner["user"]["id"])
            if job and job["status"] in {"done", "failed"}:
                break
            time.sleep(0.01)

        self.assertEqual(200, self.owner_client.get("/api/documents").status_code)
        self.assertEqual(
            doc_id,
            self.owner_client.get(f"/api/documents/{doc_id}").get_json()["session_id"],
        )
        self.assertEqual(1, len(self.owner_client.get(
            "/api/history", query_string={"session_id": doc_id}
        ).get_json()["history"]))
        self.assertEqual(200, self.owner_client.get(
            f"/api/generated-outputs/{output_id}/download"
        ).status_code)
        self.assertEqual(200, self.owner_client.get(f"/api/jobs/{job_id}").status_code)

        self.assertEqual([], other_client.get("/api/documents").get_json()["documents"])
        self.assertEqual(404, other_client.get(f"/api/documents/{doc_id}").status_code)
        self.assertEqual(404, other_client.get(f"/api/documents/{doc_id}/file").status_code)
        self.assertEqual(404, other_client.get(
            f"/api/documents/{doc_id}/export/markdown"
        ).status_code)
        self.assertEqual(404, other_client.delete(f"/api/documents/{doc_id}").status_code)
        self.assertEqual(404, other_client.post(
            "/api/chat", json={"question": "private?", "session_id": doc_id}
        ).status_code)
        self.assertEqual([], other_client.get(
            "/api/history", query_string={"session_id": doc_id}
        ).get_json()["history"])
        self.assertEqual([], other_client.get(
            "/api/generated-outputs"
        ).get_json()["generated_outputs"])
        self.assertEqual(404, other_client.get(
            f"/api/generated-outputs/{output_id}"
        ).status_code)
        self.assertEqual(404, other_client.get(
            f"/api/generated-outputs/{output_id}/download"
        ).status_code)
        self.assertNotIn(job_id, [job["id"] for job in other_client.get(
            "/api/jobs"
        ).get_json()["jobs"]])
        self.assertEqual(404, other_client.get(f"/api/jobs/{job_id}").status_code)

    def test_registration_validation_login_and_logout(self):
        invalid = self.client.post(
            "/api/auth/register",
            json={"email": "not-an-email", "password": "short"},
        )
        self.assertEqual(400, invalid.status_code)
        duplicate = self.client.post(
            "/api/auth/register",
            json={"email": "OWNER@example.test", "password": "research-password-42"},
        )
        self.assertEqual(409, duplicate.status_code)
        login = self.client.post(
            "/api/auth/login",
            json={"email": "OWNER@example.test", "password": "research-password-42"},
        )
        self.assertEqual(200, login.status_code)
        self.assertNotIn("password_hash", login.get_json())
        session = self.authorized_client(login.get_json()["token"])
        self.assertEqual(200, session.get("/api/auth/me").status_code)
        self.assertEqual(200, session.post("/api/auth/logout").status_code)
        self.assertEqual(401, session.get("/api/auth/me").status_code)


if __name__ == "__main__":
    unittest.main()
