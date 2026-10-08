"""HTTP routing layer. Designed for localhost; see README before internet deployment."""
from __future__ import annotations
import base64, csv, hmac, io, json, os, re, secrets, sqlite3, threading, time
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from . import storage as s,panta

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'web'
MAX_BODY=100_000
_login_attempts={}
_limiter_lock=threading.Lock()
_last_panta_check = 0.0
_check_lock = threading.Lock()

class RequestError(Exception):
    def __init__(self,status,message): super().__init__(message);self.status=status;self.message=message

def field(obj,name,maxlen=200,required=True):
    v=obj.get(name,'')
    if not isinstance(v,str):raise RequestError(400,f'{name} must be text')
    v=v.strip()
    if required and not v:raise RequestError(400,f'{name} is required')
    if len(v)>maxlen:raise RequestError(400,f'{name} is too long (limit {maxlen})')
    return v

def probability(v):
    if isinstance(v,bool):raise RequestError(400,'Probability must be numeric')
    try: num=float(v)
    except (ValueError,TypeError):raise RequestError(400,'Probability must be numeric')
    if not 0<=num<=100:raise RequestError(400,'Probability must be between 0 and 100')
    return num/100

def amount(v):
    if isinstance(v,bool):raise RequestError(400,'Invalid dollar impact')
    try:num=float(v)
    except (TypeError,ValueError):raise RequestError(400,'Invalid dollar impact')
    if not 0<=num<=1e12:raise RequestError(400,'Dollar impact out of range')
    return num

def integer(v):
    try:n=int(v)
    except (ValueError,TypeError):raise RequestError(400,'Invalid id')
    if n<=0:raise RequestError(400,'Invalid id')
    return n

def demo_markets():
    return {'source':'demo','nextCursor':None,'items':[
        {'marketId':'demo-growth-2026','title':'Will a software startup hit 500 active users?','category':'business','phase':'primary','status':'demo','volumeUsdc':None,'yesPrice':0.42,'noPrice':0.58,'source':'demo','description':'Fictional example. NOT listed on Panta.'},
        {'marketId':'demo-launch-2026','title':'Will a product ship before its deadline?','category':'technology','phase':'primary','status':'demo','volumeUsdc':None,'yesPrice':0.63,'noPrice':0.37,'source':'demo','description':'Fictional example. NOT listed on Panta.'},
        {'marketId':'demo-contract-2026','title':'Will three enterprise customers sign this quarter?','category':'business','phase':'primary','status':'demo','volumeUsdc':None,'yesPrice':0.51,'noPrice':0.49,'source':'demo','description':'Fictional example. NOT listed on Panta.'},
    ]}

