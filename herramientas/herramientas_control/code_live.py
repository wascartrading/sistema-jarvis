#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""code_live.py - OJOS Y MANOS PARA CODIGO, EN VIVO (16/09/2026, orden del jefe).

TRAIDO DEL DESMENUZADO (JARVIS-HRZ, actions/code_agent.py): "Vision + accion
para resolver problemas de codigo en pantalla". Aqui queda adaptado a MI
sistema: el pensamiento pasa por el gateway LOCAL (OmniRoute), cada cambio va
con COPIA DE SEGURIDAD y todo se VERIFICA de verdad (compilar y ejecutar).
Nunca "confio y ya".

Orden del jefe (16/09/2026): "vamos a traer esas joyas: el bucle de ver,
escribir, compilar y corregir; y el self_edit... para cuando yo te pida que
modifiques o arregles un codigo en tiempo real o en vivo".

Acciones (via cli.py, modulo "code" o "code_live"):
  python cli.py code leer <ruta> [desde] [hasta]
  python cli.py code editar <ruta> "<buscar>" "<reemplazar>" [todas=1]
  python cli.py code editar_json <ruta> <archivo.json>
  python cli.py code agregar <ruta> "<texto>"
  python cli.py code compilar <ruta>
  python cli.py code probar <ruta> [timeout]
  python cli.py code reparar <ruta> [vueltas] [modelo]
  python cli.py code abrir <ruta>            (lo muestra en el editor, AL FRENTE)
  python cli.py code escribir "<texto>"      (teclea en el editor que este al frente)

EL BUCLE DE REPARACION (el corazon, igual que el suyo):
  1) compila (py_compile). Si esta bien, lo PRUEBA ejecutandolo.
  2) si falla, le pide al modelo un arreglo en JSON: {"ediciones":[{buscar,reemplazar}]}
  3) aplica las ediciones con copia de seguridad, recompila y repite (3 vueltas).
  4) informa: que cambio, cuantas vueltas y resultado final verificado.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

try:
    from . import vision_deepseek as vd          # gateway OmniRoute + sesion
except Exception:                                 # pragma: no cover
    vd = None

_MARCA = time.strftime("%Y%m%d_%H%M%S")
_MODELO = os.environ.get("JARVIS_CODE_MODELO", "kiro/claude-haiku-4.5")
_TIMEOUT_MODELO = 90.0
_EXT_PY = (".py", ".pyw")


