import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import { createHandler, createWakeHandler, REPOSITORY, WORKFLOW, GITHUB_DISPATCH_URL }
  from '../../drafts/cron_controlled_dispatch/redesign/edge/dispatch.mjs';
import { createLedger } from '../../drafts/cron_controlled_dispatch/redesign/edge/ledger.mjs';

const ID='00000000-0000-4000-8000-000000000001';
const RELEASE='00000000-0000-4000-8000-000000000002';
const RECEIPT='00000000-0000-4000-8000-000000000003';
const SHA='a'.repeat(40);
const PAT=['github','pat','synthetic'.repeat(8)].join('_');
const request=(body={authorization_id:ID},headers={})=>new Request('https://edge.invalid/dispatch',{
  method:'POST',headers:{'content-type':'application/json',...headers},body:JSON.stringify(body),
});
const accepted=()=>Response.json({workflow_run_id:123,
  run_url:`https://api.github.com/repos/${REPOSITORY}/actions/runs/123`,
  html_url:`https://github.com/${REPOSITORY}/actions/runs/123`});

// Policy double only. These tests do NOT establish PostgreSQL or ingress identity.
function harness(options={}) {
  const state={consumed:false,committed:false,claims:0,fetches:0,trace:[]};
  let clock=10000;
  const grant={verified:true,authorization_id:ID,release_id:RELEASE,repository:REPOSITORY,
    workflow:WORKFLOW,ref:'dev',expected_sha:SHA,
    not_before:new Date(9000).toISOString(),expires_at:new Date(20000).toISOString(),...options.grant};
  const ledger={
    claim:async(id,sha,release)=>{
      state.claims++;
      if(options.claimError) throw new Error(PAT);
      if(options.released===false || state.consumed || id!==ID || sha!==SHA || release!==RELEASE) return {claimed:false};
      state.consumed=true;state.committed=options.committed!==false;state.trace.push('claim');
      if(options.commitResponseLost) throw new Error(PAT);
      return {claimed:true,authorization_id:ID,release_id:RELEASE,claim_id:RECEIPT,
        repository:REPOSITORY,workflow:WORKFLOW,ref:'dev',expected_sha:SHA,
        expires_at:grant.expires_at,...options.permit};
    },
    confirm:async()=>{
      state.trace.push('confirm');
      if(options.confirmError) throw new Error(PAT);
      if(options.expireOnConfirm) clock=21000;
      return state.committed;
    },
    finish:async(_id,_receipt,result)=>{
      state.result=result;state.trace.push('finish');
      if(options.finishError) throw new Error(PAT);
      return true;
    },
  };
  const fetchImpl=async(url,init)=>{
    assert.equal(state.committed,true);
    state.fetches++;state.trace.push('github');state.sent={url,init};
    if(options.networkError) throw options.networkError;
    return options.response?.()??accepted();
  };
  const handler=createHandler({githubPat:PAT,ledger,fetchImpl,now:()=>clock,
    verifyIngress:async()=>options.falseIngress?null:grant});
  return {handler,state};
}

test('verified legitimate ingress consumes, confirms and sends only the fixed operation',async()=>{
  const h=harness();const response=await h.handler(request());
  assert.equal(response.status,202);assert.equal((await response.json()).workflow_run_id,123);
  assert.deepEqual(h.state.trace,['claim','confirm','github','finish']);
  assert.equal(h.state.sent.url,GITHUB_DISPATCH_URL);
  assert.equal(h.state.sent.init.redirect,'error');assert.ok(h.state.sent.init.signal instanceof AbortSignal);
  assert.deepEqual(JSON.parse(h.state.sent.init.body),{ref:'dev',return_run_details:true,
    inputs:{dispatch_id:ID,expected_sha:SHA}});
});

test('public wake cannot consume or access a transport, even for a released known UUID',async()=>{
  const handler=createWakeHandler();
  const responses=await Promise.all(Array.from({length:32},()=>handler(request())));
  assert.ok(responses.every(r=>r.status===403));
});

