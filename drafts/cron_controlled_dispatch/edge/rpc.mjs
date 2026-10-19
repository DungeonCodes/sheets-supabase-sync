// LEGACY REJECTED FIXTURE: preserved for historical tests; never deploy this adapter.
// Current dedicated-role SQL adapter: ../redesign/edge/ledger.mjs.
export function createRpc({ stagingUrl, serviceKey, fetchImpl }) {
  const base = new URL(stagingUrl);
  if (base.protocol !== "https:" || base.pathname !== "/" || base.username || base.password ||
      base.search || base.hash || !serviceKey) throw new Error("rpc_configuration_invalid");
  async function call(name, body) {
    const response = await fetchImpl(`${base.origin}/rest/v1/rpc/${name}`, {
      method: "POST", redirect: "error", signal: AbortSignal.timeout(5000),
      headers: {
        apikey: serviceKey, Authorization: `Bearer ${serviceKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });
    if (!response.ok || response.headers.get("preference-applied")?.includes("tx=rollback")) {
      throw new Error("rpc_unconfirmed");
    }
    return response.json();
  }
  return {
    claim: (id) => call("cron_claim_dispatch", { p_authorization: id }),
    confirm: (id, receipt) => call("cron_confirm_dispatch_claim", {
      p_authorization: id, p_claim: receipt,
    }),
    finish: (id, receipt, result) => call("cron_finish_dispatch", {
      p_authorization: id, p_claim: receipt, p_outcome: result.outcome,
      p_http_status: result.http_status, p_run_id: result.run_id,
    }),
  };
}
