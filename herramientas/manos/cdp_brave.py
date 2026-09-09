# cdp_brave.py - Control de Brave/Chrome (Chromium) YA ABIERTO via CDP.
# manos de JARVIS (creado 23/08/2026, investigacion del jefe).
#
# OBJETIVO: hacer clic exacto en elementos del DOM (ej. "capitulo 13" en HBO
# Max), leer DOM, hacer scroll, navegar a una URL exacta... SIN OCR y SIN
# reabrir sesion (HBO Max mantiene la sesion porque controlamos la misma
# instancia ya abierta).
#
# Requisito: lanzar Brave/Chrome una vez con el puerto de depuracion remota:
#   "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
#       --remote-debugging-port=9222 --user-data-dir="C:\brave-cdp"
#   (o relanzar la misma instancia; ver DOCUMENTO de investigacion).
#
# Uso:
#   python cdp_brave.py --list                       # lista pestanas
#   python cdp_brave.py --navegar "https://..."      # navega la pestana activa
#   python cdp_brave.py --leer "h2, .title"          # lee texto de selectores
#   python cdp_brave.py --buscar "capitulo 13"       # busca elementos por texto
#   python cdp_brave.py --clic-texto "capitulo 13"   # hace clic en el 1er match
#   python cdp_brave.py --clic-selector ".play-btn"  # hace clic por selector CSS
#   python cdp_brave.py --scroll "elemento/texto"    # hace scroll hasta un elemento
#
# Modulos usados: solo urllib (stdlib) + websocket-client (pip install websocket-client)
import argparse
import json
import sys
import time
import urllib.request

DEBUG_PORT = 9222
DEBUG_HOST = "127.0.0.1"

# ----------------------------------------------------------------------------
# Capa HTTP: descubrir pestanas / obtener websocket de debug
# ----------------------------------------------------------------------------
def _http_json(path):
    url = "http://%s:%d%s" % (DEBUG_HOST, DEBUG_PORT, path)
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.loads(r.read().decode("utf-8"))


def listar_pestanas():
    """Devuelve /json -> lista de objetivos (pestanas) del navegador."""
    return _http_json("/json")


def buscar_pestana(titulo=None, url=None):
    """Devuelve el target de tipo 'page' que matchea por titulo/subcadena o URL."""
    for t in listar_pestanas():
        if t.get("type") != "page":
            continue
        if titulo and titulo.lower() in (t.get("title") or "").lower():
            return t
        if url and url.lower() in (t.get("url") or "").lower():
            return t
    return None


def pestana_activa(filtro=None):
    """Elige la mejor pestana 'page' con webSocketDebuggerUrl.

    Prefiere URLs http/https (ignora 'data:' y 'chrome://' que dan 403).
    Si 'filtro' (subcadena) se da y hay coincidencia, la prioriza.
    """
    candidatos = []
    for t in listar_pestanas():
        if t.get("type") != "page" or not t.get("webSocketDebuggerUrl"):
            continue
        url = t.get("url") or ""
        if url.startswith("data:") or url.startswith("chrome://") \
           or url.startswith("brave://"):
            continue
        candidatos.append(t)
    if filtro:
        for c in candidatos:
            if filtro.lower() in (c.get("url") or "").lower() \
               or filtro.lower() in (c.get("title") or "").lower():
                return c
    return candidatos[0] if candidatos else None


# ----------------------------------------------------------------------------
# Capa WebSocket + CDP
# ----------------------------------------------------------------------------
class CDP:
    """Cliente CDP minimo. Requiere 'websocket-client' (pip install websocket-client)."""

    def __init__(self, ws_url, timeout=15):
        import websocket  # import tardio para que --list funcione sin el paquete
        self._ws = websocket.create_connection(ws_url, timeout=timeout)
        self._id = 0

    def call(self, method, params=None):
        """Envia un comando CDP y espera su respuesta (bloqueante)."""
        self._id += 1
        msg = {"id": self._id, "method": method, "params": params or {}}
        self._ws.send(json.dumps(msg))
        while True:
            raw = self._ws.recv()
            data = json.loads(raw)
            if data.get("id") == self._id:
                if "error" in data:
                    raise RuntimeError("%s -> %s" % (method, data["error"]))
                return data.get("result", {})
            # eventos (method) se ignoran aqui para mantenerlo simple

    def close(self):
        try:
            self._ws.close()
        except Exception:
            pass


def _run(ws_url, method, params=None):
    c = CDP(ws_url)
    try:
        return c.call(method, params)
    finally:
        c.close()


# ----------------------------------------------------------------------------
# Acciones de alto nivel (trabajan con Runtime.evaluate, sin DOM.getDocument)
# ----------------------------------------------------------------------------
def eval_js(ws_url, expression):
    """Runtime.evaluate con returnByValue=True. Devuelve value (o None)."""
    res = _run(ws_url, "Runtime.evaluate",
               {"expression": expression, "returnByValue": True})
    return res.get("result", {}).get("value")


def navegar(ws_url, url):
    return _run(ws_url, "Page.navigate", {"url": url})


def leer_dom(ws_url, selectores):
    """Aplica document.querySelectorAll por cada selector y devuelve sus textos."""
    js = """(() => {
        const sels = %s;
        const salida = {};
        for (const sel of sels) {
            const nodes = document.querySelectorAll(sel);
            salida[sel] = Array.from(nodes).map(n => (n.innerText || n.textContent || '').trim());
        }
        return salida;
    })()""" % json.dumps(selectores)
    return eval_js(ws_url, js)


