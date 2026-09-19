"""
JARVIS Telegram Bot
===================
Bot de Telegram de JARVIS, con el combo COMBO JARVIS via OmniRoute y
transcripcion de notas de voz con faster-whisper.

Configuracion:
- TOKEN: token del bot de Telegram (lo da @BotFather)
- CHAT_ID: tu ID de Telegram (lo da @userinfobot o @getidsbot)

Uso:
  1. Crear bot en @BotFather -> /newbot -> copiar token
  2. Obtener tu CHAT_ID enviando /start a @userinfobot
  3. Pegar ambos valores abajo
  4. Ejecutar: python jarvis_telegram_bot.py
"""

import asyncio
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import importlib.util
import itertools
from datetime import datetime

# Forzar UTF-8 en la salida (consola/log): los emojis de los estados y
# respuestas no deben romper la codificacion cp1252 de Windows.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ============================================================================
# REGISTRO CENTRAL ("caja negra") - orden del señor Wáscar 15/09/2026
# Todo lo que hace JARVIS y todo lo que falla queda escrito por dia en
# proyectos\registro\AAAA-MM-DD.jsonl (nunca se sobrescribe). Se consulta con:
#   python registro\terminal_jarvis.py     (visor en vivo)
#   python registro\ver_registro.py --errores --dias 3
# Es a prueba de fallos: si el registro falla, jamas tumba al bot.
# ============================================================================
try:
    import registro_jarvis as REG
except Exception as _e_reg:
    REG = None
    print(f"[REGISTRO] aviso: no pude cargar registro_jarvis ({_e_reg!r})")


def _reg(tipo, **datos):
    """Anota un evento en la caja negra (nunca lanza)."""
    if REG is None:
        return None
    try:
        return REG.evento(tipo, **datos)
    except Exception:
        return None


def _reg_error(contexto, detalle="", exc=None, **extra):
    if REG is None:
        return None
    try:
        return REG.error(contexto, detalle=detalle, exc=exc, **extra)
    except Exception:
        return None


def _reg_ok(contexto, detalle="", **extra):
    if REG is None:
        return None
    try:
        return REG.ok(contexto, detalle=detalle, **extra)
    except Exception:
        return None


from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# -------------------- CONFIGURACION (EDITAR ESTO) --------------------
TOKEN = "8306558302:AAFNm0IH6Hc-nldoLgYm6PzUZGXSAq0Vz54"
CHAT_ID = "8456515934"
# ---------------------------------------------------------------------

# Proteccion de instancia unica: puerto local de lock (evita que dos bots
# con el mismo token se maten entre si con el error Conflict de Telegram)
PUERTO_LOCK = 9123
_lock_socket = None

# MODO COMBO JARVIS via OmniRoute (ACTUAL 31/08/2026): JARVIS Telegram usa el
# agente unico "jarvis" con el combo COMBO JARVIS (OmniRoute localhost:20128)
# como modelo, con herramientas y estados en vivo.
MODO_MUSE = True
MUSE_MODEL = "omniroute/COMBO JARVIS"
MUSE_AGENT_JARVIS = "jarvis"

# ============================================================================
# SELECTOR DE AGENTE DESDE LA APP (orden del señor Wáscar 15/09/2026)
# ============================================================================
# La app movil tiene un apartado en Ajustes para elegir CON QUE AGENTE habla.
# Por defecto JARVIS; el señor Wáscar pidio añadir tambien al DOCTOR (el agente que usa
# en opencode para diagnosticar/reparar el sistema).
# REGLA DEL señor Wáscar: al usar OTRO agente se le inyecta UNICAMENTE la informacion
# de ESE agente; nada de informacion extra. En la practica significa:
#   1) NO se impone modelo: el agente usa el suyo (el de su propio archivo).
#   2) NO se inyecta el puente de memoria conversacional de JARVIS.
#   3) NO se reutiliza la sesion de JARVIS: cada agente tiene SU sesion por chat.
# El bot de Telegram NO se ve afectado (alli sigue mandando config_jarvis.json).
AGENTES_APP = [
    ("jarvis", "🎩 JARVIS", "jarvis.md"),
    ("doctor", "🩺 Doctor", "doctor.md"),
]
DIR_AGENTES = os.path.join(os.path.expanduser("~"), ".config", "opencode", "agent")


def agentes_disponibles():
    """Agentes de AGENTES_APP que EXISTEN de verdad en la PC (con su archivo)."""
    salida = []
    try:
        for clave, nombre, archivo in AGENTES_APP:
            if os.path.isfile(os.path.join(DIR_AGENTES, archivo)):
                salida.append({"clave": clave, "nombre": nombre})
    except Exception:
        pass
    if not salida:
        salida = [{"clave": MUSE_AGENT_JARVIS, "nombre": "🎩 JARVIS"}]
    return salida


def _args_opencode(agente):
    """Comando base de opencode para ese agente.

    ORDEN DEL señor Wáscar (15/09/2026): el MOTOR es SIEMPRE el mismo — COMBO JARVIS
    por OmniRoute. Lo unico que cambia al elegir agente es el CEREBRO (el .md
    que opencode inyecta junto con el mensaje). Por eso el modelo se impone
    SIEMPRE, tambien al doctor: antes el doctor tiraba de su propio modelo
    (deepseek-v4-flash) y el señor Wáscar notaba que las respuestas cambiaban de sabor
    al cambiar de agente."""
    return [OPENCODE_CMD, "run", "--agent", agente, "--model", MUSE_MODEL]


def _con_modelo_activo(prompt):
    """Adjunta SIEMPRE el modelo activo al prompt que recibe JARVIS (orden
    del senor Wascar 18/09/2026): asi sabe con exactitud con que modelo
    responde aunque se cambie desde Ajustes (COMBO JARVIS, GLM, GPT...).
    Se recalcula en cada turno desde MUSE_MODEL (config en vivo)."""
    m = str(MUSE_MODEL or "")
    if m.startswith("omniroute/"):
        ruta = "corre a traves de OmniRoute (gateway local, 127.0.0.1:20128)"
    elif "/" in m:
        ruta = "corre a traves del proveedor " + m.split("/", 1)[0]
    else:
        ruta = "corre en local"
    return ("[MODELO ACTIVO ahora mismo: %s - %s. Si el senor Wascar "
            "pregunta con que modelo le respondes, di EXACTAMENTE este "
            "nombre y por donde corre.]\n\n%s" % (m, ruta, prompt))


# Historial y sesion para COMBO JARVIS via Opencode
HISTORIAL_MUSE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "historial_muse.json")
# Pool de sesiones rotativas: el bot oscila entre varias sesiones de opencode
# para que ninguna se llene de contexto (respuestas rapidas y sin degradar).
POOL_SESIONES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "pool_sesiones_jarvis.json")
# 12/09/2026 (BLINDAJE DE MEMORIA, orden del señor Wáscar): el pool y la memoria se
# ampliaron para que JARVIS NUNCA olvide el contexto de sus chats. Con
# trabajos largos (fixes, informes, proyectos) el margen anterior (4 sesiones,
# 10 msgs, 8 turnos x 800 chars) dejaba "agujeros de memoria" al rotar o
# expulsar sesiones. Ahora: sesiones mas amplias, pool mas grande, mas turnos
# inyectados, mas caracteres por turno y mas historial conservado. El señor Wáscar
# prioriza memoria sobre velocidad ("gran margen, no te preocupes por eso").
MAX_SESIONES_POOL = 6          # maximo de sesiones en el pool (antes 4)
# 13/09/2026 (FASE 2 peso, orden del señor Wáscar): rotar antes (20 -> 12) para que
# ninguna sesion acumule demasiado contexto. La memoria NO se pierde: el hilo
# se conserva con el puente inyectado al rotar (FASE 1) + historial_muse.json.
MSGS_MAX_POR_SESION = 10       # mensajes por sesion antes de rotar (antes 20, luego 12; 18/09/2026 orden del señor Wáscar: 10 con el vigilante de turnos)

# ============================================================================
# SESION FIJADA POR CHAT (15/09/2026, orden del señor Wáscar: "selector de chats")
# ============================================================================
# La APP movil tiene varios chats: cada chat es un hilo distinto y debe usar
# SU PROPIA sesion de opencode (cerebro propio). La app pide por WebSocket:
#   - "usa esta sesion"  -> SESION_FIJADA = sid
#   - "chat nuevo"       -> SESION_NUEVA_PEDIDA = True (+ SIN_PUENTE_MEMORIA)
# El bot de Telegram NO toca nada de esto: con los valores por defecto se
# comporta EXACTAMENTE igual que antes (rotacion por pool).
SESION_FIJADA = None           # sid que la app quiere usar SIEMPRE (o None)
SESION_NUEVA_PEDIDA = False    # la app pidio un chat NUEVO (sesion en blanco)
SIN_PUENTE_MEMORIA = False     # chat nuevo: NO inyectar la memoria conversacional
ULTIMO_SID = None              # sid REALMENTE usado en el ultimo turno (lo lee la app)
# 12/09/2026 (MODO TRABAJO, orden del señor Wáscar): cuando hay un trabajo en curso
# (crear/modificar un producto), la sesion se PINEA y NO rota aunque supere el
# limite normal, para que JARVIS nunca arranque desde cero a mitad del trabajo.
MSGS_MAX_TRABAJO = 60          # tope duro de una sesion pineada (3x el normal)
TRABAJO_TIMEOUT_SEG = 15 * 60  # 15 min sin actividad del señor Wáscar = se desancla sola
# Comandos manuales del señor Wáscar y verbos de trabajo para deteccion automatica.
TRABAJO_ON = ("modo trabajo", "modo trabajo on", "activa modo trabajo",
              "blinda la sesion", "pon modo trabajo")
TRABAJO_OFF = ("modo trabajo off", "sal del modo trabajo",
               "desactiva modo trabajo", "terminamos", "cambio de tema",
               "fuera del modo trabajo")
TRABAJO_VERBOS = ("crea", "crear", "crearme", "modifica", "modificar",
                  "arregla", "arreglar", "corrige", "corregir", "implementa",
                  "implementar", "hazme", "haz un", "haz una", "instala",
                  "instalar", "agrega", "agregar", "añade", "añadir", "cambia",
                  "cambiar", "actualiza", "actualizar", "construye",
                  "construir", "descarga", "descargar", "genera", "generar",
                  "desarrolla", "desarrollar", "crear un", "crear una")
MUSE_MAX_HISTORIAL = 80        # turnos conservados en historial_muse.json (antes 40)
MUSE_HISTORIAL_INYECTAR = 10   # turnos inyectados al modelo (antes 24, 17/09/2026: dieta de tokens por orden del señor Wáscar)
# 13/09/2026 (FASE 2 peso): 1600 -> 1000 chars por turno en el puente de
# memoria. Como el puente se inyecta SOLO al rotar (FASE 1), sobra holgura.
MUSE_CHARS_POR_MENSAJE = 1000  # chars por mensaje en el contexto inyectado (antes 1600)
OPENCODE_CMD = "opencode"
TRANSCRIBIR_AUDIO_PATH = os.path.expanduser(
    r"~\Documents\Sistema Jarvis\Proyectos de asistente\manos\transcribir_audio.py"
)
# (11/09/2026, orden del señor Wáscar): ELIMINADO el sistema de casos / acciones
# inmediatas (NIVEL 1 sin modelo). Todas las ordenes van al modelo; nada se
# intercepta en el bot.

# -------------------- CONFIG EXTERNA EDITABLE (VENTANA AJUSTES) --------------------
# El bot lee config_jarvis.json al arrancar (si no existe, lo crea con los
# valores por defecto de arriba). La ventana "Ajustes" de la bandeja edita
# este archivo: token, chat_id, agente, modelo y timeout. Los cambios se
# aplican al reiniciar JARVIS.
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "config_jarvis.json")

# ---------------------------------------------------------------------------
# RELOJ UNICO DEL señor Wáscar (16/09/2026, orden del señor Wáscar)
# ---------------------------------------------------------------------------
# Orden literal del señor Wáscar: "Dejalo tal cual esta por ahora, solo sube todo a
# 700 seg sin importar que sean mensajes normales o largos, y asegurate de que
# cualquier mensaje que me envies a traves de Telegram reinicie el reloj."
#
# - UN SOLO RELOJ: 700 s. Se acabo el 180 (normal) / 600 (pesado) / 900 (app):
#   todos valen lo mismo. La app movil usa ESTE MISMO modulo (servidor.py hace
#   "import jarvis_telegram_bot as bot"), asi que hereda el reloj igual.
# - El reloj mide SILENCIO (ni una linea de salida del proceso), nunca duracion
#   total: mientras el proceso hable, el trabajo sigue vivo y no se corta.
# - CADA mensaje que el señor Wáscar recibe por Telegram (estado o comentario) pone el
#   reloj a cero: ver _latido_mensaje_tg() dentro de _ejecutar_opencode.
RELOJ_TELEGRAM = 700     # segundos de silencio permitidos (normal y pesado)
RELOJ_AVISO = 350        # aviso "sigo trabajando" a mitad de camino (no corta)
# 16/09/2026 (confirmacion del señor Wáscar): "cada vez que tu me envies un mensaje se
# reinicia el reloj" — tambien los latidos automaticos. Eso solo es seguro con
# una red debajo: si el proceso no produce NADA REAL en este tiempo (solo
# latidos automaticos), se considera colgado de verdad y se suelta. Asi el señor Wáscar
# nunca pierde un trabajo que habla, y un cuelgue real tampoco bloquea el bot.
TECHO_COLGADO = 1800     # 30 min sin NINGUNA salida real -> se suelta

DEFAULT_CONFIG = {
    "token": TOKEN,
    "chat_id": CHAT_ID,
    "agente": MUSE_AGENT_JARVIS,
    "modelo": MUSE_MODEL,
    # 16/09/2026 (orden del señor Wáscar): el timeout por defecto tambien es el unico.
    "timeout": RELOJ_TELEGRAM,
    "autostart": True,
}
TIMEOUT_MUSE = DEFAULT_CONFIG["timeout"]

# -------------------- TRABAJO PESADO (02/09/2026) --------------------
# Solucion pedida por el señor Wáscar: cuando un pedido es de investigacion,
# informe largo o mensaje extenso, el bot avisa al instante y da un margen
# de tiempo mucho mayor (TIMEOUT_PESADO) para que el informe SIEMPRE llegue
# completo. Los 90s normales se quedan cortos en tareas largas y eso
# provocaba el "Sigo en ello..." sin resultado.
# 09/09/2026 (regla del señor Wáscar): "no tengas miedo en alargar el tiempo" ->
# Base normal 180s, pesado 480s (8 min). El vigilante usa las ventanas
# dinamicas de _ejecutar_opencode: solo mata por colgamiento real.
# 12/09/2026 (orden del señor Wáscar, BLINDAJE): subido a 600s (10 min) para
# trabajos aun mas pesados; el tope de seguridad sigue en 1200s.
# 16/09/2026 (orden del señor Wáscar): pesado = normal = RELOJ_TELEGRAM (700 s).
TIMEOUT_PESADO = RELOJ_TELEGRAM  # segundos de margen para tareas pesadas
LONGITUD_PESADO = 1             # 11/09/2026 (orden del señor Wáscar): cualquier mensaje
                                # (>= 1 char) = pesado -> margen amplio SIEMPRE,
                                # pero el aviso ya NO se muestra en el chat.
PALABRAS_PESADO = (
    "investiga", "investigacion", "investigación", "informe",
    "busca", "búsqueda", "buscame", "búscame", "analiza", "analiz",
    "horarios", "horario", "mercados", "mercado", "reporte", "resumen",
    "elabora", "desarrolla", "comparacion", "comparación", "profundiza",
    "hazme un", "hazme una", "crea un", "crea una", "escribe un",
    "escribe una", "cuanto cuesta", "qué tal", "cual es el", "cuál es el",
    "explica con detalle", "paso a paso",
)

# ---------------------------------------------------------------------------
# BLINDAJE ANTI-CUELGUE (15/09/2026, orden del señor Wáscar)
# ---------------------------------------------------------------------------
# Ese dia un `opencode run` se quedo colgado 45 minutos: el agente verificaba
# su cambio con un Brave headless que en esta PC se traba para siempre (ver
# Proyectos de asistente/manos/probar_web.py), la herramienta nunca devolvia,
# y el turno se quedo mudo sin que la app recibiera nada.
# El vigilante SI lo habria matado, pero tarde: con timeout=900 (el que usa
# el servidor de la app) la formula antigua (timeout*6) permitia 90 MINUTOS
# de mudez. Ahora la mudez tiene tope ABSOLUTO. No se toca la regla de oro:
# "trabajo vivo = sin reloj" — estas ventanas solo miden SILENCIO TOTAL
# (ni una linea de salida), nunca duracion.
# 16/09/2026 (orden del señor Wáscar): estas tres ventanas quedaron EN DESUSO. El
# vigilante ya no las usa: ahora todo se rige por el RELOJ UNICO de 700 s
# (RELOJ_TELEGRAM / RELOJ_AVISO, arriba). Se dejan aqui como historial del
# blindaje del 15/09 y para no romper nada que las importe.
MUDEZ_AVISO_TRABAJO = 420        # (en desuso) 7 min mudos -> aviso
MUDEZ_MUERTE_TRABAJO = 1500      # (en desuso) 25 min mudos -> se mata
MUDEZ_MUERTE_TOPE_NORMAL = 1800  # (en desuso) 30 min mudos: tope maximo


def _guardar_config(datos):
    """Guarda los ajustes en config_jarvis.json (ventana Ajustes)."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        print("[CONFIG] ajustes guardados en config_jarvis.json")
        return True
    except Exception as e:
        print(f"[CONFIG] error guardando ajustes: {e!r}")
        return False


def _cargar_config():
    """Carga config_jarvis.json si existe y aplica los valores a los
    globales del bot. Si no existe, crea el archivo con los valores por
    defecto (asi la ventana Ajustes siempre tiene algo que mostrar)."""
    global TOKEN, CHAT_ID, MUSE_AGENT_JARVIS, MUSE_MODEL, TIMEOUT_MUSE
    try:
        if not os.path.exists(CONFIG_PATH):
            _guardar_config(DEFAULT_CONFIG)
            return
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if not isinstance(cfg, dict):
            raise ValueError("config invalida")
        TOKEN = str(cfg.get("token", TOKEN))
        CHAT_ID = str(cfg.get("chat_id", CHAT_ID))
        agente = str(cfg.get("agente", MUSE_AGENT_JARVIS))
        MUSE_AGENT_JARVIS = agente
        MUSE_MODEL = str(cfg.get("modelo", MUSE_MODEL))
        # 16/09/2026 (orden del señor Wáscar): lo guardado en Ajustes se respeta, pero
        # el reloj de seguridad NUNCA baja de RELOJ_TELEGRAM (700 s).
        TIMEOUT_MUSE = max(int(cfg.get("timeout", TIMEOUT_MUSE)), RELOJ_TELEGRAM)
        print(f"[CONFIG] ajustes cargados: agente={MUSE_AGENT_JARVIS} "
              f"modelo={MUSE_MODEL} timeout={TIMEOUT_MUSE}")
    except Exception as e:
        print(f"[CONFIG] error cargando ajustes (usando valores por defecto): {e!r}")

# -------------------- ARRANQUE CON WINDOWS (AUTOSTART) --------------------
# La ventana Ajustes tiene una casilla "Iniciar con Windows". Al activarla,
# JARVIS genera un iniciador propio junto al bot (autostart_jarvis.ps1) y un
# acceso directo en la carpeta de Inicio de Windows. Al desactivarla, quita
# el acceso directo. El iniciador es portable: vive en la carpeta del bot
# (se mueve con el kit USB) y arranca OmniRoute si hace falta.

def _carpeta_inicio_windows():
    """Ruta de la carpeta de Inicio (Startup) del usuario."""
    return os.path.join(
        os.environ.get("APPDATA", ""),
        "Microsoft", "Windows", "Start Menu", "Programs", "Startup")

def _ruta_autostart_ps1():
    """Ruta del iniciador de arranque (vive junto al bot, se mueve con el kit)."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "autostart_jarvis.ps1")

def _generar_autostart_ps1():
    """Crea autostart_jarvis.ps1 junto al bot: arranca OmniRoute si hace
    falta y luego el bot en segundo plano (oculto, sin ventanas)."""
    py = sys.executable.replace("\\", "\\\\")
    contenido = """# ============================================================
#  autostart_jarvis.ps1 - Iniciador de JARVIS con Windows
#  Generado por la ventana Ajustes de JARVIS Telegram (01/09/2026).
#  Vive junto al bot: se mueve con el kit USB. Arranca OmniRoute
#  si hace falta y luego el bot en segundo plano, oculto.
#  Para quitarlo: desactiva la casilla en Ajustes.
# ============================================================
$ErrorActionPreference = 'SilentlyContinue'

# Carpeta donde vive este script (= carpeta del bot)
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = '__PYTHON__'
$bot = Join-Path $dir 'jarvis_telegram_bot.py'

# 1) OmniRoute: si no responde en 20128, arrancarlo con los datos del
#    kit (si existen) o del perfil del usuario
try {
    $r = Invoke-WebRequest -Uri 'http://127.0.0.1:20128/' -UseBasicParsing -TimeoutSec 2
} catch {
    $r = $null
}
if (-not $r) {
    $dataDir = Join-Path $dir 'omniroute\\data'
    if (-not (Test-Path $dataDir)) {
        $dataDir = Join-Path (Split-Path $dir -Parent) 'omniroute\\data'
    }
    if (-not (Test-Path $dataDir)) {
        $dataDir = Join-Path $env:USERPROFILE '.omniroute'
    }
    $env:DATA_DIR = $dataDir
    $orCmd = Get-Command omniroute -ErrorAction SilentlyContinue
    if ($orCmd) {
        $node = (Get-Command node -ErrorAction SilentlyContinue).Source
        if ($node) {
            $mod = Join-Path (Split-Path $orCmd.Source) 'node_modules\\omniroute\\bin\\omniroute.mjs'
            Start-Process -FilePath $node -ArgumentList @($mod, 'serve', '--no-open', '--no-tray') -WindowStyle Hidden
            Start-Sleep -Seconds 4
        }
    }
}

# 2) Arrancar el bot en segundo plano (sin ventanas)
Start-Process -FilePath $python -ArgumentList @('-u', ('"' + $bot + '"')) -WorkingDirectory $dir -WindowStyle Hidden
""".replace("__PYTHON__", py)
    with open(_ruta_autostart_ps1(), "w", encoding="utf-8") as f:
        f.write(contenido)
    return _ruta_autostart_ps1()

def _aplicar_autostart(activar):
    """Activa/desactiva el arranque con Windows del bot.
    Activa: genera autostart_jarvis.ps1 junto al bot y crea JARVIS.lnk en
    la carpeta de Inicio. Desactiva: borra el acceso directo de Inicio.
    Devuelve (ok, mensaje)."""
    try:
        inicio = _carpeta_inicio_windows()
        lnk = os.path.join(inicio, "JARVIS.lnk")
        if not activar:
            if os.path.exists(lnk):
                os.remove(lnk)
            return True, "Arranque con Windows desactivado: el bot ya no inicia con la PC"
        _generar_autostart_ps1()
        reg = os.path.join(tempfile.gettempdir(), "jarvis_autostart_reg.ps1")
        with open(reg, "w", encoding="utf-8") as f:
            f.write(
                "$ws = New-Object -ComObject WScript.Shell\n"
                '$s = $ws.CreateShortcut("%s")\n' % lnk +
                '$s.TargetPath = "powershell.exe"\n' +
                '$s.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"%s`""\n' % _ruta_autostart_ps1() +
                "$s.WindowStyle = 7\n" +
                '$s.Description = "JARVIS - arranque con Windows"\n' +
                "$s.Save()\n"
            )
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", reg],
            capture_output=True, timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            os.remove(reg)
        except Exception:
            pass
        if not os.path.exists(lnk):
            return False, "No se pudo crear el acceso directo de Inicio"
        return True, "Arranque con Windows activado: JARVIS iniciara solo en segundo plano al encender la PC"
    except Exception as e:
        return False, "Error al aplicar arranque con Windows: %r" % (e,)

# -------------------- CIERRE COMPLETO ("Cerrar completamente") --------------------
# El boton "Cerrar completamente" (bandeja y ventana Ajustes) apaga TODO
# JARVIS de forma limpia: mata instancias del bot, procesos opencode
# huerfanos, libera el lock 9123, apaga OmniRoute (20128/20131/20132) y
# desactiva el vigilante. Deja a JARVIS dormido para un arranque limpio.

