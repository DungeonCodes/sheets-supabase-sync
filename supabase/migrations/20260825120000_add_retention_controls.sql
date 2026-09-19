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

-- Referencia central para guards administrativos. Nao recebe payload, nao usa
-- SQL dinamico e permanece SECURITY INVOKER.
create function public.retention_hold_applies(target_data_source_id uuid)
returns boolean
language sql
stable
set search_path = pg_catalog, public
as $$
  select exists (
    select 1
    from public.retention_holds
    where released_at is null
      and (
        scope = 'institution'
        or (scope = 'source' and data_source_id = target_data_source_id)
      )
  );
$$;

-- Todas as operacoes administrativas conflitantes usam primeiro este lock
-- institucional e, depois, o lock da fonte. O namespace e separado do lock
-- operacional de sincronizacao.
create function public.acquire_retention_locks(target_data_source_id uuid)
returns void
language plpgsql
set search_path = pg_catalog, public
as $$
begin
  perform pg_advisory_xact_lock(
    hashtextextended('sheets-supabase-sync:retention:institution', 0)
  );

  if target_data_source_id is not null then
    perform pg_advisory_xact_lock(
      hashtextextended(
        'sheets-supabase-sync:retention:source:' || target_data_source_id::text,
        0
      )
    );
  end if;
end;
$$;

create function public.guard_sync_run_lifecycle()
returns trigger
language plpgsql
set search_path = pg_catalog, public
as $$
declare
  source_is_syncable boolean;
begin
  select enabled and lifecycle_status = 'active'
  into source_is_syncable
  from public.data_sources
  where id = new.data_source_id
  for share;

  if source_is_syncable is distinct from true then
    raise exception using
      errcode = '23514',
      message = 'data source is not synchronizable';
  end if;

  return new;
end;
$$;

create trigger sync_runs_lifecycle_guard
before insert on public.sync_runs
for each row
execute function public.guard_sync_run_lifecycle();

create function public.guard_data_source_hold()
returns trigger
language plpgsql
set search_path = pg_catalog, public
as $$
begin
  if tg_op = 'DELETE' then
    perform public.acquire_retention_locks(old.id);
    if public.retention_hold_applies(old.id) then
      raise exception using
        errcode = '23514',
        message = 'active retention hold blocks data source deletion';
    end if;
    return old;
  end if;

  if new.lifecycle_status in ('offboarding', 'retired')
      and new.lifecycle_status is distinct from old.lifecycle_status then
    perform public.acquire_retention_locks(old.id);
    if public.retention_hold_applies(old.id) then
      raise exception using
        errcode = '23514',
        message = 'active retention hold blocks destructive lifecycle transition';
    end if;
  end if;

  return new;
end;
$$;

create trigger data_sources_hold_lifecycle_guard
before update of lifecycle_status on public.data_sources
for each row
execute function public.guard_data_source_hold();

create trigger data_sources_hold_delete_guard
before delete on public.data_sources
for each row
execute function public.guard_data_source_hold();

-- Historico, erros, requests, current e runs nao podem ser removidos por um
-- caminho administrativo direto enquanto houver hold aplicavel.
create function public.guard_retention_hold_delete()
returns trigger
language plpgsql
set search_path = pg_catalog, public
as $$
begin
  perform public.acquire_retention_locks(old.data_source_id);
  if public.retention_hold_applies(old.data_source_id) then
    raise exception using
      errcode = '23514',
      message = 'active retention hold blocks destructive record deletion';
  end if;
  return old;
end;
$$;

create trigger raw_import_rows_hold_delete_guard
before delete on public.raw_import_rows
for each row
execute function public.guard_retention_hold_delete();

create trigger raw_current_rows_hold_delete_guard
before delete on public.raw_current_rows
for each row
execute function public.guard_retention_hold_delete();

create trigger import_errors_hold_delete_guard
before delete on public.import_errors
for each row
execute function public.guard_retention_hold_delete();

create trigger schema_change_requests_hold_delete_guard
before delete on public.schema_change_requests
for each row
execute function public.guard_retention_hold_delete();

create trigger sync_runs_hold_delete_guard
before delete on public.sync_runs
for each row
execute function public.guard_retention_hold_delete();

