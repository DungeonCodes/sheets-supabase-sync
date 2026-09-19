# Meeting MVP

Dashboard autônomo para apresentar o estado técnico do projeto Sheets → Supabase.

## Como abrir

Abra `index.html` diretamente no Chrome:

```powershell
Start-Process .\demo\meeting\index.html
```

Não há instalação, servidor, build, npm, CDN ou conexão necessária. CSS, JavaScript e o dataset sintético estão no próprio HTML.

## Finalidade e limites

O dashboard apresenta o pipeline operacional validado, incluindo resiliência, governança, retention/lifecycle e a prova multi-source local. A seção Analytics MVP é uma demonstração com dados fictícios e não consulta Google, Supabase, PostgreSQL ou qualquer serviço externo.

Ainda não comprova o Star Schema físico, transformação analítica, RBAC analítico, BI real, scheduler/runtime, executor real de purge, operação produtiva ou E2E final.

