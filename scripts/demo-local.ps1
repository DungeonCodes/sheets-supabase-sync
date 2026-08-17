param(
    [Parameter(Mandatory = $true)]
    [string]$DatabaseUrl
)

$ErrorActionPreference = 'Stop'
$repo = Resolve-Path "$PSScriptRoot\.."
$env:PYTHONPATH = "$repo\src"
$python = "$repo\.venv\Scripts\python.exe"
$snapshot = "$repo\runtime\snapshots\demo.json"
$artifacts = "$repo\runtime\artifacts\demo"

function Invoke-DemoStep {
    param([string]$Name, [string]$Fixture)
    Write-Host "`n=== $Name ==="
    & $python -m sheets_supabase_sync.cli --config "$repo\configs\examples\local.json" --input "$repo\data\fixtures\$Fixture" --snapshot $snapshot --artifacts "$artifacts\$Name" --mode apply-local --database-url $DatabaseUrl
}

Invoke-DemoStep '01-inicial' 'demo_initial.csv'
Invoke-DemoStep '02-nova-linha' 'demo_added.csv'
Invoke-DemoStep '03-linha-alterada' 'demo_changed.csv'
Invoke-DemoStep '04-remocao-logica' 'demo_removed.csv'
Invoke-DemoStep '05-restauracao' 'demo_restored.csv'
Invoke-DemoStep '06-idempotencia' 'demo_restored.csv'

Write-Host "`nDemonstracao concluida. Consulte $artifacts para manifests, relatorios e SQL auditavel."
