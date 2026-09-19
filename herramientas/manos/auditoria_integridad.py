# ============================================================
#  auditoria_jarvis.py (v2) - AUDITORIA DE INTEGRIDAD COMPLETA
#  Temporal (se elimina al terminar). Solo LEE y mide: no cambia nada.
#  v2: corrige los falsos fallos de la v1 (rutas reales de memoria, interfaz
#  del widget embebida, compilacion sin escribir bytecode, CLOSE_WAIT por
#  proceso, tareas con codificacion tolerante) y anade pruebas funcionales.
# ============================================================
import ast
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.request

BASE = r"C:\Users\wasc4\Documents\Sistema Jarvis"
PROY = os.path.join(BASE, "proyectos")
MANOS = os.path.join(BASE, "Proyectos de asistente", "manos")
MEM = r"C:\Users\wasc4\.config\opencode\agent\memoria"
SKIP_DIRS = {"venv", ".venv", "node_modules", "__pycache__", ".git", "build",
             "dist", ".opencode", "site-packages", "Backups", ".cache"}
NO_WIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)
INFORME = []
ok_total = 0
fallos_total = 0


def seccion(t):
    INFORME.append("")
    INFORME.append("== " + t + " ==")


def linea(ok, txt):
    global ok_total, fallos_total
    if ok:
        ok_total += 1
        INFORME.append("  OK    " + txt)
    else:
        fallos_total += 1
        INFORME.append("  FALLO " + txt)


def nota(txt):
    INFORME.append("        " + txt)


def recorrer(raiz, exts):
    for dirpath, dirnames, filenames in os.walk(raiz):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if any(f.endswith(e) for e in exts) and ".bak" not in f:
                yield os.path.join(dirpath, f)


def ps(cmd, timeout=90):
    """PowerShell con codificacion tolerante (la consola en espanol no es utf-8)."""
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                           capture_output=True, timeout=timeout,
                           creationflags=NO_WIN)
        return r.stdout.decode("cp850", "replace")
    except Exception as e:
        return "ERROR: %r" % (e,)


# ---------------- 1) CODIGO: COMPILACION ----------------
seccion("1) COMPILACION DE CODIGO PYTHON")
malos = []
n_py = 0
for ruta in recorrer(PROY, (".py",)):
    n_py += 1
    try:
        with open(ruta, "rb") as fh:
            datos = fh.read()
        compile(datos, ruta, "exec")   # respeta el encoding del archivo
    except SyntaxError as e:
        malos.append("%s -> linea %s: %s" % (os.path.basename(ruta), e.lineno, e.msg))
    except Exception as e:
        malos.append("%s -> %s" % (os.path.basename(ruta), str(e)[:70]))
linea(not malos, "%d archivos .py compilados, %d con error de sintaxis" % (n_py, len(malos)))
for m in malos[:10]:
    nota(m)

# ---------------- 2) JSON VALIDOS ----------------
seccion("2) INTEGRIDAD DE ARCHIVOS JSON")
malos_json = []
n_json = 0
for ruta in recorrer(PROY, (".json",)):
    n_json += 1
    try:
        with open(ruta, "r", encoding="utf-8") as fh:
            json.load(fh)
    except Exception as e:
        malos_json.append("%s -> %s" % (os.path.basename(ruta), str(e)[:60]))
linea(not malos_json, "%d archivos JSON validados, %d corruptos" % (n_json, len(malos_json)))
for m in malos_json[:8]:
    nota(m)

