$ErrorActionPreference = 'Stop'

$scriptDir = $PSScriptRoot
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
$frontendRoot = Join-Path $repoRoot 'frontend'
$windowsPowerShell = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'

function Require-Command {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$InstallHint
    )

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $command) {
        throw "$Name command not found. $InstallHint"
    }
    return $command
}

function Open-DevWindow {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title,
        [Parameter(Mandatory = $true)]
        [string]$ScriptPath
    )

    Start-Process -FilePath $windowsPowerShell -ArgumentList @(
        '-NoExit',
        '-ExecutionPolicy', 'Bypass',
        '-Command', "& { `$Host.UI.RawUI.WindowTitle = '$Title'; & '$ScriptPath' }"
    ) -WindowStyle Normal
}

Require-Command -Name 'uv' -InstallHint 'Install uv first, then run this script again.' | Out-Null
Require-Command -Name 'ssh' -InstallHint 'Install OpenSSH client first.' | Out-Null
$npmCommand = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npmCommand) {
    $npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
}
if (-not $npmCommand) {
    throw 'npm command not found. Install Node.js first.'
}

Set-Location $repoRoot
Write-Host 'Syncing Python dependencies with uv ...'
uv sync

if (-not (Test-Path -LiteralPath (Join-Path $frontendRoot 'node_modules'))) {
    Write-Host 'frontend/node_modules not found. Installing frontend dependencies ...'
    Push-Location $frontendRoot
    try {
        & $npmCommand.Source install
    }
    finally {
        Pop-Location
    }
}

Open-DevWindow -Title 'BusMind DB Tunnel' -ScriptPath (Join-Path $scriptDir 'start-db-tunnel.ps1')
Start-Sleep -Seconds 2

Open-DevWindow -Title 'BusMind Backend' -ScriptPath (Join-Path $scriptDir 'start-backend.ps1')
Start-Sleep -Seconds 2

Open-DevWindow -Title 'BusMind Frontend' -ScriptPath (Join-Path $scriptDir 'start-frontend.ps1')

Write-Host 'Opened 3 PowerShell windows for tunnel, backend, and frontend.'
Write-Host 'Docs: http://127.0.0.1:8001/docs'
Write-Host 'Frontend: http://127.0.0.1:5173'
Write-Host 'If an API returns 500 because of database connection, run tools/dev/check-db-tunnel.ps1.'
