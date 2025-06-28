@echo off
setlocal enabledelayedexpansion

REM Convenience launcher for Dr. Download 2.0 on Windows
REM Installs Node.js dependencies if missing and then starts the app

cd /d "%~dp0"

echo.
echo ===============================
echo  Dr. Download 2.0
echo  Inicializando entorno...
echo ===============================
echo.

REM Verifica si node_modules existe
if not exist node_modules (
    echo Dependencias no encontradas. Instalando...
    call npm install

    echo Actualizando dependencias...
    call npm update
    REM Ejecuta "npm audit" manualmente para revisar vulnerabilidades
REM     call npm audit fix --force
) else (
    echo Dependencias encontradas. Continuando...
)

REM Ejecuta la aplicación con Electron
echo.
echo Ejecutando Dr. Download 2.0...
call npx electron .
