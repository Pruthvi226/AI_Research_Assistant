import unittest

import app as app_module


class AppSecurityTest(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()
        self.original_require_admin = app_module.FlaskConfig.REQUIRE_ADMIN_AUTH
        self.original_admin_key = app_module.FlaskConfig.ADMIN_API_KEY

    def tearDown(self):
        app_module.FlaskConfig.REQUIRE_ADMIN_AUTH = self.original_require_admin
        app_module.FlaskConfig.ADMIN_API_KEY = self.original_admin_key

    def test_security_headers_are_attached_to_api_responses(self):
        response = self.client.get('/api/health')

        self.assertEqual('nosniff', response.headers.get('X-Content-Type-Options'))
        self.assertEqual('DENY', response.headers.get('X-Frame-Options'))
        self.assertIn("frame-ancestors 'none'", response.headers.get('Content-Security-Policy', ''))

    def test_sensitive_routes_require_admin_key_when_enabled(self):
        app_module.FlaskConfig.REQUIRE_ADMIN_AUTH = True
        app_module.FlaskConfig.ADMIN_API_KEY = 'test-admin-key'

        blocked = self.client.get('/api/settings')
        allowed = self.client.get('/api/settings', headers={'X-Admin-Key': 'test-admin-key'})

        self.assertEqual(401, blocked.status_code)
        self.assertEqual('admin_auth_required', blocked.get_json().get('code'))
        self.assertEqual(200, allowed.status_code)

    def test_job_detail_polling_is_allowed_but_job_list_is_admin_only(self):
        app_module.FlaskConfig.REQUIRE_ADMIN_AUTH = True
        app_module.FlaskConfig.ADMIN_API_KEY = 'test-admin-key'

        list_response = self.client.get('/api/jobs')
        detail_response = self.client.get('/api/jobs/missing-job-id')

        self.assertEqual(401, list_response.status_code)
        self.assertEqual('admin_auth_required', list_response.get_json().get('code'))
        self.assertEqual(404, detail_response.status_code)



if __name__ == '__main__':
    unittest.main()
