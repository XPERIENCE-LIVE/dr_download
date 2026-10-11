$ErrorActionPreference = "Stop"
Import-Module (Join-Path $PSHOME "Modules/Microsoft.PowerShell.Utility/Microsoft.PowerShell.Utility.psd1")
$projectRoot = Split-Path -Parent $PSScriptRoot
$destination = Join-Path $projectRoot "electron/resources/ffmpeg"
$hashes = @{
    "ffmpeg.exe" = "CC5A6529C66D755CC3D243511A537A44CFE130ACBA1BCEA958765EDE282AB8BE"
    "ffprobe.exe" = "124A32653958026EBC653A5B934553DD849CACDB30835800ACB6EF80882BF4D1"
}
foreach ($name in $hashes.Keys) {
    $file = Join-Path $destination $name
    if ((Test-Path -LiteralPath $file) -and (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash -ne $hashes[$name]) {
        throw "FFmpeg SHA-256 mismatch: $name"
    }
}
if (-not ((Test-Path -LiteralPath (Join-Path $destination "ffmpeg.exe")) -and
    (Test-Path -LiteralPath (Join-Path $destination "ffprobe.exe")) -and
    (Test-Path -LiteralPath (Join-Path $destination "LICENSE.txt")))) {
    $version = "2024-10-02-git-358fdf3083"
    $directory = Join-Path $projectRoot "build/ffmpeg-runtime"
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
    $archive = Join-Path $directory "ffmpeg.zip"
    Invoke-WebRequest -UseBasicParsing -Uri "https://github.com/GyanD/codexffmpeg/releases/download/$version/ffmpeg-$version-full_build.zip" -OutFile $archive
    Expand-Archive -LiteralPath $archive -DestinationPath $directory -Force
    $extracted = Join-Path $directory "ffmpeg-$version-full_build"
    foreach ($name in $hashes.Keys) {
        if ((Get-FileHash -LiteralPath (Join-Path $extracted "bin/$name") -Algorithm SHA256).Hash -ne $hashes[$name]) {
            throw "FFmpeg SHA-256 mismatch: $name"
        }
    }
    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    foreach ($name in $hashes.Keys) { Copy-Item -LiteralPath (Join-Path $extracted "bin/$name") -Destination $destination }
    Copy-Item -LiteralPath (Join-Path $extracted "LICENSE") -Destination (Join-Path $destination "LICENSE.txt")
}
Write-Output "FFmpeg and FFprobe match the pinned internal build"
