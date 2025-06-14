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