test('forged headers and a known authorization UUID do not authenticate Cron',async()=>{
  const h=harness({falseIngress:true});
  assert.equal((await h.handler(request(undefined,{'x-cron-verified':'true',authorization:'Bearer artificial'}))).status,401);
  assert.equal(h.state.claims,0);assert.equal(h.state.fetches,0);assert.equal(h.state.consumed,false);
});

test('missing ingress verifier fails configuration closed',()=>{
  assert.throws(()=>createHandler({githubPat:PAT}),/configuration_invalid/);
});

for(const [name,options] of [
  ['early call',{grant:{not_before:new Date(11000).toISOString()}}],
  ['expired ingress',{grant:{expires_at:new Date(10000).toISOString()}}],
  ['overlong validity',{grant:{not_before:new Date(0).toISOString(),expires_at:new Date(400000).toISOString()}}],
  ['other repository',{grant:{repository:'example/other'}}],
  ['other workflow',{grant:{workflow:'other.yml'}}],
  ['other branch',{grant:{ref:'main'}}],
  ['wrong authorization',{grant:{authorization_id:RECEIPT}}],
]) test(`${name} never consumes`,async()=>{
  const h=harness(options);assert.equal((await h.handler(request())).status,403);
  assert.equal(h.state.claims,0);assert.equal(h.state.fetches,0);
});

test('unreleased permit cannot be consumed, and Edge exposes no rearm method',async()=>{
  const h=harness({released:false});assert.equal((await h.handler(request())).status,409);
  assert.equal(h.state.consumed,false);assert.equal(h.state.fetches,0);
  assert.deepEqual(Object.keys(createLedger({connect:async()=>null})).sort(),['claim','confirm','finish']);
});

test('32 concurrent verified attempts and a later replay have one winner',async()=>{
  const h=harness();const responses=await Promise.all(Array.from({length:32},()=>h.handler(request())));
  assert.equal(responses.filter(r=>r.status===202).length,1);assert.equal(h.state.fetches,1);
  assert.equal((await h.handler(request())).status,409);assert.equal(h.state.fetches,1);
});

for(const [name,options] of [
  ['claim failure',{claimError:true}],['lost commit response',{commitResponseLost:true}],
  ['uncommitted result',{committed:false}],['failed confirmation',{confirmError:true}],
  ['expiry after confirmation',{expireOnConfirm:true}],['forged permit',{permit:{workflow:'other.yml'}}],
]) test(`${name} never sends`,async()=>{
  const h=harness(options);assert.notEqual((await h.handler(request())).status,202);
  assert.equal(h.state.fetches,0);
});

for(const [name,options,status] of [
  ['network failure',{networkError:new Error(PAT)},'ambiguous'],
  ['timeout',{networkError:new DOMException(PAT,'TimeoutError')},'ambiguous'],
  ['HTTP failure',{response:()=>new Response('private body',{status:403})},'http_error'],
  ['redirect',{response:()=>new Response(null,{status:307})},'http_error'],
  ['204',{response:()=>new Response(null,{status:204})},'ambiguous'],
  ['malformed 200',{response:()=>new Response('private body',{status:200})},'ambiguous'],
  ['untrusted run URL',{response:()=>Response.json({workflow_run_id:123,html_url:'https://other.invalid'})},'ambiguous'],
]) test(`${name} preserves consumption and never retries`,async()=>{
  const h=harness(options);const text=await(await h.handler(request())).text();
  assert.equal(JSON.parse(text).status,status);
  assert.equal(text.includes(PAT),false);assert.equal(text.includes('private body'),false);
  assert.equal(h.state.consumed,true);await h.handler(request());assert.equal(h.state.fetches,1);
});

test('audit failure exposes no driver secret and cannot rearm',async()=>{
  const h=harness({finishError:true});const body=await(await h.handler(request())).json();
  assert.equal(body.audit_recorded,false);assert.equal(body.workflow_run_id,123);
  assert.equal(JSON.stringify(body).includes(PAT),false);await h.handler(request());assert.equal(h.state.fetches,1);
});

