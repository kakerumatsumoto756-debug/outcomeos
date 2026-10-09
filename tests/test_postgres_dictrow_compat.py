"""Regression: production psycopg dict_row must not trigger KeyError(0).

Runs fully offline, using SQLite's compatible mapping row_factory to test
PostgreSQL-style dictionary-only rows in the complete overview code path.
"""
import sqlite3
import unittest
from app import storage as s


def dict_row_factory(cursor, values):
    return {column[0]: value for column, value in zip(cursor.description, values)}


class PostgresDictionaryRowTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.execute('PRAGMA foreign_keys=ON')
        self.conn.row_factory = dict_row_factory
        self.conn.executescript(s.DDL)
        self.user_id = self.conn.execute(
            "INSERT INTO users (email,display_name,password_hash,created_at) VALUES (?,?,?,?) RETURNING id",
            ('dictrow@example.test','Mapping Test','not-used',s.utc())
        ).fetchone()['id']
        self.ws_id = s.create_workspace(self.conn,self.user_id,'Dict rows workspace')

    def tearDown(self):
        self.conn.close()

    def test_empty_workspace_overview_with_mapping_rows(self):
        overview=s.overview(self.conn,self.ws_id,self.user_id)
        self.assertEqual(overview['decisions'],[])
        self.assertEqual(overview['metrics']['total'],0)

    def test_created_decision_overview_with_mapping_rows(self):
        decision_id=s.create_decision(self.conn,self.ws_id,self.user_id,
                                      'QA market','Will it happen?')
        overview=s.overview(self.conn,self.ws_id,self.user_id)
        self.assertEqual(overview['metrics']['total'],1)
        self.assertEqual(overview['metrics']['open'],1)
        self.assertEqual(overview['decisions'][0]['id'],decision_id)
        self.assertEqual(overview['decisions'][0]['link_count'],0)
        self.assertEqual(overview['decisions'][0]['forecast_count'],0)

    def test_nonzero_counts_with_mapping_rows(self):
        did=s.create_decision(self.conn,self.ws_id,self.user_id,
                              'QA market','Will it happen?')
        self.conn.execute('INSERT INTO forecasts(decision_id,user_id,probability,reason,created_at) VALUES(?,?,?,?,?)',
                          (did,self.user_id,0.7,'QA',s.utc()))
        self.conn.execute('INSERT INTO market_links(decision_id,market_id,market_title,source,match_explanation,created_at) VALUES(?,?,?,?,?,?)',
                          (did,'demo-growth-2026','QA market','demo','test',s.utc()))
        overview=s.overview(self.conn,self.ws_id,self.user_id)
        self.assertEqual(overview['decisions'][0]['link_count'],1)
        self.assertEqual(overview['decisions'][0]['forecast_count'],1)
        self.assertEqual(overview['metrics']['markets'],1)


if __name__ == '__main__':
    unittest.main()


class WSGIMappingRowRoundTripTests(unittest.TestCase):
    """Login, decision creation and session refresh with PostgreSQL-like rows."""

    def test_signup_create_decision_reload_overview(self):
        import io
        import json
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        import vercel_wsgi

        with tempfile.TemporaryDirectory() as temp:
            database_file=str(Path(temp)/'dictrow-test.sqlite')

            def connect_with_mapping_rows():
                conn=sqlite3.connect(database_file)
                conn.execute('PRAGMA foreign_keys=ON')
                conn.row_factory=dict_row_factory
                return conn

            def request(path,method='GET',body=None,cookie=None,csrf=None):
                data=json.dumps(body).encode() if body is not None else b''
                environ={'REQUEST_METHOD':method,'PATH_INFO':path,
                         'wsgi.input':io.BytesIO(data),'REMOTE_ADDR':'127.0.0.1',
                         'HTTP_HOST':'localhost'}
                if body is not None:
                    environ.update(CONTENT_TYPE='application/json', CONTENT_LENGTH=str(len(data)))
                if cookie:environ['HTTP_COOKIE']=cookie
                if csrf:environ['HTTP_X_CSRF_TOKEN']=csrf
                details=[]
                def start_response(status, headers):details.extend([status,headers])
                content=b''.join(vercel_wsgi.application(environ,start_response))
                return int(details[0].split()[0]),dict(details[1]),json.loads(content)

            with patch.object(s,'connect',side_effect=connect_with_mapping_rows), \
                 patch.object(vercel_wsgi,'_initialized',False), \
                 patch.dict(os.environ,{'OUTCOMEOS_SEED_EXAMPLES':'0'}):
                status, headers, result=request('/api/auth/register','POST',{
                    'email':'e2e@example.test','password':'test-password123',
                    'display_name':'E2E Tester'})
                self.assertEqual(status,200)
                session_cookie=headers['Set-Cookie'].split(';')[0]
                csrf=result['csrf']
                status,_,result=request('/api/auth/me',cookie=session_cookie)
                self.assertEqual(status,200)
                self.assertIsNotNone(result['user'])
                status,_,result=request('/api/workspaces',cookie=session_cookie)
                self.assertEqual(status,200)
                workspace_id=result['workspaces'][0]['id']
                status,_,result=request(f'/api/workspaces/{workspace_id}/decisions','POST',{
                    'title':'Integration QA','question':'Will Decision Room work?'
                },cookie=session_cookie,csrf=csrf)
                self.assertEqual(status,201)
                decision_id=result['id']
                status,_,result=request(f'/api/workspaces/{workspace_id}',cookie=session_cookie)
                self.assertEqual(status,200)
                self.assertEqual(result['metrics']['total'],1)
                self.assertEqual(result['decisions'][0]['id'],decision_id)
                status,_,result=request('/api/auth/me',cookie=session_cookie)
                self.assertEqual(status,200)
                self.assertIsNotNone(result['user'])

    def test_programming_key_error_is_500_not_misleading_404(self):
        import io
        from contextlib import contextmanager
        from unittest.mock import patch
        from vercel_wsgi import _WSGIHandler

        @contextmanager
        def database():
            yield None

        h=_WSGIHandler({'REQUEST_METHOD':'GET','PATH_INFO':'/api/auth/me',
                        'wsgi.input':io.BytesIO(b'')})
        with patch.object(s,'database',database),patch.object(h,'api',side_effect=KeyError(0)),\
             patch('traceback.print_exc'):
            h.handle_req('GET')
        self.assertEqual(h._status,500)
        self.assertIn(b'Unexpected server error',h.wfile.getvalue())
