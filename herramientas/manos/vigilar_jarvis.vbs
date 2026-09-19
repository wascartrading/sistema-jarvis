' vigilar_jarvis.vbs - Ejecuta el vigilante de JARVIS SIN ventana (wscript)
' Creado por JARVIS 31/08/2026. El Task Scheduler lanza wscript.exe con este
' archivo: no se crea consola, cero parpadeo.
' Ruta corregida: el ps1 vive en Proyectos de asistente\manos.
CreateObject("WScript.Shell").Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -File ""C:\Users\wasc4\Documents\Sistema Jarvis\Proyectos de asistente\manos\vigilar_jarvis.ps1""", 0, False