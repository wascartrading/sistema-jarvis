' vigilar_jarvis.vbs - Ejecuta el vigilante de JARVIS SIN ventana (wscript)
' Creado por JARVIS 31/08/2026. El Task Scheduler lanza wscript.exe con este
' archivo: no se crea consola, cero parpadeo.
' Ruta corregida 04/09/2026: el ps1 vive en herramientas\manos del KIT.
CreateObject("WScript.Shell").Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File ""E:\Sistema Jarvis\herramientas\manos\vigilar_jarvis.ps1""", 0, False