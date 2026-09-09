#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
===================================================================
navegador_universal.py  --  HERRAMIENTA MAESTRA DE NAVEGADOR (JARVIS)
===================================================================
Controla el navegador REAL (Brave del jefe) con Playwright para
NAVEGAR por CUALQUIER pagina web (HBO Max, YouTube, Netflix, Google,
lo que sea), hacer clic en elementos REALES (por su texto), escribir,
reproducir video y SOBRE TODO ASEGURAR DE VERDAD que la accion se hizo:
espera, detecta, verifica y reporta. Nada de clics a ciegas.

COMO TRABAJA (dos modos):
  - Si ya hay un Brave con puerto CDP 9222 activo: se CONECTA a esa
    misma ventana y usa su sesion real (login de HBO), sin abrir otra.
  - Si no hay ninguno: LANZA Brave con el perfil real del jefe y con
    el puerto CDP activo, y se conecta.
  - Al terminar se DESCONECTA pero el navegador QUEDA ABIERTO en
    pantalla para que el jefe vea el resultado.
  - Verificacion REAL de reproduccion: comprueba que existe un <video>
    y que su tiempo (currentTime) esta AVANZANDO. Si esta pausado,
    reintenta solo (tecla k, clic en el reproductor) hasta 3 veces.

COMO SE USA (modo peticion JSON, lo mas flexible):
  python navegador_universal.py --instruccion '{
     "navegar": "https://play.max.com",
     "buscar": "Red John's Footsteps",
     "clic_en": "Red John's Footsteps",
     "clic_en_rol": {"rol": "button", "nombre": "Reproducir"},
     "teclear": "texto a escribir",
     "enter": true,
     "esperar": 3,
     "confirmar": "Reproduciendo",
     "confirmar_url": "red-john",
     "verificar_video": true,
     "iniciar_reproduccion": true,
     "pantalla_completa": true,
     "salir_pantalla": false,
     "scroll": "abajo",
     "reportar": true
  }'

  (tambien se puede pasar la peticion por archivo:
   python navegador_universal.py --archivo ruta/peticion.json)

ACCIONES (todas opcionales, se ejecutan en este orden):
  - navegar:           URL a abrir (str)
  - buscar:            texto a validar que existe en la pagina (str)
  - clic_en:           texto del elemento sobre el que hacer clic (str)
  - clic_en_rol:       clic por rol/nombre, ej. {"rol":"button","nombre":"Play"}
  - teclear:           texto a escribir en el campo enfocado (str)
  - enter:             true para pulsar Enter despues de teclear (bool)
  - esperar:           segundos de pausa (float)
  - confirmar:         texto o regex que DEBE aparecer para dar por bueno (str)
  - confirmar_url:     substring que debe estar en la URL final (str)
  - verificar_video:   true para comprobar de verdad que hay video
                       y que esta reproduciendose (currentTime avanza)
  - iniciar_reproduccion: true pulsa barra espaciadora (play/pause)
  - pantalla_completa: true activa F11
  - salir_pantalla:    true sale de F11
  - traer_al_frente:   true (default) trae la ventana de Brave al frente
                       de TODAS las demas y la deja visible en pantalla
                       (restaura si estaba minimizada); si es false, no la toca
  - scroll:            "abajo" | "arriba" | cantidad (px o "0.5" = 50%)
  - reportar:          true imprime el informe final (bool, default true)

EL SCRIPT SIEMPRE IMPRIME UN INFORME FINAL con lo hecho y confirmado;
JARVIS lee ese informe y sabe si de verdad se cumplio o no.

