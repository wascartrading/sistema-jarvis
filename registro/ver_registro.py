# -*- coding: utf-8 -*-
"""Consultas al registro de JARVIS (caja negra) sin abrir la terminal en vivo.

Ejemplos:
    python registro\\ver_registro.py --resumen
    python registro\\ver_registro.py --errores --dias 3
    python registro\\ver_registro.py --dia ayer --tipo mensaje,turno_fin --ultimos 20
    python registro\\ver_registro.py --buscar "timeout"
    python registro\\ver_registro.py --salud
    python registro\\ver_registro.py --dias-lista
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import registro_jarvis as RJ  # noqa: E402


def _pinta(texto, color):
    if not sys.stdout.isatty():
        return texto
    return f"{color}{texto}\033[0m"


def _linea_legible(ev):
    ts = (ev.get("ts") or "")[11:23] or "--:--:--"
    tipo = ev.get("tipo", "?")
    if tipo == "mensaje":
        cuerpo = f"JEFE: {ev.get('texto', '')}"
    elif tipo == "turno_inicio":
        cuerpo = f"turno abierto ({ev.get('canal', '?')}): {ev.get('prompt', '')[:120]}"
    elif tipo == "turno_fin":
        cuerpo = (f"turno cerrado: {ev.get('resultado')} · {ev.get('segundos', '?')}s · "
                  f"{ev.get('chars_respuesta', 0)} chars {ev.get('detalle', '')}")
    elif tipo == "error":
        cuerpo = f"[{ev.get('contexto')}] {ev.get('detalle') or ev.get('excepcion') or ''}"
    elif tipo in ("aviso", "ok"):
        cuerpo = f"[{ev.get('contexto')}] {ev.get('detalle', '')}"
    else:
        datos = {k: v for k, v in ev.items() if k not in ("ts", "epoch", "pid", "tipo")}
        cuerpo = json.dumps(datos, ensure_ascii=False)[:200]
    return f"{ts}  {tipo:<12} {cuerpo}"


def mostrar_resumen(dias):
    total = {"eventos": 0, "errores": 0, "turnos_ok": 0, "turnos_fallo": 0}
    for dia in dias:
        r = RJ.resumen(dia)
        total["eventos"] += r["eventos"]
        total["errores"] += r["errores"]
        total["turnos_ok"] += r["turnos"]["ok"]
        total["turnos_fallo"] += r["turnos"]["fallo"]
        print(_pinta(f"── {dia} ──", "\033[1m"))
        print(f"  eventos: {r['eventos']}   turnos ok: {r['turnos']['ok']}   "
              f"fallidos: {r['turnos']['fallo']}   prom: {r['promedio_turno_seg']}s")
        print(f"  errores: {r['errores']}  {r['errores_por_contexto'] or ''}")
        if r["herramientas_top"]:
            print("  herramientas:", ", ".join(f"{k} x{v}" for k, v in r["herramientas_top"]))
        tipos = {k: v for k, v in sorted(r["por_tipo"].items(), key=lambda x: -x[1])}
        print(f"  por tipo: {tipos}")
    print(_pinta(f"TOTAL {len(dias)} dia(s): {total}", "\033[1m"))


def main():
    ap = argparse.ArgumentParser(description="Consulta el registro (caja negra) de JARVIS.")
    ap.add_argument("--hoy", action="store_true", help="solo el dia de hoy (por defecto)")
    ap.add_argument("--ayer", action="store_true")
    ap.add_argument("--dia", help="AAAA-MM-DD, hoy o ayer")
    ap.add_argument("--dias", type=int, default=1, help="cuantos dias atras revisar")
    ap.add_argument("--dias-lista", action="store_true", help="lista los dias con registro")
    ap.add_argument("--resumen", action="store_true")
    ap.add_argument("--salud", action="store_true")
    ap.add_argument("--errores", action="store_true", help="solo fallos")
    ap.add_argument("--tipo", help="filtrar por tipo(s), separados por coma")
    ap.add_argument("--buscar", help="texto a buscar en los eventos")
    ap.add_argument("--ultimos", type=int, default=40)
    ap.add_argument("--todo", action="store_true", help="no limitar cantidad")
    args = ap.parse_args()

    if args.dias_lista:
        for d in RJ.dias_disponibles():
            r = RJ.resumen(d)
            print(f"  {d}   {r['eventos']:>6} eventos   {r['errores']:>4} errores   "
                  f"{r['turnos']['ok']:>4} turnos ok")
        return 0

    if args.salud:
        print(json.dumps(RJ.salud(), ensure_ascii=False, indent=2))
        return 0

    dias = []
    if args.dia:
        dias = [args.dia]
    elif args.ayer:
        dias = ["ayer"]
    else:
        from datetime import datetime, timedelta
        n = max(1, args.dias)
        dias = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                for i in range(n)]

    if args.resumen:
        mostrar_resumen(dias)
        return 0

    tipos = {t.strip() for t in args.tipo.split(",")} if args.tipo else None
    limite = None if args.todo else args.ultimos
    total = 0
    for dia in dias:
        evs = RJ.leer(dia, tipos=tipos, solo_errores=args.errores,
                      buscar=args.buscar, limite=limite)
        if not evs:
            continue
        print(_pinta(f"── {dia} ({len(evs)} eventos) ──", "\033[1m"))
        for ev in evs:
            linea = _linea_legible(ev)
            if ev.get("tipo") == "error":
                linea = _pinta(linea, "\033[91m")
            elif ev.get("tipo") == "aviso":
                linea = _pinta(linea, "\033[93m")
            print(linea)
            total += 1
    if total == 0:
        print("Sin eventos para ese filtro.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
