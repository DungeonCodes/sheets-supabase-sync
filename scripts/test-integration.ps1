$ErrorActionPreference = 'Stop'
$repo = Resolve-Path "$PSScriptRoot\.."
if (-not (Get-Command supabase -ErrorAction SilentlyContinue)) { Write-Host 'SKIP: Supabase CLI indisponivel.'; exit 0 }
try { supabase status --workdir $repo | Out-Null } catch { Write-Host 'SKIP: Supabase local nao esta ativo.'; exit 0 }
$status = supabase status --workdir $repo -o env
$dbLine = $status | Where-Object { $_ -match '^DB_URL=' } | Select-Object -First 1
if (-not $dbLine) { Write-Host 'SKIP: URL PostgreSQL local nao encontrada no status do Supabase.'; exit 0 }
$env:LOCAL_DATABASE_URL = $dbLine.Substring(7).Trim('"')
$env:RUN_SUPABASE_INTEGRATION = '1'
$env:PYTHONPATH = "$repo\src"
& "$repo\.venv\Scripts\python.exe" -m unittest discover -s "$repo\tests\integration" -p "test_*postgres*.py" -v
