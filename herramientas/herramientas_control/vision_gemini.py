#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""vision_gemini.py — PUENTE DE OJOS para JARVIS Telegram (12/09/2026, orden del jefe).

El Combo (DeepSeek V4 Flash) NO procesa imagenes: JARVIS razona en texto.
Este puente le da OJOS: captura la pantalla real, la envia a GEMINI VISION
(multimodal, NUNCA por OmniRoute) y devuelve TEXTO con la descripcion y las
COORDENADAS EXACTAS de los elementos (porcentaje normalizado + pixeles reales
convertidos con la resolucion del monitor), para que JARVIS sepa a que pixeles
dirigir los clics (visual_click) y el teclado (text_input).

Uso:
  python vision_gemini.py ver "que hay en la pantalla"
  python vision_gemini.py coords "el boton Enviar"
  python vision_gemini.py resolucion
  python vision_gemini.py captura [ruta.png]

Clave de Gemini: config.json del widget (gemini_api_key) -> fallback al
desmenuzado (api_keys.json). Modelo: gemini-2.5-flash (multimodal) con
variantes de respaldo.
"""
import base64
import ctypes
import io
import json
import os
import re
import sys
import urllib.request

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_WIDGET_CFG = os.path.join(
    os.path.dirname(_BASE_DIR), "widget_voz_jarvis", "config.json")
_DESMENUZADO_CFG = (
    r"C:\PROGRAMAS\JARVIS-HRZ-DESMENUZADO\07_LIBRERIAS_DLLS\_internal\config\api_keys.json"
)
_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={key}"
_MODELOS = ("gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-flash-latest")
_TIMEOUT = 60.0
_MAX_ANCHO = 1600          # no se redimensiona en pantallas comunes (px reales 1:1)
_CALIDAD_JPEG = 85


def _cfg_widget():
    try:
        with open(_WIDGET_CFG, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def clave():
    """Clave de Gemini: primero widget, luego desmenuzado. Nunca se imprime."""
    k = str((_cfg_widget().get("gemini_api_key") or "")).strip()
    if k and k not in ("PONER_AQUI", ""):
        return k
    try:
        with open(_DESMENUZADO_CFG, encoding="utf-8") as f:
            d = json.load(f)
        k = str((d.get("gemini_api_key") or "")).strip()
        if k and k not in ("PONER_AQUI", ""):
            return k
        k = str((d.get("gemini_api_keys") or [""])[0]).strip()
        if k and k not in ("PONER_AQUI", ""):
            return k
    except Exception:
        pass
    return ""


def resolucion():
    """Resolucion REAL del monitor primario en pixeles."""
    try:
        user32 = ctypes.windll.user32
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        if w and h:
            return int(w), int(h)
    except Exception:
        pass
    return 1920, 1080


def capturar(ruta=None):
    """Captura la pantalla con CADENA de metodos (12/09/2026):
    mss -> PIL ImageGrab -> BitBlt nativo -> PrintWindow del escritorio.
    La pantalla puede estar en reposo/bloqueada; cada metodo cubre un caso.
    Devuelve (imagen_PIL, ruta) o lanza OSError si nada funciona."""
    from PIL import Image
    img = None
    # 1) mss (la misma libreria del desmenuzado)
    try:
        import mss
        with mss.mss() as s:
            mon = s.monitors[0]
            raw = s.grab(mon)
            img = Image.frombytes("RGB", raw.size, raw.rgb)
    except Exception:
        img = None
    # 2) PIL ImageGrab
    if img is None:
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
        except Exception:
            img = None
    # 3) BitBlt nativo (ctypes, funciona en sesion interactiva)
    if img is None:
        try:
            img = _capturar_bitblt()
        except Exception:
            img = None
    # 4) PrintWindow del escritorio (respaldo estilo enviar-cap)
    if img is None:
        try:
            img = _capturar_printwindow()
        except Exception:
            img = None
    if img is None:
        raise OSError("Pantalla no capturable (monitor en reposo o sin superficie visible). Pide al jefe tocar una tecla o mover el mouse y reintenta.")
    if ruta:
        img.save(ruta)
        return img, ruta
    return img, None


def _capturar_bitblt():
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    from PIL import Image
    w, h = resolucion()
    hdc_scr = user32.GetDC(0)
    if not hdc_scr:
        raise OSError("GetDC fallo")
    try:
        hdc_mem = gdi32.CreateCompatibleDC(hdc_scr)
        hbmp = gdi32.CreateCompatibleBitmap(hdc_scr, w, h)
        gdi32.SelectObject(hdc_mem, hbmp)
        if not gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_scr, 0, 0, 0x00CC0020):
            raise OSError("BitBlt fallo")

        class _BMIH(ctypes.Structure):
            _fields_ = [
                ("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD),
            ]
        bmi = _BMIH()
        bmi.biSize = ctypes.sizeof(_BMIH)
        bmi.biWidth = w
        bmi.biHeight = -h
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0
        buf = ctypes.create_string_buffer(w * h * 4)
        if not gdi32.GetDIBits(hdc_mem, hbmp, 0, h, buf, ctypes.byref(bmi), 0):
            raise OSError("GetDIBits fallo")
        return Image.frombuffer("RGBA", (w, h), buf.raw, "raw", "BGRA", 0, 1).convert("RGB")
    finally:
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(0, hdc_scr)


def _capturar_printwindow():
    import ctypes
    from ctypes import wintypes
    from PIL import Image
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    hwnd = user32.GetDesktopWindow()
    if not hwnd:
        raise OSError("sin desktop window")
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass
    r = ctypes.wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    w = r.right - r.left
    h = r.bottom - r.top
    if w <= 0 or h <= 0:
        raise OSError("rect invalido")
    hdc_scr = user32.GetWindowDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_scr)
    hbmp = gdi32.CreateCompatibleBitmap(hdc_scr, w, h)
    gdi32.SelectObject(hdc_mem, hbmp)
    if not user32.PrintWindow(hwnd, hdc_mem, 2):  # PW_RENDERFULLCONTENT
        raise OSError("PrintWindow fallo")

    class _BMIH(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long),
            ("biHeight", ctypes.c_long), ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
            ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]
    bmi = _BMIH()
    bmi.biSize = ctypes.sizeof(_BMIH)
    bmi.biWidth = w
    bmi.biHeight = -h
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = 0
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(hdc_mem, hbmp, 0, h, buf, ctypes.byref(bmi), 0)
    gdi32.DeleteObject(hbmp)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(hwnd, hdc_scr)
    return Image.frombuffer("RGBA", (w, h), buf.raw, "raw", "BGRA", 0, 1).convert("RGB")


def _img_a_b64_jpeg(img):
    """Convierte a JPEG base64. Si la imagen supera _MAX_ANCHO la redimensiona.
    Devuelve (base64, factor) donde factor = ancho_original / ancho_enviado:
    los px que diga Gemini se multiplican por factor para obtener los reales."""
    w, h = img.size
    factor = 1.0
    if w > _MAX_ANCHO:
        factor = w / float(_MAX_ANCHO)
        nw = _MAX_ANCHO
        nh = int(round(h / factor))
        img = img.resize((nw, nh))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=_CALIDAD_JPEG)
    return base64.b64encode(buf.getvalue()).decode("ascii"), factor


def _llamar_gemini(key, modelo, prompt, img_b64):
    body = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
            ]
        }],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048},
    }
    req = urllib.request.Request(
        _API_URL.format(modelo=modelo, key=key),
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
        data = json.loads(r.read().decode("utf-8"))
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return None


def _construir_prompt(pregunta, w, h):
    return (
        "Eres el sistema de VISION de JARVIS (el asistente del jefe). "
        "La imagen adjunta es UNA CAPTURA EXACTA del monitor real del usuario, "
        "cuyo tamano es EXACTAMENTE {}x{} px (ancho x alto). Los elementos "
        "estan dibujados 1:1 con los pixeles del monitor.\n"
        "Tu MISION: localizar elementos para que un robot haga CLIC EXACTO "
        "con el mouse. REGLAS INVIOLABLES:\n"
        "1. Coordenadas SIEMPRE en PIXELES REALES del monitor, formato "
        "[Nombre] -> X , Y. X va de 0 a {} e Y va de 0 a {}. "
        "NUNCA uses porcentajes ni valores fuera de ese rango.\n"
        "2. Da el CENTRO del elemento (nunca la esquina).\n"
        "3. Tras cada elemento agrega su tamano aproximado en px: | TAMANO: WxH\n"
        "4. Si NO puedes ubicar un elemento con precision, NO lo inventes y "
        "NO lo listes. Solo lista elementos REALES y VISIBLES (botones, "
        "campos de texto, iconos, tarjetas, enlaces, barras, ventanas).\n"
        "5. Al final agrega 2-3 lineas 'QUE SE VE:' resumiendo la pantalla.\n"
        "Peticion del usuario: {}\n"
        "Formato EXACTO por elemento (una linea cada uno):\n"
        "  [Nombre del elemento] -> X , Y | TAMANO: WxH\n"
        "Ejemplo:\n"
        "  [Boton Enviar] -> 847 , 665 | TAMANO: 46x24\n"
        "IMPORTANTE: coordenadas PRECISAS o no sirven. Usa el pixel central "
        "exacto. Si no hay elementos claros, di 'SIN ELEMENTOS' y describe "
        "igual la pantalla.".format(pregunta, w, h, w, h)
    )


def _convertir_a_pixeles(texto, w, h, factor=1.0):
    """Parsea los elementos que devuelve Gemini y entrega PIXELES REALES.

    Formatos aceptados por linea:
      [Nombre] -> X , Y                 (px reales del monitor, 1:1)
      [Nombre] -> X% , Y%               (porcentaje 0-100 del ancho/alto)
      [Nombre] -> X , Y | TAMANO: WxH   (px + tamano, el formato nuevo)

    Reglas de conversion:
    - Si UNO de los dos valores es > 100, se interpreta TODO como px de la
      imagen enviada y se multiplica por `factor` (normalmente 1.0, porque la
      captura no se redimensiona en monitores <= 1600 px de ancho).
    - Si AMBOS son <= 100, se interpreta como porcentaje -> px reales.
    - Cualquier coordenada FUERA del rango real (0..w, 0..h) es una
      alucinacion de Gemini: se descarta y se CONTABILIZA para avisar."""
    con = []
    descartadas = []
    # Linea nueva: [Nombre] -> X , Y [| TAMANO: WxH]
    for m in re.finditer(
            r"\[([^\]]+)\]\s*->\s*([\d.]+)\s*%?\s*,\s*([\d.]+)\s*%?"
            r"(?:\s*\|\s*TAMANO\s*:\s*(\d+)\s*[xX]\s*(\d+))?",
            texto):
        nombre = m.group(1).strip()
        vx, vy = float(m.group(2)), float(m.group(3))
        tw = m.group(4) or ""
        th = m.group(5) or ""
        if vx <= 100 and vy <= 100:
            x = int(round(vx / 100.0 * w))
            y = int(round(vy / 100.0 * h))
            origen = "%"
        else:
            x = int(round(vx * factor))
            y = int(round(vy * factor))
            origen = "px"
        # Filtro anti-alucinacion: debe caer DENTRO del monitor real
        if 0 <= x < w and 0 <= y < h:
            tam = ("  |  TAMANO: %sx%s px" % (tw, th)) if tw and th else ""
            con.append("[%s] -> centro (%.2f%%, %.2f%%)  |  PIXELES REALES: x=%d , y=%d  (%s)%s"
                       % (nombre, (x / float(w)) * 100, (y / float(h)) * 100,
                          x, y, origen, tam))
        else:
            descartadas.append("%s (%s,%s)" % (nombre, vx, vy))
    return con, descartadas


def analizar(pregunta="describe la pantalla", ruta_guardar=None):
    key = clave()
    if not key:
        print("ERROR: no hay API key de Gemini (widget ni desmenuzado)")
        return 2
    w, h = resolucion()
    try:
        img, ruta = capturar(ruta_guardar)
    except Exception as e:
        print("ERROR capturando pantalla: %r" % e)
        return 2
    b64, factor = _img_a_b64_jpeg(img)
    prompt = _construir_prompt(pregunta, w, h)
    ultimo_err = ""
    for modelo in _MODELOS:
        try:
            texto = _llamar_gemini(key, modelo, prompt, b64)
            if texto:
                print("MODELO: %s" % modelo)
                print("RESOLUCION REAL: %dx%d" % (w, h))
                print("---DESCRIPCION---")
                print(texto.strip())
                pix, descartadas = _convertir_a_pixeles(texto, w, h, factor)
                if pix:
                    print("---PIXELES REALES (para visual_click clic x= y=)---")
                    for p in pix:
                        print(p)
                if descartadas:
                    print("---DESCARTADAS (fuera de pantalla, posible alucinacion)---")
                    for d in descartadas:
                        print("  " + d)
                return 0
        except Exception as e:
            ultimo_err = repr(e)[:160]
            continue
    print("ERROR: Gemini Vision no respondio (%s)" % ultimo_err)
    return 2


def _clic_px(x, y):
    """Clic en (x,y) reutilizando computer_control (la misma mano de visual_click)."""
    try:
        from .computer_control import click
    except Exception:
        from computer_control import click
    click(x, y)


def clic_elemento(elemento):
    """CICLO COMPLETO ojos + manos: Gemini Vision localiza el elemento ->
    convierte a px reales -> visual_click hace el clic en el centro exacto."""
    key = clave()
    if not key:
        print("ERROR: no hay API key de Gemini")
        return 2
    w, h = resolucion()
    try:
        img, _ = capturar()
    except Exception as e:
        print("ERROR capturando pantalla: %r" % e)
        return 2
    b64, factor = _img_a_b64_jpeg(img)
    prompt = _construir_prompt(
        "Localiza SOLO el elemento '%s'. Responde UNA SOLA linea con su "
        "formato exacto [%s] -> X , Y | TAMANO: WxH. Si no puedes ubicarlo "
        "con precision, responde unicamente 'SIN ELEMENTO'."
        % (elemento, elemento), w, h)
    ultimo_err = ""
    for modelo in _MODELOS:
        try:
            texto = _llamar_gemini(key, modelo, prompt, b64)
            if texto:
                pix, _desc = _convertir_a_pixeles(texto, w, h, factor)
                objetivo = None
                for linea in pix:
                    nombre = linea.split("]")[0].lstrip("[")
                    if elemento.lower() in nombre.lower():
                        objetivo = linea
                        break
                if objetivo is None and pix:
                    objetivo = pix[0]  # fallback: lo unico que dio
                if objetivo is None:
                    # Intento sin coordenadas utiles: probar el siguiente
                    # modelo (reintento automatico en vez de abortar).
                    ultimo_err = "sin coordenadas validas con " + modelo
                    continue
                m = re.search(r"x=(\d+)\s*,\s*y=(\d+)", objetivo)
                if not m:
                    ultimo_err = "parseo fallido con " + modelo
                    continue
                x, y = int(m.group(1)), int(m.group(2))
                _clic_px(x, y)
                print("MODELO: %s" % modelo)
                print("VISTO: %s" % objetivo)
                print("CLIC ejecutado en (%d, %d)." % (x, y))
                return 0
        except Exception as e:
            ultimo_err = repr(e)[:160]
            continue
    print("ERROR: no se pudo ubicar '%s' en pantalla (%s). Intenta con otra descripcion del elemento." % (elemento, ultimo_err))
    return 2


def _main(argv):
    if len(argv) < 2:
        print("Acciones: ver <pregunta> | coords <elemento> | clic <elemento> | resolucion | captura [ruta]")
        return 2
    accion = argv[1].lower()
    if accion == "resolucion":
        w, h = resolucion()
        print("%dx%d" % (w, h))
        return 0
    if accion == "captura":
        ruta = argv[2] if len(argv) > 2 else None
        img, r = capturar(ruta)
        print("OK %s (%dx%d)" % (r or "memoria", img.size[0], img.size[1]))
        return 0
    if accion == "clic":
        elemento = " ".join(argv[2:]).strip()
        if not elemento:
            print("¿Sobre qué elemento hago clic? Ej: vision clic \"Boton Enviar\"")
            return 2
        return clic_elemento(elemento)
    if accion in ("ver", "coords"):
        pregunta = " ".join(argv[2:]) or "describe la pantalla"
        if accion == "coords":
            pregunta = ("Localiza SOLO el elemento '%s' y da sus coordenadas "
                        "con el formato exacto [%s] -> X%% , Y%%" % (pregunta, pregunta))
        return analizar(pregunta)
    print("Accion desconocida: %s" % accion)
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv))