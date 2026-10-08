"""Persistent decision records: SQLite local, PostgreSQL on public hosting."""
from __future__ import annotations
import contextlib, datetime as dt, hashlib, hmac, json, math, os, secrets, sqlite3, time
from pathlib import Path

DB_PATH = os.environ.get('OUTCOMEOS_DB', str(Path(__file__).resolve().parents[1] / 'data' / 'outcomeos.sqlite3'))

def utc(): return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
def timestamp(): return int(time.time())

def connect():
    remote = os.environ.get('DATABASE_URL', '').strip()
    if remote:
        from . import postgres
        return postgres.connect(remote)
    if os.environ.get('OUTCOMEOS_REQUIRE_POSTGRES') == '1':
        raise RuntimeError('DATABASE_URL is required: refusing ephemeral SQLite on public hosting')
    p = Path(DB_PATH); p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p), timeout=10, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA busy_timeout=10000')
    conn.execute('PRAGMA journal_mode=WAL')
    return conn

@contextlib.contextmanager
def database():
    c=connect()
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback(); raise
    finally: c.close()

DDL = '''
CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY,email TEXT UNIQUE NOT NULL,display_name TEXT NOT NULL,password_hash TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE, csrf TEXT NOT NULL, expires_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS workspaces (id INTEGER PRIMARY KEY,name TEXT NOT NULL,owner_id INTEGER NOT NULL REFERENCES users(id),created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS memberships (workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,role TEXT NOT NULL CHECK(role IN ('owner','member')),PRIMARY KEY(workspace_id,user_id));
CREATE TABLE IF NOT EXISTS invites (token_hash TEXT PRIMARY KEY,workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,created_by INTEGER NOT NULL REFERENCES users(id),expires_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS decisions (id INTEGER PRIMARY KEY,workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,title TEXT NOT NULL,question TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',category TEXT NOT NULL DEFAULT 'Strategy',deadline TEXT,status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','resolved','archived')),outcome INTEGER CHECK(outcome IN (0,1)),impact_usd REAL NOT NULL DEFAULT 0 CHECK(impact_usd >= 0),created_by INTEGER NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_decisions_ws ON decisions(workspace_id,status);
CREATE TABLE IF NOT EXISTS forecasts (id INTEGER PRIMARY KEY,decision_id INTEGER NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,user_id INTEGER NOT NULL REFERENCES users(id),probability REAL NOT NULL CHECK(probability>=0 AND probability<=1),reason TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_forecasts_dec ON forecasts(decision_id,created_at);
CREATE TABLE IF NOT EXISTS notes (id INTEGER PRIMARY KEY,decision_id INTEGER NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,user_id INTEGER NOT NULL REFERENCES users(id),body TEXT NOT NULL,source_url TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS market_links (id INTEGER PRIMARY KEY,decision_id INTEGER NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,market_id TEXT NOT NULL,market_title TEXT NOT NULL,source TEXT NOT NULL CHECK(source IN ('live','demo')),match_explanation TEXT NOT NULL,created_at TEXT NOT NULL,UNIQUE(decision_id,market_id));
CREATE TABLE IF NOT EXISTS snapshots (id INTEGER PRIMARY KEY,link_id INTEGER NOT NULL REFERENCES market_links(id) ON DELETE CASCADE,yes_price REAL,no_price REAL,phase TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,source TEXT NOT NULL CHECK(source IN ('live','demo')));
CREATE INDEX IF NOT EXISTS ix_snap_link ON snapshots(link_id,id);
CREATE TABLE IF NOT EXISTS sync_runs (id INTEGER PRIMARY KEY,started_at TEXT NOT NULL,finished_at TEXT NOT NULL,updated INTEGER NOT NULL,unchanged INTEGER NOT NULL,unpriced INTEGER NOT NULL,failed INTEGER NOT NULL,detail TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY,workspace_id INTEGER NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,user_id INTEGER NOT NULL REFERENCES users(id),event TEXT NOT NULL,detail TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS public_reports (token_hash TEXT PRIMARY KEY,decision_id INTEGER NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,created_by INTEGER NOT NULL REFERENCES users(id),created_at TEXT NOT NULL,expires_at INTEGER NOT NULL,revoked_at TEXT);
CREATE INDEX IF NOT EXISTS ix_public_reports_decision ON public_reports(decision_id,expires_at);
'''