def buscar_por_texto(ws_url, texto, etiquetas=None):
    """Devuelve info de los primeros elementos cuyo texto visible contiene 'texto'."""
    tags = etiquetas or ["a", "button", "div", "span", "h1", "h2", "h3"]
    js = """(() => {
        const texto = %s;
        const tags = %s;
        const encontrados = [];
        for (const tag of tags) {
            for (const el of document.querySelectorAll(tag)) {
                const t = (el.innerText || el.textContent || '').trim();
                if (t && t.toLowerCase().includes(texto.toLowerCase())) {
                    const r = el.getBoundingClientRect();
                    encontrados.push({
                        tag: el.tagName.toLowerCase(),
                        texto: t.slice(0, 120),
                        x: Math.round(r.x + r.width / 2),
                        y: Math.round(r.y + r.height / 2),
                        aria: el.getAttribute('aria-label') || '',
                        data: Array.from(el.attributes)
                                     .filter(a => a.name.startsWith('data-'))
                                     .map(a => a.name + '=' + a.value).join(','),
                        vis: r.width > 0 && r.height > 0
                    });
                    if (encontrados.length >= 30) return encontrados;
                }
            }
        }
        return encontrados;
    })()""" % (json.dumps(texto), json.dumps(tags))
    return eval_js(ws_url, js)


def clic_en_coordenadas(ws_url, x, y):
    """Input.dispatchMouseEvent para un clic preciso en px de viewport."""
    _run(ws_url, "Input.dispatchMouseEvent",
         {"type": "mousePressed", "x": x, "y": y, "button": "left",
          "clickCount": 1})
    time.sleep(0.05)
    _run(ws_url, "Input.dispatchMouseEvent",
         {"type": "mouseReleased", "x": x, "y": y, "button": "left",
          "clickCount": 1})
    return (x, y)


def clic_por_texto(ws_url, texto):
    """Busca por texto y hace clic en el centro del 1er elemento visible."""
    found = buscar_por_texto(ws_url, texto)
    for f in found or []:
        if f.get("vis"):
            return clic_en_coordenadas(ws_url, f["x"], f["y"]), f
    raise RuntimeError("No se encontro elemento visible con texto: %s" % texto)


def scroll_hasta(ws_url, texto):
    """Hace scroll hasta que el elemento con 'texto' sea visible (scrollIntoView)."""
    js = """(() => {
        const texto = %s;
        const cand = [].slice.call(document.querySelectorAll('a,button,div,span,h1,h2,h3'))
            .filter(e => (e.innerText||'').trim().toLowerCase().includes(texto.toLowerCase()));
        if (!cand.length) return false;
        cand[0].scrollIntoView({behavior:'smooth', block:'center'});
        return true;
    })()""" % json.dumps(texto)
    return eval_js(ws_url, js)


def pulsar_tecla(ws_url, key):
    """Input.dispatchKeyEvent para una tecla tipo 'Enter' o 'Escape'."""
    _run(ws_url, "Input.dispatchKeyEvent",
         {"type": "keyDown", "key": key, "code": key})
    _run(ws_url, "Input.dispatchKeyEvent",
         {"type": "keyUp", "key": key, "code": key})


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def main():
    global DEBUG_PORT
    p = argparse.ArgumentParser(description="Control CDP de Brave/Chrome")
    p.add_argument("--port", type=int, default=DEBUG_PORT)
    p.add_argument("--list", action="store_true", help="listar pestanas")
    p.add_argument("--navegar", metavar="URL")
    p.add_argument("--leer", metavar="SELECTORES", help="csv de selectores")
    p.add_argument("--buscar", metavar="TEXTO", help="buscar elementos por texto")
    p.add_argument("--clic-texto", metavar="TEXTO", help="clic en elemento por texto")
    p.add_argument("--clic-selector", metavar="CSS")
    p.add_argument("--scroll", metavar="TEXTO")
    args = p.parse_args()

    DEBUG_PORT = args.port

    if args.list:
        for t in listar_pestanas():
            if t.get("type") == "page":
                print("- [%s] %s\n   %s" % (t.get("id")[:8], t.get("title"), t.get("url")))
        return

    target = pestana_activa()
    if not target:
        print("ERROR: no hay pestana con webSocketDebuggerUrl. "
              "¿Brave corriendo con --remote-debugging-port=%d?" % DEBUG_PORT)
        sys.exit(2)
    ws = target["webSocketDebuggerUrl"]
    print("Pestana: %s" % target.get("title"))

    if args.navegar:
        navegar(ws, args.navegar)
        time.sleep(1)
        print("Navegando a: %s" % args.navegar)
    elif args.leer:
        sel = [s.strip() for s in args.leer.split(",") if s.strip()]
        print(json.dumps(leer_dom(ws, sel), ensure_ascii=False, indent=2))
    elif args.buscar:
        print(json.dumps(buscar_por_texto(ws, args.buscar),
                         ensure_ascii=False, indent=2))
    elif args.clic_texto:
        (x, y), f = clic_por_texto(ws, args.clic_texto)
        print("Clic en (%d,%d): %s" % (x, y, f.get("texto")))
    elif args.clic_selector:
        js = """(() => { const e = document.querySelector(%s);
            if (!e) return null; const r = e.getBoundingClientRect();
            return {x: Math.round(r.x+r.width/2), y: Math.round(r.y+r.height/2)}; })()""" \
            % json.dumps(args.clic_selector)
        xy = eval_js(ws, js)
        if not xy:
            print("Selector no encontrado: %s" % args.clic_selector)
            sys.exit(1)
        clic_en_coordenadas(ws, xy["x"], xy["y"])
        print("Clic en selector %s -> (%d,%d)" % (args.clic_selector, xy["x"], xy["y"]))
    elif args.scroll:
        print("Scroll hasta: %s -> %s" % (args.scroll, scroll_hasta(ws, args.scroll)))
    else:
        p.print_help()


if __name__ == "__main__":
    main()
