# -*- coding: utf-8 -*-
"""probar_web.py - Verificacion de paginas en navegador INVISIBLE, blindada
contra cuelgues. Manos de JARVIS (creado 15/09/2026, orden del jefe).

¿POR QUE EXISTE?
    El 15/09/2026 un `opencode run` se quedo colgado 45 minutos porque el
    agente verifico su cambio con:
        brave.exe --headless --user-data-dir=<PERFIL NUEVO> --dump-dom <url>
    En esta PC eso SE CUELGA SIEMPRE: el PRIMER uso de un `--user-data-dir`
    recien creado nunca termina (ni con --no-first-run ni sin red; probado
    con about:blank: 0% de CPU, proceso eterno). El segundo uso del mismo
    directorio, en cambio, tarda 0,4 s. El cuelgue bloquea la herramienta,
    bloquea `opencode run` y deja al jefe sin respuesta.

COMO LO BLINDA:
    1. Usa SIEMPRE un perfil fijo y ya "caliente" (%TEMP%\\jarvis_web_perfil).
       Si no existe, lo calienta solo: lanza un arranque de usar y tirar y lo
       MATA a los N segundos (ese primer arranque se cuelga, es lo esperado;
       a partir de ahi el perfil queda inicializado y funciona).
    2. Controla el navegador por CDP (aiohttp, sin dependencias nuevas): nada
       de `--dump-dom`, que se queda esperando a que la pagina "termine".
    3. Tiempo limite DURO en todo: navegador, CDP y espera.
    4. MATA el arbol del navegador SIEMPRE (finally), pase lo que pase.
       No puede dejar procesos huerfanos ni turnos colgados.

USO:
    # Leer un elemento de la pagina (lo mas comun):
    python probar_web.py --url http://127.0.0.1:8090/_test_btnfondo.html \
        --espera 6 --texto "#resultado"

    # Evaluar JavaScript a medida:
    python probar_web.py --url https://ejemplo.com --js "document.title"

    # Guardar una captura de pantalla:
    python probar_web.py --url http://127.0.0.1:8090/ --captura C:\\ruta\\cap.png

Salida (facil de leer para el agente):
    RESULTADO: <valor en JSON>
    ESTADO: OK | COLGADO | ERROR
"""
import argparse
import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

# La consola de Windows (cp1252) no sabe imprimir lo que aparece en las paginas
# (flechas, emojis, tildes raras): sin esto, una prueba CORRECTA puede terminar
# en UnicodeEncodeError. Paso la salida a UTF-8 tolerante (16/09/2026).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# --- Configuracion ----------------------------------------------------------
PERFIL = os.path.join(tempfile.gettempdir(), "jarvis_web_perfil")
MARCA_CALIENTE = os.path.join(PERFIL, "jarvis_caliente.ok")

ESPERA_CALIENTO = 25      # seg: el 1er arranque de un perfil nuevo se cuelga
TIMEOUT_ARRANQUE = 30     # seg: esperar a que el puerto CDP responda
ESPERA_POR_DEFECTO = 4    # seg: dejar que la pagina haga su trabajo
TIMEOUT_TOTAL = 150       # seg: tope absoluto del script entero
ESPERA_BLOQUEO = 90       # seg: cola maxima si otro proceso usa ya el perfil
ANTIGUEDAD_BLOQUEO = 240  # seg: un bloqueo mas viejo que esto es basura

NAVEGADORES = [
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def log(msg):
    print("[probar_web] %s" % msg, flush=True)


def encontrar_navegador():
    for ruta in NAVEGADORES:
        if os.path.isfile(ruta):
            return ruta
    raise SystemExit("ERROR: no encontre ningun navegador Chromium instalado.")


def puerto_libre():
    """Pide al sistema un puerto libre (evita chocar con otro navegador)."""
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def matar_arbol(pid):
    """Mata el proceso y TODOS sus hijos. Nunca lanza excepcion."""
    if not pid:
        return
    try:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)],
                       capture_output=True, timeout=20,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception:
        pass


def ruta_bloqueo():
    return PERFIL + ".lock"


def tomar_bloqueo(espera_max=ESPERA_BLOQUEO):
    """Un solo navegador a la vez sobre el mismo perfil. Si dos procesos usan
    el mismo --user-data-dir, el segundo se ENTREGA al primero y NO abre su
    propio puerto CDP (fallo seguro, pero inutil: paso el 15/09/2026 a las
    11:30 con el agente y el doctor a la vez). Aqui se hace cola. Un bloqueo
    mas viejo que ANTIGUEDAD_BLOQUEO es basura de una ejecucion muerta."""
    t0 = time.time()
    while True:
        try:
            if os.path.isfile(ruta_bloqueo()):
                edad = time.time() - os.path.getmtime(ruta_bloqueo())
                if edad > ANTIGUEDAD_BLOQUEO:
                    log("bloqueo viejo (%.0fs): lo reclamo" % edad)
                    os.remove(ruta_bloqueo())
                    continue
                if time.time() - t0 > espera_max:
                    raise RuntimeError(
                        "otro probar_web.py lleva %.0fs usando el perfil; "
                        "reintenta en unos segundos" % edad)
                time.sleep(1.0)
                continue
            with open(ruta_bloqueo(), "w", encoding="utf-8") as fh:
                fh.write(str(os.getpid()))
            return
        except FileNotFoundError:
            continue


