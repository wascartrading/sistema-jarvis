"""
browser_control.py — Control del navegador activo (SIEMPRE Brave, regla del jefe).
Portado del desmenuzado: go_to (Ctrl+L + teclear URL letra a letra + Enter),
search, media (k/f/m/l/j/.), tabs, scroll, navigate.

Uso CLI:
  python cli.py browser go_to "https://..."
  python cli.py browser search "query"
  python cli.py browser youtube "cancion"          (busca y abre video)
  python cli.py browser media play|pause|mute|full|next|prev
  python cli.py browser new_tab [url]  |  browser close_tab
  python cli.py browser scroll down|up [cantidad]
  python cli.py browser abrir  (abre Brave si esta cerrado)
"""
import ctypes
import re
import subprocess
import time
import urllib.parse
from ctypes import wintypes

from . import text_input
from .text_input import escribir, teclado_limpio

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
BRAVE_EXE = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
BRAVE_CLASE = "Chrome_WidgetWin_1"
_BRAVE_TITULOS = ("Brave", "YouTube", "Google", "DuckDuckGo", "Bing", "wa.me", "facebook", "instagram", "netflix", "twitch", "github", "wikipedia")
INTERVALO_TECLEO = 0.025  # 25 ms entre letras (ritmo normal, se ve cada letra)

# --- Ventanas ---
_EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def _find_browser_window():
    """Devuelve el HWND de una ventana de navegador abierta (clase Chrome)."""
    encontrados = []

    @_EnumWindowsProc
    def _cb(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        clase = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, clase, 256)
        if clase.value != BRAVE_CLASE:
            return True
        titulo = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, titulo, 512)
        if titulo.value.strip():
            encontrados.append((hwnd, titulo.value))
        return True

    user32.EnumWindows(_cb, 0)
    # Prioriza ventanas con titulo reconocible de navegador
    for hwnd, titulo in encontrados:
        if any(k.lower() in titulo.lower() for k in _BRAVE_TITULOS):
            return hwnd, titulo
    return (encontrados[0] if encontrados else (None, None))


def _focus_window(hwnd, reintentos=4):
    """Trae la ventana al frente y le da foco REAL.

    Windows bloquea SetForegroundWindow entre procesos (foreground lock):
    por eso el Ctrl+L y el tecleo se perdian. Aqui se roba el foco con
    AttachThreadInput + BringWindowToTop + doble SetForegroundWindow y se
    VERIFICA con GetForegroundWindow que el foco quedo en la ventana.
    """
    if not hwnd:
        return False
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
    user32.ShowWindow(hwnd, 5)      # SW_SHOW
    time.sleep(0.15)
    hilo_actual = kernel32.GetCurrentThreadId()
    for _ in range(reintentos):
        hilo_objetivo = user32.GetWindowThreadProcessId(hwnd, None)
        adjunto = False
        if hilo_objetivo != hilo_actual:
            # Roba el foco: nos "enganchamos" al thread de la ventana objetivo
            adjunto = user32.AttachThreadInput(hilo_actual, hilo_objetivo, True)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.05)
        user32.SetForegroundWindow(hwnd)
        if adjunto:
            user32.AttachThreadInput(hilo_actual, hilo_objetivo, False)
        time.sleep(0.25)
        if user32.GetForegroundWindow() == hwnd:
            return True
    # Ultimo intento directo
    user32.SetForegroundWindow(hwnd)
    time.sleep(0.3)
    return user32.GetForegroundWindow() == hwnd


def _abrir_brave(url=None):
    """Abre Brave (con URL opcional) y devuelve HWND ya enfocado."""
    cmd = [BRAVE_EXE]
    if url:
        cmd.append(url)
    subprocess.Popen(cmd, shell=False)
    for _ in range(20):
        time.sleep(0.3)
        hwnd, _t = _find_browser_window()
        if hwnd:
            _focus_window(hwnd)
            return hwnd
    return None


def _navegador_activo():
    """Devuelve hwnd de navegador abierto o lo abre si hace falta."""
    hwnd, _t = _find_browser_window()
    if hwnd:
        _focus_window(hwnd)
        return hwnd
    return _abrir_brave()


def _titulo_ventana(hwnd):
    """Devuelve el titulo actual de la ventana."""
    try:
        titulo = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, titulo, 512)
        return titulo.value.strip()
    except Exception:
        return ""


