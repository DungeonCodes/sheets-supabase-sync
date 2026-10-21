import assert from "node:assert/strict";
import test from "node:test";
import { createHandler, GITHUB_DISPATCH_URL } from "../../drafts/cron_controlled_dispatch/edge/dispatch.mjs";
import { createRpc } from "../../drafts/cron_controlled_dispatch/edge/rpc.mjs";

const ID = "00000000-0000-4000-8000-000000000001";
const RECEIPT = "00000000-0000-4000-8000-000000000002";
const SHA = "a".repeat(40);
const TRIGGER = "b".repeat(64); // Artificial, deterministic; never a real secret.
const PAT = ["github", "pat", "x".repeat(40)].join("_"); // Synthetic test value.

function request(body = { authorization_id: ID }, credential = TRIGGER) {
  return new Request("https://edge.invalid/dispatch", {
    method: "POST", headers: { Authorization: `Bearer ${credential}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function runBody(id = 123) {
  return {
    workflow_run_id: id,
    run_url: `https://api.github.com/repos/DungeonCodes/sheets-supabase-sync/actions/runs/${id}`,
    html_url: `https://github.com/DungeonCodes/sheets-supabase-sync/actions/runs/${id}`,
  };
}

// A policy double, not a PostgreSQL emulator: no SQL is applied by these tests.
function harness(options = {}) {
  const trace = [];
  const ledger = { consumed: false, committed: false, outcome: "queued", calls: 0 };
  let clock = options.now ?? 10;
  const githubCalls = [];
  const claim = async (id) => {
    ledger.calls++;
    if (options.beforeClaimError) throw new Error(PAT);
    if (id !== ID || ledger.consumed || clock >= (options.expires ?? 20) ||
        clock < (options.notBefore ?? 0) || options.ref === "main") return { claimed: false };
    ledger.consumed = true;
    ledger.outcome = "consumed";
    if (options.afterCommitError) { ledger.committed = true; throw new Error(PAT); }
    ledger.committed = options.commit !== false;
    trace.push(ledger.committed ? "committed" : "uncommitted");
    return { claimed: true, authorization_id: id, claim_id: RECEIPT, ref: options.forgedRef ?? "dev", expected_sha: SHA,
      expires_at: new Date((options.expires ?? 20) * 1000).toISOString() };
  };
  const confirm = async () => {
    trace.push("confirm");
    if (options.confirmError) throw new Error(PAT);
    if (options.advanceAfterConfirm) clock = options.advanceAfterConfirm;
    return ledger.committed;
  };
  const fetchImpl = async (url, init) => {
    assert.equal(ledger.committed, true, "network must follow committed claim");
    trace.push("github");
    githubCalls.push({ url, init });
    if (options.networkError) throw options.networkError;
    return options.response?.() ?? Response.json(runBody());
  };
  const finish = async (_id, _receipt, result) => {
    trace.push("finish");
    if (options.auditError) throw new Error(PAT);
    ledger.outcome = result.outcome;
    ledger.result = result;
    return true;
  };
  return {
    handler: createHandler({ triggerSecret: TRIGGER, githubPat: PAT, claim, confirm, finish, fetchImpl, now: () => clock * 1000 }),
    ledger, githubCalls, trace,
  };
}

test("accepted dispatch consumes first and uses the approved endpoint/ref/envelope", async () => {
  const h = harness();
  const result = await h.handler(request());
  assert.deepEqual(h.trace, ["committed", "confirm", "github", "finish"]);
  assert.equal(h.githubCalls.length, 1);
  const { url, init } = h.githubCalls[0];
  assert.equal(url, GITHUB_DISPATCH_URL);
  assert.equal(init.method, "POST");
  assert.equal(init.redirect, "error");
  assert.equal(JSON.stringify(init).includes(TRIGGER), false);
  assert.ok(init.signal instanceof AbortSignal);
  assert.deepEqual(JSON.parse(init.body), { ref: "dev", return_run_details: true, inputs: { dispatch_id: ID, expected_sha: SHA } });
  assert.deepEqual(await result.json(), { status: "accepted", authorization_id: ID, workflow_run_id: 123, audit_recorded: true });
});

test("32 concurrent/replayed deliveries permit one GitHub fetch", async () => {
  const h = harness();
  const responses = await Promise.all(Array.from({ length: 32 }, () => h.handler(request())));
  assert.equal(h.githubCalls.length, 1);
  assert.equal(responses.filter((response) => response.status === 202).length, 1);
  assert.equal(responses.filter((response) => response.status === 409).length, 31);
});

test("a repeated Cron delivery never rearms an already consumed authorization", async () => {
  const h = harness();
  await h.handler(request());
  assert.equal((await h.handler(request())).status, 409);
  assert.equal(h.githubCalls.length, 1);
});

for (const [name, options] of [
  ["expired authorization", { expires: 10 }],
  ["not-yet-valid authorization", { notBefore: 11 }],
  ["branch other than dev", { ref: "main" }],
  ["forged RPC branch", { forgedRef: "main" }],
  ["uncommitted claim", { commit: false }],
  ["failure before consumption", { beforeClaimError: true }],
  ["lost acknowledgement after commit", { afterCommitError: true }],
  ["failure after consumption before sending", { confirmError: true }],
  ["expiration while confirming commit", { advanceAfterConfirm: 21 }],
]) {
  test(`${name} produces no GitHub request`, async () => {
    const h = harness(options);
    const response = await h.handler(request());
    assert.notEqual(response.status, 202);
    assert.equal(h.githubCalls.length, 0);
    assert.equal((await response.text()).includes(PAT), false);
  });
}

test("a lost commit acknowledgement burns the permit and accepts loss", async () => {
  const h = harness({ afterCommitError: true });
  await h.handler(request());
  assert.equal(h.ledger.consumed, true);
  assert.equal(h.ledger.committed, true);
  await h.handler(request());
  assert.equal(h.githubCalls.length, 0);
});

for (const [name, options, outcome] of [
  ["HTTP error", { response: () => new Response("sensitive body", { status: 403 }) }, "http_error"],
  ["redirect response", { response: () => new Response(null, { status: 307 }) }, "http_error"],
  ["timeout", { networkError: new DOMException(PAT, "TimeoutError") }, "ambiguous"],
  ["network failure", { networkError: new Error(PAT) }, "ambiguous"],
  ["204 without run details", { response: () => new Response(null, { status: 204 }) }, "ambiguous"],
  ["malformed 200", { response: () => new Response("not json", { status: 200 }) }, "ambiguous"],
  ["200 with wrong URL", { response: () => Response.json({ ...runBody(), html_url: "https://untrusted.invalid/run" }) }, "ambiguous"],
  ["200 without ID", { response: () => Response.json({}) }, "ambiguous"],
]) {
  test(`${name} never causes automatic retry`, async () => {
    const h = harness(options);
    const response = await h.handler(request());
    const safe = await response.text();
    assert.equal(JSON.parse(safe).status, outcome);
    assert.equal(h.ledger.outcome, outcome);
    await h.handler(request());
    assert.equal(h.githubCalls.length, 1);
    assert.equal(safe.includes(PAT), false);
    assert.equal(safe.includes("sensitive body"), false);
    assert.equal(safe.includes("untrusted.invalid"), false);
  });
}

test("audit write failure preserves the consumed permit and existing run ID", async () => {
  const h = harness({ auditError: true });
  const body = await (await h.handler(request())).json();
  assert.equal(body.workflow_run_id, 123);
  assert.equal(body.audit_recorded, false);
  assert.equal(h.ledger.consumed, true);
  await h.handler(request());
  assert.equal(h.githubCalls.length, 1);
});

test("wrong credentials, oversized input and client branch overrides cannot claim", async () => {
  const h = harness();
  assert.equal((await h.handler(request(undefined, "incorrect"))).status, 401);
  assert.equal((await h.handler(request({ authorization_id: ID, ref: "main" }))).status, 400);
  assert.equal((await h.handler(request({ authorization_id: "x".repeat(2000) }))).status, 400);
  assert.equal(h.ledger.calls, 0);
  assert.equal(h.githubCalls.length, 0);
});

test("configuration rejects credential category swaps before any transport", () => {
  const dependencies = { claim: async () => null, confirm: async () => false, finish: async () => false, fetchImpl: async () => null };
  assert.throws(() => createHandler({ ...dependencies, triggerSecret: PAT, githubPat: TRIGGER }), /configuration_invalid/);
  assert.throws(() => createHandler({ ...dependencies, triggerSecret: TRIGGER, githubPat: "synthetic-service-credential" }), /configuration_invalid/);
});

test("no credential or error body reaches responses, audit records or console", async () => {
  const logged = [];
  const original = console.log;
  console.log = (...items) => logged.push(items);
  try {
    const h = harness({ networkError: new Error(`${PAT} ${TRIGGER}`) });
    const body = await (await h.handler(request())).text();
    const evidence = JSON.stringify({ body, audit: h.ledger.result, logged });
    assert.equal(evidence.includes(PAT), false);
    assert.equal(evidence.includes(TRIGGER), false);
    assert.deepEqual(logged, []);
  } finally { console.log = original; }
});

test("RPC adapters make separate non-retried requests, with no GitHub PAT", async () => {
  const calls = [];
  const rpc = createRpc({
    stagingUrl: "https://staging.invalid", serviceKey: "synthetic-service-credential",
    fetchImpl: async (url, init) => {
      calls.push({ url, init });
      return Response.json(url.endsWith("cron_claim_dispatch") ? { claimed: true } : true);
    },
  });
  await rpc.claim(ID);
  assert.equal(await rpc.confirm(ID, RECEIPT), true);
  await rpc.finish(ID, RECEIPT, { outcome: "ambiguous", http_status: null, run_id: null });
  assert.equal(calls.length, 3);
  assert.ok(calls.every(({ url, init }) => url.startsWith("https://staging.invalid/rest/v1/rpc/") && init.redirect === "error"));
  assert.ok(calls.every(({ init }) => !JSON.stringify(init).includes(PAT)));
  assert.ok(calls.every(({ init }) => !Object.hasOwn(init.headers, "Prefer")));
});

test("RPC rollback preference and uncertain responses fail closed without retry", async () => {
  for (const type of ["rollback", "http_error", "timeout"]) {
    let calls = 0;
    const rpc = createRpc({
      stagingUrl: "https://staging.invalid", serviceKey: "synthetic-service-credential",
      fetchImpl: async () => {
        calls++;
        if (type === "timeout") throw new Error(PAT);
        return type === "rollback" ? Response.json(true, { headers: { "Preference-Applied": "tx=rollback" } })
          : new Response(PAT, { status: 500 });
      },
    });
    await assert.rejects(() => rpc.claim(ID));
    assert.equal(calls, 1);
  }
});
