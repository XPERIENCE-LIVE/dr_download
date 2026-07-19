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

try {
    Write-Host "Preparando Dr. Download..."
    Assert-Command "python"
    Assert-Command "node"
    Assert-Command "npm.cmd"

    & python -c "import fastapi, uvicorn, yt_dlp, httpx"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Instalando dependencias del motor..."
        Invoke-NativeCommand "python" @("-m", "pip", "install", "-r", "backend/requirements.txt") $projectRoot
    }
    if (-not (Test-Path (Join-Path $scriptDirectory "node_modules"))) {
        Write-Host "Instalando dependencias de la aplicacion..."
        Invoke-NativeCommand "npm.cmd" @("install") $scriptDirectory
    }

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
