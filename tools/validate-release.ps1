param([Parameter(Mandatory = $true)][string]$InstallerPath)

$ErrorActionPreference = "Stop"
Import-Module (Join-Path $PSHOME "Modules/Microsoft.PowerShell.Security/Microsoft.PowerShell.Security.psd1")
Import-Module (Join-Path $PSHOME "Modules/Microsoft.PowerShell.Utility/Microsoft.PowerShell.Utility.psd1")
$installer = Get-Item -LiteralPath $InstallerPath
$signature = Get-AuthenticodeSignature -LiteralPath $installer.FullName
if ($signature.Status -ne "Valid") {
    throw "Authenticode signature is not Valid for ${InstallerPath}: $($signature.Status)"
}
if ($signature.SignerCertificate.GetNameInfo([System.Security.Cryptography.X509Certificates.X509NameType]::SimpleName, $false) -ne "SignPath Foundation") {
    throw "Unexpected Authenticode publisher"
}
if (-not $signature.TimeStamperCertificate) { throw "Authenticode timestamp is missing" }
$chain = New-Object System.Security.Cryptography.X509Certificates.X509Chain
try {
    $chain.ChainPolicy.RevocationMode = [System.Security.Cryptography.X509Certificates.X509RevocationMode]::Online
    if (-not $chain.Build($signature.TimeStamperCertificate)) { throw "Timestamp certificate chain is not valid" }
}
finally { $chain.Dispose() }
if (-not $env:CANDIDATE_ARTIFACT_ID -or -not $env:SIGNING_REQUEST_ID -or -not $env:GITHUB_SHA -or -not $env:GITHUB_RUN_ID) {
    throw "Signed artifact origin metadata is missing"
}
$projectRoot = Split-Path -Parent $PSScriptRoot
$unsigned = Get-Content -LiteralPath (Join-Path $projectRoot "artifacts/quality/installed/evidence.json") -Raw | ConvertFrom-Json
if ($unsigned.status -ne "passed" -or -not $unsigned.installer_lifecycle_verified -or
    $unsigned.verification -ne "downloads" -or -not $unsigned.download_smoke_verified -or
    $unsigned.commit -ne $env:GITHUB_SHA -or $unsigned.run_id -ne $env:GITHUB_RUN_ID -or $unsigned.artifact_id -ne $env:CANDIDATE_ARTIFACT_ID) {
    throw "Unsigned installer evidence does not match this build"
}
if ($installer.Name -ne [System.IO.Path]::GetFileName($unsigned.installer) -or
    (Get-FileHash -LiteralPath $unsigned.installer -Algorithm SHA256).Hash -ne $unsigned.sha256) {
    throw "Unsigned candidate identity changed after testing"
}
$hash = Get-FileHash -LiteralPath $installer.FullName -Algorithm SHA256
[ordered]@{
    schema = 2; publishable = $false
    installer = $installer.Name; bytes = $installer.Length; sha256 = $hash.Hash
    unsigned_sha256 = $unsigned.sha256
    commit = $env:GITHUB_SHA; run_id = $env:GITHUB_RUN_ID
    artifact_id = $env:CANDIDATE_ARTIFACT_ID; signing_request_id = $env:SIGNING_REQUEST_ID
    authenticode = $signature.Status.ToString(); publisher = $signature.SignerCertificate.Subject
    timestamp_certificate = $signature.TimeStamperCertificate.Thumbprint
    timestamp_chain_valid = $true
    verified_at_utc = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $projectRoot "artifacts/quality/release-artifact.json") -Encoding utf8