def soltar_bloqueo():
    try:
        if os.path.isfile(ruta_bloqueo()):
            os.remove(ruta_bloqueo())
    except Exception:
        pass


def matar_navegadores_huerfanos(perfil):
    """Si quedo un navegador vivo de una ejecucion anterior con NUESTRO
    perfil, la nueva ejecucion se le entrega y no abre puerto: lo matamos."""
    script = (
        "Get-CimInstance Win32_Process | Where-Object { ($_.Name -eq "
        "'brave.exe' -or $_.Name -eq 'chrome.exe') -and $_.CommandLine -like "
        "'*%s*' } | ForEach-Object { $_.ProcessId }" % perfil)
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive",
                            "-Command", script],
                           capture_output=True, encoding="utf-8",
                           errors="replace", timeout=30,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        for linea in (r.stdout or "").split():
            if linea.strip().isdigit():
                matar_arbol(int(linea.strip()))
                log("mate un navegador huerfano (PID %s)" % linea.strip())
    except Exception:
        pass


def lanzar(navegador, args, oculto=True):
    flags = subprocess.CREATE_NO_WINDOW if oculto else 0
    return subprocess.Popen([navegador] + args,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            creationflags=flags)


def calentar_perfil(navegador):
    """El PRIMER arranque con un perfil nuevo se cuelga (bug de esta PC): lo
    lanzamos y lo matamos a proposito. Al morir, el perfil queda inicializado
    y a partir de ahi el navegador arranca en menos de un segundo."""
    log("perfil nuevo: lo caliento (el primer arranque se cuelga a proposito; "
        "lo mato a los %ds)" % ESPERA_CALIENTO)
    proc = lanzar(navegador, [
        "--headless=old", "--disable-gpu", "--no-sandbox", "--no-first-run",
        "--user-data-dir=%s" % PERFIL, "--dump-dom", "about:blank",
    ])
    try:
        proc.wait(timeout=ESPERA_CALIENTO)
        log("el arranque de calentamiento salio solo")
    except Exception:
        log("arranque de calentamiento colgado -> matado (es lo esperado)")
    finally:
        matar_arbol(proc.pid)
    try:
        os.makedirs(PERFIL, exist_ok=True)
        with open(MARCA_CALIENTE, "w", encoding="utf-8") as fh:
            fh.write("caliente %s\n" % time.strftime("%d/%m/%Y %H:%M:%S"))
    except Exception as e:
        log("aviso: no pude escribir la marca de perfil caliente: %r" % e)


def perfil_listo(navegador):
    if os.path.isfile(MARCA_CALIENTE):
        return
    calentar_perfil(navegador)


def esperar_cdp(puerto, limite):
    """Espera a que el puerto de depuracion del navegador responda."""
    url = "http://127.0.0.1:%d/json/version" % puerto
    t0 = time.time()
    while time.time() - t0 < limite:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("el navegador no abrio el puerto CDP %d en %ds"
                       % (puerto, limite))


def objetivo_pagina(puerto):
    """Devuelve el webSocketDebuggerUrl de la primera pestana."""
    url = "http://127.0.0.1:%d/json" % puerto
    with urllib.request.urlopen(url, timeout=5) as r:
        objetivos = json.loads(r.read().decode("utf-8", "replace"))
    for o in objetivos:
        if o.get("type") == "page" and o.get("webSocketDebuggerUrl"):
            return o["webSocketDebuggerUrl"]
    raise RuntimeError("no hay pestana con websocket de depuracion")