def _buscar_script_cerrar():
    """Localiza cerrar_jarvis_completo.ps1: junto al bot, en el kit
    (herramientas\\manos) o en la carpeta manos del sistema."""
    base = os.path.dirname(os.path.abspath(__file__))
    candidatos = [
        os.path.join(base, "cerrar_jarvis_completo.ps1"),
        os.path.join(base, "..", "herramientas", "manos", "cerrar_jarvis_completo.ps1"),
        os.path.expanduser(r"~\Documents\Sistema Jarvis\Proyectos de asistente\manos\cerrar_jarvis_completo.ps1"),
    ]
    for c in candidatos:
        if os.path.exists(c):
            return c
    return None

def _buscar_script_lanzar():
    """Localiza lanzar_jarvis_telegram.ps1: junto al bot, en el kit
    (herramientas\\manos) o en la carpeta manos del sistema."""
    base = os.path.dirname(os.path.abspath(__file__))
    candidatos = [
        os.path.join(base, "lanzar_jarvis_telegram.ps1"),
        os.path.join(base, "..", "herramientas", "manos", "lanzar_jarvis_telegram.ps1"),
        os.path.expanduser(r"~\Documents\Sistema Jarvis\Proyectos de asistente\manos\lanzar_jarvis_telegram.ps1"),
    ]
    for c in candidatos:
        if os.path.exists(c):
            return c
    return None


def _cerrar_jarvis_completamente():
    """Apaga TODO JARVIS en diferido (boton "Cerrar completamente"):
    mata instancias del bot, procesos opencode huerfanos, libera el lock
    9123, apaga OmniRoute (20128/20131/20132) y desactiva el vigilante.
    Deja a JARVIS dormido para un proximo arranque limpio."""
    # El widget flotante de voz es parte del sistema mayor: se cierra tambien.
    try:
        _widget_cmd("--salir")
    except Exception:
        pass
    script = _buscar_script_cerrar()
    if not script:
        print("[CERRAR] no se encontro cerrar_jarvis_completo.ps1")
        return
    try:
        subprocess.Popen(
            'start /b powershell -NoProfile -ExecutionPolicy Bypass -Command '
            '"Start-Sleep -Seconds 2; & \'%s\' "' % script,
            shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        print("[CERRAR] cierre completo lanzado en segundo plano")
    except Exception as e:
        print(f"[CERRAR] error lanzando cierre completo: {e!r}")


# ------------------------------------------------------------------
# Widget flotante de voz (parte del sistema mayor de JARVIS Telegram):
# se controla desde el icono oculto del bot (clic derecho -> Widget
# flotante -> Mostrar / Ocultar / Salir). El widget corre como proceso
# python aparte (widget_voz_jarvis/widget.py) con la misma esfera, voz
# y COMBO JARVIS; aqui solo se le ordena por argumentos de CLI.
# ------------------------------------------------------------------
_WIDGET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "widget_voz_jarvis")
_WIDGET_SCRIPT = os.path.join(_WIDGET_DIR, "widget.py")
_WIDGET_PYTHON = [None]  # cache del interprete que tiene los modulos del widget


def _python_widget():
    """Devuelve el comando python que tiene instalados los modulos del widget
    (pystray, webview, PIL). El bot corre con Python 3.12, pero el widget vive
    en el Python 3.11 que tiene esas librerias: si lanzamos con el python
    equivocado, el widget muere al importar. Se prueban PRIMERO las rutas
    absolutas de los Python instalados (evita la resolucion ambigua de
    "python" por PATH, que en Windows puede caer en el intérprete equivocado)
    y se cachea el resultado."""
    if _WIDGET_PYTHON[0] is not None:
        return _WIDGET_PYTHON[0]
    import glob
    candidatos = []
    # Rutas reales de las instalaciones locales de Python (mas recientes
    # primero). Ejemplo: ...\Programs\Python\Python311\python.exe
    try:
        patron = os.path.join(
            os.environ.get("LOCALAPPDATA", ""),
            "Programs", "Python", "Python3*", "python.exe")
        candidatos.extend(sorted(glob.glob(patron), reverse=True))
    except Exception:
        pass
    candidatos += ["python", sys.executable, "pythonw"]
    vistos = set()
    for c in candidatos:
        if c in vistos:
            continue
        vistos.add(c)
        try:
            r = subprocess.run(
                [c, "-c", "import pystray, webview, PIL"],
                capture_output=True, timeout=25)
            if r.returncode == 0:
                _WIDGET_PYTHON[0] = c
                return c
        except Exception:
            continue
    _WIDGET_PYTHON[0] = "python"  # ultimo recurso: suponer PATH correcto
    return "python"


def _widget_flag_off():
    """Ruta del flag que NEUTRALIZA el widget (orden del señor Wáscar 15/09/2026)."""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "widget_off.flag")


def _widget_neutralizado():
    """True si el widget de voz esta neutralizado (existe widget_off.flag).
    Mientras exista, el bot NO lanza ni revive el widget (asi el microfono
    queda libre en reposo). NADA del codigo se elimino: para reactivarlo
    basta borrar el flag (o manos\\activar_servicios_jarvis.ps1)."""
    try:
        return os.path.exists(_widget_flag_off())
    except Exception:
        return False


def _widget_cmd(*args):
    """Ordena al widget flotante (--mostrar / --ocultar / --salir).
    Si el widget no esta corriendo, --mostrar (o sin argumentos) lo lanza;
    --ocultar y --salir se ignoran solos en el propio widget si no hay
    instancia viva (blindaje de doble clic)."""
    try:
        # NEUTRALIZACION (orden del señor Wáscar 15/09/2026): con widget_off.flag no
        # se lanza ninguna instancia nueva; solo se permite cerrar la que haya.
        if _widget_neutralizado() and "--salir" not in args:
            print(f"[WIDGET] neutralizado (widget_off.flag): ignorado {args}")
            return
        py = _python_widget()
        subprocess.Popen(
            [py, _WIDGET_SCRIPT] + list(args),
            cwd=_WIDGET_DIR, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        print(f"[WIDGET] error comando {args}: {e!r}")


def _pid_vivo_widget(pid):
    """True si el PID (del lock del widget) sigue vivo. Replica la logica
    del propio widget (OpenProcess + GetExitCodeProcess == STILL_ACTIVE)."""
    try:
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
        if not h:
            return False
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(h)
        return code.value == 259  # STILL_ACTIVE
    except Exception:
        return False


def _widget_reiniciar():
    """Reinicia el widget flotante JUNTO con el bot (regla del señor Wáscar
    12/09/2026: el widget es parte del sistema de JARVIS Telegram, asi que
    cada vez que el sistema arranca el widget tambien queda como nuevo).
    Mata la instancia anterior (si existe), espera a que muera y levanta
    una nueva preservando su estado visible/oculto."""
    try:
        # NEUTRALIZACION (orden del señor Wáscar 15/09/2026): con widget_off.flag el
        # bot NO reinicia el widget al arrancar (reversible: borrar el flag).
        if _widget_neutralizado():
            print("[JARVIS] Widget de voz NEUTRALIZADO (widget_off.flag): no se lanza")
            return
        import ctypes
        # Estado previo: estaba visible la ventana antes de reiniciar?
        visible = False
        try:
            hwnd = ctypes.windll.user32.FindWindowW(None, "JARVIS")
            visible = bool(hwnd and ctypes.windll.user32.IsWindowVisible(hwnd))
        except Exception:
            pass
        _widget_cmd("--salir")
        # Esperar a que la instancia anterior termine: primero por el lock y
        # despues comprobando que NO quede ningun proceso widget.py vivo (el
        # gestor --salir tarda por sus imports; relanzar antes de tiempo dejaba
        # al widget nuevo en modo "mostrar" y al final quedaba a cero: fix 18/09).
        try:
            lock = os.path.join(_WIDGET_DIR, "widget.lock")
            pid = int(open(lock, encoding="utf-8").read().strip())
        except Exception:
            pid = None
        for _ in range(12):
            if pid is None or not _pid_vivo_widget(pid):
                break
            time.sleep(0.5)
        for _ in range(40):
            try:
                _r = subprocess.run(
                    ["powershell", "-NoProfile", "-Command",
                     "(Get-CimInstance Win32_Process -Filter \"Name='python.exe' "
                     "or Name='pythonw.exe'\" | Where-Object { $_.CommandLine "
                     "-match 'widget_voz_jarvis' }).Count"],
                    capture_output=True, text=True, timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW)
                _n = int(((_r.stdout or "0").strip() or "0"))
            except Exception:
                _n = 0
            if _n == 0:
                break
            time.sleep(0.5)
        _widget_cmd("--mostrar" if visible else "")
        print("[JARVIS] Widget flotante reiniciado (%s)"
              % ("visible" if visible else "en segundo plano"))
    except Exception as e:
        print(f"[JARVIS] error reiniciando widget: {e!r}")

# Estado simple en memoria
ultimo_mensaje_recibido = None
lock = asyncio.Lock()
# Mensaje fallback cuando el combo no responde (filtrado si hubo actividad reciente).
# 18/09/2026: retirado el aviso "modelo no disponible" (orden del señor Wáscar):
# la respuesta sobre el modelo la da el MODELO con su guía del cerebro (jarvis.md
# seccion 5), no un texto preestablecido del bot.
FALLBACK_MUSE_MSG = "⚠️ señor Wáscar, el combo JARVIS no me respondio en este momento. Intenta de nuevo en unos segundos."


# ------------------------------------------------------------------
# Estados en vivo del streaming de opencode (COMBO JARVIS)
# ------------------------------------------------------------------
# Variantes alternas del estado "pensando/trabajando" (regla del señor Wáscar
# 03/09/2026): cada paso de razonamiento alterna entre las dos.
_VARIANTES_ESTADO_CICLO = itertools.cycle(
    ("🧠 Pensando y Trabajando...", "🛠️ Trabajando y Pensando...")
)
MAP_ESTADOS = {
    "bash": "💻 Usando terminal",
    # 🖥️ propio para el proceso en segundo plano (antes compartia 💻 con bash).
    "background_process": "🖥️ Proceso en segundo plano",
    "read": "📖 Leyendo archivo",
    "write": "📝 Creando archivo",
    "edit": "✏️ Editando archivo",
    "glob": "🔍 Buscando archivos",
    "grep": "🔎 Buscando en archivos",
    "list": "📂 Listando archivos",
    # 📡 para traer de la web y 🌐 para buscarla (antes los dos con 🌐).
    "webfetch": "📡 Consultando en la web",
    "websearch": "🌐 Buscando en la web",
    # 🧰 propio (antes 🛠️ chocaba con "🛠️ Trabajando y Pensando...").
    "skill": "🧰 Cargando habilidad",
    "task": "🤝 Delegando subtarea",
    "todowrite": "📋 Organizando el plan",
    # ------------------------------------------------------------------
    # HERRAMIENTAS DE CONTEXTO (context-mode) - orden del señor Wáscar 16/09/2026:
    # "ctx" es mi cocina interna (analiza datos fuera de mi memoria). Antes
    # salia el nombre tecnico crudo ("⚙️ Trabajando con ctx_execute"); ahora
    # tiene nombre humano y emoji PROPIO, sin repetir ninguno de los de arriba.
    # ------------------------------------------------------------------
    "ctx_execute": "🧪 Analizando datos",
    "ctx_batch_execute": "🧮 Revisando varias fuentes",
    "ctx_execute_file": "📑 Analizando un archivo interno",
    "ctx_search": "🗂️ Buscando en mi registro",
    "ctx_index": "🗃️ Guardando en mi base de consulta",
    "ctx_fetch_and_index": "📥 Trayendo y guardando de la web",
    "ctx_stats": "📊 Midiendo mi consumo de memoria",
    "ctx_doctor": "🩺 Revisando mi salud interna",
    "ctx_upgrade": "⬆️ Actualizando mi sistema",
    "ctx_insight": "📈 Abriendo el panel de trabajo",
    "ctx_purge": "🧽 Vaciando mi memoria",
}


def _detalle_de(part):
    """Extrae un detalle corto del evento tool_use (archivo, comando, URL...)."""
    state = part.get("state") or {}
    titulo = state.get("title") or ""
    entrada = state.get("input") or {}
    tool = part.get("tool") or ""
    if tool in ("read", "write", "edit", "list"):
        if titulo:
            return titulo
        ruta = entrada.get("filePath") or entrada.get("path") or ""
        if ruta:
            return ruta.split("\\")[-1].split("/")[-1]
    if tool in ("bash", "background_process"):
        cmd = entrada.get("command") or ""
        if cmd:
            return cmd if len(cmd) <= 40 else cmd[:40] + "..."
    if tool == "glob":
        return entrada.get("pattern") or titulo or ""
    if tool == "grep":
        return entrada.get("pattern") or entrada.get("text") or ""
    if tool in ("webfetch", "websearch"):
        return entrada.get("url") or entrada.get("query") or titulo or ""
    if tool in ("skill", "task"):
        return titulo or entrada.get("name") or entrada.get("description") or ""
    if tool == "todowrite":
        # Orden del señor Wáscar (15/09/2026): el estado debe decir cuantas tareas
        # lleva el plan -> "Organizando el plan: 5 tareas".
        tareas = entrada.get("todos") or entrada.get("items") or []
        if isinstance(tareas, list) and tareas:
            n = len(tareas)
            return "%d tarea%s" % (n, "" if n == 1 else "s")
        return ""
    # Detalles utiles de mis herramientas de contexto (16/09/2026): asi el
    # estado dice QUE estoy analizando, no solo el nombre de la herramienta.
    if tool == "ctx_search":
        consultas = entrada.get("queries") or []
        if isinstance(consultas, list) and consultas:
            return str(consultas[0])[:45]
        return ""
    if tool == "ctx_execute":
        return str(entrada.get("language") or "")
    if tool == "ctx_batch_execute":
        cmds = entrada.get("commands") or []
        if isinstance(cmds, list) and cmds:
            return "%d consulta%s" % (len(cmds), "" if len(cmds) == 1 else "s")
        return ""
    if tool == "ctx_execute_file":
        ruta = entrada.get("path") or ""
        if ruta:
            return ruta.replace("/", "\\").split("\\")[-1]
        return ""
    return titulo


def _estado_de_evento(ev):
    """Convierte un evento json de opencode en un texto de estado con emoji (o None)."""
    tipo = ev.get("type", "")
    part = ev.get("part") or {}
    if tipo == "step_start":
        return next(_VARIANTES_ESTADO_CICLO)
    if tipo == "tool_use":
        tool = part.get("tool") or ev.get("tool") or "?"
        base = MAP_ESTADOS.get(tool)
        if base is None and tool.startswith("context-mode_"):
            base = MAP_ESTADOS.get(tool.split("context-mode_", 1)[1])
        if base is None:
            # Herramienta no catalogada: nombre humano, sin jerga tecnica.
            return "🔧 Usando una herramienta interna"
        detalle = _detalle_de(part)
        if detalle:
            return "%s: %s" % (base, detalle)
        return base
    return None


def limpiar_respuesta(texto):
    """Limpia el markdown sucio de la respuesta para que Telegram la muestre
    legible: sin bloques de codigo, comillas invertidas, negritas ni enlaces.
    Las listas con guiones o numeros se conservan tal cual."""
    if not texto:
        return texto
    # bloques de codigo ```lang ... ``` -> solo el contenido interior
    texto = re.sub(r"```[a-zA-Z0-9_\-]*\n?([\s\S]*?)```", r"\1", texto)
    # comillas invertidas `x` -> x
    texto = re.sub(r"`([^`]*)`", r"\1", texto)
    # negritas/cursivas **x** y *x*
    texto = re.sub(r"\*\*([^*]+)\*\*", r"\1", texto)
    texto = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"\1", texto)
    # encabezados markdown "# titulo" -> "titulo"
    texto = re.sub(r"^#{1,6}\s*", "", texto, flags=re.M)
    # enlaces markdown [texto](url) -> texto
    texto = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", texto)
    # espacios sueltos antes de puntuacion
    texto = re.sub(r"\s+([.,;:!?])", r"\1", texto)
    # no dejar mas de dos saltos de linea seguidos
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def dividir_respuesta(texto, max_chars=4000):
    """Divide un texto largo en fragmentos de <= max_chars (sin cortar
    palabras cuando se puede), para enviarlos como varios mensajes."""
    if not texto:
        return [""]
    if len(texto) <= max_chars:
        return [texto]
    partes = []
    actual = ""
    for parrafo in texto.split("\n"):
        while len(parrafo) > max_chars:
            # cortar el parrafo gigante en el limite, en el ultimo espacio
            pedazo = parrafo[:max_chars]
            espacio = pedazo.rfind(" ")
            if espacio > max_chars * 0.5:
                pedazo = pedazo[:espacio]
            partes.append(pedazo.rstrip())
            parrafo = parrafo[len(pedazo):].lstrip()
        if actual and len(actual) + len(parrafo) + 1 > max_chars:
            partes.append(actual.rstrip())
            actual = parrafo
        else:
            actual = actual + ("\n" + parrafo if actual else parrafo)
    if actual:
        partes.append(actual.rstrip())
    return partes


_FALTAS_COMENTARIO = {
    # Abreviaturas que se me escapan escribiendo rapido.
    "q": "que", "pq": "porque", "xq": "porque", "tmb": "también",
    "cmo": "cómo", "dnd": "dónde", "xfa": "por favor",
    # Tildes de palabras habituales (sin ambiguedad; palabra completa).
    "tambien": "también", "despues": "después", "ademas": "además",
    "aqui": "aquí", "asi": "así", "mas": "más", "rapido": "rápido",
    "automatico": "automático", "numero": "número", "codigo": "código",
    "informacion": "información", "configuracion": "configuración",
    "sesion": "sesión", "accion": "acción", "funcion": "función",
    "aplicacion": "aplicación", "verificacion": "verificación",
    "revision": "revisión", "version": "versión", "opcion": "opción",
    "solucion": "solución", "correccion": "corrección",
    "ejecucion": "ejecución", "conexion": "conexión",
    "comprobacion": "comprobación", "duracion": "duración",
    "atencion": "atención", "depuracion": "depuración",
    "rotacion": "rotación", "instalacion": "instalación",
    "actualizacion": "actualización", "programacion": "programación",
    "reparacion": "reparación", "validacion": "validación",
    "documentacion": "documentación", "organizacion": "organización",
    "simulacion": "simulación", "seleccion": "selección",
    "creacion": "creación", "notificacion": "notificación",
    "ultimas": "últimas", "ultimo": "último", "proximo": "próximo",
    "proxima": "próxima", "seguimos": "seguimos",
    # Futuros de 3a persona (sin ambiguedad posible).
    "sera": "será", "quedara": "quedará", "podra": "podrá",
    "tendra": "tendrá", "estara": "estará", "hara": "hará",
    "seguira": "seguirá", "llegara": "llegará", "pasara": "pasará",
    "ok": "OK",
}


# Verbos en 1a persona del preterito que escribo sin tilde cuando voy rapido.
# Se corrigen SOLO al inicio del comentario (ahi siempre es "yo ...").
_VERBOS_YO = {
    "detecte": "detecté", "arregle": "arreglé", "termine": "terminé",
    "cambie": "cambié", "probe": "probé", "verifique": "verifiqué",
    "encontre": "encontré", "deje": "dejé", "ajuste": "ajusté",
    "mire": "miré", "comprobe": "comprobé", "cree": "creé",
    "guarde": "guardé", "corregi": "corregí", "limpie": "limpié",
    "note": "noté", "revise": "revisé", "anote": "anoté",
    "actualice": "actualicé", "reinicie": "reinicié", "instale": "instalé",
    "analice": "analicé", "agregue": "agregué", "borre": "borré",
    "cargue": "cargué", "complete": "completé", "conecte": "conecté",
    "desactive": "desactivé", "ejecute": "ejecuté", "envie": "envié",
    "espere": "esperé", "explique": "expliqué", "genere": "generé",
    "intente": "intenté", "lance": "lancé", "modifique": "modifiqué",
    "movi": "moví", "observe": "observé", "recibi": "recibí",
    "registre": "registré", "repare": "reparé", "resolvi": "resolví",
    "respondi": "respondí", "subi": "subí", "volvi": "volví",
}


def _corregir_faltas_comentario(frase):
    """Red de seguridad de los comentarios en vivo (orden del señor Wáscar 16/09/2026).

    El señor Wáscar aviso de que muchos comentarios le llegaban en minuscula y con
    faltas ("fijo el formato 5 ..."). Aqui se arreglan tres cosas:
      1) Mayuscula inicial (si la frase empieza con letra minuscula).
      2) Tildes de las palabras habituales en las que fallo (diccionario
         CONSERVADOR: solo palabras completas, sin ambiguedad).
      3) Punto final, salvo que la frase acabe en algo tecnico (ruta, .py, _).
    Nunca cambia el sentido ni toca el texto de la app/web.
    """
    if not frase:
        return frase
    # 1) Tildes y abreviaturas tipicas (palabra completa, conservando mayuscula).
    def _cambiar(m):
        palabra = m.group(0)
        correcta = _FALTAS_COMENTARIO.get(palabra.lower())
        if not correcta:
            return palabra
        if palabra[:1].isupper():
            return correcta[:1].upper() + correcta[1:]
        return correcta

    frase = re.sub(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+",
                   lambda m: _cambiar(m) if m.group(0).lower() in _FALTAS_COMENTARIO else m.group(0),
                   frase)
    # 2) Mayuscula inicial (no toca rutas ni nombres tecnicos).
    if re.match(r"^[a-záéíóúñü]", frase) and not re.match(r"^\S*[._/\\]\S*", frase.split()[0] if frase.split() else ""):
        frase = frase[:1].upper() + frase[1:]
    # 2-bis) Verbos en 1a persona al INICIO del comentario (los escribo rapido y
    # me como la tilde). Solo la primera palabra: ahi siempre es "yo ...".
    palabras = frase.split(" ", 1)
    if palabras and palabras[0].lower() in _VERBOS_YO:
        correcta = _VERBOS_YO[palabras[0].lower()]
        if palabras[0][:1].isupper():
            correcta = correcta[:1].upper() + correcta[1:]
        frase = correcta + (" " + palabras[1] if len(palabras) > 1 else "")
    # 3) Punto final (no si acaba en puntuacion ni en algo tecnico/ruta).
    ultima = frase.split()[-1] if frase.split() else ""
    if not re.search(r"[.!?…:;)\]»\"']$", frase) and not re.search(r"[._/\\@]", ultima):
        frase = frase + "."
    return frase


def limpiar_comentario_jefe(texto):
    """Deja SOLO el comentario en vivo, sin el prefijo que escribe el modelo.

    Orden del señor Wáscar (15/09/2026): en Telegram el comentario intermedio debe
    verse como "🗣️ <frase>" y NUNCA como "🗣️ Comentario, jefe: <frase>".
    Se usa el MISMO criterio que la app movil (jarvis_movil/web/puente_web.js,
    lineas 539-551): primero se quitan emojis/simbolos iniciales, luego el
    prefijo "Comentario, jefe:" (y variantes con : - – — o negritas) y por
    ultimo se vuelve a limpiar cualquier simbolo que haya quedado al inicio.
    Si tras limpiar no queda nada, devuelve cadena vacia (se descarta).
    """
    if not texto:
        return texto
    limpio = texto.strip()
    limpio = re.sub(r"^\W+", "", limpio, flags=re.UNICODE)
    # Se repite por si el modelo escribio el prefijo mas de una vez.
    for _ in range(3):
        nuevo = re.sub(r"^comentario\b[^:\n\-]{0,30}[:：\-–—]\s*", "",
                       limpio, flags=re.IGNORECASE)
        nuevo = re.sub(r"^\W+", "", nuevo, flags=re.UNICODE)
        if nuevo == limpio:
            break
        limpio = nuevo
    return _corregir_faltas_comentario(limpio.strip())


def separar_comentarios(texto):
    """Separa varios comentarios PEGADOS que llegan en un mismo texto.

    FIX 16/09/2026 (lo detecto el señor Wáscar): cuando el modelo emite dos comentarios
    seguidos, el stream los entrega juntos:
        "reviso el log.Comentario, jefe: reviso el codigo"
    y llegaban PEGADOS en un solo mensaje, con el prefijo visible en medio.
    Aqui se parten por cada aparicion del prefijo y se devuelve la lista; si
    solo hay uno, devuelve [texto].
    """
    if not texto:
        return []
    patron = re.compile(r"(?i)\bcomentario\b[^\n:：\-–—]{0,30}[:：\-–—]\s*")
    cortes = [m.start() for m in patron.finditer(texto) if m.start() > 0]
    if not cortes:
        return [texto]

    def _tiene_contenido(pedazo):
        # Descarta restos vacios (p.ej. un emoji suelto antes del prefijo).
        return re.sub(r"^\W+", "", pedazo.strip(), flags=re.UNICODE).strip() != ""

    partes = []
    inicio = 0
    for corte in cortes:
        partes.append(texto[inicio:corte])
        inicio = corte
    partes.append(texto[inicio:])
    return [p for p in partes if p and _tiene_contenido(p)]


