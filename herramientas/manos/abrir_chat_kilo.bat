@echo off
REM ============================================================
REM  abrir_chat_kilo.bat - Abre el chat (TUI) de Kilo Auto Free
REM  Creado por JARVIS el 21/08/2026 para el jefe.
REM  Usa Windows Terminal si existe; si no, cmd clasico.
REM ============================================================
title Chat Kilo (JARVIS)
REM 04/09/2026 (KIT PORTATIL): usa la raiz del kit en vez de rutas viejas.
cd /d "%~dp0..\.."

where wt.exe >nul 2>&1
if %errorlevel%==0 (
    start "" wt.exe -d "%~dp0..\.." cmd /k kilo
) else (
    start "" cmd /k "cd /d ""%~dp0..\.."" & kilo"
)
exit /b 0
