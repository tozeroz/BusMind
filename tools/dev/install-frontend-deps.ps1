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
Write-Host 'Installing frontend dependencies ...'
& $npmCommand.Source install
