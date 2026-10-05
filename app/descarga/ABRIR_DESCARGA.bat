@echo off
title JARVIS - Pagina de descarga
cd /d "%~dp0"
echo Iniciando la pagina de descarga de JARVIS...
start "JARVIS Descarga" /min python servir_descarga.py 8099
timeout /t 1 >nul
start "" "http://127.0.0.1:8099/"
echo.
echo Listo. La pagina esta en http://127.0.0.1:8099/
echo En el celular, abrala en http://192.168.100.2:8099/
echo (Cierre esta ventana cuando termine.)
