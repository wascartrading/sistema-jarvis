"""
text_input.py — Escritura de texto fiable, con tildes y ñ.
Portado del desmenuzado: inyecta cada caracter como evento de teclado real
de Windows (SendInput / KEYBDINPUT con flag UNICODE). pyautogui pierde
caracteres no-ASCII; este modulo no.

Uso CLI:
  python cli.py text_input escribir "texto" [interval=0.025] [enter=1]
"""
import ctypes
import time
from ctypes import wintypes

user32 = ctypes.windll.user32

# --- Estructuras SendInput (mismas del desmenuzado) ---
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
INPUT_KEYBOARD = 1
VK_ENTER = 0x0D
VK_TAB = 0x09
VK_BACK = 0x08
VK_ESCAPE = 0x1B


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", INPUTUNION)]


def _enviar_inputs(inputs):
    """Envia una lista de estructuras INPUT a Windows."""
    if not inputs:
        return True
    n = len(inputs)
    arr = (INPUT * n)(*inputs)
    res = user32.SendInput(n, arr, ctypes.sizeof(INPUT))
    return res == n


def _input_unicode(ch, soltar):
    """Construye un INPUT de teclado para el caracter unicode `ch`."""
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wScan = ord(ch)
    inp.union.ki.dwFlags = KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if soltar else 0)
    return inp


def _input_vk(vk, soltar):
    """Construye un INPUT por codigo de tecla virtual (Enter, Tab, Back...)."""
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.union.ki.wVk = vk
    inp.union.ki.dwFlags = KEYEVENTF_KEYUP if soltar else 0
    return inp


def _caracter_unicode(ch):
    """Devuelve (down, up) para un caracter, manejando teclas de control."""
    if ch == "\n" or ch == "\r":
        return _input_vk(VK_ENTER, False), _input_vk(VK_ENTER, True)
    if ch == "\t":
        return _input_vk(VK_TAB, False), _input_vk(VK_TAB, True)
    if ch == "\b":
        return _input_vk(VK_BACK, False), _input_vk(VK_BACK, True)
    if ch == "\x1b":
        return _input_vk(VK_ESCAPE, False), _input_vk(VK_ESCAPE, True)
    return _input_unicode(ch, False), _input_unicode(ch, True)


def _estado_escribiendo(caps, num):
    """(conjunto) Estado real de Bloq Mayus/Num por si hay que tocarlos."""
    return (caps, num)


def normalizar(texto):
    """Normaliza comillas/guiones raros a caracteres estandar tecleables."""
    if not texto:
        return ""
    reemplazos = {
        "‘": "'", "’": "'", "“": '"', "”": '"', "„": '"',
        "–": "-", "—": "-", "−": "-", "…": "...",
        "\xa0": " ", "\u202f": " ", "\u200b": "", "\u200c": "", "\u200d": "",
        "\ufeff": "", "•": "- ",
    }
    out = []
    for ch in texto:
        out.append(reemplazos.get(ch, ch))
    return "".join(out)


def _escribir_unicode(texto, interval=0.025, enter_como_salto=True):
    """Escribe cada caracter con SendInput unicode (fiable hasta con ñ)."""
    for ch in texto:
        if ch == "\n" and not enter_como_salto:
            continue
        down, up = _caracter_unicode(ch)
        _enviar_inputs([down, up])
        if interval > 0:
            time.sleep(interval)


def _escribir_pyautogui(texto, interval=0.05, enter_como_salto=True):
    """Ultimo recurso si SendInput falla (pyautogui pierde no-ASCII)."""
    try:
        import pyautogui
    except Exception:
        return False
    for ch in texto:
        pyautogui.write(ch, interval=0.01)
        if interval > 0:
            time.sleep(interval / 2)
    return True


def _por_lineas(texto, interval=0.025, enter_como_salto=True):
    """Escribe por lineas para saltos de linea largos sin perderse."""
    for linea in texto.splitlines():
        _escribir_unicode(linea, interval=interval, enter_como_salto=False)
        down, up = _input_vk(VK_ENTER, False), _input_vk(VK_ENTER, True)
        _enviar_inputs([down, up])
        if interval > 0:
            time.sleep(interval)


def escribir(texto, interval=0.025, enter_como_salto=True, permitir_pegado=True):
    """API principal: escribe `texto` tecla a tecla en la ventana enfocada.

    interval = 0.025 (25 ms) = ritmo normal (~40 letras/seg, se ve cada
    letra). interval=0 = instantaneo. enter_como_salto: si el texto lleva
    saltos de linea, los convierte en pulsar Enter.
    """
    texto = normalizar(texto or "")
    if not texto:
        return True
    try:
        if "\n" in texto:
            _por_lineas(texto, interval=interval, enter_como_salto=enter_como_salto)
        else:
            _escribir_unicode(texto, interval=interval, enter_como_salto=enter_como_salto)
        return True
    except Exception as e:
        print(f"[text_input] error en escribir(): {e!r}")
        return _escribir_pyautogui(texto, enter_como_salto=enter_como_salto)


def teclado_limpio():
    """Suelta todas las teclas (evita teclas 'pegadas' tras un fallo)."""
    try:
        import pyautogui
        pyautogui.press([])  # no-op util para reset interno
    except Exception:
        pass
    # Suelta Shift/Ctrl/Alt/Win por si quedaron presionadas
    VK_SUELTAS = [0x10, 0x11, 0x12, 0x5B]
    for vk in VK_SUELTAS:
        _enviar_inputs([_input_vk(vk, True)])
    return True


# ------------------------- CLI -------------------------
def _main(argv):
    """Interfaz del dispatcher (cli.py) y de ejecucion directa.
    Acepta ambas formas: ["text_input", "escribir", ...] (dispatcher)
    y ["escribir", ...] (directo)."""
    args = list(argv)
    if args and "text_input" in args[0].lower():
        args = args[1:]
    if len(args) < 1:
        print("Acciones: escribir <texto> [interval] [enter] | limpiar")
        return 2
    accion = args[0].lower()
    if accion == "limpiar":
        teclado_limpio()
        print("Teclado limpio.")
        return 0
    if accion == "escribir":
        if len(args) < 2:
            print("Uso: text_input escribir <texto> [interval] [enter]")
            return 2
        texto = args[1]
        interval = float(args[2]) if len(args) > 2 else 0.025
        enter = (args[3] != "0") if len(args) > 3 else True
        ok = escribir(texto, interval=interval, enter_como_salto=enter)
        print("Escrito OK" if ok else "Fallo al escribir")
        return 0 if ok else 2
    print(f"Accion desconocida: {accion}")
    return 2


if __name__ == "__main__":
    import sys

    sys.exit(_main(sys.argv[1:]))