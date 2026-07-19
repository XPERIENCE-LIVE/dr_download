$ErrorActionPreference = "Stop"
$electronRoot = Split-Path -Parent $PSScriptRoot
$application = Join-Path $electronRoot "release/win-unpacked/Dr. Download.exe"
if (-not (Test-Path -LiteralPath $application -PathType Leaf)) {
    throw "Packaged application is unavailable"
}

$port = Get-Random -Minimum 12000 -Maximum 22000
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$artifactDirectory = Join-Path $electronRoot "test-artifacts/packaged-smoke-$stamp"
$outputDirectory = Join-Path $artifactDirectory "downloads"
$dataDirectory = Join-Path $artifactDirectory "data"
New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
New-Item -ItemType Directory -Force -Path $dataDirectory | Out-Null
$config = [ordered]@{
    theme = "dark"
    default_format = "video"
    language = "es"
    cookie_source = "none"
    cookie_consent = $false
    notifications = $false
    output_dir = $outputDirectory
    auto_update_engine = $true
    auto_update_app = $false
    worker_threads = 1
    log_max_bytes = 1000000
    log_backup_count = 3
}
$configJson = $config | ConvertTo-Json
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Join-Path $dataDirectory "config.json"), $configJson, $utf8)
$arguments = @("--remote-debugging-port=$port", "--user-data-dir=$dataDirectory")
$process = Start-Process -FilePath $application -ArgumentList $arguments -WindowStyle Hidden -PassThru
try {
    node (Join-Path $PSScriptRoot "packaged-ui-smoke.mjs") $port $outputDirectory
    if ($LASTEXITCODE -ne 0) { throw "Packaged UI smoke failed with exit code $LASTEXITCODE" }

    $ffprobe = Join-Path $electronRoot "resources/ffmpeg/ffprobe.exe"
    if (-not (Test-Path -LiteralPath $ffprobe -PathType Leaf)) { throw "ffprobe.exe is unavailable" }
    $mediaFiles = @(Get-ChildItem -LiteralPath $outputDirectory -File)
    if ($mediaFiles.Count -lt 2) { throw "Packaged smoke did not create both media files" }
    foreach ($mediaFile in $mediaFiles) {
        $probeJson = & $ffprobe -v error -show_entries stream=codec_type -of json $mediaFile.FullName
        if ($LASTEXITCODE -ne 0) { throw "FFprobe rejected $($mediaFile.Name)" }
        $probe = $probeJson | ConvertFrom-Json
        if (-not $probe.streams -or $probe.streams.Count -lt 1) {
            throw "No playable stream found in $($mediaFile.Name)"
        }
    }
}
finally {
    if ($process) {
        $treeArguments = @("/PID", "$($process.Id)", "/T", "/F")
        & taskkill @treeArguments 2>$null | Out-Null
    }
    $backendExecutable = Join-Path (Split-Path -Parent $application) "resources/backend/dr-download-backend.exe"
    $packagedPaths = @(
        [System.IO.Path]::GetFullPath($application),
        [System.IO.Path]::GetFullPath($backendExecutable)
    )
    $packagedProcesses = Get-CimInstance Win32_Process | Where-Object {
        $_.ExecutablePath -and $packagedPaths.Contains([System.IO.Path]::GetFullPath($_.ExecutablePath))
    }
    foreach ($packagedProcess in $packagedProcesses) {
        Stop-Process -Id $packagedProcess.ProcessId -Force -ErrorAction Stop
    }
    Start-Sleep -Milliseconds 300
    $remaining = Get-CimInstance Win32_Process | Where-Object {
        $_.ExecutablePath -and $packagedPaths.Contains([System.IO.Path]::GetFullPath($_.ExecutablePath))
    }
    if ($remaining) {
        throw "Packaged process remained after cleanup"
    }
}
