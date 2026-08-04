alter table public.data_sources
  add column if not exists last_attempt_at timestamptz,
  add column if not exists last_success_at timestamptz,
  add column if not exists last_failure_at timestamptz,
  add column if not exists consecutive_failures integer not null default 0,
  add column if not exists last_error_code text,
  add column if not exists last_error_summary text,
  add column if not exists last_duration_ms integer,
  add column if not exists last_rows_read integer,
  add column if not exists last_rows_inserted integer,
  add column if not exists last_rows_updated integer,
  add column if not exists last_rows_deleted integer,
  add column if not exists last_rows_restored integer;

-- O executor local deve adquirir pg_try_advisory_xact_lock(hashtextextended(data_source_id::text, 0))
-- antes de aplicar uma sincronizacao. A trava e liberada no fim da transacao.
