$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repoRoot

if (-not (Get-Command ssh -ErrorAction SilentlyContinue)) {
    throw 'ssh command not found. Install OpenSSH client first.'
}

Write-Host 'Opening SSH tunnel 127.0.0.1:3307 -> remote 3306 ...'
Write-Host 'Keep this window open while developing.'
ssh -N -L 3307:127.0.0.1:3306 training-server-backend
