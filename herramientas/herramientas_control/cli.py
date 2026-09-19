"""
cli.py — Dispatcher central del arsenal herramientas_control.
Permite invocar cualquier herramienta por linea de comandos:

  python cli.py text_input escribir "texto" [interval]
  python cli.py keyboard_state estado | set caps=1
  python cli.py browser go_to|search|youtube|media|abrir|new_tab|close_tab|scroll ...
  python cli.py youtube_video "busqueda"
  python cli.py web_search "consulta"
  python cli.py app abrir|cerrar|ventana|listar ...
  python cli.py computer click|hotkey|scroll|screenshot|mover ...
  python cli.py screen_vision capturar|b64
  python cli.py visual_click clic <texto> | clic x= y=
  python cli.py vision ver <pregunta> | coords <elemento> | resolucion | captura [ruta]
  python cli.py terminal ejecutar <comando> [timeout]
  python cli.py files buscar|abrir|papelera|limpiar_temp|duplicados|vaciar_papelera
  python cli.py system info|volumen|brillo|energia|papelera
  python cli.py audio estado|suena <proceso> [s]|pico|silenciar|volumen
  python cli.py git status|commit|push|...
  python cli.py whatsapp enviar <numero> <mensaje>
"""
import importlib
import os
import sys

# Asegura que el paquete padre (proyectos/) este en el path para poder hacer
# `import herramientas_control.<modulo>` desde cualquier directorio.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MODULOS = {
    "text_input": "text_input",
    "keyboard_state": "keyboard_state",
    "browser": "browser_control",
    "browser_control": "browser_control",
    "yt": "youtube_video",
    "youtube_video": "youtube_video",
    "web_search": "web_search",
    "app": "app_control",
    "app_control": "app_control",
    "computer": "computer_control",
    "computer_control": "computer_control",
    "screen_vision": "screen_vision",
    "visual_click": "visual_click",
    "vision": "vision_deepseek",
    "ojos": "vision_deepseek",
    "deepseek_vision": "vision_deepseek",
    "gemini": "vision_gemini",
    "vision_gemini": "vision_gemini",
    "terminal": "terminal_agent",
    "terminal_agent": "terminal_agent",
    "files": "file_controller",
    "file_controller": "file_controller",
    "system": "system_control",
    "system_control": "system_control",
    "git": "git_control",
    "git_control": "git_control",
    "whatsapp": "whatsapp",
    "audio": "audio_control",
    "oido": "audio_control",
    "code": "code_live",
    "code_live": "code_live",
    "codigo": "code_live",
    "self_edit": "self_edit",
    "autoedicion": "self_edit",
    "clima": "clima_control",
    "clima_control": "clima_control",
    "noticias": "noticias_control",
    "noticias_control": "noticias_control",
    "gmail": "gmail_control",
    "gmail_control": "gmail_control",
    "geo": "geolocalizacion_control",
    "geolocalizacion": "geolocalizacion_control",
    "ubicacion": "geolocalizacion_control",
    "pdf": "pdf_control",
    "pdf_control": "pdf_control",
    "convertir": "convertir_control",
    "convert": "convertir_control",
    "conversion": "convertir_control",
    "herramientas": None,  # listar
    "lista": None,
    "help": None,
}


def _ayuda():
    print(__doc__)


def _listar():
    print("Modulos disponibles:")
    for k in sorted(set(MODULOS.keys())):
        print(f"  {k}")
    print("\nEjemplos:")
    print('  python cli.py browser youtube "mi cancion"')
    print('  python cli.py browser go_to "https://www.youtube.com"')
    print('  python cli.py text_input escribir "hola mundo" 0.025')
    print('  python cli.py app ventana max youtube')
    print('  python cli.py computer screenshot')
    print('  python cli.py system info')


def main():
    if len(sys.argv) < 2:
        _ayuda()
        return 1
    mod = sys.argv[1].lower()
    if mod in ("help", "--help", "-h"):
        _ayuda()
        return 0
    if mod in ("herramientas", "lista"):
        _listar()
        return 0
    if mod not in MODULOS:
        print(f"Modulo desconocido: {mod}. Usa: python cli.py lista")
        return 2
    nombre_modulo = MODULOS[mod]
    if nombre_modulo is None:
        _listar()
        return 0
    mod_inst = importlib.import_module(f"herramientas_control.{nombre_modulo}")
    return mod_inst._main(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())