def _esperar_navegacion(hwnd, url, timeout=2.5):
    """Espera a que el titulo de la ventana cambie (senal de que navego)."""
    titulo_inicial = _titulo_ventana(hwnd)
    marca = url.lower()
    inicio = time.time()
    while time.time() - inicio < timeout:
        titulo = _titulo_ventana(hwnd)
        if titulo != titulo_inicial:
            return True
        # Si el titulo nuevo ya menciona la URL (dominio o parte clave), listo
        if marca and any(p in titulo.lower() for p in _BRAVE_TITULOS):
            return True
        time.sleep(0.3)
    return False


def go_to(url, interval=INTERVALO_TECLEO):
    """Navega a `url` en Brave de forma FIABLE.

    - Si Brave esta cerrado: se abre DIRECTAMENTE con la URL como argumento
      (cero tecleo, cero riesgo de perder letras).
    - Si Brave esta abierto: foco verificado (robo de foco), Ctrl+L, tecleo
      letra a letra y Enter; si el titulo no cambio, reintenta y, como ultimo
      respaldo, abre la URL en pestana nueva via el exe.
    """
    hwnd, _t = _find_browser_window()
    if not hwnd:
        # No hay navegador -> abrir directo con la URL (sin teclear nada)
        if _abrir_brave(url):
            return True, f"Navegando a {url}"
        return False, "No se pudo abrir el navegador"
    if not _focus_window(hwnd):
        # Foco imposible -> respaldo: abrir URL directa en pestana nueva
        _abrir_brave(url)
        return True, f"Navegando a {url} (via directa)"
    for intento in range(2):
        teclado_limpio()
        hotkey("ctrl", "l")
        time.sleep(0.35)
        escribir(url, interval=interval)
        time.sleep(0.15)
        hotkey("enter")
        if _esperar_navegacion(hwnd, url, timeout=2.5):
            return True, f"Navegando a {url}"
        if intento == 0:
            time.sleep(0.4)
    # El tecleo no cuajo dos veces -> abrir directo (pestana nueva)
    _abrir_brave(url)
    return True, f"Navegando a {url} (via directa)"


def hotkey(*teclas):
    """Pulsa una combinacion (ctrl+l, ctrl+t, enter, etc.)."""
    vk_map = {
        "ctrl": 0x11, "control": 0x11, "alt": 0x12, "shift": 0x10,
        "enter": 0x0D, "return": 0x0D, "tab": 0x09, "esc": 0x1B,
        "space": 0x20, "back": 0x08, "del": 0x2E, "up": 0x26, "down": 0x28,
        "left": 0x25, "right": 0x27, "home": 0x24, "end": 0x23,
        "pageup": 0x21, "pagedown": 0x22, "f5": 0x74,
        "k": 0x4B, "l": 0x4C, "j": 0x4A, "f": 0x46, "m": 0x4D,
        "n": 0x4E, "p": 0x50, "t": 0x54, "w": 0x57, ".": 0xBE, " ": 0x20,
    }
    pulsadas = []
    try:
        for t in teclas:
            vk = vk_map.get(str(t).lower(), None)
            if vk is None and len(str(t)) == 1:
                vk = ord(str(t).upper())
            if vk:
                user32.keybd_event(vk, 0, 0, 0)
                pulsadas.append(vk)
        time.sleep(0.05)
        for vk in reversed(pulsadas):
            user32.keybd_event(vk, 0, 2, 0)  # KEYUP
        return True
    except Exception as e:
        print(f"[browser] hotkey error: {e!r}")
        return False


def search(query, interval=INTERVALO_TECLEO):
    """Busca `query` en el navegador (barra de direcciones, Buscar con)."""
    return go_to("https://www.google.com/search?q=" + urllib.parse.quote(query), interval=interval)


def youtube(query, interval=INTERVALO_TECLEO):
    """Abre la busqueda en YouTube (o video directo si es un videoId)."""
    from .youtube_video import obtener_video_url
    url = obtener_video_url(query)
    if not url:
        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
    return go_to(url, interval=interval)


