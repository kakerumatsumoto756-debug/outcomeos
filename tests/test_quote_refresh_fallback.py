"""Regression: a catalog YES quote must remain usable when Panta detail omits it.

No production API calls. All sources simulate fresh Panta responses by exact market ID.
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

MID = '11111111111111111111111111111111'
OTHER = '22222222222222222222222222222222'


def listing(yes='0.50', no='0.50', market_id=MID):
    return panta.clean_market({
        'marketId': market_id, 'title': 'Saka 7+ points, GW6',
        'category': 'sports', 'phase': 'primary',
        'yesPrice': yes, 'noPrice': no,
    })


def detail_unpriced():
    return panta.clean_market({
        'marketId': MID, 'title': 'Saka 7+ points, GW6',
        'category': 'sports', 'phase': 'primary',
        'yesPrice': None, 'noPrice': None,
    })


class QuoteSourceTests(unittest.TestCase):
    def test_priced_detail_does_not_query_catalog(self):
        original = listing('0.62','0.38')
        with patch.object(panta, 'detail', return_value=original), \
             patch.object(panta, 'catalog', side_effect=AssertionError('no fallback')):
            result = panta.fresh_market(MID)
        self.assertEqual(result['yesPrice'], 0.62)
        self.assertEqual(result['quoteOrigin'], 'market_detail')

    def test_unpriced_detail_uses_fresh_matching_catalog_quote(self):
        with patch.object(panta, 'detail', return_value=detail_unpriced()), \
             patch.object(panta, 'catalog', return_value={
                 'items': [listing('0.50', '0.50')], 'nextCursor': None, 'source': 'live',
             }) as catalog:
            result = panta.fresh_market(MID)
        self.assertEqual(result['yesPrice'], 0.50)
        self.assertEqual(result['noPrice'], 0.50)
        self.assertEqual(result['quoteOrigin'], 'market_catalog')
        catalog.assert_called_once_with(cursor='', limit=50, fetch=None)

    def test_wrong_market_price_never_used(self):
        with patch.object(panta, 'detail', return_value=detail_unpriced()), \
             patch.object(panta, 'catalog', return_value={
                 'items': [listing('0.99', '0.01', OTHER)], 'nextCursor': None, 'source': 'live',
             }):
            result = panta.fresh_market(MID)
        self.assertIsNone(result['yesPrice'])
        self.assertEqual(result['quoteOrigin'], 'unavailable')

    def test_paginated_result_and_bounded_repeated_cursor(self):
        pages = [
            {'items': [listing('0.90', '0.10', OTHER)], 'nextCursor': 'next'},
            {'items': [listing('0.47', '0.53', MID)], 'nextCursor': None},
        ]
        with patch.object(panta, 'detail', return_value=detail_unpriced()), \
             patch.object(panta, 'catalog', side_effect=pages) as catalog:
            result = panta.fresh_market(MID, max_catalog_pages=2)
        self.assertEqual(result['yesPrice'], 0.47)
        self.assertEqual(catalog.call_count, 2)
        with patch.object(panta, 'detail', return_value=detail_unpriced()), \
             patch.object(panta, 'catalog', return_value={'items':[], 'nextCursor':'repeat'}) as catalog:
            panta.fresh_market(MID, max_catalog_pages=5)
        self.assertEqual(catalog.call_count, 2)

    def test_no_yes_in_catalog_not_inferred_from_no(self):
        with patch.object(panta, 'detail', return_value=detail_unpriced()), \
             patch.object(panta, 'catalog', return_value={
                 'items':[listing(None, '0.5')], 'nextCursor':None,
             }):
            result=panta.fresh_market(MID)
        self.assertIsNone(result['yesPrice'])
        self.assertEqual(result['quoteOrigin'], 'unavailable')

    def test_upstream_error_is_not_masked_as_no_quote(self):
        with patch.object(panta, 'detail', return_value=detail_unpriced()), \
             patch.object(panta, 'catalog', side_effect=panta.PantaError('rate limited','rate_limited')):
            with self.assertRaises(panta.PantaError) as exc:
                panta.fresh_market(MID)
        self.assertEqual(exc.exception.code, 'rate_limited')


class QuoteRefreshEndToEndTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.temp.name) / 'outcome.sqlite3')
        self.env = patch.dict(os.environ, {
            'OUTCOMEOS_DB':self.db, 'DATABASE_URL':'',
            'OUTCOMEOS_SEED_EXAMPLES':'0', 'OUTCOMEOS_REQUIRE_POSTGRES':'0',
        })
        self.env.start()
        self.previous_db = storage.DB_PATH
        storage.DB_PATH = self.db
        vercel_wsgi._initialized=False
        self.cookie=''; self.csrf=''

    def tearDown(self):
        vercel_wsgi._initialized=False
        storage.DB_PATH=self.previous_db
        self.env.stop(); self.temp.cleanup()

    def call(self, route, method='GET', body=None, anonymous=False):
        body_bytes = json.dumps(body).encode() if body is not None else b''
        environ={
            'REQUEST_METHOD':method,
            'PATH_INFO':route,
            'QUERY_STRING':'',
            'HTTP_HOST':'outcome.example',
            'HTTP_ORIGIN':'https://outcome.example',
            'wsgi.input':io.BytesIO(body_bytes),
            'REMOTE_ADDR':'127.0.0.1',
            'CONTENT_LENGTH':str(len(body_bytes)),
        }
        if body is not None: environ['CONTENT_TYPE']='application/json'
        if self.cookie and not anonymous: environ['HTTP_COOKIE']=self.cookie
        if self.csrf and not anonymous: environ['HTTP_X_CSRF_TOKEN']=self.csrf
        result=[]
        def start_response(status, headers):result.extend([status,dict(headers)])
        response=b''.join(vercel_wsgi.application(environ,start_response))
        try: data=json.loads(response)
        except Exception: data=response.decode()
        return int(result[0].split()[0]),result[1],data

    def test_refresh_recovers_live_catalog_quote_and_preserves_history(self):
        code, headers, data = self.call('/api/auth/register','POST',{
            'email':'refresh@example.test', 'display_name':'Tester', 'password':'secure-password-123',
        })
        self.assertEqual(code,200,data)
        self.cookie=headers['Set-Cookie'].split(';')[0]
        self.csrf=data['csrf']
        ws=self.call('/api/workspaces')[2]['workspaces'][0]['id']
        code,_,decision=self.call(f'/api/workspaces/{ws}/decisions','POST',{
            'title':'Saka price check', 'question':'Will Saka score 7+ points in GW6?',
        })
        self.assertEqual(code,201,decision)
        did=decision['id']
        odds={'yes':'0.50'}
        def fresh_page(*args,**kwargs):
            return {'items':[listing(odds['yes'],str(round(1-float(odds['yes']),6)))], 'nextCursor':None}
        with patch.object(panta,'detail',return_value=detail_unpriced()), \
             patch.object(panta,'catalog',side_effect=fresh_page):
            code,_,link=self.call(f'/api/decisions/{did}/links','POST',{
                'market_id':MID,'source':'live','match_explanation':'Same outcome and closing time',
            })
            self.assertEqual(code,201,link)
            lid=link['id']
            code,_,result=self.call(f'/api/links/{lid}/refresh','POST',{})
            self.assertEqual(code,200,result)
            self.assertEqual(result['snapshot_result'],'unchanged')
            self.assertEqual(result['market']['quoteOrigin'],'market_catalog')
            odds['yes']='0.55'
            code,_,result=self.call(f'/api/links/{lid}/refresh','POST',{})
            self.assertEqual(code,200,result)
            self.assertEqual(result['snapshot_result'],'updated')
        code,_,state=self.call(f'/api/decisions/{did}')
        self.assertEqual(code,200,state)
        self.assertEqual(len(state['links'][0]['history']),2)
        self.assertEqual(state['links'][0]['latest']['yes_price'],0.55)
        # Session survives another WSGI startup against the same database.
        vercel_wsgi._initialized=False
        self.assertEqual(self.call('/api/auth/me')[0],200)


if __name__=='__main__': unittest.main()
