$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath 'frontend/dist/index.html')) {
    throw 'Build the React interface first: cd frontend; npm ci; npm run build'
}
Write-Host 'BioFlux Lab: http://127.0.0.1:8000 (Ctrl+C to stop)'
& '.\.venv\Scripts\python.exe' -m uvicorn bioflux.server:app --host 127.0.0.1 --port 8000