def init_db():
    with database() as c: c.executescript(DDL)

def rowdict(r): return dict(r) if r is not None else None

def pw_hash(password):
    salt=secrets.token_bytes(16)
    hashed=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,350_000)
    return 'pbkdf2_sha256$350000$'+salt.hex()+'$'+hashed.hex()

def pw_verify(password,encoded):
    try:
        algo,n,salt,saved=encoded.split('$')
        if algo!='pbkdf2_sha256': return False
        given=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),int(n))
        return hmac.compare_digest(given, bytes.fromhex(saved))
    except (ValueError,TypeError): return False

def digest(token): return hashlib.sha256(token.encode()).hexdigest()

def create_session(c,user_id):
    token=secrets.token_urlsafe(36); csrf=secrets.token_urlsafe(36)
    c.execute('INSERT INTO sessions VALUES(?,?,?,?)',(digest(token),user_id,csrf,timestamp()+7*86400))
    return token,csrf

def auth_session(c,token):
    if not token:return None
    row=c.execute('SELECT u.id,u.email,u.display_name,s.csrf,s.expires_at FROM sessions s JOIN users u ON s.user_id=u.id WHERE token_hash=?',(digest(token),)).fetchone()
    if not row or row['expires_at']<=timestamp(): return None
    return rowdict(row)

def require_member(c,ws,user):
    row=c.execute('SELECT role FROM memberships WHERE workspace_id=? AND user_id=?',(ws,user)).fetchone()
    if not row: raise PermissionError('Workspace access denied')
    return row['role']

def require_owner(c,ws,user):
    if require_member(c,ws,user)!='owner': raise PermissionError('Workspace owner permission required')

def get_decision(c,decision_id,user):
    d=rowdict(c.execute('SELECT d.*,u.display_name AS creator FROM decisions d JOIN users u ON d.created_by=u.id WHERE d.id=?',(decision_id,)).fetchone())
    if not d: raise LookupError('Decision not found')
    require_member(c,d['workspace_id'],user)
    return d

def audit(c,ws,user,event,detail):
    c.execute('INSERT INTO audit(workspace_id,user_id,event,detail,created_at) VALUES(?,?,?,?,?)',(ws,user,event,detail,utc()))

def create_workspace(c,user,name):
    now=utc()
    ws=c.execute('INSERT INTO workspaces(name,owner_id,created_at) VALUES(?,?,?) RETURNING id',(name,user,now)).fetchone()['id']
    c.execute('INSERT INTO memberships VALUES(?,?,?)',(ws,user,'owner'))
    audit(c,ws,user,'workspace_created',name)
    return ws

def create_decision(c,ws,user,title,question,description='',category='Strategy',deadline=None,impact_usd=0):
    require_member(c,ws,user)
    now=utc()
    did=c.execute('INSERT INTO decisions(workspace_id,title,question,description,category,deadline,impact_usd,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?) RETURNING id',
        (ws,title,question,description,category,deadline,impact_usd,user,now,now)).fetchone()['id']
    audit(c,ws,user,'decision_created',title)
    return did

def forecasts_for(c,did):
    return [dict(x) for x in c.execute('SELECT f.*,u.display_name AS author FROM forecasts f JOIN users u ON f.user_id=u.id WHERE decision_id=? ORDER BY f.id DESC',(did,)).fetchall()]

def notes_for(c,did):
    return [dict(x) for x in c.execute('SELECT n.*,u.display_name AS author FROM notes n JOIN users u ON n.user_id=u.id WHERE decision_id=? ORDER BY n.id DESC',(did,)).fetchall()]

def links_for(c,did):
    result=[]
    for l in c.execute('SELECT * FROM market_links WHERE decision_id=? ORDER BY id DESC',(did,)).fetchall():
        record=dict(l)
        record['latest']=rowdict(c.execute('SELECT * FROM snapshots WHERE link_id=? ORDER BY id DESC LIMIT 1',(l['id'],)).fetchone())
        record['history']=[dict(x) for x in c.execute('SELECT * FROM snapshots WHERE link_id=? ORDER BY id DESC LIMIT 40',(l['id'],)).fetchall()][::-1]
        result.append(record)
    return result

