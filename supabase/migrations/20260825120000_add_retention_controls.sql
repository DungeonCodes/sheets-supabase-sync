-- Controles aditivos para lifecycle, legal hold e evidencia agregada de purge.
-- Esta migration nao executa purge, nao remove dados e nao altera as tres
-- migrations aplicadas anteriormente.

alter table public.data_sources
  add column lifecycle_status text not null default 'active',
  add column lifecycle_changed_at timestamptz not null default now(),
  add column lifecycle_reason_code text,
  add column lifecycle_changed_by_ref text;

-- Fontes desabilitadas existentes passam a suspensas. A referencia e tecnica,
-- opaca e nao identifica uma pessoa.
update public.data_sources
set lifecycle_status = 'suspended',
    lifecycle_reason_code = 'migration_backfill',
    lifecycle_changed_by_ref = 'system:migration4'
where not enabled;

alter table public.data_sources
  add constraint data_sources_lifecycle_status_valid check (
    lifecycle_status in ('active', 'suspended', 'offboarding', 'retired')
  ),
  add constraint data_sources_lifecycle_enabled_consistent check (
    (lifecycle_status = 'active' and enabled)
    or (lifecycle_status <> 'active' and not enabled)
  ),
  add constraint data_sources_lifecycle_metadata_consistent check (
    lifecycle_status = 'active'
    or (lifecycle_reason_code is not null and lifecycle_changed_by_ref is not null)
  ),
  add constraint data_sources_lifecycle_reason_code_safe check (
    lifecycle_reason_code is null
    or lifecycle_reason_code ~ '^[a-z][a-z0-9_.:-]{0,126}$'
  ),
  add constraint data_sources_lifecycle_actor_ref_safe check (
    lifecycle_changed_by_ref is null
    or lifecycle_changed_by_ref ~ '^[a-z][a-z0-9_.:-]{0,126}$'
  );

create table public.retention_holds (
  id uuid primary key default gen_random_uuid(),
  scope text not null,
  data_source_id uuid references public.data_sources(id) on delete set null,
  source_ref text,
  reason_code text not null,
  activated_at timestamptz not null default now(),
  activated_by_ref text not null,
  released_at timestamptz,
  released_by_ref text,
  release_reason_code text,
  constraint retention_holds_scope_valid check (
    scope in ('institution', 'source')
  ),
  constraint retention_holds_scope_consistent check (
    (scope = 'institution' and data_source_id is null and source_ref is null)
    or (
      scope = 'source'
      and source_ref is not null
      and (data_source_id is not null or released_at is not null)
    )
  ),
  constraint retention_holds_release_consistent check (
    (
      released_at is null
      and released_by_ref is null
      and release_reason_code is null
    )
    or (
      released_at is not null
      and released_by_ref is not null
      and release_reason_code is not null
      and released_at >= activated_at
    )
  ),
  constraint retention_holds_source_ref_safe check (
    source_ref is null or source_ref ~ '^[a-z][a-z0-9_.:-]{0,126}$'
  ),
  constraint retention_holds_reason_code_safe check (
    reason_code ~ '^[a-z][a-z0-9_.:-]{0,126}$'
  ),
  constraint retention_holds_activated_by_ref_safe check (
    activated_by_ref ~ '^[a-z][a-z0-9_.:-]{0,126}$'
  ),
  constraint retention_holds_released_by_ref_safe check (
    released_by_ref is null
    or released_by_ref ~ '^[a-z][a-z0-9_.:-]{0,126}$'
  ),
  constraint retention_holds_release_reason_code_safe check (
    release_reason_code is null
    or release_reason_code ~ '^[a-z][a-z0-9_.:-]{0,126}$'
  )
);

create unique index retention_holds_global_active_idx
  on public.retention_holds (scope)
  where scope = 'institution' and released_at is null;

create unique index retention_holds_source_active_idx
  on public.retention_holds (data_source_id)
  where scope = 'source' and released_at is null;

