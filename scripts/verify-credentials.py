import argparse,json,ssl
from pathlib import Path
from urllib.request import Request,urlopen
from sheets_supabase_sync.environment import load_environment,validate_environment,sanitize
p=argparse.ArgumentParser();p.add_argument('--format',choices=('text','json'),default='text');p.add_argument('--supabase-only',action='store_true');p.add_argument('--google-only',action='store_true');p.add_argument('--local-only',action='store_true');a=p.parse_args();c=[]
def add(n,s,x):c.append({'name':n,'status':s,'code':x})
try:
 e=load_environment(Path(__file__).parents[1]);validate_environment(e);add('configuration','passed','valid')
 if a.local_only and not e.secret_key:raise ValueError('Secret Key ausente')
 if not a.google_only and not a.local_only:
  if not e.secret_key:raise ValueError('Secret Key ausente')
  with urlopen(Request(e.supabase_url.rstrip('/')+'/rest/v1/',headers={'apikey':e.secret_key}),timeout=5,context=ssl.create_default_context()) as r:add('supabase_data_api','passed',str(r.status))
 if not a.supabase_only:
  q=Path(e.google_file);d=json.loads(q.read_text(encoding='utf-8'))
  if d.get('type')!='service_account' or not d.get('private_key') or not str(d.get('client_email','')).endswith('.iam.gserviceaccount.com'):raise ValueError('Estrutura Google invalida')
  add('google_service_account','passed' if a.local_only else 'warning','structure_valid' if a.local_only else 'token_nao_testado_sem_driver')
except Exception as x:add('verification','failed',sanitize(str(x)))
if a.format=='json':print(json.dumps({'status':'failed' if any(x['status']=='failed' for x in c) else 'warning' if any(x['status']=='warning' for x in c) else 'healthy','checks':c}))
else:
 for x in c:print(f"[{'OK' if x['status']=='passed' else 'AVISO' if x['status']=='warning' else 'FALHA'}] {x['name']}: {x['code']}")
raise SystemExit(2 if any(x['status']=='failed' for x in c) else 1 if any(x['status']=='warning' for x in c) else 0)