def _media(action):
    """Atajos de reproduccion de YouTube: play, pause, mute, full, next, prev, skip."""
    atajos = {
        "play": "k", "pause": "k", "play_pause": "k",
        "mute": "m", "full": "f", "fullscreen": "f",
        "next": "shift+n", "prev": "shift+p", "anterior": "shift+p",
        "skip": ".", "adelantar": "l", "retroceder": "j",
    }
    combo = atajos.get(action)
    if not combo:
        return False, f"Accion media desconocida: {action}"
    hwnd = _navegador_activo()
    if not hwnd:
        return False, "No hay navegador abierto"
    partes = combo.split("+")
    hotkey(*partes)
    return True, f"Media: {action}"


def new_tab(url=None):
    """Abre pestaña nueva (Ctrl+T) y navega a la URL si se pasa."""
    hwnd = _navegador_activo()
    if not hwnd:
        return False
    _focus_window(hwnd)
    teclado_limpio()
    hotkey("ctrl", "t")
    time.sleep(0.35)
    if url:
        time.sleep(0.2)
        escribir(url, interval=INTERVALO_TECLEO)
        hotkey("enter")
    return True


def close_tab():
    hotkey("ctrl", "w")
    return True


def scroll(direction="down", cantidad=3):
    """Scroll en la pagina (PageDown/PageUp)."""
    hwnd = _navegador_activo()
    if not hwnd:
        return False, "No hay navegador abierto"
    tecla = "pagedown" if direction == "down" else "pageup"
    for _ in range(int(cantidad)):
        hotkey(tecla)
        time.sleep(0.1)
    return True, f"Scroll {direction} x{cantidad}"


def abrir(url=None):
    """Abre el navegador (Brave) y opcionalmente una URL."""
    if not url:
        hwnd = _abrir_brave("https://www.youtube.com")
    else:
        hwnd = _abrir_brave(url)
    if hwnd:
        return True, "Brave abierto"
    return False, "No se pudo abrir Brave"


ACCIONES = {
    "go_to": go_to, "goto": go_to, "ir": go_to,
    "search": search, "buscar": search,
    "youtube": youtube, "yt": youtube,
    "media": _media, "play": _media, "pause": _media, "mute": _media,
    "full": _media, "fullscreen": _media, "next": _media, "prev": _media,
    "abrir": abrir, "open": abrir, "navegador": abrir,
    "new_tab": new_tab, "nueva_pestana": new_tab,
    "close_tab": close_tab, "cerrar_pestana": close_tab,
    "scroll": scroll,
}


def _main(argv):
    if len(argv) < 2:
        print("Acciones: go_to|search|youtube|media|abrir|new_tab|close_tab|scroll")
        return 1
    accion = argv[1].lower()
    resto = argv[2:]
    if accion in ("media", "play", "pause", "mute", "full", "next", "prev"):
        sub = resto[0] if resto else accion
        ok, msg = _media(sub)
        print(msg)
        return 0 if ok else 2
    if accion in ("abrir", "open", "navegador"):
        ok, msg = abrir(resto[0] if resto else None)
        print(msg)
        return 0 if ok else 2
    if accion in ("new_tab", "nueva_pestana"):
        ok = new_tab(resto[0] if resto else None)
        print("Pestana nueva" if ok else "Error")
        return 0 if ok else 2
    if accion == "close_tab":
        close_tab()
        print("Pestana cerrada")
        return 0
    if accion == "scroll":
        direccion = resto[0] if resto else "down"
        cant = int(resto[1]) if len(resto) > 1 else 3
        ok, msg = scroll(direccion, cant)
        print(msg)
        return 0 if ok else 2
    if accion in ("go_to", "goto", "ir"):
        if not resto:
            print("Falta la URL")
            return 2
        ok, msg = go_to(resto[0])
        print(msg)
        return 0 if ok else 2
    if accion in ("search", "buscar"):
        if not resto:
            print("Falta la busqueda")
            return 2
        ok, msg = search(" ".join(resto))
        print(msg)
        return 0 if ok else 2
    if accion in ("youtube", "yt"):
        if not resto:
            print("Falta la cancion")
            return 2
        ok, msg = youtube(" ".join(resto))
        print(msg)
        return 0 if ok else 2
    print(f"Accion desconocida: {accion}")
    return 2


if __name__ == "__main__":
    import sys
    sys.exit(_main(sys.argv))