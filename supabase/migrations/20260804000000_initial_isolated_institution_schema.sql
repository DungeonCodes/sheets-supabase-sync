create table public.data_sources (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  spreadsheet_id text not null,
  sheet_name text not null,
  source_url text,
  target_table text not null unique,
  business_key jsonb not null,
  sync_interval_minutes integer not null default 180,
  enabled boolean not null default true,
  last_sync_at timestamptz,
  next_sync_at timestamptz,
  last_attempt_at timestamptz,
  last_success_at timestamptz,
  last_failure_at timestamptz,
  consecutive_failures integer not null default 0,
  last_error_code text,
  last_error_summary text,
  last_duration_ms integer,
  last_rows_read integer,
  last_rows_inserted integer,
  last_rows_updated integer,
  last_rows_deleted integer,
  last_rows_restored integer,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint data_sources_sheet_unique unique (spreadsheet_id, sheet_name),
  constraint data_sources_target_table_format check (target_table ~ '^[a-z][a-z0-9_]{0,62}$'),
  constraint data_sources_business_key_array check (jsonb_typeof(business_key) = 'array' and jsonb_array_length(business_key) > 0),
  constraint data_sources_sync_interval_positive check (sync_interval_minutes > 0),
  constraint data_sources_failures_nonnegative check (consecutive_failures >= 0),
  constraint data_sources_metrics_nonnegative check (
    (last_duration_ms is null or last_duration_ms >= 0) and
    (last_rows_read is null or last_rows_read >= 0) and
    (last_rows_inserted is null or last_rows_inserted >= 0) and
    (last_rows_updated is null or last_rows_updated >= 0) and
    (last_rows_deleted is null or last_rows_deleted >= 0) and
    (last_rows_restored is null or last_rows_restored >= 0)
  )
);

create table public.sync_runs (
  id uuid primary key default gen_random_uuid(),
  data_source_id uuid not null references public.data_sources(id),
  status text not null,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  inserted_rows integer not null default 0,
  updated_rows integer not null default 0,
  deleted_rows integer not null default 0,
  restored_rows integer not null default 0,
  unchanged_rows integer not null default 0,
  error_summary text,
  snapshot_hash text,
  schema_metadata jsonb not null default '{}'::jsonb,
  constraint sync_runs_status_valid check (status in ('planned', 'running', 'applied', 'failed', 'blocked')),
  constraint sync_runs_counts_nonnegative check (
    inserted_rows >= 0 and updated_rows >= 0 and deleted_rows >= 0 and
    restored_rows >= 0 and unchanged_rows >= 0
  ),
  constraint sync_runs_finished_after_start check (finished_at is null or finished_at >= started_at)
);

create table public.raw_import_rows (
  id uuid primary key default gen_random_uuid(),
  data_source_id uuid not null references public.data_sources(id),
  sync_run_id uuid not null references public.sync_runs(id),
  source_row_number integer not null,
  row_key_hash text not null,
  content_hash text not null,
  payload_json jsonb not null,
  imported_at timestamptz not null default now(),
  constraint raw_import_rows_number_positive check (source_row_number > 0),
  constraint raw_import_rows_run_row_unique unique (sync_run_id, source_row_number)
);

create table public.import_errors (
  id uuid primary key default gen_random_uuid(),
  data_source_id uuid not null references public.data_sources(id),
  sync_run_id uuid references public.sync_runs(id),
  error_type text not null,
  error_message text not null,
  row_number integer,
  payload_json jsonb,
  created_at timestamptz not null default now(),
  constraint import_errors_row_number_positive check (row_number is null or row_number > 0)
);

create table public.schema_change_requests (
  id uuid primary key default gen_random_uuid(),
  data_source_id uuid not null references public.data_sources(id),
  change_type text not null,
  current_schema jsonb not null,
  proposed_schema jsonb not null,
  status text not null default 'pending',
  created_at timestamptz not null default now(),
  reviewed_at timestamptz,
  constraint schema_change_requests_status_valid check (status in ('pending', 'approved', 'rejected')),
  constraint schema_change_requests_reviewed_consistent check (
    (status = 'pending' and reviewed_at is null) or
    (status in ('approved', 'rejected') and reviewed_at is not null)
  )
);

create index data_sources_due_idx
  on public.data_sources (next_sync_at)
  where enabled;

create index sync_runs_source_started_idx
  on public.sync_runs (data_source_id, started_at desc);

create index raw_import_rows_source_imported_idx
  on public.raw_import_rows (data_source_id, imported_at desc);

create index import_errors_source_created_idx
  on public.import_errors (data_source_id, created_at desc);

create index schema_change_requests_pending_idx
  on public.schema_change_requests (data_source_id, created_at desc)
  where status = 'pending';

alter table public.data_sources enable row level security;
alter table public.sync_runs enable row level security;
alter table public.raw_import_rows enable row level security;
alter table public.import_errors enable row level security;
alter table public.schema_change_requests enable row level security;

revoke all on table public.data_sources from anon, authenticated;
revoke all on table public.sync_runs from anon, authenticated;
revoke all on table public.raw_import_rows from anon, authenticated;
revoke all on table public.import_errors from anon, authenticated;
revoke all on table public.schema_change_requests from anon, authenticated;

grant all on table public.data_sources to service_role;
grant all on table public.sync_runs to service_role;
grant all on table public.raw_import_rows to service_role;
grant all on table public.import_errors to service_role;
grant all on table public.schema_change_requests to service_role;