NOTA: si Brave esta abierto SIN puerto de depuracion, el script lo
detecta y lo avisa (hay que cerrarlo y relanzar, o JARVIS lo cierra
antes con permiso del jefe).
===================================================================
"""
import sys, json, time, argparse, subprocess, urllib.request
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

BRAVE_EXE = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
PERFIL    = r"C:\Users\wasc4\AppData\Local\BraveSoftware\Brave-Browser\User Data"
PUERTO_CDP = 9222
CDP_URL   = f"http://127.0.0.1:{PUERTO_CDP}"


# ------------------------------------------------------------------
# Utilidades Windows para traer la ventana de Brave al frente
# ------------------------------------------------------------------
def _importar_win32():
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL,
                                     wintypes.HWND, wintypes.LPARAM)
    ventanas = []

    def _nombre_proceso(pid):
        try:
            h = kernel32.OpenProcess(0x1000, False, int(pid))  # QUERY_LIMITED_INFORMATION
            if not h:
                return ""
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
            kernel32.CloseHandle(h)
            return buf.value.lower()
        except Exception:
            return ""

    @WNDENUMPROC
    def _enum(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        nombre = _nombre_proceso(pid.value)
        if "brave.exe" in nombre:
            clase = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, clase, 256)
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            area = (rect.right - rect.left) * (rect.bottom - rect.top)
            ventanas.append({
                "hwnd": hwnd,
                "titulo": buf.value,
                "clase": clase.value,
                "area": area,
                "minimizada": bool(user32.IsIconic(hwnd)),
            })
        return True

    user32.EnumWindows(_enum, 0)
    return user32, ventanas


def traer_brave_al_frente(page):
    """Activa la pestana correcta en el navegador (page.bring_to_front),
    trae la VENTANA de Brave al frente de todas las demas y la deja
    MAXIMIZADA en Windows. Devuelve (ok_frente, ok_maximizada)."""
    try:
        page.bring_to_front()
    except Exception:
        pass

    try:
        import ctypes
        user32, ventanas = _importar_win32()
        if not ventanas:
            return False, False
        # elegir la ventana principal: la de mayor area (la pestaña activa
        # en pantalla completa/F11 suele ser la mas grande)
        mejor = max(ventanas, key=lambda v: v["area"])
        hwnd = mejor["hwnd"]
        # restaurar si estaba minimizada
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        # MAXIMIZAR (regla del jefe: la ventana siempre maximizada)
        user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
        user32.BringWindowToTop(hwnd)
        # truco para saltar la restriccion de Windows y tomar el foco
        user32.keybd_event(0x12, 0, 0, 0)          # ALT pulsada
        user32.SetForegroundWindow(hwnd)
        user32.keybd_event(0x12, 0, 2, 0)          # ALT soltada
        ctypes.windll.kernel32.Sleep(300)
        maximizada = bool(user32.IsZoomed(hwnd))
        return True, maximizada
    except Exception:
        return False, False


def reporte(puntos):
    print("\n===== INFORME DE NAVEGACION (JARVIS) =====")
    for k, v in puntos.items():
        print(f"  {k}: {v}")
    print("==========================================")


def cdp_activo():
    try:
        with urllib.request.urlopen(CDP_URL + "/json/version", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def lanzar_brave():
    """Lanza Brave con el perfil real del jefe y puerto CDP activo.
    Devuelve True si logro dejarlo escuchando en el puerto."""
    try:
        subprocess.Popen([
            BRAVE_EXE,
            f"--remote-debugging-port={PUERTO_CDP}",
            f"--user-data-dir={PERFIL}",
            "--start-maximized",
            "--no-first-run",
            "--disable-blink-features=AutomationControlled",
        ])
    except Exception as e:
        print(f"ERROR al lanzar Brave: {e}")
        sys.exit(2)
    # esperar a que el puerto CDP responda (hasta 30 s)
    for _ in range(30):
        if cdp_activo():
            return True
        time.sleep(1)
    return False


def dominios_iguales(u1, u2):
    try:
        return urlparse(u1 or "").netloc.lower() == urlparse(u2 or "").netloc.lower()
    except Exception:
        return False


def elegir_pagina(context, url, cerrar_duplicadas=True):
    """REUTILIZA una pestana existente (misma URL o mismo dominio) en vez
    de abrir otra, y CIERRA las pestanas duplicadas del mismo sitio.
    Devuelve (page, reutilizada: bool). Asi nunca quedan dos ventanas de
    YouTube (ni de ningun sitio) abiertas cuando JARVIS pone un video."""
    paginas = [p for p in context.pages if not p.is_closed()]
    if not paginas:
        return context.new_page(), False
    if not url:
        return paginas[0], True

    def cerrar_duplicadas_de(page_ok):
        if not cerrar_duplicadas:
            return
        for q in paginas:
            if q is not page_ok and not q.is_closed() and dominios_iguales(q.url, url):
                try:
                    q.close()
                except Exception:
                    pass

    # 1) misma URL (o contenida): reutilizar
    for p in paginas:
        try:
            u = p.url.rstrip("/") or ""
            if u and (url.rstrip("/") in u or u in url.rstrip("/")):
                cerrar_duplicadas_de(p)
                return p, True
        except Exception:
            pass
    # 2) mismo dominio (ej. youtube.com): reutilizar y cerrar las otras
    for p in paginas:
        try:
            if p.url and dominios_iguales(p.url, url):
                cerrar_duplicadas_de(p)
                return p, True
        except Exception:
            pass
    # 3) no hay ninguna parecida: abrir pestana nueva
    return context.new_page(), False


def obtener_navegador(p, url=None):
    """Conecta por CDP a Brave (ya abierto o recien lanzado).
    Devuelve (browser, context, page, modo, reutilizada)."""
    if cdp_activo():
        browser = p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0]
        page, reutil = elegir_pagina(context, url)
        return browser, context, page, "cdp", reutil
    ok = lanzar_brave()
    if not ok:
        print("ERROR: no se pudo activar el puerto CDP de Brave.")
        print("Si Brave esta abierto sin puerto de depuracion, cierrelo y reintente.")
        sys.exit(2)
    browser = p.chromium.connect_over_cdp(CDP_URL)
    context = browser.contexts[0]
    page, reutil = elegir_pagina(context, url)
    return browser, context, page, "lanzado", reutil


def verificar_video(page):
    """Comprueba que hay un <video> y que su tiempo avanza. Si esta
    pausado, reintenta reproducir solo (k, clic, espacio) hasta 3 veces."""
    js = """() => {
        const vids = Array.from(document.querySelectorAll('video'));
        if (!vids.length) return {ok:false, motivo:'no hay elemento video'};
        const v = vids.find(x => !x.paused) || vids[0];
        return {ok:true, count:vids.length, paused:v.paused,
                tiempo: v.currentTime || 0, duracion: v.duration || 0,
                reproduciendo: !v.paused};
    }"""
    def estado():
        try:
            return page.evaluate(js)
        except Exception:
            return {"ok": False, "motivo": "error evaluando video"}
    def reproducido():
        a = estado()
        time.sleep(2.0)
        b = estado()
        if not b.get("ok"):
            return b
        avance = (b.get("tiempo") or 0) - (a.get("tiempo") or 0)
        b["avance_seg"] = round(avance, 2)
        b["reproduciendo_real"] = avance > 0.2
        return b

    for intento in range(3):
        res = reproducido()
        if res.get("reproduciendo_real"):
            return res
        if not res.get("ok"):
            return res
        # intentar arrancar: k (atajo youtube), clic en el video, espacio
        try:
            page.keyboard.press("k")
            time.sleep(1)
            res2 = reproducido()
            if res2.get("reproduciendo_real"):
                return res2
        except Exception:
            pass
        try:
            page.mouse.click(400, 300)
            time.sleep(1)
            res2 = reproducido()
            if res2.get("reproduciendo_real"):
                return res2
        except Exception:
            pass
        try:
            page.keyboard.press(" ")
            time.sleep(1)
        except Exception:
            pass
    res["reproduciendo_real"] = False
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instruccion", type=str, default=None,
                    help="JSON con las acciones a realizar")
    ap.add_argument("--archivo", type=str, default=None,
                    help="Ruta a un archivo .json con la instruccion")
    args = ap.parse_args()

    if args.archivo:
        with open(args.archivo, "r", encoding="utf-8") as f:
            ins = json.load(f)
    elif args.instruccion:
        try:
            ins = json.loads(args.instruccion)
        except Exception as e:
            print(f"ERROR: instruccion JSON invalida: {e}")
            sys.exit(1)
    else:
        print("ERROR: falta --instruccion o --archivo")
        sys.exit(1)

    puntos = {"estado": "ejecutado", "modo": None,
              "navego": ins.get("navegar", "-"),
              "reutilizo_pestana": None, "pestanas_del_sitio": None,
              "encontro": None, "clico": None,
              "video": None, "url_final": None,
              "confirmado": None, "ventana_al_frente": None,
              "ventana_maximizada": None, "nota": ""}

    with sync_playwright() as p:
        browser, context, page, modo, reutil = obtener_navegador(p, ins.get("navegar"))
        puntos["modo"] = modo
        puntos["reutilizo_pestana"] = "SI" if reutil else "NO"
        if modo == "lanzado":
            time.sleep(2)  # deja que la ventana termine de arrancar

        # 1) Navegar
        if ins.get("navegar"):
            try:
                page.goto(ins["navegar"], wait_until="domcontentloaded", timeout=40000)
            except Exception:
                pass
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            time.sleep(2)

        # 2) Scroll
        if ins.get("scroll"):
            sc = str(ins["scroll"]).strip().lower()
            try:
                if sc == "abajo":
                    page.mouse.wheel(0, 900)
                elif sc == "arriba":
                    page.mouse.wheel(0, -900)
                elif sc.endswith("%"):
                    frac = float(sc[:-1]) / 100.0
                    page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {frac})")
                else:
                    page.mouse.wheel(0, int(float(sc)))
                time.sleep(1.5)
            except Exception:
                pass

        # 3) Buscar texto (validar que existe)
        if ins.get("buscar"):
            hay = True
            try:
                page.get_by_text(ins["buscar"], exact=False).first.wait_for(timeout=8000)
            except Exception:
                hay = False
            puntos["encontro"] = f"{ins['buscar']} -> {'SI' if hay else 'NO'}"
            if not hay:
                puntos["nota"] += " No se encontro el texto buscado."

        # 4) Clic por texto
        if ins.get("clic_en"):
            hecho = False
            try:
                el = page.get_by_text(ins["clic_en"], exact=False).first
                el.scroll_into_view_if_needed(timeout=5000)
                el.click(timeout=8000)
                hecho = True
            except Exception:
                pass
            puntos["clico"] = f"{ins['clic_en']} -> {'SI' if hecho else 'NO/fallo'}"
            time.sleep(1)

        # 5) Clic por rol/nombre
        if ins.get("clic_en_rol"):
            ce = ins["clic_en_rol"]
            hecho = False
            try:
                el = page.get_by_role(ce.get("rol", "button"),
                                      name=ce.get("nombre", ""), exact=False).first
                el.scroll_into_view_if_needed(timeout=5000)
                el.click(timeout=8000)
                hecho = True
            except Exception:
                pass
            puntos["clico"] = f"[{ce.get('rol')}] {ce.get('nombre')} -> {'SI' if hecho else 'NO/fallo'}"
            time.sleep(1)

        # 5b) Clic por selector CSS (para elementos sin texto claro)
        if ins.get("clic_en_selector"):
            hecho = False
            try:
                loc = page.locator(ins["clic_en_selector"]).first
                loc.scroll_into_view_if_needed(timeout=5000)
                loc.click(timeout=8000)
                hecho = True
            except Exception:
                pass
            puntos["clico"] = f"[selector] {ins['clic_en_selector']} -> {'SI' if hecho else 'NO/fallo'}"
            time.sleep(1)

        # 6) Escribir texto
        if ins.get("teclear"):
            page.keyboard.type(ins["teclear"], delay=35)
            if ins.get("enter", False):
                page.keyboard.press("Enter")
            time.sleep(1)

        # 7) Iniciar reproduccion (barra espaciadora)
        if ins.get("iniciar_reproduccion"):
            page.keyboard.press(" ")
            time.sleep(1)

        # 8) Esperar
        if ins.get("esperar"):
            time.sleep(float(ins["esperar"]))

        # 9) Verificacion REAL de video
        if ins.get("verificar_video"):
            v = verificar_video(page)
            if v.get("ok") and v.get("reproduciendo_real"):
                puntos["video"] = (f"REPRODUCIENDOSE (video {v['count']}, "
                                   f"avance {v['avance_seg']}s)")
                puntos["nota"] += " Video confirmado reproduciendose."
            elif v.get("ok"):
                puntos["video"] = (f"video presente pero pausado/sin avanzar "
                                   f"({v.get('motivo', '')})")
                puntos["nota"] += " Video presente pero no avanzando."
            else:
                puntos["video"] = f"NO hay video: {v.get('motivo', '')}"
                puntos["nota"] += " No se detecto reproduccion de video."

        # 10) Pantalla completa / salir
        if ins.get("pantalla_completa"):
            page.keyboard.press("F11")
            time.sleep(1)
            puntos["nota"] += " Pantalla completa (F11) activada."
        if ins.get("salir_pantalla"):
            page.keyboard.press("F11")
            time.sleep(1)
            puntos["nota"] += " Salida de pantalla completa."

        # 11) Confirmar texto en pantalla
        if ins.get("confirmar"):
            encontrado = False
            try:
                page.get_by_text(ins["confirmar"], exact=False).first.wait_for(timeout=15000)
                encontrado = True
            except Exception:
                try:
                    page.wait_for_selector(f"text=/{ins['confirmar']}/i", timeout=8000)
                    encontrado = True
                except Exception:
                    encontrado = False
            puntos["confirmado"] = f"{ins['confirmar']} -> {'SI' if encontrado else 'NO'}"
            if encontrado:
                puntos["nota"] += " Accion confirmada en pantalla."
            else:
                puntos["nota"] += " NO se confirmo (revisar estado)."

        # 12) Confirmar URL final
        try:
            puntos["url_final"] = page.url
        except Exception:
            pass
        if ins.get("confirmar_url"):
            hay = ins["confirmar_url"].lower() in (puntos["url_final"] or "").lower()
            puntos["confirmado"] = f"URL contiene '{ins['confirmar_url']}' -> {'SI' if hay else 'NO'}"
            if hay:
                puntos["nota"] += " URL confirmada."

        # 13) Traer la ventana de Brave al frente y MAXIMIZADA (visible)
        if ins.get("traer_al_frente", True):
            ok, maximizada = traer_brave_al_frente(page)
            puntos["ventana_al_frente"] = "SI" if ok else "NO"
            puntos["ventana_maximizada"] = "SI" if maximizada else "NO"
            if ok:
                puntos["nota"] += " Ventana de Brave al frente en pantalla."
            if maximizada:
                puntos["nota"] += " Ventana maximizada."
            else:
                puntos["nota"] += " (maximizar no confirmado)."

        # 14) Contar pestanas del mismo sitio (deben quedar 1, sin duplicados)
        try:
            ref_url = puntos["url_final"] or ins.get("navegar", "")
            dom = urlparse(ref_url).netloc.lower()
            if dom:
                n = len([q for q in context.pages if not q.is_closed()
                         and dominios_iguales(q.url, ref_url)])
                puntos["pestanas_del_sitio"] = n
                if n and n > 1:
                    puntos["nota"] += f" Quedaron {n} pestanas del sitio (duplicadas)."
        except Exception:
            pass

        # Desconectar SIN cerrar: el navegador queda vivo para el jefe
        try:
            browser.disconnect()
        except Exception:
            pass

        if ins.get("reportar", True):
            reporte(puntos)


if __name__ == "__main__":
    main()
