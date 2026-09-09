"""diag_hbo.py - Diagnostico con Playwright/CDP: conecta a Brave, navega y lee el DOM.
manos de JARVIS. Requiere Brave relanzado con --remote-debugging-port=9222.
Uso: py312 diag_hbo.py [accion] [url]
accion: url (mostrar url/titulo), dom (listar enlaces/textos), buscar SERIE
"""
import sys
import time

PORT = 9222


def conectar():
    from playwright.sync_api import sync_playwright
    pw = sync_playwright().start()
    browser = pw.chromium.connect_over_cdp("http://127.0.0.1:%d" % PORT)
    return pw, browser


def pestana_hbomax(browser):
    for c in browser.contexts:
        for pg in c.pages:
            if "hbomax" in pg.url or "hbomax" in (pg.title() or "").lower():
                return pg
    # si no hay, crear una
    return browser.contexts[0].new_page()


def main():
    accion = sys.argv[1] if len(sys.argv) > 1 else "url"
    pw, browser = conectar()
    try:
        page = pestana_hbomax(browser)
        page.bring_to_front()
        print("URL actual: %r" % page.url)
        print("Titulo: %r" % page.title())

        if accion == "dom":
            # Listar enlaces y botones con su texto (primeros 60)
            datos = page.evaluate("""() => {
                const out = [];
                const els = document.querySelectorAll('a, button, [role="link"]');
                for (let i=0; i<els.length && out.length<60; i++) {
                    const t = (els[i].innerText || '').trim().replace(/\\s+/g,' ');
                    const h = els[i].getAttribute('href') || '';
                    if (t) out.push(t.slice(0,60) + '  =>  ' + h.slice(0,70));
                }
                return out;
            }""")
            for d in datos:
                print(" -", d)

        elif accion == "buscar":
            serie = sys.argv[2] if len(sys.argv) > 2 else "mentalista"
            page.goto("https://www.hbomax.com/search?q=%s" % serie,
                      wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)
            print("Tras navegar a busqueda: %r" % page.url)
            # busqueda profunda: elementos que contengan la serie en su texto
            datos = page.evaluate("""(needle) => {
                const out = [];
                const all = document.querySelectorAll('a, button, [role="link"], [role="button"], div, span');
                for (let i=0; i<all.length && out.length<40; i++) {
                    const t = (all[i].innerText || '').trim().replace(/\\s+/g,' ');
                    if (!t) continue;
                    if (t.toLowerCase().includes(needle)) {
                        const tag = all[i].tagName;
                        const cls = (all[i].getAttribute('class')||'').slice(0,60);
                        const href = all[i].getAttribute('href')||'';
                        out.push(tag + '|' + cls + '|' + t.slice(0,70) + (href?('  => '+href.slice(0,60)):''));
                    }
                }
                return out;
            }""", serie.lower())
            for d in datos:
                print(" -", d)
            if not datos:
                print("(sin coincidencias con %r)" % serie)

        elif accion == "url":
            pass  # ya imprimimos

        page.wait_for_timeout(500)
    finally:
        browser.close()
        pw.stop()


if __name__ == "__main__":
    main()
