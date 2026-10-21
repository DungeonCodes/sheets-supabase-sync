import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';

const yaml=readFileSync(new URL('../../drafts/github_scheduler/staging-clock.draft.yml',import.meta.url),'utf8');
const program=yaml.split('// CLOCK_PROGRAM_BEGIN')[1].split('// CLOCK_PROGRAM_END')[0]
  .split('\n').slice(1).map(line=>line.replace(/^          /,'')).join('\n');
const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;
const execute=new AsyncFunction('fetch','process','console','AbortSignal','Date',program);
const REPO='DungeonCodes/sheets-supabase-sync';
const SHA='a'.repeat(40);
const TOKEN='synthetic-automatic-job-credential';
const RUN_ID=123456;
const WORKFLOW_ID=388468858;

async function harness(options={}) {
  let now=Date.now();
  class ClockDate extends Date { static now(){return now;} }
  const env={GITHUB_REPOSITORY:REPO,GITHUB_REF:'refs/heads/main',GITHUB_EVENT_NAME:'workflow_dispatch',
    GITHUB_RUN_ATTEMPT:'1',GITHUB_RUN_ID:'999',CLOCK_ENABLED:'true',CONFIRM_DISPATCH:'true',
    EXPECTED_DEV_SHA:SHA,APPROVAL_EXPIRES_AT:new Date(now+600000).toISOString(),GH_TOKEN:TOKEN,...options.env};
  const requests=[],logs=[];let posts=0;
  const fetch=async(url,init)=>{
    requests.push({url,init});
    assert.ok(url.startsWith(`https://api.github.com/repos/${REPO}/`));
    assert.equal(init.redirect,'error');assert.ok(init.signal instanceof AbortSignal);
    assert.equal(init.headers.Authorization,`Bearer ${TOKEN}`);
    if(init.method==='POST'){
      posts++;
      if(options.postError) throw options.postError;
      if(options.status) return new Response(null,{status:options.status});
      if(options.malformed) return new Response('private response',{status:200});
      return Response.json(options.result??{workflow_run_id:RUN_ID,
        run_url:`https://api.github.com/repos/${REPO}/actions/runs/${RUN_ID}`,
        html_url:`https://github.com/${REPO}/actions/runs/${RUN_ID}`});
    }
    if(options.getError) throw options.getError;
    if(url.endsWith('/git/ref/heads/dev')) return Response.json({object:{type:'commit',sha:options.devSha??SHA}});
    if(url.includes('/runs?')){
      if(options.expireDuringPreflight) now+=700000;
      const rows=options.fullPages?Array.from({length:100},()=>({head_branch:'dev',status:'completed'}))
        :options.busy?[{head_branch:'dev',status:options.busy}]:[];
      return Response.json({workflow_runs:rows});
    }
    if(url.endsWith(`/actions/runs/${RUN_ID}`)){
      if(options.observeError) throw new Error(TOKEN);
      return Response.json({id:RUN_ID,workflow_id:WORKFLOW_ID,event:'workflow_dispatch',
        head_branch:'dev',head_sha:SHA,run_attempt:1,...options.child});
    }
    return Response.json({id:WORKFLOW_ID,path:'.github/workflows/scheduled-sync.yml',state:options.targetState??'active'});
  };
  const process={env,exitCode:0};
  await execute(fetch,process,{log:v=>logs.push(JSON.parse(v)),error:v=>logs.push(JSON.parse(v))},AbortSignal,ClockDate);
  assert.equal(JSON.stringify(logs).includes(TOKEN),false);
  assert.equal(JSON.stringify(logs).includes('private response'),false);
  return {posts,requests,logs,exitCode:process.exitCode};
}

test('exact YAML program dispatches once with the fixed dev payload and correlates run ID',async()=>{
  const h=await harness();assert.equal(h.exitCode,0);assert.equal(h.posts,1);
  assert.equal(h.logs[0].status,'dispatch_accepted_not_completed');
  assert.equal(h.logs[0].target_run_id,RUN_ID);
  const post=h.requests.find(r=>r.init.method==='POST');
  assert.ok(post.url.endsWith('/actions/workflows/scheduled-sync.yml/dispatches'));
  assert.deepEqual(JSON.parse(post.init.body),{ref:'dev',return_run_details:true});
});

