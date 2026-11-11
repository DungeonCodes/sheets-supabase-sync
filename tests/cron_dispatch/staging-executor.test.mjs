import fs from 'node:fs';
import assert from 'node:assert/strict';
import test from 'node:test';
import {spawnSync} from 'node:child_process';

const yaml=fs.readFileSync(new URL('../../.github/workflows/scheduled-sync.yml',import.meta.url),'utf8').replace(/\r\n/g,'\n');
const program=yaml.split('// EXECUTOR_GUARD_BEGIN')[1].split('// EXECUTOR_GUARD_END')[0].split('\n').slice(1).map(x=>x.replace(/^          /,'')).join('\n');
const repository=yaml.match(/GITHUB_REPOSITORY!=='([^']+)'/)[1];
const sha='a'.repeat(40);
const base={GITHUB_REPOSITORY:repository,GITHUB_REF:'refs/heads/dev',GITHUB_WORKFLOW_REF:`${repository}/.github/workflows/scheduled-sync.yml@refs/heads/dev`,GITHUB_EVENT_NAME:'workflow_dispatch',GITHUB_SHA:sha,WORKFLOW_SHA:sha,GITHUB_RUN_ID:'456',GITHUB_RUN_NUMBER:'10',GITHUB_RUN_ATTEMPT:'1',AUTHORIZED_RUN_NUMBER:'10',APPROVAL_EXPIRES_AT:new Date(Date.now()+600000).toISOString(),CLOCK_RUN_ID:'',EXECUTION_MODE:'manual',APPROVED_DEV_SHA:sha,APPROVED_INPUT_SHA:''};
function guard(patch={}) {
 const process={env:{...base,...patch},exitCode:0}, logs=[];
 new Function('process','console',program)(process,{log:x=>logs.push(JSON.parse(x))});
 return {code:process.exitCode,logs};
}
const manual={EXECUTION_MODE:'manual',APPROVED_INPUT_SHA:'',CLOCK_RUN_ID:''};
test('manual requires approved SHA and independent run authorization',()=>{
 assert.equal(guard().code,0);
 for (const mode of ['', 'manual']) assert.equal(guard({...manual,EXECUTION_MODE:mode}).code,0);
 assert.equal(guard({...manual,AUTHORIZED_RUN_NUMBER:''}).code,1);
 assert.equal(guard({...manual,GITHUB_SHA:'b'.repeat(40)}).code,1);
 assert.equal(guard({...manual,APPROVED_DEV_SHA:''}).code,1);
 assert.equal(guard({...manual,GITHUB_RUN_ATTEMPT:'2'}).code,1);
});
for(const [name,patch] of [
 ['sha mismatch',{GITHUB_SHA:'b'.repeat(40)}], ['approved missing',{APPROVED_DEV_SHA:''}],
 ['manual sha input',{APPROVED_INPUT_SHA:'b'.repeat(40)}], ['manual clock id',{CLOCK_RUN_ID:'123'}],
 ['rerun',{GITHUB_RUN_ATTEMPT:'2'}], ['branch',{GITHUB_REF:'refs/heads/main'}], ['mode',{EXECUTION_MODE:'other'}],
 ['invalid execution sha',{GITHUB_SHA:''}], ['invalid approved sha',{APPROVED_DEV_SHA:'dev'}],
 ['workflow sha changed',{WORKFLOW_SHA:'b'.repeat(40)}], ['workflow sha missing',{WORKFLOW_SHA:''}],
 ['missing run grant',{AUTHORIZED_RUN_NUMBER:''}], ['different run',{AUTHORIZED_RUN_NUMBER:'11'}],
 ['missing expiry',{APPROVAL_EXPIRES_AT:''}], ['expired',{APPROVAL_EXPIRES_AT:'2000-01-01T00:00:00Z'}],
 ['too long',{APPROVAL_EXPIRES_AT:new Date(Date.now()+3600000).toISOString()}],
 ['invalid date',{APPROVAL_EXPIRES_AT:'2026-02-30T00:00:00Z'}],
]) test(name,()=>assert.equal(guard(patch).code,1));
test('scheduled mode remains blocked even with all other authorizations',()=>{
 const result=guard({EXECUTION_MODE:'scheduled',SCHEDULE_ENABLED:'true',CLOCK_RUN_ID:'123',APPROVED_INPUT_SHA:sha});
 assert.equal(result.code,1); assert.equal(result.logs[0].code,'SCHEDULED_MODE_DISABLED');
 assert.equal(guard({...manual,APPROVED_DEV_SHA:''}).code,1);
 assert.equal(guard({AUTHORIZED_RUN_NUMBER:'',EXECUTION_MODE:'scheduled'}).code,1);
});
test('guard before checkout, verification and secrets with staging guard',()=>{
 const before=(a,b)=>assert(yaml.indexOf(a)>=0 && yaml.indexOf(a)<yaml.indexOf(b));
 before('EXECUTOR_GUARD_BEGIN','actions/checkout'); before('EXECUTOR_GUARD_BEGIN','secrets.');
 before('Verify authorization has not expired','actions/checkout');
 before('Verify checkout revision','secrets.'); before('Validate staging guard','Dispatch due staging sources');
 assert.match(yaml,/ref: \$\{\{ github.sha \}\}/); assert.match(yaml,/persist-credentials: false/);
 const [preflight, dispatch] = yaml.split('\n  dispatch:\n');
 assert.match(preflight,/\n  preflight:\n/); assert.doesNotMatch(preflight,/environment:\s*staging|secrets\./);
 assert.match(dispatch,/needs: preflight/); assert.match(dispatch,/environment: staging/);
 assert.doesNotMatch(dispatch.split('\n    steps:')[0],/\bif:\s*.*(?:always|failure|cancelled)\s*\(/);
 assert.match(dispatch,/permissions:\s+contents: read/); assert.match(yaml,/permissions: \{\}/);
});
test('guard never emits untrusted input',()=>{
 const result=guard({APPROVED_INPUT_SHA:'synthetic-private',CLOCK_RUN_ID:'synthetic-private'});
 assert(!JSON.stringify(result).includes('synthetic-private'));
});
test('dispatch rejects an expired or missing preflight authorization',()=>{
 const step=yaml.split('name: Verify authorization has not expired')[1].split('      - uses:')[0];
 const script=step.match(/node -e "([^\n]+)"/)[1];
 const check=expiry=>spawnSync(process.execPath,['-e',script],{env:{...process.env,APPROVAL_EXPIRES_AT:expiry}}).status;
 assert.equal(check(new Date(Date.now()+60000).toISOString()),0);
 assert.equal(check('2000-01-01T00:00:00Z'),1); assert.equal(check(''),1);
});
