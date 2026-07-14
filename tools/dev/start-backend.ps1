$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$backendRoot = Join-Path $repoRoot 'backend'
$envPath = Join-Path $repoRoot '.env'

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw 'uv command not found. Install uv first, then run uv sync from the project root.'
}

if (-not (Test-Path -LiteralPath $envPath)) {
    throw "Root .env not found. Copy .env.example to .env and fill in the real MySQL settings first."
}

$databaseUrlLine = Get-Content $envPath | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1
if (-not $databaseUrlLine) {
    throw 'DATABASE_URL is missing in root .env. Please configure a MySQL connection string first.'
}

$databaseUrl = ($databaseUrlLine -replace '^DATABASE_URL=', '').Trim()
if ([string]::IsNullOrWhiteSpace($databaseUrl) -or $databaseUrl -match 'CHANGE_ME') {
    throw 'DATABASE_URL in root .env is not configured with real MySQL credentials yet.'
}

if ($databaseUrl -notmatch '^mysql(\+pymysql)?://') {
    throw "DATABASE_URL in root .env must be a MySQL URL for this startup flow. Current value: $databaseUrl"
}

Set-Location $backendRoot
Write-Host "Using shared env file: $envPath"
Write-Host "Using database: $databaseUrl"
Write-Host 'Starting backend on http://127.0.0.1:8001 ...'
uv run python -m uvicorn app.main:app --reload --reload-dir app --host 127.0.0.1 --port 8001
