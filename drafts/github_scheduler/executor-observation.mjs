// Offline review helper only. No network, filesystem, credential or workflow mutation.
// Supply the parsed dispatcher summary, not raw logs; return only allowlisted fields.
const COUNTERS = ['sources_total','sources_due','sources_executed','sources_no_changes',
  'sources_skipped','sources_failed','sources_busy_deferred'];

export function observeExecutor({clockRunId, executorRunId, expectedWorkflowId, expectedSha,
  run, summary, stagingGuardVerified=false, reconciliationVerified=false, checkedAt}) {
  const result = {classification:'UNKNOWN',clock_run_id:null,executor_run_id:null,
    branch:null,commit_sha:null,created_at:null,updated_at:null,checked_at:null,
    github_conclusion:null,staging_guard_verified:stagingGuardVerified===true,
    reconciliation_verified:reconciliationVerified===true,counters:null};
  const positiveId = value => Number.isSafeInteger(value) && value>0;
  const timestamp = value => typeof value==='string' &&
    /^\d{4}-\d{2}-\d{2}T[\d:.]+Z$/.test(value) && Number.isFinite(Date.parse(value));
  if (!positiveId(clockRunId)||!positiveId(executorRunId)||!positiveId(expectedWorkflowId)||
      !/^[0-9a-f]{40}$/.test(expectedSha??'')||!timestamp(checkedAt)) return result;
  Object.assign(result,{clock_run_id:clockRunId,executor_run_id:executorRunId,checked_at:checkedAt});
  if (!run || run.id!==executorRunId || run.workflow_id!==expectedWorkflowId ||
      run.event!=='workflow_dispatch' || run.head_branch!=='dev' ||
      run.head_sha!==expectedSha || run.run_attempt!==1) {
    result.classification='IDENTITY_MISMATCH';return result;
  }
  Object.assign(result,{branch:'dev',commit_sha:expectedSha,
    created_at:timestamp(run.created_at)?run.created_at:null,
    updated_at:timestamp(run.updated_at)?run.updated_at:null});
  if (run.status!=='completed') {result.classification='PENDING';return result;}
  const conclusions=['success','failure','cancelled','timed_out','skipped','neutral','action_required','stale'];
  result.github_conclusion=conclusions.includes(run.conclusion)?run.conclusion:null;
  if (run.conclusion!=='success') {result.classification='EXECUTOR_NOT_SUCCESSFUL';return result;}
  if (!summary || summary.environment!=='staging' || summary.mode!=='apply_staging' ||
      summary.status!=='completed' || !COUNTERS.every(k=>Number.isSafeInteger(summary[k])&&summary[k]>=0)) {
    result.classification='SUMMARY_INVALID';return result;
  }
  result.counters=Object.fromEntries(COUNTERS.map(k=>[k,summary[k]]));
  const s=result.counters;
  const invalidSources=s.sources_total-s.sources_due-s.sources_skipped;
  if (invalidSources<0 || s.sources_executed!==s.sources_due ||
      s.sources_no_changes+s.sources_busy_deferred>s.sources_executed ||
      s.sources_failed<invalidSources ||
      s.sources_no_changes+s.sources_busy_deferred+s.sources_failed>s.sources_executed+invalidSources) {
    result.classification='COUNTERS_INCONSISTENT';return result;
  }
  if (s.sources_failed>0) {result.classification='SOURCES_FAILED';return result;}
  if (s.sources_busy_deferred>0) {result.classification='BUSY_DEFERRED';return result;}
  if (stagingGuardVerified!==true || reconciliationVerified!==true || !result.created_at || !result.updated_at ||
      Date.parse(result.updated_at)<Date.parse(result.created_at) || Date.parse(checkedAt)<Date.parse(result.updated_at)) {
    result.classification='AWAITING_STAGING_RECONCILIATION';return result;
  }
  result.classification=s.sources_due===0?'NO_DUE_SOURCES':'GREEN';
  return result;
}
