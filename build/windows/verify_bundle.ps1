param(
    [Parameter(Mandatory = $true)]
    [string]$BundleRoot,
    [string]$SourcePath = "Log_checker.py",
    [string]$ExpectedSeries = "2.5.0"
)

$ErrorActionPreference = "Stop"

function Get-ReleaseMarker([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Release marker file is missing: $Path"
    }

    $text = Get-Content -Raw -LiteralPath $Path
    $markers = @(
        [regex]::Matches($text, 'v(?<series>\d+\.\d+\.\d+)\((?<build>\d+)\)') |
            ForEach-Object { $_.Value } |
            Sort-Object -Unique
    )
    if ($markers.Count -ne 1) {
        throw "Inconsistent version markers in $Path`: $($markers -join ', ')"
    }
    return [string]$markers[0]
}

$sourceMarker = Get-ReleaseMarker $SourcePath
$bundleMarker = Get-ReleaseMarker (Join-Path $BundleRoot "Log_checker.py")
$expectedPattern = "^v$([regex]::Escape($ExpectedSeries))\(\d+\)$"

if ($sourceMarker -notmatch $expectedPattern) {
    throw "Source marker is not a $ExpectedSeries release: $sourceMarker"
}
if ($bundleMarker -ne $sourceMarker) {
    throw "Built bundle is stale: source=$sourceMarker bundle=$bundleMarker"
}
if (-not (Test-Path -LiteralPath (Join-Path $BundleRoot "EventInspector.exe") -PathType Leaf)) {
    throw "Built bundle is missing EventInspector.exe"
}

Write-Host "Bundle validated: $bundleMarker"