# ---------------- 3) ARCHIVOS CLAVE ----------------
seccion("3) ARCHIVOS CLAVE DEL SISTEMA")
clave = [
    (r"C:\Users\wasc4\.config\opencode\agent\jarvis.md", "Cerebro (jarvis.md)"),
    (os.path.join(BASE, "SISTEMA_JARVIS.md"), "Mapa maestro SISTEMA_JARVIS.md"),
    (os.path.join(PROY, "jarvis_telegram_bot.py"), "Bot de Telegram"),
    (os.path.join(PROY, "autostart_jarvis.ps1"), "Iniciador de arranque con Windows"),
    (os.path.join(PROY, "widget_voz_jarvis", "widget.py"), "Widget de voz"),
    (os.path.join(PROY, "jarvis_movil", "servidor.py"), "Servidor movil"),
    (os.path.join(PROY, "jarvis_movil", "web", "index.html"), "App movil (interfaz)"),
    (os.path.join(PROY, "jarvis_movil", "web", "puente_web.js"), "App movil (puente web)"),
    (os.path.join(PROY, "jarvis_puente", "agente_puente.py"), "Agente del puente"),
    (os.path.join(PROY, "herramientas_control", "cli.py"), "Herramientas de control"),
    (os.path.join(MANOS, "diagnostico_jarvis.py"), "Diagnostico"),
    (os.path.join(MANOS, "lanzar_jarvis_telegram.ps1"), "Lanzador"),
    (os.path.join(MANOS, "reiniciar_jarvis_telegram.ps1"), "Reiniciador"),
    (os.path.join(MANOS, "vigilar_jarvis.ps1"), "Vigilante"),
    (os.path.join(MANOS, "cerrar_jarvis_completo.ps1"), "Cierre completo"),
    (os.path.join(MANOS, "activar_servicios_jarvis.ps1"), "Reactivador de servicios"),
    (os.path.join(MANOS, "probar_web.py"), "Probador web blindado"),
    (os.path.join(MANOS, "ejecutar_admin.py"), "Puente de administrador"),
    (r"C:\Users\wasc4\.omniroute\storage.sqlite", "BD de OmniRoute"),
]
for ruta, nombre in clave:
    linea(os.path.exists(ruta), nombre)
for m in ("reglas_jefe.md", "preferencias.md", "proyectos.md",
          "habilidades_herramientas.md"):
    linea(os.path.exists(os.path.join(MEM, m)), "Memoria del jefe: " + m)
nota("memorias ubicadas en: " + MEM)

