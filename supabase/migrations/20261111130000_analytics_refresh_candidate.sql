-- REVIEW REQUIRED: candidate only. Do not apply without human SQL review.
-- Each source is explicitly enrolled and categories are curated per source.
create table analytics.category_allowlist (
  source_key bigint not null references analytics.dim_source(source_key),
  normalized_category text not null,
  category_label text not null,
  category_code text not null,
  primary key (source_key, normalized_category),
  check (normalized_category = lower(btrim(normalized_category)) and normalized_category <> ''),
  check (length(btrim(category_label)) > 0),
  check (category_code ~ '^[a-z0-9][a-z0-9_-]{0,62}$')
);

alter table analytics.category_allowlist enable row level security;
revoke all on analytics.category_allowlist from public, anon, authenticated, service_role;
grant select on analytics.category_allowlist to service_role;

-- Caller must use REPEATABLE READ or SERIALIZABLE; a validation failure aborts
-- the whole transaction and preserves the last committed analytical snapshot.
create function analytics.refresh_category_score(p_data_source_id uuid)
returns void language plpgsql security invoker set search_path = pg_catalog, analytics, public as $$
declare
  v_source_key bigint;
  v_raw_count bigint;
  v_fact_count bigint;
begin
  if current_setting('transaction_isolation') not in ('repeatable read', 'serializable') then
    raise exception 'analytics requires a stable transaction snapshot';
  end if;
  select source_key into strict v_source_key from analytics.dim_source
   where data_source_id = p_data_source_id and semantic_contract_version = 'category_score_v1'
   for update;
  if exists (
    select 1 from public.raw_current_rows r
    left join analytics.category_allowlist a on a.source_key = v_source_key
      and a.normalized_category = lower(btrim(r.payload_json->>'categoria'))
    where r.data_source_id = p_data_source_id and not r.is_deleted and (
      r.row_key_hash !~ '^[0-9a-f]{64}$' or a.source_key is null or
      coalesce(r.payload_json->>'pontuacao', '') !~ '^-?[0-9]+([.][0-9]+)?$'
    )
  ) then
    raise exception 'invalid analytical source data';
  end if;
  insert into analytics.dim_category(source_key, normalized_category, category_label, category_code)
  select distinct v_source_key, a.normalized_category, a.category_label, a.category_code
  from public.raw_current_rows r
  join analytics.category_allowlist a on a.source_key = v_source_key
    and a.normalized_category = lower(btrim(r.payload_json->>'categoria'))
  where r.data_source_id = p_data_source_id and not r.is_deleted
  on conflict (source_key, normalized_category) do update
    set category_label = excluded.category_label, category_code = excluded.category_code
    where (analytics.dim_category.category_label, analytics.dim_category.category_code)
      is distinct from (excluded.category_label, excluded.category_code);

  insert into analytics.fact_category_score(source_key, category_key, source_record_key, score_value, is_current)
  select v_source_key, c.category_key, r.row_key_hash, (r.payload_json->>'pontuacao')::numeric, true
  from public.raw_current_rows r
  join analytics.dim_category c on c.source_key = v_source_key
    and c.normalized_category = lower(btrim(r.payload_json->>'categoria'))
  where r.data_source_id = p_data_source_id and not r.is_deleted
  on conflict (source_key, source_record_key) do update
    set category_key = excluded.category_key, score_value = excluded.score_value, is_current = true
    where (analytics.fact_category_score.category_key, analytics.fact_category_score.score_value, analytics.fact_category_score.is_current)
      is distinct from (excluded.category_key, excluded.score_value, true);

  update analytics.fact_category_score f set is_current = false
   where f.source_key = v_source_key and f.is_current and not exists (
     select 1 from public.raw_current_rows r where r.data_source_id = p_data_source_id
       and r.row_key_hash = f.source_record_key and not r.is_deleted
   );
  select count(*) into v_raw_count from public.raw_current_rows
   where data_source_id = p_data_source_id and not is_deleted;
  select count(*) into v_fact_count from analytics.fact_category_score
   where source_key = v_source_key and is_current;
  if v_raw_count <> v_fact_count then
    raise exception 'analytical reconciliation failed';
  end if;
end;
$$;
revoke all on function analytics.refresh_category_score(uuid) from public, anon, authenticated;
grant execute on function analytics.refresh_category_score(uuid) to service_role;
