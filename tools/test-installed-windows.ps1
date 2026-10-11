param(
    [Parameter(Mandatory = $true)][string]$InstallerPath,
    [Parameter(Mandatory = $true)][ValidatePattern('^[a-fA-F0-9]{64}$')][string]$ExpectedSha256
)

$ErrorActionPreference = "Stop"
# NSIS changes shared per-user registry and shortcuts, even with a custom /D.
if ($env:GITHUB_ACTIONS -ne "true" -or $env:RUNNER_ENVIRONMENT -ne "github-hosted") {
    throw "Installation test requires a disposable GitHub-hosted Windows runner"
}
Import-Module (Join-Path $PSHOME "Modules/Microsoft.PowerShell.Utility/Microsoft.PowerShell.Utility.psd1")
$installer = (Get-Item -LiteralPath $InstallerPath).FullName
if ((Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash -ne $ExpectedSha256) {
    throw "Installer SHA-256 mismatch; refusing installation"
}
$projectRoot = Split-Path -Parent $PSScriptRoot
$evidenceDirectory = Join-Path $projectRoot "artifacts/quality/installed"
$installDirectory = [System.IO.Path]::GetFullPath((Join-Path $env:LOCALAPPDATA "Programs/DrDownload-QA"))
$application = Join-Path $installDirectory "Dr. Download.exe"
$dataDirectory = Join-Path $env:APPDATA "Dr. Download"
$shortcuts = @(
    (Join-Path ([Environment]::GetFolderPath("Desktop")) "Dr. Download.lnk"),
    (Join-Path ([Environment]::GetFolderPath("Programs")) "Dr. Download.lnk")
)
function Get-InstallationEntries {
    @(Get-ItemProperty "HKCU:/Software/Microsoft/Windows/CurrentVersion/Uninstall/*",
        "HKLM:/Software/Microsoft/Windows/CurrentVersion/Uninstall/*" -ErrorAction SilentlyContinue |
        Where-Object { $_.DisplayName -match '^Dr[.] Download(?: [0-9].*)?$' })
}
if ((Get-InstallationEntries).Count -gt 0) { throw "Existing Dr. Download installation; refusing to modify it" }
foreach ($path in @($installDirectory, $dataDirectory, $evidenceDirectory) + $shortcuts) {
    if (Test-Path -LiteralPath $path) { throw "Test path already exists; refusing to modify it: $path" }
}
New-Item -ItemType Directory -Path $evidenceDirectory | Out-Null
$evidence = [ordered]@{
    schema = 1; status = "failed"; failure = $null; publishable = $false
    installer = $installer; sha256 = $ExpectedSha256.ToUpperInvariant()
    commit = $env:GITHUB_SHA; run_id = $env:GITHUB_RUN_ID
    artifact_id = $env:CANDIDATE_ARTIFACT_ID
    os = (Get-CimInstance Win32_OperatingSystem).Caption
    os_version = [Environment]::OSVersion.VersionString
    architecture = $env:PROCESSOR_ARCHITECTURE; runner_image = $env:ImageVersion
    clean_windows_10_11_verified = $false
    environment_limit = "Fresh GitHub Windows Server runner; development tools installed but excluded from PATH"
    started_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    install_exit_code = $null; uninstall_exit_code = $null
    uninstall_verified = $false; user_data_preserved = $false
    installer_lifecycle_verified = $false; preserved_files = @()
}
$originalPath = $env:PATH
$installationStarted = $false
function Invoke-Nsis([string]$Executable, [string]$Arguments) {
    $child = Start-Process -FilePath $Executable -ArgumentList $Arguments -WindowStyle Hidden -PassThru
    if (-not $child.WaitForExit(120000)) {
        & taskkill /PID $child.Id /T /F | Out-Null
        throw "NSIS timed out"
    }
    if ($child.ExitCode -ne 0) { throw "NSIS failed with exit code $($child.ExitCode)" }
    return $child.ExitCode
}
try {
    # The Python launcher may live directly in C:/Windows, so exclude that directory too.
    $env:PATH = "$env:SystemRoot/System32;$env:SystemRoot/System32/WindowsPowerShell/v1.0"
    foreach ($command in @("python", "python3", "py", "node", "npm", "ffmpeg", "ffprobe")) {
        if (Get-Command $command -ErrorAction SilentlyContinue) { throw "External runtime is visible: $command" }
    }
    $evidence.external_runtimes_on_path = $false
    $installationStarted = $true
    # NSIS /D must be last and unquoted, including paths containing spaces.
    $evidence.install_exit_code = Invoke-Nsis $installer "/S /currentuser /D=$installDirectory"
    if (-not (Test-Path -LiteralPath $application -PathType Leaf)) { throw "Installed application is missing" }
    $entries = @(Get-InstallationEntries)
    if ($entries.Count -ne 1 -or $entries[0].QuietUninstallString -ne "`"$installDirectory\Uninstall Dr. Download.exe`" /currentuser /S") {
        throw "Installed application registry identity is incorrect"
    }
    foreach ($shortcut in $shortcuts) {
        if (-not (Test-Path -LiteralPath $shortcut -PathType Leaf)) { throw "Missing installed shortcut: $shortcut" }
        $link = (New-Object -ComObject WScript.Shell).CreateShortcut($shortcut)
        if ($link.TargetPath -ne $application) { throw "Shortcut points to a different application" }
    }
    & (Join-Path $projectRoot "electron/scripts/run-packaged-ui-smoke.ps1") `
        -ApplicationPath $application -InstallerPath $installer `
        -ArtifactDirectory (Join-Path $evidenceDirectory "ui") -UserDataDirectory $dataDirectory
    $ui = Get-Content -LiteralPath (Join-Path $evidenceDirectory "ui/evidence.json") -Raw | ConvertFrom-Json
    if ($ui.status -ne "passed") { throw "Installed UI smoke did not pass" }
    $files = @((Join-Path $dataDirectory "config.json"), (Join-Path $dataDirectory "downloads.db")) + @($ui.downloads.path)
    foreach ($file in $files) {
        if ((Get-Item -LiteralPath $file).Length -le 0) { throw "Missing persisted user data: $file" }
    }
    $evidence.status = "passed"
}
catch { $evidence.failure = $_.Exception.Message; throw }
finally {
    try {
        $installedUninstaller = Join-Path $installDirectory "Uninstall Dr. Download.exe"
        if ($installationStarted -and (Test-Path -LiteralPath $installedUninstaller)) {
            # Exercise uninstall even when the external media smoke fails; keep that gate failed.
            $files = @((Join-Path $dataDirectory "config.json"), (Join-Path $dataDirectory "downloads.db"))
            $downloads = Join-Path $evidenceDirectory "ui/downloads"
            if (Test-Path -LiteralPath $downloads) { $files += @(Get-ChildItem -LiteralPath $downloads -File -Recurse | ForEach-Object { $_.FullName }) }
            foreach ($file in ($files | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf })) {
                $evidence.preserved_files += [ordered]@{ path = $file; sha256 = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash }
            }
            $uninstaller = Join-Path $evidenceDirectory "Uninstall Dr. Download.exe"
            Copy-Item -LiteralPath $installedUninstaller -Destination $uninstaller
            $evidence.uninstaller_sha256 = (Get-FileHash -LiteralPath $uninstaller -Algorithm SHA256).Hash
            # _? prevents NSIS spawning an unobserved temporary copy; observe the actual exit code.
            $evidence.uninstall_exit_code = Invoke-Nsis $uninstaller "/S /currentuser _?=$installDirectory"
            $deadline = (Get-Date).AddSeconds(60)
            while ((Test-Path -LiteralPath $installDirectory) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 500 }
            if ((Test-Path -LiteralPath $installDirectory) -or (Get-InstallationEntries).Count -gt 0) { throw "Uninstall left installed files or registry entries" }
            foreach ($shortcut in $shortcuts) {
                if (Test-Path -LiteralPath $shortcut) { throw "Uninstall left a shortcut" }
            }
            foreach ($file in $evidence.preserved_files) {
                if ((Get-FileHash -LiteralPath $file.path -Algorithm SHA256).Hash -ne $file.sha256) { throw "Uninstall changed user data: $($file.path)" }
            }
            if ((Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash -ne $ExpectedSha256) { throw "Installer changed during test" }
            $evidence.uninstall_verified = $true
            $evidence.user_data_preserved = $evidence.preserved_files.Count -gt 0
            $evidence.installer_lifecycle_verified = $evidence.status -eq "passed"
        }
        if ($evidence.status -eq "passed" -and -not $evidence.uninstall_verified) { throw "Uninstall was not verified" }
    }
    catch {
        $evidence.status = "failed"
        $evidence.failure = "$($evidence.failure); Uninstall validation: $($_.Exception.Message)"
        throw
    }
    finally {
        $env:PATH = $originalPath
        $evidence.finished_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        $evidence.installation_started = $installationStarted
        $evidence | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $evidenceDirectory "evidence.json") -Encoding utf8
    }
}
