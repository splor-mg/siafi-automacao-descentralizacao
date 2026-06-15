@echo off
chcp 65001 >nul
setlocal

:: %~dp0 ja termina com barra — passa o caminho completo do script diretamente
PowerShell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar.ps1"
set PS_EXIT=%ERRORLEVEL%

pause
exit /b %PS_EXIT%