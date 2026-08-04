from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
@dataclass(frozen=True)
class Environment:
    app_env:str; project_ref:str; allowed_ref:str; supabase_url:str; db_url:str; secret_key:str; google_file:str
def load_environment(root:Path)->Environment:
    p=root/'.env.local'
    if not p.is_file(): raise ValueError('Configuracao local ausente')
    d={}
    for n,r in enumerate(p.read_text(encoding='utf-8').splitlines(),1):
        x=r.strip()
        if not x or x.startswith('#'): continue
        if '=' not in x: raise ValueError(f'Linha invalida: {n}')
        k,v=x.split('=',1)
        if not k.isidentifier() or k in d: raise ValueError(f'Chave invalida ou duplicada: {n}')
        d[k]=os.environ.get(k,v)
    e=Environment(d.get('APP_ENV',''),d.get('SUPABASE_PROJECT_REF',''),d.get('SUPABASE_ALLOWED_PROJECT_REF',''),d.get('SUPABASE_URL',''),d.get('SUPABASE_DB_URL',''),d.get('SUPABASE_SECRET_KEY',d.get('SUPABASE_SERVICE_ROLE_KEY','')),d.get('GOOGLE_SERVICE_ACCOUNT_FILE',''))
    if e.app_env=='production': raise ValueError('Production bloqueada')
    return e
def validate_environment(e:Environment)->None:
    if e.app_env!='staging' or not e.project_ref or e.project_ref!=e.allowed_ref: raise ValueError('Project ref nao autorizado')
    u=urlparse(e.supabase_url); d=urlparse(e.db_url)
    if u.scheme!='https' or u.hostname!=f'{e.project_ref}.supabase.co': raise ValueError('URL Supabase incompativel')
    if d.scheme not in {'postgres','postgresql'} or d.path.strip('/')!='postgres': raise ValueError('URL PostgreSQL invalida')
def sanitize(text:str)->str:
    return 'Falha de configuracao ou conectividade; detalhe sensivel ocultado'
