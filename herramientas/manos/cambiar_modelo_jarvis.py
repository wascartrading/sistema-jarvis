# -*- coding: utf-8 -*-
"""cambiar_modelo_jarvis.py — Cambiar el MOTOR (modelo) de JARVIS por orden.

Orden del senor Wascar, 18/09/2026. Hace EXACTAMENTE lo mismo que el panel de
Ajustes de JARVIS Telegram (Motor -> Guardar y reiniciar), pero desde consola:
asi JARVIS (el modelo) puede cambiar su propio motor cuando el jefe se lo pide
por el chat.

Uso:
    python cambiar_modelo_jarvis.py --ver                  # muestra actual/anterior
    python cambiar_modelo_jarvis.py "muse spark 1.3"       # busca, prueba y guarda
    python cambiar_modelo_jarvis.py "COMBO JARVIS" --reiniciar   # cambia y aplica
    python cambiar_modelo_jarvis.py "X" --simular          # solo muestra que haria

Flujo recomendado (JARVIS, por Telegram):
    1) Jefe: "cambia a muse spark 1.3"  ->  correr el script con ese nombre.
    2) Si sale "Motor CAMBIADO": preguntar "senor, lo reinicio para aplicarlo?"
    3) Con su SI: mismo script con --reiniciar (deja 12 s para que el aviso
       llegue a Telegram y llama al reinicio quirurgico oficial).

NUNCA reinicia por su cuenta: --reiniciar solo se lanza cuando el jefe confirma
(regla de oro del sistema). El cambio de config queda igual que si se hiciera
desde el panel (modelo + modelo_anterior), asi que Ajustes lo muestra al abrir.
"""
import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE = r"C:\Users\wasc4\Documents\Sistema Jarvis\proyectos"
CONFIG_PATH = os.path.join(BASE, "config_jarvis.json")
REINICIO_SCRIPT = (r"C:\Users\wasc4\Documents\Sistema Jarvis\Proyectos de asistente"
                   r"\manos\reinicio_diferido_jarvis.ps1")


def _leer_cfg():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _guardar_cfg(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def _sin_ansi(s):
    return re.sub(r"\x1b\[[0-9;]*m", "", str(s or ""))


def _catalogo():
    """{proveedor: [modelos]} tal como lo ve opencode (opencode models)."""
    try:
        r = subprocess.run(["opencode", "models"], capture_output=True,
                           text=True, timeout=90, encoding="utf-8",
                           errors="replace",
                           creationflags=0x08000000)
    except Exception:
        return {}
    cat = {}
    for linea in _sin_ansi(r.stdout or "").splitlines():
        linea = linea.strip()
        if "/" not in linea or linea.startswith("#"):
            continue
        prov, _, nombre = linea.partition("/")
        prov = prov.strip()
        nombre = nombre.strip()
        if not prov or not nombre:
            continue
        cat.setdefault(prov, [])
        if nombre not in cat[prov]:
            cat[prov].append(nombre)
    return cat


def _normalizar(s):
    s = str(s or "").strip().lower()
    s = s.replace("_", "-").replace(" ", "-")
    while "--" in s:
        s = s.replace("--", "-")
    return s


def _buscar(texto, catalogo):
    """Devuelve (id_exacto, candidatos). Busca por: id exacto -> nombre exacto
    normalizado -> id normalizado -> coincidencia parcial."""
    q = _normalizar(texto)
    q_directo = str(texto or "").strip().lower()
    todos = []
    for prov in sorted(catalogo):
        for m in catalogo[prov]:
            todos.append(prov + "/" + m)
    for mid in todos:
        if mid.lower() == q_directo:
            return mid, []
    exactos = [mid for mid in todos if _normalizar(mid.split("/", 1)[1]) == q]
    if len(exactos) == 1:
        return exactos[0], []
    if len(exactos) > 1:
        return None, sorted(exactos)[:10]
    d2 = [mid for mid in todos if _normalizar(mid) == q]
    if len(d2) == 1:
        return d2[0], []
    if len(d2) > 1:
        return None, sorted(d2)[:10]
    par = [mid for mid in todos if q and q in _normalizar(mid)]
    if len(par) == 1:
        return par[0], []
    if par:
        return None, sorted(par)[:12]
    return None, []


def _probar(modelo, timeout=25):
    """Prueba real (igual que el boton Probar del panel). No deja huerfanos:
    al expirar mata todo el arbol del proceso (taskkill /T)."""
    t0 = time.time()
    p = None
    try:
        p = subprocess.Popen(
            ["opencode", "run", "--model", str(modelo),
             "Responde unicamente: OK"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding="utf-8", errors="replace",
            creationflags=0x08000000)
        try:
            out, err = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"],
                               capture_output=True, timeout=10,
                               creationflags=0x08000000)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
            return {"ok": False, "ms": int((time.time() - t0) * 1000),
                    "error": "timeout"}
        ms = int((time.time() - t0) * 1000)
        if p.returncode == 0 and (out or "").strip():
            return {"ok": True, "ms": ms}
        return {"ok": False, "ms": ms, "error": _sin_ansi(err or "sin salida")[:200]}
    except Exception as e:
        return {"ok": False, "ms": int((time.time() - t0) * 1000),
                "error": str(e)[:200]}


def _reg_cambio(nuevo, anterior):
    try:
        sys.path.insert(0, BASE)
        import registro_jarvis as RJ
        RJ.evento("ok", contexto="cambio_modelo",
                  detalle=f"motor: {anterior} -> {nuevo} (via herramienta)")
    except Exception:
        pass


def _reiniciar():
    """Receta oficial probada: EncodedCommand (no pierde comillas) + el script
    de reinicio diferido (12 s de margen para que el aviso llegue al chat)."""
    try:
        cmd = "& '%s' -Segundos 12" % REINICIO_SCRIPT
        b64 = base64.b64encode(cmd.encode("utf-16-le")).decode()
        subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-EncodedCommand", b64],
            creationflags=0x08000000)
        return True
    except Exception as e:
        print("   detalle:", repr(e))
        return False


