// Local-only evidence inspection. Input is untrusted; output is an allowlist.
const id = x => typeof x === 'string' && /^[1-9]\d*$/.test(x) ? x : Number.isSafeInteger(x) && x > 0 ? String(x) : null;
const sha = x => typeof x === 'string' && /^[0-9a-f]{40}$/.test(x) ? x : null;
const stamp = x => {
  if (typeof x !== 'string' || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{3})?Z$/.test(x)) return null;
  const date = new Date(x);
  return Number.isFinite(date.valueOf()) && date.toISOString().replace('.000Z','Z') === x.replace('.000Z','Z') ? x : null;
};
const counts = ['sources_total','sources_due','sources_executed','sources_failed','sources_busy_deferred','sources_no_changes','sources_skipped'];
const integer = x => Number.isSafeInteger(x) && x >= 0;
function classify(clock, executor, run) {
  if (!clock || !executor || !run) return 'INCOMPLETE';
  if (clock.status !== 'DISPATCH_ACCEPTED') return 'AMBIGUOUS';
  if (clock.target_branch !== 'dev' || clock.clock_branch !== 'main' || run.head_branch !== 'dev' ||
      run.event !== 'workflow_dispatch' || run.run_attempt !== 1 || executor.mode !== 'scheduled' ||
      !sha(clock.expected_dev_sha) || clock.expected_dev_sha !== sha(clock.executor_sha) ||
      clock.expected_dev_sha !== sha(executor.executor_sha) || clock.expected_dev_sha !== sha(run.head_sha)) return 'IDENTITY_MISMATCH';
  if (id(clock.executor_run_id) !== id(executor.executor_run_id) || id(clock.executor_run_id) !== id(run.id) ||
      id(clock.clock_run_id) !== id(executor.clock_run_id)) return 'IDENTITY_MISMATCH';
  if (!stamp(clock.at) || !stamp(executor.actual_at) || !stamp(run.updated_at)) return 'INCOMPLETE';
  // Dispatch acceptance can be logged after a fast child has already completed.
  // GitHub metadata can have second precision while the summary has milliseconds.
  if (Date.parse(run.updated_at) + 999 < Date.parse(executor.actual_at)) return 'INCONSISTENT';
  if (run.status !== 'completed') return 'PENDING';
  if (['failure','timed_out','action_required'].includes(run.conclusion) && !counts.every(k => integer(executor[k]))) return 'INFRASTRUCTURE_FAILURE';
  if (!counts.every(k => integer(executor[k]))) return 'INCOMPLETE';
  const s = executor, invalid = s.sources_total - s.sources_due - s.sources_skipped;
  if (invalid < 0 || s.sources_executed !== s.sources_due || s.sources_failed < invalid ||
      s.sources_no_changes + s.sources_busy_deferred + s.sources_failed > s.sources_executed + invalid) return 'INCONSISTENT';
  if (s.sources_failed > 0) return 'PARTIAL_FAILURE';
  if (run.conclusion !== 'success') return ['failure','timed_out','action_required'].includes(run.conclusion) ? 'INFRASTRUCTURE_FAILURE' : 'AMBIGUOUS';
  const expected = s.sources_busy_deferred ? 'CLOCK_BUSY' : s.sources_due ? 'EXECUTOR_SUCCESS' : 'CLOCK_SKIPPED_NO_DUE';
  if (s.state !== expected) return 'INCONSISTENT';
  if (s.sources_busy_deferred) return 'BUSY_DEFERRED';
  if (!s.sources_due) return 'NO_DUE';
  return s.sources_no_changes === s.sources_executed ? 'NO_CHANGES' : 'SUCCESS';
}

// Records are {kind:'clock'|'executor'|'run', ...}; run metadata is read-only,
// independently supplied. No timestamps or fields are invented from missing data.
export function reportEvidence(records) {
  if (!Array.isArray(records)) return {error:'INVALID_DOCUMENT',observations:[],last_valid_at:null};
  const groups = new Map(), executors = new Map();
  let invalid = 0;
  for (const r of records) {
    if (!r || typeof r !== 'object' || Array.isArray(r) || !['clock','executor','run'].includes(r.kind)) { invalid++; continue; }
    const key = r.kind === 'clock' ? id(r.clock_run_id) : r.kind === 'executor' ? id(r.clock_run_id) : null;
    const eid = r.kind === 'run' ? id(r.id) : id(r.executor_run_id);
    if (r.kind !== 'clock' && eid) {
      const entries = executors.get(eid) || {executor:[],run:[]};
      entries[r.kind].push(r); executors.set(eid,entries);
    }
    if (key) { const g=groups.get(key) || {clock:[],executor:[]}; g[r.kind].push(r); groups.set(key,g); }
    else if (r.kind !== 'run' || !eid) invalid++;
  }
  const observations=[];
  for (const [clockId, g] of groups) {
    // Exact repeated records are harmless; conflicting copies are ambiguous.
    const unique = a => [...new Map(a.map(x => [JSON.stringify(x),x])).values()];
    const cs=unique(g.clock), es=unique(g.executor);
    const accepted=cs.filter(x=>x.status==='DISPATCH_ACCEPTED');
    const c=accepted[0], e=es[0], eid=id(c?.executor_run_id) || id(e?.executor_run_id);
    const runs=unique(executors.get(eid)?.run || []);
    let state = accepted.length > 1 || es.length > 1 || runs.length > 1 ? 'AMBIGUOUS' : classify(c,e,runs[0]);
    if (cs.some(x=>x.status==='EXECUTOR_UNKNOWN')) state='AMBIGUOUS';
    const duplicate = g.clock.length > cs.length || g.executor.length > es.length || (executors.get(eid)?.run.length || 0) > runs.length;
    observations.push({clock_run_id:clockId,executor_run_id:eid,state,duplicate,
      actual_at:stamp(e?.actual_at),executor_sha:sha(e?.executor_sha),sources_failed:integer(e?.sources_failed)?e.sources_failed:null});
  }
  // An uncorrelated executor/run must remain visible as incomplete.
  for (const [eid, entries] of executors) if (!observations.some(o=>o.executor_run_id===eid))
    observations.push({clock_run_id:null,executor_run_id:eid,state:'INCOMPLETE',duplicate:false,actual_at:null,executor_sha:null,sources_failed:null});
  for (const item of observations) if (item.executor_run_id && observations.filter(o=>o.executor_run_id===item.executor_run_id).length>1) item.state='AMBIGUOUS';
  observations.sort((a,b)=>(a.clock_run_id || '').localeCompare(b.clock_run_id || ''));
  const valid=observations.filter(x=>['SUCCESS','NO_CHANGES','NO_DUE'].includes(x.state) && x.actual_at);
  valid.sort((a,b)=>Date.parse(b.actual_at)-Date.parse(a.actual_at));
  return {error:invalid?'INVALID_RECORDS':null,observations,last_valid_at:valid[0]?.actual_at ?? null};
}

export function parseEvidence(text) {
  try { return reportEvidence(JSON.parse(text)); }
  catch { return {error:'INVALID_JSON',observations:[],last_valid_at:null}; }
}
