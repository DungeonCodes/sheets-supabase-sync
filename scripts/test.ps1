$ErrorActionPreference = 'Stop'
$repo = Resolve-Path "$PSScriptRoot\.."
$env:PYTHONPATH = "$repo\src"
& "$repo\.venv\Scripts\python.exe" -m unittest discover -s "$repo\tests" -v