for(const [name,env,code] of [
  ['other repository',{GITHUB_REPOSITORY:'example/fork'},'WRONG_REPOSITORY_OR_REF'],
  ['dev invocation',{GITHUB_REF:'refs/heads/dev'},'WRONG_REPOSITORY_OR_REF'],
  ['pull request',{GITHUB_EVENT_NAME:'pull_request'},'WRONG_EVENT'],
  ['rerun',{GITHUB_RUN_ATTEMPT:'2'},'RERUN_FORBIDDEN'],
  ['clock disabled',{CLOCK_ENABLED:''},'CLOCK_DISABLED'],
  ['missing confirmation',{CONFIRM_DISPATCH:'false'},'CONFIRMATION_REQUIRED'],
  ['invalid SHA',{EXPECTED_DEV_SHA:'main'},'EXPECTED_SHA_INVALID'],
  ['missing automatic token',{GH_TOKEN:''},'AUTOMATIC_TOKEN_MISSING'],
  ['expired approval',{APPROVAL_EXPIRES_AT:'2020-01-01T00:00:00Z'},'APPROVAL_WINDOW_INVALID'],
  ['missing approval',{APPROVAL_EXPIRES_AT:''},'APPROVAL_WINDOW_INVALID'],
]) test(`${name} blocks before any API call`,async()=>{
  const h=await harness({env});assert.equal(h.posts,0);assert.equal(h.requests.length,0);
  assert.equal(h.logs[0].code,code);assert.equal(h.exitCode,1);
});

for(const status of ['queued','in_progress','waiting','pending','requested'])
  test(`${status} target causes an explicit skip, not another dispatch`,async()=>{
    const h=await harness({busy:status});assert.equal(h.posts,0);assert.equal(h.exitCode,0);
    assert.equal(h.logs[0].status,'busy_skip');
  });

test('changed dev SHA and disabled target both block dispatch',async()=>{
  for(const options of [{devSha:'b'.repeat(40)},{targetState:'disabled_manually'}]){
    const h=await harness(options);assert.equal(h.posts,0);assert.equal(h.exitCode,1);
  }
});

test('bounded pagination stops if concurrency state cannot be established',async()=>{
  const h=await harness({fullPages:true});assert.equal(h.posts,0);
  assert.equal(h.logs[0].code,'CONCURRENCY_STATE_UNKNOWN');assert.equal(h.requests.length,12);
});

test('approval is checked again immediately before POST',async()=>{
  const h=await harness({expireDuringPreflight:true});assert.equal(h.posts,0);
  assert.equal(h.logs[0].code,'APPROVAL_WINDOW_INVALID');
});

for(const [name,options] of [
  ['network timeout',{postError:new DOMException(TOKEN,'TimeoutError')}],
  ['network error',{postError:new Error(TOKEN)}],['HTTP failure',{status:403}],
  ['redirect',{status:307}],['204',{status:204}],['malformed 200',{malformed:true}],
  ['ambiguous 200',{result:{workflow_run_id:RUN_ID}}],
]) test(`${name} makes one POST only and records ambiguity without leaking credentials`,async()=>{
  const h=await harness(options);assert.equal(h.posts,1);assert.equal(h.exitCode,1);
  assert.equal(h.logs[0].dispatch_attempted,true);
});

test('failed GET preflight has zero POSTs and no automatic retry',async()=>{
  const h=await harness({getError:new Error(TOKEN)});assert.equal(h.posts,0);assert.equal(h.requests.length,1);
});

test('lost observation after accepted dispatch retains run ID and does not repeat POST',async()=>{
  const h=await harness({observeError:true});assert.equal(h.posts,1);
  assert.equal(h.logs[0].accepted_run_id,RUN_ID);assert.equal(h.exitCode,1);
});

test('wrong child branch, SHA, event and attempt are rejected after acceptance, without retry',async()=>{
  for(const child of [{head_branch:'main'},{head_sha:'b'.repeat(40)},{event:'schedule'},{run_attempt:2}]){
    const h=await harness({child});assert.equal(h.posts,1);assert.equal(h.exitCode,1);
    assert.equal(h.logs[0].code,'DISPATCH_IDENTITY_MISMATCH');
  }
});

test('schedule-mode code is ready for future review, but YAML has no active schedule',async()=>{
  const h=await harness({env:{GITHUB_EVENT_NAME:'schedule',CONFIRM_DISPATCH:''}});
  assert.equal(h.posts,1);
  assert.doesNotMatch(yaml,/^\s*schedule\s*:/m);
  assert.doesNotMatch(yaml,/^\s*cron\s*:/m);
});

test('clock has only job-scoped permissions and no data secrets, environment or third-party actions',()=>{
  assert.match(yaml,/^permissions: \{\}/m);
  assert.match(yaml,/      actions: write\n      contents: read/);
  assert.doesNotMatch(yaml,/secrets\.|SUPABASE_|GOOGLE_|^\s*environment\s*:|\buses:/m);
  assert.match(yaml,/GH_TOKEN: \$\{\{ github.token \}\}/);
  assert.match(yaml,/group: staging-clock/);assert.match(yaml,/cancel-in-progress: false/);
});

test('unchanged target still has staging environment, existing concurrency and Python entrypoint',()=>{
  const target=readFileSync(new URL('../../.github/workflows/scheduled-sync.yml',import.meta.url),'utf8');
  assert.match(target,/environment: staging/);assert.match(target,/group: staging-dispatch-\$\{\{ github.ref \}\}/);
  assert.match(target,/cancel-in-progress: false/);assert.match(target,/sheets_supabase_sync\.batch_cli/);
  assert.doesNotMatch(target,/^\s*schedule\s*:/m);
});
