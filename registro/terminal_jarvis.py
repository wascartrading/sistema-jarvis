# -*- coding: utf-8 -*-
"""TERMINAL DE JARVIS - visor en vivo de todo mi trabajo (caja negra).

Uso:
    python registro\\terminal_jarvis.py            (visor en vivo)
    python registro\\terminal_jarvis.py --desde-error   (arranca mostrando fallos)

Muestra, en tiempo real, TODO lo que hace JARVIS: mensajes del jefe, turnos,
herramientas, comentarios, respuestas, avisos y ERRORES; con un panel de
estado arriba (bot, OmniRoute, Telegram, conteos del dia).

Teclas:
    1 = todo          2 = fallos y avisos     3 = Telegram (conversacion)
    4 = herramientas   5 = salud ahora         c = limpiar
    h = ayuda          q = salir

Sin dependencias externas. Colores ANSI. Registro: proyectos\\registro\\AAAA-MM-DD.jsonl
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    import registro_jarvis as RJ
except Exception:  # pragma: no cover
    RJ = None

# ----------------------------------------------------------------------
# Colores / consola
# ----------------------------------------------------------------------
def _habilitar_ansi():
    if os.name != "nt":
        return True
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-11)
        modo = ctypes.c_uint32()
        if k.GetConsoleMode(h, ctypes.byref(modo)):
            k.SetConsoleMode(h, modo.value | 0x0004)  # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        return True
    except Exception:
        return False


ANSI_OK = _habilitar_ansi()


def c(texto, color):
    if not ANSI_OK:
        return texto
    return f"{color}{texto}\033[0m"


NEGRITA = "\033[1m"
GRIS = "\033[90m"
ROJO = "\033[91m"
VERDE = "\033[92m"
AMARILLO = "\033[93m"
AZUL = "\033[94m"
MAGENTA = "\033[95m"
CIAN = "\033[96m"
BLANCO = "\033[97m"
INVERSO = "\033[7m"
LIMPIAR = "\033[2J\033[H"


def limpiar_pantalla():
    if ANSI_OK:
        sys.stdout.write(LIMPIAR)
    else:
        os.system("cls" if os.name == "nt" else "clear")


# ----------------------------------------------------------------------
# Filtros
# ----------------------------------------------------------------------
FILTROS = {
    "1": ("todo", None, None),
    "2": ("fallos y avisos", {"error", "aviso"}, None),
    "3": ("Telegram (conversacion)", {"mensaje", "turno_inicio", "turno_fin", "respuesta", "cola", "reinicio"}, None),
    "4": ("herramientas y estados", {"estado", "comentario", "hook", "ok"}, None),
}

ETIQUETAS = {
    "mensaje": ("JEFE  ", CIAN),
    "turno_inicio": ("TURNO>", AZUL),
    "turno_fin": ("TURNO<", AZUL),
    "respuesta": ("RESP  ", VERDE),
    "estado": ("HERR  ", GRIS),
    "comentario": ("NOTA  ", BLANCO),
    "error": ("ERROR ", ROJO),
    "aviso": ("AVISO ", AMARILLO),
    "ok": ("OK    ", VERDE),
    "nota": ("BITAC ", MAGENTA),
    "arranque": ("INICIO", VERDE),
    "parada": ("PARADA", AMARILLO),
    "cola": ("COLA  ", AMARILLO),
    "reinicio": ("REINIC", AMARILLO),
    "salud": ("SALUD ", GRIS),
    "vision": ("VISION", MAGENTA),
    "envio": ("ENVIO ", CIAN),
    "telegram_envio": ("TG-SEND", CIAN),
}


def _detalle_legible(ev):
    """Texto corto y util de un evento."""
    t = ev.get("tipo", "?")
    partes = []
    if t == "mensaje":
        partes.append(ev.get("texto", ""))
        if ev.get("canal"):
            partes.append(f"[{ev['canal']}]")
    elif t == "turno_inicio":
        partes.append(ev.get("prompt", "") or "")
        if ev.get("pesado"):
            partes.append("[pesado]")
    elif t == "turno_fin":
        partes.append(f"{ev.get('resultado')} · {ev.get('segundos', '?')}s · {ev.get('chars_respuesta', 0)} chars")
        if ev.get("detalle"):
            partes.append(ev["detalle"])
    elif t == "error":
        partes.append(f"[{ev.get('contexto')}] {ev.get('detalle') or ev.get('excepcion') or ''}")
    elif t in ("aviso", "ok"):
        partes.append(f"[{ev.get('contexto')}] {ev.get('detalle', '')}")
    else:
        for k in ("texto", "detalle", "mensaje", "descripcion"):
            if ev.get(k):
                partes.append(str(ev[k]))
                break
        for k, v in ev.items():
            if k in ("ts", "epoch", "pid", "tipo", "turno"):
                continue
            if str(v) and (not partes or str(v) not in partes[0]):
                partes.append(f"{k}={v}")
    texto = " ".join(str(p) for p in partes if p).replace("\n", " ⏎ ")
    return texto[:260]


def formatear(ev):
    ts = (ev.get("ts") or "")[11:23] or "--:--:--"
    etiqueta, color = ETIQUETAS.get(ev.get("tipo"), ("EVENT ", BLANCO))
    if ev.get("tipo") == "error" and ev.get("critico"):
        etiqueta = "CRITIC"
    return (c(ts, GRIS) + " " + c(etiqueta, color + (NEGRITA if ev.get("tipo") == "error" else "")
                                     if ANSI_OK else "") + " " + _detalle_legible(ev))


# ----------------------------------------------------------------------
# Panel de estado
# ----------------------------------------------------------------------
def panel(estado, resumen, filtro):
    ancho = 100
    linea = c("─" * ancho, GRIS)
    hoy = resumen.get("turnos", {})
    err_ctx = resumen.get("errores_por_contexto", {})
    top_err = ", ".join(f"{k}:{v}" for k, v in list(err_ctx.items())[:3]) or "ninguno"
    bot = f"PID {estado.get('bot_pid')}" if estado.get("bot_pid") else "SIN PROCESO"
    inst = estado.get("bot_instancias", 0)
    omni = ("OK %sms" % estado.get("omniroute_ms")) if estado.get("omniroute_ok") else \
        ("CAIDO (%s)" % estado.get("omniroute_error"))
    reloj = datetime.now().strftime("%H:%M:%S")
    salida = [
        linea,
        c("  JARVIS · TERMINAL DE TRABAJO", NEGRITA + BLANCO)
        + c(f"   filtro: {filtro}   (h=ayuda  q=salir)   {reloj}", GRIS),
        linea,
        ("  " + c("Telegram/bot:", GRIS) + " " + c(bot, VERDE if inst == 1 else ROJO)
         + c(f" ({inst} instancia/s)", GRIS)
         + "   " + c("OmniRoute:", GRIS) + " " + c(omni, VERDE if estado.get("omniroute_ok") else ROJO)),
        ("  " + c("Turnos hoy:", GRIS) + f" {hoy.get('ok', 0)} ok / {hoy.get('fallo', 0)} fallidos"
         + c(f"   prom {resumen.get('promedio_turno_seg', 0)}s", GRIS)
         + "   " + c("Errores:", GRIS) + " " + c(str(resumen.get("errores", 0)),
                                                 ROJO if resumen.get("errores") else VERDE)
         + c(f"  ({top_err})", GRIS)),
        ("  " + c("Ultimo mensaje:", GRIS) + " " + c(str(estado.get("ultimo_mensaje_jefe") or "--")[:60], CIAN)
         + c(f"  {estado.get('ultimo_mensaje_ts') or ''}", GRIS)),
    ]
    if estado.get("ultimo_error"):
        salida.append("  " + c("Ultimo fallo:", GRIS) + " "
                      + c(f"[{estado.get('ultimo_error_contexto')}] {str(estado['ultimo_error'])[:70]}", ROJO)
                      + c(f"  {estado.get('ultimo_error_ts') or ''}", GRIS))
    salida.append(linea)
    return "\n".join(salida)


# ----------------------------------------------------------------------
# Bucle principal
# ----------------------------------------------------------------------
def seguir(desde_error=False, solo_hoy=True):
    filtro_clave = "2" if desde_error else "1"
    nombre_filtro, tipos, _ = FILTROS[filtro_clave]
    archivo = RJ._ruta_dia() if RJ else None
    pos = 0
    if archivo and os.path.exists(archivo):
        pos = os.path.getsize(archivo)
    ultimo_panel = 0.0
    estado = RJ.salud() if RJ else {}
    resumen = RJ.resumen() if RJ else {}
    pendientes = []
    if archivo and os.path.exists(archivo):
        # contexto: ultimas 25 lineas del filtro actual
        for ev in RJ.leer(solo_errores=(filtro_clave == "2"), limite=25):
            if tipos and ev.get("tipo") not in tipos:
                continue
            pendientes.append(formatear(ev))

    limpiar_pantalla()
    sys.stdout.write(panel(estado, resumen, nombre_filtro) + "\n")
    for l in pendientes:
        print(l)
    sys.stdout.write(c("\n  ▸ en vivo… (esperando actividad)\n", GRIS))
    sys.stdout.flush()

    while True:
        # teclado
        try:
            import msvcrt
            while msvcrt.kbhit():
                tecla = msvcrt.getwch().lower()
                if tecla in ("q", "\x1b"):
                    print("\n" + c("  Terminal cerrada. El registro sigue guardandose, jefe.", GRIS))
                    return
                if tecla == "c":
                    limpiar_pantalla()
                    sys.stdout.write(panel(estado, resumen, nombre_filtro) + "\n")
                    sys.stdout.flush()
                elif tecla in FILTROS:
                    filtro_clave = tecla
                    nombre_filtro, tipos, _ = FILTROS[tecla]
                    limpiar_pantalla()
                    sys.stdout.write(panel(estado, resumen, nombre_filtro) + "\n")
                    sys.stdout.flush()
                elif tecla == "5":
                    estado = RJ.salud()
                    resumen = RJ.resumen()
                    limpiar_pantalla()
                    sys.stdout.write(panel(estado, resumen, nombre_filtro) + "\n")
                    sys.stdout.flush()
                elif tecla == "h":
                    limpiar_pantalla()
                    sys.stdout.write(panel(estado, resumen, nombre_filtro) + "\n")
                    print(c("  TECLAS", NEGRITA))
                    print("   1 todo   2 fallos/avisos   3 Telegram   4 herramientas   5 salud ahora   c limpiar   q salir")
                    print(c(f"  Fuente: {archivo}", GRIS))
                    print(c("  Todos los dias quedan guardados en proyectos\\registro\\AAAA-MM-DD.jsonl", GRIS))
                    sys.stdout.flush()
        except Exception:
            pass

        # rotacion de dia
        if RJ:
            nuevo = RJ._ruta_dia()
            if nuevo != archivo:
                archivo = nuevo
                pos = 0
                print(c(f"\n  ── nuevo dia de registro: {os.path.basename(archivo)} ──", GRIS))

        # novedades
        try:
            if archivo and os.path.exists(archivo):
                tam = os.path.getsize(archivo)
                if tam < pos:      # el archivo se recreo
                    pos = 0
                if tam > pos:
                    with open(archivo, "r", encoding="utf-8", errors="replace") as f:
                        f.seek(pos)
                        nuevas = f.readlines()
                        pos = f.tell()
                    for linea in nuevas:
                        linea = linea.strip()
                        if not linea:
                            continue
                        try:
                            ev = json.loads(linea)
                        except Exception:
                            continue
                        if tipos and ev.get("tipo") not in tipos:
                            continue
                        print(formatear(ev))
                    sys.stdout.flush()
        except Exception:
            pass

        # panel cada 10 s
        if time.time() - ultimo_panel > 10:
            ultimo_panel = time.time()
            estado = RJ.salud() if RJ else {}
            resumen = RJ.resumen() if RJ else {}
            sys.stdout.write("\033[s")  # guardar cursor
            sys.stdout.write(panel(estado, resumen, nombre_filtro) + "\n")
            sys.stdout.write(f"  {c('▸ en vivo…', GRIS)}  " + "\033[u")
            sys.stdout.flush()
        time.sleep(0.4)


def main():
    ap = argparse.ArgumentParser(description="Terminal de trabajo de JARVIS (caja negra).")
    ap.add_argument("--desde-error", action="store_true", help="arranca mostrando solo fallos y avisos")
    args = ap.parse_args()
    if not RJ:
        print("No se pudo cargar registro_jarvis.py")
        return 1
    try:
        seguir(desde_error=args.desde_error)
    except KeyboardInterrupt:
        print("\nCerrado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
