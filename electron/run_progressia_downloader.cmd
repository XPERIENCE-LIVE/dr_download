@echo off
setlocal

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_progressia_downloader.ps1" %*
set "launcher_exit=%ERRORLEVEL%"

if not "%launcher_exit%"=="0" (
    echo.
    echo El inicio fallo. Revisa el mensaje anterior.
    pause
)

exit /b %launcher_exit%