def main():
    ap = argparse.ArgumentParser(
        description="Cambia el motor de JARVIS (igual que el panel de Ajustes).")
    ap.add_argument("modelo", nargs="?",
                    help="modelo o parte del nombre (ej: 'muse spark 1.3', 'COMBO JARVIS')")
    ap.add_argument("--ver", action="store_true",
                    help="muestra el modelo actual y el anterior")
    ap.add_argument("--reiniciar", action="store_true",
                    help="aplica el cambio lanzando el reinicio oficial")
    ap.add_argument("--simular", action="store_true",
                    help="solo muestra que haria (sin probar ni escribir)")
    args = ap.parse_args()

    cfg = _leer_cfg()
    actual = str(cfg.get("modelo", "omniroute/COMBO JARVIS"))
    anterior = str(cfg.get("modelo_anterior", "") or "")

    if args.ver or not args.modelo:
        print(f"Motor ACTUAL: {actual}")
        if anterior:
            print(f"Motor ANTERIOR: {anterior}")
        if not args.modelo and not args.ver:
            print('Uso: cambiar_modelo_jarvis.py "nuevo modelo"  |  --ver  |  --reiniciar')
        return 0

    cat = _catalogo()
    if not cat:
        print("❌ No pude leer el catalogo de opencode (opencode models).")
        return 1
    mid, candidatos = _buscar(args.modelo, cat)
    if not mid:
        if candidatos:
            print(f"⚠️ Varios modelos coinciden con «{args.modelo}». Diga el ID exacto:")
            for c in candidatos:
                print("   -", c)
        else:
            print(f"⚠️ No encontre ningun modelo que coincida con «{args.modelo}».")
        return 1

    if mid.lower() == actual.lower():
        print(f"ℹ️ El motor actual ya es «{mid}». No hay nada que cambiar.")
        if args.reiniciar:
            ok = _reiniciar()
            print("🔄 Reinicio lanzado." if ok else "❌ No pude lanzar el reinicio.")
            return 0 if ok else 1
        return 0

    if args.simular:
        print(f"[SIMULACION] Cambiaria: {actual}  ->  {mid}")
        print("[SIMULACION] (luego, con --reiniciar, se aplicaria)")
        return 0

    print(f"⏳ Probando «{mid}» (prueba real, unos segundos)...")
    r = _probar(mid, timeout=25)
    if not (r and r.get("ok")):
        motivo = str((r or {}).get("error", "sin respuesta"))[:120]
        print(f"❌ «{mid}» no esta disponible ahora mismo ({motivo}).")
        print("   NO cambie nada: elija otro modelo.")
        return 1

    if actual and actual != mid:
        cfg["modelo_anterior"] = actual
    cfg["modelo"] = mid
    _guardar_cfg(cfg)
    _reg_cambio(mid, actual)
    print(f"✅ Motor CAMBIADO a «{mid}» (probado: responde en {r.get('ms', 0)} ms).")
    print(f"   (Anterior: {actual})")

    if args.reiniciar:
        ok = _reiniciar()
        if ok:
            print("🔄 Reinicio lanzado (~12 s: deja salir este aviso y aplica el cambio).")
        else:
            print("❌ No pude lanzar el reinicio (use el boton Reiniciar del menu).")
        return 0 if ok else 1

    print("   Para aplicarlo: ejecutar de nuevo con --reiniciar (o cambiar desde Ajustes).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