# ---------------- 4) INTERFAZ DEL WIDGET ----------------
seccion("4) INTERFAZ DEL WIDGET (esfera)")
try:
    html = os.path.join(PROY, "widget_voz_jarvis", "assets", "widget.html")
    w = open(html, encoding="utf-8", errors="replace").read()
    linea("esfera" in w.lower() and "<" in w,
          "Interfaz de la esfera: assets\\widget.html (%d KB)" % (len(w) // 1024))
    py = open(os.path.join(PROY, "widget_voz_jarvis", "widget.py"),
              encoding="utf-8", errors="replace").read()
    linea("widget.html" in py, "widget.py carga esa interfaz (webview)")
except Exception as e:
    linea(False, "No se pudo leer la interfaz del widget: %s" % str(e)[:60])

# ---------------- 5) FLAGS DE NEUTRALIZACION ----------------
seccion("5) NEUTRALIZACION PEDIDA POR EL JEFE (15/09/2026)")
for f in ("widget_off.flag", "movil_off.flag", "puente_off.flag"):
    linea(os.path.exists(os.path.join(PROY, f)), "Bandera presente: " + f)

# ---------------- 6) AUTOSTART CON WINDOWS ----------------
seccion("6) ARRANQUE CON WINDOWS")
lnk = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows",
                   "Start Menu", "Programs", "Startup", "JARVIS.lnk")
linea(os.path.exists(lnk), "JARVIS.lnk en la carpeta de Inicio")
ps1 = os.path.join(PROY, "autostart_jarvis.ps1")
linea(os.path.exists(ps1), "autostart_jarvis.ps1 generado junto al bot")
try:
    c = open(ps1, encoding="utf-8", errors="replace").read()
    linea("jarvis_telegram_bot.py" in c and "Start-Process" in c,
          "El iniciador arranca el bot oculto")
    linea("20128" in c, "El iniciador levanta OmniRoute si esta caido")
except Exception as e:
    linea(False, "No se pudo leer el iniciador: %s" % str(e)[:60])

# ---------------- 7) PROCESOS Y PUERTOS ----------------
seccion("7) PROCESOS Y PUERTOS")
salida = ps("Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe' OR Name='node.exe'\" | "
            "ForEach-Object { $_.ProcessId.ToString() + '|' + $_.CommandLine }")
bots, widgets, moviles, puentes, omniroute, otros = [], [], [], [], [], []
for l in salida.splitlines():
    l = l.strip()
    if not l or "|" not in l:
        continue
    pid, cmd = l.split("|", 1)
    if "jarvis_telegram_bot" in cmd:
        bots.append(pid)
    elif "widget_voz_jarvis" in cmd:
        widgets.append(pid)
    elif "servidor.py" in cmd:
        moviles.append(pid)
    elif "agente_puente" in cmd:
        puentes.append(pid)
    elif "omniroute" in cmd:
        omniroute.append(pid)
    else:
        otros.append(pid)
linea(len(bots) == 1, "Bot de Telegram: %d instancia(s) %s" % (len(bots), bots))
linea(len(omniroute) >= 1, "OmniRoute: %d proceso(s) %s (lanzador + servidor)" % (len(omniroute), omniroute))
linea(len(widgets) == 0, "Widget de voz APAGADO (0 instancias) - pedido del jefe")
linea(len(moviles) == 0, "Servidor movil APAGADO (0 instancias) - pedido del jefe")
linea(len(puentes) == 0, "Agente del puente APAGADO (0 instancias) - pedido del jefe")
for o in otros:
    nota("otro proceso python/node: PID " + o)

puertos = ps("(Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | "
             "Select-Object -ExpandProperty LocalPort) -join ','").strip()
pl = set(int(x) for x in puertos.split(",") if x.strip().isdigit())
linea(20128 in pl, "OmniRoute escuchando en 20128")
linea(8090 not in pl and 8443 not in pl, "Puertos 8090/8443 libres (movil neutralizado)")
linea(9123 not in pl, "Puerto 9123 libre (sin lock zombie de instancia)")

cw = ps("@(Get-NetTCPConnection -ErrorAction SilentlyContinue | "
        "Where-Object { $_.State -eq 'CloseWait' }) | ForEach-Object { "
        "$p = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue; "
        "$_.OwningProcess.ToString() + '|' + $p.ProcessName }").strip()
cw_lineas = [x.strip() for x in cw.splitlines() if x.strip() and "|" in x]
propios_cw = [x for x in cw_lineas if re.search(r"python|node|opencode", x, re.I) and "OpenCode" not in x]
ajenos_cw = [x for x in cw_lineas if x not in propios_cw]
linea(len(propios_cw) == 0,
      "Conexiones colgadas (CLOSE_WAIT) del sistema JARVIS: %d %s" % (len(propios_cw), propios_cw if propios_cw else ""))
for a in ajenos_cw:
    nota("CLOSE_WAIT de otro programa (no es JARVIS): " + a)

# ---------------- 8) GATEWAY (CEREBRO) ----------------
seccion("8) GATEWAY DEL CEREBRO (OMNIROUTE)")
t0 = time.time()
try:
    with urllib.request.urlopen("http://127.0.0.1:20128/", timeout=8) as r:
        code = r.status
    linea(code == 200, "OmniRoute HTTP %d en %d ms" % (code, int((time.time() - t0) * 1000)))
except Exception as e:
    linea(False, "OmniRoute no responde: %s" % str(e)[:70])
try:
    con = sqlite3.connect(r"C:\Users\wasc4\.omniroute\storage.sqlite")
    tablas = [f[0] for f in con.execute(
        "select name from sqlite_master where type='table'").fetchall()]
    linea(True, "BD OmniRoute legible: %d tablas" % len(tablas))
    if "combos" in tablas:
        filas = con.execute("select name from combos").fetchall()
        nombres = [str(f[0]) for f in filas]
        linea(any("JARVIS" in n.upper() for n in nombres),
              "Combo del cerebro presente: %s" % ", ".join(nombres))
    else:
        linea(False, "Tabla 'combos' AUSENTE en la BD")
    con.close()
except Exception as e:
    linea(False, "BD OmniRoute ilegible: %s" % str(e)[:70])

# ---------------- 9) DATOS DEL BOT ----------------
seccion("9) DATOS Y ESTADO DEL BOT")
for arch, nombre in (("historial_muse.json", "Historial de conversaciones"),
                     ("pool_sesiones_jarvis.json", "Pool de sesiones"),
                     ("config_jarvis.json", "Configuracion")):
    p = os.path.join(PROY, arch)
    if not os.path.exists(p):
        linea(False, nombre + " no existe")
        continue
    try:
        with open(p, "r", encoding="utf-8") as fh:
            d = json.load(fh)
        extra = " (%d %s)" % (len(d), "elementos" if isinstance(d, list) else "claves")
        linea(True, nombre + extra)
    except Exception as e:
        linea(False, nombre + " corrupto: " + str(e)[:60])

salida = ps("Get-Content \"$env:TEMP\\opencode\\jarvis_bot_err.log\" -Tail 300 -ErrorAction SilentlyContinue")
errores = [l for l in salida.splitlines() if re.search(r"Traceback|Error|Exception", l)]
linea(len(errores) == 0, "Log de errores del bot: %s" % ("limpio" if not errores else "%d lineas con error" % len(errores)))
for e in errores[:5]:
    nota(e[:110])

salida = ps("Get-Content \"$env:TEMP\\opencode\\jarvis_bot_out.log\" -Tail 400 -ErrorAction SilentlyContinue")
arranques = len(re.findall(r"Iniciando bot de Telegram", salida))
linea(True, "Arranques del bot registrados (ultimas 400 lineas): %d" % arranques)
linea("NEUTRALIZADO (widget_off.flag)" in salida,
      "El candado del widget actuo en el ultimo arranque")

# ---------------- 10) TAREAS PROGRAMADAS ----------------
seccion("10) TAREAS PROGRAMADAS DEL SISTEMA")
salida = ps("schtasks /query /fo CSV /nh")
for nombre in ("JARVIS Vigilante", "JARVIS_ELEVADO"):
    if nombre in salida:
        estado = "Listo" if nombre in salida else "?"
        linea(True, "Tarea programada presente: " + nombre)
    else:
        linea(False, "Tarea programada AUSENTE: " + nombre)

# ---------------- 11) PRUEBAS FUNCIONALES ----------------
seccion("11) PRUEBAS FUNCIONALES REALES")
# 11.1 Filtro del prefijo del comentario (casos reales)
try:
    src = open(os.path.join(PROY, "jarvis_telegram_bot.py"), encoding="utf-8").read()
    arbol = ast.parse(src)
    fuente = None
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.FunctionDef) and nodo.name == "limpiar_comentario_jefe":
            fuente = ast.get_source_segment(src, nodo)
            break
    ns = {"re": re}
    exec(fuente, ns)
    f = ns["limpiar_comentario_jefe"]
    casos = {
        "Comentario, jefe: Hola jefe": "Hola jefe",
        "💬 **Comentario, jefe:** Voy al punto": "Voy al punto",
        "Comentario jefe - Abro el archivo": "Abro el archivo",
        "Comentario, JEFE: Mayusculas": "Mayusculas",
        "Sin prefijo": "Sin prefijo",
    }
    malos_c = [k for k, v in casos.items() if f(k) != v]
    linea(not malos_c, "Filtro del prefijo del comentario: %d/%d casos correctos"
          % (len(casos) - len(malos_c), len(casos)))
    linea(f("Comentario, jefe:") == "", "Comentario vacio tras limpiar: se descarta")
