create table if not exists public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id),
  name text not null,
  created_at timestamptz not null default now()
);

create table if not exists public.data_sources (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.projects(id),
  source_key text not null unique,
  source_type text not null check (source_type in ('google_sheet', 'fixture')),
  created_at timestamptz not null default now()
);

create table if not exists public.sync_runs (
  id uuid primary key default gen_random_uuid(),
  data_source_id uuid references public.data_sources(id),
  status text not null check (status in ('planned', 'applied', 'failed')),
  manifest jsonb not null default '{}'::jsonb,
  started_at timestamptz not null default now(),
  completed_at timestamptz
);

create table if not exists public.raw_import_rows (
  id uuid primary key default gen_random_uuid(),
  sync_run_id uuid references public.sync_runs(id),
  source_id text not null,
  external_key text not null,
  raw_data jsonb not null,
  row_hash text not null,
  deleted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (source_id, external_key)
);

create table if not exists public.import_errors (
  id uuid primary key default gen_random_uuid(),
  sync_run_id uuid references public.sync_runs(id),
  external_key text,
  error_code text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.schema_change_requests (
  id uuid primary key default gen_random_uuid(),
  data_source_id uuid references public.data_sources(id),
  change_type text not null,
  details jsonb not null,
  status text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
  created_at timestamptz not null default now()
);

create table if not exists public.mirror_records (
  id uuid primary key default gen_random_uuid(),
  source_id text not null,
  external_key text not null,
  raw_data jsonb not null,
  row_hash text not null,
  deleted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (source_id, external_key)
);

create index if not exists raw_import_rows_active_idx on public.raw_import_rows (source_id) where deleted_at is null;
create index if not exists mirror_records_active_idx on public.mirror_records (source_id) where deleted_at is null;
create index if not exists sync_runs_source_idx on public.sync_runs (data_source_id, started_at desc);

create or replace view public.active_mirror_records as select * from public.mirror_records where deleted_at is null;
alter table public.organizations enable row level security;
alter table public.projects enable row level security;
alter table public.data_sources enable row level security;
alter table public.sync_runs enable row level security;
alter table public.raw_import_rows enable row level security;
alter table public.import_errors enable row level security;
alter table public.schema_change_requests enable row level security;
alter table public.mirror_records enable row level security;
-- Policies de leitura sao intencionalmente adiadas ate existir o modelo de usuarios/tenancy.
