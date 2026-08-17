-- Migration incremental aditiva do estado raw atual.
-- Nao altera a baseline 20260804000000, ja aplicada e imutavel.
-- Sem operacao destrutiva: nenhuma remocao de tabela, coluna, dado ou renomeacao.
-- Separacao de responsabilidades:
--   public.raw_import_rows  -> historico append-only do que foi observado em cada execucao;
--   public.raw_current_rows -> estado atual unico por fonte e chave de negocio.

create table public.raw_current_rows (
  id uuid primary key default gen_random_uuid(),
  data_source_id uuid not null references public.data_sources(id),
  row_key_hash text not null,
  content_hash text not null,
  payload_json jsonb not null,
  source_row_number integer,
  is_deleted boolean not null default false,
  version integer not null default 1,
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  deleted_at timestamptz,
  last_sync_run_id uuid references public.sync_runs(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint raw_current_rows_source_key_unique unique (data_source_id, row_key_hash),
  constraint raw_current_rows_key_hash_present check (char_length(row_key_hash) > 0),
  constraint raw_current_rows_content_hash_present check (char_length(content_hash) > 0),
  constraint raw_current_rows_version_positive check (version > 0),
  constraint raw_current_rows_source_row_number_positive check (
    source_row_number is null or source_row_number > 0
  ),
  constraint raw_current_rows_tombstone_consistent check (
    (is_deleted and deleted_at is not null) or (not is_deleted and deleted_at is null)
  ),
  constraint raw_current_rows_seen_window_ordered check (last_seen_at >= first_seen_at),
  constraint raw_current_rows_updated_after_created check (updated_at >= created_at),
  constraint raw_current_rows_deleted_after_first_seen check (
    deleted_at is null or deleted_at >= first_seen_at
  )
);

-- Consulta justificadora: varredura do estado ativo de uma fonte e deteccao de linhas
-- nao observadas na ultima execucao.
--   select row_key_hash, content_hash from public.raw_current_rows
--   where data_source_id = $1 and not is_deleted order by last_seen_at desc;
create index raw_current_rows_active_idx
  on public.raw_current_rows (data_source_id, last_seen_at desc)
  where not is_deleted;

-- Consulta justificadora: inventario de tombstones de uma fonte para retencao,
-- restauracao e procedimento LGPD.
--   select row_key_hash, deleted_at from public.raw_current_rows
--   where data_source_id = $1 and is_deleted order by deleted_at desc;
create index raw_current_rows_tombstone_idx
  on public.raw_current_rows (data_source_id, deleted_at desc)
  where is_deleted;

-- Consulta justificadora: reconciliacao das linhas afetadas por uma execucao.
--   select row_key_hash, version from public.raw_current_rows where last_sync_run_id = $1;
create index raw_current_rows_last_run_idx
  on public.raw_current_rows (last_sync_run_id);

alter table public.raw_current_rows enable row level security;

-- O ambiente Supabase pode conceder privilegios padrao amplos a tabelas novas.
-- Esta tabela tem contrato proprio de menor privilegio, independente desses defaults.
revoke all privileges on table public.raw_current_rows from public, anon, authenticated, service_role;

-- O backend recebe apenas leitura, insercao e atualizacao: a exclusao nesta camada
-- e sempre logica e qualquer remocao fisica exige procedimento revisado por humano.
grant select, insert, update on table public.raw_current_rows to service_role;

-- Classificacao aditiva do historico append-only. Ambas as colunas sao opcionais,
-- portanto compativeis com a baseline aplicada e com um banco sem dados.
-- Eventos de exclusao nao sao observados na planilha e continuam representados
-- apenas em public.raw_current_rows e nos contadores de public.sync_runs, porque a
-- unicidade (sync_run_id, source_row_number) da baseline nao pode representar uma
-- linha ausente sem risco de colisao.
alter table public.raw_import_rows add column change_type text;

alter table public.raw_import_rows add column row_version integer;

alter table public.raw_import_rows
  add constraint raw_import_rows_change_type_valid check (
    change_type is null or change_type in ('inserted', 'changed', 'restored', 'unchanged')
  );

alter table public.raw_import_rows
  add constraint raw_import_rows_row_version_positive check (
    row_version is null or row_version > 0
  );
