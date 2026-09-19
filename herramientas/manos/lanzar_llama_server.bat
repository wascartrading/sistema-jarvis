@echo off
title Iniciador IA Local - JARVIS
echo ============================================================
echo   Iniciador de la IA local (DeepSeek-V4-Pro-Qwen3.5-4B)
echo   Al cargar el modelo, JARVIS se reinicia y conecta a el.
echo ============================================================
echo.
echo Iniciando el modelo local DeepSeek...
start "Llama Server" cmd /k "cd /d C:\Users\wasc4\Downloads\LLAMACPP && llama-server.exe -m C:\Users\wasc4\Downloads\DeepSeek-V4-Pro-Qwen3.5-4B-MTP-Q4_K_M.gguf --host 127.0.0.1 --port 8080 -c 16384 -ngl 99 -fa on --temp 0.2 --top-k 80 --repeat-penalty 1.05"

echo Esperando a que el modelo cargue (puerto 8080)...
:espera
timeout /t 5 /nobreak >nul
powershell -NoProfile -Command "if (Get-NetTCPConnection -State Listen -LocalPort 8080 -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
if errorlevel 1 goto espera

echo Modelo listo. Reiniciando el asistente (JARVIS)...
powershell -NoProfile -ExecutionPolicy Bypass -File "C:\Users\wasc4\Documents\Sistema Jarvis\Proyectos de asistente\manos\lanzar_jarvis_telegram.ps1"

echo.
echo ============================================================
echo   Listo, jefe. JARVIS conectado al modelo local.
echo   Cierra esta ventana cuando quieras.
echo ============================================================
pause >nul