def record_live_snapshot(c, link_id, market, *, timestamp=None):
    """Store only validated real price observations, without duplicate points.

    Returns 'updated', 'unchanged', or 'unpriced'. The caller is responsible
    for validating the market ID against the requested link.
    """
    from . import panta
    yes = panta.price(market.get('yesPrice'))
    no = panta.price(market.get('noPrice'))
    if yes is None:
        return 'unpriced'
    phase = str(market.get('phase') or 'unknown')[:40]
    prior = c.execute('SELECT yes_price,no_price,phase FROM snapshots WHERE link_id=? ORDER BY id DESC LIMIT 1', (link_id,)).fetchone()
    if prior and round(float(prior['yes_price']), 6) == yes and (round(float(prior['no_price']), 6) if prior['no_price'] is not None else None) == no and prior['phase'] == phase:
        return 'unchanged'
    c.execute('INSERT INTO snapshots(link_id,yes_price,no_price,phase,created_at,source) VALUES(?,?,?,?,?,?)',
              (link_id,yes,no,phase,timestamp or utc(),'live'))
    return 'updated'


def last_sync(c):
    result = c.execute('SELECT started_at,finished_at,updated,unchanged,unpriced,failed,detail FROM sync_runs ORDER BY id DESC LIMIT 1').fetchone()
    return rowdict(result)


def latest_team_forecast(c,did):
    # Avoid overweighting prolific users; latest forecast per user only.
    rows=c.execute('SELECT probability FROM forecasts f WHERE decision_id=? AND id=(SELECT MAX(id) FROM forecasts WHERE decision_id=f.decision_id AND user_id=f.user_id)',(did,)).fetchall()
    return round(sum(x['probability'] for x in rows)/len(rows),4) if rows else None

def score(c,ws):
    # Average Brier score of the latest individual forecast per user on resolved decisions.
    rows=c.execute('''SELECT f.probability,d.outcome FROM forecasts f JOIN decisions d ON d.id=f.decision_id
        WHERE d.workspace_id=? AND d.status='resolved' AND d.outcome IS NOT NULL AND f.id=(SELECT MAX(id) FROM forecasts WHERE decision_id=f.decision_id AND user_id=f.user_id)''',(ws,)).fetchall()
    return {'brier':round(sum((x['probability']-x['outcome'])**2 for x in rows)/len(rows),4) if rows else None,'evaluated_forecasts':len(rows)}

def overview(c,ws,user):
    require_member(c,ws,user)
    dec=[dict(x) for x in c.execute('SELECT d.*,u.display_name AS creator FROM decisions d JOIN users u ON d.created_by=u.id WHERE workspace_id=? ORDER BY d.id DESC',(ws,)).fetchall()]
    for d in dec:
        d['team_probability']=latest_team_forecast(c,d['id'])
        d['link_count']=c.execute('SELECT COUNT(*) FROM market_links WHERE decision_id=?',(d['id'],)).fetchone()[0]
        d['forecast_count']=c.execute('SELECT COUNT(*) FROM forecasts WHERE decision_id=?',(d['id'],)).fetchone()[0]
    members=[dict(x) for x in c.execute('SELECT u.id,u.display_name,u.email,m.role FROM memberships m JOIN users u ON m.user_id=u.id WHERE workspace_id=? ORDER BY m.role DESC,u.id',(ws,)).fetchall()]
    return {'workspace':rowdict(c.execute('SELECT * FROM workspaces WHERE id=?',(ws,)).fetchone()),'members':members,'decisions':dec,'metrics':{'total':len(dec),'open':sum(d['status']=='open' for d in dec),'resolved':sum(d['status']=='resolved' for d in dec),'markets':sum(d['link_count'] for d in dec),**score(c,ws)}}

def decision_details(c,did,user):
    d=get_decision(c,did,user)
    d['forecasts']=forecasts_for(c,did)
    d['notes']=notes_for(c,did)
    d['links']=links_for(c,did)
    d['team_probability']=latest_team_forecast(c,did)
    return d

