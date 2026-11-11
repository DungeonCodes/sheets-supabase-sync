import test from 'node:test';
import assert from 'node:assert/strict';
import {reportEvidence,parseEvidence} from './evidence.mjs';
import {assessTick} from './observation.mjs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const sha='a'.repeat(40);
const clock={kind:'clock',status:'DISPATCH_ACCEPTED',clock_run_id:'1',executor_run_id:2,at:'2026-10-21T00:00:00Z',clock_branch:'main',target_branch:'dev',expected_dev_sha:sha,executor_sha:sha};
const executor={kind:'executor',mode:'scheduled',state:'EXECUTOR_SUCCESS',clock_run_id:'1',executor_run_id:'2',executor_sha:sha,actual_at:'2026-10-21T00:01:00Z',sources_total:1,sources_due:1,sources_executed:1,sources_failed:0,sources_busy_deferred:0,sources_no_changes:0,sources_skipped:0};
const run={kind:'run',id:2,head_branch:'dev',head_sha:sha,event:'workflow_dispatch',run_attempt:1,status:'completed',conclusion:'success',updated_at:'2026-10-21T00:02:00Z'};
const state=(c=clock,e=executor,r=run)=>reportEvidence([c,e,r]).observations[0].state;
test('success, no changes, partial failure and busy are distinct',()=>{
 assert.equal(state(),'SUCCESS');
 assert.equal(state(clock,{...executor,sources_no_changes:1}),'NO_CHANGES');
 assert.equal(state(clock,{...executor,state:'EXECUTOR_PARTIAL_FAILURE',sources_failed:1}, {...run,conclusion:'failure'}),'PARTIAL_FAILURE');
 assert.equal(state(clock,{...executor,state:'CLOCK_BUSY',sources_busy_deferred:1}),'BUSY_DEFERRED');
 assert.equal(state(clock,{...executor,state:'CLOCK_SKIPPED_NO_DUE',sources_due:0,sources_executed:0,sources_skipped:1}),'NO_DUE');
});
test('failures, pending, missing and ambiguous never imply success',()=>{
 assert.equal(state(clock,{...executor,sources_total:undefined},{...run,conclusion:'failure'}),'INFRASTRUCTURE_FAILURE');
 assert.equal(state(clock,executor,{...run,status:'in_progress'}),'PENDING');
 assert.equal(reportEvidence([clock]).observations[0].state,'INCOMPLETE');
 assert.equal(reportEvidence([{...clock,status:'EXECUTOR_UNKNOWN'}]).observations[0].state,'AMBIGUOUS');
 assert.equal(reportEvidence([clock,{...clock,status:'EXECUTOR_UNKNOWN'},executor,run]).observations[0].state,'AMBIGUOUS');
 assert.equal(reportEvidence([executor]).observations[0].state,'INCOMPLETE');
 assert.deepEqual(reportEvidence([]).observations,[]);
});
test('identity, timestamps, counters and conflicting events fail closed',()=>{
 assert.equal(state(clock,executor,{...run,head_branch:'main'}),'IDENTITY_MISMATCH');
 assert.equal(state(clock,{...executor,executor_sha:'b'.repeat(40)},run),'IDENTITY_MISMATCH');
 assert.equal(state(clock,{...executor,actual_at:'2026-02-30T00:00:00Z'},run),'INCOMPLETE');
 assert.equal(state(clock,executor,{...run,updated_at:'2026-10-20T00:00:00Z'}),'INCONSISTENT');
 assert.equal(state(clock,{...executor,sources_no_changes:2},run),'INCONSISTENT');
 assert.equal(reportEvidence([clock,executor,{...executor,sources_failed:1},run]).observations[0].state,'AMBIGUOUS');
 assert(reportEvidence([clock,{...clock,clock_run_id:'3'},executor,run]).observations.every(x=>x.state==='AMBIGUOUS'));
});
test('out of order, exact duplicates, sanitized output, and last valid',()=>{
 const report=reportEvidence([run,executor,clock,clock,{...run,id:3,token:'synthetic-private'}]);
 const item=report.observations.find(x=>x.clock_run_id==='1');
 assert.equal(item.state,'SUCCESS'); assert.equal(item.duplicate,true);
 assert.equal(report.last_valid_at,executor.actual_at); assert(!JSON.stringify(report).includes('synthetic-private'));
 assert.equal(parseEvidence('{').error,'INVALID_JSON'); assert.equal(parseEvidence('{}').error,'INVALID_DOCUMENT');
});
test('late or missing slot needs independent expected time',()=>{
 const base={enabled:true,workflowActive:true,expectedAt:100,now:200,toleranceMs:10};
 assert.equal(assessTick({...base,observedAt:120}),'late_alert');
 assert.equal(assessTick({...base,observedAt:null}),'missing_alert');
});
test('CLI accepts only local input and never echoes invalid or secret fields',()=>{
 const file=fileURLToPath(new URL('./inspect-evidence.mjs',import.meta.url));
 const valid=spawnSync(process.execPath,[file],{input:JSON.stringify([clock,executor,run]),encoding:'utf8'});
 assert.equal(valid.status,0); assert.equal(JSON.parse(valid.stdout).last_valid_at,executor.actual_at);
 const bad=spawnSync(process.execPath,[file],{input:'{"private":"synthetic-secret"',encoding:'utf8'});
 assert.equal(bad.status,1); assert.equal(JSON.parse(bad.stdout).error,'INVALID_JSON'); assert(!bad.stdout.includes('synthetic-secret'));
});
