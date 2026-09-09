# ocr_preciso.py - OCR de ALTA PRECISION con Tesseract (pytesseract) + OpenCV.
# Ventajas sobre Windows.Media.Ocr:
#   - Mejor precision de digitos/numero pequenos con preprocesamiento (tesseract
#     se entrena con fuentes variadas y es MUY bueno con numeros).
#   - Coordenadas de PALABRAS y de CARACTERES (image_to_data + image_to_boxes)
#     exactas y configurables.
#   - Modo pagina (PSM) para bloques, lineas, palabras o digitos sueltos.
#   - Whitelist de caracteres: p.ej solo "0123456789." para leer numeros sin
#     que confunda E13/E12/E14 (E vs 1 se resuelve limitando el alfabeto).
#
# Requisitos (instalar una sola vez, en la PC del jefe):
#   1) Tesseract OCR para Windows:
#        - Descargar e instalar de: https://github.com/UB-Mannheim/tesseract/wiki
#          (instalador de 64 bits, p.ej. tesseract-ocr-w64-setup-5.x.exe)
#        - Anotar la ruta (por defecto C:\Program Files\Tesseract-OCR\tesseract.exe)
#   2) pip install pytesseract pillow opencv-python numpy
#   3) Si hace falta python: Simple ejecutar con el que use el asistente.
#
# Uso:
#   python ocr_preciso.py                          # OCR de toda la pantalla
#   python ocr_preciso.py --region 100 200 400 150 # solo esa region
#   python ocr_preciso.py --digits                 # solo numeros (whitelist)
#   python ocr_preciso.py --scale 3 --contrast     # amplia 3x + contraste
#   python ocr_preciso.py --template icono.png     # busca icono plantilla
#

import argparse
import subprocess
import sys
import os
import json

# ---------- Configuracion ----------
# Ruta al ejecutable de tesseract. Cambiala si instalaste en otra carpeta.
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def _capturar_pantalla(region=None):
    """Captura la pantalla (o una region) con PIL.ImageGrab.
    region: (x, y, w, h) o None para toda la pantalla."""
    from PIL import ImageGrab
    if region:
        x, y, w, h = region
        bbox = (x, y, x + w, y + h)
    else:
        bbox = None
    return ImageGrab.grab(bbox=bbox)

def _preprocesar(img, scale=3, contrast=True, gray=True, threshold=None):
    """Mejora la imagen para OCR: grises, contraste, upscale, binarizacion.
    Devuelve la imagen OpenCV (numpy) ya procesada + el factor de escala."""
    import cv2
    import numpy as np

    # PIL -> numpy BGR
    img_np = np.array(img.convert("RGB"))
    bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

    # Escala de grises
    if gray:
        proc = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    else:
        proc = bgr.copy()

    # Contraste (ecualizacion de histograma CLAHE ayuda con texto gris sobre gris)
    if contrast and gray:
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        proc = clahe.apply(proc)

    # Upscale (multiplicar por entero para no deformar trazos)
    if scale > 1:
        proc = cv2.resize(proc, None, fx=scale, fy=scale,
                          interpolation=cv2.INTER_CUBIC)

    # Binarizacion (umbral adaptativo resalta digitos pequenos)
    if threshold is not None and gray:
        proc = cv2.adaptiveThreshold(
            proc, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, threshold[0], threshold[1])

    return proc, scale

def _configurar_tesseract():
    import pytesseract
    if os.path.exists(TESSERACT_CMD):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    return pytesseract

def _ocr(words_mode=True, digits=False, region=None, scale=3, contrast=True):
    """Devuelve lista de dicts: {texto, conf, x, y, w, h, cx, cy}."""
    pytesseract = _configurar_tesseract()
    import cv2

    img = _capturar_pantalla(region)
    proc, factor = _preprocesar(img, scale=scale, contrast=contrast)

    # Opciones de tesseract
    configs = "--oem 3"
    if digits:
        # SOLO numeros y decimal, con pagina enfocada a bloques de texto plano
        configs += " --psm 6 -c tessedit_char_whitelist=0123456789.,+-"
    elif words_mode:
        configs += " --psm 6"   # bloque de texto uniforme, mejor para UI
    else:
        configs += " --psm 3"   # deteccion automatica

    datos = pytesseract.image_to_data(proc, config=configs, output_type="dict")
    resultados = []
    n = len(datos["text"])
    for i in range(n):
        texto = str(datos["text"][i]).strip()
        if not texto:
            continue
        conf = datos["conf"][i]
        try:
            conf_num = float(conf)
        except (TypeError, ValueError):
            conf_num = -1
        x = int(datos["left"][i]) / factor
        y = int(datos["top"][i]) / factor
        w = int(datos["width"][i]) / factor
        h = int(datos["height"][i]) / factor
        # Sumar el desplazamiento de la region si se recorto
        if region:
            x += region[0]; y += region[1]
        resultados.append({
            "texto": texto,
            "conf": conf_num,
            "x": int(x), "y": int(y),
            "w": int(w), "h": int(h),
            "cx": int(x + w / 2), "cy": int(y + h / 2),
        })
    return resultados

