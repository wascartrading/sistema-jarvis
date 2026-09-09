@echo off
title JARVIS - Kit Portatil
chcp 65001 >nul
echo ============================================
echo   JARVIS PORTATIL - Iniciador automatico
echo ============================================
echo.

REM Obtener la ruta de ESTA carpeta (funciona desde cualquier USB/PC)
set "KIT=%~dp0"
set "KIT=%KIT:~0,-1%"

echo Ruta del kit: %KIT%
echo.
echo Preparando el sistema... (primera vez puede tardar unos minutos)
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%KIT%\setup\instalar_jarvis.ps1" -KitDir "%KIT%"

echo.
echo Proceso terminado. Revise el mensaje de arriba.
pause
