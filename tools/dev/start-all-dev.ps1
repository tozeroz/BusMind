$ErrorActionPreference = 'Stop'

$scriptDir = $PSScriptRoot
$windowsPowerShell = Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'

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

Open-DevWindow -Title 'BusMind DB Tunnel' -ScriptPath (Join-Path $scriptDir 'start-db-tunnel.ps1')
Start-Sleep -Seconds 2

Open-DevWindow -Title 'BusMind Backend' -ScriptPath (Join-Path $scriptDir 'start-backend.ps1')
Start-Sleep -Seconds 2

Open-DevWindow -Title 'BusMind Frontend' -ScriptPath (Join-Path $scriptDir 'start-frontend.ps1')

Write-Host 'Opened 3 PowerShell windows for tunnel, backend, and frontend.'
Write-Host 'Docs: http://127.0.0.1:8000/docs'
Write-Host 'Frontend: http://127.0.0.1:5173'