def _coordenadas_caracteres(region=None, scale=3):
    """Devuelve coord de CADA caracter (para leer E vs 1, iconos, etc).
    Usa image_to_boxes (coordenadas en el sistema de la imagen escalada)."""
    pytesseract = _configurar_tesseract()
    import cv2
    img = _capturar_pantalla(region)
    proc, factor = _preprocesar(img, scale=scale)

    # Extraer texto con boxes de caracteres
    boxes = pytesseract.image_to_boxes(proc, config="--oem 3 --psm 6")
    # Leer el texto detectado para emparejar (opcional; devolvemos boxes puros)
    lineas = []
    for linea in boxes.splitlines():
        partes = linea.split()
        # formato: char left bottom right top page
        if len(partes) >= 6:
            char = partes[0]
            left = int(partes[1]) / factor
            bot = int(partes[2]) / factor
            right = int(partes[3]) / factor
            top = int(partes[4]) / factor
            h = proc.shape[0] / factor  # alto de pantalla original
            y = h - top   # tesseract da Y desde abajo
            if region:
                left += region[0]; y += region[1]
            lineas.append({
                "char": char,
                "x": int(left), "y": int(y),
                "w": int(right - left), "h": int(top - bot),
            })
    return lineas

def _template_match(template_path, region=None, umbral=0.8):
    """Busca un icono/boton por coincidencia de plantilla (OpenCV).
    Devuelve lista de {x, y, cx, cy, conf} de todas las coincidencias
    sobre el umbral. Sirve cuando el OCR no lee iconos."""
    import cv2
    import numpy as np

    img = _capturar_pantalla(region)
    img_np = np.array(img.convert("RGB"))
    pantalla = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    plantilla = cv2.imread(template_path)
    if plantilla is None:
        print(json.dumps({"error": "no se pudo leer la plantilla: " + template_path}))
        return []

    th, tw = plantilla.shape[:2]
    res = cv2.matchTemplate(pantalla, plantilla, cv2.TM_CCOEFF_NORMED)
    _, maxval, _, maxloc = cv2.minMaxLoc(res)
    coincidencias = []
    # Umbral global: posiciones con valor alto
    loc = np.where(res >= umbral)
    ya_encontradas = []
    for pt in zip(*loc[::-1]):
        x, y = pt
        # evitar duplicados demasiado cercanos
        if any(abs(x - ex) < tw * 0.6 and abs(y - ey) < th * 0.6
               for (ex, ey) in ya_encontradas):
            continue
        ya_encontradas.append((x, y))
        if region:
            sx = x + region[0]; sy = y + region[1]
        else:
            sx = x; sy = y
        coincidencias.append({
            "x": sx, "y": sy, "w": tw, "h": th,
            "cx": sx + tw // 2, "cy": sy + th // 2,
            "conf": round(float(res[y, x]), 3),
        })
    return coincidencias

def main():
    ap = argparse.ArgumentParser(description="OCR de alta precision (Tesseract+OpenCV)")
    ap.add_argument("--region", nargs=4, type=int, metavar=("X", "Y", "W", "H"),
                    help="region de pantalla x y w h")
    ap.add_argument("--digits", action="store_true", help="modo numeros (whitelist)")
    ap.add_argument("--scale", type=int, default=3, help="factor de ampliacion")
    ap.add_argument("--no-contrast", action="store_true", help="no aplicar contraste/CLAHE")
    ap.add_argument("--boxes", action="store_true", help="mostrar coord de caracteres")
    ap.add_argument("--template", type=str, default=None,
                    help="ruta a imagen (icono) para template matching")
    ap.add_argument("--threshold", type=float, default=0.8,
                    help="umbral de coincidencia para template (0..1)")
    args = ap.parse_args()

    region = tuple(args.region) if args.region else None
    contrast = not args.no_contrast

    if args.template:
        r = _template_match(args.template, region, args.threshold)
        print(json.dumps({"tipo": "template", "resultados": r}, ensure_ascii=False))
        return

    if args.boxes:
        r = _coordenadas_caracteres(region, args.scale)
        print(json.dumps({"tipo": "caracteres", "resultados": r}, ensure_ascii=False))
        return

    r = _ocr(words_mode=True, digits=args.digits, region=region,
             scale=args.scale, contrast=contrast)
    resultado = {
        "tipo": "palabras",
        "region": list(region) if region else "completa",
        "palabras": r,
    }
    print(json.dumps(resultado, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
