'use strict';
const fs=require('node:fs');const vm=require('node:vm');const assert=require('node:assert/strict');
const source=fs.readFileSync(__dirname+'/../web/app.js','utf8');
function fixture(fetcher){
 const dom=Object.fromEntries(['#app','#content','#toast-root','#modal-root','#auth-error'].map(id=>[id,{innerHTML:'',hidden:true,textContent:'',isConnected:true,querySelector(){return {focus(){}}}}]));
 const listeners={};let toastTimeout=()=>{};
 class FD{constructor(form){return Object.entries(form.values||{})} [Symbol.iterator](){return this.entries[Symbol.iterator]()}}
 const context={
  fetch:fetcher,AbortController,URLSearchParams,FormData:FD,URL,Number,Math,Promise,
  setTimeout(fn,ms){if(ms===4200){toastTimeout=fn;return 1}return setTimeout(fn,Math.min(ms,2))},clearTimeout,
  window:{scrollTo(){}},location:{search:'',origin:'https://example.test',pathname:'/app'},history:{replaceState(){}},
  document:{querySelector:s=>dom[s]||null,addEventListener:(ev,fn)=>{listeners[ev]=fn}},
  console:{log(){},warn(){},error(){}},confirm:()=>true,navigator:{clipboard:{writeText:async()=>{}}}
 };
 vm.createContext(context);vm.runInContext(source,context,{filename:'app.js'});
 return {context,dom};
}
const respond=(data,status=200)=>({status,ok:status>=200&&status<300,async json(){return data}});
async function wait(ms=30){return new Promise(r=>setTimeout(r,ms))}
(async()=>{
 // A transient failure on initial auth must not expose a misleading signup screen.
 let fail=true;const a=fixture(async url=>{if(fail)throw new Error('network offline');return respond({user:null,panta_configured:false})});
 await wait();assert.match(a.dom['#app'].innerHTML,/Temporarily unable to reach OutcomeOS/);
 fail=false;await vm.runInContext('doAction({dataset:{act:"auth-retry"}})',a.context);await wait();
 assert.match(a.dom['#app'].innerHTML,/Create my workspace/);

 // POST must happen exactly once, even if the first read returns a stale overview.
 let posts=0,gets=0;
 const overview=(d=[])=>({workspace:{id:7,name:'QA'},members:[{id:1,role:'owner'}],decisions:d,metrics:{total:d.length,open:d.length,resolved:0,markets:0,brier:null}});
 const b=fixture(async (url,options={})=>{
  if(url==='/api/auth/me')return respond({user:null});
  if(url==='/api/workspaces/7/decisions'&&options.method==='POST'){posts++;return respond({id:99,workspace_id:7,status:'open'},201)}
  if(url==='/api/workspaces/7'){gets++;return respond(overview(gets>1?[{id:99,title:'QA',question:'Will it happen?',status:'open',category:'QA',team_probability:null,link_count:0}]:[]))}
  throw Error('unexpected request '+url);
 });
 await wait(10);
 vm.runInContext("S.user={id:1,display_name:'QA'};S.csrf='token';S.ws=7;S.overview={workspace:{id:7,name:'QA'},members:[{id:1,role:'owner'}],decisions:[],metrics:{}};S.view='dashboard'",b.context);
 await vm.runInContext("submitForm({id:'decision-form',values:{title:'QA',question:'Will it happen?'}})",b.context);
 assert.equal(posts,1);assert.equal(gets,2);
 assert.equal(vm.runInContext('S.overview.decisions.length',b.context),1);

 // Clicking a market link must fetch server decisions, not rely on a stale initial list.
 const c=fixture(async url=>{
  if(url==='/api/auth/me')return respond({user:null});
  if(url==='/api/workspaces/7')return respond(overview([{id:99,title:'QA',question:'Will it happen?',status:'open',category:'QA'}]));
  throw Error('unexpected request '+url);
 });
 await wait(10);
 vm.runInContext("S.user={id:1,display_name:'QA'};S.ws=7;S.overview={workspace:{id:7,name:'QA'},members:[{id:1,role:'owner'}],decisions:[],metrics:{}};S.marketData={items:[{marketId:'11111111111111111111111111111111',title:'A real market',source:'live'}]};",c.context);
 await vm.runInContext("doAction({dataset:{act:'link-selected',id:'11111111111111111111111111111111'}})",c.context);
 assert.match(c.dom['#modal-root'].innerHTML,/Choose decision room/);
 assert.match(c.dom['#modal-root'].innerHTML,/QA/);
 console.log('client regression tests: 3 passed');
})().catch(error=>{console.error(error);process.exitCode=1});
