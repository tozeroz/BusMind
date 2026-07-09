# Collect one real-time Traffic Speed Bands snapshot from LTA DataMall.
param(
    [string]$AccountKey,
    [string]$RawDir
)

. "$PSScriptRoot\_lta_common.ps1"

Set-LtaTls
$key = Get-LtaAccountKey -AccountKey $AccountKey
$raw = Get-LtaRawDir -RawDir $RawDir
$headers = Get-LtaHeaders -AccountKey $key

$sampleDay = Get-Date -Format "yyyy-MM-dd"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outDir = Join-Path $raw "traffic_speed_bands\$sampleDay"
$outFile = Join-Path $outDir "traffic_speed_bands_$timestamp.json"
New-Dir $outDir

$items = Invoke-LtaODataAll -Endpoint "v4/TrafficSpeedBands" -Headers $headers
$record = [pscustomobject]@{
    query_time = (Get-Date).ToString("s")
    endpoint = "v4/TrafficSpeedBands"
    value = $items
}

Save-Json -Data $record -Path $outFile -Depth 30
Write-Host "Saved $($items.Count) Traffic Speed Bands rows to $outFile"
