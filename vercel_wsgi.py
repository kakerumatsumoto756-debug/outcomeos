"""WSGI bridge exposing the existing OutcomeOS request handler to serverless hosts.

No network listener is started in the Vercel runtime. All writes must go to Neon.
"""
from __future__ import annotations
import io
import os
import threading
import traceback
from email.message import Message
from urllib.parse import quote

from app.http_api import Handler
from app import storage

_initialized = False
_init_lock = threading.Lock()


def _ensure_database():
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if not _initialized:
            if os.getenv('VERCEL') == '1' and not os.getenv('DATABASE_URL'):
                raise RuntimeError('DATABASE_URL is required on Vercel')
            storage.init_db()
            _initialized = True


class _WSGIHandler(Handler):
    """Adapt BaseHTTPRequestHandler's documented methods to an in-memory response."""
    def __init__(self, environ):
        self.command = environ['REQUEST_METHOD']
        self.path = environ.get('PATH_INFO', '/')
        query = environ.get('QUERY_STRING')
        if query:
            self.path += '?' + query
        self.client_address = (environ.get('REMOTE_ADDR', '0.0.0.0'), 0)
        message = Message()
        for key, value in environ.items():
            if key.startswith('HTTP_'):
                header = key[5:].replace('_','-')
                message[header] = str(value)
        for key in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
            if key in environ:
                message[key.replace('_','-')] = str(environ[key])
        self.headers = message
        self.rfile = environ['wsgi.input']
        self.wfile = io.BytesIO()
        self._status = 500
        self._response_headers = []

    def send_response(self, code, message=None):
        self._status = code

    def send_header(self, keyword, value):
        self._response_headers.append((keyword, value))

    def end_headers(self):
        pass


def application(environ, start_response):
    # Never allow a Vercel instance to silently fall back to ephemeral SQLite.
    if os.getenv('VERCEL') == '1':
        os.environ['OUTCOMEOS_REQUIRE_POSTGRES'] = '1'
        os.environ['OUTCOMEOS_COOKIE_SECURE'] = '1'
        os.environ['OUTCOMEOS_SEED_EXAMPLES'] = '0'
    try:
        _ensure_database()
    except Exception:
        traceback.print_exc()
        payload = b'{"error":"Database connection unavailable"}'
        start_response('503 Service Unavailable', [('Content-Type','application/json'), ('Cache-Control','no-store'), ('Content-Length',str(len(payload)))])
        return [payload]
    handler = _WSGIHandler(environ)
    if handler.command not in ('GET', 'POST', 'PATCH', 'DELETE'):
        payload = b'{"error":"Method not allowed"}'
        start_response('405 Method Not Allowed',[('Content-Type','application/json'),('Allow','GET, POST, PATCH, DELETE'),('Content-Length',str(len(payload)))])
        return [payload]
    handler.handle_req(handler.command)
    try:
        import http
        reason = http.HTTPStatus(handler._status).phrase
    except (ValueError, KeyError):
        reason = 'Unknown'
    start_response(f'{handler._status} {reason}', handler._response_headers)
    return [handler.wfile.getvalue()]
