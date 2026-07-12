$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$backendRoot = Join-Path $repoRoot 'backend'

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'uv command not found. Install uv first, then run uv sync from the project root.'
}

Set-Location $backendRoot
Write-Host 'Starting backend on http://127.0.0.1:8001 ...'
uv run python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
