param(
    [string]$ApplicationPath,
    [switch]$Packaged,
    [string]$ArtifactDirectory,
    [string]$EnginePath,
    [ValidateRange(1, 3600)][int]$Duration = 15,
    [string]$YouTubeUrl = "https://www.youtube.com/watch?v=aqz-KE-bpKQ",
    [string]$VimeoUrl = "https://vimeo.com/1084537"
)
$ErrorActionPreference = "Stop"
$electronRoot = Split-Path -Parent $PSScriptRoot
$repositoryRoot = Split-Path -Parent $electronRoot
if (-not $ApplicationPath) {
    $ApplicationPath = if ($Packaged) { Join-Path $electronRoot "release/win-unpacked/Dr. Download.exe" } else { Join-Path $electronRoot "node_modules/electron/dist/electron.exe" }
}
$application = [System.IO.Path]::GetFullPath($ApplicationPath)
if (-not (Test-Path -LiteralPath $application -PathType Leaf)) { throw "Application executable is unavailable" }
if (-not $ArtifactDirectory) { $ArtifactDirectory = Join-Path $repositoryRoot "artifacts/quality/streaming-implementation/real-electron-$(Get-Date -Format yyyyMMdd-HHmmss-fff)" }
$artifacts = [System.IO.Path]::GetFullPath($ArtifactDirectory)
$profile = Join-Path $artifacts "data"
$outputDirectory = Join-Path $artifacts "downloads"
if (Test-Path -LiteralPath $profile) { throw "Use a new artifact directory; the isolated profile already exists" }
New-Item -ItemType Directory -Path $profile -Force | Out-Null
New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
if ($EnginePath) {
    $engine = [System.IO.Path]::GetFullPath($EnginePath)
    if (-not (Test-Path -LiteralPath $engine -PathType Leaf)) { throw "Explicit engine fixture is unavailable" }
    New-Item -ItemType Directory -Path (Join-Path $profile "engine") | Out-Null
    Copy-Item -LiteralPath $engine -Destination (Join-Path $profile "engine/yt-dlp.exe")
}
$utf8 = New-Object System.Text.UTF8Encoding($false)
$config = @{ theme = "dark"; language = "en"; cookie_source = "none"; cookie_consent = $false; sponsorblock_consent = $false;
    output_dir = $outputDirectory; notifications = $false; auto_update_engine = $true; auto_update_app = $false; worker_threads = 1 }
[System.IO.File]::WriteAllText((Join-Path $profile "config.json"), ($config | ConvertTo-Json), $utf8)
$node = Join-Path $electronRoot "resources/node/node.exe"
if ($Packaged) { $node = Join-Path (Split-Path -Parent $application) "resources/node/node.exe" }
if (-not (Test-Path -LiteralPath $node -PathType Leaf)) { throw "Bundled Node is unavailable" }
$identity = [ordered]@{
    kind = $(if ($Packaged) { "packaged-executable" } else { "development-electron" }); publishable = $false
    commit = (& git -C $repositoryRoot rev-parse HEAD).Trim(); dirty = [bool](& git -C $repositoryRoot status --porcelain)
    command = "run-playback-ui-smoke.ps1 -Duration $Duration"; application = $application
    application_sha256 = (Get-FileHash -LiteralPath $application -Algorithm SHA256).Hash
    source_files = @(); runs = @(); status = "failed"; started_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    engine_provisioning = $(if ($EnginePath) { "Explicit existing real engine; first-run engine installation is outside this run" } else { "First-run engine installation" })
    os = [System.Environment]::OSVersion.VersionString; architecture = $env:PROCESSOR_ARCHITECTURE
    runtime_files = @()
}
if ($EnginePath) { $identity.engine_sha256 = (Get-FileHash -LiteralPath $engine -Algorithm SHA256).Hash }
if ($EnginePath) { $identity.runtime_files += @{ path = (Join-Path $profile "engine/yt-dlp.exe"); sha256 = $identity.engine_sha256 } }
$resources = if ($Packaged) { Join-Path (Split-Path -Parent $application) "resources" } else { Join-Path $electronRoot "resources" }
$runtimePaths = @("node/node.exe", "ffmpeg/ffmpeg.exe", "ffmpeg/ffprobe.exe")
if ($Packaged) { $runtimePaths += "backend/dr-download-backend.exe" }
foreach ($relative in $runtimePaths) {
    $file = Join-Path $resources $relative
    $identity.runtime_files += @{ path = $file; sha256 = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash }
}
$sourcePaths = & git -C $repositoryRoot ls-files --cached --others --exclude-standard -- backend electron tools
foreach ($relative in $sourcePaths) {
    $file = Join-Path $repositoryRoot $relative
    if (Test-Path -LiteralPath $file -PathType Leaf) { $identity.source_files += @{ path = $relative; sha256 = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash } }
}
if ($Packaged) {
    $asar = Join-Path (Split-Path -Parent $application) "resources/app.asar"
    $identity.app_asar_sha256 = (Get-FileHash -LiteralPath $asar -Algorithm SHA256).Hash
} else {
    $identity.renderer_files = @(Get-ChildItem -LiteralPath (Join-Path $electronRoot "dist") -Recurse -File | ForEach-Object {
        @{ path = $_.FullName; sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash }
    })
}

