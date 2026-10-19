// DRAFT ONLY. Do not deploy in the SQL preparation gate.
// Configure verify_jwt=false for this function only: its dedicated trigger
// credential is checked by dispatch.mjs. Never use a service_role key in Cron.
import { createHandler } from "./dispatch.mjs";
import { createRpc } from "./rpc.mjs";

// Fail closed: reusable trigger and broad service_role adapter are NOT approved.
// Keep the previous implementation inspectable; this entrypoint cannot dispatch.
throw new Error("inactive_preparation_review_blocked_see_review_md");

const stagingUrl = Deno.env.get("SUPABASE_URL") ?? "";
const allowedRef = Deno.env.get("CRON_STAGING_PROJECT_REF") ?? "";
if (!/^[a-z0-9]{20}$/.test(allowedRef) || stagingUrl !== `https://${allowedRef}.supabase.co`) {
  throw new Error("staging_binding_invalid");
}
const transport = fetch.bind(globalThis);
const rpc = createRpc({
  stagingUrl, serviceKey: Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "", fetchImpl: transport,
});
Deno.serve(createHandler({
  triggerSecret: Deno.env.get("CRON_TRIGGER_SECRET") ?? "",
  githubPat: Deno.env.get("GITHUB_DISPATCH_PAT") ?? "",
  fetchImpl: transport, ...rpc,
}));