def alert_summary(c,ws,user,threshold=0.15):
    require_member(c,ws,user)
    alerts=[]
    links=c.execute('''SELECT l.*,d.title AS decision_title,d.status FROM market_links l JOIN decisions d ON d.id=l.decision_id WHERE d.workspace_id=? AND d.status='open' ''',(ws,)).fetchall()
    for link in links:
        history=c.execute('SELECT yes_price,created_at FROM snapshots WHERE link_id=? AND yes_price IS NOT NULL ORDER BY id DESC LIMIT 2',(link['id'],)).fetchall()
        if not history: continue
        if len(history)==2 and abs(history[0]['yes_price']-history[1]['yes_price'])>=threshold:
            alerts.append({'kind':'price_shift','title':link['decision_title'],'market_title':link['market_title'],'decision_id':link['decision_id'],'difference':round(history[0]['yes_price']-history[1]['yes_price'],4),'source':link['source']})
        opinion=latest_team_forecast(c,link['decision_id'])
        if opinion is not None and abs(opinion-history[0]['yes_price'])>=threshold:
            alerts.append({'kind':'divergence','title':link['decision_title'],'market_title':link['market_title'],'decision_id':link['decision_id'],'difference':round(opinion-history[0]['yes_price'],4),'source':link['source']})
    return alerts

def seed_workspace(c,user,ws):
    """Explicitly synthetic onboarding examples, not Panta markets."""
    examples=[
        ('Expansion readiness','Will our APAC beta reach 500 activated users by November 15?','Define activation in your analytics, then collect evidence and record a forecast.','Growth',0.38,12500.0),
        ('Shipping velocity','Will version 2.0 be released before December 1?','A binary milestone that makes execution risk visible to the team.','Product',0.72,8000.0),
        ('Market opportunity','Will three enterprise customers sign paid annual contracts this quarter?','Review external signals and internal team estimates weekly.','Strategy',0.46,30000.0),
    ]
    for title,question,description,category,prob,impact in examples:
        did=create_decision(c,ws,user,title,question,description,category,None,impact)
        c.execute('INSERT INTO forecasts(decision_id,user_id,probability,reason,created_at) VALUES(?,?,?,?,?)',(did,user,prob,'Synthetic onboarding example; replace with a real estimate.',utc()))


def public_report(c, token):
    """A deliberately small, anonymous view. No member names, emails, evidence notes, IPs or credentials."""
    import re
    if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{35,100}', token):
        return None
    row = c.execute("""SELECT d.id,d.title,d.question,d.description,d.category,d.deadline,d.status,d.outcome,
        d.created_at,d.updated_at,r.created_at AS shared_at,r.expires_at
        FROM public_reports r JOIN decisions d ON d.id=r.decision_id
        WHERE r.token_hash=? AND r.revoked_at IS NULL AND r.expires_at>?""", (digest(token), timestamp())).fetchone()
    if not row: return None
    did = row['id']
    forecast = latest_team_forecast(c, did)
    markets = []
    for market in c.execute("""SELECT l.id,l.market_title,l.market_id,l.source,l.match_explanation
            FROM market_links l WHERE l.decision_id=? ORDER BY l.id DESC LIMIT 25""", (did,)):
        snapshots = c.execute("""SELECT yes_price,no_price,created_at,source,phase
                FROM snapshots WHERE link_id=? ORDER BY id DESC LIMIT 30""", (market['id'],)).fetchall()
        markets.append({
            'market_title':market['market_title'], 'market_id':market['market_id'],
            'source':market['source'], 'match_explanation':market['match_explanation'],
            'history':[dict(s) for s in reversed(snapshots)],
        })
    return {'title':row['title'],'question':row['question'],'description':row['description'],
        'category':row['category'],'deadline':row['deadline'],'status':row['status'],
        'outcome':row['outcome'],'team_probability':forecast,'markets':markets,
        'shared_at':row['shared_at'],'updated_at':row['updated_at'],
        'expires_at':row['expires_at'], 'disclaimer':'A market quote is a price, not a calibrated probability.'}
