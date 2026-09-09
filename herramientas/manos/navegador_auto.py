# navegador_auto.py - Mando maestro unificado de automatizacion web de JARVIS.
# manos de JARVIS (creado en sesion de instalacion/consolidacion del arsenal).
#
# CONTROL BRAVE/CHROME VIA CDP (puerto 9222) sobre el perfil DEDICADO C:\brave-cdp.
# Conserva sesiones (p.ej. HBO Max) y permite manejar interfaces web dinamicas
# sin OCR: navegar, hacer clic por texto/selector, escribir, extraer, teclear,
# pantalla completa, capturar, buscar episodios en HBO Max.
#
# Requisito: Brave con CDP ya levantado. Puedes levantarlo de dos formas:
#   a) Este script:   python navegador_auto.py --asegurar        (lo lanza si falta)
#   b) A mano:        C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe
#                     --remote-debugging-port=9222 --remote-allow-origins=* \
#                     --user-data-dir=C:\brave-cdp
# OJO: el flag --remote-allow-origins=* es OBLIGATORIO en Brave/Chrome 111+
# para que el cliente CDP (websocket) no reciba 403 Forbidden.
#
# Uso:
#   python navegador_auto.py --asegurar                      # lanza/verifica Brave CDP
#   python navegador_auto.py --estado                         # estado del navegador
#   python navegador_auto.py --abrir "https://play.hbomax.com" # navega la pestana activa
#   python navegador_auto.py --clic "Capítulo 3"              # clic en el 1er elemento visible
#   python navegador_auto.py --escribir "batman"              # escribe texto en el foco
#   python navegador_auto.py --tecla Enter                    # pulsa una tecla
#   python navegador_auto.py --leer "h1, .title, [aria-label]" # extrae textos por selector
#   python navegador_auto.py --buscar "continuar"             # localiza elementos por texto
#   python navegador_auto.py --scroll "temporada 2"           # scroll hasta un texto
#   python navegador_auto.py --episodio 13 --serie "el mentalista"  # episodio en HBO Max
#   python navegador_auto.py --foto salida.png                # screenshot de la pestana activa
#   python navegador_auto.py --list                            # lista pestanas
#
# Nota: para reproducir DRM (HBO Max/Netflix) el navegador va en ventana NORMAL (no
# headless) con GPU; el clic se hace por coordenadas del viewport vía Input CDP.
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import cdp_brave as cdp  # reutiliza la capa CDP ya consolidada

PERFIL = r"C:\brave-cdp"
BRAVE = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
INICIO = "https://play.hbomax.com"
PUERTO = 9222
HOST = "127.0.0.1"


# ---------------------------------------------------------------------------
# Estado / lanazador
# ---------------------------------------------------------------------------
def cdp_activo():
    try:
        with urllib.request.urlopen(
                "http://%s:%d/json/version" % (HOST, PUERTO), timeout=3) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:
        return None


def asegurar():
    """Lanza Brave (perfil dedicado + CDP) si no esta corriendo."""
    info = cdp_activo()
    if info:
        print("CDP ya activo en el puerto %d." % PUERTO)
        return True
    print("Brave con CDP no detectado; lanzando perfil dedicado %s..." % PERFIL)
    try:
        subprocess.Popen([BRAVE,
                          "--remote-debugging-port=%d" % PUERTO,
                          "--remote-allow-origins=*",
                          "--user-data-dir=%s" % PERFIL,
                          "--no-first-run",
                          INICIO])
    except Exception as e:
        print("ERROR al lanzar Brave: %s" % e)
        return False
    for _ in range(45):
        time.sleep(1)
        if cdp_activo():
            print("Brave CDP listo en %s:%d." % (HOST, PUERTO))
            return True
    print("AVISO: el puerto %d no respondio tras 45s." % PUERTO)
    return False


def estado():
    info = cdp_activo()
    if not info:
        print("CDP NO activo. Corre: python navegador_auto.py --asegurar")
        return
    ver = json.loads(info)
    print("Navegador CDP listo:")
    print("  Protocolo: %s | Navegador: %s" % (ver.get("protocolVersion"),
                                               ver.get("Browser", "?")))
    print("  V8: %s" % ver.get("V8", "?"))
    paginas = cdp.listar_pestanas()
    pages = [p for p in paginas if p.get("type") == "page"]
    print("  Pestanas page: %d" % len(pages))
    for p in pages[:8]:
        print("   - %s\n     %s" % ((p.get("title") or "")[:60], p.get("url") or ""))


# ---------------------------------------------------------------------------
# Acciones de alto nivel
# ---------------------------------------------------------------------------
def pestana(filtro=None):
    t = cdp.pestana_activa(filtro=filtro)
    if not t:
        raise RuntimeError("Sin pestana utilizable. Abre primero el navegador.")
    return t["webSocketDebuggerUrl"]


