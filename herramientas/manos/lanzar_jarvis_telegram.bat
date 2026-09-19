@echo off
title JARVIS Telegram Bot
echo ============================================
echo   JARVIS Telegram - reinicio limpio
echo ============================================
echo Matando instancias anteriores del bot...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | Where-Object { $_.CommandLine -match 'jarvis_telegram_bot' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 2 /nobreak >nul
echo Bot iniciado. Cierra esta ventana para detenerlo.
cd /d "C:\Users\wasc4\Documents\Sistema Jarvis\proyectos"
"C:\Users\wasc4\AppData\Local\Programs\Python\Python312\python.exe" -u "jarvis_telegram_bot.py"
pause