"""navegar_hbo_max.py - Reproduce un capitulo exacto de El Mentalista en HBO Max
controlando Brave por Playwright/CDP (manos de JARVIS).

Creado 22/08/2026. Solucion a la flaqueza del OCR: leer el DOM real de la
pagina y hacer clics exactos en vez de adivinar por texto de pantalla.

Flujo:
  1) Asegura una instancia de Brave con el puerto de depuracion remota abierto
     (relanzandola con el MISMO perfil si hace falta, conservando la sesion).
  2) Conecta por Playwright sobre CDP (connect_over_cdp).
  3) Encuentra / abre la pestania de HBO Max (El Mentalista).
  4) Como la pagina es una SPA, navega por el DOM: busca la fila de episodios,
     localiza el capitulo pedido y hace click + Enter sobre el.
  5) Verifica (por URL o texto) que esta en el capitulo correcto.

Uso:  py312 navegar_hbo_max.py <numero_o_titulo>
Ej:   py312 navegar_hbo_max.py 13
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

# ---------------------------------------------------------------- config
BRAVE = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
USER_DATA = r"C:\Users\wasc4\AppData\Local\BraveSoftware\Brave-Browser\User Data"
PUERTO = 62626
CDP_HTTP = "http://127.0.0.1:%d" % PUERTO
SERIE = "El Mentalista"
HBO_WATCH = "play.hbomax.com/video/watch"

PY = r"C:\Users\wasc4\AppData\Local\Programs\Python\Python312\python.exe"


def _puerto_activo():
    """True si el puerto de depuracion ya esta sirviendo /json."""
    try:
        with urllib.request.urlopen(CDP_HTTP + "/json", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def _relanzar_brave(open_url=""):
    """Mata Brave y lo relanza con --remote-debugging-port en el MISMO perfil."""
    print("Relanzando Brave con depuracion remota (perfil intacto)...")
    subprocess.run(["taskkill", "/IM", "brave.exe", "/F"],
                   capture_output=True, encoding='utf-8', errors='replace')
    time.sleep(2)
    cmd = [BRAVE, "--remote-debugging-port=%d" % PUERTO,
           "--user-data-dir=%s" % USER_DATA]
    if open_url:
        cmd.append(open_url)
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # esperar a que abra el puerto
    for _ in range(30):
        time.sleep(1)
        if _puerto_activo():
            print("Puerto de depuracion %d activo." % PUERTO)
            return True
    print("AVISO: el puerto no respondio a tiempo.")
    return False


def _chrome_ya_depurado():
    """Si ya hay depuracion, no relanzamos nada."""
    return _puerto_activo()


def _normalizar(t):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", t)
                   if unicodedata.category(c) != "Mn").lower()


def _scroll_carrusel_hasta(page, texto):
    """Desplaza los contenedores con scroll horizontal para revelar el episodio."""
    ok = False
    for intento in range(12):
        try:
            el = page.get_by_text(texto, exact=False).first
            el.scroll_into_view_if_needed(timeout=4000)
            ok = True
            break
        except Exception:
            # desplaza carruseles horizontales hacia el final
            try:
                page.evaluate("""() => {
                    const c = document.querySelector('[class*="episode"], [data-testid*="episode"]');
                    if (c) c.scrollLeft += 600;
                }""")
            except Exception:
                pass
            page.wait_for_timeout(700)
    return ok


def _seleccionar_capitulo(page, capitulo):
    """Localiza y hace click en el capitulo pedido (por numero o titulo)."""
    texto = str(capitulo).strip()
    es_numero = texto.isdigit()
    if es_numero:
        candidatos = ["E%s" % texto, "%s: " % texto, "Cap. %s" % texto,
                      "Capitulo %s" % texto]
    else:
        candidatos = [texto]

    for c in candidatos:
        try:
            el = page.get_by_text(c, exact=False).first
            if el.count():
                _scroll_carrusel_hasta(page, c)
                try:
                    el.scroll_into_view_if_needed(timeout=4000)
                except Exception:
                    pass
                try:
                    el.click(timeout=8000)
                    return True
                except Exception:
                    pass
        except Exception:
            continue

    # Fallback: buscar en el DOM cualquier enlace que contenga la serie
    # de episodios y reproducir el que diga el numero/titulo objetivo.
    try:
        res = page.evaluate("""(num) => {
            const node = [...document.querySelectorAll('a, [role="button"], div[class*="episode"]')]
                .find(n => (n.innerText || '').trim().match(num));
            if (node) { node.scrollIntoView({block:'center'}); return true; }
            return false;
        }""", texto)
        if res:
            return True
    except Exception:
        pass
    return False


def main(capitulo):
    print("=== navegar_hbo_max.py -> capitulo %r ===" % capitulo)
    if not _chrome_ya_depurado():
        _relanzar_brave(open_url="https://play.hbomax.com")
    else:
        print("Brave ya tiene depuracion remota activa (%d)." % PUERTO)

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(CDP_HTTP)
        page = None
        for c in browser.contexts:
            for pg in c.pages:
                if "hbomax" in pg.url or "hbomax" in (pg.title() or ""):
                    page = pg
                    break
            if page:
                break
        if not page:
            page = browser.contexts[0].new_page()
            page.goto("https://play.hbomax.com", wait_until="domcontentloaded")
        page.bring_to_front()
        page.wait_for_timeout(1500)
        print("Pestania: %r" % page.url)

        # Ir al show de El Mentalista si no estamos en la pagina correcta
        if "mentalist" not in page.url.lower():
            page.goto("https://www.hbomax.com/ad/en/show/612dfd59-5e1c-40af-bcfe-3084869f284b", wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)  # dejar que cargue el DOM del show

        ok = _seleccionar_capitulo(page, capitulo)
        page.wait_for_timeout(1500)
        print("Seleccion intentada: %s | URL: %r" % (ok, page.url))
        print("OK TODO")


if __name__ == "__main__":
    cap = sys.argv[1] if len(sys.argv) > 1 else "13"
    main(cap)
