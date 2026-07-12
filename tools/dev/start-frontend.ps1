$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$frontendRoot = Join-Path $repoRoot 'frontend'

$npmCommand = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npmCommand) {
    $npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
}

if (-not $npmCommand) {
    throw 'npm command not found. Install Node.js and ensure npm is available in PATH first.'
}

Set-Location $frontendRoot
Write-Host 'Starting frontend on http://127.0.0.1:5173 ...'
& $npmCommand.Source run dev
