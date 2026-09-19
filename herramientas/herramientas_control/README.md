# herramientas_control — Arsenal de control fisico de la PC (JARVIS Telegram)

Portado del JARVIS-HRZ desmenuzado al sistema JARVIS Telegram (11/09/2026).
Todas las herramientas se invocan desde el agente con:

```
python "C:\Users\wasc4\Documents\Sistema Jarvis\proyectos\herramientas_control\cli.py" <modulo> <accion> [args]
```

## Modulos y ejemplos

| Modulo | Acciones | Ejemplo |
|---|---|---|
| `text_input` | escribir texto tecla a tecla (SendInput unicode, tildes/ñ), limpiar teclado | `cli.py text_input escribir "hola" 0.025` |
| `keyboard_state` | estado y control Bloq Mayus/Num | `cli.py keyboard_state set caps=1` |
| `browser` | go_to, search, youtube, media, new_tab, close_tab, scroll, abrir (SIEMPRE Brave) | `cli.py browser youtube "nombre cancion"` |
| `youtube_video` | obtener videoId del primer resultado de YouTube | `cli.py youtube_video "query"` |
| `web_search` | busqueda web (DuckDuckGo) con snippets | `cli.py web_search "consulta"` |
| `app` | abrir app/URI, cerrar por proceso, ventana min/max/restore/front/cerrar, listar | `cli.py app cerrar chrome` |
| `computer` | click, hotkey, scroll, screenshot, mover raton | `cli.py computer click x=500 y=400` |
| `screen_vision` | capturar PNG o base64 | `cli.py screen_vision capturar` |
| `visual_click` | clic por texto del elemento (UI Automation) o coordenadas | `cli.py visual_click clic "Enviar"` |
| `vision` | **OJOS de JARVIS**: manda la captura a `kiro/claude-haiku-4.5` por OMNIROUTE (modelo principal de visión desde el 16/09/2026; lista `_MODELOS` lista para añadir más) y devuelve la descripción + elementos con PIXELES REALES y tamaño para las manos (Gemini retirado del flujo activo) | `cli.py vision ver "que hay"` · `cli.py vision coords "Boton Enviar"` · `cli.py vision clic "Boton Enviar"` · `cli.py vision resolucion` |
| `terminal` | ejecutar comandos (headless o consola=1) | `cli.py terminal ejecutar "dir"` |
| `files` | buscar, abrir, papelera, limpiar_temp, duplicados MD5, vaciar_papelera | `cli.py files buscar "informe"` |
| `system` | info CPU/RAM/disco, volumen, brillo, plan energia | `cli.py system info` |
| `git` | status, add, commit, push, pull, log, clone, diff, remote | `cli.py git status --dir=C:\repo` |
| `whatsapp` | enviar mensaje por WhatsApp Web (tecleando en Brave) | `cli.py whatsapp enviar 5215512345678 "hola"` |

## Reglas de uso (importantes)

- REGLA DEL JEFE: navegador = SIEMPRE Brave; musica = SIEMPRE YouTube.
- `browser go_to` = Ctrl+L + teclear URL letra a letra (interval 25 ms) + Enter.
  Es el sistema de "escritura visible pero rapidisima" del desmenuzado.
- `interval=0` en text_input = escritura instantanea.
- `teclado_limpio()` antes/despues de teclear para evitar teclas pegadas.
- Borrar a papelera NUNCA borra definitivo (usa SHFileOperation con UNDO);
  el borrado definitivo solo con orden explicita del jefe.
- `git_control` NO modifica config ni hace push sin orden; respeta la regla
  de luz verde del cerebro JARVIS.
- Los modulos importan dependencias opcionales (PIL, uiautomation) con
  try/except: el nucleo (text_input, browser, computer, app) es 100% nativo
  Windows (ctypes) sin dependencias.