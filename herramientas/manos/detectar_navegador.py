# detectar_navegador.py - DETECTA Y USA las funciones/capacidades de un navegador
# Chromium (Brave/Chrome/Edge) via CDP. manos de JARVIS (creado 24/08/2026,
# investigacion del jefe: "investiga mas sobre como usar y detectar las funciones
# del navegador").
#
# QUE HACE:
#   1. Se conecta al CDP de un navegador YA abierto (--remote-debugging-port=9222)
#      o a la instancia headless de pruebas que JARVIS pueda lanzar.
#   2. Enumera TODOS los dominios CDP soportados (Schema.getDomains) y marca
#      cuales de los utiles para automatizacion existen (Page, DOM, Runtime,
#      Input, Emulation, Network, Performance, Accessibility, Media, Fetch,
#      Browser, Overlay...). Asi sabemos "que funciones del navegador" hay.
#   3. Ejecuta un CAPABILITY REPORT en JavaScript dentro de la pagina para
#      detectar las APIs del navegador real (WebGL, WebRTC, DRM/EME/Widevine,
#      Media Session, Fullscreen, Picture-in-Picture, autoplay, MediaDevices,
#      etc.) y devuelve true/false por funcion.
#   4. Detecta si es headless o navegador normal (user-agent, navigator.webdriver).
#
# Uso:
#   python detectar_navegador.py                 # conexion a 9222 + reporte completo
#   python detectar_navegador.py --port 9222
#   python detectar_navegador.py --dominios      # solo enumerar dominios CDP
#   python detectar_navegador.py --api           # solo el reporte de APIs JS
#   python detectar_navegador.py --json          # salida JSON para parsear
#
# Requisito: 'websocket-client' (pip install websocket-client), ya instalado.
import argparse
import json
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DEBUG_HOST = "127.0.0.1"
DEBUG_PORT = 9222

# Dominios CDP que nos importan para automatizacion/multimedia. El script marca
# cuales existen en el navegador actual.
DOMINIOS_UTILES = [
    "Page", "DOM", "Runtime", "Input", "Emulation", "Network",
    "Performance", "Accessibility", "Media", "Fetch", "Browser",
    "Overlay", "DOMSnapshot", "CSS", "Log", "SystemInfo", "Target",
    "Storage", "WebAudio", "Tracing", "Profiler",
]


def _http_json(path):
    # Opener SIN proxy: el CDP es localhost y un proxy (de variables del SO)
    # puede desviar la peticion y devolver 404. Con ProxyHandler({}) va directo.
    url = "http://%s:%d%s" % (DEBUG_HOST, DEBUG_PORT, path)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=6) as r:
        return json.loads(r.read().decode("utf-8"))


# ----------------------------------------------------------------------------
# Capa WebSocket CDP
# ----------------------------------------------------------------------------
class CDP:
    def __init__(self, ws_url, timeout=20):
        import websocket
        self._ws = websocket.create_connection(ws_url, timeout=timeout)
        self._id = 0

    def call(self, method, params=None):
        self._id += 1
        self._ws.send(json.dumps({"id": self._id, "method": method,
                                  "params": params or {}}))
        while True:
            data = json.loads(self._ws.recv())
            if data.get("id") == self._id:
                if "error" in data:
                    raise RuntimeError("%s -> %s" % (method, data["error"]))
                return data.get("result", {})
            # ignorar eventos

    def close(self):
        try:
            self._ws.close()
        except Exception:
            pass