create table public.purge_runs (
  id uuid primary key default gen_random_uuid(),
  data_source_id uuid references public.data_sources(id) on delete set null,
  source_ref text not null,
  run_type text not null,
  status text not null default 'planned',
  dry_run boolean not null default true,
  policy_ref text not null,
  policy_version text not null,
  policy_digest text not null,
  dry_run_digest text not null,
  cutoffs jsonb not null,
  candidate_counts jsonb not null default '{}'::jsonb,
  affected_counts jsonb not null default '{}'::jsonb,
  outcome_code text,
  approved_at timestamptz,
  approved_by_ref text,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  executed_by_ref text,
  hold_checked_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint purge_runs_type_valid check (
    run_type in ('retention', 'offboarding')
  ),
  constraint purge_runs_status_valid check (
    status in ('planned', 'approved', 'running', 'completed', 'failed', 'cancelled')
  ),
  constraint purge_runs_source_ref_safe check (
    source_ref ~ '^[a-z][a-z0-9_.:-]{0,126}$'
  ),
  constraint purge_runs_policy_ref_safe check (
    policy_ref ~ '^[a-z][a-z0-9_.:/-]{0,126}$'
  ),
  constraint purge_runs_policy_version_safe check (
    policy_version ~ '^[a-z0-9][a-z0-9_.:-]{0,126}$'
  ),
  constraint purge_runs_policy_digest_valid check (
    policy_digest ~ '^[0-9a-f]{64}$'
  ),
  constraint purge_runs_dry_run_digest_valid check (
    dry_run_digest ~ '^[0-9a-f]{64}$'
  ),
  constraint purge_runs_aggregates_objects check (
    jsonb_typeof(cutoffs) = 'object'
    and jsonb_typeof(candidate_counts) = 'object'
    and jsonb_typeof(affected_counts) = 'object'
  ),
  constraint purge_runs_dry_run_has_no_effect check (
    not dry_run or affected_counts = '{}'::jsonb
  ),
  constraint purge_runs_approval_consistent check (
    (approved_at is null and approved_by_ref is null)
    or (
      approved_at is not null
      and approved_by_ref is not null
      and approved_at >= started_at
    )
  ),
  constraint purge_runs_destructive_approval_required check (
    dry_run
    or status in ('planned', 'failed', 'cancelled')
    or (approved_at is not null and approved_by_ref is not null)
  ),
  constraint purge_runs_approved_status_consistent check (
    status <> 'approved'
    or (not dry_run and approved_at is not null and approved_by_ref is not null)
  ),
  constraint purge_runs_terminal_consistent check (
    (
      status in ('completed', 'failed', 'cancelled')
      and finished_at is not null
      and outcome_code is not null
      and finished_at >= started_at
    )
    or (
      status in ('planned', 'approved', 'running')
      and finished_at is null
      and outcome_code is null
    )
  ),
  constraint purge_runs_outcome_code_safe check (
    outcome_code is null or outcome_code ~ '^[a-z][a-z0-9_.:-]{0,126}$'
  ),
  constraint purge_runs_approved_by_ref_safe check (
    approved_by_ref is null
    or approved_by_ref ~ '^[a-z][a-z0-9_.:-]{0,126}$'
  ),
  constraint purge_runs_executed_by_ref_safe check (
    executed_by_ref is null
    or executed_by_ref ~ '^[a-z][a-z0-9_.:-]{0,126}$'
  ),
  constraint purge_runs_updated_after_created check (
    updated_at >= created_at
  )
);

create index sync_runs_retention_idx
  on public.sync_runs (data_source_id, finished_at)
  where finished_at is not null and status in ('applied', 'failed', 'blocked');

create index schema_change_requests_retention_idx
  on public.schema_change_requests (data_source_id, reviewed_at)
  where status in ('approved', 'rejected') and reviewed_at is not null;

create index purge_runs_executable_idx
  on public.purge_runs (data_source_id, started_at)
  where status in ('planned', 'approved', 'running');

alter table public.retention_holds enable row level security;
alter table public.purge_runs enable row level security;

revoke all privileges on table public.retention_holds
  from public, anon, authenticated, service_role;
revoke all privileges on table public.purge_runs
  from public, anon, authenticated, service_role;

grant select on table public.retention_holds to service_role;
grant select on table public.purge_runs to service_role;

-- Remove privilegios administrativos herdados da baseline e recompõe apenas o
-- contrato usado pelo sincronizador. Lifecycle permanece administrativo.
revoke all privileges on table public.data_sources
  from public, anon, authenticated, service_role;
grant select on table public.data_sources to service_role;
grant insert (name, spreadsheet_id, sheet_name, target_table, business_key)
  on public.data_sources to service_role;
grant update (
  last_sync_at,
  next_sync_at,
  last_attempt_at,
  last_success_at,
  last_failure_at,
  consecutive_failures,
  last_error_code,
  last_error_summary,
  last_duration_ms,
  last_rows_read,
  last_rows_inserted,
  last_rows_updated,
  last_rows_deleted,
  last_rows_restored,
  updated_at
) on public.data_sources to service_role;

revoke all privileges on table public.sync_runs
  from public, anon, authenticated, service_role;
grant select, insert, update on table public.sync_runs to service_role;

revoke all privileges on table public.import_errors
  from public, anon, authenticated, service_role;
grant select, insert on table public.import_errors to service_role;

revoke all privileges on table public.schema_change_requests
  from public, anon, authenticated, service_role;
grant select, insert on table public.schema_change_requests to service_role;
