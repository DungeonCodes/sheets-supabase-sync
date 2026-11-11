import 'server-only';
import { Client } from 'pg';
import { headers } from 'next/headers';
import { hasAccess } from './auth';

export type Category = { name: string; count: number; average: number; minimum: number; maximum: number };
export type DashboardData = { mode: 'demo' | 'postgres'; source: string; active: boolean; records: number; failures: number; lastSync: string; executor: string; categoryOptions: string[]; categories: Category[]; history: { label: string; status: string }[] };

const fixture: DashboardData = {
  mode: 'demo', source: 'Fonte demonstrativa', active: true, records: 8, failures: 1, lastSync: '21 out · 14:30', executor: 'Aguardando', categoryOptions:['Categoria X','Categoria Y','Categoria Z'],
  categories: [
    {name:'Categoria X',count:4,average:8.5,minimum:7,maximum:10},
    {name:'Categoria Y',count:3,average:7.3,minimum:6,maximum:9},
    {name:'Categoria Z',count:1,average:9,minimum:9,maximum:9},
  ],
  history: [{label:'Hoje · 14:30',status:'Concluída'},{label:'Hoje · 11:30',status:'Sem alterações'},{label:'Ontem · 17:30',status:'Falha parcial'}],
};

export function filterDemo(category: string): DashboardData {
  return {...fixture, categories: category ? fixture.categories.filter(item => item.name === category) : fixture.categories};
}

export async function getDashboard(category: string): Promise<DashboardData> {
  const token = process.env.DASHBOARD_ACCESS_TOKEN;
  if (token || process.env.DASHBOARD_MODE === 'postgres') {
    if (!token || token.length < 24 || !hasAccess((await headers()).get('authorization') ?? '', token)) throw new Error('Access denied');
  }
  if (process.env.DASHBOARD_MODE !== 'postgres') return filterDemo(category);
  const url = new URL(process.env.DASHBOARD_DATABASE_URL ?? '');
  if (!['127.0.0.1', '[::1]'].includes(url.hostname) || !['postgres:', 'postgresql:'].includes(url.protocol) || url.pathname !== '/analytics_fixture' || url.search || url.hash) throw new Error('Local fixture database required');
  const sourceRef = process.env.DASHBOARD_SOURCE_REF ?? '';
  if (!/^[a-z][a-z0-9_.:-]{0,126}$/.test(sourceRef)) throw new Error('Source scope required');
  const client = new Client({connectionString:url.toString(), connectionTimeoutMillis:3000});
  await client.connect();
  try {
    await client.query('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY');
    const source = await client.query(`select d.source_name, s.enabled, s.last_success_at, s.consecutive_failures,
      (select count(*)::int from analytics.fact_category_score f where f.source_key=d.source_key and f.is_current) as records
      from analytics.dim_source d join public.data_sources s on s.id=d.data_source_id
      where d.source_ref=$1 and d.semantic_contract_version='category_score_v1'`, [sourceRef]);
    if (source.rows.length !== 1) throw new Error('Source unavailable');
    const categories = await client.query(`select c.category_label as name, count(*)::int as count,
      avg(f.score_value)::float8 as average, min(f.score_value)::float8 as minimum, max(f.score_value)::float8 as maximum
      from analytics.fact_category_score f join analytics.dim_source d on d.source_key=f.source_key
      join analytics.dim_category c on c.category_key=f.category_key and c.source_key=f.source_key
      where d.source_ref=$1 and d.semantic_contract_version='category_score_v1' and f.is_current and ($2='' or c.category_label=$2)
      group by c.category_label order by count(*) desc, c.category_label`, [sourceRef,category]);
    const options = await client.query(`select distinct c.category_label from analytics.dim_category c
      join analytics.dim_source d on d.source_key=c.source_key where d.source_ref=$1
      and d.semantic_contract_version='category_score_v1' order by c.category_label`, [sourceRef]);
    const runs = await client.query(`select r.status, r.finished_at from public.sync_runs r
      join analytics.dim_source d on d.data_source_id=r.data_source_id
      where d.source_ref=$1 and d.semantic_contract_version='category_score_v1' order by r.started_at desc limit 5`, [sourceRef]);
    await client.query('COMMIT');
    const s=source.rows[0];
    return {mode:'postgres',source:s.source_name,active:s.enabled,records:s.records,failures:s.consecutive_failures,categoryOptions:options.rows.map(r=>r.category_label),
      lastSync:s.last_success_at ? new Date(s.last_success_at).toLocaleString('pt-BR',{timeZone:'UTC'})+' UTC' : 'Ainda não registrada',
      executor:'Sem evidência local', categories:categories.rows,
      history:runs.rows.map(r=>({label:r.finished_at ? new Date(r.finished_at).toLocaleString('pt-BR',{timeZone:'UTC'})+' UTC' : 'Em andamento',status:({applied:'Concluída',failed:'Falha',blocked:'Bloqueada',running:'Em andamento',planned:'Planejada'} as Record<string,string>)[r.status] ?? 'Desconhecido'}))};
  } finally { await client.end(); }
}
