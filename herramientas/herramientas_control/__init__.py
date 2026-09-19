"""
herramientas_control — Arsenal de control fisico de la PC portado del
JARVIS-HRZ desmenuzado al sistema JARVIS Telegram (11/09/2026).

Modulos:
  text_input        tecleo fiable (SendInput unicode, tildes y ñ)
  keyboard_state    estado Bloq Mayus / Bloq Num
  browser_control   control del navegador (Brave): go_to, search, media, tabs
  youtube_video     abre videos de YouTube
  web_search        busquedas web (DuckDuckGo)
  app_control       ventanas y apps: abrir, cerrar, min/max/restore
  computer_control  clic, hotkeys, scroll, screenshot
  screen_vision     captura de pantalla (PNG / base64)
  visual_click      clic inteligente (UI Automation + coordenadas)
  terminal_agent    ejecutar comandos (headless o consola visible)
  file_controller   buscar, abrir, papelera, limpiar temp, organizar MD5
  system_control    CPU/RAM/disco, volumen, brillo, plan energia
  git_control       wrapper git + GitHub
  whatsapp          WhatsApp Web con tecleo

Uso desde el agente:
  python "C:\\Users\\wasc4\\Documents\\Sistema Jarvis\\proyectos\\herramientas_control\\cli.py" <modulo> <accion> [args]
"""
__version__ = "1.0.0"