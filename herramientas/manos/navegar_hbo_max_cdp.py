# navegar_hbo_max_cdp.py - Navegar a un episodio exacto en HBO Max usando
# Playwright + CDP sobre el Brave YA ABIERTO (conserva la sesion de HBO Max).
# manos de JARVIS (creado 23/08/2026, investigacion CDP del jefe).
#
# REQUISITO PREVIO: relanzar Brave una sola vez con el puerto de depuracion
# usando el MISMO perfil (conserva la sesion de HBO Max). Ejemplo:
#
#   & "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" `
#       --remote-debugging-port=9222 `
#       --user-data-dir="C:\Users\wasc4\AppData\Local\BraveSoftware\Brave-Browser\User Data"
#
# Uso:
#   python navegar_hbo_max_cdp.py                 # abre el episodio y lo busca
#   python navegar_hbo_max_cdp.py --episodio 13   # episodio a buscar (def 13)
#   python navegar_hbo_max_cdp.py --url "https://..."  # navega a URL exacta
#
# Requiere el PY312 del proyecto (playwright instalado):
#   C:\Users\wasc4\AppData\Local\Programs\Python\Python312\python.exe
import argparse
import sys
import time

DEBUG_PORT = 9222
URL = "https://play.hbomax.com"  # raiz; el navegador conserva la sesion


def conectar():
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    try:
        browser = pw.chromium.connect_over_cdp("http://127.0.0.1:%d" % DEBUG_PORT)
    except Exception as e:
        pw.stop()
        print("ERROR: no se pudo conectar a BRAVE en el puerto %d." % DEBUG_PORT)
        print("Revisa que Brave este relanzado con --remote-debugging-port=%d." % DEBUG_PORT)
        print("  Detalle: %s" % e)
        sys.exit(2)
    return pw, browser


def primera_page(browser):
    """Usa la primera pestana 'page' abierta; si no hay, crea una."""
    ctx = browser.contexts[0]
    if ctx.pages:
        return ctx.pages[0]
    return ctx.new_page()


def navegar_y_seleccionar(url, episodio):
    pw, browser = conectar()
    try:
        page = primera_page(browser)
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)  # deja que el SPA de HBO Max monte el DOM

        # 1) Intentar localizar el episodio por su texto ("Capítulo 13" o "Episode 13").
        #    HBO Max suele renderizar "Capítulo 13" (es) o "E13"/"Episode 13".
        candidatos = ["Capítulo %d" % episodio, "Episode %d" % episodio,
                      "Cap. %d" % episodio, "E%d" % episodio]
        localizador = None
        for txt in candidatos:
            loc = page.get_by_text(txt, exact=False).first
            try:
                if loc.count(timeout=3000) > 0:
                    localizador = loc
                    print("Localizado por texto: %r" % txt)
                    break
            except Exception:
                continue

        if localizador is not None:
            localizador.scroll_into_view_if_needed(timeout=5000)
            localizador.click(timeout=10000)
            print("Clic hecho en: %s" % localizador.inner_text(timeout=5000).strip())
        else:
            print("No se encontro el episodio %d por texto; busco por aria-label/data..." % episodio)
            # Alternativa: buscar por aria-label que contenga "episode" o el numero.
            loc = page.locator("[aria-label*='%d' i], [data-id*='-ep-%d']" % (episodio, episodio)) \
                      .or_(page.locator("text=%d" % episodio)).first
            loc.click(timeout=10000)
            print("Clic por aria-label/data: ok")

        # 2) Esperar a que cargue el reproductor y poner pantalla completa (F11).
        time.sleep(5)
        page.keyboard.press("F11")
        print("Pantalla completa (F11) aplicada.")
    finally:
        browser.close()  # cierra SOLO la conexion CDP, NO Brave
        pw.stop()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodio", type=int, default=13)
    ap.add_argument("--url", default=URL, help="URL exacta a la que navegar")
    ap.add_argument("--port", type=int, default=DEBUG_PORT)
    args = ap.parse_args()
    DEBUG_PORT = args.port
    if args.url != URL:
        navegar_y_seleccionar(args.url, args.episodio)
    else:
        navegar_y_seleccionar(URL, args.episodio)
    print("Listo.")