test('caller cannot select a branch or inject SQL through the envelope',async()=>{
  const h=harness();assert.equal((await h.handler(request({authorization_id:ID,ref:'main'}))).status,400);
  assert.equal((await h.handler(request({authorization_id:"'; SELECT 1; --"}))).status,400);
  assert.equal(h.state.claims,0);
});

test('ledger makes independent committed transactions with parameterized fixed SQL',async()=>{
  const sessions=[];
  const ledger=createLedger({connect:async()=>{
    const trace=[];sessions.push(trace);
    return {query:async(query,parameters)=>{trace.push({query,parameters});return {rows:[{result:true}]};},
      close:async()=>trace.push({closed:true})};
  }});
  await ledger.claim(ID,SHA,RELEASE);await ledger.confirm(ID,RECEIPT);
  await ledger.finish(ID,RECEIPT,{outcome:'ambiguous',http_status:null,run_id:null});
  assert.equal(sessions.length,3);assert.equal(sessions[0][0].query,'BEGIN');
  assert.equal(sessions[1][0].query,'BEGIN READ ONLY');
  for(const trace of sessions){assert.equal(trace.at(-2).query,'COMMIT');assert.equal(trace.at(-1).closed,true);}
  assert.deepEqual(sessions[0][4].parameters,[ID,SHA,RELEASE]);
  assert.ok(sessions.every(trace=>!JSON.stringify(trace).includes(PAT)));
});

test('uncertain DB commit returns a generic error without retry',async()=>{
  let connections=0,commits=0;
  const ledger=createLedger({connect:async()=>{connections++;return {
    query:async(query)=>{if(query==='COMMIT'){commits++;throw new Error('synthetic-db-password');}
      return {rows:[{result:true}]};},close:async()=>{throw new Error('synthetic-db-password');},
  };}});
  await assert.rejects(()=>ledger.claim(ID,SHA,RELEASE),error=>error.message==='ledger_unavailable');
  assert.equal(connections,1);assert.equal(commits,1);
});

const base=new URL('../../drafts/cron_controlled_dispatch/redesign/',import.meta.url);
const read=name=>readFileSync(new URL(name,base),'utf8');
test('SQL limits Edge to three private capabilities and cannot rearm',()=>{
  const schema=read('sql/10_control.draft.sql');const routines=read('sql/20_routines.draft.sql');
  assert.match(schema,/NOLOGIN NOSUPERUSER NOBYPASSRLS/);
  assert.match(schema,/FROM PUBLIC,anon,authenticated,service_role,cron_dispatch_edge_v2/);
  assert.doesNotMatch(routines,/public\.|vault\.|net\.|pg_xact_status|claim_xid/);
  assert.match(routines,/TO cron_dispatch_edge_v2;/);
  assert.match(routines,/release\(uuid,bigint\),cron_dispatch_v2.cancel\(uuid\) TO postgres/);
  assert.match(routines,/FOR UPDATE/);assert.match(routines,/permit_cannot_be_rearmed/);
  for(const header of routines.match(/CREATE FUNCTION[\s\S]+?AS \$\w+\$/g)??[])
    assert.match(header,/SET search_path=pg_catalog/);
  const uncommented=(schema+routines).replace(/--[^\n]*/g,'');
  assert.doesNotMatch(uncommented,/PASSWORD|vault\.create_secret|CREATE EXTENSION|cron\.schedule/);
});

test('entrypoint is blocked without broad key, trigger secret or live listener',()=>{
  const entry=read('edge/index.ts');
  assert.match(entry,/throw new Error\('redesign_requires_verified_ingress/);
  assert.doesNotMatch(entry,/SERVICE_ROLE|TRIGGER_SECRET|Deno\.serve|Deno\.env/);
});

test('redesigned handler and ledger have no logging or dynamic transport endpoint',()=>{
  const code=read('edge/dispatch.mjs')+read('edge/ledger.mjs');
  assert.doesNotMatch(code,/console\.|SUPABASE_SERVICE_ROLE_KEY|CRON_TRIGGER_SECRET/);
  assert.doesNotMatch(code,/request\.headers\.get\(['"]authorization/);
  assert.doesNotMatch(read('edge/ledger.mjs'),/fetch\(|https?:\/\//);
});
