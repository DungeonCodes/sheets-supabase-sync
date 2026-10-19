import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import test from 'node:test';

const root = new URL('../../drafts/cron_controlled_dispatch/', import.meta.url);
const read = (name) => readFileSync(new URL(name, root), 'utf8');
const sql = (name) => read(name).replace(/--[^\n]*/g, '').toLowerCase();

test('operational setup and activation fail closed pending security redesign', () => {
  for (const file of readdirSync(new URL('sql/', root))) {
    if (!/^(10|20|30|40|50)_/.test(file)) continue;
    const source = sql(`sql/${file}`);
    assert.match(source, /begin\s+raise exception 'inactive_preparation_review_blocked_see_review_md';/);
  }
  const entry = read('edge/index.ts');
  assert.ok(entry.indexOf('throw new Error("inactive_preparation_review_blocked') < entry.indexOf('Deno.env.get'));
});

test('probe has no network, extension, scheduling, business table or credential access', () => {
  for (const file of readdirSync(new URL('probe/', root)).filter((name) => name.endsWith('.sql'))) {
    const source = sql(`probe/${file}`);
    assert.doesNotMatch(source, /\b(vault|net|cron|public)\s*\./);
    assert.doesNotMatch(source, /https?:|create\s+(extension|role)|\b(call|delete|truncate|drop)\b/);
    assert.doesNotMatch(source, /sync_runs|raw_import_rows|raw_current_rows|service_role_key|github_pat_/);
  }
});

test('isolated setup is fresh, guarded and does not overwrite prior evidence', () => {
  const source = sql('probe/00_setup.draft.sql');
  assert.match(source, /current_user <> 'postgres'/);
  assert.match(source, /isolated_probe_approval_required/);
  assert.match(source, /probe_schema_exists_do_not_reset/);
  assert.match(source, /create schema cron_tx_probe authorization postgres/);
  assert.doesNotMatch(source, /if not exists|on conflict|security definer/);
  assert.equal((source.match(/security invoker set search_path=pg_catalog/g) ?? []).length, 2);
  assert.match(source, /revoke all on all functions in schema cron_tx_probe from public,anon,authenticated,service_role/);
});

test('probe models locked one-use consumption and checks expiry after row lock', () => {
  const source = sql('probe/00_setup.draft.sql');
  assert.match(source, /claim_count in \(0,1\)/);
  assert.match(source, /new.claim_count < old.claim_count/);
  assert.match(source, /for update;/);
  assert.ok(source.indexOf('candidate.expires_at<=clock_timestamp()') > source.indexOf('for update;'));
  assert.match(source, /ref='dev'/);
  assert.match(source, /set_config\('synchronous_commit','on',true\)/);
  assert.doesNotMatch(source, /pg_xact_status|claim_xid/);
});

test('observer uses independent backend metadata and a fresh read committed transaction', () => {
  const source = sql('probe/10_observe_readonly.sql');
  assert.match(source, /begin isolation level read committed read only/);
  assert.match(source, /claimant_pid<>pg_backend_pid\(\)/);
  assert.match(source, /r.rolcanlogin/);
  assert.match(source, /rollback;/);
  assert.doesNotMatch(source, /for update|for share/);
});

test('probe rollback disables only isolated control and preserves consumed evidence', () => {
  const source = sql('probe/30_disable.draft.sql');
  assert.match(source, /isolated_probe_approval_required/);
  assert.match(source, /update cron_tx_probe.control set enabled=false/);
  assert.doesNotMatch(source, /update cron_tx_probe.permits|claim_count\s*=\s*0/);
  assert.match(source, /not enabled as disabled/);
});

test('runbook preserves concurrency barriers and limits the completed database proof', () => {
  const source = read('probe/README.md');
  for (const marker of ['APROVAR PROBE TRANSACIONAL ISOLADO EM STAGING', 'ROLLBACK;',
    'COMMIT;', 'competing_won', 'claimed_by_other_backend=true', 'Não é exactly-once',
    'Não prova PostgREST', 'Timeout não é sucesso']) assert.ok(source.includes(marker), marker);
});

test('inventory reads only metadata and includes all LOGIN roles and effective column access', () => {
  const source = sql('review_role_inventory_readonly.sql');
  assert.match(source, /begin read only/);
  assert.match(source, /r.rolcanlogin/);
  assert.match(source, /has_any_column_privilege/);
  assert.match(source, /pg_auth_members/);
  assert.doesNotMatch(source, /select\s+\*|select\s+.*headers|select\s+.*decrypted_secret\s+from/);
});
