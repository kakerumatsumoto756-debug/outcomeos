"""Strict read-only Panta REST adapter.

The Panta key is configured server-side. This module deliberately does not
implement trading, wallet signing, market creation or token transfers.
"""
from __future__ import annotations

import json
import math
from decimal import Decimal, InvalidOperation
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

DEFAULT_BASE = 'https://live-api.panta.market/api/v1'
MAX_RESPONSE_BYTES = 2_000_000
MARKET_ID_PATTERN = re.compile(r'[1-9A-HJ-NP-Za-km-z]{25,60}\Z')


class PantaError(Exception):
    def __init__(self, message: str, code: str = 'upstream_error'):
        super().__init__(message)
        self.code = code


def enabled() -> bool:
    return bool(os.environ.get('PANTA_API_KEY', '').strip())


def _base_url() -> str:
    base = os.environ.get('PANTA_API_BASE', DEFAULT_BASE).rstrip('/')
    if not (base.startswith('https://') or base.startswith('http://localhost:') or base.startswith('http://127.0.0.1:')):
        raise PantaError('Panta base URL must use HTTPS (except localhost tests).', 'bad_configuration')
    if any(x in base for x in ('?', '#', '@')):
        raise PantaError('Panta base URL contains invalid characters.', 'bad_configuration')
    return base


def request_json(path: str, params: dict | None = None, fetch=None) -> dict:
    """Single read-only JSON request. Fail closed on schema/network/auth errors."""
    key = os.environ.get('PANTA_API_KEY', '').strip()
    if not key:
        raise PantaError('No Panta API key configured. Live data is unavailable.', 'not_configured')
    if not path.startswith('/') or path.startswith('//') or '..' in path:
        raise PantaError('Invalid API path.', 'bad_request')
    url = _base_url() + path + ('?' + urlencode(params) if params else '')
    req = Request(url, headers={
        'X-Api-Key': key, 'Accept': 'application/json',
        'User-Agent': 'OutcomeOS/1.1 (read-only decision intelligence)',
    }, method='GET')
    try:
        with (fetch or urlopen)(req, timeout=12) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise PantaError('Panta response exceeded the size limit.', 'invalid_response')
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise PantaError('Unexpected Panta response format.', 'invalid_response')
        return data
    except HTTPError as exc:
        status = exc.code
        if status in (401, 403):
            raise PantaError('Panta rejected the API key or permissions (HTTP %d).' % status, 'unauthorized') from exc
        if status == 429:
            raise PantaError('Panta rate limit reached (HTTP 429). Wait before retrying.', 'rate_limited') from exc
        if status == 404:
            raise PantaError('Market or endpoint not found on Panta (HTTP 404).', 'not_found') from exc
        raise PantaError('Panta API error (HTTP %d).' % status, 'upstream_error') from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise PantaError('Cannot reach Panta. Check your network or try again later.', 'network_error') from exc
    except (ValueError, UnicodeError) as exc:
        raise PantaError('Panta returned invalid JSON.', 'invalid_response') from exc


def valid_market_id(market_id: str) -> bool:
    return isinstance(market_id, str) and bool(MARKET_ID_PATTERN.fullmatch(market_id))


def price(value) -> float | None:
    """Quarantines non-numeric, non-finite, negative and out-of-range quotes."""
    if value is None or value == '' or isinstance(value, bool):
        return None
    try:
        value = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return round(value, 6) if math.isfinite(value) and 0 <= value <= 1 else None


def volume(value) -> str | None:
    """Panta returns volumeUsdc as a human-readable decimal string."""
    if value is None or isinstance(value, bool):
        return None
    try:
        numeric = Decimal(str(value))
        return format(numeric, 'f')[:80] if numeric.is_finite() and numeric >= 0 and len(str(value)) <= 80 else None
    except (InvalidOperation, ValueError, OverflowError):
        return None


def categories(fetch=None) -> dict:
    """Use upstream allowlist rather than guessing valid category filters."""
    result = request_json('/categories/', fetch=fetch)
    names = result.get('categories')
    if not isinstance(names, list) or len(names) > 150:
        raise PantaError('Panta categories response was invalid.', 'invalid_response')
    if not all(isinstance(x, str) and re.fullmatch(r'[a-z0-9_-]{1,40}', x) for x in names):
        raise PantaError('Panta returned invalid market category names.', 'invalid_response')
    return {'categories': list(dict.fromkeys(names)), 'source': 'live'}


def clean_market(item: dict) -> dict:
    """Keep only public fields needed in UI; never expose API metadata/secrets."""
    if not isinstance(item, dict) or not valid_market_id(item.get('marketId')):
        raise PantaError('Panta returned an invalid market identifier.', 'invalid_response')
    def limited(field: str, fallback: str, size: int) -> str:
        value = item.get(field)
        return str(value if value is not None else fallback)[:size]
    return {
        'marketId': item['marketId'],
        'title': limited('title', 'Untitled market', 300),
        'category': limited('category', 'Other', 80),
        'phase': limited('phase', 'unknown', 40),
        'status': limited('status', 'unknown', 40),
        'volumeUsdc': volume(item.get('volumeUsdc')),
        'yesPrice': price(item.get('yesPrice')),
        'noPrice': price(item.get('noPrice')),
        'description': limited('description', '', 1500),
        'source': 'live',
    }


def catalog(category: str = '', phase: str = '', cursor: str = '', limit: int = 30, fetch=None) -> dict:
    query = {'limit': min(max(int(limit), 1), 50)}
    if category:
        query['category'] = category
    if phase:
        query['phase'] = phase
    if cursor:
        query['cursor'] = cursor
    result = request_json('/markets/', query, fetch)
    items = result.get('items')
    if not isinstance(items, list):
        raise PantaError('Panta market catalog missing items array.', 'invalid_response')
    if len(items) > 1000:
        raise PantaError('Panta returned too many market items.', 'invalid_response')
    clean = [clean_market(item) for item in items]
    next_cursor = result.get('nextCursor')
    if next_cursor is not None and (not isinstance(next_cursor, str) or len(next_cursor) > 500):
        raise PantaError('Panta returned an invalid pagination cursor.', 'invalid_response')
    return {'items': clean, 'nextCursor': next_cursor, 'source': 'live'}


def detail(market_id: str, fetch=None) -> dict:
    if not valid_market_id(market_id):
        raise PantaError('Invalid Panta market identifier.', 'bad_request')
    item = request_json('/markets/' + quote(market_id, safe='') + '/', fetch=fetch)
    market = clean_market(item)
    if market['marketId'] != market_id:
        raise PantaError('Panta market ID does not match the requested ID.', 'invalid_response')
    return market