-- TRUNCATE nao percorre triggers de linha; qualquer hold ativo bloqueia a
-- remocao em massa das tabelas operacionais protegidas.
create function public.guard_retention_hold_truncate()
returns trigger
language plpgsql
set search_path = pg_catalog, public
as $$
begin
  perform public.acquire_retention_locks(null);
  if exists (
    select 1 from public.retention_holds where released_at is null
  ) then
    raise exception using
      errcode = '23514',
      message = 'active retention hold blocks truncate';
  end if;
  return null;
end;
$$;

create trigger data_sources_hold_truncate_guard
before truncate on public.data_sources
for each statement
execute function public.guard_retention_hold_truncate();

create trigger sync_runs_hold_truncate_guard
before truncate on public.sync_runs
for each statement
execute function public.guard_retention_hold_truncate();

create trigger raw_import_rows_hold_truncate_guard
before truncate on public.raw_import_rows
for each statement
execute function public.guard_retention_hold_truncate();

create trigger raw_current_rows_hold_truncate_guard
before truncate on public.raw_current_rows
for each statement
execute function public.guard_retention_hold_truncate();

create trigger import_errors_hold_truncate_guard
before truncate on public.import_errors
for each statement
execute function public.guard_retention_hold_truncate();

create trigger schema_change_requests_hold_truncate_guard
before truncate on public.schema_change_requests
for each statement
execute function public.guard_retention_hold_truncate();

-- Evidencia administrativa nao faz parte de um mecanismo de limpeza em massa.
create function public.guard_administrative_evidence_truncate()
returns trigger
language plpgsql
set search_path = pg_catalog, public
as $$
begin
  perform public.acquire_retention_locks(null);
  raise exception using
    errcode = '23514',
    message = 'administrative retention evidence cannot be truncated';
end;
$$;

create trigger retention_holds_evidence_truncate_guard
before truncate on public.retention_holds
for each statement
execute function public.guard_administrative_evidence_truncate();

create function public.guard_released_retention_hold()
returns trigger
language plpgsql
set search_path = pg_catalog, public
as $$
begin
  if tg_op = 'INSERT' then
    perform public.acquire_retention_locks(new.data_source_id);
    return new;
  end if;

  perform public.acquire_retention_locks(coalesce(new.data_source_id, old.data_source_id));

  if old.released_at is null and new.released_at is not null then
    if new.id is distinct from old.id
        or new.scope is distinct from old.scope
        or new.data_source_id is distinct from old.data_source_id
        or new.source_ref is distinct from old.source_ref
        or new.reason_code is distinct from old.reason_code
        or new.activated_at is distinct from old.activated_at
        or new.activated_by_ref is distinct from old.activated_by_ref then
      raise exception using
        errcode = '23514',
        message = 'retention hold release cannot rewrite activation evidence';
    end if;
    return new;
  end if;

  if old.released_at is not null and not (
    old.data_source_id is not null
    and new.data_source_id is null
    and new.id is not distinct from old.id
    and new.scope is not distinct from old.scope
    and new.source_ref is not distinct from old.source_ref
    and new.reason_code is not distinct from old.reason_code
    and new.activated_at is not distinct from old.activated_at
    and new.activated_by_ref is not distinct from old.activated_by_ref
    and new.released_at is not distinct from old.released_at
    and new.released_by_ref is not distinct from old.released_by_ref
    and new.release_reason_code is not distinct from old.release_reason_code
  ) then
    raise exception using
      errcode = '23514',
      message = 'released retention hold evidence is immutable';
  end if;

  return new;
end;
$$;