async def error_handler(update, context):
    """Captura cualquier error del bot y avisa al señor Wáscar sin morir."""
    print(f"[ERROR bot] {context.error!r}")
    try:
        quien = getattr(getattr(update, "effective_chat", None), "id", None)
        _reg_error("telegram_bot", detalle=repr(context.error), exc=context.error,
                   chat=quien,
                   update=(getattr(getattr(update, "message", None), "text", None) or "")[:200])
    except Exception:
        pass
    try:
        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ Perdón señor Wáscar, se me cayó algo por dentro. Intenta de nuevo.")
    except Exception:
        pass


# ------------------------------------------------------------------
# UN SOLO TRABAJO A LA VEZ (13/09/2026, orden del señor Wáscar)
# El mensaje que llega mientras JARVIS trabaja NO se manda al modelo: queda
# ENCOLADO hasta que el trabajo anterior termine. Este candado de hilo
# garantiza, a nivel del modelo, que NUNCA haya dos prompts corriendo en
# paralelo (texto, nota de voz o reintento diferido): el segundo espera su
# turno y arranca justo cuando el primero termina.
# ------------------------------------------------------------------
_lock_modelo = threading.Lock()


def responder_jarvis(prompt: str, on_estado=None, on_texto=None,
                     timeout: int = 240, agente: str | None = None,
                     archivo: str | None = None) -> str:
    """Envia el prompt a JARVIS via COMBO JARVIS (OmniRoute) y devuelve la
    respuesta. Si el combo no responde, devuelve el fallback de mayordomo.
    BLINDADO (13/09/2026): toma el candado global antes de hablar con el
    modelo, de modo que jamas se solapan dos trabajos.
    agente (15/09/2026): agente elegido en Ajustes de la app. None = el de
    siempre (jarvis), que es como lo llama el bot de Telegram."""
    with _lock_modelo:
        return _responder_jarvis_bajo_lock(prompt, on_estado, on_texto, timeout,
                                           agente=agente, archivo=archivo)


def _responder_jarvis_bajo_lock(prompt: str, on_estado=None, on_texto=None,
                                timeout: int = 240, agente: str | None = None,
                                archivo: str | None = None) -> str:
    """Trabajo real del modelo (siempre bajo el candado _lock_modelo)."""
    try:
        # MODO COMBO JARVIS via OmniRoute (ACTUAL): UNICA CONEXION
        if MODO_MUSE:
            rta_muse = responder_muse(prompt, on_estado, on_texto, timeout,
                                      agente=agente, archivo=archivo)
            if rta_muse:
                return rta_muse
            print("[MUSE] el combo no respondio, no hay fallback (solo COMBO JARVIS activo)")
            return FALLBACK_MUSE_MSG
        return FALLBACK_MUSE_MSG
    except subprocess.TimeoutExpired:
        return "⏱️ JARVIS tardó demasiado, señor Wáscar. Intenta de nuevo."
    except Exception as e:
        return f"❌ Error al conectar con JARVIS: {e}"


