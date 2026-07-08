# Fetch full BusStops, BusRoutes, and BusServices snapshots.
param(
    [string]$AccountKey,
    [string]$RawDir
)

. "$PSScriptRoot\_lta_common.ps1"

Set-LtaTls
$key = Get-LtaAccountKey -AccountKey $AccountKey
$raw = Get-LtaRawDir -RawDir $RawDir
$apiDir = Join-Path $raw "api_response"
$headers = Get-LtaHeaders -AccountKey $key

New-Dir $apiDir

$datasets = @(
    @{ Endpoint = "BusStops"; File = "BusStops_full.json" },
    @{ Endpoint = "BusRoutes"; File = "BusRoutes_full.json" },
    @{ Endpoint = "BusServices"; File = "BusServices_full.json" }
)

foreach ($dataset in $datasets) {
    $items = Invoke-LtaODataAll -Endpoint $dataset.Endpoint -Headers $headers
    $outFile = Join-Path $apiDir $dataset.File
    Save-Json -Data $items -Path $outFile
    Write-Host "Saved $($items.Count) records to $outFile"
}
