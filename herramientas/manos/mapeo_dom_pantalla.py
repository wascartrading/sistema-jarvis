# mapeo_dom_pantalla.py - Mapear coordenadas del DOM (navegador) a coordenadas de
# pantalla y capturar/ampliar regiones concretas. Util para automatizar Chrome/
# Edge/Brave con click en pixeles exactos.
#
# EL PROBLEMA: getBoundingClientRect() devuelve pixeles CSS, pero el click real
# necesita pixeles de PANTALLA (fisicos). La conversion tiene 3 factores:
#   1) ZOOM del navegador (Ctrl + / Ctrl -). rect ya viene en CSS px (zoom aplicado)
#      pero NO incluye el DPI scaling de Windows.
#   2) DPI SCALING de Windows (125%, 150%...). Si tu pantalla esta al 150%, un
#      elemento que el DOM reporta en (x,y) queda en pantalla en (x*1.5, y*1.5).
#   3) POSICION de la ventana del navegador (barra de titulo, barra de pestañas).
#      El rect es relativo al viewport; hay que sumar el borde superior/izquierdo.
#
# FORMA MAS ROBUSTA (la que usa esta herramienta): instalar un script de
# marcadores que ejecute en la pagina:
#   javascript:void(document.querySelectorAll('*').forEach(...))  # (complicado)
# Mejor: usar las DevTools (CDP) para pedirle al navegador las coordenadas y
# luego CONVERTIR con el factor de DPI.
#
# Para simplificar, este modulo expone dos cosas:
#   - calcular_factor_escala(): factor de DPI de Windows (via ctypes).
#   - dom_a_pantalla(rect_css_x, rect_css_y, ventana_offset_x, ventana_offset_y):
#     convierte un rect del DOM a coordenadas de pantalla.
#   - capturar_region_ampliada(wx, wy, ww, wh, escala): captura y amplia esa parte.
#
# Requisitos: pillow, (opcional) opencv-python. Windows.

import ctypes
import json
from PIL import Image, ImageGrab

# Resampling de alta calidad compatible con Pillow 9 y 10+
try:
    _LANCZOS = Image.Resampling.LANCZOS
except AttributeError:
    _LANCZOS = Image.LANCZOS

def calcular_factor_escala():
    """Devuelve el factor de DPI de Windows (1.0, 1.25, 1.5, 1.75, 2.0 ...).
    Se lee de la configuración del monitor. Si falla, asume 1.0."""
    try:
        # Escala global del usuario (Windows 10/11)
        user32 = ctypes.windll.user32
        # SetProcessDPIAware una vez para que GetDpiForSystem funcione correcto
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor aware
        except Exception:
            pass
        dpi = user32.GetDpiForSystem()
        if dpi > 0:
            return dpi / 96.0
    except Exception:
        pass
    return 1.0

def dom_a_pantalla(x_css, y_css, ventana_izq, ventana_arr, factor=None):
    """Convierte un punto (x,y) en pixeles CSS del viewport a pixeles de pantalla.
    ventana_izq/ventana_arr: posicion del area del contenido del navegador en
    coordenadas de pantalla (puedes obtenerla con la API de ventanas o con OCR
    de los bordes). factor: escala DPI; si es None se calcula solo."""
    if factor is None:
        factor = calcular_factor_escala()
    return {
        "x_pantalla": int(x_css * factor + ventana_izq),
        "y_pantalla": int(y_css * factor + ventana_arr),
        "factor_dpi": factor,
    }

def capturar_region_ampliada(x, y, w, h, escala=3, guardar=None):
    """Captura la region (x,y,w,h) de pantalla y la amplia `escala` veces.
    Devuelve la imagen ampliada (PIL). Si `guardar` es una ruta, la guarda."""
    img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
    img = img.resize((w * escala, h * escala), _LANCZOS)
    if guardar:
        img.save(guardar)
    return img

# ------- Ejemplo de uso directo -------
if __name__ == "__main__":
    # Ejemplo: un boton cuyo getBoundingClientRect devuelve
    # {left: 180, top: 320, width: 120, height: 40}
    # y la ventana del navegador tiene su area de contenido en pantalla en (0, 90).
    rect = {"left": 180, "top": 320, "width": 120, "height": 40}
    factor = calcular_factor_escala()
    pos = dom_a_pantalla(rect["left"], rect["top"], 0, 90, factor)
    print(json.dumps({
        "rect_css": rect,
        "factor_dpi": factor,
        "esquina_dom_a_pantalla": pos,
        "centro_pantalla": {
            "x": int(pos["x_pantalla"] + rect["width"] * factor / 2),
            "y": int(pos["y_pantalla"] + rect["height"] * factor / 2),
        },
    }, indent=2))