# Capability-report JavaScript: detecta en la pagina las funciones del navegador.
# Usa protecciones (typeof / try-catch) para no lanzar si una API no existe.
CAPABILITY_JS = r"""(() => {
  const r = (nom, fn) => { try { return !!fn(); } catch (e) { return false; } };
  const out = {};

  // Perfil / deteccion de navegador
  out.userAgent = navigator.userAgent;
  out.webdriver = !!navigator.webdriver;          // true si lo controla una automatizacion
  out.headless = /HeadlessChrome/.test(navigator.userAgent) || !!navigator.userAgent.includes('Headless');
  out.javaScript = r('js', () => typeof window !== 'undefined');
  out.cookies = r('cookies', () => navigator.cookieEnabled);
  out.onLine = navigator.onLine;
  out.language = navigator.language;

  // Graficos
  out.webgl = r('webgl', () => {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl') || c.getContext('experimental-webgl'));
  });
  out.webgl2 = r('webgl2', () => {
    const c = document.createElement('canvas');
    return !!c.getContext('webgl2');
  });
  out.canvas = r('canvas', () => !!document.createElement('canvas').getContext('2d'));

  // Multimedia / reproduccion protegida (DRM/EME, clave para HBO Max/Netflix)
  out.eme = r('eme', () => typeof navigator.requestMediaKeySystemAccess === 'function');
  out.widevine = r('widevine', () => navigator.requestMediaKeySystemAccess &&
      navigator.requestMediaKeySystemAccess('com.widevine.alpha', []));
  out.mediaSession = r('mediaSession', () => typeof navigator.mediaSession !== 'undefined');
  out.getAutoplayPolicy = r('getAutoplayPolicy', () => navigator.getAutoplayPolicy && navigator.getAutoplayPolicy('mediaelement'));
  out.pictureInPicture = r('pictureInPicture', () => typeof document.pictureInPictureEnabled === 'boolean');
  out.fullscreen = r('fullscreen', () => typeof document.fullscreenEnabled === 'boolean' || typeof document.webkitFullscreenEnabled === 'boolean');

  // Captura de medios / dispositivos
  out.getUserMedia = r('getUserMedia', () => navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
  out.enumerateDevices = r('enumerateDevices', () => navigator.mediaDevices && navigator.mediaDevices.enumerateDevices);

  // Red / WebRTC
  out.webrtc = r('webrtc', () => typeof RTCPeerConnection === 'function' || typeof webkitRTCPeerConnection === 'function');
  out.webSocket = r('webSocket', () => typeof WebSocket === 'function');
  out.fetch = r('fetch', () => typeof fetch === 'function');
  out.serviceWorker = r('serviceWorker', () => typeof navigator.serviceWorker !== 'undefined');

  // Storage
  out.localStorage = r('localStorage', () => { window.localStorage.setItem('__t','1'); return true; });
  out.sessionStorage = r('sessionStorage', () => { window.sessionStorage.setItem('__t','1'); return true; });
  out.indexedDB = r('indexedDB', () => typeof indexedDB !== 'undefined');

  // Multimedia abierta
  out.webAudio = r('webAudio', () => typeof AudioContext === 'function' || typeof webkitAudioContext === 'function');
  out.video = r('video', () => !!document.createElement('video').canPlayType('video/mp4'));
  out.videoHls = r('videoHls', () => !!document.createElement('video').canPlayType('application/vnd.apple.mpegurl'));

  // Generales utiles
  out.fullscreenState = (() => {
    try { return document.fullscreenEnabled === true; } catch (e) { return false; }
  })();
  out.touch = r('touch', () => 'ontouchstart' in window || navigator.maxTouchPoints > 0);
  out.geolocation = r('geolocation', () => !!navigator.geolocation);
  out.notifications = r('notifications', () => !!navigator.serviceWorker && Notification);
  out.composition = r('composition', () => typeof WebGL2RenderingContext !== 'undefined');

  return out;
})()"""


# ----------------------------------------------------------------------------
# Acciones
# ----------------------------------------------------------------------------
def dominios_cdp(ws_url):
    """Schema.getDomains -> lista de nombres de dominios que SOPORTA el browser."""
    res = _run(ws_url, "Schema.getDomains")
    return [d.get("name") for d in res.get("domains", [])]


def version_browser():
    """/json/version -> nombre, version, protocolo, UA."""
    v = _http_json("/json/version")
    return {
        "browser": v.get("Browser"),
        "protocolo": v.get("Protocol-Version"),
        "user_agent": v.get("User-Agent"),
        "v8": v.get("V8-Version"),
    }


def _run(ws_url, method, params=None):
    c = CDP(ws_url)
    try:
        return c.call(method, params)
    finally:
        c.close()


def _ws_pestana():
    """Elige una pestana 'page' con webSocketDebuggerUrl para ejecutar JS."""
    for t in _http_json("/json"):
        if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
            return t["webSocketDebuggerUrl"]
    return None


def navegar_ws(ws_url, url):
    _run(ws_url, "Page.navigate", {"url": url})
    time.sleep(1.2)


def eval_js(ws_url, expression):
    res = _run(ws_url, "Runtime.evaluate",
               {"expression": expression, "returnByValue": True})
    return res.get("result", {}).get("value")


def capability_report(ws_url):
    """Navega a una pagina segura y ejecuta el reporte de APIs JS."""
    # Primero cargar un documento real para que haya DOM/media elements.
    data_url = ("data:text/html,<title>cap</title><body><h1>capability</h1></body>")
    navegar_ws(ws_url, data_url)
    return eval_js(ws_url, CAPABILITY_JS)


def main():
    global DEBUG_PORT
    p = argparse.ArgumentParser(description="Detectar funciones/capacidades de un "
                                            "navegador Chromium via CDP")
    p.add_argument("--port", type=int, default=DEBUG_PORT)
    p.add_argument("--dominios", action="store_true",
                   help="solo enumerar dominios CDP (Schema.getDomains)")
    p.add_argument("--api", action="store_true",
                   help="solo reporte de APIs JS (capabilities de la pagina)")
    p.add_argument("--json", action="store_true", help="salida JSON")
    args = p.parse_args()
    DEBUG_PORT = args.port

    try:
        ver = version_browser()
    except Exception as e:
        print("ERROR: no hay CDP en el puerto %d. ¿Navegador con "
              "--remote-debugging-port=%d? (%s)" % (DEBUG_PORT, DEBUG_PORT, e))
        sys.exit(2)

    ws = _ws_pestana()
    haz_dominios = args.dominios or not args.api
    haz_api = args.api or not args.dominios

    reporte = {"version": ver}
    if haz_dominios and ws:
        try:
            doms = dominios_cdp(ws)
            reporte["dominios_total"] = len(doms)
            reporte["dominios_utiles"] = {
                d: (d in doms) for d in DOMINIOS_UTILES
            }
        except Exception as e:
            reporte["error_dominios"] = str(e)
    if haz_api and ws:
        try:
            reporte["apis"] = capability_report(ws)
        except Exception as e:
            reporte["error_apis"] = str(e)

    print(json.dumps(reporte, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
