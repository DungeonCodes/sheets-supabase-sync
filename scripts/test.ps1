$ErrorActionPreference = 'Stop'
$repo = Resolve-Path "$PSScriptRoot\.."
$env:PYTHONPATH = "$repo\src"
py -3.13 -m unittest discover -s "$repo\tests" -v