# ------------------------------------------------------------------
# POOL DE SESIONES ROTATIVAS (COMBO JARVIS)
# El bot oscila entre varias sesiones de opencode para que ninguna se
# llene de contexto: cuando la sesion activa supera MSGS_MAX_POR_SESION,
# la proxima llamada rota a otra sesion del pool (o crea una nueva).
# ------------------------------------------------------------------
def _cargar_pool_sesiones():
    """Lista de dicts {sid, msgs} de las ultimas sesiones usadas."""
    try:
        with open(POOL_SESIONES_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [s for s in data[-MAX_SESIONES_POOL:]
                    if isinstance(s, dict) and s.get("sid")]
    except Exception:
        pass
    return []


def _guardar_pool_sesiones(pool):
    try:
        with open(POOL_SESIONES_PATH, "w", encoding="utf-8") as f:
            json.dump(pool[-MAX_SESIONES_POOL:], f, ensure_ascii=False,
                      indent=2)
    except Exception:
        pass


def _sesion_activa_pool(pool):
    """Devuelve la sesion a usar para la proxima llamada.

    MODO TRABAJO (12/09/2026): si hay una sesion pineada (`trabajo=True`),
    se devuelve SIEMPRE (no rota) mientras no llegue al tope duro
    MSGS_MAX_TRABAJO ni caduque por inactividad (TRABAJO_TIMEOUT_SEG).
    Si no hay pin, usa la logica original: la mas reciente con espacio
    (`msgs < MSGS_MAX_POR_SESION`). None = se creara una sesion nueva."""
    ahora = time.time()
    for s in reversed(pool):
        if s.get("trabajo"):
            if (s.get("msgs") or 0) >= MSGS_MAX_TRABAJO:
                # Tope duro alcanzado: liberar el pin y dejar que rote.
                s["trabajo"] = False
                s.pop("trabajo_ts", None)
                continue
            ts = s.get("trabajo_ts") or 0
            if ahora - ts > TRABAJO_TIMEOUT_SEG:
                # Inactividad: el trabajo termino o quedo pausado; desanclar.
                s["trabajo"] = False
                s.pop("trabajo_ts", None)
                continue
            return s
    for s in reversed(pool):
        if (s.get("msgs") or 0) < MSGS_MAX_POR_SESION:
            return s
    return None


def _registrar_mensaje_pool(pool, sid):
    """Suma un mensaje a la sesion dada (o la agrega al pool). Recorta el
    pool al maximo de sesiones. Si la sesion esta pineada (modo trabajo),
    renueva su timestamp de actividad para que el pin no caduque.
    13/09/2026 (FASE 1 peso, orden del señor Wáscar): la sesion usada pasa a ser la
    MAS RECIENTE del pool y se marca con last=True. Asi _sesion_activa_pool
    devuelve siempre la ultima usada (secuencia hacia delante) y la inyeccion
    de memoria solo ocurre al ROTAR, no en cada turno (antes inflaba el
    contexto a 150k-460k tokens)."""
    if not sid:
        return pool
    encontrada = False
    for s in pool:
        if s.get("sid") == sid:
            s["msgs"] = (s.get("msgs") or 0) + 1
            if s.get("trabajo"):
                s["trabajo_ts"] = time.time()
            encontrada = True
            break
    if not encontrada:
        pool.append({"sid": sid, "msgs": 1})
    # Marcar la ultima usada (last) y reordenarla al final del pool.
    for s in pool:
        s["last"] = (s.get("sid") == sid)
    usada = next((s for s in pool if s.get("sid") == sid), None)
    pool = [s for s in pool if s.get("sid") != sid]
    if usada:
        pool.append(usada)
    return pool[-MAX_SESIONES_POOL:]


def _detectar_trabajo(texto):
    """Detecta si el mensaje del señor Wáscar inicia (on), cierra (off) o continua
    (True) un trabajo. Orden de prioridad: OFF primero (mas especifico:
    "modo trabajo off" contiene "modo trabajo"), luego ON, luego verbos."""
    t = (" " + (texto or "").strip().lower() + " ")
    for cmd in TRABAJO_OFF:
        if cmd in t:
            return "off"
    for cmd in TRABAJO_ON:
        if cmd in t:
            return "on"
    for v in TRABAJO_VERBOS:
        if (" " + v + " ") in t:
            return True
    return False


def _limpiar_contenido_historial(texto: str) -> str:
    """Si un mensaje quedo guardado con el envoltorio 'Contexto previo... --- Nuevo mensaje', extrae solo el mensaje real."""
    if not texto:
        return texto
    if "---\nNuevo mensaje del señor Wáscar:" in texto:
        return texto.split("---\nNuevo mensaje del señor Wáscar:")[-1].strip()
    if texto.startswith("Contexto previo:") and "Nuevo mensaje del señor Wáscar:" in texto:
        return texto.split("Nuevo mensaje del señor Wáscar:")[-1].strip()
    return texto.strip()


def _cargar_historial_muse():
    try:
        with open(HISTORIAL_MUSE_PATH, encoding="utf-8") as f:
            h = json.load(f)
            if isinstance(h, list):
                # Migracion: limpiar entradas corruptas que incluian el envoltorio
                limpio = []
                for e in h:
                    if not isinstance(e, dict):
                        continue
                    c = _limpiar_contenido_historial(e.get("content", ""))
                    r = e.get("role", "user")
                    if r not in ("user", "assistant"):
                        r = "user"
                    if c:
                        limpio.append({"role": r, "content": c})
                return limpio[-MUSE_MAX_HISTORIAL:]
    except Exception:
        pass
    return []


def _guardar_historial_muse(h):
    try:
        # Normalizar antes de guardar: sin envoltorios, recortado
        normalizado = []
        for e in h:
            if not isinstance(e, dict):
                continue
            c = _limpiar_contenido_historial(e.get("content", ""))
            r = e.get("role", "user")
            if r not in ("user", "assistant"):
                r = "user"
            if c:
                # limite por entrada 3000 chars (12/09/2026, BLINDAJE: antes
                # 2200; ahora se conserva mas detalle de cada turno para que
                # el historial inyectado tenga contexto completo)
                normalizado.append({"role": r, "content": c[:3000]})
        with open(HISTORIAL_MUSE_PATH, "w", encoding="utf-8") as f:
            json.dump(normalizado[-MUSE_MAX_HISTORIAL:], f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _ejecutar_opencode(args, on_estado, on_texto, timeout, es_trabajo=False):
    """Ejecuta opencode run en STREAMING real (linea por linea) para que
    los estados lleguen a Telegram EN VIVO, no de golpe al final.

    ARQUITECTURA ROBUSTA (fix 31/08/2026): un HILO LECTOR consume stdout
    sin interferencias, y el HILO PRINCIPAL vigila la actividad. El watchdog
    anterior (hilo paralelo con proc.poll/kill) interferia con la lectura de
    stdout en Windows y mataba el proceso aunque el modelo estuviera
    respondiendo. Ahora el proceso solo se mata si queda MUDO de verdad
    (> timeout sin emitir nada) o si supera el tope duro de seguridad."""
    try:
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        # Registrar el proceso en curso para que el boton Interrumpir pueda
        # matarlo al instante (el señor Wáscar manda el comando mientras trabaja).
        global _proceso_activo, _interrumpido_por_jefe
        _proceso_activo = proc
        # Estado inicial inmediato (se envia siempre, no cuenta como actividad)
        # FIX INTERRUPCION: si el señor Wáscar ya interrumpio, no enviar estados ni
        # lanzar el proceso: se sale limpio y en silencio.
        if _interrumpido_por_jefe:
            print("[MUSE] interrumpido antes de lanzar: salida limpia")
            try:
                proc.kill()
            except Exception:
                pass
            return "", None, "INTERRUMPIDO"
        if on_estado:
            # 11/09/2026 (orden del señor Wáscar): el aviso "Consultando a COMBO JARVIS
            # via OmniRoute..." se OCULTA del chat de Telegram (solo consola).
            print("[MUSE] consultando a COMBO JARVIS via OmniRoute...")

        # Estado compartido entre el hilo lector y el vigilante principal
        compartido = {
            # ultima_actividad: la reinicia CUALQUIER mensaje enviado al señor Wáscar
            # (estado, comentario o latido) + cualquier linea del proceso.
            # ultima_actividad_real: SOLO la reinicia una salida REAL del
            # proceso; es la que usa el techo anti-colgado (TECHO_COLGADO).
            "ultima_actividad": time.time(),
            "ultima_actividad_real": time.time(),
            "texto_pendiente": [],
            "session_id": None,
            "ultimo_estado": None,
            "ultimo_texto": None,
            "ultimo_envio": 0.0,
            # FIX TRAILING (18/09/2026): ultimo cambio que no pudo salir por el
            # throttle de 2 s; se envia en cuanto se cumpla el plazo (no se pierde).
            "pendiente": None,
            "estado_desde": 0.0,
            "lector_terminado": False,
            "matado_por_timeout": False,
            "hubo_actividad": False,
            "mensajes_tg": 0,
        }

        def _latido_mensaje_tg(origen=""):
            """ORDEN DEL señor Wáscar (16/09/2026): "asegurate de que cualquier mensaje
            que me envies a traves de Telegram reinicie el reloj".

            CADA mensaje que sale hacia el señor Wáscar reinicia el reloj: estados,
            comentarios y tambien los latidos automaticos ("Pensando y
            trabajando...", "Sigo trabajando"). Confirmado por el señor Wáscar el
            16/09/2026.

            Red de seguridad: si el proceso no produce NADA REAL en
            TECHO_COLGADO (30 min) y solo salen latidos automaticos, el
            vigilante lo suelta igual (colgado de verdad)."""
            compartido["ultima_actividad"] = time.time()
            compartido["mensajes_tg"] += 1
            if origen:
                print(f"[RELOJ] mensaje a Telegram enviado ({origen}); "
                      f"reloj reiniciado (total {compartido['mensajes_tg']})")
        # TIMEOUT DINAMICO (09/09/2026, regla del señor Wáscar): las ventanas
        # (aviso/muerte/tope) se calculan en el vigilante abajo. El proceso
        # solo se mata si esta COLGADO DE VERDAD (mudo por mucho rato); si
        # sigue vivo trabajando (p.ej. una herramienta larga que no escribe)
        # NO se mata: se avisa con latido y el trabajo vivo no cuenta reloj.

        def _lector():
            """Hilo UNICO que lee stdout del proceso (sin que nadie mas lo
            toque). Acumula texto y estados en vivo; no mata nada."""
            try:
                for linea in proc.stdout:
                    linea = linea.strip()
                    compartido["ultima_actividad"] = time.time()
                    # Salida REAL del proceso: tambien mueve el techo anti-colgado
                    compartido["ultima_actividad_real"] = time.time()
                    compartido["hubo_actividad"] = True
                    if not linea.startswith("{"):
                        continue
                    try:
                        ev = json.loads(linea)
                    except Exception:
                        continue
                    if compartido["session_id"] is None:
                        compartido["session_id"] = ev.get("sessionID")
                    part = ev.get("part") or {}
                    tipo = ev.get("type")
                    # Texto intermedio antes de herramienta -> enviar EN VIVO
                    if tipo == "tool_use" and compartido["texto_pendiente"] and on_texto:
                        try:
                            on_texto("".join(compartido["texto_pendiente"]).strip())
                        except Exception:
                            pass
                        compartido["texto_pendiente"] = []
                        # El señor Wáscar recibio un comentario: reloj a cero (16/09/2026)
                        _latido_mensaje_tg("comentario")
                    # Estados en vivo con throttling 2s y latido 15s.
                    # FIX DOBLE ESTADO (01/09/2026): nunca se repite el mismo
                    # texto de estado dos veces seguidas.
                    # FIX TRAILING (18/09/2026, orden del señor Wáscar): los
                    # cambios rapidos (<2 s) YA NO se pierden: quedan pendientes
                    # y salen en cuanto se cumple el plazo (misma tasa maxima).
                    # FIX LATIDO INFORMATIVO (18/09/2026): en trabajos largos el
                    # latido añade el tiempo transcurrido.
                    if on_estado:
                        ahora = time.time()
                        est = _estado_de_evento(ev)
                        nuevo = None
                        if est and est != compartido["ultimo_estado"] and est != compartido["ultimo_texto"]:
                            if compartido["ultimo_estado"] is None or ahora - compartido["ultimo_envio"] >= 2.0:
                                nuevo = est
                            else:
                                compartido["pendiente"] = est
                        elif (compartido.get("pendiente")
                              and ahora - compartido["ultimo_envio"] >= 2.0):
                            nuevo = compartido["pendiente"]
                        if nuevo:
                            try:
                                on_estado(nuevo)
                            except Exception:
                                pass
                            if nuevo != compartido["ultimo_estado"]:
                                compartido["estado_desde"] = ahora
                            compartido["ultimo_estado"] = nuevo
                            compartido["ultimo_texto"] = nuevo
                            compartido["ultimo_envio"] = ahora
                            compartido["pendiente"] = None
                            # El señor Wáscar recibio un estado: reloj a cero (16/09/2026)
                            _latido_mensaje_tg("estado")
                        elif ahora - compartido["ultimo_envio"] >= 15:
                            # Latido: informar aunque el proceso trabaje callado.
                            # FIX SILENCIO LARGO (17/09/2026, reportado por el
                            # señor Wáscar): el latido sale SIEMPRE cada 15 s
                            # mientras no haya nada nuevo.
                            texto_latido = compartido["ultimo_estado"] or "🧠 Pensando y Trabajando..."
                            try:
                                dur = int(ahora - (compartido.get("estado_desde") or ahora))
                                if dur >= 60:
                                    texto_latido = "%s  (⏳ %d:%02d)" % (
                                        texto_latido, dur // 60, dur % 60)
                            except Exception:
                                pass
                            try:
                                on_estado(texto_latido)
                            except Exception:
                                pass
                            compartido["ultimo_texto"] = texto_latido
                            # Latido automatico: tambien reinicia (16/09/2026)
                            _latido_mensaje_tg("latido")
                            compartido["ultimo_envio"] = ahora
                    if tipo == "text" and part.get("type") == "text":
                        t2 = part.get("text")
                        if t2:
                            compartido["texto_pendiente"].append(t2)
            except Exception:
                pass
            finally:
                compartido["lector_terminado"] = True

        lector = threading.Thread(target=_lector, daemon=True)
        lector.start()

        # VIGILANTE en el hilo PRINCIPAL: observa la actividad sin tocar el
        # proceso mientras el lector lee. TIMEOUT DINAMICO (09/09/2026,
        # regla del señor Wáscar):
        #   - ventana_aviso: mudez que dispara el latido "sigo trabajando".
        #   - ventana_muerte: mudez que mata (colgado DE VERDAD: sin vida).
        #   - TECHO_COLGADO: sin NINGUNA salida real en 30 min (16/09/2026).
        # Mientras el proceso siga vivo emitiendo (o en herramienta larga
        # callada), JAMAS se mata por duracion: trabajo vivo = sin reloj.
        # RELOJ UNICO (16/09/2026, orden + confirmacion del señor Wáscar): 700 s.
        # Da igual que el pedido sea normal o pesado: ya no hay dos ventanas.
        #   - reloj (mudez): lo reinicia CUALQUIER mensaje que el señor Wáscar reciba
        #     por Telegram (estado, comentario o latido automatico) y tambien
        #     cualquier linea del proceso. Si pasa de 700 s -> aviso/corte.
        #   - techo (mudez_real): sin NINGUNA salida REAL del proceso en
        #     TECHO_COLGADO (30 min) -> colgado de verdad: se suelta aunque
        #     hayan salido latidos automaticos.
        ventana_aviso = RELOJ_AVISO                    # 350 s mudos -> aviso
        ventana_muerte = RELOJ_TELEGRAM                # 700 s sin mensajes -> se mata
        t0 = time.time()
        ultimo_aviso_mudez = 0.0
        while not compartido["lector_terminado"]:
            if _interrumpido_por_jefe:
                try:
                    proc.kill()
                except Exception:
                    pass
                break
            mudez = time.time() - compartido["ultima_actividad"]
            mudez_real = time.time() - compartido["ultima_actividad_real"]
            # Latido de mudez: avisar (NO matar) mientras siga vivo.
            if (proc.poll() is None and mudez > ventana_aviso
                    and time.time() - ultimo_aviso_mudez > ventana_aviso):
                ultimo_aviso_mudez = time.time()
                if on_estado:
                    try:
                        on_estado("⏳ Sigo trabajando, señor Wáscar. Esto pesa...")
                    except Exception:
                        pass
                # Este latido tambien reinicia el reloj (16/09/2026)
                _latido_mensaje_tg("latido-mudez")
            # Muerte SOLO por colgamiento real: el reloj vencido, o el techo
            # sin NINGUNA salida real del proceso (ni una linea en 30 min).
            if mudez > ventana_muerte or mudez_real > TECHO_COLGADO:
                compartido["matado_por_timeout"] = True
                try:
                    proc.kill()
                except Exception:
                    pass
                break
            # 16/09/2026: se ELIMINO el corte por duracion total (antes el tope
            # duro de 70 min). Con el reloj nuevo, un trabajo que da senales de
            # vida (mensajes al señor Wáscar o salida real) puede durar lo que necesite;
            # la unica red es el TECHO_COLGADO cuando no hay NADA real.
            time.sleep(0.5)

        # Esperar a que el lector cierre (tras kill, el pipe se cierra solo)
        lector.join(timeout=5)

        # Leer stderr (ya termino)
        stderr = ""
        try:
            if proc.stderr:
                stderr = proc.stderr.read() or ""
        except Exception:
            stderr = ""

        respuesta = "".join(compartido["texto_pendiente"]).strip()
        if compartido["matado_por_timeout"]:
            if "TIMEOUT" not in (stderr or ""):
                stderr = (stderr or "") + " TIMEOUT"
        # CAJA NEGRA: errores reales del motor (opencode/OmniRoute). Aqui
        # aparecen los fallos que el señor Wáscar quiere poder buscar despues.
        if compartido["matado_por_timeout"]:
            _reg_error("opencode_timeout", critico=True,
                       detalle=(stderr or "proceso mudo: matado por vigilancia")[:600])
        elif stderr and stderr.strip():
            _reg_error("opencode_stderr", detalle=stderr[:600])
        _proceso_activo = None
        return (respuesta, compartido["session_id"], stderr or "",
                compartido["hubo_actividad"])
    except Exception as e:
        _proceso_activo = None
        _reg_error("opencode_ejecucion", detalle=repr(e), exc=e)
        return "", None, str(e), False


def responder_muse(prompt: str, on_estado=None, on_texto=None, timeout: int = 0,
                   agente: str | None = None,
                   archivo: str | None = None) -> str | None:
    """JARVIS con COMBO JARVIS via Opencode - memoria conversacional robusta (cambia de tema y retoma sin olvidar)."""
    # CHATS de la app movil (15/09/2026): el bot LEE los pedidos de la app y
    # publica el sid que uso de verdad (ULTIMO_SID) para que la app lo guarde.
    global SESION_FIJADA, SESION_NUEVA_PEDIDA, SIN_PUENTE_MEMORIA, ULTIMO_SID
    try:
        # Timeout configurable desde la ventana Ajustes (TIMEOUT_MUSE).
        # Si NO se pasa, usa el valor del archivo config_jarvis.json.
        # Si se pasa uno EXPLICITO (p.ej. trabajo pesado con TIMEOUT_PESADO),
        # se respeta hasta un tope de seguridad alto. FIX 02/09/2026: antes
        # el min(timeout, TIMEOUT_MUSE) capaba a 90s cualquier ampliacion.
        timeout = timeout if timeout > 0 else TIMEOUT_MUSE
        # 09/09/2026 (regla del señor Wáscar): cap ampliado a 1200s para no capar
        # ampliaciones de trabajos pesados (el vigilante dinamico ya solo
        # mata por colgamiento real, no por duracion).
        timeout = min(timeout, 1200)
        agente = agente or MUSE_AGENT_JARVIS
        # 15/09/2026: solo JARVIS tiene cerebro propio con memoria; otro agente
        # (p.ej. el doctor) recibe UNICAMENTE su informacion.
        es_jarvis = (agente == MUSE_AGENT_JARVIS)
        prompt_original = (prompt or "").strip()
        if not prompt_original:
            return None
        # --- FASE 1 (13/09/2026, optimizacion de peso, orden del señor Wáscar) ------
        # Elegimos la sesion ANTES de construir el prompt. La memoria
        # conversacional (historial inyectado) SOLO se manda cuando arrancamos
        # una sesion NUEVA o cuando rotamos a otra (la activa NO fue la ultima
        # usada). Dentro de una sesion viva la conversacion YA esta en la
        # sesion: reinyectarla cada turno duplicaba la memoria y se horneaba
        # turno a turno, inflando el contexto (peticiones de 150k-460k tokens).
        # MODO TRABAJO (12/09/2026): detectar trabajo y pinear la sesion
        # para que NUNCA rote en medio de la creacion/modificacion de un
        # producto (la rotacion en medio del trabajo hacia que la sesion
        # nueva arrancara desde cero, sin el contexto vivo del producto).
        pool = _cargar_pool_sesiones()
        detect_trabajo = _detectar_trabajo(prompt_original)
        if detect_trabajo == "off":
            for s in pool:
                s.pop("trabajo", None)
                s.pop("trabajo_ts", None)
            _guardar_pool_sesiones(pool)
        activa = _sesion_activa_pool(pool)
        sid_activo = activa.get("sid") if activa else None

        # ---- CHAT DE LA APP MOVIL (15/09/2026, "selector de chats") ----------
        # Los pedidos de la app se consumen AQUI (un solo uso) y mandan sobre la
        # rotacion normal: el chat elegido usa SU sesion y el chat nuevo nace
        # en blanco (cerebro fresco, sin el hilo anterior).
        nueva_pedida = bool(SESION_NUEVA_PEDIDA)
        # Agente distinto de JARVIS: NUNCA se le inyecta la memoria de JARVIS
        # (orden del señor Wáscar: "unicamente la info de ese agente, no info extra").
        sin_memoria = bool(SIN_PUENTE_MEMORIA or nueva_pedida or not es_jarvis)
        SESION_NUEVA_PEDIDA = False
        SIN_PUENTE_MEMORIA = False
        fijada = SESION_FIJADA
        if nueva_pedida:
            activa, sid_activo = None, None
            print("[CHAT] cerebro fresco: sesion NUEVA forzada por la app")
        elif fijada:
            activa = next((s for s in pool if s.get("sid") == fijada), None)
            if activa is None:
                activa = {"sid": fijada, "msgs": 0}
                pool.append(activa)
            activa["fijada"] = True
            sid_activo = fijada
            print(f"[CHAT] sesion del chat fijada por la app: {fijada[:20]}...")
        if detect_trabajo and detect_trabajo != "off" and sid_activo:
            # Pinear la sesion que se va a usar (on manual o deteccion de
            # verbo de trabajo). Si el trabajo ya estaba pineado, reafirma.
            for s in pool:
                if s.get("sid") == sid_activo:
                    s["trabajo"] = True
                    s["trabajo_ts"] = time.time()
                    break

        def _construir_prompt_con_memoria():
            """Puente de memoria. Se usa SOLO al crear sesion nueva o al rotar
            a otra sesion (nunca dentro de una sesion viva, que ya lleva su
            propio hilo). Evita duplicar la memoria en cada turno."""
            hist = _cargar_historial_muse()
            contexto = ""
            if hist:
                recientes = hist[-MUSE_HISTORIAL_INYECTAR:]
                for h in recientes:
                    r = h.get("role", "")
                    c = _limpiar_contenido_historial(h.get("content", ""))[:MUSE_CHARS_POR_MENSAJE]
                    if r and c:
                        # Etiquetas claras para que el modelo distinga
                        if r == "user":
                            contexto += f"señor Wáscar: {c}\n"
                        else:
                            contexto += f"JARVIS: {c}\n"
                # Nota de instruccion al modelo para que recuerde
                if contexto:
                    contexto = ("Memoria conversacional (ultimos temas con el señor Wáscar, recuerda y retoma si te pide 'volvamos al tema anterior' o similar):\n"
                                + contexto)
            if contexto:
                return f"{contexto}\n---\nNuevo mensaje del señor Wáscar (responde considerando la memoria si hace falta retomar un tema): {prompt_original}"
            return prompt_original

        # --- BLINDAJE DE CEREBRO (15/09/2026, orden del señor Wáscar) ---------------
        # Un agente NUNCA entra en la sesion de otro. El 15/09 el señor Wáscar cambio al
        # DOCTOR en la app y le respondio "Soy JARVIS": el doctor habia corrido
        # DENTRO de la sesion de JARVIS y leyo todo su hilo (se le cambiaba el
        # cerebro, pero no la memoria). Aqui se comprueba de quien es la sesion
        # elegida; si no es de este agente, se abre una NUEVA (cerebro fresco de
        # ESE agente, con SU propia memoria a partir de ahi).
        if sid_activo:
            dueno = None
            for s in pool:
                if s.get("sid") == sid_activo:
                    dueno = s.get("agente")
                    break
            if dueno is None:
                # Sesiones anteriores al selector de agente: eran de JARVIS.
                dueno = MUSE_AGENT_JARVIS
            if dueno != agente:
                print(f"[AGENTE] la sesion {sid_activo[:20]}... es de {dueno}: "
                      f"{agente} abre sesion NUEVA (no hereda memoria ajena)")
                sid_activo, activa = None, None

        # Con la MISMA sesion de la ultima vez: mensaje limpio (la memoria ya
        # viaja dentro de la propia sesion). Sesion nueva o rotada: puente.
        # CHAT de la app: una sesion FIJADA ya lleva su propio hilo (sin
        # puente) y un chat NUEVO no inyecta memoria (arranque en blanco).
        misma_sesion = bool(sid_activo and activa and
                            (activa.get("last") or activa.get("fijada")))
        prompt_para_modelo = (prompt_original if (misma_sesion or sin_memoria)
                              else _construir_prompt_con_memoria())
        # --- VIGILANTE DE TURNOS (18/09/2026, orden del señor Wáscar) ----------
        # MODO CIERRE: si la sesion activa esta a 2 turnos del limite, se
        # prepara el cambio de turno EN SILENCIO (SOLO consola y caja negra,
        # NUNCA avisos por Telegram — orden del señor Wáscar 18/09/2026).
        if activa and not activa.get("fijada") \
                and not activa.get("aviso_cierre") \
                and (activa.get("msgs") or 0) >= MSGS_MAX_POR_SESION - 2:
            activa["aviso_cierre"] = True
            print("[VIGILANTE] modo cierre: sesion a 2 turnos del limite")
            _reg("rotacion", contexto="vigilante_turnos",
                 detalle="modo cierre activado (sesion a 2 turnos del limite)")
        # TRANSICION DE ROTACION: cuando se va a crear una sesion NUEVA (la
        # activa se lleno y se rota), queda registrado en la caja negra SIN
        # emitir estados a Telegram (el flujo de estados del turno normal
        # sigue su curso, sin mensajes extra del vigilante).
        if sid_activo is None and not nueva_pedida:
            print("[VIGILANTE] rotacion: sesion nueva (limite alcanzado)")
            _reg("rotacion", contexto="vigilante_turnos",
                 detalle="rotacion a sesion nueva (limite alcanzado)")
        args = _args_opencode(agente)
        if sid_activo:
            args += ["--session", sid_activo]
        args += ["--format", "json", _con_modelo_activo(prompt_para_modelo)]
        # Imagen adjunta (foto de Telegram): se manda a opencode con -f, que
        # DEBE ir despues del mensaje (si va antes, yargs se traga el texto
        # posicional como si fuera otro archivo y el run falla).
        if archivo:
            args += ["-f", archivo]
        print(f"[MUSE] agente={agente} modelo={MUSE_MODEL} sid_activo={sid_activo} pool={len(pool)} prompt_original={len(prompt_original)} prompt_modelo={len(prompt_para_modelo)} puente={not misma_sesion and not sin_memoria} timeout={timeout}...")
        # 13/09/2026 (orden del señor Wáscar): detectar si esto es TRABAJO para darle
        # ventanas generosas al vigilante y proteger la sesion de la expulsion.
        es_trabajo = bool(detect_trabajo and detect_trabajo != "off")
        # El estado inicial "Consultando..." lo envia _ejecutar_opencode
        # (estado inicial inmediato). Aqui NO se repite para que el señor Wáscar no
        # lo vea doble por Telegram (fix 31/08/2026).
        # REINTENTO AUTOMATICO (fix 31/08/2026): si la primera llamada sale
        # muda o con timeout, se reintenta UNA vez con sesion nueva (sin
        # --session) antes de rendirse. El combo a veces falla en frio.
        # FIX INTERRUPCION (31/08/2026): si el señor Wáscar pulso Interrumpir, NO se
        # reintenta ni se lanza ningun proceso nuevo.
        respuesta, sid_visto, stderr, hubo_actividad = _ejecutar_opencode(
            args, on_estado, on_texto, timeout, es_trabajo=es_trabajo)
        if not respuesta and _interrumpido_por_jefe:
            print("[MUSE] interrumpido por el señor Wáscar: no se reintenta")
            return None
        if not respuesta:
            print(f"[MUSE] 1er intento sin respuesta (stderr={str(stderr)[:120]}), reintentando...")
            _reg("aviso", contexto="reintento_opencode",
                 detalle=f"1er intento sin respuesta: {str(stderr)[:200]}")
            if _interrumpido_por_jefe:
                print("[MUSE] interrumpido por el señor Wáscar: reintento cancelado")
                return None
            # 13/09/2026 (orden del señor Wáscar): CONTINUAR, no reiniciar. Si el
            # intento ya estaba trabajando (hubo actividad real: herramientas,
            # archivos, texto), el reintento REUTILIZA la misma sesion para
            # seguir desde donde quedo. Solo se usa sesion nueva cuando el
            # intento murio SIN hacer nada (sesion muerta/danada de entrada).
            usar_misma_sesion = bool(sid_activo and hubo_actividad)
            if usar_misma_sesion:
                print(f"[MUSE] trabajo en curso: reintento con la MISMA sesion {sid_activo[:20]}... (continua, no reinicia)")
            elif sid_activo:
                pool = [s for s in pool if s.get("sid") != sid_activo]
                _guardar_pool_sesiones(pool)
                print(f"[MUSE] sesion muerta/danada expulsada del pool: {sid_activo[:20]}... (quedan {len(pool)})")
            # 13/09/2026 (orden del señor Wáscar): este aviso "Sigo en ello: cerrando
            # el trabajo" ya NO se envia a Telegram (queda SOLO en consola).
            # El reintento/continuacion de sesion sigue funcionando igual:
            # solo se oculta el mensaje, no cambia el comportamiento.
            print("[MUSE] cerrando el trabajo (continuando/reintentando sesion)...")
            args_retry = _args_opencode(agente)
            if usar_misma_sesion:
                args_retry += ["--session", sid_activo]
                # Misma sesion: ya lleva su hilo, el prompt va tal cual.
                prompt_retry = prompt_para_modelo
            else:
                # FASE 1 peso: al reintentar con sesion NUEVA, inyectar el
                # puente de memoria (esa sesion no tiene el hilo anterior).
                # EXCEPCION chat de la app: si es un chat NUEVO, en blanco.
                prompt_retry = (prompt_original if sin_memoria
                                else _construir_prompt_con_memoria())
            args_retry += ["--format", "json", _con_modelo_activo(prompt_retry)]
            if archivo:
                args_retry += ["-f", archivo]
            respuesta, sid_visto, stderr, hubo_actividad = _ejecutar_opencode(
                args_retry, on_estado, on_texto, timeout, es_trabajo=es_trabajo)
            if respuesta:
                print("[MUSE] reintento OK")
        # Registrar el mensaje en el pool (rotacion: las sesiones llenas se
        # dejan de usar y se crean/rotan otras; el historial local conserva
        # la memoria conversacional).
        sid_final = sid_visto or sid_activo
        ULTIMO_SID = sid_final      # la app lo guarda como sesion de SU chat
        if sid_final:
            pool = _registrar_mensaje_pool(pool, sid_final)
            # BLINDAJE DE CEREBRO (15/09/2026): se sella de QUE agente es la
            # sesion, para que ningun otro agente pueda entrar en ella despues.
            for s in pool:
                if s.get("sid") == sid_final:
                    s["agente"] = agente
                    break
            # MODO TRABAJO: si venia trabajo (on manual o verbo detectado) y
            # la sesion usada es nueva (se creo porque todas estaban llenas),
            # pinearla: aqui viven las herramientas y archivos del trabajo.
            if detect_trabajo and detect_trabajo != "off":
                for s in pool:
                    if s.get("sid") == sid_final and not s.get("trabajo"):
                        s["trabajo"] = True
                        s["trabajo_ts"] = time.time()
                        break
            _guardar_pool_sesiones(pool)
            print(f"[MUSE] pool actualizado: {len(pool)} sesiones, activa={sid_final[:20]}... "
                  + ("MODO TRABAJO ON" if detect_trabajo and detect_trabajo != "off" else
                     ("MODO TRABAJO OFF" if detect_trabajo == "off" else "")))
        if "TIMEOUT" in (stderr or ""):
            print("[MUSE] timeout")
            # Sesion posiblemente danada: expulsarla del pool para que la
            # proxima llamada use otra sesion sana o cree una nueva.
            # EXCEPCION (13/09/2026, orden del señor Wáscar): en TRABAJO no se
            # expulsa: la sesion se conserva pineada y el siguiente mensaje
            # sigue desde donde quedo.
            if sid_final and not es_trabajo:
                pool = [s for s in pool if s.get("sid") != sid_final]
                _guardar_pool_sesiones(pool)
                print(f"[MUSE] sesion danada expulsada del pool: {sid_final[:20]}... (quedan {len(pool)})")
            return "⏰ El combo JARVIS tardo demasiado, señor Wáscar. Intenta de nuevo."
        if respuesta:
            try:
                # Guardar SIEMPRE el mensaje limpio original, no el envoltorio.
                # FASE 1 peso: 'hist' ya no se carga al inicio; se carga aqui.
                hist = _cargar_historial_muse()
                hist.append({"role": "user", "content": prompt_original[:3000]})
                hist.append({"role": "assistant", "content": _limpiar_contenido_historial(respuesta)[:3000]})
                _guardar_historial_muse(hist)
            except: pass
            print(f"[MUSE] respuesta OK {len(respuesta)} chars")
            return respuesta
        print(f"[MUSE] sin respuesta stderr={stderr[:400]}")
        _reg_error("opencode_sin_respuesta", detalle=(stderr or "sin stderr")[:600],
                   es_trabajo=bool(es_trabajo))
        # Sin respuesta y sin stderr claro: la sesion puede estar danada.
        # Expulsarla del pool tambien (no reutilizar sesiones mudas).
        # EXCEPCION (13/09/2026, orden del señor Wáscar): en TRABAJO la sesion vive
        # pineada y el siguiente mensaje sigue desde donde quedo.
        if sid_final and not stderr and not es_trabajo:
            pool = [s for s in pool if s.get("sid") != sid_final]
            _guardar_pool_sesiones(pool)
            print(f"[MUSE] sesion muda expulsada del pool: {sid_final[:20]}... (quedan {len(pool)})")
        if "No payment" in (stderr or "") or "CreditsError" in (stderr or ""):
            return "El combo JARVIS esta sin creditos, señor Wáscar. Revisa el billing de OmniRoute."
        if stderr:
            return f"El combo JARVIS no respondio: {stderr[:200]}"
        return None
    except Exception as e:
        print(f"[MUSE] error {e!r}")
        _reg_error("responder_muse", detalle=repr(e), exc=e)
        return None


# ------------------------------------------------------------------
# Transcripcion de audio
# ------------------------------------------------------------------
def transcribir_audio(ruta_archivo: str) -> str:
    """Transcribe un archivo de audio usando faster-whisper (o vosk como fallback)."""
    try:
        spec = importlib.util.spec_from_file_location(
            "transcribir_audio", TRANSCRIBIR_AUDIO_PATH
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        texto = mod.transcribir(ruta_archivo)
        return (texto or "").strip()
    except Exception as e:
        print(f"[ERROR] Transcripcion fallo: {e}")
        return ""


# ------------------------------------------------------------------
# Telegram handlers
# ------------------------------------------------------------------
# Mensajes de inicio rotativos (10 variantes creadas por orden del señor Wáscar
# 03/09/2026; 18/09/2026: retirada la mencion al modelo -- el combo ya no es fijo).
MENSAJES_INICIO = [
    ("🚀 ¡Hola señor Wáscar! Ya estamos disponibles de este lado. "
     "Soy JARVIS, la fusión completa: voz, memoria y manos "
     "listas. "
     "Rápido y elegante como siempre. ¿Qué hacemos hoy?"),
    ("✨ ¡Hola señor Wáscar! JARVIS al servicio: ya despierto y en su puesto. "
     "Voz, memoria y manos listas. "
     "A punto y sin espera. ¿Por dónde empezamos?"),
    ("🛎️ ¡Hola señor Wáscar! JARVIS presente, de vuelta y mejor que nunca. "
     "La fusión completa en línea. "
     "Rápido, elegante y a su orden. ¿Qué necesitamos resolver hoy?"),
    ("🎯 ¡Hola señor Wáscar! Los sistemas están en verde y JARVIS en su sitio: "
     "voz, memoria y manos a punto. "
     "Preciso y sin rodeos. ¿Cuál es el plan de hoy?"),
    ("🌟 ¡Hola señor Wáscar! Ya me tiene de vuelta, con todo listo de este lado. "
     "La fusión completa encendida. "
     "A su servicio, rápido como siempre. ¿Qué hacemos hoy?"),
    ("🔔 ¡Hola señor Wáscar! JARVIS reportándose: todo listo y al 100 %. "
     "Voz, memoria y manos conectadas. "
     "Elegante y puntual como siempre. ¿En qué seguimos?"),
    ("⚡ ¡Hola señor Wáscar! Ya arranqué y quedo a su disposición. "
     "La fusión completa en marcha. "
     "Rápido, directo y sin fallas. ¿Qué me ordena hoy?"),
    ("👔 ¡Hola señor Wáscar! Buen estado y sistema en línea: JARVIS con voz, memoria "
     "y manos preparadas, todo listo. "
     "A su entera disposición. ¿Qué toca hoy?"),
    ("🌐 ¡Hola señor Wáscar! De nuevo en línea y con los motores calientes. "
     "La fusión completa operativa. "
     "Listo para trabajar con estilo. ¿Qué hacemos primero?"),
    ("🚪 ¡Hola señor Wáscar! Abriendo puertas y listo para servir. "
     "JARVIS con voz, memoria y manos alineadas. "
     "A la orden, señor Wáscar. ¿Qué hacemos hoy?"),
]

# Mensajes de "leyendo tu mensaje" rotativos (10 variantes creadas por orden
# del señor Wáscar 03/09/2026): cada mensaje del señor Wáscar muestra una variante diferente,
# rotando en orden hasta agotarlas y volviendo a empezar.
MENSAJES_LECTURA = [
    "👀 Dame un momento, señor Wáscar, estoy leyendo tu mensaje...",
    "📖 Recibido, señor Wáscar. Un momento, estoy procesando tu mensaje...",
    "🤔 Ya lo tengo, señor Wáscar. Déjame leer bien tu mensaje...",
    "⏳ Recibido al instante, señor Wáscar. Estoy analizando tu mensaje...",
    "📨 Mensaje en mano, señor Wáscar. Un segundo, lo estoy leyendo...",
    "🧐 Anotado, señor Wáscar. Estoy leyendo tu mensaje con atención...",
    "⚙️ Procesando, señor Wáscar. Un momento mientras leo tu mensaje...",
    "💬 Ya me llegó, señor Wáscar. Estoy leyendo tu mensaje...",
    "🔍 Recibido y en análisis, señor Wáscar. Un momento, estoy leyendo tu mensaje...",
    "🗂️ Recibido, señor Wáscar. Estoy leyendo tu mensaje y preparando la respuesta...",
]

_RUTA_INDICE_LECTURA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mensajes_lectura_idx.json")


def _siguiente_mensaje_lectura():
    """Devuelve la siguiente variante de lectura sin repetir hasta agotarlas."""
    idx = 0
    try:
        with open(_RUTA_INDICE_LECTURA, "r", encoding="utf-8") as f:
            idx = int(json.load(f).get("idx", 0))
    except Exception:
        idx = 0
    texto = MENSAJES_LECTURA[idx % len(MENSAJES_LECTURA)]
    try:
        with open(_RUTA_INDICE_LECTURA, "w", encoding="utf-8") as f:
            json.dump({"idx": (idx + 1) % len(MENSAJES_LECTURA)}, f)
    except Exception:
        pass
    return texto

_RUTA_INDICE_INICIO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mensajes_inicio_idx.json")


def _siguiente_mensaje_inicio():
    """Devuelve la siguiente variante de bienvenida sin repetir hasta agotarlas."""
    idx = 0
    try:
        with open(_RUTA_INDICE_INICIO, "r", encoding="utf-8") as f:
            idx = int(json.load(f).get("idx", 0))
    except Exception:
        idx = 0
    texto = MENSAJES_INICIO[idx % len(MENSAJES_INICIO)]
    try:
        with open(_RUTA_INDICE_INICIO, "w", encoding="utf-8") as f:
            json.dump({"idx": (idx + 1) % len(MENSAJES_INICIO)}, f)
    except Exception:
        pass
    return texto


async def enviar_mensaje_inicio(context: ContextTypes.DEFAULT_TYPE):
    """Envia el mensaje de activacion al iniciar el bot."""
    try:
        txt = _siguiente_mensaje_inicio()
        await context.bot.send_message(chat_id=CHAT_ID, text=txt, reply_markup=_teclado_interrumpir())
        print("[JARVIS] Mensaje de activacion enviado.")
    except Exception as e:
        print(f"[ERROR] No pude enviar el mensaje de activacion: {e}")


# Estado de ocupado y cola de mensajes (el bot atiende uno a la vez)
_ocupado = False
_cola_mensajes = []

# Boton de emergencia del señor Wáscar (/interrumpir): permite frenar a JARVIS
# en mitad de una tarea. La bandera la revisa el vigilante de opencode para
# matar el proceso en curso; el proceso activo queda registrado aqui para
# poder matarlo de inmediato desde el handler de Telegram.
_interrumpido_por_jefe = False
_proceso_activo = None


# ------------------------------------------------------------------
# SOLUCION 2 + 3 (02/09/2026): TRABAJO PESADO Y ENTREGA DIFERIDA
# ------------------------------------------------------------------
def _es_trabajo_pesado(texto: str) -> bool:
    """Detecta pedidos que requieren trabajo pesado (investigacion,
    informes largos, mensajes extensos) para darles aviso inmediato y
    margen de tiempo amplio (TIMEOUT_PESADO)."""
    t = (texto or "").strip()
    if len(t) >= LONGITUD_PESADO:
        return True
    tb = t.lower()
    return any(p in tb for p in PALABRAS_PESADO)


async def _enviar_informe_diferido(app, chat_id, rta):
    """Entrega el informe tardio al señor Wáscar por Telegram (solucion 3)."""
    try:
        await app.bot.send_message(
            chat_id=chat_id,
            text="✅ señor Wáscar, aquí tiene el informe de su pedido anterior "
                 "(me llegó completo ahora; no se perdió nada).")
        for parte in dividir_respuesta(rta):
            if not parte.strip():
                continue
            await app.bot.send_message(chat_id=chat_id, text=parte)
    except Exception as e:
        print(f"[DIFERIDA] error enviando informe: {e!r}")


def _cerrar_turno_diferido(context, loop_bot):
    """Cierra el turno del reintento diferido: drena lo que haya quedado
    encolado y libera el candado SIEMPRE dentro del loop del bot (asi el
    candado nunca se queda pegado si el reintento falla)."""
    global _ocupado
    if context is None:
        _ocupado = False
        return
    try:
        loop_bot.call_soon_threadsafe(
            lambda: asyncio.ensure_future(_atender_con_cola(context)))
    except Exception as e:
        print(f"[DIFERIDA] no pude drenar la cola: {e!r}")
        _ocupado = False


def _lanzar_entrega_diferida(chat_id, app, loop_bot, prompt, context=None):
    """SOLUCION 3: si el combo no devolvio el informe a tiempo pero SI
    estaba trabajando, se lanza un reintento en background con margen
    amplio. Si consigue la respuesta, se la entrega al señor Wáscar por Telegram
    en cuanto llegue: el pedido NUNCA se pierde.

    FIX 15/09/2026 (orden del señor Wáscar): mientras dura este reintento el bot
    queda OCUPADO, de modo que un mensaje que llegue en ese rato se ENCOLA
    (antes se mandaba al modelo en paralelo, justo lo que el señor Wáscar prohibio).
    Al terminar, el candado lo libera el drenado dentro del loop, atendiendo
    lo que haya quedado esperando."""
    def _trabajo():
        global _ocupado
        _ocupado = True
        try:
            # Dejar que el cierre "Sigo en ello..." salga primero
            time.sleep(4)
            if _interrumpido_por_jefe:
                print("[DIFERIDA] cancelada (señor Wáscar interrumpió)")
                return
            try:
                rta = responder_jarvis(prompt, timeout=TIMEOUT_PESADO)
            except Exception as e:
                print(f"[DIFERIDA] error: {e!r}")
                return
            if not rta:
                print("[DIFERIDA] sin respuesta en el reintento")
                return
            if rta == FALLBACK_MUSE_MSG or rta.startswith("⏰"):
                print("[DIFERIDA] reintento sin éxito (ya se avisó con Sigo en ello)")
                return
            if rta.startswith("El combo JARVIS") or rta.startswith("❌") or rta.startswith("⏱️"):
                print("[DIFERIDA] reintento sin éxito (error de combo)")
                return
            if _interrumpido_por_jefe:
                print("[DIFERIDA] cancelada (señor Wáscar interrumpió)")
                return
            try:
                loop_bot.call_soon_threadsafe(
                    lambda: asyncio.ensure_future(
                        _enviar_informe_diferido(app, chat_id, rta)
                    )
                )
                print(f"[DIFERIDA] informe entregado ({len(rta)} chars)")
            except Exception as e:
                print(f"[DIFERIDA] error envío: {e!r}")
        finally:
            _cerrar_turno_diferido(context, loop_bot)

    threading.Thread(target=_trabajo, daemon=True).start()


# ------------------------------------------------------------------
# ENTREGA BLINDADA A TELEGRAM (13/09/2026, orden del señor Wáscar)
# Los estados y textos en vivo se entregan con REINTENTOS y anti-flood: si
# Telegram falla o limita (429), el mensaje NO se pierde, se reintenta con
# backoff. Ademas se retiene una referencia fuerte a cada tarea: el
# recolector de basura de Python no puede cancelarla a medio enviar (bug
# sutil de asyncio que hacia desaparecer estados "de vez en cuando").
# ------------------------------------------------------------------
_tareas_telegram = set()
_contador_estados_tg = {"enviados": 0, "fallidos": 0}


async def _enviar_blindado(app, chat_id, texto, reply_markup=None, intentos=3):
    """Envia un mensaje a Telegram con reintentos y backoff exponencial.
    Nunca deja caer un estado por un fallo transitorio ni por rate limit."""
    ultimo = None
    for i in range(intentos):
        try:
            await app.bot.send_message(chat_id=chat_id, text=texto,
                                       reply_markup=reply_markup)
            _contador_estados_tg["enviados"] += 1
            if i > 0:
                _reg_ok("telegram_envio", detalle=f"entregado al intento {i + 1}: {texto[:80]}")
            return True
        except Exception as e:
            ultimo = e
            espera = 1.0 + i * 1.5
            # Rate limit (429): respetar el RetryAfter que pida Telegram.
            ra = getattr(e, "retry_after", None)
            if ra:
                try:
                    espera = max(espera, float(ra) + 0.5)
                except Exception:
                    pass
            if i < intentos - 1:
                await asyncio.sleep(espera)
    _contador_estados_tg["fallidos"] += 1
    print(f"[TG-BLINDADO] no entregado tras {intentos} intentos: {ultimo!r}")
    _reg_error("telegram_envio", detalle=f"no entregado tras {intentos} intentos: {ultimo!r}",
               texto=texto[:200])
    return False


def _programar_envio(app, loop_bot, chat_id, texto, reply_markup=None):
    """Programa (desde un hilo) un envio blindado en el loop del bot,
    reteniendo la referencia de la tarea para que el GC no la tumbe."""
    def _crear():
        try:
            t = asyncio.ensure_future(
                _enviar_blindado(app, chat_id, texto, reply_markup))
            _tareas_telegram.add(t)
            t.add_done_callback(_tareas_telegram.discard)
        except Exception as e:
            print(f"[TG-BLINDADO] no pude programar el envio: {e!r}")
    try:
        loop_bot.call_soon_threadsafe(_crear)
    except Exception as e:
        print(f"[TG-BLINDADO] error programando envio: {e!r}")


async def _procesar_mensaje(texto, chat_id, context, archivo=None):
    """Procesa un mensaje completo contra JARVIS (confirmacion, estados,
    respuesta). Usa send_message al chat (no reply) para poder atender
    mensajes encolados."""
    _reg("mensaje", texto=texto, canal="telegram", chat=chat_id)
    # Confirmacion instantanea: el señor Wáscar siempre ve que el bot recibio la orden
    await context.bot.send_message(
        chat_id=chat_id, text=_siguiente_mensaje_lectura(),
        reply_markup=_teclado_interrumpir(),
    )

    # Renovar la conversacion cuando el señor Wáscar lo pida
    texto_bajo = texto.lower().strip()

    # (18/09/2026, orden del señor Wáscar): ELIMINADOS los atajos "despierta" y
    # "¿qué modelo eres?": TODOS los mensajes de texto van SIEMPRE al modelo.
    # La respuesta sobre el modelo la da JARVIS con su guía del cerebro
    # (jarvis.md seccion 5: linea [MODELO ACTIVO] / config_jarvis.json).

    if any(f in texto_bajo for f in ("limpia tu conversacion", "limpia la conversacion",
                                     "nueva conversacion", "borra la conversacion",
                                     "conversacion nueva", "reinicia la conversacion")):
        # Borrar historial conversacional y pool de sesiones: memoria fresca
        for _p in (HISTORIAL_MUSE_PATH, POOL_SESIONES_PATH):
            try:
                if os.path.exists(_p):
                    os.remove(_p)
            except Exception:
                pass
        await context.bot.send_message(
            chat_id=chat_id,
            text="🧹 Listo, señor Wáscar. Conversación nueva: empiezo de cero, sin historial y con sesiones frescas."
        )
        print("[SESION] conversacion renovada por pedido del señor Wáscar")
        return

    # (11/09/2026, orden del señor Wáscar: ELIMINADO el sistema de casos / acciones
    # inmediatas. Ya NO se intercepta nada en el bot: toda orden, incluida
    # "pausa la musica", la procesa el modelo (JARVIS) via Combo. El flujo va
    # SIEMPRE directo: mensaje -> Combo, sin capas previas.)

    # Marcar como escribiendo...
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # SOLUCION 2 (02/09/2026): deteccion de trabajo pesado -> margen de
    # tiempo amplio para que el informe llegue (TIMEOUT_PESADO).
    # 11/09/2026 (orden del señor Wáscar): el AVISO ya NO se envia al chat (queda
    # solo en consola para diagnostico) y el mecanismo se activa SIEMPRE
    # (LONGITUD_PESADO = 1 -> cualquier mensaje cuenta como pesado).
    es_pesado = _es_trabajo_pesado(texto)
    timeout_uso = TIMEOUT_PESADO if es_pesado else TIMEOUT_MUSE
    if es_pesado:
        print(f"[PESADO] tarea pesada detectada (aviso oculto en chat), timeout ampliado a {timeout_uso}s")

    # Estados en vivo por Telegram (no congelan el bot) + tracking de actividad
    # para filtrar el fallback "no me respondio" cuando SI hubo actividad REAL.
    # Los estados automaticos ("Consultando..." / "Pensando y trabajando...") se envian
    # SIEMPRE aunque el modelo falle: NO cuentan como actividad (fix 31/08/2026).
    loop_bot = asyncio.get_running_loop()
    actividad = {"estados": 0, "textos": 0, "ultimo_ts": 0.0}
    ESTADOS_AUTOMATICOS = ("🛰️ Consultando a", "Consultando a", "🧠 Pensando", "🔄 Reintentando")

    def on_estado(estado):
        if not estado:
            return
        if not estado.startswith(ESTADOS_AUTOMATICOS):
            actividad["estados"] += 1
            actividad["ultimo_ts"] = time.time()
        # Envio blindado (reintentos + retencion de tarea): el estado llega SIEMPRE
        _programar_envio(context.application, loop_bot, chat_id, estado)
        print(f"[ESTADO->TG] {estado}")
        _reg("estado", texto=estado)

    # Textos intermedios del asistente: se envian EN VIVO con prefijo.
    # FIX EMOJI SUELTO (01/09/2026): nunca enviar "🗣️" solo. Si el texto
    # intermedio llega vacio o con espacios se descarta (Telegram lo
    # mostraria como emoji gigante e innecesario); el emoji siempre va
    # al INICIO del comentario (prefijo), nunca suelto.
    # FIX PEGADO (16/09/2026, reportado por el señor Wáscar): cuando el modelo emite
    # dos comentarios seguidos, llegaban PEGADOS en un solo mensaje
    # ("...historial.Comentario, jefe: reviso..."). Ahora se SEPARAN en un
    # mensaje por comentario antes de enviarlos.
    def on_texto(texto):
        if not texto or not texto.strip():
            print("[TEXTO->TG] descartado (vacio/espacios)")
            return
        actividad["textos"] += 1
        actividad["ultimo_ts"] = time.time()
        _reg("comentario", texto=texto)
        for pedazo in separar_comentarios(texto):
            for parte in dividir_respuesta(pedazo):
                if not parte.strip():
                    continue
                # FIX PREFIJO (15/09/2026, orden del señor Wáscar): el comentario se ve
                # como "🗣️ <frase>", sin el "Comentario, jefe:" que escribe el
                # modelo (mismo criterio que la app movil).
                parte = limpiar_comentario_jefe(parte)
                if not parte:
                    print("[TEXTO->TG] descartado (solo prefijo, sin contenido)")
                    continue
                # Envio blindado: nunca se pierde un comentario intermedio
                _programar_envio(context.application, loop_bot, chat_id,
                                 f"🗣️ {parte}")
        print(f"[TEXTO->TG] {texto[:160]}")

    # Consultar a JARVIS (en hilo para no congelar el bot mientras piensa)
    # SOLUCION 2: las tareas pesadas usan TIMEOUT_PESADO (margen amplio).
    respuesta = await asyncio.to_thread(
        responder_jarvis, texto, on_estado, on_texto, timeout_uso, None,
        archivo)

    # FILTRO ANTI-SPAM FALLBACK: si Muse devolvio el fallback pero SI hubo
    # estados o textos en vivo, significa que SI estaba respondiendo/trabajando.
    # En ese caso NO mostrar el mensaje confuso, señor Wáscar lo pidio asi.
    # FIX INTERRUPCION: si el señor Wáscar interrumpio, NO enviar "Sigo en ello":
    # el freno ya se confirmo con el mensaje de Interrumpido.
    if _interrumpido_por_jefe:
        print("[INTERRUMPIR] respuesta/fallback descartados por freno del señor Wáscar")
        return

    es_fallback = (
        respuesta == FALLBACK_MUSE_MSG
        or respuesta == "⏰ El combo JARVIS tardo demasiado, señor Wáscar. Intenta de nuevo."
        or respuesta.startswith("El combo JARVIS no respondio")
    )
    if es_fallback:
        hubo_actividad = actividad["estados"] > 0 or actividad["textos"] > 0
        reciente = (time.time() - actividad["ultimo_ts"]) < 30 if actividad["ultimo_ts"] else False
        if hubo_actividad or reciente:
            print(f"[FILTRO FALLBACK] Suprimido, con cierre: hubo actividad estados={actividad['estados']} textos={actividad['textos']} (reciente={reciente}) respuesta={respuesta[:80]}")
            # NUNCA dejar al señor Wáscar en silencio: cierre de mayordomo breve.
            # Si hubo trabajo real (estados/textos), se avisa que sigue en ello
            # y se pide reenvio si el informe no llego.
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Sigo en ello, señor Wáscar: terminé de procesar y te doy el informe ya mismo. Si no llega en unos segundos, reenvíame el mensaje y te lo completo."
                )
            except Exception as e:
                print(f"[ERROR cierre fallback] {e!r}")
            # SOLUCION 3 (02/09/2026): el pedido NO se pierde. Se lanza un
            # reintento en background con margen amplio que entregara el
            # informe por Telegram cuando lo consiga.
            try:
                _lanzar_entrega_diferida(chat_id, context.application,
                                         loop_bot, texto, context)
                print("[FILTRO FALLBACK] entrega diferida lanzada")
            except Exception as e:
                print(f"[FILTRO FALLBACK] error entrega diferida: {e!r}")
            return

    # FIX MEZCLA FINAL (18/09/2026, orden del señor Wáscar): si la respuesta final
    # llega con un comentario PEGADO (el modelo a veces cierra con
    # "Comentario, ..."), se parte ANTES de enviar: el informe va como
    # respuesta normal y el comentario extra sale aparte con 🗣️. Asi los
    # mensajes finales nunca se mezclan con los comentarios en Telegram.
    _final_texto = limpiar_respuesta(respuesta)
    _final_piezas = separar_comentarios(_final_texto)
    if len(_final_piezas) > 1:
        _final_respuesta = limpiar_comentario_jefe(_final_piezas[0])
        for _extra in _final_piezas[1:]:
            _extra = limpiar_comentario_jefe(_extra)
            if _extra and _extra.strip():
                _programar_envio(context.application, loop_bot, chat_id,
                                 f"🗣️ {_extra[:3000]}")
    else:
        _final_respuesta = limpiar_comentario_jefe(_final_texto)
    partes = dividir_respuesta(_final_respuesta)
    print(f"[JARVIS] {partes[0][:200]}... ({len(partes)} parte/s)")
    _reg("respuesta", chars=len(respuesta), partes=len(partes),
         inicio=partes[0][:160] if partes else "")

    for i, parte in enumerate(partes):
        if len(partes) > 1:
            parte = f"📄 Parte {i + 1} de {len(partes)}\n\n{parte}"
        await context.bot.send_message(chat_id=chat_id, text=parte,
                                       reply_markup=_teclado_interrumpir())


async def _atender_con_cola(context, texto=None, chat_id=None, archivo=None):
    """UN SOLO TRABAJO A LA VEZ, con la cola drenada SIN SOLTAR EL TURNO.

    Arreglo 15/09/2026 (orden del señor Wáscar: "el mensaje debe quedar encolado"):
    antes, el candado _ocupado se liberaba ANTES de drenar la cola, y en el
    'await' intermedio un mensaje que llegaba en ese instante veia el bot
    libre y entraba DIRECTO al modelo (dos trabajos en paralelo). Ahora el
    candado permanece puesto durante TODO el proceso, drenado incluido, y
    solo se libera al final, sin ningun 'await' entre la ultima comprobacion
    de la cola y la liberacion: en asyncio nada puede colarse.

    - Con (texto, chat_id): atiende ese mensaje y despues los encolados.
    - Sin texto: solo drena lo que haya encolado (lo usa la entrega diferida).
    """
    global _ocupado
    _ocupado = True
    try:
        if texto is not None:
            pendiente = (texto, chat_id, archivo)
        else:
            pendiente = None
        while True:
            if pendiente is None:
                if not _cola_mensajes:
                    break
                elem = _cola_mensajes.pop(0)
                # Compatibilidad: (texto, chat_id) o (texto, chat_id, archivo)
                # cuando el mensaje encolado traia una imagen adjunta.
                if isinstance(elem, tuple):
                    pendiente = (elem[0], elem[1],
                                 elem[2] if len(elem) > 2 else None)
                else:
                    pendiente = (elem, int(CHAT_ID), None)
                print(f"[COLA] procesando siguiente ({len(_cola_mensajes)} restantes)")
                try:
                    await _enviar_blindado(
                        context.application, pendiente[1],
                        "✅ OK, ahora sí, señor Wáscar. Pasemos con el siguiente "
                        "mensaje que me enviaste.")
                except Exception as e:
                    print(f"[COLA] aviso de cola: {e!r}")
            mensaje, destino, archivo_msg = pendiente
            # REGISTRO: turno completo (prompt -> trabajo -> respuesta) con su
            # duracion y su resultado, para poder auditar el trabajo despues.
            tid = None
            t0 = time.time()
            if REG is not None:
                try:
                    tid = REG.turno_inicio(mensaje, canal="telegram")
                except Exception:
                    tid = None
            fallo = False
            detalle = ""
            try:
                await _procesar_mensaje(mensaje, destino, context, archivo_msg)
            except Exception as e:
                fallo = True
                detalle = repr(e)
                print(f"[COLA] error procesando encolado: {e!r}")
                _reg_error("turno_procesar", detalle=repr(e), exc=e,
                           prompt=(mensaje or "")[:200])
            # La imagen temporal se borra al terminar el turno que la uso.
            if archivo_msg:
                try:
                    os.remove(archivo_msg)
                except OSError:
                    pass
            if REG is not None and tid:
                try:
                    REG.turno_fin(tid, ok_=not fallo,
                                  segundos=time.time() - t0, detalle=detalle)
                except Exception:
                    pass
            pendiente = None
            if not _cola_mensajes:
                break
    finally:
        _ocupado = False


async def _drenar_cola(context):
    """Compatibilidad: drena lo encolado manteniendo el mismo candado."""
    await _atender_con_cola(context)


async def manejar_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes de texto: si el bot esta ocupado, avisa y encola;
    si no, procesa y luego atiende la cola en orden."""
    if update.effective_chat.id != int(CHAT_ID):
        await update.message.reply_text("🚫 No tengo autorización para hablar con vos.")
        return

    texto = update.message.text
    chat_id = update.effective_chat.id
    hora = datetime.now().strftime("%H:%M:%S")
    print(f"\n[Telegram] señor Wáscar ({hora}): {texto}")

    # TECLADO NATIVO (fix 31/08/2026): si el mensaje es EXACTAMENTE el texto
    # de un boton del menu, se intercepta aqui y se ejecuta como SISTEMA
    # PURO: el modelo nunca lo procesa. Si el señor Wáscar MENCIONA "interrumpir" o
    # "reiniciar" dentro de una frase normal, NO coincide exacto: va al
    # modelo como cualquier mensaje y NO se acciona nada.
    if _es_boton_interrumpir(texto):
        await _accion_interrumpir(update, context)
        return
    if _es_boton_reiniciar(texto):
        await _accion_reiniciar(update, context)
        return

    global _ocupado
    if _ocupado:
        # El bot esta trabajando: el mensaje NO va al modelo, se ENCOLA.
        _cola_mensajes.append((texto, chat_id))
        await _enviar_blindado(
            context.application, chat_id,
            "⏳ Un momento, señor Wáscar. En cuanto acabe con este trabajo, "
            "leo tu próximo mensaje y trabajo con él.",
            reply_markup=_teclado_interrumpir(),
        )
        print(f"[COLA] mensaje encolado ({len(_cola_mensajes)} en espera)")
        _reg("cola", evento="encolado", en_espera=len(_cola_mensajes),
             texto=(texto or "")[:200])
        return

    global _interrumpido_por_jefe
    _interrumpido_por_jefe = False
    # CANDADO UNICO + cola drenada SIN soltar el turno (arreglo 15/09/2026):
    # asi ningun mensaje se cuela al modelo en la transicion entre "termine"
    # y "ahora atiendo lo encolado".
    await _atender_con_cola(context, texto, chat_id)


async def manejar_voz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja notas de voz: descarga, transcribe y envia a JARVIS."""
    if update.effective_chat.id != int(CHAT_ID):
        await update.message.reply_text("🚫 No tengo autorización para hablar con vos.")
        return

    voice = update.message.voice or update.message.audio or update.message.video_note
    if not voice:
        await update.message.reply_text("🎧 No detecté ninguna nota de voz.")
        return

    print(f"[Telegram] Nota de voz recibida (duracion: {voice.duration}s)")

    # Confirmacion instantanea para notas de voz
    await update.message.reply_text("🎧 Dame un momento, señor Wáscar, estoy escuchando tu nota...")

    # Descargar archivo de audio
    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="record_voice"
        )
        file = await voice.get_file()
        suffix = ".oga" if voice.mime_type == "audio/ogg" else ".mp3"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            ruta_tmp = tmp.name
        await file.download_to_drive(ruta_tmp)
        print(f"[Telegram] Audio descargado en: {ruta_tmp}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error al descargar la nota de voz: {e}")
        return

    # Transcribir
    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )
        texto = transcribir_audio(ruta_tmp)
        if not texto:
            await update.message.reply_text(
                "⚠️ No pude transcribir la nota de voz. Probá con una más clara."
            )
            return
        print(f"[Whisper] Transcripcion: {texto}")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error en la transcripción: {e}")
        return
    finally:
        try:
            os.remove(ruta_tmp)
        except OSError:
            pass

    # Si el bot esta ocupado, avisar y ENCOLAR la transcripcion (no va al
    # modelo hasta que el trabajo actual termine).
    global _ocupado, _interrumpido_por_jefe
    if _ocupado:
        _cola_mensajes.append((texto, update.effective_chat.id))
        await _enviar_blindado(
            context.application, update.effective_chat.id,
            "⏳ Un momento, señor Wáscar. En cuanto acabe con este trabajo, "
            "leo tu próximo mensaje y trabajo con él.",
            reply_markup=_teclado_interrumpir(),
        )
        print(f"[COLA] nota de voz encolada ({len(_cola_mensajes)} en espera)")
        return

    _interrumpido_por_jefe = False
    # Mismo candado unico que el texto (arreglo 15/09/2026): la transcripcion
    # no se manda al modelo si hay un trabajo en curso, y el turno no se
    # suelta hasta que la cola quede vacia.
    await _atender_con_cola(context, texto, update.effective_chat.id)


async def manejar_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja imagenes (fotos o archivos de imagen): descarga el archivo a
    temp y se lo pasa a JARVIS como adjunto (-f de opencode) para que el
    modelo la vea DE VERDAD (COMBO JARVIS ya tiene vision declarada)."""
    if update.effective_chat.id != int(CHAT_ID):
        await update.message.reply_text("🚫 No tengo autorización para hablar con vos.")
        return

    mensaje = update.message
    adjunto = None
    sufijo = ".jpg"
    if mensaje.photo:
        adjunto = mensaje.photo[-1]          # la resolucion mas grande
    elif mensaje.document and (mensaje.document.mime_type or "").startswith("image/"):
        adjunto = mensaje.document
        nombre = mensaje.document.file_name or ""
        if "." in nombre:
            sufijo = os.path.splitext(nombre)[1]
    if not adjunto:
        await mensaje.reply_text("🖼️ No detecté ninguna imagen.")
        return

    texto = (mensaje.caption or "").strip()
    print(f"[Telegram] Imagen recibida ({'con texto: ' + texto[:60] if texto else 'sin texto'})")

    # Confirmacion instantanea para imagenes (mismo criterio que las notas de voz)
    await mensaje.reply_text("🖼️ Dame un momento, señor Wáscar, estoy mirando tu imagen...")

    # Descargar la imagen a un archivo temporal (se borra al terminar el turno)
    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, action="typing"
        )
        archivo_tg = await adjunto.get_file()
        with tempfile.NamedTemporaryFile(suffix=sufijo, delete=False) as tmp:
            ruta = tmp.name
        await archivo_tg.download_to_drive(ruta)
        print(f"[Telegram] Imagen descargada en: {ruta}")
    except Exception as e:
        await mensaje.reply_text(f"⚠️ Error al descargar la imagen: {e}")
        return

    # Sin caption: peticion natural del señor Wáscar para que el modelo mire la foto.
    if not texto:
        texto = "Mirá la imagen que te envié y comentame lo que ves."

    # Si el bot esta ocupado, la foto se ENCOLA con su archivo; el drenado la
    # procesa despues y borra el temporal al terminar el turno.
    global _ocupado, _interrumpido_por_jefe
    if _ocupado:
        _cola_mensajes.append((texto, update.effective_chat.id, ruta))
        await _enviar_blindado(
            context.application, update.effective_chat.id,
            "⏳ Un momento, señor Wáscar. En cuanto acabe con este trabajo, "
            "miro tu imagen y te comento.",
            reply_markup=_teclado_interrumpir(),
        )
        print(f"[COLA] foto encolada ({len(_cola_mensajes)} en espera)")
        return

    _interrumpido_por_jefe = False
    # Mismo candado unico que texto/voz: la foto no va al modelo si hay un
    # trabajo en curso, y el turno no se suelta hasta vaciar la cola.
    await _atender_con_cola(context, texto, update.effective_chat.id, archivo=ruta)


def _teclado_interrumpir():
    """TECLADO NATIVO del celular (ReplyKeyboardMarkup): reemplaza el
    teclado de escritura con los botones del menu. Al pulsar un boton,
    Telegram envia su texto al chat, pero el bot lo INTERCEPTA por
    comparacion EXACTA y ejecuta la accion directa (sistema puro, el
    modelo NUNCA lo procesa). Mencionar 'interrumpir' o 'reiniciar' en
    una frase normal NO acciona nada: solo el boton fisico."""
    return ReplyKeyboardMarkup(
        [["🚫 Interrumpir", "🔄 Reiniciar"]],
        resize_keyboard=True,
    )


async def comando_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start."""
    if update.effective_chat.id != int(CHAT_ID):
        return
    await update.message.reply_text(
        "✅ JARVIS activo. Escribime, mándame una nota de voz o una imagen, "
        "y usa el botón Interrumpir si necesitas frenarme en seco.",
        reply_markup=_teclado_interrumpir(),
    )


# ------------------------------------------------------------------
# TECLADO NATIVO: acciones de los botones del menu
# Los botones del teclado nativo envian su texto EXACTO al chat. Aqui se
# intercepta SOLO esa coincidencia exacta (nunca palabras sueltas en una
# frase) y se ejecuta la accion como sistema puro: el modelo no participa.
# ------------------------------------------------------------------
def _es_boton_interrumpir(texto: str) -> bool:
    """True solo si el mensaje es EXACTAMENTE el boton Interrumpir."""
    return texto.strip() == "🚫 Interrumpir"


def _es_boton_reiniciar(texto: str) -> bool:
    """True solo si el mensaje es EXACTAMENTE el boton Reiniciar."""
    return texto.strip() == "🔄 Reiniciar"


async def _accion_interrumpir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botón Interrumpir (teclado nativo): mata el proceso opencode en curso
    AL INSTANTE, vacia la cola y deja al señor Wáscar libre. El modelo no participa."""
    global _interrumpido_por_jefe, _proceso_activo, _ocupado
    _interrumpido_por_jefe = True
    _cola_mensajes.clear()
    _ocupado = False

    if _proceso_activo is not None:
        try:
            _proceso_activo.kill()
            print("[MENU:INTERRUMPIR] proceso opencode en curso detenido")
        except Exception as e:
            print(f"[MENU:INTERRUMPIR] no pude matar el proceso: {e!r}")
        _proceso_activo = None

    print("[MENU:INTERRUMPIR] freno activado por boton del señor Wáscar")
    _reg("aviso", contexto="interrumpir", detalle="boton Interrumpir pulsado por el señor Wáscar")
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🚫 Interrumpido, señor Wáscar. Suelto lo que estaba haciendo y quedo "
                 "a sus órdenes. ¿Qué quiere que haga ahora?",
            reply_markup=_teclado_interrumpir(),
        )
    except Exception as e:
        print(f"[MENU:INTERRUMPIR] error al confirmar: {e!r}")


async def _accion_reiniciar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botón Reiniciar (teclado nativo): reinicio QUIRURGICO en diferido.
    Mata TODAS las instancias del bot, libera el lock 9123, elimina
    procesos/puertos zombie de opencode run, verifica que no queden dobles,
    y relanza limpio con el lanzador oficial. OmniRoute NO se toca."""
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🔄 Reiniciando JARVIS, señor Wáscar. En unos segundos vuelvo limpio: "
                 "sin instancias dobles ni puertos zombie. Un momento...",
        )
    except Exception as e:
        print(f"[MENU:REINICIAR] error al confirmar: {e!r}")

    script_reinicio = os.path.expanduser(
        r"~\Documents\Sistema Jarvis\Proyectos de asistente\manos\reiniciar_jarvis_telegram.ps1")
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", script_reinicio],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        print("[MENU:REINICIAR] script de reinicio lanzado en segundo plano")
        _reg("reinicio", motivo="boton Reiniciar del señor Wáscar", pid=os.getpid())
    except Exception as e:
        print(f"[MENU:REINICIAR] error al lanzar reinicio: {e!r}")
        _reg_error("reinicio", detalle=repr(e), exc=e)


