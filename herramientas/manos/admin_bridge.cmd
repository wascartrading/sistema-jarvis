@echo off
rem Lanzador de la tarea JARVIS_ELEVADO: ejecuta el puente de administrador.
rem Usa %~dp0 (carpeta donde vive este .cmd) para funcionar en cualquier PC/kit.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0admin_bridge.ps1"
