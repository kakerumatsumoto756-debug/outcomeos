"""Unit and HTTP integration tests. All Panta responses mocked—never fabricate live connectivity."""
import http.cookiejar, json, os, tempfile, threading, unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

tmp=tempfile.TemporaryDirectory(prefix='outcomeos-test-')
os.environ['OUTCOMEOS_DB']=str(Path(tmp.name)/'test.sqlite3')
from app import storage as s,panta
from app.http_api import create_server,demo_markets,probability,RequestError

class TestCore(unittest.TestCase):
    def setUp(self):
        s.init_db()
        with s.database() as c:
            c.execute('DELETE FROM public_reports');c.execute('DELETE FROM invites');c.execute('DELETE FROM sessions');c.execute('DELETE FROM notes');c.execute('DELETE FROM snapshots');c.execute('DELETE FROM market_links');c.execute('DELETE FROM forecasts');c.execute('DELETE FROM audit');c.execute('DELETE FROM decisions');c.execute('DELETE FROM memberships');c.execute('DELETE FROM workspaces');c.execute('DELETE FROM users')
    def test_password(self):
        secret=s.pw_hash('very-secure-passphrase')
        self.assertTrue(s.pw_verify('very-secure-passphrase',secret))
        self.assertFalse(s.pw_verify('wrong',secret))
        self.assertNotIn('very-secure-passphrase',secret)
    def test_probability_validation(self):
        self.assertEqual(probability(78),.78)
        for v in [-1,101,'nope',None,False]:
            with self.assertRaises(RequestError):probability(v)
    def test_team_forecast_uses_last_submission_per_user(self):
        with s.database() as c:
            alice=c.execute("INSERT INTO users(email,display_name,password_hash,created_at) VALUES('a@b.co','Alice','h','now')").lastrowid
            bob=c.execute("INSERT INTO users(email,display_name,password_hash,created_at) VALUES('b@b.co','Bob','h','now')").lastrowid
            ws=s.create_workspace(c,alice,'Demo')
            c.execute("INSERT INTO memberships VALUES(?,?,'member')",(ws,bob))
            did=s.create_decision(c,ws,alice,'Ship it','Will it ship?')
            for uid,p in [(alice,.1),(alice,.8),(bob,.6)]: c.execute('INSERT INTO forecasts(decision_id,user_id,probability,reason,created_at) VALUES(?,?,?,?,?)',(did,uid,p,'','now'))
            self.assertAlmostEqual(s.latest_team_forecast(c,did),.7)
            c.execute("UPDATE decisions SET status='resolved',outcome=1 WHERE id=?",(did,))
            self.assertEqual(s.score(c,ws)['evaluated_forecasts'],2)
            self.assertAlmostEqual(s.score(c,ws)['brier'],.10)
    def test_workspace_authorization(self):
        with s.database() as c:
            alice=c.execute("INSERT INTO users(email,display_name,password_hash,created_at) VALUES('alice@b.co','Alice','h','now')").lastrowid
            bob=c.execute("INSERT INTO users(email,display_name,password_hash,created_at) VALUES('bob@b.co','Bob','h','now')").lastrowid
            ws=s.create_workspace(c,alice,'Private')
            did=s.create_decision(c,ws,alice,'Secret','Will it happen?')
            with self.assertRaises(PermissionError):s.get_decision(c,did,bob)
    def test_panta_no_key(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(panta.PantaError,'No Panta API key'):panta.catalog()
    def test_demo_label_and_market_sanitize(self):
        r=demo_markets()
        self.assertEqual(r['source'],'demo')
        self.assertTrue(all(m['source']=='demo' and m['marketId'].startswith('demo-') for m in r['items']))
        self.assertIsNone(panta.price('NaN'))
        self.assertIsNone(panta.price('12'))
        self.assertEqual(panta.price('0.52'),0.52)
    def test_documented_market_catalog_and_price_detail_contract(self):
        from io import BytesIO
        from urllib.parse import urlsplit,parse_qs
        class FakeResponse:
            def __init__(self,obj):self.payload=json.dumps(obj).encode()
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self,limit):return self.payload[:limit]
        def fake(req,timeout=12):
            self.assertEqual(req.get_header('X-api-key'),'pk_test_dummy')
            if req.full_url.endswith('/markets/11111111111111111111111111111111/'):
                return FakeResponse({'marketId':'11111111111111111111111111111111','title':'Real test fixture','yesPrice':'0.58','noPrice':'0.42','phase':'primary'})
            q=parse_qs(urlsplit(req.full_url).query)
            self.assertEqual(q['category'],['sports'])
            self.assertEqual(q['limit'],['30'])
            return FakeResponse({'items':[{'marketId':'11111111111111111111111111111111','title':'Example catalog market','yesPrice':None,'noPrice':None,'phase':'primary'}],'nextCursor':None})
        with patch.dict(os.environ,{'PANTA_API_KEY':'pk_test_dummy'}):
            catalog=panta.catalog(category='sports',fetch=fake)
            self.assertIsNone(catalog['items'][0]['yesPrice'])
            detail=panta.detail('11111111111111111111111111111111',fetch=fake)
            self.assertEqual(detail['yesPrice'],.58)
            self.assertEqual(detail['noPrice'],.42)

    def test_invalid_market_id_rejected(self):
        with self.assertRaises(panta.PantaError):panta.detail('../../etc/passwd')

class TestHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=create_server('127.0.0.1',0)
        cls.port=cls.server.server_address[1]
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=5)
    def setUp(self):
        with s.database() as c:
            for t in ['public_reports','invites','sessions','notes','snapshots','market_links','forecasts','audit','decisions','memberships','workspaces','users']:c.execute('DELETE FROM '+t)
        self.cookies=http.cookiejar.CookieJar()
        self.client=build_opener(HTTPCookieProcessor(self.cookies))
        self.csrf=''
    def req(self,path,method='GET',data=None,client=None,csrf=None):
        body=json.dumps(data).encode() if data is not None else None
        headers={'Content-Type':'application/json'} if data is not None else {}
        if method!='GET':headers['X-CSRF-Token']=self.csrf if csrf is None else csrf
        request=Request('http://127.0.0.1:'+str(self.port)+path,body,headers,method=method)
        client=client or self.client
        try:
            response=client.open(request,timeout=6);status=response.status
        except HTTPError as e:response=e;status=e.code
        raw=response.read();content=response.headers.get('Content-Type','')
        if 'json' in content:return status,json.loads(raw)
        return status,raw
    def register(self,email='test@example.com',password='very-strong-password'):
        code,data=self.req('/api/auth/register','POST',{'email':email,'password':password,'display_name':'Tester'})
        self.assertEqual(code,200,data)
        self.csrf=data['csrf']
        return (self.req('/api/workspaces')[1]['workspaces'][0]['id'])
    def test_complete_own_workspace_workflow(self):
        ws=self.register()
        code,overview=self.req(f'/api/workspaces/{ws}')
        self.assertEqual(code,200);self.assertEqual(len(overview['decisions']),3)
        status,d=self.req(f'/api/workspaces/{ws}/decisions','POST',{'title':'Our question','question':'Will we launch?','description':'Settles on launch date.','impact_usd':1000})
        self.assertEqual(status,201);did=d['id']
        self.assertEqual(self.req(f'/api/decisions/{did}/forecasts','POST',{'probability':70,'reason':'We have capacity.'})[0],201)
        self.assertEqual(self.req(f'/api/decisions/{did}/notes','POST',{'body':'Some evidence','source_url':'https://example.org'})[0],201)
        mark=demo_markets()['items'][0]
        self.assertEqual(self.req(f'/api/decisions/{did}/links','POST',{'market_id':mark['marketId'],'source':'demo','match_explanation':'Synthetic test only'})[0],201)
        status,details=self.req(f'/api/decisions/{did}')
        self.assertEqual(status,200);self.assertEqual(details['team_probability'],.7)
        self.assertEqual(details['links'][0]['latest']['yes_price'],.42)
        self.assertEqual(details['links'][0]['source'],'demo')
        self.assertEqual(self.req(f'/api/links/{details["links"][0]["id"]}/refresh','POST',{})[0],400)
        a=self.req(f'/api/workspaces/{ws}/alerts?threshold=.1')[1]['alerts']
        self.assertTrue(any(x['kind']=='divergence' for x in a))
        self.assertEqual(self.req(f'/api/decisions/{did}/resolve','POST',{'outcome':True})[0],200)
        self.assertEqual(self.req(f'/api/decisions/{did}/forecasts','POST',{'probability':40})[0],409)
        self.assertAlmostEqual(self.req(f'/api/workspaces/{ws}')[1]['metrics']['brier'],.09)
        self.assertEqual(self.req(f'/api/workspaces/{ws}/export')[0],200)
        self.assertEqual(self.req(f'/api/workspaces/{ws}/csv')[0],200)
    def test_created_decision_visible_with_fresh_session_and_open_status(self):
        # Critical regression: creating a decision and auditing it must be
        # followed by an authoritative workspace listing, including after GET /auth/me.
        with patch.dict(os.environ,{'OUTCOMEOS_SEED_EXAMPLES':'0'}):
            ws=self.register('fresh@example.com')
        code,created=self.req(f'/api/workspaces/{ws}/decisions','POST',{
            'title':'E2E QA — BTC year-end 2026',
            'question':'Will a verifiable BTC outcome occur by December 31?',
            'description':'QA fixture; no real funds or market prices.',
            'deadline':'2026-12-31',
            'category':'QA'})
        self.assertEqual(code,201,created)
        self.assertEqual(created['workspace_id'],ws)
        self.assertEqual(created['status'],'open')
        code,workspace=self.req(f'/api/workspaces/{ws}')
        self.assertEqual(code,200)
        self.assertEqual(workspace['metrics']['open'],1)
        self.assertEqual(len(workspace['decisions']),1)
        self.assertEqual(workspace['decisions'][0]['id'],created['id'])
        self.assertEqual(workspace['decisions'][0]['status'],'open')
        diagnostic=self.req(f'/api/workspaces/{ws}/diagnostics')[1]
        self.assertEqual(diagnostic['workspace_id'],ws)
        self.assertEqual(diagnostic['open_decisions'],1)
        self.assertEqual(diagnostic['audit_create_events'],1)
        self.assertEqual(self.req('/api/auth/me')[1]['user']['email'],'fresh@example.com')
        self.assertEqual(self.req(f'/api/workspaces/{ws}')[1]['decisions'][0]['id'],created['id'])
        code,activity=self.req(f'/api/workspaces/{ws}/activity')
        self.assertEqual(code,200)
        self.assertTrue(any(a['event']=='decision_created' for a in activity['activity']))

    def test_missing_panta_title_or_quotes_are_not_fabricated(self):
        id='11111111111111111111111111111111'
        market=panta.clean_market({'marketId':id,'title':'  ', 'yesPrice':None,'noPrice':None, 'phase':'secondary'})
        self.assertEqual(market['title'], 'Untitled Panta market (11111111…)')
        self.assertFalse(market['titleAvailable'])
        self.assertFalse(market['quoteAvailable'])
        self.assertIsNone(market['yesPrice'])
        self.assertIsNone(market['noPrice'])

    def test_mocked_live_panta_link_and_quote_refresh(self):
        ws=self.register('live@example.com')
        did=self.req(f'/api/workspaces/{ws}/decisions','POST',{'title':'Launch metric','question':'Will goal be hit by Dec 1?','impact_usd':2000})[1]['id']
        market='11111111111111111111111111111111'
        first={'marketId':market,'title':'Public test fixture','phase':'primary','yesPrice':.40,'noPrice':.60}
        second={**first,'yesPrice':.77,'noPrice':.23}
        with patch('app.http_api.panta.detail',side_effect=[first,second]):
            st,link=self.req(f'/api/decisions/{did}/links','POST',{'market_id':market,'source':'live','match_explanation':'Same event / settlement date'})
            self.assertEqual(st,201)
            st,quote=self.req('/api/links/'+str(link['id'])+'/refresh','POST',{})
            self.assertEqual(st,200)
            self.assertEqual(quote['market']['yesPrice'],.77)
        record=self.req(f'/api/decisions/{did}')[1]['links'][0]
        self.assertEqual(record['source'],'live')
        self.assertEqual(len(record['history']),2)
        self.assertEqual(record['latest']['yes_price'],.77)
        alerts=self.req(f'/api/workspaces/{ws}/alerts?threshold=.1')[1]['alerts']
        self.assertTrue(any(a['kind']=='price_shift' for a in alerts))

    def test_anonymous_report_owner_only_and_revocable(self):
        ws=self.register('share-owner@example.com')
        did=self.req(f'/api/workspaces/{ws}/decisions','POST',{
            'title':'Product launch decision','question':'Will it ship by Friday?',
            'description':'Publicly agreed criteria'})[1]['id']
        self.req(f'/api/decisions/{did}/forecasts','POST',{'probability':63,'reason':'Private individual reason'})
        self.req(f'/api/decisions/{did}/notes','POST',{'body':'Top secret memo','source_url':'https://internal.example'})
        original=self.req(f'/api/decisions/{did}/report','POST',{})
        self.assertEqual(original[0],201)
        token=original[1]['token']
        
        with s.database() as db:
            self.assertEqual(db.execute('SELECT token_hash FROM public_reports').fetchone()[0],s.digest(token))
        anonymous=build_opener()
        code,report=self.req('/api/public/'+token,client=anonymous)
        self.assertEqual(code,200)
        self.assertEqual(report['team_probability'],.63)
        self.assertEqual(report['title'],'Product launch decision')
        raw=json.dumps(report)
        for secret in ('share-owner@example.com','Top secret memo','Private individual reason','csrf','password_hash','members'):
            self.assertNotIn(secret,raw)
        self.assertEqual(self.req('/share?abc=whatever',client=anonymous)[0],200)
        replacement=self.req(f'/api/decisions/{did}/report','POST',{})
        self.assertEqual(replacement[0],201)
        self.assertEqual(self.req('/api/public/'+token,client=anonymous)[0],404)
        active=replacement[1]['token']
        self.assertEqual(self.req('/api/public/'+active,client=anonymous)[0],200)
        self.assertEqual(self.req(f'/api/decisions/{did}/report','DELETE')[0],200)
        self.assertEqual(self.req('/api/public/'+active,client=anonymous)[0],404)

    def test_share_permission_and_expiration(self):
        ws=self.register('owner2@example.com')
        did=self.req(f'/api/workspaces/{ws}/decisions','POST',{'title':'Test','question':'Will it rain?'})[1]['id']
        owner=self.client
        owner_csrf=self.csrf
        self.cookies=http.cookiejar.CookieJar();self.client=build_opener(HTTPCookieProcessor(self.cookies));self.csrf=''
        self.register('member2@example.com')
        self.assertEqual(self.req(f'/api/decisions/{did}/report','POST',{})[0],403)
        with s.database() as c:
            c.execute('INSERT INTO memberships VALUES(?,?,?)',(ws,c.execute('SELECT id FROM users WHERE email=?',('member2@example.com',)).fetchone()[0],'member'))
        self.assertEqual(self.req(f'/api/decisions/{did}/report','POST',{})[0],403)
        self.assertEqual(self.req(f'/api/decisions/{did}/report','GET')[0],403)
        code,data=self.req(f'/api/decisions/{did}/report','POST',{},client=owner,csrf=owner_csrf)
        self.assertEqual(code,201)
        token=data['token']
        with s.database() as c:c.execute('UPDATE public_reports SET expires_at=0 WHERE token_hash=?',(s.digest(token),))
        self.assertEqual(self.req('/api/public/'+token,client=build_opener())[0],404)

    def test_auth_and_csrf(self):
        ws=self.register()
        self.assertEqual(self.req('/api/workspaces','POST',{'name':'Attack'},csrf='wrong')[0],403)
        self.assertEqual(self.req('/api/decisions/9999')[0],404)
        self.assertEqual(self.req('/api/auth/logout','POST',{})[0],200)
        self.assertEqual(self.req('/api/workspaces')[0],401)
    def test_cross_account_private_and_invitation(self):
        ws=self.register('alice@example.com')
        alice_client=self.client;alice_csrf=self.csrf
        self.cookies=http.cookiejar.CookieJar();self.client=build_opener(HTTPCookieProcessor(self.cookies));self.csrf=''
        self.register('bob@example.com')
        self.assertEqual(self.req(f'/api/workspaces/{ws}')[0],403)
        self.assertEqual(self.req('/api/decisions/1')[0],403)
        # Owner creates a one-time 24-hour invitation.
        status,inv=self.req(f'/api/workspaces/{ws}/invites','POST',{},client=alice_client,csrf=alice_csrf)
        self.assertEqual(status,201)
        self.assertEqual(self.req('/api/invites/accept','POST',{'token':inv['token']})[0],200)
        self.assertEqual(self.req(f'/api/workspaces/{ws}')[0],200)
        self.assertEqual(self.req(f'/api/workspaces/{ws}/invites','POST',{})[0],403)
    def test_external_error_does_not_spoof_live(self):
        self.register()
        with patch.dict(os.environ,{'PANTA_API_KEY':''}):
            code,data=self.req('/api/markets')
            self.assertEqual(code,503);self.assertEqual(data['source'],'unavailable')
    def test_health_static_and_invalid_input(self):
        self.register()
        self.assertEqual(self.req('/api/health')[0],200)
        status,html=self.req('/');self.assertEqual(status,200);self.assertIn(b'OutcomeOS',html)
        ws=self.req('/api/workspaces')[1]['workspaces'][0]['id']
        self.assertEqual(self.req(f'/api/workspaces/{ws}/decisions','POST',{'title':'bad','question':'test','impact_usd':-1})[0],400)
        self.assertEqual(self.req('/../../secret')[0],404)

if __name__=='__main__':unittest.main()
