# Sample real-time Bus Arrival records for selected bus stops.
param(
    [string]$AccountKey,
    [string]$RawDir,
    [int]$MaxStops = 50,
    [int]$DelayMilliseconds = 300,
    [string[]]$BusStopCodes
)

. "$PSScriptRoot\_lta_common.ps1"

Set-LtaTls
$key = Get-LtaAccountKey -AccountKey $AccountKey
$raw = Get-LtaRawDir -RawDir $RawDir
$headers = Get-LtaHeaders -AccountKey $key

if (-not $BusStopCodes -or $BusStopCodes.Count -eq 0) {
    $busStopsPath = Join-Path $raw "api_response\BusStops_full.json"
    if (-not (Test-Path $busStopsPath)) {
        throw "Missing $busStopsPath. Run fetch_lta_static.ps1 first or pass -BusStopCodes."
    }

    $BusStopCodes = (Read-JsonFile -Path $busStopsPath | Select-Object -First $MaxStops).BusStopCode
} else {
    $BusStopCodes = $BusStopCodes | Select-Object -First $MaxStops
}

$sampleDay = Get-Date -Format "yyyy-MM-dd"
$outDir = Join-Path $raw "bus_arrival_samples\$sampleDay"
$outFile = Join-Path $outDir "bus_arrival_sample.jsonl"
New-Dir $outDir

foreach ($stop in $BusStopCodes) {
    $url = "$script:LtaBaseUrl/v3/BusArrival?BusStopCode=$stop"
    try {
        $resp = Invoke-RestMethod -Uri $url -Headers $headers
        $record = [pscustomobject]@{
            query_time = (Get-Date).ToString("s")
            bus_stop_code = $stop
            response = $resp
        }
        ($record | ConvertTo-Json -Depth 30 -Compress) | Add-Content -Encoding UTF8 $outFile
        Write-Host "OK stop $stop"
        Start-Sleep -Milliseconds $DelayMilliseconds
    } catch {
        Write-Host "Failed stop $stop : $($_.Exception.Message)"
    }
}

Write-Host "Saved Bus Arrival samples to $outFile"