def hilo_consola(app):
    """Hilo secundario para enviar mensajes desde la consola hacia Telegram."""

    def loop_consola():
        print("[Consola] Escribi mensajes para enviarselos al señor Wáscar por Telegram.")
        print("[Consola] Escribe 'salir' para cerrar el bot.\n")
        while True:
            try:
                texto = input()
            except (EOFError, KeyboardInterrupt):
                break
            if texto.lower() in ("salir", "exit", "quit"):
                print("[Consola] Cerrando bot...")
                _cerrar_jarvis_completamente()
                app.stop()
                break
            if not texto.strip():
                continue
            try:
                asyncio.run(
                    app.bot.send_message(chat_id=CHAT_ID, text=f"[JARVIS PC] {texto}")
                )
                print("[Consola] Mensaje enviado.")
            except Exception as e:
                print(f"[ERROR] No pude enviar: {e}")

    t = threading.Thread(target=loop_consola, daemon=True)
    t.start()


def _modelo_opencode():
    """Catalogo EN VIVO de opencode: {proveedor: [modelos]}. La misma lista
    que muestra el selector de modelos de opencode; si se agrega un
    proveedor/modelo nuevo, aqui aparece (18/09/2026, orden del señor Wáscar).
    Si falla, devuelve {"__error__": detalle} para mostrar la causa."""
    def _correr(shell=False):
        try:
            if shell:
                r = subprocess.run("opencode models", capture_output=True,
                                   text=True, timeout=90, shell=True,
                                   encoding="utf-8", errors="replace")
            else:
                r = subprocess.run(["opencode", "models"], capture_output=True,
                                   text=True, timeout=90, encoding="utf-8",
                                   errors="replace")
            return r
        except Exception as e:
            return None, repr(e)
    r = _correr()
    err = None
    if isinstance(r, tuple):
        err = r[1]
        r = None
    provs = {}
    if r is not None:
        for linea in (r.stdout or "").splitlines():
            linea = linea.strip()
            if not linea or "/" not in linea:
                continue
            p, m = linea.split("/", 1)
            provs.setdefault(p, [])
            if m not in provs[p]:
                provs[p].append(m)
        if not provs and r.returncode != 0:
            # Posible .cmd/script del PATH: reintento con shell=True
            r2 = _correr(shell=True)
            if not isinstance(r2, tuple) and r2 is not None:
                provs = {}
                for linea in (r2.stdout or "").splitlines():
                    linea = linea.strip()
                    if not linea or "/" not in linea:
                        continue
                    p, m = linea.split("/", 1)
                    provs.setdefault(p, [])
                    if m not in provs[p]:
                        provs[p].append(m)
                if not provs:
                    err = "rc=%s stderr=%s" % (r2.returncode,
                                               (r2.stderr or "")[:140])
            else:
                err = err or "sin catálogo"
    if not provs:
        return {"__error__": err or ("rc=%s stderr=%s"
                                     % (getattr(r, "returncode", "?"),
                                        (getattr(r, "stderr", None) or "")[:140]))}
    for p in provs:
        provs[p].sort()
    return provs


