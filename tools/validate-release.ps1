$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$releaseDirectory = Join-Path $projectRoot "electron/release"
$installer = Get-ChildItem -LiteralPath $releaseDirectory -Filter "Dr-Download-Setup-*-x64.exe" -File |
    Sort-Object LastWriteTimeUtc -Descending |
    Select-Object -First 1

if (-not $installer) { throw "NSIS installer is unavailable" }

$requiredFiles = @(
    (Join-Path $projectRoot "electron/resources/backend/dr-download-backend.exe"),
    (Join-Path $projectRoot "electron/resources/ffmpeg/ffmpeg.exe"),
    (Join-Path $projectRoot "electron/resources/ffmpeg/ffprobe.exe"),
    (Join-Path $projectRoot "electron/resources/node/node.exe")
)
foreach ($requiredFile in $requiredFiles) {
    if (-not (Test-Path -LiteralPath $requiredFile -PathType Leaf)) {
        throw "Required release runtime is unavailable: $requiredFile"
    }
}

$signature = Get-AuthenticodeSignature -LiteralPath $installer.FullName
if ($signature.Status -ne "Valid") {
    throw "Authenticode signature is not Valid: $($signature.Status)"
}

$hash = Get-FileHash -LiteralPath $installer.FullName -Algorithm SHA256
$evidenceDirectory = Join-Path $projectRoot "artifacts/quality"
New-Item -ItemType Directory -Force -Path $evidenceDirectory | Out-Null
[ordered]@{
    schema = 1
    installer = $installer.Name
    bytes = $installer.Length
    sha256 = $hash.Hash
    authenticode = $signature.Status.ToString()
    ffprobe = "ffprobe.exe"
    node = "node.exe"
    backend = "dr-download-backend.exe"
    verified_at_utc = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $evidenceDirectory "release-artifact.json") -Encoding utf8
