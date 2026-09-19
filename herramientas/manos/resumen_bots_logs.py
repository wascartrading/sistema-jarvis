# -*- coding: utf-8 -*-
"""resumen_bots_logs.py — Lee los logs de los bots 24/7 y saca el resumen.

Uso:
    python resumen_bots_logs.py <archivo.log> [<archivo2.log> ...]

Saca, por cada log: la ventana de tiempo que cubre, cuántas marcas de inicio
de sesión hay (para saber si hubo reinicios automáticos), si aparecen
Traceback o SIGTERM, el último estado completo del bot (cuenta, balance,
profit, operativas, winrate, martingala) y el último contador de WS.

No inventa nada: si un dato no está en el log, lo dice con un guion.
"""

import re
import sys

# la consola de Windows no entiende todo: que no tumbe el resumen
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

RUIDO = ("newer Railway CLI", "railway upgrade", "CategoryInfo",
         "FullyQualifiedErrorId", "En línea", "En linea", "node.exe :",
         "System.Management.Automation", "+ ", "Warning: Permanently added")

# --- patrones del bot ---
P_ESTADO = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}\s+(.*)$")
P_MINUTO = re.compile(r"MINUTO\s+(\d{2}:\d{2}(?::\d{2})?)\s*\|\s*activos:\s*(\d+)\s*\|\s*listos:\s*(\d+)\s*\|\s*MG:\s*(\d+)")
P_CUENTA = re.compile(r"CUENTA:\s*(.+?)\s*\|\s*EMAIL:\s*(\S+)")
P_BALANCE = re.compile(r"BALANCE:\s*(\S+)\s*\|\s*PROFIT SESION:\s*(\S+)")
P_OPS = re.compile(r"OPERATIVAS:\s*(\d+)\s*tomadas\s*\|\s*G:\s*(\d+)\s*\|\s*P:\s*(\d+)\s*\|\s*E:\s*(\d+)\s*\|\s*RECHAZADAS:\s*(\d+)\s*\|\s*WINRATE:\s*([\d.]+)%")
P_MG = re.compile(r"MARTINGALA:\s*nivel\s*(\d+)\s*\|\s*monto actual\s*(\S+)")
P_WS = re.compile(r"WS:\s*(\d+)\s*llamada\(s\)\s*este minuto\s*\(total\s*(\d+)\)")


def marca(linea):
    """Devuelve el texto tras la fecha, o la linea entera."""
    m = P_ESTADO.match(linea.strip())
    return m.group(1).strip() if m else linea.strip()


def fecha(linea):
    m = re.match(r"^(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2})", linea.strip())
    return m.group(1) if m else "?"


def resumen(ruta):
    print("=" * 62)
    print("ARCHIVO:", ruta)
    try:
        with open(ruta, encoding="utf-8-sig", errors="replace") as f:
            lineas = [l.rstrip("\n") for l in f if l.strip()]
    except OSError as e:
        print("  no se pudo leer:", e)
        return
    lineas = [l for l in lineas if not any(r in l for r in RUIDO)]
    if not lineas:
        print("  log vacio")
        return

    print("VENTANA:", fecha(lineas[0]), "->", fecha(lineas[-1]),
          f"({len(lineas)} lineas)")
    print("PRIMERAS LINEAS:")
    for l in lineas[:3]:
        print("   ", l[:110])

    # --- huecos: si el bot deja de escribir un rato, algo paso ---
    import datetime as dt

    def a_fecha(linea):
        try:
            return dt.datetime.fromisoformat(fecha(linea).replace(" ", "T"))
        except ValueError:
            return None

    huecos, previa = [], None
    for l in lineas:
        f = a_fecha(l)
        if f is None:
            continue
        if previa and (f - previa).total_seconds() > 180:
            huecos.append((previa, f, int((f - previa).total_seconds())))
        previa = f
    print(f"HUECOS de mas de 3 minutos sin escribir: {len(huecos)}")
    for ini, fin, seg in huecos[-6:]:
        print(f"    de {ini} a {fin} ({seg // 60} min)" + ("  <-- posible reinicio" if seg > 600 else ""))

    # --- marcas de arranque / sesion ---
    claves = ("INICIO DE SESION", "SESION INICIADA", "SESION NUEVA",
              "ABRIENDO SESION", "NUEVA SESION", "ARRANCANDO", "INICIANDO",
              "VERSION DEL BOT", "CONEXION ESTABLECIDA")
    arranques = [l for l in lineas if any(k in l.upper() for k in claves)]
    print(f"MARCAS DE SESION/ARRANQUE: {len(arranques)}")
    for l in arranques[-6:]:
        print("   ", fecha(l), marca(l)[:110])

    # --- errores ---
    for palabra in ("Traceback", "SIGTERM", "SIGKILL", "Exception",
                    "reinici", "MemoryError", "Killed"):
        n = sum(1 for l in lineas if palabra.lower() in l.lower())
        print(f"{palabra:<12}: {n}")

    # --- ultimo estado completo ---
    ult = {}
    for l in lineas:
        t = marca(l)
        m = P_MINUTO.search(t)
        if m:
            ult = {"minuto": m.group(1), "activos": m.group(2),
                   "listos": m.group(3), "mg": m.group(4), "hora": fecha(l)}
            continue
        for clave, patron in (("cuenta", P_CUENTA), ("balance", P_BALANCE),
                              ("ops", P_OPS), ("martingala", P_MG), ("ws", P_WS)):
            m = patron.search(t)
            if m:
                ult[clave] = m.groups()
    print("ULTIMO ESTADO:")
    if "minuto" in ult:
        print(f"  hora {ult['hora']} · minuto {ult['minuto']} · "
              f"activos en seguimiento {ult['activos']} · listos {ult['listos']} · "
              f"MG {ult['mg']}")
    if "cuenta" in ult:
        print(f"  cuenta {ult['cuenta'][0]} · email {ult['cuenta'][1]}")
    if "balance" in ult:
        print(f"  balance {ult['balance'][0]} · profit sesion {ult['balance'][1]}")
    if "ops" in ult:
        tomadas, g, p, e, r, w = ult["ops"]
        print(f"  operativas {tomadas} tomadas · G {g} · P {p} · E {e} · "
              f"rechazadas {r} · winrate {w}%")
    if "martingala" in ult:
        print(f"  martingala nivel {ult['martingala'][0]} · monto {ult['martingala'][1]}")
    if "ws" in ult:
        print(f"  WS ultimo minuto {ult['ws'][0]} · total {ult['ws'][1]}")
    print( "  (los datos son del ultimo reporte que el bot escribio)")


def main():
    rutas = sys.argv[1:]
    if not rutas:
        print("uso: python resumen_bots_logs.py <archivo.log> [mas archivos]")
        return 1
    for r in rutas:
        resumen(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
