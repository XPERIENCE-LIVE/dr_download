@echo off
title PROGRESSIA Downloader Launcher
cd /d %~dp0

echo.
echo 🚀 Iniciando servidor de desarrollo Vite...
start "Vite Server" cmd /k "cd /d %~dp0 && npm run dev"

echo.
echo ⚡ Iniciando aplicación Electron...
timeout /t 2 > nul
start "Electron App" cmd /k "cd /d %~dp0 && npx electron ."

exit
