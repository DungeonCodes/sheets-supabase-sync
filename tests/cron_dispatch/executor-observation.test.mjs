import assert from 'node:assert/strict';
import test from 'node:test';
import {observeExecutor} from '../../drafts/github_scheduler/executor-observation.mjs';

const SHA='a'.repeat(40);
function evidence(overrides={}) {
  return {clockRunId:101,executorRunId:202,expectedWorkflowId:303,expectedSha:SHA,
    checkedAt:'2026-01-01T12:05:00Z',stagingGuardVerified:true,reconciliationVerified:true,
    run:{id:202,workflow_id:303,event:'workflow_dispatch',head_branch:'dev',head_sha:SHA,
      run_attempt:1,status:'completed',conclusion:'success',created_at:'2026-01-01T12:00:00Z',
      updated_at:'2026-01-01T12:04:00Z'},
    summary:{environment:'staging',mode:'apply_staging',status:'completed',sources_total:1,
      sources_due:1,sources_executed:1,sources_no_changes:1,sources_skipped:0,
      sources_failed:0,sources_busy_deferred:0},...overrides};
}

test('GREEN requires identity, actual summary, guard and staging reconciliation',()=>{
  const r=observeExecutor(evidence());assert.equal(r.classification,'GREEN');
  assert.equal(r.counters.sources_no_changes,1);assert.equal(r.executor_run_id,202);
});
test('exit code success and GitHub success do not hide a source failure',()=>{
  const e=evidence();e.summary.sources_failed=1;e.summary.sources_no_changes=0;
  e.summary.exit_code=0;
  assert.equal(observeExecutor(e).classification,'SOURCES_FAILED');
});
test('busy source is deferred, not GREEN or a workflow retry instruction',()=>{
  const e=evidence();e.summary.sources_busy_deferred=1;e.summary.sources_no_changes=0;
  assert.equal(observeExecutor(e).classification,'BUSY_DEFERRED');
});
test('zero eligible sources is an explicit valid outcome',()=>{
  const e=evidence();Object.assign(e.summary,{sources_due:0,sources_executed:0,sources_no_changes:0,sources_skipped:1});
  assert.equal(observeExecutor(e).classification,'NO_DUE_SOURCES');
});
for(const patch of [{summary:null},{summary:{environment:'production'}},{summary:{status:'selected'}}])
  test(`missing or wrong summary fails closed: ${JSON.stringify(patch)}`,()=>{
    assert.equal(observeExecutor(evidence(patch)).classification,'SUMMARY_INVALID');
  });
for(const patch of [{sources_failed:-1},{sources_failed:'0'},{sources_no_changes:2},
  {sources_due:2},{sources_executed:0}])
  test(`invalid counters cannot be GREEN: ${JSON.stringify(patch)}`,()=>{
    const e=evidence();Object.assign(e.summary,patch);
    assert.notEqual(observeExecutor(e).classification,'GREEN');
  });
for(const patch of [{head_branch:'main'},{head_sha:'b'.repeat(40)},{run_attempt:2},{workflow_id:404}])
  test(`identity mismatch is explicit: ${JSON.stringify(patch)}`,()=>{
    const e=evidence();Object.assign(e.run,patch);
    assert.equal(observeExecutor(e).classification,'IDENTITY_MISMATCH');
  });
test('accepted or running executor remains pending',()=>{
  const e=evidence();e.run.status='in_progress';e.run.conclusion=null;
  assert.equal(observeExecutor(e).classification,'PENDING');
});
for(const conclusion of ['failure','cancelled','timed_out','skipped'])
  test(`unsuccessful executor ${conclusion} is not GREEN`,()=>{
    const e=evidence();e.run.conclusion=conclusion;
    assert.equal(observeExecutor(e).classification,'EXECUTOR_NOT_SUCCESSFUL');
  });
for(const patch of [{stagingGuardVerified:false},{reconciliationVerified:false},
  {stagingGuardVerified:'yes'},{reconciliationVerified:'yes'}])
  test(`unverified staging evidence is incomplete: ${JSON.stringify(patch)}`,()=>{
    assert.equal(observeExecutor(evidence(patch)).classification,'AWAITING_STAGING_RECONCILIATION');
  });
test('unknown inputs and arbitrary private fields are never returned',()=>{
  const e=evidence();e.summary.private_data='synthetic-private-value';e.run.token='synthetic-private-value';
  assert.equal(JSON.stringify(observeExecutor(e)).includes('synthetic-private-value'),false);
  assert.equal(observeExecutor(evidence({clockRunId:null})).classification,'UNKNOWN');
});
test('invalid or out-of-order observation timestamps cannot be GREEN',()=>{
  assert.equal(observeExecutor(evidence({checkedAt:'invalid'})).classification,'UNKNOWN');
  const e=evidence();e.run.updated_at='2026-01-01T12:10:00Z';
  assert.equal(observeExecutor(e).classification,'AWAITING_STAGING_RECONCILIATION');
});