except Exception as e:
    linea(False, "No se pudo probar el filtro: %s" % str(e)[:70])

# 11.2 Herramientas de control (prueba real del cli)
try:
    cli = os.path.join(PROY, "herramientas_control", "cli.py")
    r = subprocess.run([sys.executable, cli, "system", "info"],
                       capture_output=True, timeout=90, cwd=os.path.dirname(cli),
                       creationflags=NO_WIN)
    txt = (r.stdout or b"").decode("utf-8", "replace")
    linea(r.returncode == 0 and len(txt.strip()) > 0,
          "Herramientas de control responden (system info): %d bytes de salida" % len(txt))
except Exception as e:
    linea(False, "Herramientas de control: %s" % str(e)[:70])

# 11.3 Lock del widget apunta a un PID muerto?
try:
    lk = os.path.join(PROY, "widget_voz_jarvis", "widget.lock")
    if os.path.exists(lk):
        pid_lk = open(lk, encoding="utf-8").read().strip()
        vivo = ps("@(Get-Process -Id %s -ErrorAction SilentlyContinue).Count" % pid_lk).strip()
        linea(vivo in ("0", ""),
              "widget.lock apunta a PID %s (%s)" % (pid_lk, "muerto, sin fantasma" if vivo in ("0", "") else "VIVO"))
    else:
        linea(True, "Sin widget.lock (widget nunca arrancado)")
except Exception as e:
    linea(False, "widget.lock: %s" % str(e)[:60])

# ---------------- INFORME ----------------
print("\n".join(INFORME))
print("")
print("RESULTADO GLOBAL: %d comprobaciones OK, %d fallos" % (ok_total, fallos_total))