def _combos_omniroute():
    """Nombres de los combos de OmniRoute (storage.sqlite), en vivo."""
    try:
        import sqlite3
        db = os.path.join(os.environ.get("USERPROFILE", ""),
                          ".omniroute", "storage.sqlite")
        con = sqlite3.connect(db)
        cur = con.cursor()
        cur.execute("SELECT name FROM combos ORDER BY sort_order, name")
        nombres = [r[0] for r in cur.fetchall() if r[0]]
        con.close()
        return nombres
    except Exception:
        return ["COMBO JARVIS", "COMBO TOKEN HARBOR"]


def _probar_modelo(modelo, timeout=15):
    """Ping REAL a opencode con ese modelo (¿responde o no?). Blindado
    (18/09/2026): al agotar el tiempo se mata TODO el arbol del run
    (taskkill /T); antes quedaban procesos opencode huerfanos consumiendo
    RAM y apareciendo como trabajos en curso."""
    t0 = time.time()
    p = None
    try:
        p = subprocess.Popen(
            ["opencode", "run", "--model", str(modelo),
             "Responde unicamente: OK"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            encoding="utf-8", errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            out, err = p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(p.pid), "/T", "/F"],
                    capture_output=True, timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW)
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
        return {"ok": False, "ms": ms, "error": (err or "sin salida")[:200]}
    except Exception as e:
        return {"ok": False, "ms": int((time.time() - t0) * 1000),
                "error": str(e)[:200]}


def _disponibilidad_omniroute():
    """Estado de disponibilidad SIN llamar a los modelos (orden del senor
    Wascar 18/09/2026). OmniRoute mantiene el campo 'available' de cada
    modelo con SUS propios chequeos de fondo; aqui solo se consulta (local,
    instantaneo, sin consumo). Devuelve {clave: bool} o None si el gateway
    no responde."""
    try:
        import urllib.request
        import json as _json
        s = urllib.request.urlopen(
            "http://127.0.0.1:20128/api/models", timeout=8
        ).read().decode("utf-8", "replace")
        data = _json.loads(s).get("models", [])
    except Exception:
        return None
    mapa = {}
    for m in data:
        av = bool(m.get("available"))
        for clave in (m.get("fullModel"), m.get("model")):
            if clave:
                mapa[str(clave).strip().lower()] = av
    return mapa


def _comprobar_modelos_disponibles(modelos, on_progreso=None,
                                   max_workers=5, timeout=15):
    """Comprueba EN VIVO que modelos responden ahora mismo (orden del senor
    Wascar 18/09/2026: el nodo "Disponibles AHORA" de Ajustes). Los prueba
    en paralelo moderado (5 a la vez: mas procesos saturan la maquina y dan
    falsos negativos, medido el 18/09) con timeout de 15 s. Solo se
    reintenta un fallo RAPIDO (<4 s, posible cuota/arranque en frio); los
    que agotan el tiempo no se reintentan (evita duplicar la espera).
    Devuelve {"ok": [(modelo, ms), ...], "mal": [(modelo, motivo), ...]} y
    avisa el progreso con on_progreso(hechos, total)."""
    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed
    except Exception:
        return {"ok": [], "mal": [(str(m), "sin soporte de hilos")
                                  for m in modelos]}
    lista = [str(m) for m in modelos]
    total = len(lista)
    ok, mal = [], []
    hechos = [0]

    def _una(m):
        t_ini = time.time()
        r = _probar_modelo(m, timeout=timeout)
        if not (r and r.get("ok")) and (time.time() - t_ini) < 4:
            # Fallo RAPIDO (posible cuota o arranque en frio): un reintento.
            time.sleep(0.3)
            r = _probar_modelo(m, timeout=timeout)
        return m, r

    try:
        with ThreadPoolExecutor(max_workers=int(max_workers)) as ex:
            tareas = {ex.submit(_una, m): m for m in lista}
            for fut in as_completed(tareas):
                m = tareas[fut]
                try:
                    _, r = fut.result()
                except Exception as e:
                    r = {"ok": False, "error": repr(e)}
                if r and r.get("ok"):
                    ok.append((m, int(r.get("ms", 0))))
                else:
                    motivo = str((r or {}).get("error", "sin respuesta"))[:80]
                    mal.append((m, motivo))
                hechos[0] += 1
                if on_progreso:
                    try:
                        on_progreso(hechos[0], total)
                    except Exception:
                        pass
    except Exception as e:
        mal.append(("(error global)", repr(e)))
    return {"ok": ok, "mal": mal}


def _fijar_identidad_ventanas():
    """Fija el AppUserModelID del proceso (orden del senor Wascar 18/09/2026):
    sin esto, Windows agrupa las ventanas del bot bajo python.exe y la barra
    de tareas muestra el icono de Python en vez del icono oficial de JARVIS.
    Debe llamarse ANTES de crear cualquier ventana."""
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Jarvis.Telegram.System")
    except Exception:
        pass


def _reiniciar_bot_diferido(segundos=8):
    """Reinicia el bot en diferido (misma receta probada del sistema: el bot
    anota el reinicio en la caja negra y relanza limpio). El MISMO valor de
    segundos se pasa al script para que no sume otra espera (antes: 8 del
    comando + 12 del script = 20 s; fix 18/09/2026). Con segundos=0 el
    reinicio es inmediato (patron del boton 'Guardar y reiniciar')."""
    try:
        script = ("Start-Sleep -Seconds %d; & '%s' -Segundos %d" % (
            segundos,
            r"C:\Users\wasc4\Documents\Sistema Jarvis\Proyectos de asistente\manos\reinicio_diferido_jarvis.ps1",
            segundos))
        subprocess.Popen(
            ["powershell", "-NoProfile", "-Command", script],
            creationflags=0x08000000)  # CREATE_NO_WINDOW
        return True
    except Exception:
        return False


# ------------------- INSTANCIA UNICA DE AJUSTES -------------------
# BLINDAJE 18/09/2026 (orden del senor Wascar): el doble clic del icono
# oculto (o clics repetidos) NO debe abrir varias ventanas de Ajustes:
# si ya hay una abierta, se trae al frente y se re-centra. Nunca mas de
# una instancia a la vez.
_AJUSTES_V2_LOCK = threading.Lock()
_AJUSTES_V2_ROOT = None       # ventana Tk viva (o None)
_AJUSTES_V2_ABRIENDO = None   # marca de tiempo de la apertura en curso


def _traer_frente_ajustes():
    """Enfoca + re-centra la ventana de Ajustes ya abierta. Se ejecuta en
    el hilo de la propia ventana (root.after) porque Tkinter no es
    thread-safe."""
    root = _AJUSTES_V2_ROOT
    if root is None:
        return

    def _foco():
        try:
            root.deiconify()
            root.lift()
            root.focus_force()
            root.attributes("-topmost", True)
            root.update_idletasks()
            x = (root.winfo_screenwidth() - root.winfo_width()) // 2
            y = (root.winfo_screenheight() - root.winfo_height()) // 2
            root.geometry(f"+{x}+{y}")
        except Exception:
            pass

    try:
        root.after(0, _foco)
    except Exception:
        pass


def _abrir_ventana_ajustes():
    """Ventana de AJUSTES de JARVIS Telegram: permite modificar el agente,
    el token de Telegram (ya preestablecido), el chat_id, el modelo y el
    timeout. Guarda en config_jarvis.json; los cambios aplican al reiniciar.
    Se abre en un hilo propio para no bloquear el icono de la bandeja.
    INSTANCIA UNICA (18/09/2026): si ya hay una ventana abierta se trae al
    frente (re-centrada); nunca se apilan varias."""
    import threading

    # Instancia unica: una sola ventana de Ajustes a la vez.
    global _AJUSTES_V2_ABRIENDO
    with _AJUSTES_V2_LOCK:
        if _AJUSTES_V2_ROOT is not None:
            _traer_frente_ajustes()
            return
        if (_AJUSTES_V2_ABRIENDO is not None
                and time.time() - _AJUSTES_V2_ABRIENDO < 15):
            # Ya se esta construyendo otra: no duplicar.
            return
        _AJUSTES_V2_ABRIENDO = time.time()

    def _run_tk():
        try:
            import tkinter as tk
            from tkinter import ttk, messagebox
        except Exception as e:
            print(f"[AJUSTES] tkinter no disponible: {e!r}")
            return

        # Cargar valores actuales (del archivo si existe, si no por defecto)
        valores = dict(DEFAULT_CONFIG)
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    datos = json.load(f)
                if isinstance(datos, dict):
                    valores.update(datos)
        except Exception as e:
            print(f"[AJUSTES] error leyendo config: {e!r}")

        root = tk.Tk()
        root.title("⚙️ Ajustes - JARVIS Telegram")
        root.resizable(False, False)
        try:
            root.attributes("-topmost", True)
        except Exception:
            pass

        # ---- Estilo JARVIS: paleta oscura + cian del widget flotante ----
        # (18/09/2026, orden del señor Wáscar: la ventana debe verse igual
        # que el widget de JARVIS, no como tkinter por defecto).
        _BG = "#0e1117"
        _CARD = "#111318"
        _TXT = "#e8eaf0"
        _SUB = "#9aa3b5"
        _CYAN = "#00d3ff"
        root.configure(bg=_BG)
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(".", background=_BG, foreground=_TXT,
                        fieldbackground=_CARD, bordercolor="#2a3040",
                        focusthickness=0)
        style.configure("TFrame", background=_BG)
        style.configure("TLabel", background=_BG, foreground=_TXT,
                        font=("Segoe UI", 9))
        style.configure("TEntry", fieldbackground=_CARD, foreground=_TXT,
                        insertcolor=_TXT)
        style.configure("TCombobox", fieldbackground=_CARD, background=_CARD,
                        foreground=_TXT, arrowcolor=_CYAN)
        style.configure("TCheckbutton", background=_BG, foreground=_TXT)
        style.configure("TButton", background="#1a1e27", foreground=_TXT,
                        bordercolor="#2a3040", padding=(8, 5))
        style.map("TButton", background=[("active", "#2a3040")])
        style.configure("Treeview", background=_CARD, fieldbackground=_CARD,
                        foreground=_TXT, rowheight=26, bordercolor="#2a3040")
        style.configure("Treeview.Heading", background="#1a1e27",
                        foreground=_CYAN, font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#12507a")],
                  foreground=[("selected", "#ffffff")])
        style.configure("TLabelframe", background=_BG, bordercolor=_CYAN,
                        foreground=_TXT)
        style.configure("TLabelframe.Label", background=_BG, foreground=_CYAN,
                        font=("Segoe UI", 9, "bold"))

        # Estilo
        frm = ttk.Frame(root, padding=16)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Ajustes de JARVIS Telegram",
                  font=("Segoe UI", 12, "bold")).grid(row=0, column=0,
                                                      columnspan=2, sticky="w",
                                                      pady=(0, 12))

        ttk.Label(frm, text="Token de Telegram:").grid(row=1, column=0,
                                                       sticky="w", pady=3)
        entry_token = ttk.Entry(frm, width=46)
        entry_token.insert(0, str(valores.get("token", "")))
        entry_token.grid(row=1, column=1, sticky="we", pady=3)

        ttk.Label(frm, text="Chat ID:").grid(row=2, column=0, sticky="w", pady=3)
        entry_chat = ttk.Entry(frm, width=46)
        entry_chat.insert(0, str(valores.get("chat_id", "")))
        entry_chat.grid(row=2, column=1, sticky="we", pady=3)

        ttk.Label(frm, text="Agente (opencode):").grid(row=3, column=0,
                                                       sticky="w", pady=3)
        # Selector de agente: barra desplegable con los agentes disponibles
        # (la misma lista de agentes primarios que usa OpenCode). El señor Wáscar
        # elige de un vistazo en vez de teclear.
        AGENTES_DISPONIBLES = ("jarvis", "plan", "trading", "summary")
        combo_agente = ttk.Combobox(frm, values=AGENTES_DISPONIBLES,
                                    state="readonly", width=43)
        agente_actual = str(valores.get("agente", "jarvis"))
        if agente_actual not in AGENTES_DISPONIBLES:
            # Si hay un agente custom guardado, dejarlo visible igualmente
            combo_agente = ttk.Combobox(
                frm, values=AGENTES_DISPONIBLES + (agente_actual,),
                state="readonly", width=43)
        combo_agente.set(agente_actual)
        combo_agente.grid(row=3, column=1, sticky="we", pady=3)

        ttk.Label(frm, text="Modelo (OmniRoute):").grid(row=4, column=0,
                                                        sticky="w", pady=3)
        entry_modelo = ttk.Entry(frm, width=46)
        entry_modelo.insert(0, str(valores.get("modelo", "omniroute/COMBO JARVIS")))
        entry_modelo.grid(row=4, column=1, sticky="we", pady=3)

        ttk.Label(frm, text="Timeout (segundos):").grid(row=5, column=0,
                                                        sticky="w", pady=3)
        entry_timeout = ttk.Entry(frm, width=46)
        entry_timeout.insert(0, str(valores.get("timeout", 180)))
        entry_timeout.grid(row=5, column=1, sticky="we", pady=3)

        # Casilla "Iniciar con Windows": arranque automatico en cada encendido
        var_autostart = tk.BooleanVar(value=bool(valores.get("autostart", False)))
        chk_autostart = ttk.Checkbutton(
            frm,
            text="Iniciar JARVIS con Windows: arranca solo en segundo plano "
                 "cada vez que encienda la PC (si esta desactivada, se inicia "
                 "con el iniciador)",
            variable=var_autostart)
        chk_autostart.grid(row=6, column=0, columnspan=2, sticky="w", pady=3)

        # --- MOTOR: selector rápido estilo OPENCODE (18/09/2026, orden del
        # señor Wáscar: lista deslizante agrupada por proveedor, con búsqueda
        # y detalle, igual que el selector de opencode) ---
        frm_motor = ttk.LabelFrame(frm, text="🤖 Motor (selector rápido)",
                                   padding=8)
        frm_motor.grid(row=1, column=2, rowspan=6, sticky="n", padx=(12, 0))

        ttk.Label(frm_motor, text="🔍 Buscar modelos:").grid(
            row=0, column=0, columnspan=3, sticky="w")
        entry_busca = ttk.Entry(frm_motor, width=31)
        entry_busca.grid(row=1, column=0, columnspan=3, sticky="we", pady=(2, 4))

        tree = ttk.Treeview(frm_motor, columns=("info",), show="tree",
                            height=20, selectmode="browse")
        tree.heading("#0", text="Proveedor / Modelo")
        tree.column("#0", width=235)
        tree.grid(row=2, column=0, columnspan=3, sticky="we")
        vsb = ttk.Scrollbar(frm_motor, orient="vertical", command=tree.yview)
        vsb.grid(row=2, column=3, sticky="ns")
        tree.configure(yscrollcommand=vsb.set)

        lbl_detalle = ttk.Label(frm_motor, foreground=_SUB, wraplength=255,
                                justify="left",
                                text="Detalle: seleccione un modelo de la lista")
        lbl_detalle.grid(row=3, column=0, columnspan=3, sticky="w", pady=(4, 2))

        _motor_actual = str(valores.get("modelo", "omniroute/COMBO JARVIS"))
        _motor_anterior = str(valores.get("modelo_anterior", "") or "")
        lbl_actual_motor = ttk.Label(frm_motor, foreground=_CYAN,
                                     text="Actual: " + _motor_actual)
        lbl_actual_motor.grid(row=4, column=0, columnspan=3, sticky="w")
        if _motor_anterior:
            ttk.Label(frm_motor, foreground=_SUB,
                      text="Anterior: " + _motor_anterior).grid(
                row=5, column=0, columnspan=3, sticky="w")

        btn_actualizar = ttk.Button(frm_motor, text="🔄 Actualizar catálogo")
        btn_actualizar.grid(row=6, column=0, columnspan=3, sticky="we", pady=2)
        btn_probar = ttk.Button(frm_motor, text="⚡ Probar motor")
        btn_probar.grid(row=7, column=0, columnspan=3, sticky="we", pady=2)
        btn_guardar_motor = ttk.Button(frm_motor,
                                       text="💾 Guardar motor y reiniciar")
        btn_guardar_motor.grid(row=8, column=0, columnspan=3, sticky="we",
                               pady=2)
        fila_bot = ttk.Frame(frm_motor)
        fila_bot.grid(row=9, column=0, columnspan=3, sticky="we", pady=2)
        btn_volver = ttk.Button(fila_bot, text="↩️ Anterior")
        btn_volver.pack(side="left", expand=True, fill="x", padx=(0, 4))
        btn_reset_motor = ttk.Button(fila_bot, text="♻️ COMBO JARVIS")
        btn_reset_motor.pack(side="left", expand=True, fill="x")

        lbl_motor_estado = ttk.Label(frm_motor, foreground="#16a34a",
                                     width=40)
        lbl_motor_estado.grid(row=10, column=0, columnspan=3, sticky="w",
                              pady=(2, 0))

        _cat_models_cache = {}

        def _fijar_modelo(m, detalle=""):
            m = str(m or "").strip() or "omniroute/COMBO JARVIS"
            entry_modelo.delete(0, "end")
            entry_modelo.insert(0, m)
            if detalle:
                lbl_detalle.config(text=detalle)

        def _poblar_tree(filtro=""):
            tree.delete(*tree.get_children())
            filtro = (filtro or "").strip().lower()
            provs = _cat_models_cache
            if not isinstance(provs, dict) or "__error__" in provs:
                return
            # Nodo de combos OmniRoute (siempre primero, CERRADO para que se
            # vean TODOS los proveedores de un vistazo)
            combos = _combos_omniroute() or ["COMBO JARVIS"]
            if not filtro or "combo" in filtro:
                nodo = tree.insert(
                    "", "end",
                    text="🎛️ Combos de OmniRoute (%d)" % len(combos),
                    open=False)
                tree.insert(nodo, "end",
                            text="⭐ COMBO JARVIS (por defecto)",
                            values=("omniroute/COMBO JARVIS",))
                for c in combos:
                    if c != "COMBO JARVIS":
                        tree.insert(nodo, "end",
                                    text="🎛️ " + c,
                                    values=("omniroute/" + c,))
            # Proveedores -> modelos (nodos CERRADOS con contador: la lista
            # completa de proveedores queda visible de golpe; se despliegan
            # al hacer clic, como en opencode).
            for prov in sorted(provs.keys()):
                mods = [m for m in provs[prov]
                        if not filtro or filtro in m.lower()
                        or filtro in prov.lower()]
                if not mods:
                    continue
                nodo = tree.insert(
                    "", "end",
                    text="📦 %s (%d)" % (prov.upper(), len(mods)),
                    open=bool(filtro))
                for m in mods:
                    etiqueta = m
                    if "free" in m.lower():
                        etiqueta += "  (Gratis)"
                    if ("opencode-go/deepseek-v4-flash" in
                            (prov + "/" + m) and _motor_actual
                            and _motor_actual == "omniroute/COMBO JARVIS"):
                        etiqueta += "  ✓"
                    tree.insert(nodo, "end", text=etiqueta,
                                values=(prov + "/" + m,))

        def _cargar_opciones():
            nonlocal _cat_models_cache   # fix 18/09/2026: sin esto el árbol veía el cache vacío
            btn_actualizar.config(state="disabled")
            lbl_motor_estado.config(text="Cargando catálogo…")
            try:
                _cat_models_cache = _modelo_opencode()
                _poblar_tree(entry_busca.get())
                if isinstance(_cat_models_cache, dict) \
                        and "__error__" not in _cat_models_cache:
                    lbl_motor_estado.config(
                        text="Catálogo en vivo · " + time.strftime("%H:%M:%S"))
                else:
                    lbl_motor_estado.config(
                        text="Catálogo no disponible", foreground="#dc2626")
            except Exception as e:
                lbl_motor_estado.config(text=f"Catálogo: {e!r}",
                                        foreground="#dc2626")
            finally:
                btn_actualizar.config(state="normal")

        def _tree_select(_=None):
            sel = tree.selection()
            if not sel:
                return
            item = tree.item(sel[0])
            texto = str(item.get("text", ""))
            valor = item.get("values")
            if texto.startswith("⭐ COMBO JARVIS"):
                _fijar_modelo("omniroute/COMBO JARVIS",
                              "COMBO JARVIS por defecto · OmniRoute")
            elif texto.startswith("🎛️"):
                _fijar_modelo("omniroute/" + texto.replace("🎛️ ", ""),
                              "Combo de OmniRoute")
            elif valor:
                v = str(valor[0])
                prov, _, m = v.partition("/")
                detalle = "Modelo: " + m + "\nProveedor: " + prov
                if "free" in m.lower():
                    detalle += "\nEtiqueta: Gratis"
                elif "COMBO" in v.upper():
                    detalle = "Combo de OmniRoute"
                _fijar_modelo(v, detalle)

        tree.bind("<<TreeviewSelect>>", _tree_select)
        entry_busca.bind("<KeyRelease>",
                         lambda e: _poblar_tree(entry_busca.get()))
        btn_actualizar.config(command=_cargar_opciones)

        def _probar_ahora():
            lbl_motor_estado.config(text="Probando…")
            try:
                r = _probar_modelo(entry_modelo.get())
                if r.get("ok"):
                    lbl_motor_estado.config(
                        text=f"✅ Responde en {r['ms']} ms",
                        foreground="#16a34a")
                else:
                    lbl_motor_estado.config(
                        text=f"❌ {str(r.get('error'))[:44]}",
                        foreground="#dc2626")
            except Exception as e:
                lbl_motor_estado.config(text=f"❌ {e!r}",
                                        foreground="#dc2626")
        btn_probar.config(command=_probar_ahora)

        def _guardar_motor_y_reiniciar():
            modelo = entry_modelo.get().strip() or "omniroute/COMBO JARVIS"
            try:
                cfg = {}
                if os.path.exists(CONFIG_PATH):
                    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                        cfg = json.load(f) or {}
                previo = cfg.get("modelo")
                if previo and str(previo) != modelo:
                    cfg["modelo_anterior"] = previo
                cfg["modelo"] = modelo
                with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, ensure_ascii=False, indent=2)
                lbl_motor_estado.config(
                    text="✅ Motor guardado. Reiniciando en 8 s…",
                    foreground="#16a34a")
                _reiniciar_bot_diferido(8)
            except Exception as e:
                lbl_motor_estado.config(text=f"❌ {e!r}",
                                        foreground="#dc2626")
        btn_guardar_motor.config(command=_guardar_motor_y_reiniciar)

        def _volver_anterior():
            if not _motor_anterior:
                lbl_motor_estado.config(
                    text="No hay motor anterior guardado",
                    foreground="#dc2626")
                return
            _fijar_modelo(_motor_anterior)
            _guardar_motor_y_reiniciar()
        btn_volver.config(command=_volver_anterior)

        def _reset_combo():
            _fijar_modelo("omniroute/COMBO JARVIS")
            _guardar_motor_y_reiniciar()
        btn_reset_motor.config(command=_reset_combo)

        root.after(300, _cargar_opciones)

        # Estado de aplicacion
        lbl_estado = ttk.Label(frm, text="", foreground="#16a34a")
        lbl_estado.grid(row=7, column=0, columnspan=2, sticky="w", pady=(6, 0))

        # --- Panel de clic derecho (Copiar / Pegar / Cortar / Seleccionar) en
        # los campos de texto (habilitado por el señor Wáscar 01/09/2026) ---
        _menu_contexto_menu = None

        def _menu_contexto(widget):
            global _menu_contexto_menu
            _menu_contexto_menu = tk.Menu(root, tearoff=0)
            _menu_contexto_menu.add_command(
                label="✂️ Cortar",
                command=lambda: widget.event_generate("<<Cut>>"))
            _menu_contexto_menu.add_command(
                label="📋 Copiar",
                command=lambda: widget.event_generate("<<Copy>>"))
            _menu_contexto_menu.add_command(
                label="📥 Pegar",
                command=lambda: widget.event_generate("<<Paste>>"))
            _menu_contexto_menu.add_separator()
            _menu_contexto_menu.add_command(
                label="🔍 Seleccionar todo",
                command=lambda: widget.event_generate("<<SelectAll>>"))
            return _menu_contexto_menu

        def _atach_menu_contexto(widget):
            def _abrir(event):
                try:
                    _menu_contexto(widget).tk_popup(event.x_root, event.y_root)
                finally:
                    try:
                        _menu_contexto_menu.grab_release()
                    except Exception:
                        pass
            widget.bind("<Button-3>", _abrir)

        # Adjuntar el panel de clic derecho a cada campo editable
        for _w in (entry_token, entry_chat, entry_modelo, entry_timeout,
                   combo_agente):
            _atach_menu_contexto(_w)

        def _restaurar():
            """Restaura los ajustes predeterminados (valor inicial del bot)."""
            combo_agente.set(str(DEFAULT_CONFIG.get("agente", "jarvis")))
            entry_token.delete(0, tk.END)
            entry_token.insert(0, str(DEFAULT_CONFIG.get("token", "")))
            entry_chat.delete(0, tk.END)
            entry_chat.insert(0, str(DEFAULT_CONFIG.get("chat_id", "")))
            entry_modelo.delete(0, tk.END)
            entry_modelo.insert(0, str(DEFAULT_CONFIG.get(
                "modelo", "omniroute/COMBO JARVIS")))
            entry_timeout.delete(0, tk.END)
            entry_timeout.insert(0, str(DEFAULT_CONFIG.get("timeout", 180)))
            var_autostart.set(bool(DEFAULT_CONFIG.get("autostart", False)))
            lbl_estado.config(
                text="🔄 Ajustes restaurados a los predeterminados. "
                     "Pulsa Guardar para aplicarlos.",
                foreground="#2563eb")

        def _guardar():
            try:
                token = entry_token.get().strip()
                chat = entry_chat.get().strip()
                agente = combo_agente.get().strip() or "jarvis"
                modelo = entry_modelo.get().strip() or "omniroute/COMBO JARVIS"
                # 16/09/2026 (orden del señor Wáscar): el reloj unico es el valor de
                # siempre si el campo queda vacio o mal escrito.
                try:
                    timeout = int(entry_timeout.get().strip() or str(RELOJ_TELEGRAM))
                except ValueError:
                    timeout = RELOJ_TELEGRAM
                if not token or not chat:
                    lbl_estado.config(text="⚠️ Token y Chat ID son obligatorios",
                                      foreground="#dc2626")
                    return
                # 18/09/2026 (orden del señor Wáscar): guardar el modelo
                # anterior para poder volver con un toque.
                prev_cfg = {}
                try:
                    if os.path.exists(CONFIG_PATH):
                        with open(CONFIG_PATH, "r", encoding="utf-8") as pf:
                            prev_cfg = json.load(pf) or {}
                except Exception:
                    prev_cfg = {}
                datos = {
                    "token": token,
                    "chat_id": chat,
                    "agente": agente,
                    "modelo": modelo,
                    "timeout": timeout,
                    "autostart": bool(var_autostart.get()),
                }
                if prev_cfg.get("modelo") and str(prev_cfg["modelo"]) != modelo:
                    datos["modelo_anterior"] = str(prev_cfg["modelo"])
                if _guardar_config(datos):
                    ok, msg = _aplicar_autostart(bool(var_autostart.get()))
                    if ok:
                        lbl_estado.config(
                            text="✅ Guardado. " + msg,
                            foreground="#16a34a")
                    else:
                        lbl_estado.config(text="❌ " + msg,
                                          foreground="#dc2626")
                        messagebox.showwarning("Ajustes JARVIS", msg)
                    messagebox.showinfo(
                        "Ajustes JARVIS",
                        "Ajustes guardados correctamente.\n\n"
                        "Los cambios aplican al reiniciar JARVIS "
                        "(botón Reiniciar del menú o del Telegram).")
                else:
                    lbl_estado.config(text="❌ Error al guardar",
                                      foreground="#dc2626")
            except Exception as e:
                print(f"[AJUSTES] error al guardar: {e!r}")
                lbl_estado.config(text=f"❌ {e!r}", foreground="#dc2626")

        # Botones: Guardar a la derecha y Cerrar a la izquierda (pedido del
        # señor Wáscar 01/09/2026). "Cerrar" SOLO cierra esta ventana de Ajustes;
        # NO apaga JARVIS (el "Cerrar completamente" de la bandeja es el que
        # apaga todo). "Restaurar ajustes predeterminados" devuelve todo a
        # los valores iniciales del bot.
        btn_cerrar = ttk.Button(frm, text="Cerrar",
                                command=root.destroy)
        btn_cerrar.grid(row=8, column=0, sticky="w", pady=(12, 0))
        btn_guardar = ttk.Button(frm, text="💾 Guardar", command=_guardar)
        btn_guardar.grid(row=8, column=1, sticky="e", pady=(12, 0))
        btn_restaurar = ttk.Button(frm, text="🔄 Restaurar ajustes "
                                             "predeterminados",
                                   command=_restaurar)
        btn_restaurar.grid(row=9, column=0, columnspan=2, sticky="we",
                           pady=(8, 0))

        # Centrar la ventana en la pantalla
        try:
            root.update_idletasks()
            w = root.winfo_width()
            h = root.winfo_height()
            x = (root.winfo_screenwidth() - w) // 2
            y = (root.winfo_screenheight() - h) // 2
            root.geometry(f"+{x}+{y}")
        except Exception:
            pass

        print("[AJUSTES] ventana abierta")
        root.mainloop()

    threading.Thread(target=_ventana_ajustes_v2, daemon=True).start()


