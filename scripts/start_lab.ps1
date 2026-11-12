$ErrorActionPreference = 'Stop'
$studyRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $studyRoot
& (Join-Path $studyRoot '.venv/Scripts/python.exe') -m streamlit run app.py
exit $LASTEXITCODE
