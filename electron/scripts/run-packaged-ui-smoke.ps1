param([string]$ApplicationPath, [string]$InstallerPath)

$ErrorActionPreference = "Stop"
$electronRoot = Split-Path -Parent $PSScriptRoot

function Start-PackagedApplication([string]$Application, [string[]]$Arguments) {
    $nodeMode = $env:ELECTRON_RUN_AS_NODE
    try {
        # Codex's host flag would run the packaged Electron executable as Node.
        Remove-Item Env:ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue
        Start-Process -FilePath $Application -ArgumentList $Arguments -WindowStyle Hidden -PassThru
    }
    finally { $env:ELECTRON_RUN_AS_NODE = $nodeMode }
}

function Assert-ContainedFile([string]$Directory, [string]$Filename) {
    $root = [System.IO.Path]::GetFullPath($Directory).TrimEnd("\", "/") + [System.IO.Path]::DirectorySeparatorChar
    if (-not [System.IO.Path]::GetFullPath($Filename).StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Completed file is outside the isolated output directory: $Filename"
    }
}

function Assert-MediaStreams([string]$FormatId, $Probe) {
    $types = @($Probe.streams | ForEach-Object { $_.codec_type })
    if ($FormatId -eq "audio-mp3") {
        if ($types.Count -ne 1 -or $types[0] -ne "audio" -or $Probe.streams[0].codec_name -ne "mp3") {
            throw "MP3 output must contain one MP3 audio stream"
        }
    }
    elseif ($FormatId -in @("video-best", "video-compatible")) {
        if ($types -notcontains "video" -or $types -notcontains "audio") { throw "Video output must contain video and audio streams" }
        if ($FormatId -eq "video-compatible") {
            $video = @($Probe.streams | Where-Object { $_.codec_type -eq "video" })
            $audio = @($Probe.streams | Where-Object { $_.codec_type -eq "audio" })
            if ($video.Count -ne 1 -or $audio.Count -ne 1 -or $video[0].codec_name -ne "h264" -or $audio[0].codec_name -ne "aac") {
                throw "Compatible MP4 must contain H.264 video and AAC audio"
            }
        }
    }
    else { throw "Unsupported smoke format: $FormatId" }
}

if (-not $ApplicationPath) { $ApplicationPath = Join-Path $electronRoot "release/win-unpacked/Dr. Download.exe" }
if (-not $InstallerPath) {
    $version = (Get-Content -LiteralPath (Join-Path $electronRoot "package.json") -Raw | ConvertFrom-Json).version
    $InstallerPath = Join-Path $electronRoot "release/Dr-Download-Setup-$version-x64.exe"
}
$application = [System.IO.Path]::GetFullPath($ApplicationPath)
$installer = [System.IO.Path]::GetFullPath($InstallerPath)
$resources = Join-Path (Split-Path -Parent $application) "resources"
$backendExecutable = Join-Path $resources "backend/dr-download-backend.exe"
$ffprobe = Join-Path $resources "ffmpeg/ffprobe.exe"
$identityPaths = @($installer, $application, (Join-Path $resources "app.asar"), $backendExecutable,
    $ffprobe, (Join-Path $resources "ffmpeg/ffmpeg.exe"), (Join-Path $resources "node/node.exe"))
foreach ($path in $identityPaths) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required packaged artifact is unavailable: $path" }
}
$packagedPaths = @($application, [System.IO.Path]::GetFullPath($backendExecutable))
$existing = Get-CimInstance Win32_Process | Where-Object {
    $_.ExecutablePath -and $packagedPaths.Contains([System.IO.Path]::GetFullPath($_.ExecutablePath))
}
if ($existing) { throw "Selected packaged application is already running; close it before the isolated smoke" }