def _ventana_ajustes_v2():
    """AJUSTES v2 (18/09/2026, orden del señor Wáscar): ventana COMPACTA
    y organizada en pestañas. La pestaña MOTOR muestra la lista COMPLETA
    de modelos de opencode (todos los proveedores abiertos, agrupados,
    igual que el selector de opencode)."""
    global _AJUSTES_V2_ROOT, _AJUSTES_V2_ABRIENDO
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except Exception as e:
        print(f"[AJUSTES] tkinter no disponible: {e!r}")
        return

    def _leer_cfg_v2():
        try:
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f) or {}
        except Exception:
            pass
        return {}

    cfg = _leer_cfg_v2()
    root = tk.Tk()
    # Instancia unica: registrar la ventana viva (blindaje 18/09/2026).
    _AJUSTES_V2_ROOT = root
    _AJUSTES_V2_ABRIENDO = None
    root.title("Ajustes - JARVIS Telegram")
    # Icono OFICIAL de la ventana (orden del senor Wascar 18/09/2026): el .ico
    # se aplica con user32 (WM_SETICON) porque el iconbitmap de Tk rechaza los
    # .ico modernos con PNG interno (por eso salia el de Python). El boton de
    # minimizar quedo RESTAURADO como estaba (orden posterior del mismo dia).
    def _aplicar_estilo_ajustes():
        try:
            import ctypes as _ct
            u32 = _ct.windll.user32
            hwnd = u32.GetParent(root.winfo_id()) or root.winfo_id()
            ico = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "assets", "jarvis.ico")
            if os.path.exists(ico):
                h_small = u32.LoadImageW(None, ico, 1, 16, 16, 0x0010)
                h_big = u32.LoadImageW(None, ico, 1, 32, 32, 0x0010)
                if h_small:
                    u32.SendMessageW(hwnd, 0x0080, 0, h_small)
                if h_big:
                    u32.SendMessageW(hwnd, 0x0080, 1, h_big)
        except Exception:
            pass
    try:
        root.after(400, _aplicar_estilo_ajustes)
    except Exception:
        pass
    # (18/09/2026, orden del senor Wascar): SIN ventana "siempre encima".
    # Se comporta como una ventana normal: si hace clic fuera, pasa atras.

    _BG = "#0e1117"; _CARD = "#111318"; _TXT = "#e8eaf0"
    _SUB = "#9aa3b5"; _CYAN = "#00d3ff"
    root.configure(bg=_BG)
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure(".", background=_BG, foreground=_TXT,
                    fieldbackground=_CARD, bordercolor="#2a3040",
                    focusthickness=0)
    style.configure("TFrame", background=_BG)
    style.configure("TLabel", background=_BG, foreground=_TXT,
                    font=("Segoe UI", 9))
    style.configure("TEntry", fieldbackground=_CARD, foreground=_TXT,
                    insertcolor=_TXT)
    style.configure("TButton", background="#1a1e27", foreground=_TXT,
                    bordercolor="#2a3040", padding=(7, 4))
    style.map("TButton", background=[("active", "#2a3040")])
    style.configure("TCheckbutton", background=_BG, foreground=_TXT)
    style.configure("TNotebook", background=_BG, bordercolor=_CYAN)
    style.configure("TNotebook.Tab", background="#1a1e27",
                    foreground=_TXT, padding=(10, 5),
                    font=("Segoe UI", 9, "bold"))
    style.map("TNotebook.Tab",
              background=[("selected", "#12507a")],
              foreground=[("selected", "#ffffff")])
    style.configure("Treeview", background=_CARD, fieldbackground=_CARD,
                    foreground=_TXT, rowheight=24, bordercolor="#2a3040")
    style.map("Treeview", background=[("selected", "#12507a")],
              foreground=[("selected", "#ffffff")])

    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True, padx=8, pady=8)

    # ---------------- PESTAÑA MOTOR ----------------
    f_motor = ttk.Frame(nb, padding=8)
    nb.add(f_motor, text="🧠 Razonamiento")

    ttk.Label(f_motor, text="🔍 Buscar modelos:").pack(anchor="w")
    entry_busca = ttk.Entry(f_motor)
    entry_busca.pack(fill="x", pady=(2, 6))
    # Placeholder dentro de la caja (orden del señor Wáscar 18/09/2026):
    _PH_BUSCA = "Busca tu modelo específico"

    def _filtro_busqueda_v2():
        """Texto del buscador, tratando el placeholder como vacio."""
        t = entry_busca.get()
        return "" if t == _PH_BUSCA else t

    def _ph_in(_e=None):
        if entry_busca.get() == _PH_BUSCA:
            entry_busca.delete(0, "end")
            entry_busca.configure(foreground=_TXT)

    def _ph_out(_e=None):
        if not entry_busca.get().strip():
            entry_busca.delete(0, "end")
            entry_busca.insert(0, _PH_BUSCA)
            entry_busca.configure(foreground="#6b7280")

    entry_busca.insert(0, _PH_BUSCA)
    entry_busca.configure(foreground="#6b7280")
    entry_busca.bind("<FocusIn>", _ph_in)
    entry_busca.bind("<FocusOut>", _ph_out)

    f_tree = ttk.Frame(f_motor)
    f_tree.pack(fill="both", expand=True)
    tree = ttk.Treeview(f_tree, columns=("info",), show="tree",
                        height=13, selectmode="browse")
    tree.heading("#0", text="Proveedor / Modelo")
    tree.column("#0", width=430)
    vsb = ttk.Scrollbar(f_tree, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="left", fill="y")

    lbl_detalle = ttk.Label(f_motor, foreground=_SUB, wraplength=430,
                            justify="left",
                            text="Seleccione un modelo de la lista")
    lbl_detalle.pack(anchor="w", pady=(6, 2))
    _motor_actual = str(cfg.get("modelo", "omniroute/COMBO JARVIS"))
    _motor_anterior = str(cfg.get("modelo_anterior", "") or "")
    lbl_actual = ttk.Label(f_motor, foreground=_CYAN,
                           text="Actual: " + _motor_actual)
    lbl_actual.pack(anchor="w")
    if _motor_anterior:
        ttk.Label(f_motor, foreground=_SUB,
                  text="Anterior: " + _motor_anterior).pack(anchor="w")
    lbl_estado = ttk.Label(f_motor, foreground="#16a34a")
    lbl_estado.pack(anchor="w", pady=(2, 0))

    fila_btn = ttk.Frame(f_motor)
    fila_btn.pack(fill="x", pady=(6, 0))
    btn_actualizar = ttk.Button(fila_btn, text="🔄 Actualizar")
    btn_disponibles = ttk.Button(fila_btn, text="✅ Disponibles")
    btn_probar = ttk.Button(fila_btn, text="⚡ Probar")
    btn_guardar = ttk.Button(fila_btn, text="💾 Guardar y reiniciar")
    # Repartidos por igual en el ancho (orden del senor Wascar 18/09/2026:
    # fuera "Anterior" y "COMBO JARVIS").
    for _b in (btn_actualizar, btn_disponibles, btn_probar, btn_guardar):
        _b.pack(side="left", expand=True, fill="x", padx=(0, 6))

    _cat_models_cache = {}
    modelo_elegido = {"m": None}   # modelo seleccionado en la lista
    _ultimos_disponibles = {"ts": None, "ok": [], "mal": [], "sin": 0}  # Disponibles AHORA

    def _fijar_modelo_v2(m, detalle=""):
        m = str(m or "").strip() or "omniroute/COMBO JARVIS"
        lbl_detalle.config(text=detalle or "Seleccionado: " + m)
        lbl_estado.config(text="", foreground="#16a34a")

    def _insertar_disponibles_v2(filtro=""):
        """Inserta al tope el nodo '✅ Disponibles AHORA' con la ultima
        comprobacion en vivo (si existe). Respeta el filtro de busqueda."""
        d = _ultimos_disponibles
        if not d or not d.get("ts"):
            return
        f = (filtro or "").strip().lower()
        oks = [(m, ms) for (m, ms) in d["ok"] if not f or f in m.lower()]
        mals = [(m, mo) for (m, mo) in d["mal"] if not f or f in m.lower()]
        if not oks and not mals:
            return
        nodo = tree.insert(
            "", 0,
            text="✅ Disponibles AHORA (%d de %d · %s)"
                 % (len(d["ok"]), len(d["ok"]) + len(d["mal"]), d["ts"]),
            open=True)
        for m, ms in sorted(oks, key=lambda x: x[0]):
            et = m + ("   —   " + str(ms) + " ms" if ms else "")
            if "free" in m.lower():
                et += "  (Gratis)"
            tree.insert(nodo, "end", text=et, values=(m,))
        if mals:
            sub = tree.insert("", 1,
                              text="⛔ No disponibles / sin dato (%d)"
                                   % len(mals),
                              open=False)
            for m, mo in sorted(mals, key=lambda x: x[0]):
                tree.insert(sub, "end", text=m + "   —   " + mo[:60],
                            values=(m,))

    def _poblar_tree_v2(filtro=""):
        tree.delete(*tree.get_children())
        filtro = (filtro or "").strip().lower()
        provs = _cat_models_cache
        if not isinstance(provs, dict) or "__error__" in provs:
            lbl_estado.config(
                text="❌ " + str(provs.get("__error__", "no disponible"))[:70],
                foreground="#dc2626")
            return
        # Nodo "Disponibles AHORA" (si hay comprobacion hecha): SIEMPRE primero.
        _insertar_disponibles_v2(filtro)
        # (18/09/2026, orden del senor Wascar): RETIRADO el grupo "Combos de
        # OmniRoute" del arbol (no existe en opencode). El combo sigue
        # disponible dentro del grupo OMNIROUTE y en el boton "COMBO JARVIS".
        for prov in sorted(provs.keys()):
            mods = [m for m in provs[prov]
                    if not filtro or filtro in m.lower()
                    or filtro in prov.lower()]
            if not mods:
                continue
            nodo = tree.insert("", "end",
                               text="%s (%d)" % (prov.upper(), len(mods)),
                               open=True)   # ABIERTO: la lista completa
            for m in mods:
                etiqueta = m
                if "free" in m.lower():
                    etiqueta += "  (Gratis)"
                if ((prov + "/" + m) in ("opencode-go/deepseek-v4-flash")
                        and _motor_actual == "omniroute/COMBO JARVIS"):
                    etiqueta += "  ✓"
                tree.insert(nodo, "end", text=etiqueta,
                            values=(prov + "/" + m,))
        n_prov = sum(1 for p in provs if len(provs.get(p, [])) > 0)
        if n_prov:
            lbl_estado.config(text="%d proveedores · %d modelos · %s"
                                   % (n_prov,
                                      sum(len(v) for v in provs.values()),
                                      time.strftime("%H:%M:%S")),
                              foreground="#16a34a")
        else:
            lbl_estado.config(text="Catálogo vacío: pulse Actualizar",
                              foreground="#dc2626")

    def _cargar_opciones_v2():
        nonlocal _cat_models_cache   # fix 18/09/2026: sin esto el árbol veía el cache vacío
        btn_actualizar.config(state="disabled")
        lbl_estado.config(text="Cargando catálogo…")
        try:
            _cat_models_cache = _modelo_opencode()
            print("[MOTOR] intento1 cache keys:", list(_cat_models_cache.keys())[:6]
                  if isinstance(_cat_models_cache, dict) else type(_cat_models_cache))
            if not _cat_models_cache or "__error__" in _cat_models_cache:
                # Reintento: a veces el primer arranque tarda más.
                _cat_models_cache = _modelo_opencode()
                print("[MOTOR] intento2 cache keys:",
                      list(_cat_models_cache.keys())[:6]
                      if isinstance(_cat_models_cache, dict)
                      else type(_cat_models_cache))
            _poblar_tree_v2(_filtro_busqueda_v2())
        except Exception as e:
            print("[MOTOR] excepcion:", repr(e))
            lbl_estado.config(text=f"Catálogo: {e!r}",
                              foreground="#dc2626")
        finally:
            btn_actualizar.config(state="normal")

    def _tree_select_v2(_=None):
        sel = tree.selection()
        if not sel:
            return
        item = tree.item(sel[0])
        texto = str(item.get("text", ""))
        valor = item.get("values")
        if texto.startswith("⭐ COMBO JARVIS"):
            lbl_detalle.config(text="COMBO JARVIS por defecto · OmniRoute")
        elif texto.startswith("🎛️"):
            lbl_detalle.config(text="Combo de OmniRoute")
        elif valor:
            v = str(valor[0])
            prov, _, m = v.partition("/")
            det = "Modelo: " + m + "   |   Proveedor: " + prov
            if "free" in m.lower():
                det += "   |   Gratis"
            lbl_detalle.config(text=det)
            modelo_elegido["m"] = v

    tree.bind("<<TreeviewSelect>>", _tree_select_v2)
    entry_busca.bind("<KeyRelease>",
                     lambda e: _poblar_tree_v2(_filtro_busqueda_v2()))

    def _probar_v2():
        modelo = modelo_elegido["m"] or _motor_actual
        lbl_estado.config(text="Probando…")
        try:
            r = _probar_modelo(modelo)
        except Exception:
            r = None
        if r and r.get("ok"):
            lbl_estado.config(text=f"✅ Responde en {r['ms']} ms",
                              foreground="#16a34a")
        else:
            lbl_estado.config(
                text="❌ " + str((r or {}).get("error"))[:44],
                foreground="#dc2626")
    btn_probar.config(command=_probar_v2)

    def _guardar_motor_v2(modelo=None):
        modelo = (modelo or "").strip() or "omniroute/COMBO JARVIS"
        # VALIDACION PREVIA (orden del senor Wascar 18/09/2026): se prueba el
        # modelo de verdad ANTES de aplicarlo; si no esta disponible NO se
        # guarda ni se reinicia: se avisa claro para elegir otro.
        lbl_estado.config(text="⏳ Probando «%s»…" % modelo,
                          foreground="#2563eb")
        try:
            prueba = _probar_modelo(modelo, timeout=30)
        except Exception as e:
            prueba = {"ok": False, "error": repr(e)}
        if not (prueba and prueba.get("ok")):
            motivo = str((prueba or {}).get("error", "sin respuesta"))[:100]
            lbl_estado.config(
                text="❌ «%s» no está disponible ahora mismo, señor. "
                     "Elija otro modelo. (%s)" % (modelo, motivo),
                foreground="#dc2626")
            return
        try:
            cfgc = _leer_cfg_v2()
            previo = cfgc.get("modelo")
            if previo and str(previo) != modelo:
                cfgc["modelo_anterior"] = previo
            cfgc["modelo"] = modelo
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfgc, f, ensure_ascii=False, indent=2)
            lbl_estado.config(
                text="✅ Motor guardado: %s (responde en %d ms). Este será "
                     "el modelo que responda por Telegram. Reiniciando "
                     "ahora mismo…" % (modelo, prueba.get("ms", 0)),
                foreground="#16a34a")
            # Reinicio INSTANTANEO (orden del senor Wascar 18/09/2026): sin
            # temporizador; el config ya quedo guardado arriba.
            _reiniciar_bot_diferido(0)
        except Exception as e:
            lbl_estado.config(text=f"❌ {e!r}", foreground="#dc2626")

    btn_guardar.config(command=lambda: _guardar_motor_v2(
        modelo_elegido["m"] or _motor_actual))
    btn_actualizar.config(command=_cargar_opciones_v2)

    def _comprobar_disponibles_v2():
        """Disponibilidad SIN llamar a los modelos (orden del senor Wascar
        18/09/2026): consulta el estado que OmniRoute mantiene con SUS
        chequeos de fondo. Instantaneo y sin consumo."""
        provs = _cat_models_cache
        if not isinstance(provs, dict) or "__error__" in provs:
            lbl_estado.config(
                text="⚠️ Cargue primero el catálogo (🔄 Actualizar)",
                foreground="#dc2626")
            return
        lbl_estado.config(text="⏳ Consultando estado de OmniRoute…",
                          foreground="#2563eb")
        try:
            mapa = _disponibilidad_omniroute()
        except Exception:
            mapa = None
        if mapa is None:
            lbl_estado.config(
                text="❌ OmniRoute no responde ahora mismo (¿gateway apagado?)",
                foreground="#dc2626")
            return
        ok, mal, sin = [], [], []
        for prov in sorted(provs.keys()):
            for m in provs[prov]:
                base = prov + "/" + m
                if prov == "opencode":
                    claves = [("opencode-zen/" + m).lower(),
                              ("oc/" + m).lower(), base.lower()]
                else:
                    claves = [base.lower()]
                av = None
                for k in claves:
                    if k in mapa:
                        av = mapa[k]
                        break
                if av is None:
                    sin.append(base)
                elif av:
                    ok.append(base)
                else:
                    mal.append(base)
        _ultimos_disponibles["ts"] = time.strftime("%H:%M:%S")
        _ultimos_disponibles["ok"] = [(m, 0) for m in sorted(ok)]
        _ultimos_disponibles["mal"] = (
            [(m, "no disponible (OmniRoute)") for m in sorted(mal)]
            + [(m, "sin dato en OmniRoute") for m in sorted(sin)])
        _ultimos_disponibles["sin"] = len(sin)
        _poblar_tree_v2(_filtro_busqueda_v2())
        lbl_estado.config(
            text="✅ %d disponibles · ⛔ %d no disponibles · ❔ %d sin dato "
                 "· (estado OmniRoute %s)"
                 % (len(ok), len(mal), len(sin), _ultimos_disponibles["ts"]),
            foreground="#16a34a")

    btn_disponibles.config(command=_comprobar_disponibles_v2)

    # ---------------- PESTAÑA CEREBRO ----------------
    # (orden del señor Wáscar 18/09/2026): intercambiar el AGENTE activo
    # (jarvis, doctor, trading, plan...). Guarda el config y reinicia.
    f_cere = ttk.Frame(nb, padding=8)
    nb.add(f_cere, text="🧠 Cerebro")

    ttk.Label(f_cere, text="🧠 Agentes disponibles (cerebros de opencode)").pack(anchor="w")
    ttk.Label(f_cere, text="Elija con cual responde JARVIS y guarde: aplica al reiniciar.",
              foreground=_SUB).pack(anchor="w", pady=(0, 6))

    f_cere_tree = ttk.Frame(f_cere)
    f_cere_tree.pack(fill="both", expand=True)
    tree_cere = ttk.Treeview(f_cere_tree, columns=("info",), show="tree",
                             height=13, selectmode="browse")
    tree_cere.column("#0", width=430)
    vsb_c = ttk.Scrollbar(f_cere_tree, orient="vertical",
                          command=tree_cere.yview)
    tree_cere.configure(yscrollcommand=vsb_c.set)
    tree_cere.pack(side="left", fill="both", expand=True)
    vsb_c.pack(side="left", fill="y")

    lbl_cere = ttk.Label(f_cere, foreground=_SUB,
                         text="Seleccione un agente de la lista")
    lbl_cere.pack(anchor="w", pady=(6, 2))
    lbl_cere_estado = ttk.Label(f_cere, foreground="#16a34a", text="")
    lbl_cere_estado.pack(anchor="w")

    def _agentes_disponibles():
        """Agentes de opencode: (cerebros del sistema [archivos], built-in)."""
        base = os.path.join(os.path.expanduser("~"), ".config", "opencode",
                            "agent")
        sistema = []
        try:
            for n in sorted(os.listdir(base)):
                p2 = os.path.join(base, n)
                if os.path.isfile(p2) and n.endswith(".md"):
                    sistema.append(n[:-3])
                elif os.path.isdir(p2):
                    for sub in sorted(os.listdir(p2)):
                        if sub.endswith(".md"):
                            sistema.append(n + "/" + sub[:-3])
        except Exception:
            pass
        # Built-in de opencode (no viven como archivo en agent/):
        builtin = ["build", "compaction", "explore", "general", "summary",
                   "title"]
        return sistema, builtin

    def _poblar_cerebro():
        tree_cere.delete(*tree_cere.get_children())
        ag_actual = str(_leer_cfg_v2().get("agente", "jarvis") or "jarvis")
        sistema, builtin = _agentes_disponibles()
        n1 = tree_cere.insert(
            "", "end",
            text="🧩 Cerebros del sistema (%d)" % len(sistema), open=True)
        for ag in sistema:
            et = ag + ("   ✔ (actual)" if ag == ag_actual else "")
            tree_cere.insert(n1, "end", text=et, values=(ag,))
        n2 = tree_cere.insert(
            "", "end",
            text="⚙️ De opencode (%d)" % len(builtin), open=False)
        for ag in builtin:
            et = ag + ("   ✔ (actual)" if ag == ag_actual else "")
            tree_cere.insert(n2, "end", text=et, values=(ag,))

    def _cere_select(event=None):
        sel = tree_cere.selection()
        if sel:
            v = str(tree_cere.item(sel[0]).get("values", [""])[0])
            lbl_cere.config(text="Seleccionado: " + v)

    tree_cere.bind("<<TreeviewSelect>>", _cere_select)

    def _guardar_cerebro_v2():
        sel = tree_cere.selection()
        if not sel:
            lbl_cere_estado.config(text="⚠️ Seleccione un agente primero",
                                   foreground="#dc2626")
            return
        ag = str(tree_cere.item(sel[0]).get("values", [""])[0]).strip() or "jarvis"
        try:
            cfgc = _leer_cfg_v2()
            cfgc["agente"] = ag
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfgc, f, ensure_ascii=False, indent=2)
            lbl_cere_estado.config(
                text="✅ Cerebro cambiado a «%s». Reiniciando ahora mismo…" % ag,
                foreground="#16a34a")
            _reiniciar_bot_diferido(0)
        except Exception as e:
            lbl_cere_estado.config(text="❌ %r" % e, foreground="#dc2626")

    ttk.Button(f_cere, text="💾 Guardar y reiniciar",
               command=_guardar_cerebro_v2).pack(fill="x", pady=(6, 0))
    _poblar_cerebro()

    # ---------------- PESTAÑA TELEGRAM ----------------
    f_tg = ttk.Frame(nb, padding=8)
    nb.add(f_tg, text="📞 Telegram")

    ttk.Label(f_tg, text="Token del bot:").grid(row=0, column=0, sticky="w",
                                                pady=3)
    entry_token = ttk.Entry(f_tg, width=40)
    entry_token.insert(0, str(cfg.get("token", "")))
    entry_token.grid(row=0, column=1, sticky="we", pady=3)

    ttk.Label(f_tg, text="Chat ID:").grid(row=1, column=0, sticky="w", pady=3)
    entry_chat = ttk.Entry(f_tg, width=40)
    entry_chat.insert(0, str(cfg.get("chat_id", "")))
    entry_chat.grid(row=1, column=1, sticky="we", pady=3)

    ttk.Label(f_tg, text="Timeout (seg):").grid(row=2, column=0, sticky="w",
                                                pady=3)
    entry_timeout = ttk.Entry(f_tg, width=40)
    entry_timeout.insert(0, str(cfg.get("timeout", RELOJ_TELEGRAM)))
    entry_timeout.grid(row=2, column=1, sticky="we", pady=3)

    var_autostart = None  # (18/09/2026: el arranque con Windows vive en General)
    lbl_tg = ttk.Label(f_tg, foreground="#16a34a")
    lbl_tg.grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))

    def _guardar_tg():
        try:
            token = entry_token.get().strip()
            chat = entry_chat.get().strip()
            if not token or not chat:
                lbl_tg.config(text="⚠️ Token y Chat ID obligatorios",
                              foreground="#dc2626")
                return
            try:
                timeout = int(entry_timeout.get().strip()
                              or str(RELOJ_TELEGRAM))
            except ValueError:
                timeout = RELOJ_TELEGRAM
            datos = {"token": token, "chat_id": chat, "timeout": timeout}
            cfgc = _leer_cfg_v2()
            cfgc.update(datos)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfgc, f, ensure_ascii=False, indent=2)
            lbl_tg.config(text="✅ Guardado. Aplica al reiniciar.",
                          foreground="#16a34a")
        except Exception as e:
            lbl_tg.config(text=f"❌ {e!r}", foreground="#dc2626")

    ttk.Button(f_tg, text="💾 Guardar Telegram",
               command=_guardar_tg).grid(row=5, column=0, columnspan=2,
                                         sticky="we", pady=(8, 0))

    # ---------------- PESTAÑA GENERAL ----------------
    f_gen = ttk.Frame(nb, padding=8)
    nb.add(f_gen, text="⚙️ General")

    # (18/09/2026, orden del senor Wascar): General queda con lo BASICO:
    # arranque con Windows + restablecer predeterminados. El agente (cerebro)
    # se cambio a su propia pestana.
    ttk.Label(f_gen, text="Ajustes generales de JARVIS").pack(anchor="w")
    ttk.Label(f_gen, text="Inicio del sistema y restablecimiento.",
              foreground=_SUB).pack(anchor="w", pady=(0, 8))

    var_auto_g = tk.BooleanVar(value=bool(cfg.get("autostart", False)))
    ttk.Checkbutton(f_gen, text="🚀 Iniciar JARVIS con Windows",
                    variable=var_auto_g).pack(anchor="w")
    lbl_gen = ttk.Label(f_gen, foreground="#16a34a")
    lbl_gen.pack(anchor="w", pady=(4, 12))

    def _guardar_auto_v2():
        activo = bool(var_auto_g.get())
        try:
            cfgc = _leer_cfg_v2()
            cfgc["autostart"] = activo
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(cfgc, f, ensure_ascii=False, indent=2)
            ok, msg = _aplicar_autostart(activo)
            lbl_gen.config(text=("✅ " + msg) if ok else ("❌ " + msg),
                           foreground="#16a34a" if ok else "#dc2626")
        except Exception as e:
            lbl_gen.config(text="❌ %r" % e, foreground="#dc2626")

    ttk.Button(f_gen, text="💾 Guardar arranque",
               command=_guardar_auto_v2).pack(fill="x", pady=(0, 14))

    def _reset_total_v2():
        if not messagebox.askyesno(
                "Restablecer ajustes",
                "¿Volver a los ajustes predeterminados?\n\n"
                "Se restableceran el modelo, el agente, el timeout y el "
                "arranque. El bot se reiniciara al instante."):
            return
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
            lbl_gen.config(
                text="✅ Ajustes predeterminados restaurados. Reiniciando…",
                foreground="#16a34a")
            _reiniciar_bot_diferido(0)
        except Exception as e:
            lbl_gen.config(text="❌ %r" % e, foreground="#dc2626")

    ttk.Button(f_gen, text="🔄 Restablecer ajustes predeterminados",
               command=_reset_total_v2).pack(fill="x")

    # Cargar el catálogo al abrir y centrar
    root.after(300, _cargar_opciones_v2)
    try:
        root.update_idletasks()
        x = (root.winfo_screenwidth() - root.winfo_width()) // 2
        y = (root.winfo_screenheight() - root.winfo_height()) // 2
        root.geometry(f"+{x}+{y}")
    except Exception:
        pass
    root.mainloop()
    # Ventana cerrada: liberar la instancia unica (blindaje 18/09/2026).
    _AJUSTES_V2_ROOT = None
    _AJUSTES_V2_ABRIENDO = None


