"""
screen_vision.py — Captura de pantalla (PNG o base64) para analisis visual.
Portado del desmenuzado (_capture_screen_base64 simplificado).

Uso CLI:
  python cli.py screen_vision capturar [ruta]
  python cli.py screen_vision b64
"""
import base64
import os


def _capture_screen_base64():
    """Captura y devuelve base64 de la imagen (para vision IA)."""
    from .computer_control import screenshot
    ruta = screenshot()
    if not ruta:
        return None
    with open(ruta, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def capturar(ruta=None):
    from .computer_control import screenshot
    r = screenshot(ruta)
    if not r:
        return None
    return r


def _main(argv):
    import sys
    if len(argv) < 2:
        print("Acciones: capturar [ruta] | b64")
        return 2
    accion = argv[1].lower()
    if accion == "b64":
        b = _capture_screen_base64()
        if not b:
            print("Fallo al capturar")
            return 2
        print(b[:200])
        print(f"...[total {len(b)} chars base64]")
        return 0
    if accion == "capturar":
        ruta = argv[2] if len(argv) > 2 else None
        r = capturar(ruta)
        if r:
            print(f"OK {r}")
            return 0
        print("Fallo la captura")
        return 2
    print(f"Accion desconocida: {accion}")
    return 2


if __name__ == "__main__":
    _main(sys.argv)