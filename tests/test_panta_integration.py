"""Contract, HTTP diagnostic, and polling tests. No calls to Panta's live server."""
import json
import os
import threading
import unittest
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError

# Tests run in the same process as test_outcomeos, which configures a temporary DB.
# This module uses its own isolated DB if unittest module loading order changes.
import tempfile
from pathlib import Path
_test_db = tempfile.TemporaryDirectory(prefix='outcomeos-api-contract-')
from app import panta, storage as s, sync


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode('utf-8')
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, count): return self.payload[:count]


MID = '11111111111111111111111111111111'


class PantaContractTests(unittest.TestCase):
    def test_invalid_prices_never_stored(self):
        for value in (True, float('nan'), float('inf'), -0.01, 1.01, 'inf', 'nan', {}, []):
            self.assertIsNone(panta.price(value))
        self.assertEqual(panta.price('0.57'), 0.57)

    def test_market_id_mismatch_fails_closed(self):
        def fake(req, timeout=12):
            return FakeResponse({'marketId': '22222222222222222222222222222222', 'title': 'Wrong market'})
        with patch.dict(os.environ, {'PANTA_API_KEY': 'pk_test_mock'}):
            with self.assertRaisesRegex(panta.PantaError, 'does not match'):
                panta.detail(MID, fetch=fake)

    def test_catalog_rejects_missing_ids_and_unexpected_items(self):
        with patch.dict(os.environ, {'PANTA_API_KEY': 'pk_test_mock'}):
            with self.assertRaises(panta.PantaError):
                panta.catalog(fetch=lambda request, timeout=12: FakeResponse({'items': [{}]}))
            with self.assertRaises(panta.PantaError):
                panta.catalog(fetch=lambda request, timeout=12: FakeResponse({'items': 'not-a-list'}))

    def test_http_errors_are_actionable_without_exposing_credentials(self):
        for status, code in ((401, 'unauthorized'), (403, 'unauthorized'), (429, 'rate_limited'), (404, 'not_found')):
            def fake(request, timeout=12):
                raise HTTPError(request.full_url, status, 'remote', {}, BytesIO(b'private upstream body'))
            with patch.dict(os.environ, {'PANTA_API_KEY': 'pk_test_PRIVATE_SECRET'}):
                with self.assertRaises(panta.PantaError) as thrown:
                    panta.catalog(fetch=fake)
                self.assertEqual(thrown.exception.code, code)
                self.assertNotIn('PRIVATE_SECRET', str(thrown.exception))
                self.assertNotIn('private upstream body', str(thrown.exception))

    def test_snapshot_ignores_invalid_and_unchanged_quote(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(s, 'DB_PATH', str(Path(directory) / 'data.db')):
                s.init_db()
                with s.database() as c:
                    uid = c.execute('INSERT INTO users(email,display_name,password_hash,created_at) VALUES(?,?,?,?)', ('testing@outcome.local','Tester','hash',s.utc())).lastrowid
                    wid = s.create_workspace(c, uid, 'Contract tests')
                    did = s.create_decision(c, wid, uid, 'Decision', 'Will this happen?')
                    lid = c.execute('INSERT INTO market_links(decision_id,market_id,market_title,source,match_explanation,created_at) VALUES(?,?,?,?,?,?)', (did,MID,'Sample','live','Same settlement',s.utc())).lastrowid
                    a = {'yesPrice': .4, 'noPrice': .6, 'phase': 'primary'}
                    self.assertEqual(s.record_live_snapshot(c, lid, {'yesPrice': 'not available'}), 'unpriced')
                    self.assertEqual(s.record_live_snapshot(c, lid, a), 'updated')
                    self.assertEqual(s.record_live_snapshot(c, lid, a), 'unchanged')
                    self.assertEqual(s.record_live_snapshot(c, lid, {**a,'yesPrice':.41}), 'updated')
                    self.assertEqual(c.execute('SELECT COUNT(*) FROM snapshots').fetchone()[0], 2)

    def test_sync_deduplicates_and_tracks_status(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(s, 'DB_PATH', str(Path(directory) / 'data.db')):
                s.init_db()
                with s.database() as c:
                    uid = c.execute('INSERT INTO users(email,display_name,password_hash,created_at) VALUES(?,?,?,?)', ('testing@outcome.local','Tester','hash',s.utc())).lastrowid
                    wid = s.create_workspace(c, uid, 'Poll tests')
                    did = s.create_decision(c, wid, uid, 'Decision', 'Will this happen?')
                    c.execute('INSERT INTO market_links(decision_id,market_id,market_title,source,match_explanation,created_at) VALUES(?,?,?,?,?,?)', (did,MID,'Sample','live','Same settlement',s.utc()))
                market={'marketId':MID, 'yesPrice':0.5, 'noPrice':0.5, 'phase':'primary'}
                with patch.object(panta, 'enabled', return_value=True), patch.object(panta, 'detail', return_value=market):
                    self.assertEqual(sync.sync_once(pause=0)['updated'],1)
                    self.assertEqual(sync.sync_once(pause=0)['unchanged'],1)
                with s.database() as c:
                    self.assertEqual(c.execute('SELECT COUNT(*) FROM snapshots').fetchone()[0], 1)
                    self.assertEqual(s.last_sync(c)['unchanged'],1)


if __name__ == '__main__':
    unittest.main()


class LoopbackPantaTests(unittest.TestCase):
    """Exercise the actual HTTP integration against a local fake Panta server."""
    def test_real_http_catalog_details_and_credential_header(self):
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        requests = []
        class Upstream(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                requests.append((self.path, self.headers.get('X-Api-Key')))
                if self.headers.get('X-Api-Key') != 'pk_test_local_integration':
                    self.send_response(403); self.end_headers(); return
                if self.path.startswith('/api/v1/markets/?'):
                    result = {'items': [{'marketId': MID, 'title': 'Loopback market', 'phase': 'primary'}], 'nextCursor': None}
                elif self.path == f'/api/v1/markets/{MID}/':
                    result = {'marketId': MID, 'title': 'Loopback market', 'phase': 'primary', 'yesPrice': '0.73', 'noPrice': '0.27'}
                else:
                    self.send_response(404); self.end_headers(); return
                raw = json.dumps(result).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
        upstream = ThreadingHTTPServer(('127.0.0.1', 0), Upstream)
        thread = threading.Thread(target=upstream.serve_forever, daemon=True)
        thread.start()
        try:
            with patch.dict(os.environ, {'PANTA_API_KEY': 'pk_test_local_integration', 'PANTA_API_BASE': f'http://127.0.0.1:{upstream.server_address[1]}/api/v1'}):
                listing = panta.catalog('sports', limit=1)
                self.assertEqual(listing['source'], 'live')
                self.assertIsNone(listing['items'][0]['yesPrice'])
                item = panta.detail(MID)
                self.assertEqual(item['yesPrice'], 0.73)
                self.assertEqual(item['noPrice'], 0.27)
                self.assertEqual(len(requests), 2)
                self.assertTrue(all(req[1] == 'pk_test_local_integration' for req in requests))
        finally:
            upstream.shutdown(); upstream.server_close(); thread.join(timeout=5)

    def test_diagnostics_never_reveals_key_and_requires_auth(self):
        import http.cookiejar
        import app.http_api as api_module
        from urllib.request import Request, HTTPCookieProcessor, build_opener
        from app.http_api import create_server
        with tempfile.TemporaryDirectory() as directory, patch.object(s, 'DB_PATH', str(Path(directory) / 'data.db')):
            server = create_server('127.0.0.1', 0)
            runner = threading.Thread(target=server.serve_forever, daemon=True)
            runner.start()
            jar = http.cookiejar.CookieJar()
            client = build_opener(HTTPCookieProcessor(jar))
            def request(path, method='GET', payload=None, csrf=''):
                data = json.dumps(payload).encode() if payload is not None else None
                headers = {'Content-Type': 'application/json', 'X-CSRF-Token': csrf}
                req = Request(f'http://127.0.0.1:{server.server_address[1]}{path}', data=data, headers=headers, method=method)
                try:
                    resp = client.open(req, timeout=5)
                except HTTPError as error:
                    resp = error
                with resp:
                    return resp.status, json.loads(resp.read())
            try:
                with patch.dict(os.environ, {'PANTA_API_KEY': 'pk_test_SUPER_PRIVATE'}):
                    self.assertEqual(request('/api/panta/status')[0], 401)
                    status, login = request('/api/auth/register', 'POST', {'email': 'panta-status@test.com', 'display_name': 'Tester', 'password': 'strongsecurepassword'})
                    self.assertEqual(status, 200)
                    csrf = login['csrf']
                    code, info = request('/api/panta/status')
                    self.assertEqual(code, 200)
                    self.assertTrue(info['configured'])
                    self.assertFalse(info['checked_live'])
                    self.assertNotIn('SUPER_PRIVATE', json.dumps(info))
                    self.assertEqual(request('/api/panta/check', 'POST', {}, csrf='bad')[0], 403)
                    with patch.object(panta, 'catalog', return_value={'items': [{'marketId': MID}], 'source': 'live'}):
                        api_module._last_panta_check = 0.0
                        code, result = request('/api/panta/check', 'POST', {}, csrf=csrf)
                        self.assertEqual(code, 200)
                        self.assertEqual(result['connection'], 'verified')
                        self.assertEqual(result['catalog_items'], 1)
                        self.assertNotIn('SUPER_PRIVATE', json.dumps(result))
                        self.assertEqual(request('/api/panta/check', 'POST', {}, csrf=csrf)[0], 429)
            finally:
                server.shutdown(); server.server_close(); runner.join(timeout=5)


class CategoryAndVolumeTests(unittest.TestCase):
    def test_actual_documented_category_allowlist(self):
        documented = ['sports','crypto','politics','entertainment','finance','science','world','other']
        with patch.dict(os.environ, {'PANTA_API_KEY': 'pk_test_mock'}):
            result = panta.categories(fetch=lambda req,timeout=12: FakeResponse({'categories': documented}))
            self.assertEqual(result['categories'], documented)
            with self.assertRaises(panta.PantaError):
                panta.categories(fetch=lambda req,timeout=12: FakeResponse({'categories':['<script>']}))
    def test_decimal_volume_preserved_without_float_corruption(self):
        market = panta.clean_market({'marketId': MID, 'volumeUsdc': '1200.05', 'yesPrice': '0.52'})
        self.assertEqual(market['volumeUsdc'], '1200.05')
        self.assertEqual(market['yesPrice'], .52)
        self.assertIsNone(panta.volume('nan'))