def escribir(ws, texto):
    js = """(ev => {
        const el = document.activeElement;
        if (!el) return 'sin-foco';
        const proto = Object.getPrototypeOf(el);
        const setter = Object.getOwnPropertyDescriptor(
            proto && proto.value ? proto.value.constructor.prototype : HTMLInputElement.prototype,
            'value');
        if (setter && setter.set) setter.set.call(el, %s);
        el.dispatchEvent(new Event('input', {bubbles:true}));
        el.dispatchEvent(new Event('change', {bubbles:true}));
        return 'ok';
    })()""" % json.dumps(texto)
    res = cdp.eval_js(ws, js)
    if res == "ok":
        cdp._run(ws, "Input.insertText", {"text": texto})
        print("Texto escrito en el elemento con foco.")
    else:
        print("AVISO: no habia foco editable (%s). Escribo igual via Input." % res)
        cdp._run(ws, "Input.insertText", {"text": texto})


def foto(ws, ruta):
    res = cdp._run(ws, "Page.captureScreenshot", {"format": "png"})
    data = res.get("data")
    if not data:
        raise RuntimeError("La pestana devolvio una captura vacia.")
    import base64
    with open(ruta, "wb") as f:
        f.write(base64.b64decode(data))
    print("Captura guardada en: %s" % ruta)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Mando maestro de automatizacion web de JARVIS")
    ap.add_argument("--port", type=int, default=PUERTO)
    ap.add_argument("--asegurar", action="store_true", help="lanzar/verificar Brave CDP")
    ap.add_argument("--estado", action="store_true", help="estado del navegador")
    ap.add_argument("--list", action="store_true", help="listar pestanas")
    ap.add_argument("--abrir", metavar="URL")
    ap.add_argument("--clic", metavar="TEXTO")
    ap.add_argument("--clic-selector", metavar="CSS")
    ap.add_argument("--escribir", metavar="TEXTO")
    ap.add_argument("--tecla", metavar="TECLA", help="Enter, Escape, F11, ...")
    ap.add_argument("--leer", metavar="SELECTORES")
    ap.add_argument("--buscar", metavar="TEXTO")
    ap.add_argument("--scroll", metavar="TEXTO")
    ap.add_argument("--episodio", type=int, help="numero de episodio en HBO Max")
    ap.add_argument("--serie", default=None, help="nombre de la serie (para buscar episodio)")
    ap.add_argument("--foto", metavar="PNG", help="captura de pantalla")
    args = ap.parse_args()

    cdp.DEBUG_PORT = args.port  # las funciones de estado usan la constante 9222

    if args.asegurar:
        asegurar()
        return
    if args.estado:
        estado()
        return

    if not cdp_activo():
        print("CDP NO activo. Corre primero: python navegador_auto.py --asegurar")
        sys.exit(2)

    if args.list:
        for t in cdp.listar_pestanas():
            if t.get("type") == "page":
                print("- [%s] %s\n   %s" % (t.get("id")[:8], t.get("title"), t.get("url")))
        return

    ws = pestana()
    print("Pestana activa: %s" % (cdp.pestana_activa().get("title")))

    if args.abrir:
        cdp.navegar(ws, args.abrir)
        time.sleep(2.5)
        print("Navegando a: %s" % args.abrir)
    elif args.clic:
        (x, y), f = cdp.clic_por_texto(ws, args.clic)
        print("Clic (%d,%d) en: %s" % (x, y, f.get("texto", args.clic)))
    elif args.clic_selector:
        js = ("(() => { const e = document.querySelector(%s); if (!e) return null; "
              "const r = e.getBoundingClientRect(); return {x: Math.round(r.x+r.width/2), "
              "y: Math.round(r.y+r.height/2)}; })()") % json.dumps(args.clic_selector)
        xy = cdp.eval_js(ws, js)
        if not xy:
            print("Selector no encontrado: %s" % args.clic_selector)
            sys.exit(1)
        cdp.clic_en_coordenadas(ws, xy["x"], xy["y"])
        print("Clic en selector %s en (%d,%d)." % (args.clic_selector, xy["x"], xy["y"]))
    elif args.escribir:
        escribir(ws, args.escribir)
    elif args.tecla:
        cdp.pulsar_tecla(ws, args.tecla)
        print("Tecla pulsada: %s" % args.tecla)
    elif args.leer:
        sel = [s.strip() for s in args.leer.split(",") if s.strip()]
        print(json.dumps(cdp.leer_dom(ws, sel), ensure_ascii=False, indent=2))
    elif args.buscar:
        print(json.dumps(cdp.buscar_por_texto(ws, args.buscar),
                         ensure_ascii=False, indent=2))
    elif args.scroll:
        print("Scroll hasta %r: %s" % (args.scroll, cdp.scroll_hasta(ws, args.scroll)))
    elif args.episodio:
        # Busca el episodio por su numero en la pestana actual (HBO Max).
        cand = ["Capítulo %d" % args.episodio, "Episode %d" % args.episodio,
                "Cap. %d" % args.episodio, "E%d" % args.episodio]
        hecho = False
        for txt in cand:
            try:
                _, f = cdp.clic_por_texto(ws, txt)
                print("Episodio localizado: %s" % f.get("texto", txt))
                hecho = True
                break
            except Exception:
                continue
        if not hecho:
            print("No se encontro el episodio %d por texto en la pestana actual." % args.episodio)
            sys.exit(1)
        time.sleep(4)
        cdp.pulsar_tecla(ws, "F11")
        print("Pantalla completa (F11).")
    elif args.foto:
        try:
            foto(ws, args.foto)
        except Exception as e:
            print("ERROR de captura: %s" % e)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