# --------------------------------------------------------------------------
# COPIAS DE SEGURIDAD (nada se toca sin copia previa)
# --------------------------------------------------------------------------
def _bak(ruta):
    """Copia el archivo a <ruta>.bak_AAAAMMDD_HHMMSS y devuelve la ruta."""
    destino = "%s.bak_%s" % (ruta, time.strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(ruta, destino)
    return destino


def copias(ruta):
    """Lista las copias de seguridad de un archivo (mas nueva primero)."""
    carpeta, base = os.path.split(ruta)
    patron = re.compile(re.escape(base) + r"\.bak_(\d{8}_\d{6})$")
    encontradas = []
    for f in os.listdir(carpeta or "."):
        m = patron.match(f)
        if m:
            p = os.path.join(carpeta, f)
            encontradas.append((m.group(1), p))
    return sorted(encontradas, reverse=True)


def restaurar(ruta, copia=None):
    """Devuelve el archivo a una copia (la ultima si no se indica otra)."""
    lista = copias(ruta)
    if not lista:
        return False, "No hay copias de %s" % ruta
    elegida = None
    if copia:
        for marca, p in lista:
            if copia in (marca, p):
                elegida = p
        if not elegida:
            return False, "No encuentro la copia '%s'" % copia
    else:
        elegida = lista[0][1]
    _bak(ruta)                      # copia tambien lo que habia, por si acaso
    shutil.copy2(elegida, ruta)
    return True, "Restaurado desde: %s" % elegida


# --------------------------------------------------------------------------
# LEER / EDITAR
# --------------------------------------------------------------------------
def leer(ruta, desde=None, hasta=None, con_numeros=True):
    """Devuelve el contenido, opcionalmente numerado y por rango de lineas."""
    if not os.path.exists(ruta):
        return "No existe: %s" % ruta
    with open(ruta, encoding="utf-8", errors="replace") as f:
        lineas = f.read().split("\n")
    ini = max(1, int(desde)) if desde else 1
    fin = min(len(lineas), int(hasta)) if hasta else len(lineas)
    trozo = lineas[ini - 1:fin]
    if not con_numeros:
        return "\n".join(trozo)
    ancho = len(str(fin))
    return "\n".join("%*d| %s" % (ancho, i, t)
                     for i, t in enumerate(trozo, start=ini))


def _normaliza_linea(t):
    return re.sub(r"\s+", " ", t.strip())


def _aplicar(ruta, buscar, reemplazar, todas=False):
    """Reemplazo EXACTO. Si no aparece igual, prueba por lineas (espacios
    flexibles). Devuelve (ok, mensaje)."""
    with open(ruta, encoding="utf-8", errors="replace") as f:
        original = f.read()
    # 1) coincidencia exacta
    veces = original.count(buscar)
    if veces == 1 or (veces > 1 and todas):
        nuevo = original.replace(buscar, reemplazar) if todas else \
            original.replace(buscar, reemplazar, 1)
        with open(ruta, "w", encoding="utf-8", newline="") as f:
            f.write(nuevo)
        return True, "reemplazo exacto (%d vez/veces)" % (veces if todas else 1)
    # 2) por lineas (tolera espacios y sangria distintos)
    obj = [_normaliza_linea(l) for l in buscar.split("\n") if l.strip()]
    if obj:
        lineas = original.split("\n")
        norm = [_normaliza_linea(l) for l in lineas]
        hallados = []
        for i in range(len(norm) - len(obj) + 1):
            if norm[i:i + len(obj)] == obj:
                hallados.append(i)
        if hallados:
            i = hallados[0]
            nuevas = (lineas[:i] + reemplazar.split("\n") + lineas[i + len(obj):])
            with open(ruta, "w", encoding="utf-8", newline="") as f:
                f.write("\n".join(nuevas))
            return True, "reemplazo por lineas (posicion %d)" % (i + 1)
    if veces == 0:
        return False, "no encontre el texto exacto ni por lineas"
    return False, "el texto aparece %d veces; usa todas=1 si quieres todas" % veces


def editar(ruta, buscar, reemplazar, todas=False, backup=True):
    """Edita un archivo con copia de seguridad y verificacion de sintaxis."""
    if not os.path.exists(ruta):
        return False, "No existe: %s" % ruta
    respaldo = _bak(ruta) if backup else "(sin copia)"
    ok, msg = _aplicar(ruta, buscar, reemplazar, todas)
    if not ok:
        return False, "%s | copia: %s" % (msg, respaldo)
    extra = ""
    if ruta.lower().endswith(_EXT_PY):
        bien, error = compilar(ruta)
        extra = " | compila OK" if bien else " | OJO, NO COMPILA: %s" % error
    return True, "%s | copia: %s%s" % (msg, respaldo, extra)


def aplicar_ediciones(ruta, ediciones):
    """Aplica una lista [{'buscar':..,'reemplazar':..}] de una sola pasada."""
    respaldo = _bak(ruta)
    aplicadas, fallos = 0, []
    for ed in ediciones:
        buscar = ed.get("buscar") or ed.get("target") or ""
        reemplazar = ed.get("reemplazar", ed.get("replacement", ""))
        if not buscar:
            continue
        ok, msg = _aplicar(ruta, buscar, reemplazar, ed.get("todas", False))
        if ok:
            aplicadas += 1
        else:
            fallos.append("%s -> %s" % (buscar.strip().split("\n")[0][:60], msg))
    return aplicadas, fallos, respaldo


def agregar(ruta, texto, backup=True):
    """Agrega texto al final del archivo (con copia de seguridad)."""
    if not os.path.exists(ruta):
        return False, "No existe: %s" % ruta
    respaldo = _bak(ruta) if backup else "(sin copia)"
    with open(ruta, "a", encoding="utf-8", newline="") as f:
        f.write(texto if texto.endswith("\n") else texto + "\n")
    extra = ""
    if ruta.lower().endswith(_EXT_PY):
        bien, error = compilar(ruta)
        extra = " | compila OK" if bien else " | OJO, NO COMPILA: %s" % error
    return True, "agregado al final | copia: %s%s" % (respaldo, extra)


# --------------------------------------------------------------------------
# VERIFICAR: COMPILAR Y PROBAR
# --------------------------------------------------------------------------
def compilar(ruta):
    """(ok, mensaje). Usa py_compile y devuelve el error tal cual lo da Python."""
    if not os.path.exists(ruta):
        return False, "No existe: %s" % ruta
    if ruta.lower().endswith(".json"):
        try:
            json.load(open(ruta, encoding="utf-8"))
            return True, "JSON valido"
        except Exception as e:
            return False, "JSON invalido: %s" % e
    if not ruta.lower().endswith(_EXT_PY):
        return True, "(sin verificador para esta extension)"
    r = subprocess.run([sys.executable, "-m", "py_compile", ruta],
                       capture_output=True, text=True, errors="replace")
    if r.returncode == 0:
        return True, "compila sin errores"
    salida = (r.stderr or r.stdout or "").strip()
    lineas = [l for l in salida.split("\n") if l.strip()]
    return False, " | ".join(lineas[-4:])


def probar(ruta, timeout=20):
    """Ejecuta el archivo con Python y devuelve (codigo, salida)."""
    try:
        r = subprocess.run([sys.executable, "-X", "utf8", ruta],
                           capture_output=True, text=True, errors="replace",
                           timeout=timeout, cwd=os.path.dirname(ruta) or None)
        salida = ((r.stdout or "") + (r.stderr or "")).strip()
        return r.returncode, salida[-1500:]
    except subprocess.TimeoutExpired:
        return -1, "Se paso de %ss (posible bucle infinito)" % timeout


# --------------------------------------------------------------------------
# EL CEREBRO: pedirle el arreglo al modelo por OmniRoute
# --------------------------------------------------------------------------
def _chat(modelo, prompt, timeout=_TIMEOUT_MODELO):
    """Llamada de SOLO TEXTO al gateway local (OpenAI-compatible)."""
    if vd is None:
        raise RuntimeError("no pude importar vision_deepseek")
    key, url = vd._gateway()
    cuerpo = {
        "model": modelo,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 3000,
        "temperature": 0.1,
    }
    req = urllib.request.Request(
        url, data=json.dumps(cuerpo).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + key,
                 "x-opencode-session": getattr(vd, "_SESSION_ID", "jarvis-code")},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8"))
    txt = (data.get("choices") or [{}])[0].get("message", {}).get("content")
    if isinstance(txt, list):
        txt = " ".join(str(p.get("text", "")) if isinstance(p, dict) else str(p)
                       for p in txt)
    return txt or ""


_PROMPT = (
    "Eres un programador senior y arreglas codigo Python roto.\n"
    "Te paso el ARCHIVO COMPLETO y el ERROR EXACTO de Python.\n"
    "Devuelve SOLO un JSON valido con este formato:\n"
    '{"ediciones": [{"buscar": "texto EXACTO que existe en el archivo",'
    ' "reemplazar": "texto corregido"}], "explicacion": "una linea"}\n'
    "REGLAS: 'buscar' debe copiarse LITERAL (mismos espacios, comas y saltos) "
    "de una parte del archivo; no inventes lineas; no uses markdown; "
    "haz el minimo cambio posible.\n\n"
    "=== ERROR DE PYTHON ===\n%s\n\n=== ARCHIVO %s ===\n%s\n"
)


def _json_de(texto):
    """Saca el primer objeto JSON de la respuesta, aunque venga con ```json."""
    if not texto:
        return None
    limpio = texto.replace("```json", "```").split("```")
    for trozo in limpio:
        i, f = trozo.find("{"), trozo.rfind("}")
        if i >= 0 and f > i:
            try:
                return json.loads(trozo[i:f + 1])
            except Exception:
                continue
    return None


def pedir_arreglo(ruta, codigo, error, modelo=_MODELO):
    """Le pide al modelo las ediciones para arreglar el error. Devuelve dict."""
    prompt = _PROMPT % (error, os.path.basename(ruta), codigo)
    try:
        texto = _chat(modelo, prompt)
    except urllib.error.HTTPError as e:
        return {"error": "el modelo respondio HTTP %s" % e.code}
    except Exception as e:
        return {"error": "no pude hablar con el gateway: %r" % e}
    datos = _json_de(texto)
    if not datos:
        return {"error": "el modelo no devolvio JSON valido",
                "crudo": texto[:300]}
    return datos


# --------------------------------------------------------------------------
# EL BUCLE: REPARAR
# --------------------------------------------------------------------------
def _estado(ruta, ejecutar=True):
    """(ok, error) del archivo: primero compila y luego se ejecuta de verdad.
    Asi el bucle pilla los DOS tipos de fallo: los de sintaxis y los que solo
    aparecen al correr (NameError, TypeError, division por cero...)."""
    bien, error = compilar(ruta)
    if not bien:
        return False, "Error de sintaxis: %s" % error
    if ejecutar and ruta.lower().endswith(_EXT_PY):
        codigo, salida = probar(ruta)
        if codigo != 0 or "Traceback (most recent call last)" in salida:
            return False, "Error al ejecutar (codigo %s): %s" % (codigo, salida[-900:])
        return True, salida
    return True, ""


def reparar(ruta, vueltas=3, modelo=_MODELO, ejecutar_al_final=True):
    """Bucle ver -> escribir -> compilar/ejecutar -> corregir. (ok, resumen)."""
    if not os.path.exists(ruta):
        return False, "No existe: %s" % ruta
    informe = []
    bien, error = _estado(ruta)
    if bien:
        informe.append("ya estaba bien: compila y se ejecuta sin errores")
    for vuelta in range(1, max(1, int(vueltas)) + 1):
        if bien:
            break
        codigo = leer(ruta, con_numeros=False)
        propuesta = pedir_arreglo(ruta, codigo, error, modelo)
        if propuesta.get("error"):
            informe.append("vuelta %d: %s" % (vuelta, propuesta["error"]))
            break
        ediciones = propuesta.get("ediciones") or propuesta.get("edits") or []
        if not ediciones:
            informe.append("vuelta %d: el modelo no propuso ediciones" % vuelta)
            break
        n, fallos, respaldo = aplicar_ediciones(ruta, ediciones)
        informe.append("vuelta %d: %d ediciones aplicadas (copia: %s)"
                       % (vuelta, n, os.path.basename(respaldo)))
        if propuesta.get("explicacion"):
            informe.append("   motivo: %s" % str(propuesta["explicacion"])[:160])
        for f in fallos:
            informe.append("   no pude aplicar: %s" % f)
        bien, error = _estado(ruta)
        if bien:
            informe.append("   revisado: compila y corre bien")
    if not bien:
        informe.append("NO QUEDO ARREGLADO. Ultimo error: %s" % str(error)[:400])
        return False, "\n".join(informe)
    if ejecutar_al_final and ruta.lower().endswith(_EXT_PY):
        codigo_salida, salida = probar(ruta)
        informe.append("prueba de ejecucion: codigo %s" % codigo_salida)
        if salida:
            informe.append("salida: %s" % salida.replace("\n", " / ")[:400])
    return True, "\n".join(informe)


# --------------------------------------------------------------------------
# EN VIVO (para que el jefe lo vea en pantalla)
# --------------------------------------------------------------------------
def abrir(ruta):
    """Abre el archivo en su editor y lo trae AL FRENTE."""
    try:
        from . import file_controller as fc
        return fc.abrir(ruta)
    except Exception as e:
        return False, "No pude abrirlo: %r" % e


def escribir(texto, interval=0.02):
    """Teclea en la ventana que este al frente (modo en vivo)."""
    try:
        from . import text_input as ti
        ti.escribir(texto, interval=interval)
        return True, "tecleado (%d caracteres)" % len(texto)
    except Exception as e:
        return False, "No pude teclear: %r" % e


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def _main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    accion = argv[1].lower()
    args = argv[2:]
    if accion == "leer":
        if not args:
            print("Falta la ruta")
            return 2
        desde = args[1] if len(args) > 1 else None
        hasta = args[2] if len(args) > 2 else None
        print(leer(args[0], desde, hasta))
        return 0
    if accion == "editar":
        if len(args) < 3:
            print('Uso: editar <ruta> "<buscar>" "<reemplazar>" [todas=1]')
            return 2
        todas = len(args) > 3 and "todas=1" in args[3]
        ok, msg = editar(args[0], args[1], args[2], todas=todas)
        print(("OK: " if ok else "FALLO: ") + msg)
        return 0 if ok else 1
    if accion == "editar_json":
        if len(args) < 2:
            print("Uso: editar_json <ruta> <archivo.json>")
            return 2
        datos = json.load(open(args[1], encoding="utf-8"))
        lista = datos.get("ediciones", datos) if isinstance(datos, dict) else datos
        n, fallos, respaldo = aplicar_ediciones(args[0], lista)
        print("Aplicadas: %d | copia: %s" % (n, respaldo))
        for f in fallos:
            print("   fallo:", f)
        return 0
    if accion == "agregar":
        if len(args) < 2:
            print('Uso: agregar <ruta> "<texto>"')
            return 2
        ok, msg = agregar(args[0], args[1])
        print(("OK: " if ok else "FALLO: ") + msg)
        return 0 if ok else 1
    if accion == "compilar":
        if not args:
            print("Falta la ruta")
            return 2
        ok, msg = compilar(args[0])
        print(("COMPILA OK: " if ok else "ERROR: ") + msg)
        return 0 if ok else 1
    if accion == "probar":
        if not args:
            print("Falta la ruta")
            return 2
        t = int(args[1]) if len(args) > 1 else 20
        codigo, salida = probar(args[0], t)
        print("Codigo: %s\n%s" % (codigo, salida))
        return 0
    if accion == "reparar":
        if not args:
            print("Falta la ruta")
            return 2
        vueltas = int(args[1]) if len(args) > 1 else 3
        modelo = args[2] if len(args) > 2 else _MODELO
        ok, resumen = reparar(args[0], vueltas=vueltas, modelo=modelo)
        print(("REPARADO OK\n" if ok else "SIN ARREGLAR\n") + resumen)
        return 0 if ok else 1
    if accion == "abrir":
        if not args:
            print("Falta la ruta")
            return 2
        ok, msg = abrir(args[0])
        print(msg)
        return 0 if ok else 1
    if accion == "escribir":
        if not args:
            print("Falta el texto")
            return 2
        ok, msg = escribir(args[0], float(args[1]) if len(args) > 1 else 0.02)
        print(msg)
        return 0 if ok else 1
    if accion == "copias":
        if not args:
            print("Falta la ruta")
            return 2
        for marca, p in copias(args[0]):
            print("  %s -> %s" % (marca, p))
        return 0
    if accion == "restaurar":
        if not args:
            print("Falta la ruta")
            return 2
        ok, msg = restaurar(args[0], args[1] if len(args) > 1 else None)
        print(("OK: " if ok else "FALLO: ") + msg)
        return 0 if ok else 1
    print("Acciones: leer|editar|editar_json|agregar|compilar|probar|reparar|"
          "abrir|escribir|copias|restaurar")
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