function Invoke-UiRun([bool]$Persistence) {
    $port = Get-Random -Minimum 23000 -Maximum 32000
    $arguments = @("--remote-debugging-port=$port", "--user-data-dir=`"$profile`"")
    if (-not $Packaged) { $arguments = @("`"$electronRoot`"") + $arguments }
    $applicationProcess = $null
    $smokeProcess = $null
    $owned = @{}
    $run = [ordered]@{ persistence = $Persistence; graceful_exit = $false; forced_cleanup = $false; remaining_processes = @() }
    $nodeMode = $env:ELECTRON_RUN_AS_NODE
    try {
        Remove-Item Env:ELECTRON_RUN_AS_NODE -ErrorAction SilentlyContinue
        $applicationProcess = Start-Process -FilePath $application -ArgumentList $arguments -WindowStyle Hidden -PassThru -WorkingDirectory $electronRoot
        $suffix = if ($Persistence) { "persistence" } else { "playback" }
        $script = Join-Path $PSScriptRoot "playback-ui-smoke.mjs"
        $smokeArguments = @("`"$script`"", "$port", "`"$outputDirectory`"", "`"$artifacts`"")
        $smokeArguments += if ($Persistence) { "--verify-persistence" } else { @("`"$YouTubeUrl`"", "`"$VimeoUrl`"", "--duration=$Duration") }
        $smokeProcess = Start-Process -FilePath $node -ArgumentList $smokeArguments -WindowStyle Hidden -PassThru -WorkingDirectory $electronRoot -RedirectStandardOutput (Join-Path $artifacts "$suffix-stdout.log") -RedirectStandardError (Join-Path $artifacts "$suffix-stderr.log")
        $smokeProcess.Handle | Out-Null
        $deadline = (Get-Date).AddSeconds(2 * $Duration + 450)
        do {
            $snapshot = @(Get-CimInstance Win32_Process)
            $ids = @($applicationProcess.Id)
            do {
                $before = $ids.Count
                $ids = @($ids + @($snapshot | Where-Object { $ids -contains $_.ParentProcessId } | ForEach-Object { $_.ProcessId }) | Sort-Object -Unique)
            } while ($ids.Count -gt $before)
            foreach ($child in $snapshot | Where-Object { $ids -contains $_.ProcessId }) { $owned[[string]$child.ProcessId] = $child }
            $smokeProcess.Refresh()
            if ($smokeProcess.HasExited) { break }
            if ((Get-Date) -gt $deadline) { throw "Playback smoke exceeded its bounded runtime" }
            Start-Sleep -Milliseconds 500
        } while ($true)
        $smokeProcess.WaitForExit()
        $run.smoke_exit_code = $smokeProcess.ExitCode
        $run.graceful_exit = $applicationProcess.WaitForExit(25000)
        if (-not $run.graceful_exit) { throw "Application did not exit after CDP close" }
    }
    finally {
        $env:ELECTRON_RUN_AS_NODE = $nodeMode
        if ($smokeProcess -and -not $smokeProcess.HasExited) { Stop-Process -Id $smokeProcess.Id -Force }
        if ($applicationProcess) {
            $applicationProcess.Refresh()
            if (-not $applicationProcess.HasExited) { $run.forced_cleanup = $true; & taskkill /PID $applicationProcess.Id /T /F 2>$null | Out-Null }
        }
        foreach ($child in $owned.Values) {
            $live = Get-CimInstance Win32_Process -Filter "ProcessId = $($child.ProcessId)"
            if ($live -and $live.CreationDate -eq $child.CreationDate) {
                $run.remaining_processes += @{ pid = $child.ProcessId; name = $child.Name }
                Stop-Process -Id $child.ProcessId -Force -ErrorAction SilentlyContinue
            }
        }
        $identity.runs += $run
        if ($run.remaining_processes.Count) { throw "Owned processes remained after application close; cleanup was required" }
    }
}

try {
    Invoke-UiRun $false
    $playbackEvidence = Get-Content -LiteralPath (Join-Path $artifacts "evidence.json") -Raw | ConvertFrom-Json
    if ($playbackEvidence.functional_status -ne "passed") { throw "Playback UI functional verification failed: $($playbackEvidence.failure)" }
    Invoke-UiRun $true
    foreach ($file in $identity.source_files) {
        if ((Get-FileHash -LiteralPath (Join-Path $repositoryRoot $file.path) -Algorithm SHA256).Hash -ne $file.sha256) { throw "Source changed during the smoke: $($file.path)" }
    }
    if (-not $Packaged) {
        foreach ($file in $identity.renderer_files) {
            if ((Get-FileHash -LiteralPath $file.path -Algorithm SHA256).Hash -ne $file.sha256) { throw "Compiled renderer changed during the smoke" }
        }
    }
    foreach ($file in $identity.runtime_files) {
        if ((Get-FileHash -LiteralPath $file.path -Algorithm SHA256).Hash -ne $file.sha256) { throw "Runtime changed during the smoke: $($file.path)" }
    }
    if ((Get-FileHash -LiteralPath $application -Algorithm SHA256).Hash -ne $identity.application_sha256) { throw "Application executable changed during the smoke" }
    if ($Packaged -and (Get-FileHash -LiteralPath $asar -Algorithm SHA256).Hash -ne $identity.app_asar_sha256) { throw "Packaged application changed during the smoke" }
    if ($identity.runs[-1].smoke_exit_code -eq 0) { $identity.functional_status = "passed" }
    if (@($identity.runs | Where-Object { $_.smoke_exit_code -ne 0 }).Count) { throw "Playback UI verification failed: $($playbackEvidence.failure)" }
    $identity.status = "passed"
}
catch { $identity.failure = $_.Exception.Message; throw }
finally {
    $identity.finished_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    [System.IO.File]::WriteAllText((Join-Path $artifacts "identity-and-cleanup.json"), ($identity | ConvertTo-Json -Depth 15), $utf8)
    Write-Output "Playback UI evidence: $artifacts"
}
