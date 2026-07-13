$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$backendRoot = Join-Path $repoRoot 'backend'
$backendEnvPath = Join-Path $backendRoot '.env'

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'uv command not found. Install uv first, then run uv sync from the project root.'
}

if (-not (Test-Path -LiteralPath $backendEnvPath)) {
    throw "backend/.env not found. Copy backend/.env.example to backend/.env and fill in the real MySQL settings first."
}

$databaseUrlLine = Get-Content $backendEnvPath | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1
if (-not $databaseUrlLine) {
    throw 'DATABASE_URL is missing in backend/.env. Please configure a MySQL connection string first.'
}

$databaseUrl = ($databaseUrlLine -replace '^DATABASE_URL=', '').Trim()
if ([string]::IsNullOrWhiteSpace($databaseUrl) -or $databaseUrl -match 'CHANGE_ME') {
    throw 'DATABASE_URL in backend/.env is not configured with real MySQL credentials yet.'
}

if ($databaseUrl -notmatch '^mysql(\+pymysql)?://') {
    throw "DATABASE_URL in backend/.env must be a MySQL URL for this startup flow. Current value: $databaseUrl"
}

Set-Location $backendRoot
Write-Host "Using backend env file: $backendEnvPath"
Write-Host "Using database: $databaseUrl"
Write-Host 'Starting backend on http://127.0.0.1:8001 ...'
uv run python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
