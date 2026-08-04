-- Arquitetura isolada por instituicao. Esta migration e destinada ao ambiente local novo.
drop view if exists public.active_mirror_records;
drop table if exists public.mirror_records;
drop table if exists public.raw_import_rows;
drop table if exists public.import_errors;
drop table if exists public.schema_change_requests;
drop table if exists public.sync_runs;
drop table if exists public.data_sources;
drop table if exists public.projects;
drop table if exists public.organizations;

create table public.data_sources (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  spreadsheet_id text not null,
  sheet_name text not null,
  source_url text,
  target_table text not null unique check (target_table ~ '^[a-z][a-z0-9_]{0,62}$'),
  business_key jsonb not null,
  sync_interval_minutes integer not null default 180 check (sync_interval_minutes > 0),
  enabled boolean not null default true,
  last_sync_at timestamptz,
  next_sync_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (spreadsheet_id, sheet_name)
);

create table public.sync_runs (
  id uuid primary key default gen_random_uuid(),
  data_source_id uuid not null references public.data_sources(id),
  status text not null check (status in ('planned', 'applied', 'failed', 'blocked')),
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  inserted_rows integer not null default 0,
  updated_rows integer not null default 0,
  deleted_rows integer not null default 0,
  restored_rows integer not null default 0,
  unchanged_rows integer not null default 0,
  error_summary text,
  snapshot_hash text
);

create table public.raw_import_rows (
  id uuid primary key default gen_random_uuid(),
  data_source_id uuid not null references public.data_sources(id),
  sync_run_id uuid not null references public.sync_runs(id),
  source_row_number integer not null,
  row_key_hash text not null,
  content_hash text not null,
  payload_json jsonb not null,
  imported_at timestamptz not null default now()
);

create table public.import_errors (
  id uuid primary key default gen_random_uuid(),
  data_source_id uuid not null references public.data_sources(id),
  sync_run_id uuid references public.sync_runs(id),
  error_type text not null,
  error_message text not null,
  row_number integer,
  payload_json jsonb,
  created_at timestamptz not null default now()
);

create table public.schema_change_requests (
  id uuid primary key default gen_random_uuid(),
  data_source_id uuid not null references public.data_sources(id),
  change_type text not null,
  current_schema jsonb not null,
  proposed_schema jsonb not null,
  status text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
  created_at timestamptz not null default now(),
  reviewed_at timestamptz
);

create index data_sources_due_idx on public.data_sources (next_sync_at) where enabled;
create index sync_runs_source_idx on public.sync_runs (data_source_id, started_at desc);
create index raw_import_rows_source_idx on public.raw_import_rows (data_source_id, imported_at desc);

alter table public.data_sources enable row level security;
alter table public.sync_runs enable row level security;
alter table public.raw_import_rows enable row level security;
alter table public.import_errors enable row level security;
alter table public.schema_change_requests enable row level security;
-- Policies de leitura dependem do mecanismo de acesso do backend da instituicao.
