"""
computer_control.py — Control directo del equipo: clic, hotkeys, scroll,
captura de pantalla. Portado del desmenuzado (pyautogui, con fallback ctypes).

Uso CLI:
  python cli.py computer click x=500 y=400 [doble=1]
  python cli.py computer hotkey ctrl+s
  python cli.py computer scroll x=500 y=400 veces=3
  python cli.py computer screenshot [ruta]
  python cli.py computer mover x=500 y=400
"""
import ctypes
import os
import time
from ctypes import wintypes

user32 = ctypes.windll.user32

# ---- clic con ctypes (sin dependencias) ----
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800
WHEEL_DELTA = 120


def mover(x, y):
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.05)
    return True


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def _hwnd_bajo_cursor(x, y):
    """HWND de la ventana bajo las coordenadas (None si falla)."""
    try:
        return user32.WindowFromPoint(_POINT(int(x), int(y)))
    except Exception:
        return None


def _activar_ventana_para_clic(x, y):
    """Si la ventana bajo el cursor NO es la activa, Windows se traga el
    primer clic solo para enfocarla (click-to-activate) y el botón no se
    pulsa. Solucion: traerla al frente; si el sistema no lo permite, hacer
    un clic de activacion previo para que el clic real llegue al control."""
    try:
        hwnd = _hwnd_bajo_cursor(x, y)
        if not hwnd:
            return
        activa = user32.GetForegroundWindow()
        if hwnd == activa:
            return
        try:
            user32.SetForegroundWindow(hwnd)
            time.sleep(0.08)
            # comprobar si de verdad quedo activa
            if user32.GetForegroundWindow() == hwnd:
                return
        except Exception:
            pass
        # fallback: clic de activacion (no se transmite al control)
        _clic_bruto(x, y, "left", intervalo=0.05)
        time.sleep(0.15)
    except Exception:
        pass


def _clic_bruto(x, y, boton="left", intervalo=0.06):
    """Eventos de clic puros en la POSICION ACTUAL del cursor."""
    down = MOUSEEVENTF_LEFTDOWN if boton == "left" else MOUSEEVENTF_RIGHTDOWN
    up = MOUSEEVENTF_LEFTUP if boton == "left" else MOUSEEVENTF_RIGHTUP
    user32.mouse_event(down, 0, 0, 0, 0)
    time.sleep(intervalo)
    user32.mouse_event(up, 0, 0, 0, 0)
    time.sleep(intervalo)


def _clic_en(coords, boton="left", doble=False, intervalo=0.06):
    x, y = int(coords[0]), int(coords[1])
    _activar_ventana_para_clic(x, y)
    mover(x, y)
    veces = 2 if doble else 1
    for _ in range(veces):
        _clic_bruto(x, y, boton, intervalo)


def click(x, y, boton="left", doble=False):
    return _clic_en((x, y), boton=boton, doble=doble)


def clic_en_pantalla(x, y, boton="left", doble=False):
    return _clic_en((x, y), boton=boton, doble=doble)


def hotkey(*teclas):
    """Combinaiones con VK (ctrl, alt, shift, letras, f1-f12...)."""
    vk = {
        "ctrl": 0x11, "control": 0x11, "alt": 0x12, "shift": 0x10,
        "win": 0x5B, "enter": 0x0D, "tab": 0x09, "esc": 0x1B, "space": 0x20,
        "back": 0x08, "del": 0x2E, "up": 0x26, "down": 0x28, "left": 0x25,
        "right": 0x27, "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
        "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74, "f6": 0x75,
        "f7": 0x76, "f8": 0x77, "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    }
    pulsadas = []
    for t in teclas:
        t = str(t).lower()
        code = vk.get(t)
        if code is None and len(t) == 1:
            code = ord(t.upper())
        if code:
            user32.keybd_event(code, 0, 0, 0)
            pulsadas.append(code)
    time.sleep(0.05)
    for code in reversed(pulsadas):
        user32.keybd_event(code, 0, 2, 0)
    return True


def scroll_en(x, y, veces=3, hacia="down"):
    mover(x, y)
    delta = -WHEEL_DELTA if hacia in ("down", "abajo") else WHEEL_DELTA
    for _ in range(int(veces)):
        user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
        time.sleep(0.05)
    return True


def screenshot(ruta=None):
    """Captura la pantalla completa a PNG (PIL si esta, si no BitBlt)."""
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        if not ruta:
            ruta = os.path.join(os.environ.get("TEMP", r"C:\Windows\Temp"), "jarvis_captura.png")
        img.save(ruta)
        return ruta
    except Exception:
        pass
    # Fallback: BitBlt + save BMP hecho a mano es muy largo; usamos PowerShell
    try:
        import subprocess
        if not ruta:
            ruta = os.path.join(os.environ.get("TEMP", r"C:\Windows\Temp"), "jarvis_captura.png")
        script = f"""
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
$b = New-Object Drawing.Bitmap([Windows.Forms.Screen]::PrimaryScreen.Bounds.Width, [Windows.Forms.Screen]::PrimaryScreen.Bounds.Height)
$g = [Drawing.Graphics]::FromImage($b)
$g.CopyFromScreen(0,0,0,0,$b.Size)
$b.Save('{ruta}')
"""
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                       capture_output=True, timeout=30)
        if os.path.exists(ruta):
            return ruta
    except Exception as e:
        print(f"[computer] screenshot fallback error: {e!r}")
    return None


def _main(argv):
    import sys
    if len(argv) < 2:
        print("Acciones: click|hotkey|scroll|screenshot|mover")
        return 2
    accion = argv[1].lower()
    resto = argv[2:]

    def _kv():
        d = {}
        for arg in resto:
            if "=" in arg:
                k, v = arg.split("=", 1)
                d[k] = v
        return d

    if accion in ("click", "clic"):
        p = _kv()
        try:
            x = int(p.get("x", resto[0] if resto else 0))
            y = int(p.get("y", resto[1] if len(resto) > 1 else 0))
        except Exception:
            print(f"Necesito x e y (enteros). Args: {resto}")
            return 2
        click(x, y, boton=p.get("boton", "left"), doble=(p.get("doble", "0") == "1"))
        print(f"Clic en ({x}, {y})")
        return 0
    if accion == "hotkey":
        if not resto:
            print("Faltan las teclas (ej: ctrl s)")
            return 2
        partes = []
        for t in resto:
            partes.extend(t.split("+"))
        hotkey(*partes)
        print(f"Hotkey: {'+'.join(partes)}")
        return 0
    if accion == "scroll":
        p = _kv()
        try:
            x = int(p.get("x", 960))
            y = int(p.get("y", 540))
        except Exception:
            x, y = 960, 540
        veces = int(p.get("veces", 3))
        hacia = p.get("hacia", "down")
        scroll_en(x, y, veces, hacia)
        print(f"Scroll {hacia} x{veces} en ({x},{y})")
        return 0
    if accion in ("screenshot", "cap"):
        ruta = resto[0] if resto else None
        r = screenshot(ruta)
        if r:
            print(f"OK {r}")
            return 0
        print("Fallo la captura")
        return 2
    if accion in ("mover", "move"):
        p = _kv()
        try:
            x = int(p.get("x", resto[0]))
            y = int(p.get("y", resto[1]))
        except Exception:
            print("Necesito x e y")
            return 2
        mover(x, y)
        print(f"Ratón en ({x},{y})")
        return 0
    print(f"Accion desconocida: {accion}")
    return 2


if __name__ == "__main__":
    _main(sys.argv)