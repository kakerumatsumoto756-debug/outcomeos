'use strict';
const q=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=v=>v===null||v===undefined?'Not available':(100*Number(v)).toFixed(1)+'%';
const date=v=>v?new Date(typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)?v+'T12:00:00':v).toLocaleString():'Not specified';
function timeline(history){
 const pts=history.filter(x=>Number.isFinite(x.yes_price)&&x.yes_price>=0&&x.yes_price<=1);
 if(pts.length<2)return '<p class="report-meta">Not enough valid recorded quotes to show a trend.</p>';
 const points=pts.map((p,i)=>`${(i*100/(pts.length-1)).toFixed(2)},${(95-90*p.yes_price).toFixed(2)}`).join(' ');
 return `<svg viewBox="0 0 100 100" preserveAspectRatio="none" class="report-chart" role="img" aria-label="Historical recorded YES quote"><line x1="0" y1="50" x2="100" y2="50"/><polyline points="${points}"/></svg>`;
}
async function render(){
 const token=new URLSearchParams(location.search).get('t');
 if(!token||!/^[\w-]{35,100}$/.test(token))throw Error('No valid share token found.');
 const res=await fetch('/api/public/'+encodeURIComponent(token),{credentials:'omit',cache:'no-store'});
 if(!res.ok)throw Error('This report has expired, was revoked, or does not exist.');
 const d=await res.json();
 const markets=d.markets.map(m=>{
  const latest=m.history.at(-1);
  const live=m.source==='live';
  return `<article class="report-market ${live?'report-live':'report-demo'}"><div class="report-label">${live?'LIVE PANTA MARKET · SAVED HISTORICAL QUOTE':'SYNTHETIC DEMO DATA'}</div><h3>${esc(m.market_title)}</h3><p>${esc(m.match_explanation)}</p><div class="report-grid"><div><div class="report-label">Recorded YES price</div><div class="report-stat">${pct(latest?.yes_price)}</div></div><div><div class="report-label">Last recorded (not a real-time stream)</div><div>${esc(date(latest?.created_at))}</div></div></div>${timeline(m.history)}</article>`;
 }).join('');
 q('#report').innerHTML=`<section class="report-panel"><div class="report-label">${esc(d.category)} · ${esc(d.status)}</div><h1>${esc(d.title)}</h1><h2>${esc(d.question)}</h2><p>${esc(d.description||'No public context provided.')}</p><div class="report-grid"><div><div class="report-label">Team consensus estimate</div><div class="report-stat">${pct(d.team_probability)}</div></div><div><div class="report-label">Outcome</div><div class="report-stat">${d.status==='resolved'?(d.outcome?'YES':'NO'):'Pending'}</div></div><div><div class="report-label">Deadline</div><div>${esc(date(d.deadline))}</div></div></div><p class="report-meta">Report issued ${esc(date(d.shared_at))}. Link expires ${esc(date(new Date(d.expires_at*1000).toISOString()))}.</p></section><section class="report-panel"><h2>Market-linked evidence</h2><div class="report-warning">Panta quotes are market trading prices, not independently verified probabilities. Prices shown here are stored historical observations, not current tradable quotes. Only use markets with clearly matching resolution definitions.</div>${markets||'<p>No markets linked to this decision.</p>'}</section><p class="report-meta">Private evidence notes, emails, user identities and individual forecasts are not included in this public report.</p>`;
}
render().catch(e=>{q('#report').innerHTML=`<section class="report-panel"><h1>Report unavailable</h1><p>${esc(e.message)}</p></section>`});
