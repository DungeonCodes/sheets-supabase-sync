-- Evolui o historico raw para eventos de negocio, sem alterar migrations aplicadas.
-- O staging foi confirmado vazio antes deste gate. A precondicao explicita evita
-- converter silenciosamente observacoes antigas para a nova semantica.

do $$
begin
  if exists (select 1 from public.raw_import_rows) then
    raise exception 'raw_import_rows precisa estar vazio para migracao event-only';
  end if;
end
$$;

alter table public.raw_import_rows
  drop constraint raw_import_rows_run_row_unique,
  drop constraint raw_import_rows_number_positive,
  drop constraint raw_import_rows_change_type_valid;

alter table public.raw_import_rows
  alter column source_row_number drop not null,
  alter column content_hash drop not null,
  alter column payload_json drop not null,
  alter column change_type set not null,
  alter column row_version set not null;

alter table public.raw_import_rows
  add constraint raw_import_rows_event_identity_unique
    unique (sync_run_id, data_source_id, row_key_hash),
  add constraint raw_import_rows_key_hash_present
    check (char_length(row_key_hash) > 0),
  add constraint raw_import_rows_change_type_valid
    check (change_type in ('insert', 'update', 'tombstone', 'restore')),
  add constraint raw_import_rows_source_row_number_positive
    check (source_row_number is null or source_row_number > 0),
  add constraint raw_import_rows_event_payload_consistent
    check (
      (
        change_type = 'tombstone'
        and source_row_number is null
        and content_hash is null
        and payload_json is null
      )
      or
      (
        change_type in ('insert', 'update', 'restore')
        and source_row_number is not null
        and char_length(content_hash) > 0
        and payload_json is not null
      )
    );

revoke all privileges on table public.raw_import_rows
  from public, anon, authenticated, service_role;
grant select, insert on table public.raw_import_rows to service_role;
