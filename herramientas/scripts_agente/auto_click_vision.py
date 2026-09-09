#!/usr/bin/env python3
# Wally - Auto Click por Vision
# Motor: Muse Spark 1.2 + OpenCV + PyAutoGUI
# Uso: python auto_click_vision.py --click 800 500
#      python auto_click_vision.py --find plantilla.png
#      python auto_click_vision.py --capture
import sys, os, time
from pathlib import Path

try:
    import pyautogui
    import cv2
    import numpy as np
    from PIL import ImageGrab
except ImportError as e:
    print(f"Falta dependencia: {e}")
    print("Instala: pip install pyautogui opencv-python pillow mss numpy")
    sys.exit(1)

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

CAPTURE_PATH = os.path.join(os.environ.get("TEMP", "."), "vision_capture.png")

def tomar_capture(path=CAPTURE_PATH):
    """Toma capture 1366x768 y lo guarda"""
    img = ImageGrab.grab()
    img.save(path, "PNG")
    print(f"[Wally] Capture guardado: {path} {img.size[0]}x{img.size[1]}")
    return path

def click_en(x, y, delay=0.5):
    """Click exacto en coordenadas"""
    print(f"[Wally] Click en {x},{y}")
    time.sleep(delay)
    pyautogui.moveTo(int(x), int(y), duration=0.3)
    pyautogui.click()
    print("[Wally] Click hecho")

def buscar_y_click(plantilla_path, threshold=0.8, delay=0.5):
    """Busca plantilla en pantalla con OpenCV y hace click en el centro"""
    if not os.path.exists(plantilla_path):
        print(f"No existe plantilla: {plantilla_path}")
        return False
    print(f"[Wally] Buscando: {plantilla_path}")
    # capture temporal
    capture = tomar_capture()
    img = cv2.imread(capture)
    tpl = cv2.imread(plantilla_path)
    if img is None or tpl is None:
        print("Error leyendo imagenes")
        return False
    res = cv2.matchTemplate(img, tpl, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    print(f"Match max_val={max_val:.3f} en {max_loc}")
    if max_val >= threshold:
        h, w = tpl.shape[:2]
        cx = max_loc[0] + w//2
        cy = max_loc[1] + h//2
        print(f"Encontrado! Centro {cx},{cy}")
        click_en(cx, cy, delay)
        return True
    else:
        print(f"No encontrado (threshold {threshold})")
        return False

def vision_click_demo():
    """Demo: explica el flujo vision + click"""
    print("""
[Wally Vision Click - Flujo con Muse Spark 1.2]
1. Tomo capture con --capture
2. Tu me envias capture por Telegram o yo lo analizo
3. Yo (Muse Spark 1.2) veo la imagen y digo: "click en [x,y]"
4. Ejecuto: python auto_click_vision.py --click x y

Ejemplo real con tu ultimo capture 1366x768:
 - Boton 'Continuar al chat' esta aprox en [680, 450]
 - Boton 'Abrir aplicacion' aprox en [680, 390]
Prueba: python auto_click_vision.py --click 680 450
""")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        vision_click_demo()
        print("\nUso:")
        print("  --capture              -> toma capture")
        print("  --click X Y            -> click en coord")
        print("  --find plantilla.png   -> busca imagen y click")
        print("  --demo                 -> ver flujo vision")
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd == "--capture":
        tomar_capture()
    elif cmd == "--click" and len(sys.argv) >= 4:
        click_en(sys.argv[2], sys.argv[3])
    elif cmd == "--find" and len(sys.argv) >= 3:
        buscar_y_click(sys.argv[2])
    elif cmd == "--demo":
        vision_click_demo()
    else:
        print(f"Comando desconocido: {cmd}")
        vision_click_demo()
