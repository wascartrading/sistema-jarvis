@echo off
start "" cmd /c "ping -n 3 127.0.0.1 >nul & taskkill /f /im kilo.exe & ping -n 2 127.0.0.1 >nul & start "" "C:\Users\wasc4\AppData\Roaming\npm\node_modules\@kilocode\cli\node_modules\@kilocode\cli-windows-x64\bin\kilo.exe""
