param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("pr", "release")]
    [string]$Level
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$evidenceDirectory = Join-Path $projectRoot "artifacts/quality"
$startedAt = (Get-Date).ToUniversalTime()
$status = "failed"
$failure = $null
New-Item -ItemType Directory -Force -Path $evidenceDirectory | Out-Null
Set-Location -LiteralPath $projectRoot

function Assert-LastExitCode([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed with exit code $LASTEXITCODE"
    }
}

function Get-WorkspaceSha256 {
    $sourceRoots = @("backend", "electron/src", "tools", "tests", "docs", ".github")
    $files = foreach ($sourceRoot in $sourceRoots) {
        Get-ChildItem -LiteralPath (Join-Path $projectRoot $sourceRoot) -File -Recurse |
            Where-Object { $_.FullName -notmatch "(__pycache__|test-artifacts|[\\/]logs[\\/])" }
    }
    $files += Get-ChildItem -LiteralPath $projectRoot -File
    $files += Get-ChildItem -LiteralPath (Join-Path $projectRoot "electron") -File |
        Where-Object { $_.Extension -in @(".js", ".json") }
    $records = foreach ($file in ($files | Sort-Object FullName -Unique)) {
        $relative = $file.FullName.Substring($projectRoot.Length).TrimStart("\", "/")
        "$relative|$((Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash)"
    }
    $bytes = [System.Text.Encoding]::UTF8.GetBytes(($records -join "`n"))
    $hasher = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([System.BitConverter]::ToString($hasher.ComputeHash($bytes))).Replace("-", "")
    }
    finally {
        $hasher.Dispose()
    }
}

try {
    python tools/contract_validator.py
    Assert-LastExitCode "contract-validator"

    python -m pip check
    Assert-LastExitCode "python-dependency-integrity"

    python -m pytest -q
    Assert-LastExitCode "pytest"

    Push-Location -LiteralPath "electron"
    node node_modules/jest/bin/jest.js --runInBand
    $jestExitCode = $LASTEXITCODE
    Pop-Location
    if ($jestExitCode -ne 0) { throw "jest failed with exit code $jestExitCode" }

    npm --prefix electron run lint
    Assert-LastExitCode "eslint"

    npm --prefix electron run build
    Assert-LastExitCode "vite-build"

    npm audit --prefix electron --audit-level=high
    Assert-LastExitCode "npm-security-audit"

    if ($Level -eq "release") {
        npm --prefix electron run package:win
        Assert-LastExitCode "windows-package"

        npm --prefix electron run smoke:packaged-ui
        Assert-LastExitCode "packaged-ui-smoke"

        & (Join-Path $projectRoot "tools/validate-release.ps1")
    }

    $status = "passed"
}
catch {
    $failure = $_.Exception.Message
    throw
}
finally {
    $evidence = [ordered]@{
        schema = 1
        level = $Level
        status = $status
        failure = $failure
        started_at_utc = $startedAt.ToString("o")
        finished_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        workspace_sha256 = Get-WorkspaceSha256
        os = [System.Environment]::OSVersion.VersionString
        architecture = $env:PROCESSOR_ARCHITECTURE
        commit = $env:GITHUB_SHA
    }
    $json = $evidence | ConvertTo-Json
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText((Join-Path $evidenceDirectory "quality-$Level.json"), $json, $utf8)
}
