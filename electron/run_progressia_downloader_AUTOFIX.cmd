@echo off
setlocal

REM === NUEVO BLOQUE DE AUTO-INSTALACIÓN DE DEPENDENCIAS ===
echo Verificando entorno de Node.js...
where node >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo Node.js no está instalado. Por favor, instálalo desde https://nodejs.org/
    pause
    exit /b 1
)

echo Verificando e instalando dependencias necesarias...
cd /d %~dp0
if exist package.json (
    echo Ejecutando npm install para asegurar dependencias...
    call npm install
    echo Actualizando dependencias si es necesario...
    call npm update
) else (
    echo No se encontró package.json en la carpeta actual. Verifica tu proyecto.
    pause
    exit /b 1
)
REM === FIN DEL BLOQUE NUEVO ===

REM === BLOQUE ORIGINAL CONSERVADO ===
@echo off
setlocal enabledelayedexpansion

REM === Ir a carpeta del proyecto ===
cd /d C:\PROYECTOS\MediaDownloaderPROv2.0\electron

REM === Lanzar Vite en segundo plano ===
start "VITE SERVER" cmd /c "npm run dev"

REM === Esperar hasta que Vite esté listo ===
echo Esperando a que Vite se inicie...
:waitloop
timeout /t 2 >nul
for /f "tokens=*" %%i in ('netstat -aon ^| findstr ":5173"') do (
    set "line=%%i"
    if not "!line!"=="" (
        goto vite_ready
    )
)
for /f "tokens=*" %%i in ('netstat -aon ^| findstr ":5174"') do (
    set "line=%%i"
    if not "!line!"=="" (
        goto vite_ready
    )
)
goto waitloop

:vite_ready
echo Vite detectado. Iniciando Electron...

REM === Lanzar Electron ===
call node_modules\.bin\electron.cmd .

endlocal
pause

