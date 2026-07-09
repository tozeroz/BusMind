# Check whether required LTA raw data files are present.
param(
    [string]$RawDir
)

. "$PSScriptRoot\_lta_common.ps1"

$raw = Get-LtaRawDir -RawDir $RawDir

Write-Host "Raw data directory: $raw"
Write-Host ""

$expectedFiles = @(
    "api_response\BusStops_full.json",
    "api_response\BusRoutes_full.json",
    "api_response\BusServices_full.json"
)

foreach ($relativePath in $expectedFiles) {
    $path = Join-Path $raw $relativePath
    if (Test-Path $path) {
        $items = Read-JsonFile -Path $path
        Write-Host "OK $relativePath records=$($items.Count)"
    } else {
        Write-Host "MISSING $relativePath"
    }
}

Write-Host ""

$volumeZips = Get-ChildItem -Recurse -File -Path (Join-Path $raw "passenger_volume_stop"), (Join-Path $raw "passenger_volume_od") -Filter "original.zip" -ErrorAction SilentlyContinue
foreach ($zip in $volumeZips) {
    Write-Host "OK $($zip.FullName) bytes=$($zip.Length)"
}

if (-not $volumeZips) {
    Write-Host "MISSING passenger volume original.zip files"
}

Write-Host ""

$arrivalFiles = Get-ChildItem -Recurse -File -Path (Join-Path $raw "bus_arrival_samples") -Filter "*.jsonl" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
foreach ($file in $arrivalFiles | Select-Object -First 5) {
    $lineCount = (Get-Content $file.FullName).Count
    Write-Host "OK $($file.FullName) lines=$lineCount bytes=$($file.Length)"
}

if (-not $arrivalFiles) {
    Write-Host "MISSING bus arrival sample jsonl files"
}

Write-Host ""

$trafficFiles = Get-ChildItem -Recurse -File -Path (Join-Path $raw "traffic_speed_bands") -Include "*.json", "*.jsonl" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
foreach ($file in $trafficFiles | Select-Object -First 5) {
    Write-Host "OK $($file.FullName) bytes=$($file.Length)"
}

if (-not $trafficFiles) {
    Write-Host "MISSING traffic speed bands snapshots"
}
