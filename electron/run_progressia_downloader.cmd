@echo off
setlocal enabledelayedexpansion

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

    echo Corrigiendo vulnerabilidades...
    call npm audit fix --force
) else (
    echo Dependencias encontradas. Continuando...
)

REM Ejecuta la aplicación con Electron
echo.
echo Ejecutando Dr. Download 2.0...
call npx electron .