$port = Get-Random -Minimum 12000 -Maximum 22000
$stamp = Get-Date -Format "yyyyMMdd-HHmmss-fff"
$artifactDirectory = Join-Path $electronRoot "test-artifacts/packaged-smoke-$stamp"
$outputDirectory = Join-Path $artifactDirectory "downloads"
$dataDirectory = Join-Path $artifactDirectory "data"
New-Item -ItemType Directory -Path $outputDirectory | Out-Null
New-Item -ItemType Directory -Path $dataDirectory | Out-Null
$utf8 = New-Object System.Text.UTF8Encoding($false)
$identity = @(foreach ($path in $identityPaths) {
    [ordered]@{ path = $path; bytes = (Get-Item -LiteralPath $path).Length; sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash }
})
$evidence = [ordered]@{
    schema = 2; status = "failed"; failure = $null; kind = "win-unpacked-real-ui"
    artifacts = $identity
    installer_authenticode = (Get-AuthenticodeSignature -LiteralPath $installer).Status.ToString()
    installer_lifecycle_verified = $false
    installer_lifecycle_limit = "NSIS writes shared per-user registry and shortcuts; isolated Windows account or VM required"
    public_release_ready = $false
    started_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    downloads = @(); downloaded_files_preserved = $false
}
$config = [ordered]@{
    theme = "dark"; default_format = "video"; language = "es"
    cookie_source = "none"; cookie_consent = $false; notifications = $false
    output_dir = $outputDirectory; auto_update_engine = $true; auto_update_app = $false
    worker_threads = 1; log_max_bytes = 1000000; log_backup_count = 3
}
[System.IO.File]::WriteAllText((Join-Path $dataDirectory "config.json"), ($config | ConvertTo-Json), $utf8)
$arguments = @("--remote-debugging-port=$port", "--user-data-dir=`"$dataDirectory`"")
$process = $null
try {
    $process = Start-PackagedApplication $application $arguments
    $uiJson = node (Join-Path $PSScriptRoot "packaged-ui-smoke.mjs") $port $outputDirectory $artifactDirectory
    if ($LASTEXITCODE -ne 0) { throw "Packaged UI smoke failed with exit code $LASTEXITCODE" }
    $uiText = $uiJson -join "`n"
    [System.IO.File]::WriteAllText((Join-Path $artifactDirectory "ui-result.json"), $uiText, $utf8)
    $ui = $uiText | ConvertFrom-Json
    $evidence.ui = $ui
    if ($ui.tasks.Count -ne 3 -or (@($ui.tasks.formatId | Sort-Object -Unique)).Count -ne 3) {
        throw "Packaged smoke must complete MP3, maximum quality video, and compatible MP4 tasks"
    }
    foreach ($task in $ui.tasks) {
        Assert-ContainedFile $outputDirectory $task.filename
        $mediaFile = Get-Item -LiteralPath $task.filename
        if ($task.status -ne "completed" -or $mediaFile.Length -le 0) { throw "Download did not produce a completed non-empty file" }
        $probeJson = & $ffprobe -v error -show_entries stream=codec_type,codec_name -of json $mediaFile.FullName
        if ($LASTEXITCODE -ne 0) { throw "FFprobe rejected $($mediaFile.Name)" }
        $probe = ($probeJson -join "`n") | ConvertFrom-Json
        Assert-MediaStreams $task.formatId $probe
        $evidence.downloads += [ordered]@{
            id = $task.id; format = $task.formatId; path = $mediaFile.FullName; bytes = $mediaFile.Length
            sha256 = (Get-FileHash -LiteralPath $mediaFile.FullName -Algorithm SHA256).Hash
            streams = $probe.streams
        }
    }
    $evidence.status = "passed"
}
catch {
    $evidence.failure = $_.Exception.Message
    throw
}
finally {
    try {
        if ($process) {
            $snapshot = @(Get-CimInstance Win32_Process)
            $ownedIds = @($process.Id)
            do {
                $previousCount = $ownedIds.Count
                $ownedIds = @($ownedIds + @($snapshot | Where-Object { $ownedIds -contains $_.ParentProcessId } | ForEach-Object { $_.ProcessId }) | Sort-Object -Unique)
            } while ($ownedIds.Count -gt $previousCount)
            $owned = @($snapshot | Where-Object { $ownedIds -contains $_.ProcessId })
            $treeArguments = @("/PID", "$($process.Id)", "/T", "/F")
            $process.Refresh()
            if (-not $process.HasExited) { & taskkill @treeArguments 2>$null | Out-Null }
            foreach ($child in $owned) {
                $live = Get-CimInstance Win32_Process -Filter "ProcessId = $($child.ProcessId)"
                if ($live -and $live.CreationDate -eq $child.CreationDate) { Stop-Process -Id $child.ProcessId -Force -ErrorAction Stop }
            }
            Start-Sleep -Milliseconds 300
            foreach ($child in $owned) {
                $live = Get-CimInstance Win32_Process -Filter "ProcessId = $($child.ProcessId)"
                if ($live -and $live.CreationDate -eq $child.CreationDate) { throw "Packaged process remained after cleanup" }
            }
        }
        foreach ($download in $evidence.downloads) {
            if ((Get-FileHash -LiteralPath $download.path -Algorithm SHA256).Hash -ne $download.sha256) { throw "Downloaded file changed during cleanup" }
        }
        foreach ($artifact in $identity) {
            if ((Get-FileHash -LiteralPath $artifact.path -Algorithm SHA256).Hash -ne $artifact.sha256) { throw "Packaged artifact changed during the smoke" }
        }
        $evidence.downloaded_files_preserved = $evidence.downloads.Count -eq 3
    }
    catch {
        $evidence.status = "failed"
        $evidence.failure = $_.Exception.Message
        throw
    }
    finally {
        $evidence.finished_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        $evidencePath = Join-Path $artifactDirectory "evidence.json"
        [System.IO.File]::WriteAllText($evidencePath, ($evidence | ConvertTo-Json -Depth 12), $utf8)
        Write-Output "Packaged smoke evidence: $evidencePath"
    }
}
