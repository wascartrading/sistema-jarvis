@echo off
REM ============================================================
REM  abrir_chat_kilo.bat - Abre el chat (TUI) de Kilo Auto Free
REM  Creado por JARVIS el 21/08/2026 para el jefe.
REM  Usa Windows Terminal si existe; si no, cmd clasico.
REM ============================================================
title Chat Kilo (JARVIS)
cd /d "C:\Users\wasc4\Documents\Sistema Jarvis"

where wt.exe >nul 2>&1
if %errorlevel%==0 (
    start "" wt.exe -d "C:\Users\wasc4\Documents\Sistema Jarvis" cmd /k kilo
) else (
    start "" cmd /k "cd /d ""C:\Users\wasc4\Documents\Sistema Jarvis"" & kilo"
)
exit /b 0
