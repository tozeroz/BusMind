# Shared helpers for LTA DataMall raw data collection scripts.
Set-StrictMode -Version 2.0

$script:LtaBaseUrl = "https://datamall2.mytransport.sg/ltaodataservice"

function Set-LtaTls {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
}

function Get-ProjectRoot {
    $scriptsDir = Split-Path -Parent $PSScriptRoot
    return (Split-Path -Parent (Split-Path -Parent $scriptsDir))
}

function Get-LtaRawDir {
    param(
        [string]$RawDir
    )

    if ([string]::IsNullOrWhiteSpace($RawDir)) {
        return (Join-Path (Get-ProjectRoot) "data\raw\lta")
    }

    return $RawDir
}

function Get-LtaAccountKey {
    param(
        [string]$AccountKey
    )

    if (-not [string]::IsNullOrWhiteSpace($AccountKey)) {
        return $AccountKey
    }

    if (-not [string]::IsNullOrWhiteSpace($env:LTA_ACCOUNT_KEY)) {
        return $env:LTA_ACCOUNT_KEY
    }

    throw "Missing AccountKey. Pass -AccountKey or set environment variable LTA_ACCOUNT_KEY."
}

function New-Dir {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    New-Item -ItemType Directory -Force $Path | Out-Null
}

function Get-LtaHeaders {
    param(
        [Parameter(Mandatory = $true)]
        [string]$AccountKey
    )

    return @{
        AccountKey = $AccountKey
        accept = "application/json"
    }
}

function Save-Json {
    param(
        [Parameter(Mandatory = $true)]
        [object]$Data,
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [int]$Depth = 30
    )

    $Data | ConvertTo-Json -Depth $Depth | Set-Content -Encoding UTF8 $Path
}

function Invoke-LtaODataAll {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Endpoint,
        [Parameter(Mandatory = $true)]
        [hashtable]$Headers,
        [int]$PageSize = 500
    )

    $all = New-Object System.Collections.ArrayList

    for ($skip = 0; ; $skip += $PageSize) {
        $url = "$script:LtaBaseUrl/$Endpoint" + '?$skip=' + $skip
        Write-Host "Fetching $url"
        $resp = Invoke-RestMethod -Uri $url -Headers $Headers

        if (-not $resp.value -or $resp.value.Count -eq 0) {
            break
        }

        foreach ($item in $resp.value) {
            [void]$all.Add($item)
        }

        if ($resp.value.Count -lt $PageSize) {
            break
        }
    }

    return $all
}

function Read-JsonFile {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    return (Get-Content $Path -Raw | ConvertFrom-Json)
}
