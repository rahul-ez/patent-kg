"""Opt-in MySQL authentication/ownership checks; clean only their own UUID data."""
import os
import secrets
import sys
import types
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'backend/src'))


@unittest.skipUnless(os.getenv('RUN_DATABASE_TESTS') == '1', 'Set RUN_DATABASE_TESTS=1')
class LiveAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from dotenv import load_dotenv
        load_dotenv(ROOT / '.env')
        from api.main import app
        from api.routers import auth
        from persistence.database import get_engine
        from fastapi.testclient import TestClient
        cls.app = app
        cls.engine = get_engine()
        cls.users = []
        cls.password = secrets.token_urlsafe(24)
        for label in ('A', 'B'):
            email = 'auth-check-' + str(uuid4()) + '@example.com'
            client = TestClient(app, headers={'X-Requested-With': 'patent-client'})
            with patch.object(auth.auth_store, 'throttle', return_value=True):
                response = client.post('/api/auth/signup', json={'email': email, 'password': cls.password, 'display_name': 'Auth verification ' + label})
            if response.status_code != 201:
                raise AssertionError('Temporary signup failed: ' + str(response.status_code))
            cls.users.append(response.json()['user'])

    @classmethod
    def tearDownClass(cls):
        from sqlalchemy import text
        with cls.engine.begin() as connection:
            for user in cls.users:
                # The accounts were created by this class; their sessions cascade.
                connection.execute(text('DELETE FROM analysis_cases WHERE owner_user_id=:id'), {'id': user['user_id']})
                connection.execute(text('DELETE FROM app_users WHERE user_id=:id'), {'id': user['user_id']})

    def setUp(self):
        from fastapi.testclient import TestClient
        from persistence import auth_store, analysis_store
        self.auth = auth_store
        self.store = analysis_store
        self.cases = []
        self.clients = []
        self.tokens = []
        for user in self.users:
            token, _ = auth_store.create_session(user['user_id'], 1)
            client = TestClient(self.app, headers={'X-Requested-With': 'patent-client', 'X-CSRF-Token': auth_store.csrf_token(token)})
            client.cookies.set('patent_session', token)
            self.clients.append(client)
            self.tokens.append(token)
        self.a, self.b = self.clients
        created = self.a.post('/api/cases', json={'title': 'Private verification case', 'idea_text': 'A private test sensor invention'})
        self.assertEqual(created.status_code, 201)
        self.case = created.json()
        self.cases.append(self.case['case_id'])

    def tearDown(self):
        from sqlalchemy import text
        with self.engine.begin() as connection:
            for case_id in self.cases:
                connection.execute(text('DELETE FROM analysis_cases WHERE case_id=:id'), {'id': case_id})
        for token in self.tokens:
            self.auth.revoke_session(token)

    def pipeline(self):
        return {'query_id': 'repeated-auth-test-query', 'query_text': 'private sensor', 'nlp_result': {'clean_text': 'private sensor', 'keywords': [], 'entities': []},
                'model': 'controlled-auth-test-fixture', 'top_k': 1, 'results': [], 'gnn_status': 'success', 'kg_status': 'success'}

    def saved_run(self):
        return self.store.persist_pipeline_result('Original private idea', 1, 'novelty', self.pipeline(), self.case['case_id'], owner_user_id=self.users[0]['user_id'])

    def test_login_hashes_sessions_and_logout_revokes_captured_cookie(self):
        from sqlalchemy import text
        from api.routers import auth
        with patch.object(auth.auth_store, 'throttle', return_value=True):
            response = self.a.post('/api/auth/login', json={'email': self.users[0]['email'].upper(), 'password': self.password})
        self.assertEqual(response.status_code, 200)
        token = self.a.cookies.get('patent_session', domain='testserver.local', path='/api')
        self.tokens.append(token)
        self.a.cookies.clear()
        self.a.cookies.set('patent_session', token)
        self.a.headers['X-CSRF-Token'] = response.json()['csrf_token']
        with self.engine.connect() as connection:
            password_hash = connection.execute(text('SELECT password_hash FROM app_users WHERE user_id=:id'), {'id': self.users[0]['user_id']}).scalar_one()
            stored = connection.execute(text('SELECT token_hash FROM auth_sessions WHERE token_hash=:hash'), {'hash': self.auth.digest(token)}).scalar_one()
        self.assertTrue(password_hash.startswith('$argon2id$'))
        self.assertNotEqual(password_hash, self.password)
        self.assertNotEqual(stored, token)
        self.assertEqual(self.a.post('/api/auth/logout').status_code, 204)
        self.a.cookies.set('patent_session', token)
        self.assertEqual(self.a.get('/api/auth/me').status_code, 401)

    def test_other_users_cannot_list_read_update_delete_or_append(self):
        self.assertNotIn(self.case['case_id'], [case['case_id'] for case in self.b.get('/api/cases').json()])
        self.assertEqual(self.b.get('/api/cases/' + self.case['case_id']).status_code, 404)
        self.assertEqual(self.b.patch('/api/cases/' + self.case['case_id'], json={'title': 'Hijacked'}).status_code, 404)
        self.assertEqual(self.b.delete('/api/cases/' + self.case['case_id']).status_code, 404)
        response = self.b.post('/api/pipeline/run', json={'idea': 'sensor', 'case_id': self.case['case_id']})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.a.get('/api/cases/' + self.case['case_id']).json()['title'], 'Private verification case')

    def test_run_ownership_is_enforced_for_reads_nested_ids_and_direct_writes(self):
        saved = self.saved_run()
        run_id = saved['run_id']
        self.assertEqual(self.b.get('/api/cases/' + self.case['case_id'] + '/runs/' + run_id).status_code, 404)
        for url in ('/api/evaluate', '/api/evaluate/full', '/api/improve'):
            for payload in ({'idea': 'sensor', 'run_id': run_id}, {'idea': 'sensor', 'pipeline_result': {'run_id': run_id}}):
                with self.subTest(url=url, nested='pipeline_result' in payload):
                    self.assertEqual(self.b.post(url, json=payload).status_code, 404)
        with self.assertRaises(ValueError):
            self.store.persist_evaluation(run_id, {'patentability_score': 1, 'risk': 'High', 'verdict': 'Test'}, owner_user_id=self.users[1]['user_id'])
        with self.assertRaises(ValueError):
            self.store.persist_improvements(run_id, {'strategies': []}, owner_user_id=self.users[1]['user_id'])

    def test_authorized_pipeline_saves_under_session_owner_and_preserves_runs(self):
        module = types.ModuleType('integration.pipeline')
        module.run_end_to_end = lambda *args, **kwargs: self.pipeline()
        with patch.dict(sys.modules, {'integration.pipeline': module}):
            for _ in range(2):
                response = self.a.post('/api/pipeline/run', json={'idea': 'Revised private idea', 'top_k': 1, 'case_id': self.case['case_id'], 'owner_user_id': self.users[1]['user_id']})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['persistence_status'], 'persisted')
        case = self.a.get('/api/cases/' + self.case['case_id']).json()
        self.assertEqual(len(case['runs']), 2)
        run = self.a.get('/api/cases/' + self.case['case_id'] + '/runs/' + case['runs'][0]['run_id']).json()
        self.assertEqual(run['idea_text'], 'Revised private idea')
        self.assertEqual(self.b.get('/api/cases/' + self.case['case_id']).status_code, 404)

    def test_case_risk_report_never_exposes_another_owners_rows(self):
        saved = self.saved_run()
        self.store.persist_evaluation(saved['run_id'], {'patentability_score': 61, 'risk': 'Medium', 'verdict': 'Test'}, owner_user_id=self.users[0]['user_id'])
        self.assertIn(self.case['case_id'], [row['case_id'] for row in self.a.get('/api/reports/case_risk').json()['rows']])
        self.assertNotIn(self.case['case_id'], [row['case_id'] for row in self.b.get('/api/reports/case_risk').json()['rows']])

    def test_expired_and_disabled_sessions_are_rejected(self):
        from sqlalchemy import text
        with self.engine.begin() as connection:
            connection.execute(text('UPDATE auth_sessions SET expires_at=:expiry WHERE token_hash=:hash'), {'expiry': datetime.now() - timedelta(days=2), 'hash': self.auth.digest(self.tokens[0])})
        self.assertEqual(self.a.get('/api/auth/me').status_code, 401)
        with self.engine.begin() as connection:
            connection.execute(text('UPDATE app_users SET is_active=FALSE WHERE user_id=:id'), {'id': self.users[1]['user_id']})
        try:
            self.assertEqual(self.b.get('/api/auth/me').status_code, 401)
        finally:
            with self.engine.begin() as connection:
                connection.execute(text('UPDATE app_users SET is_active=TRUE WHERE user_id=:id'), {'id': self.users[1]['user_id']})

    def test_orphan_case_requires_explicit_operator_assignment(self):
        from sqlalchemy import text
        import importlib.util
        case_id = str(uuid4())
        self.cases.append(case_id)
        with self.engine.begin() as connection:
            connection.execute(text("INSERT INTO analysis_cases(case_id,title,idea_text,status) VALUES (:id,'Temporary orphan','Temporary idea','draft')"), {'id': case_id})
        self.assertEqual(self.a.get('/api/cases/' + case_id).status_code, 404)
        self.assertEqual(self.b.get('/api/cases/' + case_id).status_code, 404)
        spec = importlib.util.spec_from_file_location('assign_case_owner', ROOT / 'backend/scripts/database/assign_case_owner.py')
        operator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(operator)
        operator.assign(self.engine, case_id, self.users[0]['email'])
        self.assertEqual(self.a.get('/api/cases/' + case_id).status_code, 200)
        self.assertEqual(self.b.get('/api/cases/' + case_id).status_code, 404)
        with self.assertRaises(ValueError):
            operator.assign(self.engine, case_id, self.users[1]['email'])

    def test_shared_database_throttle_is_enforced_and_reset_after_window(self):
        from sqlalchemy import text
        key = 'auth-verification-' + str(uuid4())
        try:
            self.assertTrue(self.auth.throttle(key, 2, 60))
            self.assertTrue(self.auth.throttle(key, 2, 60))
            self.assertFalse(self.auth.throttle(key, 2, 60))
            with self.engine.begin() as connection:
                connection.execute(text('UPDATE auth_rate_limits SET window_started=:past WHERE bucket_key=:key'), {'past': datetime.now() - timedelta(days=2), 'key': self.auth.digest(key)})
            self.assertTrue(self.auth.throttle(key, 2, 60))
        finally:
            with self.engine.begin() as connection:
                connection.execute(text('DELETE FROM auth_rate_limits WHERE bucket_key=:key'), {'key': self.auth.digest(key)})


if __name__ == '__main__':
    unittest.main()
