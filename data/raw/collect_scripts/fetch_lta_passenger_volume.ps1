# Fetch monthly Passenger Volume download links and raw zip files.
param(
    [string]$AccountKey,
    [Parameter(Mandatory = $true)]
    [ValidatePattern("^\d{6}$")]
    [string]$Month,
    [string]$RawDir
)

. "$PSScriptRoot\_lta_common.ps1"

Set-LtaTls
$key = Get-LtaAccountKey -AccountKey $AccountKey
$raw = Get-LtaRawDir -RawDir $RawDir
$apiDir = Join-Path $raw "api_response"
$stopDir = Join-Path $raw "passenger_volume_stop\$Month"
$odDir = Join-Path $raw "passenger_volume_od\$Month"
$headers = Get-LtaHeaders -AccountKey $key

New-Dir $apiDir
New-Dir $stopDir
New-Dir $odDir

$stopResp = Invoke-RestMethod -Uri "$script:LtaBaseUrl/PV/Bus?Date=$Month" -Headers $headers
$odResp = Invoke-RestMethod -Uri "$script:LtaBaseUrl/PV/ODBus?Date=$Month" -Headers $headers

$stopRespPath = Join-Path $apiDir "PassengerVolumeByBusStops_$Month.json"
$odRespPath = Join-Path $apiDir "PassengerVolumeByOriginDestinationBusStops_$Month.json"
Save-Json -Data $stopResp -Path $stopRespPath
Save-Json -Data $odResp -Path $odRespPath

if (-not $stopResp.value -or -not $stopResp.value[0].Link) {
    throw "Passenger Volume by Bus Stops response did not contain a download Link."
}

if (-not $odResp.value -or -not $odResp.value[0].Link) {
    throw "Passenger Volume by OD Bus Stops response did not contain a download Link."
}

$stopZip = Join-Path $stopDir "original.zip"
$odZip = Join-Path $odDir "original.zip"

Write-Host "Downloading Passenger Volume by Bus Stops for $Month"
Invoke-WebRequest -Uri $stopResp.value[0].Link -OutFile $stopZip

Write-Host "Downloading Passenger Volume by OD Bus Stops for $Month"
Invoke-WebRequest -Uri $odResp.value[0].Link -OutFile $odZip

Write-Host "Saved API response to $stopRespPath"
Write-Host "Saved API response to $odRespPath"
Write-Host "Saved raw zip to $stopZip"
Write-Host "Saved raw zip to $odZip"
