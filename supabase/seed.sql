insert into public.data_sources (name, spreadsheet_id, sheet_name, target_table, business_key, sync_interval_minutes)
values ('pesquisa-satisfacao', 'fixture', 'Respostas', 'pesquisa_satisfacao', '["id_resposta"]'::jsonb, 180)
on conflict (name) do nothing;
