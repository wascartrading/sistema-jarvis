@echo off
title ABRIR OMNIROUTE - JARVIS
chcp 65001 >nul
echo ============================================
echo   ABRIR OMNIROUTE (panel de ajustes)
echo ============================================
echo.

REM Ruta de ESTA carpeta (funciona desde cualquier USB/PC)
set "KIT=%~dp0"
set "KIT=%KIT:~0,-1%"

echo Detectando OmniRoute en el puerto activo de esta PC...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%KIT%\herramientas\manos\abrir_omniroute.ps1"

echo.
echo Terminado. El panel de OmniRoute deberia estar abierto en el navegador.
echo.
pause