class Handler(BaseHTTPRequestHandler):
    server_version='OutcomeOS/1.3'
    def log_message(self,format,*args):
        # Never log query tokens (invite/report), report-token URLs, headers or POST bodies.
        safe_path='/api/public/[redacted]' if self.path.startswith('/api/public/') else urlsplit(self.path).path
        print('[OutcomeOS]',self.client_address[0],self.command,safe_path,flush=True)
    def _headers(self,content_type='application/json; charset=utf-8',extra=None):
        self.send_header('Content-Type',content_type)
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.send_header('Cache-Control','no-store')
        if extra:
            for k,v in extra.items():self.send_header(k,v)
    def json(self,status,obj,extra=None):
        body=json.dumps(obj,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()
        self.send_response(status)
        self._headers(extra=extra)
        self.send_header('Content-Length',str(len(body)))
        self.end_headers();self.wfile.write(body)
    def blob(self,status,data,mime,extra=None):
        self.send_response(status);self._headers(mime,extra)
        self.send_header('Content-Length',str(len(data)))
        self.end_headers();self.wfile.write(data)
    def parse(self):
        length=self.headers.get('Content-Length','')
        if not length.isdigit():raise RequestError(411,'Content-Length required')
        n=int(length)
        if n>MAX_BODY:raise RequestError(413,'Request too large')
        if not self.headers.get('Content-Type','').lower().startswith('application/json'):raise RequestError(415,'JSON content type required')
        try: obj=json.loads(self.rfile.read(n))
        except (ValueError,UnicodeError): raise RequestError(400,'Malformed JSON')
        if not isinstance(obj,dict):raise RequestError(400,'Expected a JSON object')
        return obj
    def session_token(self):
        cookie=SimpleCookie()
        try:cookie.load(self.headers.get('Cookie',''))
        except Exception:return ''
        return cookie['outcome_session'].value if 'outcome_session' in cookie else ''
    def session(self,c):
        sess=s.auth_session(c,self.session_token())
        if not sess:raise RequestError(401,'Please sign in')
        return sess
    def csrf(self,sess):
        provided=self.headers.get('X-CSRF-Token','')
        if not provided or not hmac.compare_digest(provided,sess['csrf']):raise RequestError(403,'CSRF check failed')
        origin=self.headers.get('Origin')
        if origin:
            origin_host=urlsplit(origin).netloc
            if origin_host!=self.headers.get('Host',''):raise RequestError(403,'Origin check failed')
    def cookie(self,value,maxage):
        secure='; Secure' if os.environ.get('OUTCOMEOS_COOKIE_SECURE')=='1' else ''
        return f'outcome_session={value}; HttpOnly; SameSite=Strict; Path=/; Max-Age={maxage}{secure}'
    def handle_req(self,method):
        try:
            url=urlsplit(self.path);path=url.path;qs={k:v[-1] for k,v in parse_qs(url.query).items()}
            if path.startswith('/api/'):
                with s.database() as c:
                    result=self.api(c,method,path,qs)
                if result is not None:
                    if len(result)==4:
                        status,body,mime,headers=result
                        self.blob(status,body,mime,headers)
                    else:
                        status,body,headers=result
                        self.json(status,body,headers)
            elif method=='GET':self.static(path)
            else:raise RequestError(404,'Not found')
        except RequestError as e:self.json(e.status,{'error':e.message})
        except PermissionError as e:self.json(403,{'error':str(e)})
        except LookupError as e:self.json(404,{'error':str(e)})
        except sqlite3.IntegrityError:self.json(409,{'error':'A duplicate or invalid record was submitted'})
        except panta.PantaError as e:self.json(503,{'error':str(e),'source':'unavailable'})
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception as e:
            # Psycopg constraint exceptions are intentionally translated without
            # exposing private SQL statements or underlying database details.
            if e.__class__.__name__ in ('UniqueViolation', 'ForeignKeyViolation', 'CheckViolation'):
                self.json(409,{'error':'A duplicate or invalid record was submitted'})
                return
            import traceback
            traceback.print_exc()
            try:self.json(500,{'error':'Unexpected server error. Check server logs.'})
            except OSError:pass
    def do_GET(self):self.handle_req('GET')
    def do_POST(self):self.handle_req('POST')
    def do_PATCH(self):self.handle_req('PATCH')
    def do_DELETE(self):self.handle_req('DELETE')
    def static(self,path):
        allowed={'/':'landing.html','/app':'index.html','/landing.css':'landing.css','/index.html':'index.html','/app.js':'app.js','/style.css':'style.css','/favicon.svg':'favicon.svg','/share':'share.html','/share.js':'share.js','/share.css':'share.css'}
        filename=allowed.get(path)
        if not filename:raise RequestError(404,'Not found')
        mime='text/html; charset=utf-8' if filename.endswith('.html') else ('text/javascript; charset=utf-8' if filename.endswith('.js') else ('text/css; charset=utf-8' if filename.endswith('.css') else 'image/svg+xml'))
        self.blob(200,(WEB/filename).read_bytes(),mime)
    def api(self,c,method,path,qs):
        if method=='GET' and path=='/api/health':return 200,{'status':'ok','version':'1.3.0','panta_configured':panta.enabled()},None
        # Public showcase view: only an opt-in, expiring aggregate report.
        public_match = re.fullmatch(r'/api/public/([A-Za-z0-9_-]{35,100})', path)
        if method=='GET' and public_match:
            report=s.public_report(c,public_match.group(1))
            if not report:raise RequestError(404,'Report not found or expired')
            return 200,report,None
        if method=='POST' and path in ('/api/auth/register','/api/auth/login'):
            # Per-IP best-effort limiter, not a substitute for reverse-proxy rate limiting.
            ip=self.client_address[0]
            with _limiter_lock:
                now=time.monotonic();attempts=[x for x in _login_attempts.get(ip,[]) if now-x<300]
                if len(attempts)>=20:raise RequestError(429,'Too many attempts; try again later')
                attempts.append(now);_login_attempts[ip]=attempts
            data=self.parse();email=field(data,'email',254).lower();pw=field(data,'password',200)
            if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email):raise RequestError(400,'Valid email required')
            if path.endswith('/register'):
                display=field(data,'display_name',60)
                if len(pw)<10:raise RequestError(400,'Password must have at least 10 characters')
                if c.execute('SELECT 1 FROM users WHERE email=?',(email,)).fetchone():raise RequestError(409,'Email already registered')
                uid=c.execute('INSERT INTO users(email,display_name,password_hash,created_at) VALUES(?,?,?,?) RETURNING id',(email,display,s.pw_hash(pw),s.utc())).fetchone()['id']
                ws=s.create_workspace(c,uid,display+"'s workspace")
                if os.environ.get('OUTCOMEOS_SEED_EXAMPLES','1') == '1':
                    s.seed_workspace(c,uid,ws)
            else:
                u=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
                if not u or not s.pw_verify(pw,u['password_hash']):raise RequestError(401,'Incorrect email or password')
                uid=u['id']
            token,csrf=s.create_session(c,uid)
            return 200,{'user':{'id':uid,'email':email},'csrf':csrf}, {'Set-Cookie':self.cookie(token,7*86400)}
        if method=='GET' and path=='/api/auth/me':
            session=s.auth_session(c,self.session_token())
            if not session:return 200,{'user':None,'panta_configured':panta.enabled()},None
            return 200,{'user':{k:session[k] for k in ('id','email','display_name')},'csrf':session['csrf'],'panta_configured':panta.enabled()},None
        sess=self.session(c);user=sess['id']
        if method!='GET':self.csrf(sess)
        if method=='POST' and path=='/api/auth/logout':
            c.execute('DELETE FROM sessions WHERE token_hash=?',(s.digest(self.session_token()),))
            return 200,{'ok':True},{'Set-Cookie':self.cookie('',0)}
        # Explicit authenticated diagnostics: never return API key material.
        if method=='GET' and path=='/api/panta/status':
            return 200,{'configured':panta.enabled(),'base':'custom' if os.environ.get('PANTA_API_BASE') else 'official',
                'last_sync':s.last_sync(c),'read_only':True,'checked_live':False},None
        if method=='POST' and path=='/api/panta/check':
            global _last_panta_check
            if not panta.enabled():
                raise panta.PantaError('No Panta API key configured. Live data is unavailable.','not_configured')
            with _check_lock:
                now=time.monotonic()
                if now-_last_panta_check<30:
                    raise RequestError(429,'Please wait 30 seconds between live connection checks')
                _last_panta_check=now
            markets=panta.catalog(limit=1)
            return 200,{'connection':'verified','source':'live','checked_at':s.utc(),
                'catalog_items':len(markets['items']),'key_validated_for_market_listing':True},None
        if method=='GET' and path=='/api/workspaces':
            rows=c.execute('SELECT w.id,w.name,m.role FROM workspaces w JOIN memberships m ON w.id=m.workspace_id WHERE m.user_id=? ORDER BY w.id',(user,)).fetchall()
            return 200,{'workspaces':[dict(x) for x in rows]},None
        if method=='POST' and path=='/api/workspaces':
            d=self.parse();ws=s.create_workspace(c,user,field(d,'name',100))
            return 201,{'id':ws},None
        if method=='POST' and path=='/api/invites/accept':
            d=self.parse();token=field(d,'token',200)
            inv=c.execute('SELECT * FROM invites WHERE token_hash=? AND expires_at>?',(s.digest(token),s.timestamp())).fetchone()
            if not inv:raise RequestError(404,'Invitation not found or expired')
            c.execute('INSERT INTO memberships VALUES(?,?,?) ON CONFLICT DO NOTHING',(inv['workspace_id'],user,'member'))
            s.audit(c,inv['workspace_id'],user,'member_joined','Accepted workspace invitation')
            return 200,{'workspace_id':inv['workspace_id']},None
        match=re.fullmatch(r'/api/workspaces/(\d+)(?:/(\w+))?',path)
        if match:
            ws=integer(match.group(1));action=match.group(2) or ''
            s.require_member(c,ws,user)
            if method=='GET' and not action:return 200,s.overview(c,ws,user),None
            if method=='POST' and action=='invites':
                s.require_owner(c,ws,user)
                token=secrets.token_urlsafe(30)
                c.execute('INSERT INTO invites VALUES(?,?,?,?)',(s.digest(token),ws,user,s.timestamp()+86400))
                s.audit(c,ws,user,'invite_created','24-hour invitation issued')
                return 201,{'token':token,'expires_hours':24},None
            if method=='GET' and action=='activity':
                acts=c.execute('SELECT a.event,a.detail,a.created_at,u.display_name AS author FROM audit a JOIN users u ON u.id=a.user_id WHERE workspace_id=? ORDER BY a.id DESC LIMIT 80',(ws,)).fetchall()
                return 200,{'activity':[dict(x) for x in acts]},None
            if method=='GET' and action=='alerts':
                try:threshold=max(0.01,min(1,float(qs.get('threshold','.15'))))
                except ValueError:raise RequestError(400,'Invalid threshold')
                return 200,{'alerts':s.alert_summary(c,ws,user,threshold),'threshold':threshold},None
            if method=='GET' and action=='export':
                data=s.overview(c,ws,user)
                data['details']=[s.decision_details(c,d['id'],user) for d in data['decisions']]
                raw=json.dumps(data,ensure_ascii=False,indent=2).encode()
                return 200,raw,'application/json; charset=utf-8',{'Content-Disposition':'attachment; filename="outcomeos-export.json"'}
            if method=='GET' and action=='csv':
                dec=s.overview(c,ws,user)['decisions']
                f=io.StringIO();writer=csv.writer(f);writer.writerow(['id','title','question','status','outcome','team_probability','forecast_count','link_count','impact_usd','created_at'])
                for d in dec:writer.writerow([d.get(x) for x in ('id','title','question','status','outcome','team_probability','forecast_count','link_count','impact_usd','created_at')])
                return 200,f.getvalue().encode('utf-8-sig'),'text/csv; charset=utf-8',{'Content-Disposition':'attachment; filename="outcomeos-decisions.csv"'}
            if method=='POST' and action=='decisions':
                d=self.parse();deadline=field(d,'deadline',30,False) or None
                if deadline and not re.fullmatch(r'\d{4}-\d{2}-\d{2}',deadline):raise RequestError(400,'Use YYYY-MM-DD for deadline')
                did=s.create_decision(c,ws,user,field(d,'title',120),field(d,'question',350),field(d,'description',2500,False),field(d,'category',50,False) or 'Strategy',deadline,amount(d.get('impact_usd',0)))
                return 201,{'id':did},None
        # Owner-only share issuance/revocation. Share token displayed once and stored hashed.
        report_match=re.fullmatch(r'/api/decisions/(\d+)/report',path)
        if report_match:
            did=integer(report_match.group(1))
            decision=s.get_decision(c,did,user)
            s.require_owner(c,decision['workspace_id'],user)
            if method=='GET':
                active=c.execute('SELECT created_at,expires_at FROM public_reports WHERE decision_id=? AND revoked_at IS NULL AND expires_at>? ORDER BY created_at DESC LIMIT 1',(did,s.timestamp())).fetchone()
                return 200,{'active':bool(active),'expires_at':active['expires_at'] if active else None},None
            if method=='POST':
                # A fresh share invalidates all older links, including ones not yet expired.
                c.execute('UPDATE public_reports SET revoked_at=? WHERE decision_id=? AND revoked_at IS NULL',(s.utc(),did))
                token=secrets.token_urlsafe(36)
                c.execute('INSERT INTO public_reports(token_hash,decision_id,created_by,created_at,expires_at,revoked_at) VALUES(?,?,?,?,?,NULL)',
                          (s.digest(token),did,user,s.utc(),s.timestamp()+7*86400))
                s.audit(c,decision['workspace_id'],user,'public_report_issued','Report for decision #'+str(did))
                return 201,{'token':token,'expires_hours':168,'notice':'Anyone with this link can view the title, question, description, aggregate forecasts and linked market history. No personal identities or evidence notes are shared.'},None
            if method=='DELETE':
                c.execute('UPDATE public_reports SET revoked_at=? WHERE decision_id=? AND revoked_at IS NULL',(s.utc(),did))
                s.audit(c,decision['workspace_id'],user,'public_report_revoked','Report for decision #'+str(did))
                return 200,{'ok':True},None
        match=re.fullmatch(r'/api/decisions/(\d+)(?:/(\w+))?',path)
        if match:
            did=integer(match.group(1));action=match.group(2) or ''
            d=s.get_decision(c,did,user);ws=d['workspace_id']
            if method=='GET' and not action:return 200,s.decision_details(c,did,user),None
            if method=='PATCH' and not action:
                inp=self.parse()
                if d['status']!='open':raise RequestError(409,'Cannot modify a resolved or archived decision')
                vals={}
                for k,maxlen in [('title',120),('question',350),('description',2500),('category',50)]:
                    if k in inp:vals[k]=field(inp,k,maxlen,k in ('title','question'))
                if 'impact_usd' in inp:vals['impact_usd']=amount(inp['impact_usd'])
                if 'deadline' in inp:
                    dl=field(inp,'deadline',30,False)
                    if dl and not re.fullmatch(r'\d{4}-\d{2}-\d{2}',dl):raise RequestError(400,'Use YYYY-MM-DD for deadline')
                    vals['deadline']=dl or None
                if not vals:raise RequestError(400,'Nothing to update')
                vals['updated_at']=s.utc()
                c.execute('UPDATE decisions SET '+','.join(f'{k}=?' for k in vals)+' WHERE id=?',(*vals.values(),did))
                s.audit(c,ws,user,'decision_updated',str(did))
                return 200,{'ok':True},None
            if method=='POST' and action=='archive':
                if d['status']=='resolved':raise RequestError(409,'Resolved decisions cannot be archived')
                c.execute('UPDATE decisions SET status=?,updated_at=? WHERE id=?',('archived',s.utc(),did))
                s.audit(c,ws,user,'decision_archived',d['title'])
                return 200,{'ok':True},None
            if method=='POST' and action=='resolve':
                s.require_owner(c,ws,user)
                if d['status']!='open':raise RequestError(409,'Only open decisions may be resolved')
                inp=self.parse();outcome=inp.get('outcome')
                if type(outcome) is not bool:raise RequestError(400,'Outcome must be true or false')
                c.execute('UPDATE decisions SET status=?,outcome=?,updated_at=? WHERE id=?',('resolved',int(outcome),s.utc(),did))
                s.audit(c,ws,user,'decision_resolved',d['title']+' → '+('YES' if outcome else 'NO'))
                return 200,{'ok':True},None
            if method=='POST' and action=='forecasts':
                if d['status']!='open':raise RequestError(409,'Decision is not open for forecasts')
                inp=self.parse();p=probability(inp.get('probability'))
                reason=field(inp,'reason',1000,False)
                c.execute('INSERT INTO forecasts(decision_id,user_id,probability,reason,created_at) VALUES(?,?,?,?,?)',(did,user,p,reason,s.utc()))
                s.audit(c,ws,user,'forecast_added',d['title']+' · '+str(round(p*100))+'%')
                return 201,{'ok':True},None
            if method=='POST' and action=='notes':
                inp=self.parse();body=field(inp,'body',3000)
                url=field(inp,'source_url',500,False)
                if url and not url.startswith(('https://','http://')):raise RequestError(400,'Evidence URL must use http(s)')
                c.execute('INSERT INTO notes(decision_id,user_id,body,source_url,created_at) VALUES(?,?,?,?,?)',(did,user,body,url,s.utc()))
                s.audit(c,ws,user,'evidence_added',d['title'])
                return 201,{'ok':True},None
            if method=='POST' and action=='links':
                if d['status']!='open':raise RequestError(409,'Decision must be open')
                inp=self.parse();mid=field(inp,'market_id',100);src=field(inp,'source',10);why=field(inp,'match_explanation',1000)
                if src=='live':
                    market=panta.detail(mid)
                    if market['marketId']!=mid:raise RequestError(409,'Market ID mismatch')
                elif src=='demo':
                    market=next((m for m in demo_markets()['items'] if m['marketId']==mid),None)
                    if not market:raise RequestError(400,'Unknown demo market')
                else:raise RequestError(400,'Invalid market source')
                lid=c.execute('INSERT INTO market_links(decision_id,market_id,market_title,source,match_explanation,created_at) VALUES(?,?,?,?,?,?) RETURNING id',
                    (did,mid,market['title'],src,why,s.utc())).fetchone()['id']
                if src=='live':
                    s.record_live_snapshot(c,lid,market)
                elif market['yesPrice'] is not None:
                    c.execute('INSERT INTO snapshots(link_id,yes_price,no_price,phase,created_at,source) VALUES(?,?,?,?,?,?)',(lid,market['yesPrice'],market['noPrice'],market['phase'],s.utc(),src))
                s.audit(c,ws,user,'market_linked',d['title']+' ↔ '+market['title'])
                return 201,{'id':lid},None
        match=re.fullmatch(r'/api/links/(\d+)(?:/(\w+))?',path)
        if match:
            lid=integer(match.group(1));action=match.group(2) or ''
            link=c.execute('SELECT l.*,d.workspace_id,d.status FROM market_links l JOIN decisions d ON l.decision_id=d.id WHERE l.id=?',(lid,)).fetchone()
            if not link:raise RequestError(404,'Linked market not found')
            s.require_member(c,link['workspace_id'],user)
            if method=='DELETE' and not action:
                c.execute('DELETE FROM market_links WHERE id=?',(lid,));s.audit(c,link['workspace_id'],user,'market_unlinked',link['market_title'])
                return 200,{'ok':True},None
            if method=='POST' and action=='refresh':
                if link['source']!='live':raise RequestError(400,'Demo quotes cannot be refreshed as live data')
                market=panta.detail(link['market_id'])
                result=s.record_live_snapshot(c,lid,market)
                s.audit(c,link['workspace_id'],user,'quote_refreshed',link['market_title']+' ('+result+')')
                return 200,{'market':market,'snapshot_result':result},None
        if method=='GET' and path=='/api/markets/categories':return 200,panta.categories(),None
        if method=='GET' and path=='/api/markets/demo':return 200,demo_markets(),None
        if method=='GET' and path=='/api/markets':
            cat=qs.get('category','')[:70];phase=qs.get('phase','')[:25];cursor=qs.get('cursor','')[:160]
            return 200,panta.catalog(cat,phase,cursor),None
        match=re.fullmatch(r'/api/markets/([1-9A-HJ-NP-Za-km-z]{25,60})',path)
        if method=='GET' and match:return 200,panta.detail(match.group(1)),None
        raise RequestError(404,'Unknown endpoint')

def create_server(host=None,port=None):
    s.init_db()
    host=host or os.environ.get('OUTCOMEOS_HOST','127.0.0.1')
    port=int(port if port is not None else os.environ.get('PORT','8766'))
    return ThreadingHTTPServer((host,port),Handler)

def main():
    server=create_server();print(f'OutcomeOS running at http://{server.server_address[0]}:{server.server_address[1]}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
