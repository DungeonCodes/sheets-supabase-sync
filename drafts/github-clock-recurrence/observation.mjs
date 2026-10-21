/** Evaluate only sanitized executor summaries; exit zero is insufficient. */
export function assessExecution(summary, exitCode, conclusion) {
  const fields = ['sources_due','sources_executed','sources_failed','sources_busy_deferred'];
  if (!summary || fields.some(k => !Number.isSafeInteger(summary[k]) || summary[k]<0)) return 'unknown_alert';
  if (exitCode!==0 || conclusion!=='success' || summary.sources_failed>0) return 'failure_alert';
  if (summary.sources_busy_deferred>0) return 'busy_reconcile';
  return summary.sources_due===0 ? 'no_eligible_sources' : 'success';
}
/** Expected slot supplied by approved cadence; never inferred from receipt time. */
export function assessTick({enabled, workflowActive, expectedAt, observedAt, now, toleranceMs}) {
  if (!enabled) return 'disabled';
  if (!workflowActive) return 'workflow_disabled_alert';
  if (![expectedAt,now,toleranceMs].every(Number.isFinite) || toleranceMs<0) return 'unknown_alert';
  if (observedAt==null) return now>expectedAt+toleranceMs ? 'missing_alert' : 'waiting';
  if (!Number.isFinite(observedAt)) return 'unknown_alert';
  return observedAt>expectedAt+toleranceMs ? 'late_alert' : 'on_time';
}

export const OPERATIONAL_STATES = Object.freeze(['CLOCK_DISABLED','CLOCK_SKIPPED_NO_DUE','CLOCK_BUSY','DISPATCH_ACCEPTED','EXECUTOR_SUCCESS','EXECUTOR_PARTIAL_FAILURE','EXECUTOR_FAILED','EXECUTOR_UNKNOWN','TICK_DELAYED','TICK_MISSING_OR_UNKNOWN']);
const countFields=['sources_total','sources_due','sources_executed','sources_failed','sources_busy_deferred'];
/** Contract only. No network, persistence, or alert delivery. Unknown values remain null. */
export function publicObservation(input) {
  const iso=x=>typeof x==='string' && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{3})?Z$/.test(x) && Number.isFinite(Date.parse(x))?x:null;
  const id=x=>typeof x==='string' && /^[1-9]\d*$/.test(x)?x:null;
  const sha=x=>typeof x==='string' && /^[0-9a-f]{40}$/.test(x)?x:null;
  const count=x=>Number.isSafeInteger(x) && x>=0?x:null;
  return {state:OPERATIONAL_STATES.includes(input.state)?input.state:'EXECUTOR_UNKNOWN',
    mode:['manual','scheduled'].includes(input.mode)?input.mode:null,
    expected_at:iso(input.expected_at),actual_at:iso(input.actual_at),
    clock_run_id:id(input.clock_run_id),executor_run_id:id(input.executor_run_id),
    clock_sha:sha(input.clock_sha),executor_sha:sha(input.executor_sha),
    ...Object.fromEntries(countFields.map(key=>[key,count(input[key])])),
    duration_seconds:typeof input.duration_seconds==='number' && Number.isFinite(input.duration_seconds) && input.duration_seconds>=0?input.duration_seconds:null,
    last_success_at:iso(input.last_success_at)};
}
export function executorState(summary, exitCode, conclusion) {
  if (summary && Number.isSafeInteger(summary.sources_failed) && summary.sources_failed>0) return 'EXECUTOR_PARTIAL_FAILURE';
  if (['failure','timed_out','action_required'].includes(conclusion) || Number.isInteger(exitCode) && exitCode!==0) return 'EXECUTOR_FAILED';
  if (!summary || countFields.some(k=>!Number.isSafeInteger(summary[k]) || summary[k]<0) || exitCode!==0 || conclusion!=='success') return 'EXECUTOR_UNKNOWN';
  if(summary.sources_busy_deferred) return 'CLOCK_BUSY';
  return summary.sources_due ? 'EXECUTOR_SUCCESS' : 'CLOCK_SKIPPED_NO_DUE';
}
