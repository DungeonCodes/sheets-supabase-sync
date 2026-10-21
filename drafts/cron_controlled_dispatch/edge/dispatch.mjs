// LEGACY REJECTED FIXTURE: preserved for historical tests, not a deployment proposal.
// Current redesign lives in ../redesign/edge/. No operational entrypoint imports this.
export const GITHUB_DISPATCH_URL =
  "https://api.github.com/repos/DungeonCodes/sheets-supabase-sync/actions/workflows/scheduled-sync.yml/dispatches";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const SHA = /^[0-9a-f]{40}$/;
const encoder = new TextEncoder();

async function authenticated(header, expected) {
  if (!header?.startsWith("Bearer ") || header.length > 520) return false;
  const algorithm = { name: "HMAC", hash: "SHA-256" };
  const importKey = (value) => crypto.subtle.importKey(
    "raw", encoder.encode(value), algorithm, false, ["sign", "verify"],
  );
  const candidate = header.slice(7);
  if (!candidate) return false;
  const [received, configured] = await Promise.all([
    importKey(candidate), importKey(expected),
  ]);
  const message = encoder.encode("cron-controlled-dispatch-auth-v1");
  const signature = await crypto.subtle.sign("HMAC", received, message);
  return crypto.subtle.verify("HMAC", configured, signature, message);
}

function reply(status, httpStatus = 200, metadata = {}) {
  return Response.json({ status, ...metadata }, { status: httpStatus });
}

async function authorizationId(request) {
  if (request.headers.get("content-type")?.split(";")[0] !== "application/json") {
    return null;
  }
  const reader = request.body?.getReader();
  if (!reader) return null;
  let bytes = 0;
  const chunks = [];
  while (true) {
    const item = await reader.read();
    if (item.done) break;
    bytes += item.value.byteLength;
    if (bytes > 1024) {
      await reader.cancel();
      return null;
    }
    chunks.push(item.value);
  }
  const data = new Uint8Array(bytes);
  let offset = 0;
  for (const chunk of chunks) {
    data.set(chunk, offset);
    offset += chunk.byteLength;
  }
  const parsed = JSON.parse(new TextDecoder().decode(data));
  if (!parsed || Object.keys(parsed).length !== 1) return null;
  return UUID.test(parsed.authorization_id ?? "") ? parsed.authorization_id : null;
}

function acceptedRun(body) {
  const id = body?.workflow_run_id;
  if (!Number.isSafeInteger(id) || id <= 0) return null;
  const api = `https://api.github.com/repos/DungeonCodes/sheets-supabase-sync/actions/runs/${id}`;
  const html = `https://github.com/DungeonCodes/sheets-supabase-sync/actions/runs/${id}`;
  if (body.run_url !== api || body.html_url !== html) return null;
  return id;
}

async function dispatch(fetchImpl, githubPat, claim, id) {
  try {
    const response = await fetchImpl(GITHUB_DISPATCH_URL, {
      method: "POST",
      redirect: "error",
      signal: AbortSignal.timeout(15000),
      headers: {
        Authorization: `Bearer ${githubPat}`,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "sheets-supabase-sync-controlled-dispatch",
        "X-GitHub-Api-Version": "2026-03-10",
      },
      body: JSON.stringify({
        ref: "dev", return_run_details: true,
        inputs: { dispatch_id: id, expected_sha: claim.expected_sha },
      }),
    });
    if (response.status === 200) {
      let body;
      try { body = await response.json(); } catch {
        return { outcome: "ambiguous", http_status: 200, run_id: null };
      }
      const runId = acceptedRun(body);
      return { outcome: runId ? "accepted" : "ambiguous", http_status: 200, run_id: runId };
    }
    return {
      outcome: response.status === 204 ? "ambiguous" : "http_error",
      http_status: response.status, run_id: null,
    };
  } catch {
    // Neither network error details nor HTTP bodies are logged or returned.
    return { outcome: "ambiguous", http_status: null, run_id: null };
  }
}

export function createHandler({ triggerSecret, githubPat, claim, confirm, finish, fetchImpl, now = Date.now }) {
  if (!/^[0-9a-f]{64}$/.test(triggerSecret ?? "") ||
      !/^github_pat_[A-Za-z0-9_]{20,}$/.test(githubPat ?? "") || !fetchImpl) {
    throw new Error("dispatch_configuration_invalid");
  }
  return async (request) => {
    if (request.method !== "POST") return reply("method_not_allowed", 405);
    let id;
    try {
      if (!await authenticated(request.headers.get("authorization"), triggerSecret)) {
        return reply("unauthorized", 401);
      }
      id = await authorizationId(request);
    } catch {
      return reply("invalid_request", 400);
    }
    if (!id) return reply("invalid_request", 400);
    let permit;
    try {
      // RPC response alone is insufficient: confirm observes the committed row
      // from a second transaction, including pg_xact_status(claim_xid).
      permit = await claim(id);
      if (!permit?.claimed) return reply("not_authorized", 409);
      if (permit.ref !== "dev" || !SHA.test(permit.expected_sha ?? "") ||
          !UUID.test(permit.claim_id ?? "") || permit.authorization_id !== id ||
          !Number.isFinite(Date.parse(permit.expires_at))) {
        return reply("claim_invalid", 409);
      }
      if (await confirm(id, permit.claim_id) !== true) return reply("commit_unconfirmed", 409);
      if (now() >= Date.parse(permit.expires_at)) return reply("authorization_expired", 409);
    } catch {
      return reply("claim_uncertain", 503);
    }
    // Exactly one application-level fetch invocation, no retry loop.
    const result = await dispatch(fetchImpl, githubPat, permit, id);
    let recorded = false;
    try {
      recorded = await finish(id, permit.claim_id, result) === true;
    } catch {
      // Authorization stays burned if recording fails. Never repeat dispatch.
    }
    return reply(result.outcome, 202, {
      authorization_id: id, workflow_run_id: result.run_id, audit_recorded: recorded,
    });
  };
}
