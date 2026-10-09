"""Opt-in, read-only polling of linked Panta markets.

Run python -m app.sync --once or --loop --interval 900.
No API keys are printed; failed markets do not abort the whole batch.
"""
from __future__ import annotations

import argparse
import time
from . import panta, storage as s


def sync_once(max_links=100, pause=1.0):
    if not panta.enabled():
        print('Panta sync skipped: PANTA_API_KEY not configured', flush=True)
        return {'updated': 0, 'unchanged': 0, 'unpriced': 0, 'failed': 0, 'skipped': True}
    s.init_db()
    start = s.utc()
    with s.database() as conn:
        links = [dict(x) for x in conn.execute('''
            SELECT l.id,l.market_id FROM market_links l
            JOIN decisions d ON l.decision_id=d.id
            WHERE l.source='live' AND d.status='open'
            ORDER BY l.id LIMIT ?''', (max(1, min(int(max_links), 1000)),)).fetchall()]
    counters = {'updated': 0, 'unchanged': 0, 'unpriced': 0, 'failed': 0}
    for index, link in enumerate(links):
        try:
            market = panta.fresh_market(link['market_id'])  # validates returned ID
            with s.database() as conn:
                found = conn.execute('''SELECT 1 FROM market_links l JOIN decisions d ON d.id=l.decision_id
                    WHERE l.id=? AND l.market_id=? AND l.source='live' AND d.status='open' ''',
                    (link['id'], link['market_id'])).fetchone()
                if found:
                    result = s.record_live_snapshot(conn, link['id'], market)
                    counters[result] += 1
                else:
                    counters['unchanged'] += 1
        except (panta.PantaError, ValueError) as exc:
            counters['failed'] += 1
            print(f'Panta market link #{link["id"]} could not be synced: {exc}', flush=True)
            if isinstance(exc, panta.PantaError) and exc.code == 'rate_limited':
                print('Rate limited. Remaining links deferred to next scheduled run.', flush=True)
                counters['failed'] += len(links) - index - 1
                break
        if pause and index < len(links) - 1:
            time.sleep(max(pause, 0))
    with s.database() as conn:
        conn.execute('''INSERT INTO sync_runs(started_at,finished_at,updated,unchanged,unpriced,failed,detail)
            VALUES(?,?,?,?,?,?,?)''', (start, s.utc(), *(counters[x] for x in ('updated','unchanged','unpriced','failed')),
            'Read-only Panta polling'))
    result = {**counters, 'skipped': False}
    print('Panta sync complete: ' + ', '.join(f'{k}={v}' for k, v in counters.items()), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description='Read-only Panta quote history sync')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--once', action='store_true')
    group.add_argument('--loop', action='store_true')
    parser.add_argument('--interval', type=int, default=900, help='Loop interval seconds (minimum 300)')
    args = parser.parse_args()
    if args.once:
        return sync_once()
    if args.interval < 300:
        parser.error('Loop interval must be at least 300 seconds')
    while True:
        sync_once()
        time.sleep(args.interval)


if __name__ == '__main__':
    main()
