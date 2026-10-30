"""Authentication boundary tests without AI calls or running databases."""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from fastapi.testclient import TestClient
from api.main import app
from api.routers import auth
from persistence import auth_store, analysis_store

TOKEN = 'A' * 43
CSRF = auth_store.csrf_token(TOKEN)
USER = {'user_id': 'owner-a', 'email': 'a@example.com', 'display_name': 'Owner A'}


class AuthContractTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.client.cookies.set('patent_session', TOKEN)
        self.client.headers.update({'X-Requested-With': 'patent-client', 'X-CSRF-Token': CSRF})
        self.lookup = patch.object(auth_store, 'read_session', return_value={**USER, 'expires_at': datetime.now(timezone.utc) + timedelta(hours=1)})
        self.lookup.start()
        self.addCleanup(self.lookup.stop)

    def test_anonymous_requests_cannot_reach_analysis_or_private_reports(self):
        self.client.cookies.clear()
        for method, url, data in [('get', '/api/cases', None), ('get', '/api/reports/case_risk', None),
                                  ('get', '/api/kg/stats?patent_ids=p1', None), ('get', '/api/kg/graph?patent_ids=p1', None),
                                  ('post', '/api/pipeline/run', {'idea': 'sensor'}), ('post', '/api/evaluate', {'idea': 'sensor'}),
                                  ('post', '/api/evaluate/full', {'idea': 'sensor'}), ('post', '/api/improve', {'idea': 'sensor'}),
                                  ('post', '/api/kg/expand', {'patent_ids': ['p1']})]:
            with self.subTest(url=url):
                response = self.client.request(method, url, **({'json': data} if data is not None else {}))
                self.assertEqual(response.status_code, 401)

    def test_csrf_is_required_for_writes_but_me_returns_it(self):
        response = self.client.get('/api/auth/me')
        self.assertEqual(response.json()['csrf_token'], CSRF)
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.client.headers.pop('X-CSRF-Token')
        with patch.object(analysis_store, 'create_case') as create:
            self.assertEqual(self.client.post('/api/cases', json={'title': 'Case', 'idea_text': 'Sensor'}).status_code, 403)
            create.assert_not_called()

    def test_cross_origin_writes_are_rejected_even_with_valid_csrf(self):
        response = self.client.post('/api/auth/logout', headers={'Origin': 'https://untrusted.example'})
        self.assertEqual(response.status_code, 403)

    def test_invalid_or_expired_session_is_rejected(self):
        with patch.object(auth_store, 'read_session', return_value=None):
            self.assertEqual(self.client.get('/api/auth/me').status_code, 401)

    def test_account_storage_failure_is_503_without_connection_details(self):
        from persistence.database import DatabaseUnavailable
        with patch.object(auth_store, 'read_session', side_effect=DatabaseUnavailable('private connection details')):
            response = self.client.get('/api/auth/me')
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('private connection', response.text)

    def test_owned_saved_work_uses_server_snapshot_not_client_replacements(self):
        from api.auth import owned_run_input, Principal
        from improvement.schemas import ImprovementRequest
        original = {'idea_text': 'Original private idea', 'case_id': 'owned-case',
                    'pipeline_result': {'results': [{'patent_id': 'original'}]},
                    'evaluation_result': {'patentability_score': 60}}
        request = ImprovementRequest(idea='Forged idea', run_id='owned-run', pipeline_result={'run_id': 'owned-run', 'results': []}, evaluation_result={'patentability_score': 100})
        principal = Principal(**USER, csrf_token=CSRF, expires_at=datetime.now(timezone.utc))
        with patch.object(analysis_store, 'get_owned_run', return_value=original):
            owned_run_input(request, principal)
        self.assertEqual(request.idea, original['idea_text'])
        self.assertEqual(request.pipeline_result, original['pipeline_result'])
        self.assertEqual(request.evaluation_result, original['evaluation_result'])

    def test_foreign_case_cannot_start_an_ai_request(self):
        with patch.object(analysis_store, 'get_case', return_value=None) as lookup:
            response = self.client.post('/api/pipeline/run', json={'idea': 'sensor', 'case_id': 'foreign'})
        self.assertEqual(response.status_code, 404)
        lookup.assert_called_once_with('foreign', owner_user_id=USER['user_id'])

    def test_nested_foreign_run_ids_are_checked_before_evaluation_or_improvement(self):
        for path in ('/api/evaluate', '/api/evaluate/full', '/api/improve'):
            with self.subTest(path=path), patch.object(analysis_store, 'get_owned_run', return_value=None):
                response = self.client.post(path, json={'idea': 'sensor', 'pipeline_result': {'run_id': 'foreign', 'results': []}})
                self.assertEqual(response.status_code, 404)

    def test_login_rejects_form_origins_and_missing_custom_header(self):
        self.client.headers.pop('X-Requested-With')
        response = self.client.post('/api/auth/login', json={'email': 'a@example.com', 'password': 'Any password'})
        self.assertEqual(response.status_code, 403)

    def test_invalid_credentials_have_generic_message(self):
        with patch.object(auth_store, 'throttle', return_value=True), patch.object(auth_store, 'find_user', return_value=None):
            response = self.client.post('/api/auth/login', json={'email': 'missing@example.com', 'password': 'An incorrect passphrase'})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()['detail'], 'Email or password is incorrect.')

    def test_registration_validation_never_echoes_password(self):
        response = self.client.post('/api/auth/signup', json={'email': 'a@example.com', 'display_name': 'A', 'password': 'tiny-secret'})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn('tiny-secret', response.text)

    def test_login_cookie_is_http_only_secure_when_configured_and_token_is_not_json(self):
        password = 'Correct passphrase for a test'
        stored = {**USER, 'is_active': True, 'password_hash': auth.hasher.hash(password)}
        with patch.object(auth_store, 'throttle', return_value=True), patch.object(auth_store, 'find_user', return_value=stored), patch.object(auth_store, 'create_session', return_value=('B' * 43, datetime.now(timezone.utc) + timedelta(hours=1))), patch.dict(os.environ, {'SESSION_COOKIE_SECURE': 'true'}):
            response = self.client.post('/api/auth/login', json={'email': 'a@example.com', 'password': password})
        self.assertEqual(response.status_code, 200)
        cookie = response.headers['set-cookie']
        for flag in ('HttpOnly', 'Secure', 'SameSite=lax', 'Path=/api'):
            self.assertIn(flag, cookie)
        self.assertNotIn('B' * 43, response.text)
        self.assertNotIn(password, response.text)

    def test_login_throttled_before_password_work(self):
        with patch.object(auth_store, 'throttle', return_value=False), patch.object(auth_store, 'find_user') as find:
            response = self.client.post('/api/auth/login', json={'email': 'a@example.com', 'password': 'An incorrect passphrase'})
        self.assertEqual(response.status_code, 429)
        find.assert_not_called()

    def test_logout_revokes_only_current_session(self):
        with patch.object(auth_store, 'revoke_session') as revoke:
            response = self.client.post('/api/auth/logout')
        self.assertEqual(response.status_code, 204)
        revoke.assert_called_once_with(TOKEN)


if __name__ == '__main__':
    unittest.main()
