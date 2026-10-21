// OFFLINE DRAFT. Ingress verification is a mandatory, independently trusted boundary.
export const REPOSITORY = 'DungeonCodes/sheets-supabase-sync';
export const WORKFLOW = 'scheduled-sync.yml';
export const REF = 'dev';
export const GITHUB_DISPATCH_URL = `https://api.github.com/repos/${REPOSITORY}/actions/workflows/${WORKFLOW}/dispatches`;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const SHA = /^[0-9a-f]{40}$/;
const reply = (status, code = 200, metadata = {}) => Response.json({ status, ...metadata }, { status: code });

async function readId(request) {
  if (request.headers.get('content-type')?.split(';')[0] !== 'application/json') return null;
  const reader = request.body?.getReader();
  if (!reader) return null;
  const chunks = [];
  let length = 0;
  const deadline = AbortSignal.timeout(2000);
  const abort = () => { void reader.cancel().catch(() => {}); };
  deadline.addEventListener('abort', abort, { once: true });
  try {
    while (true) {
      const part = await reader.read();
      if (deadline.aborted) return null;
      if (part.done) break;
      length += part.value.byteLength;
      if (length > 1024) { await reader.cancel(); return null; }
      chunks.push(part.value);
    }
    const buffer = new Uint8Array(length);
    let offset = 0;
    for (const chunk of chunks) { buffer.set(chunk, offset); offset += chunk.byteLength; }
    const parsed = JSON.parse(new TextDecoder().decode(buffer));
    if (!parsed || Array.isArray(parsed) || Object.keys(parsed).length !== 1) return null;
    return UUID.test(parsed.authorization_id ?? '') ? parsed.authorization_id : null;
  } finally { deadline.removeEventListener('abort', abort); }
}

function validGrant(grant, id, now) {
  const start = Date.parse(grant?.not_before);
  const end = Date.parse(grant?.expires_at);
  return grant?.verified === true && grant.authorization_id === id &&
    grant.repository === REPOSITORY && grant.workflow === WORKFLOW && grant.ref === REF &&
    SHA.test(grant.expected_sha ?? '') && UUID.test(grant.release_id ?? '') &&
    Number.isFinite(start) && Number.isFinite(end) && end > start && end-start <= 300000 &&
    now >= start && now < end;
}

async function dispatch(fetchImpl, githubPat, id, sha) {
  try {
    const response = await fetchImpl(GITHUB_DISPATCH_URL, {
      method: 'POST', redirect: 'error', signal: AbortSignal.timeout(15000),
      headers: {
        Authorization: `Bearer ${githubPat}`, Accept: 'application/vnd.github+json',
        'Content-Type': 'application/json', 'User-Agent': 'sheets-supabase-sync-controlled-dispatch',
        'X-GitHub-Api-Version': '2026-03-10',
      },
      body: JSON.stringify({ ref: REF, return_run_details: true,
        inputs: { dispatch_id: id, expected_sha: sha } }),
    });
    if (response.status !== 200) return {
      outcome: response.status === 204 ? 'ambiguous' : 'http_error',
      http_status: response.status, run_id: null,
    };
    let body;
    try { body = await response.json(); } catch {
      return { outcome: 'ambiguous', http_status: 200, run_id: null };
    }
    const runId = body?.workflow_run_id;
    const valid = Number.isSafeInteger(runId) && runId > 0 &&
      body.run_url === `https://api.github.com/repos/${REPOSITORY}/actions/runs/${runId}` &&
      body.html_url === `https://github.com/${REPOSITORY}/actions/runs/${runId}`;
    return { outcome: valid ? 'accepted' : 'ambiguous', http_status: 200, run_id: valid ? runId : null };
  } catch { return { outcome: 'ambiguous', http_status: null, run_id: null }; }
}

export function createHandler({ verifyIngress, githubPat, ledger, fetchImpl, now = Date.now }) {
  if (typeof verifyIngress !== 'function' || !/^github_pat_[A-Za-z0-9_]{20,}$/.test(githubPat ?? '') ||
      !['claim','confirm','finish'].every((name) => typeof ledger?.[name] === 'function') ||
      typeof fetchImpl !== 'function') throw new Error('dispatch_configuration_invalid');
  return async (request) => {
    if (request.method !== 'POST') return reply('method_not_allowed', 405);
    let grant, id;
    try {
      // NEVER trust X-* headers, UUID knowledge, source IP, or JSON as proof.
      // No built-in implementation: public pg_net ingress remains blocked.
      grant = await verifyIngress(request);
      if (grant?.verified !== true) return reply('unauthorized', 401);
      id = await readId(request);
    } catch { return reply('unauthorized_or_invalid_request', 401); }
    if (!id) return reply('invalid_request', 400);
    if (!validGrant(grant, id, now())) return reply('not_authorized', 403);
    let permit;
    try {
      permit = await ledger.claim(id, grant.expected_sha, grant.release_id);
      if (!permit?.claimed) return reply('not_authorized', 409);
      if (permit.authorization_id !== id || permit.ref !== REF ||
          permit.repository !== REPOSITORY || permit.workflow !== WORKFLOW ||
          permit.expected_sha !== grant.expected_sha || permit.release_id !== grant.release_id ||
          !UUID.test(permit.claim_id ?? '') ||
          !Number.isFinite(Date.parse(permit.expires_at)) ||
          now() >= Date.parse(permit.expires_at)) return reply('claim_invalid', 409);
      // Fresh committed transaction, not pg_xact_status and not own uncommitted writes.
      if (await ledger.confirm(id, permit.claim_id) !== true) return reply('commit_unconfirmed', 409);
      if (now() >= Math.min(Date.parse(permit.expires_at), Date.parse(grant.expires_at))) {
        return reply('authorization_expired', 409);
      }
    } catch { return reply('claim_uncertain', 503); }
    const result = await dispatch(fetchImpl, githubPat, id, permit.expected_sha);
    let recorded = false;
    try { recorded = await ledger.finish(id, permit.claim_id, result) === true; } catch { /* Never resend. */ }
    return reply(result.outcome, 202, { authorization_id: id,
      workflow_run_id: result.run_id, audit_recorded: recorded });
  };
}

// Public wake endpoint deliberately has NO ledger/PAT/transport dependency.
// It cannot consume a permit, enqueue work, or promise dispatch to its caller.
export function createWakeHandler() {
  return async (request) => request.method === 'POST'
    ? reply('wake_not_authorized_for_dispatch', 403) : reply('method_not_allowed', 405);
}