create trigger retention_holds_released_immutable_guard
before insert or update on public.retention_holds
for each row
execute function public.guard_released_retention_hold();

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
  raw_import_rows_cutoff timestamptz,
  sync_runs_cutoff timestamptz,
  import_errors_cutoff timestamptz,
  schema_change_requests_cutoff timestamptz,
  candidate_data_sources bigint not null default 0,
  candidate_raw_import_rows bigint not null default 0,
  candidate_raw_current_rows bigint not null default 0,
  candidate_sync_runs bigint not null default 0,
  candidate_import_errors bigint not null default 0,
  candidate_schema_change_requests bigint not null default 0,
  affected_data_sources bigint not null default 0,
  affected_raw_import_rows bigint not null default 0,
  affected_raw_current_rows bigint not null default 0,
  affected_sync_runs bigint not null default 0,
  affected_import_errors bigint not null default 0,
  affected_schema_change_requests bigint not null default 0,
  outcome_code text,
  approved_at timestamptz,
  approved_by_ref text,
  started_at timestamptz,
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
  constraint purge_runs_candidate_counts_nonnegative check (
    candidate_data_sources >= 0
    and candidate_raw_import_rows >= 0
    and candidate_raw_current_rows >= 0
    and candidate_sync_runs >= 0
    and candidate_import_errors >= 0
    and candidate_schema_change_requests >= 0
  ),
  constraint purge_runs_affected_counts_nonnegative check (
    affected_data_sources >= 0
    and affected_raw_import_rows >= 0
    and affected_raw_current_rows >= 0
    and affected_sync_runs >= 0
    and affected_import_errors >= 0
    and affected_schema_change_requests >= 0
  ),
  constraint purge_runs_dry_run_has_no_effect check (
    not dry_run or (
      affected_data_sources = 0
      and affected_raw_import_rows = 0
      and affected_raw_current_rows = 0
      and affected_sync_runs = 0
      and affected_import_errors = 0
      and affected_schema_change_requests = 0
    )
  ),
  constraint purge_runs_approval_pair_consistent check (
    (approved_at is null and approved_by_ref is null)
    or (approved_at is not null and approved_by_ref is not null)
  ),
  constraint purge_runs_finished_status_consistent check (
    (
      status in ('completed', 'failed', 'cancelled')
      and finished_at is not null
      and outcome_code is not null
    )
    or (
      status in ('planned', 'approved', 'running')
      and finished_at is null
      and outcome_code is null
    )
  ),
  constraint purge_runs_finished_after_start check (
    finished_at is null
    or finished_at >= coalesce(started_at, created_at)
  ),
  constraint purge_runs_approval_before_start check (
    approved_at is null
    or started_at is null
    or approved_at <= started_at
  ),
  constraint purge_runs_approval_before_finish check (
    approved_at is null
    or finished_at is null
    or approved_at <= finished_at
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

create function public.guard_purge_run()
returns trigger
language plpgsql
set search_path = pg_catalog, public
as $$
begin
  if tg_op = 'INSERT' and not new.dry_run then
    perform public.acquire_retention_locks(new.data_source_id);
  elsif tg_op = 'UPDATE' and not coalesce(new.dry_run, old.dry_run) then
    perform public.acquire_retention_locks(coalesce(new.data_source_id, old.data_source_id));
  end if;

  if tg_op = 'INSERT' then
    if new.status <> 'planned' then
      raise exception using errcode = '23514', message = 'purge run must start planned';
    end if;
    if not new.dry_run and new.data_source_id is null then
      raise exception using errcode = '23514', message = 'destructive purge run requires source';
    end if;
  else
    if old.status in ('completed', 'failed', 'cancelled') then
      if old.data_source_id is not null
          and new.data_source_id is null
          and new.id is not distinct from old.id
          and new.source_ref is not distinct from old.source_ref
          and new.run_type is not distinct from old.run_type
          and new.status is not distinct from old.status
          and new.dry_run is not distinct from old.dry_run
          and new.policy_ref is not distinct from old.policy_ref
          and new.policy_version is not distinct from old.policy_version
          and new.policy_digest is not distinct from old.policy_digest
          and new.dry_run_digest is not distinct from old.dry_run_digest
          and new.raw_import_rows_cutoff is not distinct from old.raw_import_rows_cutoff
          and new.sync_runs_cutoff is not distinct from old.sync_runs_cutoff
          and new.import_errors_cutoff is not distinct from old.import_errors_cutoff
          and new.schema_change_requests_cutoff is not distinct from old.schema_change_requests_cutoff
          and new.candidate_data_sources is not distinct from old.candidate_data_sources
          and new.candidate_raw_import_rows is not distinct from old.candidate_raw_import_rows
          and new.candidate_raw_current_rows is not distinct from old.candidate_raw_current_rows
          and new.candidate_sync_runs is not distinct from old.candidate_sync_runs
          and new.candidate_import_errors is not distinct from old.candidate_import_errors
          and new.candidate_schema_change_requests is not distinct from old.candidate_schema_change_requests
          and new.affected_data_sources is not distinct from old.affected_data_sources
          and new.affected_raw_import_rows is not distinct from old.affected_raw_import_rows
          and new.affected_raw_current_rows is not distinct from old.affected_raw_current_rows
          and new.affected_sync_runs is not distinct from old.affected_sync_runs
          and new.affected_import_errors is not distinct from old.affected_import_errors
          and new.affected_schema_change_requests is not distinct from old.affected_schema_change_requests
          and new.outcome_code is not distinct from old.outcome_code
          and new.approved_at is not distinct from old.approved_at
          and new.approved_by_ref is not distinct from old.approved_by_ref
          and new.started_at is not distinct from old.started_at
          and new.finished_at is not distinct from old.finished_at
          and new.executed_by_ref is not distinct from old.executed_by_ref
          and new.hold_checked_at is not distinct from old.hold_checked_at
          and new.created_at is not distinct from old.created_at
          and new.updated_at is not distinct from old.updated_at then
        return new;
      end if;
      raise exception using errcode = '23514', message = 'terminal purge evidence is immutable';
    end if;

    if not new.dry_run and new.data_source_id is null then
      raise exception using errcode = '23514', message = 'destructive purge run requires source';
    end if;

    if old.status <> new.status then
      if old.status = 'planned' and (
        (old.dry_run and new.status in ('running', 'failed', 'cancelled'))
        or (not old.dry_run and new.status in ('approved', 'failed', 'cancelled'))
      ) then
        null;
      elsif old.status = 'approved' and new.status in ('running', 'failed', 'cancelled') then
        null;
      elsif old.status = 'running' and new.status in ('completed', 'failed', 'cancelled') then
        null;
      else
        raise exception using errcode = '23514', message = 'invalid purge run status transition';
      end if;
    end if;

    if old.status <> 'planned' and (
      new.source_ref is distinct from old.source_ref
      or new.run_type is distinct from old.run_type
      or new.dry_run is distinct from old.dry_run
      or new.policy_ref is distinct from old.policy_ref
      or new.policy_version is distinct from old.policy_version
      or new.policy_digest is distinct from old.policy_digest
      or new.dry_run_digest is distinct from old.dry_run_digest
      or new.raw_import_rows_cutoff is distinct from old.raw_import_rows_cutoff
      or new.sync_runs_cutoff is distinct from old.sync_runs_cutoff
      or new.import_errors_cutoff is distinct from old.import_errors_cutoff
      or new.schema_change_requests_cutoff is distinct from old.schema_change_requests_cutoff
      or new.candidate_data_sources is distinct from old.candidate_data_sources
      or new.candidate_raw_import_rows is distinct from old.candidate_raw_import_rows
      or new.candidate_raw_current_rows is distinct from old.candidate_raw_current_rows
      or new.candidate_sync_runs is distinct from old.candidate_sync_runs
      or new.candidate_import_errors is distinct from old.candidate_import_errors
      or new.candidate_schema_change_requests is distinct from old.candidate_schema_change_requests
      or new.approved_at is distinct from old.approved_at
      or new.approved_by_ref is distinct from old.approved_by_ref
    ) then
      raise exception using errcode = '23514', message = 'approved purge context is immutable';
    end if;

    if old.status = 'planned'
        and new.status in ('failed', 'cancelled')
        and new.approved_at is not null then
      raise exception using
        errcode = '23514',
        message = 'pre-execution terminal cannot add approval outside approved status';
    end if;

    if old.status = 'running' and (
      new.started_at is distinct from old.started_at
      or new.executed_by_ref is distinct from old.executed_by_ref
      or new.hold_checked_at is distinct from old.hold_checked_at
    ) then
      raise exception using
        errcode = '23514',
        message = 'running execution evidence is immutable';
    end if;
  end if;

  if new.status = 'planned' and (
    new.approved_at is not null
    or new.approved_by_ref is not null
    or new.started_at is not null
    or new.executed_by_ref is not null
    or new.hold_checked_at is not null
    or new.affected_data_sources <> 0
    or new.affected_raw_import_rows <> 0
    or new.affected_raw_current_rows <> 0
    or new.affected_sync_runs <> 0
    or new.affected_import_errors <> 0
    or new.affected_schema_change_requests <> 0
  ) then
    raise exception using errcode = '23514', message = 'planned purge run cannot contain execution evidence';
  end if;

  if new.status = 'approved' and (
    new.dry_run
    or new.approved_at is null
    or new.approved_by_ref is null
    or new.started_at is not null
    or new.executed_by_ref is not null
    or new.hold_checked_at is not null
    or new.affected_data_sources <> 0
    or new.affected_raw_import_rows <> 0
    or new.affected_raw_current_rows <> 0
    or new.affected_sync_runs <> 0
    or new.affected_import_errors <> 0
    or new.affected_schema_change_requests <> 0
  ) then
    raise exception using errcode = '23514', message = 'approved purge run is inconsistent';
  end if;

  if new.status = 'running' and (
    new.started_at is null
    or new.executed_by_ref is null
    or new.hold_checked_at is null
  ) then
    raise exception using errcode = '23514', message = 'running purge run requires start, executor and hold check';
  end if;

  if new.status = 'completed' and (
    new.started_at is null
    or new.executed_by_ref is null
    or new.hold_checked_at is null
  ) then
    raise exception using errcode = '23514', message = 'completed purge run requires execution evidence';
  end if;

  if new.status in ('failed', 'cancelled') and new.started_at is null and (
    new.executed_by_ref is not null
    or new.hold_checked_at is not null
    or new.affected_data_sources <> 0
    or new.affected_raw_import_rows <> 0
    or new.affected_raw_current_rows <> 0
    or new.affected_sync_runs <> 0
    or new.affected_import_errors <> 0
    or new.affected_schema_change_requests <> 0
  ) then
    raise exception using errcode = '23514', message = 'pre-execution terminal cannot contain execution evidence';
  end if;

  if new.status in ('failed', 'cancelled') and new.started_at is not null and (
    new.executed_by_ref is null
    or new.hold_checked_at is null
  ) then
    raise exception using errcode = '23514', message = 'executed terminal requires executor and hold check';
  end if;

  -- O executor futuro e transacional: falha ou cancelamento nao pode alegar
  -- efeito persistido depois do rollback da unidade destrutiva.
  if new.status in ('failed', 'cancelled') and (
    new.affected_data_sources <> 0
    or new.affected_raw_import_rows <> 0
    or new.affected_raw_current_rows <> 0
    or new.affected_sync_runs <> 0
    or new.affected_import_errors <> 0
    or new.affected_schema_change_requests <> 0
  ) then
    raise exception using errcode = '23514', message = 'failed or cancelled purge run cannot contain affected counts';
  end if;

  if new.dry_run and (
    new.affected_data_sources <> 0
    or new.affected_raw_import_rows <> 0
    or new.affected_raw_current_rows <> 0
    or new.affected_sync_runs <> 0
    or new.affected_import_errors <> 0
    or new.affected_schema_change_requests <> 0
  ) then
    raise exception using errcode = '23514', message = 'dry run cannot contain affected counts';
  end if;

  if not new.dry_run and new.started_at is not null and (
    new.approved_at is null
    or new.approved_by_ref is null
    or new.hold_checked_at < new.approved_at
    or new.hold_checked_at > new.started_at
  ) then
    raise exception using errcode = '23514', message = 'destructive execution requires prior approval and hold check';
  end if;

  if not new.dry_run
      and new.status in ('approved', 'running', 'completed')
      and public.retention_hold_applies(new.data_source_id) then
    raise exception using errcode = '23514', message = 'active retention hold blocks destructive purge run';
  end if;

  return new;
end;
$$;

create trigger purge_runs_guard
before insert or update on public.purge_runs
for each row
execute function public.guard_purge_run();

create trigger purge_runs_evidence_truncate_guard
before truncate on public.purge_runs
for each statement
execute function public.guard_administrative_evidence_truncate();

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

-- As funcoes sao internas aos guards e nao formam API para papeis operacionais.
revoke all privileges on function public.retention_hold_applies(uuid)
  from public, anon, authenticated, service_role;
revoke all privileges on function public.acquire_retention_locks(uuid)
  from public, anon, authenticated, service_role;
revoke all privileges on function public.guard_sync_run_lifecycle()
  from public, anon, authenticated, service_role;
revoke all privileges on function public.guard_data_source_hold()
  from public, anon, authenticated, service_role;
revoke all privileges on function public.guard_retention_hold_delete()
  from public, anon, authenticated, service_role;
revoke all privileges on function public.guard_released_retention_hold()
  from public, anon, authenticated, service_role;
revoke all privileges on function public.guard_retention_hold_truncate()
  from public, anon, authenticated, service_role;
revoke all privileges on function public.guard_administrative_evidence_truncate()
  from public, anon, authenticated, service_role;
revoke all privileges on function public.guard_purge_run()
  from public, anon, authenticated, service_role;

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