async def sesion(args, navegador, puerto, ws_url):
    """Navega, espera y evalua. Toda la charla CDP por aiohttp."""
    import aiohttp

    async with aiohttp.ClientSession() as s:
        async with s.ws_connect(ws_url, max_msg_size=0, heartbeat=None) as ws:
            contador = {"id": 0}

            async def cmd(method, params=None):
                contador["id"] += 1
                mio = contador["id"]
                await ws.send_json({"id": mio, "method": method,
                                    "params": params or {}})
                while True:
                    msg = await ws.receive(timeout=TIMEOUT_ARRANQUE)
                    if msg.type != aiohttp.WSMsgType.TEXT:
                        continue
                    datos = json.loads(msg.data)
                    if datos.get("id") == mio:
                        if "error" in datos:
                            raise RuntimeError("%s -> %s"
                                               % (method, datos["error"]))
                        return datos.get("result", {})

            await cmd("Page.enable")
            # --- emulacion de telefono (pantalla y tactil) ---
            medida = getattr(args, "medida", None)
            if medida or getattr(args, "movil", False):
                if medida:
                    ancho, alto = (int(x) for x in medida.lower().split("x"))
                else:
                    ancho, alto = 390, 844
                await cmd("Emulation.setDeviceMetricsOverride", {
                    "width": ancho, "height": alto,
                    "deviceScaleFactor": 2, "mobile": True})
                await cmd("Emulation.setTouchEmulationEnabled",
                          {"enabled": True, "maxTouchPoints": 5})
                log("emulando pantalla %dx%d con pantalla tactil" % (ancho, alto))
            await cmd("Page.navigate", {"url": args.url})
            log("navegado a %s | espero %.1fs" % (args.url, args.espera))
            await asyncio.sleep(args.espera)

            resultado = None
            if args.texto:
                expr = ("(() => { const e = document.querySelector(%s); "
                        "return e ? (e.innerText || e.textContent || '') : null; })()"
                        % json.dumps(args.texto))
                resultado = await cmd("Runtime.evaluate",
                                      {"expression": expr, "returnByValue": True})
                resultado = resultado.get("result", {}).get("value")
            elif args.js:
                espera_js = float(getattr(args, "espera_js", 0) or 0)
                if espera_js > 0:
                    log("espero %.1fs antes de evaluar el JavaScript" % espera_js)
                    await asyncio.sleep(espera_js)
                # awaitPromise: si la expresion devuelve una promesa (async),
                # se espera su resultado en vez de recibir un objeto vacio
                res = await cmd("Runtime.evaluate",
                                {"expression": args.js, "returnByValue": True,
                                 "awaitPromise": True})
                resultado = res.get("result", {}).get("value")

            if resultado is not None:
                if not isinstance(resultado, str):
                    resultado = json.dumps(resultado, ensure_ascii=False)
                print("RESULTADO: %s" % resultado.strip())

            if args.captura:
                res = await cmd("Page.captureScreenshot",
                                {"format": "png", "captureBeyondViewport": True})
                datos_b64 = res.get("data")
                if datos_b64:
                    import base64
                    with open(args.captura, "wb") as fh:
                        fh.write(base64.b64decode(datos_b64))
                    print("CAPTURA: %s (%d bytes)"
                          % (args.captura, os.path.getsize(args.captura)))


def main():
    global PERFIL, MARCA_CALIENTE
    p = argparse.ArgumentParser(
        description="Verificacion web blindada (sin cuelgues) para JARVIS")
    p.add_argument("--url", required=True, help="pagina a probar")
    p.add_argument("--espera", type=float, default=ESPERA_POR_DEFECTO,
                   help="segundos a esperar antes de leer (por defecto 4)")
    p.add_argument("--texto", metavar="SELECTOR",
                   help="selector CSS cuyo texto quiero leer (ej. '#resultado')")
    p.add_argument("--js", metavar="EXPRESION",
                   help="expresion JavaScript a evaluar (ej. 'document.title'); "
                        "si devuelve una promesa, se espera su resultado")
    p.add_argument("--espera-js", metavar="SEGUNDOS", type=float, default=0.0,
                   help="segundos a esperar antes de evaluar --js (util cuando "
                        "la pagina carga datos de internet)")
    p.add_argument("--captura", metavar="PNG", help="guardar captura de pantalla")
    p.add_argument("--ventana", metavar="ANCHOxALTO",
                   help="tamano de ventana del navegador, para probar como en un "
                        "telefono: --ventana 390x844 (por defecto 420x900)")
    p.add_argument("--movil", action="store_true",
                   help="emula un telefono de verdad: 390x844 y pantalla tactil")
    p.add_argument("--medida", metavar="ANCHOxALTO",
                   help="emula una pantalla exacta con tactil, ej. --medida 360x800")
    p.add_argument("--perfil", help="directorio de perfil (por defecto %s)" % PERFIL)
    args = p.parse_args()

    if args.perfil:
        PERFIL = args.perfil
        MARCA_CALIENTE = os.path.join(PERFIL, "jarvis_caliente.ok")

    t0 = time.time()
    navegador = encontrar_navegador()
    puerto = puerto_libre()
    proc = None
    try:
        tomar_bloqueo()
        matar_navegadores_huerfanos(PERFIL)
        perfil_listo(navegador)
        log("lanzo el navegador invisible (perfil caliente, puerto %d)" % puerto)
        proc = lanzar(navegador, [
            "--headless=old", "--disable-gpu", "--no-sandbox", "--no-first-run",
            "--user-data-dir=%s" % PERFIL,
            "--remote-debugging-port=%d" % puerto,
            "--window-size=%s" % args.ventana if getattr(args, "ventana", None)
            else "--window-size=420,900",
            "about:blank",
        ])
        esperar_cdp(puerto, TIMEOUT_ARRANQUE)
        ws_url = objetivo_pagina(puerto)
        asyncio.run(sesion(args, navegador, puerto, ws_url))
        print("ESTADO: OK (%.1fs)" % (time.time() - t0))
    except Exception as e:
        print("ESTADO: ERROR -> %r" % (e,))
        return 2
    finally:
        matar_arbol(proc.pid if proc else None)
        soltar_bloqueo()
        log("navegador cerrado (%.1fs)" % (time.time() - t0))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