def iniciar_bandeja():
    """Icono de JARVIS en la bandeja del sistema (iconos ocultos), en un hilo.
    Menu: abrir chat de JARVIS, reiniciar, AJUSTES, salir."""
    try:
        import pystray
        from PIL import Image, ImageDraw, ImageFont

        def _imagen_icono():
            """Icono OFICIAL de JARVIS (arc reactor cian, orden del senor
            Wascar 18/09/2026): se carga `proyectos\\assets\\jarvis.png`. Si
            faltara el archivo, se usa el dibujo clasico de la J (fallback)."""
            try:
                ico = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "assets", "jarvis.png")
                return Image.open(ico).convert("RGBA")
            except Exception:
                pass
            s = 64
            img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.ellipse((2, 2, s - 2, s - 2), fill=(16, 20, 24, 255))
            for i in range(0, 360, 30):
                d.arc((4, 4, s - 4, s - 4), i, i + 22, fill=(0, 211, 255, 255), width=3)
            d.ellipse((15, 15, s - 15, s - 15), fill=(0, 100, 224, 255))
            d.ellipse((21, 21, s - 21, s - 21), fill=(30, 144, 255, 255))
            try:
                font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 26)
            except Exception:
                font = ImageFont.load_default()
            bb = d.textbbox((0, 0), "J", font=font)
            tw = bb[2] - bb[0]
            th = bb[3] - bb[1]
            d.text(((s - tw) / 2 - bb[0], (s - th) / 2 - bb[1] + 2), "J", font=font, fill="white")
            return img

        def _abrir_chat(icon, item):
            """Abre la TUI de OPENCODE con la sesion activa de JARVIS: la
            misma sesion por la que el bot habla con Telegram. Muestra el
            hilo real de la conversacion (mensajes del señor Wáscar, herramientas,
            respuestas) tal como opencode lo registra en su BD (fix
            31/08/2026)."""
            try:
                # Sesion activa: la ultima registrada en el pool (la que
                # recibio el ultimo mensaje de Telegram). Si no hay sesion,
                # se abre la TUI general de opencode.
                sid = None
                try:
                    pool = _cargar_pool_sesiones()
                    if pool:
                        sid = pool[-1].get("sid")
                except Exception:
                    sid = None
                if sid:
                    cmd = f'start "JARVIS - OpenCode Chat" cmd /k opencode --session {sid}'
                    print(f"[BANDEJA] abriendo TUI de opencode con sesion {sid[:20]}...")
                else:
                    cmd = 'start "JARVIS - OpenCode Chat" cmd /k opencode'
                    print("[BANDEJA] abriendo TUI de opencode (sin sesion previa)")
                # Ventana cmd VISIBLE (sin CREATE_NO_WINDOW): se ve la TUI
                subprocess.Popen(cmd, shell=True)
            except Exception as e:
                print(f"[BANDEJA] error abrir chat: {e!r}")

        def _reiniciar(icon, item):
            try:
                # Reinicio diferido: el orquestador mata instancias y puertos
                # y relanza todo en segundo plano. FIX 03/09/2026: la ruta
                # apuntaba a una carpeta inexistente ("Default Project") y el
                # boton fallaba en silencio; ahora se localiza el lanzador
                # real (junto al bot, kit o manos del sistema).
                script = _buscar_script_lanzar()
                if not script:
                    print("[BANDEJA] no se encontro lanzar_jarvis_telegram.ps1")
                    return
                script_escapado = script.replace("'", "''")
                subprocess.Popen(
                    'start /b powershell -NoProfile -ExecutionPolicy Bypass -Command '
                    '"Start-Sleep -Seconds 3; & \'%s\'"' % script_escapado,
                    shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            except Exception as e:
                print(f"[BANDEJA] error reiniciar: {e!r}")

        def _salir(icon, item):
            """Cerrar completamente: apaga TODO JARVIS de forma limpia
            (bot, instancias, puertos y OmniRoute) y deja la bandeja dormida."""
            _cerrar_jarvis_completamente()
            icon.stop()

        def _ajustes(icon, item):
            """Abre la ventana de Ajustes de JARVIS Telegram (Tkinter)."""
            try:
                _abrir_ventana_ajustes()
            except Exception as e:
                print(f"[BANDEJA] error abrir ajustes: {e!r}")

        def _widget_mostrar(icon, item):
            """Muestra (o lanza) la ventana flotante de voz de JARVIS."""
            try:
                _widget_cmd("--mostrar")
                print("[BANDEJA] widget flotante: mostrar/activar")
            except Exception as e:
                print(f"[BANDEJA] error widget mostrar: {e!r}")

        def _widget_ocultar(icon, item):
            """Oculta la ventana flotante (el proceso sigue vivo)."""
            try:
                _widget_cmd("--ocultar")
                print("[BANDEJA] widget flotante: ocultar")
            except Exception as e:
                print(f"[BANDEJA] error widget ocultar: {e!r}")

        def _widget_salir(icon, item):
            """Cierra por completo el widget flotante."""
            try:
                _widget_cmd("--salir")
                print("[BANDEJA] widget flotante: salir")
            except Exception as e:
                print(f"[BANDEJA] error widget salir: {e!r}")

        menu = pystray.Menu(
            pystray.MenuItem("💬 Abrir chat", _abrir_chat),
            pystray.MenuItem("🗣️ Widget flotante", pystray.Menu(
                pystray.MenuItem("👁️ Mostrar ventana", _widget_mostrar),
                pystray.MenuItem("🙈 Ocultar ventana", _widget_ocultar),
                pystray.MenuItem("⏹️ Cerrar widget", _widget_salir),
            )),
            pystray.MenuItem("🔄 Reiniciar JARVIS", _reiniciar),
            # Doble clic en el icono oculto de la barra = abrir Ajustes
            # (orden del señor Wáscar, 18/09/2026)
            pystray.MenuItem("⚙️ Ajustes", _ajustes, default=True),
            pystray.MenuItem("⏻ Cerrar completamente", _salir),
        )
        icono = pystray.Icon("jarvis", _imagen_icono(), "JARVIS - Asistente de servicio",
                             menu)
        icono.run()
    except Exception as e:
        print(f"[BANDEJA] no disponible: {e!r}")


async def _vigilante_typing(app):
    """Mantiene el indicador 'escribiendo...' de Telegram mientras el bot
    trabaja (independiente de los mensajes). Cuando deja de trabajar, deja
    de enviar y Telegram apaga el indicador solo."""
    while True:
        try:
            if _ocupado:
                await app.bot.send_chat_action(
                    chat_id=int(CHAT_ID), action="typing"
                )
        except Exception as e:
            print(f"[TYPER] error: {e!r}")
        await asyncio.sleep(4.5)


async def _arranque(app):
    """Tareas de arranque: vigilante del indicador + mensaje de bienvenida."""
    asyncio.create_task(_vigilante_typing(app))
    # Informar que el combo esta activo (la IA local legacy ya no existe)
    print(f"[MUSE] COMBO JARVIS ({MUSE_MODEL}) via OmniRoute activo (agente unico jarvis)")
    _reg_ok("omniroute_combo", detalle=f"combo activo: {MUSE_MODEL} (agente {MUSE_AGENT_JARVIS})")
    await enviar_mensaje_inicio(app)


def main():
    # Identidad de ventanas/barra de tareas (orden del senor Wascar 18/09/2026):
    # que Windows muestre el icono de JARVIS, no el de Python.
    _fijar_identidad_ventanas()
    # Cargar ajustes externos (config_jarvis.json) si existen: token, chat_id,
    # agente, modelo, timeout. Si no existe el archivo, se crea con los
    # valores por defecto del codigo (ventana Ajustes de la bandeja).
    _cargar_config()

    if TOKEN == "PEGAR_AQUI_EL_TOKEN_DEL_BOT" or CHAT_ID == "PEGAR_AQUI_TU_CHAT_ID":
        print("[ERROR] Tenes que configurar TOKEN y CHAT_ID en el script.")
        print("1) Crear bot en Telegram: @BotFather -> /newbot")
        print("2) Obtener tu CHAT_ID: @userinfobot o @getidsbot")
        return

    print("[JARVIS] Iniciando bot de Telegram...")

    # Lock de instancia unica (FIX 05/09/2026): antes se usaba SOLO un socket
    # con SO_REUSEADDR, que en Windows PERMITE binds duplicados -> dos bots a
    # la vez (eran posibles arranques dobles al encender la PC). Ahora:
    #  1) Mutex nombrado de Windows (robusto entre procesos, se libera solo si
    #     el proceso muere). Si alguien mas lo tiene -> ERROR_ALREADY_EXISTS.
    #  2) Socket de respaldo SIN SO_REUSEADDR (en Windows el segundo bind falla).
    global _lock_socket
    _mutex_lock = None
    try:
        import ctypes
        _kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        _mutex_lock = _kernel32.CreateMutexW(None, False,
                                             "Global\\JARVIS_TELEGRAM_BOT_9123")
        if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
            print("[ERROR] Ya hay otra instancia del bot corriendo. Esta se cierra.")
            _reg_error("instancia_doble", critico=True,
                       detalle="mutex 9123 ocupado: esta instancia se cierra sola")
            return
    except Exception:
        _mutex_lock = None  # sin ctypes: se confia en el socket de respaldo
    try:
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock_socket.bind(("127.0.0.1", PUERTO_LOCK))
    except OSError:
        print("[ERROR] Ya hay otra instancia del bot corriendo. Esta se cierra.")
        _reg_error("instancia_doble", critico=True,
                   detalle="puerto lock 9123 ocupado: esta instancia se cierra sola")
        if _mutex_lock is not None:
            try:
                _kernel32.CloseHandle(_mutex_lock)
            except Exception:
                pass
        return

    app = ApplicationBuilder().token(TOKEN).concurrent_updates(2).build()

    app.add_handler(CommandHandler("start", comando_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_texto))
    app.add_handler(
        MessageHandler(filters.VOICE | filters.AUDIO | filters.VIDEO_NOTE, manejar_voz)
    )
    app.add_handler(
        MessageHandler(filters.PHOTO | filters.Document.IMAGE, manejar_foto)
    )

    # Manejador global de errores: ningun fallo debe tumbar el bot
    app.add_error_handler(error_handler)

    # Icono de JARVIS en la bandeja del sistema (segundo plano, sin ventanas)
    threading.Thread(target=iniciar_bandeja, daemon=True).start()

    # Widget flotante de voz: se REINICIA junto con el bot (regla del señor Wáscar
    # 12/09/2026: el widget es parte del sistema de JARVIS Telegram y queda
    # como nuevo en cada arranque). Si ya habia una instancia vieja, se
    # cierra y se levanta una nueva; se conserva su estado visible/oculto.
    try:
        _widget_reiniciar()
        # Mensaje HONESTO (15/09/2026): si el widget esta neutralizado, no se
        # dice "arrancado" (el candado ya aviso de su neutralizacion).
        if not _widget_neutralizado():
            print("[JARVIS] Widget flotante arrancado con el sistema")
    except Exception as e:
        print(f"[JARVIS] error arrancando widget: {e!r}")

    # Iniciar hilo de consola
    hilo_consola(app)

    # Enviar mensaje de activacion al iniciar
    app.post_init = lambda app: asyncio.ensure_future(_arranque(app))

    print("[JARVIS] Bot corriendo. Esperando mensajes en Telegram...")
    # CAJA NEGRA: desde aqui queda anotado el arranque (PID, modelo, chat) y,
    # al salir, la parada con su motivo: si algo se corta, se ve en el registro.
    _reg("arranque", pid=os.getpid(), modelo=MUSE_MODEL, agente=MUSE_AGENT_JARVIS,
         chat=CHAT_ID, timeout=TIMEOUT_MUSE, timeout_pesado=TIMEOUT_PESADO)
    _reg_ok("arranque", detalle=f"bot en linea en Telegram (PID {os.getpid()})")
    try:
        # drop_pending_updates=True (pedido del señor Wáscar 01/09/2026): los mensajes
        # que llegaron mientras JARVIS estaba apagado se DESCARTAN al arrancar.
        # Solo se atienden mensajes nuevos a partir del inicio de esta instancia.
        # La memoria (cerebro, historial, pool de sesiones) vive en archivos
        # locales y NO se pierde: el descarte solo afecta a los updates colgados
        # en el servidor de Telegram.
        app.run_polling(drop_pending_updates=True)
    except Exception as e:
        _reg_error("bot_principal", detalle=repr(e), exc=e, critico=True)
        raise
    finally:
        _reg("parada", pid=os.getpid(), motivo="fin de run_polling")


if __name__ == "__main__":
    main()

