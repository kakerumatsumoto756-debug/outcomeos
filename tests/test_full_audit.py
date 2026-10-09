"""End-to-end local WSGI checks for auth, rooms, Panta, reports, permissions.

Panta is mocked deliberately: these tests verify our adapter and application
logic, not third-party production availability or credential validity.
"""
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app import panta, storage
import vercel_wsgi

MARKET_ID = '11111111111111111111111111111111'


class WSGIAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.temp.name) / 'outcome.sqlite3')
        self.env = patch.dict(os.environ, {'OUTCOMEOS_DB': self.db, 'DATABASE_URL': '',
                                        'OUTCOMEOS_SEED_EXAMPLES': '0', 'OUTCOMEOS_REQUIRE_POSTGRES': '0'})
        self.env.start()
        self.original_path = storage.DB_PATH
        storage.DB_PATH = self.db
        vercel_wsgi._initialized = False
        self.auth_cookie = ''
        self.csrf = ''

    def tearDown(self):
        vercel_wsgi._initialized = False
        storage.DB_PATH = self.original_path
        self.env.stop()
        self.temp.cleanup()

    def request(self, path, method='GET', body=None, *, cookie=None, csrf=None):
        b = json.dumps(body).encode() if body is not None else b''
        env = {'REQUEST_METHOD': method,
               'PATH_INFO': path.split('?')[0], 'QUERY_STRING': path.partition('?')[2],
               'HTTP_HOST': 'outcomeos.example', 'HTTP_ORIGIN': 'https://outcomeos.example',
               'wsgi.input': io.BytesIO(b), 'REMOTE_ADDR': '127.0.0.1'}
        if body is not None:
            env.update(CONTENT_TYPE='application/json', CONTENT_LENGTH=str(len(b)))
        if cookie is not None or self.auth_cookie:
            env['HTTP_COOKIE'] = cookie if cookie is not None else self.auth_cookie
        if csrf is not None or self.csrf:
            env['HTTP_X_CSRF_TOKEN'] = csrf if csrf is not None else self.csrf
        meta = []
        def start(status, headers): meta.extend((status, headers))
        with patch.object(vercel_wsgi,'_initialized', vercel_wsgi._initialized):
            response = b''.join(vercel_wsgi.application(env, start))
        code = int(meta[0].split(' ')[0])
        headers = dict(meta[1])
        try: data=json.loads(response)
        except Exception: data=response.decode()
        return code, headers, data

    def register(self, email='audit@example.test'):
        status, headers, data = self.request('/api/auth/register','POST',{'email':email,'display_name':'Audit User','password':'secure-password-123'})
        self.assertEqual(status,200, data)
        self.auth_cookie = headers['Set-Cookie'].split(';')[0]
        self.csrf = data['csrf']
        return data

    def test_full_e2e_decision_panta_forecast_report_and_session(self):
        self.register()
        code, _, auth = self.request('/api/auth/me')
        self.assertEqual(code,200)
        self.assertIsNotNone(auth['user'])
        code, _, workspaces = self.request('/api/workspaces')
        self.assertEqual(code,200)
        ws = workspaces['workspaces'][0]['id']
        code, _, created = self.request(f'/api/workspaces/{ws}/decisions','POST',
                                        {'title':'Panta market decision','question':'Will event X occur?',
                                         'description':'Compare future official resolution.'})
        self.assertEqual(code,201,created)
        did = created['id']
        code, _, overview=self.request(f'/api/workspaces/{ws}')
        self.assertEqual(code,200, overview)
        self.assertEqual(overview['metrics']['open'],1)
        self.assertEqual(overview['decisions'][0]['id'],did)
        code, _, forecast=self.request(f'/api/decisions/{did}/forecasts','POST',{'probability':63,'reason':'Reasoned estimate'})
        self.assertEqual(code,201, forecast)
        with patch.object(panta,'detail',return_value={'marketId':MARKET_ID,'title':'Test genuine-shaped Panta market',
                                                         'source':'live','phase':'primary','yesPrice':0.57,'noPrice':0.43}):
            code, _, link=self.request(f'/api/decisions/{did}/links','POST',{'market_id':MARKET_ID,'source':'live','match_explanation':'Same exact settlement event'})
            self.assertEqual(code,201,link)
            code, _, refresh=self.request(f"/api/links/{link['id']}/refresh",'POST',{})
            self.assertEqual(code,200)
            self.assertEqual(refresh['snapshot_result'],'unchanged')
        code, _, detail=self.request(f'/api/decisions/{did}')
        self.assertEqual(code,200)
        self.assertEqual(len(detail['links']),1)
        self.assertEqual(len(detail['links'][0]['history']),1)
        self.assertAlmostEqual(detail['team_probability'],.63)
        code, _, report=self.request(f'/api/decisions/{did}/report','POST',{})
        self.assertEqual(code,201,report)
        token=report['token']
        # public report from an anonymous client (must not leak notes or names)
        saved=self.auth_cookie;self.auth_cookie='';self.csrf=''
        code, _, public=self.request('/api/public/'+token)
        self.assertEqual(code,200,public)
        self.assertEqual(len(public['markets'][0]['history']),1)
        self.assertNotIn('email',json.dumps(public))
        self.assertNotIn('password',json.dumps(public))
        # Recycled server process simulation: session and records still durable.
        vercel_wsgi._initialized=False
        self.auth_cookie=saved
        code, _, auth=self.request('/api/auth/me')
        self.assertEqual(code,200)
        self.assertIsNotNone(auth['user'])
        code, _, again=self.request(f'/api/workspaces/{ws}')
        self.assertEqual(again['decisions'][0]['id'],did)

    def test_auth_csrf_enforced(self):
        self.register()
        ws=self.request('/api/workspaces')[2]['workspaces'][0]['id']
        self.csrf='invalid-token'
        status, _, response=self.request(f'/api/workspaces/{ws}/decisions','POST',{'title':'Oops','question':'Will this fail?'})
        self.assertEqual(status,403)
        self.assertIn('CSRF', response['error'])
        self.assertEqual(self.request(f'/api/workspaces/{ws}')[2]['metrics']['total'],0)

    def test_invalid_deadline_rejected_in_create_and_update(self):
        self.register()
        ws=self.request('/api/workspaces')[2]['workspaces'][0]['id']
        code, _, result=self.request(f'/api/workspaces/{ws}/decisions','POST',{'title':'Date test','question':'Will it happen?','deadline':'2026-02-30'})
        self.assertEqual(code,400,result)
        code,_,created=self.request(f'/api/workspaces/{ws}/decisions','POST',{'title':'Date test','question':'Will it happen?','deadline':'2026-12-31'})
        self.assertEqual(code,201,created)
        code,_,res=self.request(f"/api/decisions/{created['id']}",'PATCH',{'deadline':'2026-13-01'})
        self.assertEqual(code,400,res)

    def test_nonfinite_threshold_is_rejected(self):
        self.register()
        ws=self.request('/api/workspaces')[2]['workspaces'][0]['id']
        for value in ['nan', 'inf', '-inf']:
            code,_,obj=self.request(f'/api/workspaces/{ws}/alerts?threshold={value}')
            self.assertEqual(code,400,obj)

    def test_csv_export_prevents_formula_injection(self):
        self.register()
        ws=self.request('/api/workspaces')[2]['workspaces'][0]['id']
        code,_,created=self.request(f'/api/workspaces/{ws}/decisions','POST',{
            'title':'=HYPERLINK("https://example.test","click")',
            'question':'+SUM(1,2) is not a trustworthy forecast'})
        self.assertEqual(code,201,created)
        code,headers,raw=self.request(f'/api/workspaces/{ws}/csv')
        self.assertEqual(code,200)
        self.assertIn("'=HYPERLINK",raw)
        self.assertIn("'+SUM",raw)

    def test_invite_route_is_on_actual_app_not_marketing_page(self):
        text=Path(__file__).resolve().parents[1].joinpath('web','app.js').read_text()
        self.assertIn("location.origin+'/app?invite='",text)
        self.assertIn('const inviteToken=new URLSearchParams(location.search)',text)
        self.assertEqual(self.request('/app?invite=abc')[0],200)


if __name__=='__main__':unittest.main()
