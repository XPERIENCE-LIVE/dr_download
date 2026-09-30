param([switch]$CheckOnly)

$ErrorActionPreference = "Stop"
$scriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = (Resolve-Path (Join-Path $scriptDirectory "..")).Path

function Assert-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "No se encontro '$Name' en PATH. Instalalo y vuelve a ejecutar el lanzador."
    }
}

function Invoke-NativeCommand {
    param([string]$Command, [string[]]$Arguments, [string]$WorkingDirectory)
    Push-Location $WorkingDirectory
    try {
        & $Command @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "El comando '$Command $($Arguments -join ' ')' termino con codigo $LASTEXITCODE."
        }
    }
    finally { Pop-Location }
}

function Get-DepsHash {
    param([string[]]$Paths)
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    $combined = ""
    foreach ($path in $Paths) {
        if (Test-Path $path) { $combined += (Get-FileHash -Path $path -Algorithm SHA256).Hash }
    }
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($combined)
    return [System.BitConverter]::ToString($sha256.ComputeHash($bytes))
}

try {
    Write-Host "Preparando Dr. Download..."
    Assert-Command "python"
    Assert-Command "node"
    Assert-Command "npm.cmd"

    $requirementsPath = Join-Path $projectRoot "backend/requirements.txt"
    $packageJsonPath = Join-Path $scriptDirectory "package.json"
    $packageLockPath = Join-Path $scriptDirectory "package-lock.json"
    $stampPath = Join-Path $scriptDirectory ".deps-stamp.json"

    $currentHash = Get-DepsHash -Paths @($requirementsPath, $packageJsonPath, $packageLockPath)
    $previousHash = if (Test-Path $stampPath) { Get-Content $stampPath -Raw } else { "" }
    $depsChanged = $currentHash -ne $previousHash

    & python -c "import fastapi, uvicorn, yt_dlp, httpx" 2>$null
    if ($LASTEXITCODE -ne 0 -or $depsChanged) {
        Write-Host "Instalando/actualizando dependencias del motor..."
        Invoke-NativeCommand "python" @("-m", "pip", "install", "-r", "backend/requirements.txt") $projectRoot
    }
    if (-not (Test-Path (Join-Path $scriptDirectory "node_modules")) -or $depsChanged) {
        Write-Host "Instalando/actualizando dependencias de la aplicacion..."
        Invoke-NativeCommand "npm.cmd" @("install") $scriptDirectory
    }
    Set-Content -Path $stampPath -Value $currentHash -NoNewline

    Write-Host "Compilando la interfaz..."
    Invoke-NativeCommand "npm.cmd" @("run", "build") $scriptDirectory
    if ($CheckOnly) {
        Write-Host "LAUNCHER_CHECK_OK"
    }
    else {
        Write-Host "Abriendo Dr. Download..."
        # Electron asigna un puerto privado, inicia el backend y lo cierra al salir.
        Invoke-NativeCommand "npm.cmd" @("start") $scriptDirectory
    }
    exit 0
}
catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
