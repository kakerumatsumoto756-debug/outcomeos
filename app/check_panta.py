"""Manual diagnostics: python -m app.check_panta

No API keys or private responses are printed. Only the official read-only
list/categories endpoints are queried.
"""
from __future__ import annotations
import json
from . import panta


def main():
    if not panta.enabled():
        print(json.dumps({'connection': 'not_configured', 'hint': 'Set PANTA_API_KEY in your environment; do not share it.'}))
        return 2
    try:
        markets = panta.catalog(limit=1)
        categories = panta.categories()
        print(json.dumps({'connection': 'verified', 'catalog_items_on_first_page': len(markets['items']),
            'categories': categories['categories'], 'scope': 'read_only'}, ensure_ascii=False))
        return 0
    except panta.PantaError as exc:
        print(json.dumps({'connection': 'failed', 'error_code': exc.code, 'message': str(exc)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
