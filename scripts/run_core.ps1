$ErrorActionPreference = 'Stop'
$studyRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $studyRoot
$studyPython = Join-Path $studyRoot '.venv/Scripts/python.exe'
& $studyPython -m bioflux.cli all
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $studyPython scripts/verify_artifacts.py
exit $LASTEXITCODE
