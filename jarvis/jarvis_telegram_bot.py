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
from datetime import datetime

# Forzar UTF-8 en la salida (consola/log): los emojis de los estados y
# respuestas no deben romper la codificacion cp1252 de Windows.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

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
# Historial y sesion para COMBO JARVIS via Opencode
HISTORIAL_MUSE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "historial_muse.json")
# Pool de sesiones rotativas: el bot oscila entre varias sesiones de opencode
# para que ninguna se llene de contexto (respuestas rapidas y sin degradar).
POOL_SESIONES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "pool_sesiones_jarvis.json")
MAX_SESIONES_POOL = 4          # maximo de sesiones en el pool
MSGS_MAX_POR_SESION = 10       # mensajes por sesion antes de rotar
MUSE_MAX_HISTORIAL = 40  # ampliado para recordar mas temas y permitir retomar
MUSE_HISTORIAL_INYECTAR = 8  # turnos inyectados (balance: memoria + velocidad)
MUSE_CHARS_POR_MENSAJE = 800  # chars por mensaje en el contexto inyectado
OPENCODE_CMD = "opencode"
TRANSCRIBIR_AUDIO_PATH = os.path.expanduser(
    r"~\Documents\Sistema Jarvis\Proyectos de asistente\manos\transcribir_audio.py"
)

# -------------------- CONFIG EXTERNA EDITABLE (VENTANA AJUSTES) --------------------
# El bot lee config_jarvis.json al arrancar (si no existe, lo crea con los
# valores por defecto de arriba). La ventana "Ajustes" de la bandeja edita
# este archivo: token, chat_id, agente, modelo y timeout. Los cambios se
# aplican al reiniciar JARVIS.
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "config_jarvis.json")

DEFAULT_CONFIG = {
    "token": TOKEN,
    "chat_id": CHAT_ID,
    "agente": MUSE_AGENT_JARVIS,
    "modelo": MUSE_MODEL,
    "timeout": 90,
    "autostart": True,
}
TIMEOUT_MUSE = DEFAULT_CONFIG["timeout"]


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
        TIMEOUT_MUSE = int(cfg.get("timeout", TIMEOUT_MUSE))
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

# Estado simple en memoria
ultimo_mensaje_recibido = None
lock = asyncio.Lock()
# Mensaje fallback cuando el combo no responde (filtrado si hubo actividad reciente)
FALLBACK_MUSE_MSG = "⚠️ Jefe, el combo JARVIS no me respondio en este momento. Intenta de nuevo en unos segundos."


# ------------------------------------------------------------------
# Estados en vivo del streaming de opencode (COMBO JARVIS)
# ------------------------------------------------------------------
MAP_ESTADOS = {
    "bash": "💻 Ejecutando en la terminal",
    "background_process": "💻 Ejecutando en la terminal",
    "read": "📖 Leyendo archivo",
    "write": "📝 Escribiendo archivo",
    "edit": "✏️ Editando archivo",
    "glob": "🔍 Buscando archivos",
    "grep": "🔎 Buscando en archivos",
    "list": "📂 Listando archivos",
    "webfetch": "🌐 Consultando en la web",
    "websearch": "🌐 Buscando en la web",
    "skill": "🛠️ Cargando habilidad",
    "task": "🤝 Delegando subtarea",
    "todowrite": "📋 Organizando el plan",
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
    return titulo


def _estado_de_evento(ev):
    """Convierte un evento json de opencode en un texto de estado con emoji (o None)."""
    tipo = ev.get("type", "")
    part = ev.get("part") or {}
    if tipo == "step_start":
        return "🧠 Pensando y trabajando..."
    if tipo == "tool_use":
        tool = part.get("tool") or ev.get("tool") or "?"
        base = MAP_ESTADOS.get(tool)
        if base is None:
            return "⚙️ Trabajando con %s" % tool
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


async def error_handler(update, context):
    """Captura cualquier error del bot y avisa al jefe sin morir."""
    print(f"[ERROR bot] {context.error!r}")
    try:
        if update and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ Perdón jefe, se me cayó algo por dentro. Intenta de nuevo.")
    except Exception:
        pass


def responder_jarvis(prompt: str, on_estado=None, on_texto=None,
                   timeout: int = 240) -> str:
    """Envia el prompt a JARVIS via COMBO JARVIS (OmniRoute) y devuelve la
    respuesta. Si el combo no responde, devuelve el fallback de mayordomo."""
    try:
        # MODO COMBO JARVIS via OmniRoute (ACTUAL): UNICA CONEXION
        if MODO_MUSE:
            rta_muse = responder_muse(prompt, on_estado, on_texto, timeout)
            if rta_muse:
                return rta_muse
            print("[MUSE] el combo no respondio, no hay fallback (solo COMBO JARVIS activo)")
            return FALLBACK_MUSE_MSG
        return FALLBACK_MUSE_MSG
    except subprocess.TimeoutExpired:
        return "⏱️ JARVIS tardó demasiado, jefe. Intenta de nuevo."
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
    """Devuelve la sesion mas reciente del pool que aun tiene espacio
    (msgs < limite). None si todas estan llenas (se creara una nueva)."""
    for s in reversed(pool):
        if (s.get("msgs") or 0) < MSGS_MAX_POR_SESION:
            return s
    return None


def _registrar_mensaje_pool(pool, sid):
    """Suma un mensaje a la sesion dada (o la agrega al pool). Recorta el
    pool al maximo de sesiones."""
    if not sid:
        return pool
    for s in pool:
        if s.get("sid") == sid:
            s["msgs"] = (s.get("msgs") or 0) + 1
            return pool[-MAX_SESIONES_POOL:]
    pool.append({"sid": sid, "msgs": 1})
    return pool[-MAX_SESIONES_POOL:]


def _limpiar_contenido_historial(texto: str) -> str:
    """Si un mensaje quedo guardado con el envoltorio 'Contexto previo... --- Nuevo mensaje', extrae solo el mensaje real."""
    if not texto:
        return texto
    if "---\nNuevo mensaje del jefe:" in texto:
        return texto.split("---\nNuevo mensaje del jefe:")[-1].strip()
    if texto.startswith("Contexto previo:") and "Nuevo mensaje del jefe:" in texto:
        return texto.split("Nuevo mensaje del jefe:")[-1].strip()
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
                # limite por entrada 2200 chars para no inflar el archivo
                normalizado.append({"role": r, "content": c[:2200]})
        with open(HISTORIAL_MUSE_PATH, "w", encoding="utf-8") as f:
            json.dump(normalizado[-MUSE_MAX_HISTORIAL:], f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _ejecutar_opencode(args, on_estado, on_texto, timeout):
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
        # matarlo al instante (el jefe manda el comando mientras trabaja).
        global _proceso_activo, _interrumpido_por_jefe
        _proceso_activo = proc
        # Estado inicial inmediato (se envia siempre, no cuenta como actividad)
        # FIX INTERRUPCION: si el jefe ya interrumpio, no enviar estados ni
        # lanzar el proceso: se sale limpio y en silencio.
        if _interrumpido_por_jefe:
            print("[MUSE] interrumpido antes de lanzar: salida limpia")
            try:
                proc.kill()
            except Exception:
                pass
            return "", None, "INTERRUMPIDO"
        if on_estado:
            try:
                on_estado("🛰️ Consultando a COMBO JARVIS via OmniRoute...")
            except Exception:
                pass

        # Estado compartido entre el hilo lector y el vigilante principal
        compartido = {
            "ultima_actividad": time.time(),
            "texto_pendiente": [],
            "session_id": None,
            "ultimo_estado": None,
            "ultimo_texto": None,
            "ultimo_envio": 0.0,
            "lector_terminado": False,
            "matado_por_timeout": False,
        }
        tope_duro = max(timeout * 4, 600)

        def _lector():
            """Hilo UNICO que lee stdout del proceso (sin que nadie mas lo
            toque). Acumula texto y estados en vivo; no mata nada."""
            try:
                for linea in proc.stdout:
                    linea = linea.strip()
                    compartido["ultima_actividad"] = time.time()
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
                    # Estados en vivo con throttling 2s y latido 15s.
                    # FIX DOBLE ESTADO (01/09/2026): nunca se repite el mismo
                    # texto de estado dos veces seguidas (el latido ya no
                    # reenvia "Pensando..." si ese texto ya se mostro, y el
                    # primer step_start no reenvia el placeholder del latido).
                    if on_estado:
                        ahora = time.time()
                        est = _estado_de_evento(ev)
                        if est and est != compartido["ultimo_estado"] and est != compartido["ultimo_texto"]:
                            if compartido["ultimo_estado"] is None or ahora - compartido["ultimo_envio"] >= 2.0:
                                try:
                                    on_estado(est)
                                except Exception:
                                    pass
                                compartido["ultimo_estado"] = est
                                compartido["ultimo_texto"] = est
                                compartido["ultimo_envio"] = ahora
                        elif ahora - compartido["ultimo_envio"] >= 15:
                            # Latido: informar aunque el proceso trabaje callado,
                            # pero solo si ese texto no se envio ya (nada de
                            # dos "Pensando y trabajando..." consecutivos).
                            texto_latido = compartido["ultimo_estado"] or "🧠 Pensando y trabajando..."
                            if compartido["ultimo_texto"] != texto_latido:
                                try:
                                    on_estado(texto_latido)
                                except Exception:
                                    pass
                                compartido["ultimo_texto"] = texto_latido
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
        # proceso mientras el lector lee. Solo mata si hay mudez real o si el
        # jefe pulsa /interrumpir (freno de emergencia).
        t0 = time.time()
        while not compartido["lector_terminado"]:
            if _interrumpido_por_jefe:
                try:
                    proc.kill()
                except Exception:
                    pass
                break
            if time.time() - compartido["ultima_actividad"] > timeout:
                compartido["matado_por_timeout"] = True
                try:
                    proc.kill()
                except Exception:
                    pass
                break
            if time.time() - t0 > tope_duro:
                compartido["matado_por_timeout"] = True
                try:
                    proc.kill()
                except Exception:
                    pass
                break
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
        _proceso_activo = None
        return respuesta, compartido["session_id"], stderr or ""
    except Exception as e:
        _proceso_activo = None
        return "", None, str(e)


def responder_muse(prompt: str, on_estado=None, on_texto=None, timeout: int = 0) -> str | None:
    """JARVIS con COMBO JARVIS via Opencode - memoria conversacional robusta (cambia de tema y retoma sin olvidar)."""
    try:
        # Timeout configurable desde la ventana Ajustes (TIMEOUT_MUSE).
        # Si no se pasa, usa el valor del archivo config_jarvis.json.
        timeout = TIMEOUT_MUSE if timeout <= 0 else min(timeout, TIMEOUT_MUSE)
        agente = MUSE_AGENT_JARVIS
        prompt_original = (prompt or "").strip()
        if not prompt_original:
            return None
        hist = _cargar_historial_muse()
        # Construir contexto amplio y limpio (ultimos N mensajes, sin envoltorios)
        contexto = ""
        if hist:
            # hist ya viene limpio por _cargar_historial_muse
            recientes = hist[-MUSE_HISTORIAL_INYECTAR:]
            for h in recientes:
                r = h.get("role", "")
                c = _limpiar_contenido_historial(h.get("content", ""))[:MUSE_CHARS_POR_MENSAJE]
                if r and c:
                    # Etiquetas claras para que el modelo distinga
                    if r == "user":
                        contexto += f"Jefe: {c}\n"
                    else:
                        contexto += f"JARVIS: {c}\n"
            # Nota de instruccion al modelo para que recuerde
            if contexto:
                contexto = ("Memoria conversacional (ultimos temas con el jefe, recuerda y retoma si te pide 'volvamos al tema anterior' o similar):\n"
                            + contexto)
        if contexto:
            prompt_para_modelo = f"{contexto}\n---\nNuevo mensaje del jefe (responde considerando la memoria si hace falta retomar un tema): {prompt_original}"
        else:
            prompt_para_modelo = prompt_original
        # Pool de sesiones rotativas: elegir la sesion activa del pool
        # (la mas reciente con espacio) o ninguna (se creara una nueva).
        pool = _cargar_pool_sesiones()
        activa = _sesion_activa_pool(pool)
        sid_activo = activa.get("sid") if activa else None
        args = [OPENCODE_CMD, "run", "--agent", agente, "--model", MUSE_MODEL]
        if sid_activo:
            args += ["--session", sid_activo]
        args += ["--format", "json", prompt_para_modelo]
        print(f"[MUSE] agente={agente} modelo={MUSE_MODEL} sid_activo={sid_activo} pool={len(pool)} prompt_original={len(prompt_original)} prompt_modelo={len(prompt_para_modelo)} historial={len(hist)} timeout={timeout}...")
        # El estado inicial "Consultando..." lo envia _ejecutar_opencode
        # (estado inicial inmediato). Aqui NO se repite para que el jefe no
        # lo vea doble por Telegram (fix 31/08/2026).
        # REINTENTO AUTOMATICO (fix 31/08/2026): si la primera llamada sale
        # muda o con timeout, se reintenta UNA vez con sesion nueva (sin
        # --session) antes de rendirse. El combo a veces falla en frio.
        # FIX INTERRUPCION (31/08/2026): si el jefe pulso Interrumpir, NO se
        # reintenta ni se lanza ningun proceso nuevo.
        respuesta, sid_visto, stderr = _ejecutar_opencode(args, on_estado, on_texto, timeout)
        if not respuesta and _interrumpido_por_jefe:
            print("[MUSE] interrumpido por el jefe: no se reintenta")
            return None
        if not respuesta:
            print(f"[MUSE] 1er intento sin respuesta (stderr={str(stderr)[:120]}), reintentando con sesion nueva...")
            if _interrumpido_por_jefe:
                print("[MUSE] interrumpido por el jefe: reintento cancelado")
                return None
            if on_estado:
                try: on_estado("🔄 Reintentando con conexión fresca, jefe...")
                except: pass
            args_retry = [OPENCODE_CMD, "run", "--agent", agente, "--model", MUSE_MODEL,
                          "--format", "json", prompt_para_modelo]
            respuesta, sid_visto, stderr = _ejecutar_opencode(args_retry, on_estado, on_texto, timeout)
            if respuesta:
                print("[MUSE] reintento OK")
        # Registrar el mensaje en el pool (rotacion: las sesiones llenas se
        # dejan de usar y se crean/rotan otras; el historial local conserva
        # la memoria conversacional).
        sid_final = sid_visto or sid_activo
        if sid_final:
            pool = _registrar_mensaje_pool(pool, sid_final)
            _guardar_pool_sesiones(pool)
            print(f"[MUSE] pool actualizado: {len(pool)} sesiones, activa={sid_final[:20]}...")
        if "TIMEOUT" in (stderr or ""):
            print("[MUSE] timeout")
            # Sesion posiblemente danada: expulsarla del pool para que la
            # proxima llamada use otra sesion sana o cree una nueva.
            if sid_final:
                pool = [s for s in pool if s.get("sid") != sid_final]
                _guardar_pool_sesiones(pool)
                print(f"[MUSE] sesion danada expulsada del pool: {sid_final[:20]}... (quedan {len(pool)})")
            return "⏰ El combo JARVIS tardo demasiado, jefe. Intenta de nuevo."
        if respuesta:
            try:
                # Guardar SIEMPRE el mensaje limpio original, no el envoltorio
                hist.append({"role": "user", "content": prompt_original[:2200]})
                hist.append({"role": "assistant", "content": _limpiar_contenido_historial(respuesta)[:2200]})
                _guardar_historial_muse(hist)
            except: pass
            print(f"[MUSE] respuesta OK {len(respuesta)} chars")
            return respuesta
        print(f"[MUSE] sin respuesta stderr={stderr[:400]}")
        # Sin respuesta y sin stderr claro: la sesion puede estar danada.
        # Expulsarla del pool tambien (no reutilizar sesiones mudas).
        if sid_final and not stderr:
            pool = [s for s in pool if s.get("sid") != sid_final]
            _guardar_pool_sesiones(pool)
            print(f"[MUSE] sesion muda expulsada del pool: {sid_final[:20]}... (quedan {len(pool)})")
        if "No payment" in (stderr or "") or "CreditsError" in (stderr or ""):
            return "El combo JARVIS esta sin creditos, jefe. Revisa el billing de OmniRoute."
        if stderr:
            return f"El combo JARVIS no respondio: {stderr[:200]}"
        return None
    except Exception as e:
        print(f"[MUSE] error {e!r}")
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
# Mensajes de inicio rotativos (10 variantes creadas por orden del jefe
# 03/09/2026): cada arranque del bot saluda con una variante diferente,
# rotando en orden hasta agotarlas y volviendo a empezar.
MENSAJES_INICIO = [
    ("🚀 ¡Hola jefe! Ya estamos disponibles de este lado. "
     "Soy JARVIS, la fusión completa: voz, memoria y manos "
     "listas con el combo COMBO JARVIS vía OmniRoute. "
     "Rápido y elegante como siempre. ¿Qué hacemos hoy?"),
    ("✨ ¡Hola jefe! JARVIS al servicio: ya despierto y en su puesto. "
     "Voz, memoria y manos listas con el combo COMBO JARVIS vía OmniRoute. "
     "A punto y sin espera. ¿Por dónde empezamos?"),
    ("🛎️ ¡Hola jefe! JARVIS presente, de vuelta y mejor que nunca. "
     "La fusión completa en línea con el combo COMBO JARVIS vía OmniRoute. "
     "Rápido, elegante y a su orden. ¿Qué necesitamos resolver hoy?"),
    ("🎯 ¡Hola jefe! Los sistemas están en verde y JARVIS en su sitio: "
     "voz, memoria y manos con el combo COMBO JARVIS vía OmniRoute. "
     "Preciso y sin rodeos. ¿Cuál es el plan de hoy?"),
    ("🌟 ¡Hola jefe! Ya me tiene de vuelta, con todo listo de este lado. "
     "La fusión completa encendida con el combo COMBO JARVIS vía OmniRoute. "
     "A su servicio, rápido como siempre. ¿Qué hacemos hoy?"),
    ("🔔 ¡Hola jefe! JARVIS reportándose: todo listo y al 100 %. "
     "Voz, memoria y manos conectadas con el combo COMBO JARVIS vía OmniRoute. "
     "Elegante y puntual como siempre. ¿En qué seguimos?"),
    ("⚡ ¡Hola jefe! Ya arranqué y quedo a su disposición. "
     "La fusión completa en marcha con el combo COMBO JARVIS vía OmniRoute. "
     "Rápido, directo y sin fallas. ¿Qué me ordena hoy?"),
    ("👔 ¡Hola jefe! Buen estado y sistema en línea: JARVIS con voz, memoria "
     "y manos preparadas, todo con el combo COMBO JARVIS vía OmniRoute. "
     "A su entera disposición. ¿Qué toca hoy?"),
    ("🌐 ¡Hola jefe! De nuevo en línea y con los motores calientes. "
     "La fusión completa operativa con el combo COMBO JARVIS vía OmniRoute. "
     "Listo para trabajar con estilo. ¿Qué hacemos primero?"),
    ("🚪 ¡Hola jefe! Abriendo puertas y listo para servir. "
     "JARVIS con voz, memoria y manos alineadas con el combo "
     "COMBO JARVIS vía OmniRoute. A la orden, jefe. ¿Qué hacemos hoy?"),
]

# Mensajes de "leyendo tu mensaje" rotativos (10 variantes creadas por orden
# del jefe 03/09/2026): cada mensaje del jefe muestra una variante diferente,
# rotando en orden hasta agotarlas y volviendo a empezar.
MENSAJES_LECTURA = [
    "👀 Dame un momento, jefe, estoy leyendo tu mensaje...",
    "📖 Recibido, jefe. Un momento, estoy procesando tu mensaje...",
    "🤔 Ya lo tengo, jefe. Déjame leer bien tu mensaje...",
    "⏳ Recibido al instante, jefe. Estoy analizando tu mensaje...",
    "📨 Mensaje en mano, jefe. Un segundo, lo estoy leyendo...",
    "🧐 Anotado, jefe. Estoy leyendo tu mensaje con atención...",
    "⚙️ Procesando, jefe. Un momento mientras leo tu mensaje...",
    "💬 Ya me llegó, jefe. Estoy leyendo tu mensaje...",
    "🔍 Recibido y en análisis, jefe. Un momento, estoy leyendo tu mensaje...",
    "🗂️ Recibido, jefe. Estoy leyendo tu mensaje y preparando la respuesta...",
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

# Boton de emergencia del jefe (/interrumpir): permite frenar a JARVIS
# en mitad de una tarea. La bandera la revisa el vigilante de opencode para
# matar el proceso en curso; el proceso activo queda registrado aqui para
# poder matarlo de inmediato desde el handler de Telegram.
_interrumpido_por_jefe = False
_proceso_activo = None


async def _procesar_mensaje(texto, chat_id, context):
    """Procesa un mensaje completo contra JARVIS (confirmacion, estados,
    respuesta). Usa send_message al chat (no reply) para poder atender
    mensajes encolados."""
    # Confirmacion instantanea: el jefe siempre ve que el bot recibio la orden
    await context.bot.send_message(
        chat_id=chat_id, text=_siguiente_mensaje_lectura(),
        reply_markup=_teclado_interrumpir(),
    )

    # Renovar la conversacion cuando el jefe lo pida
    texto_bajo = texto.lower().strip()

    # Comando despierta: JARVIS siempre esta activo con COMBO JARVIS. La
    # respuesta es confirmacion (la IA local legacy ya no existe).
    if any(f in texto_bajo for f in ("despierta a muse", "despierta a spark", "despierta a opencode",
                                      "despierta a la ia local", "despierta a la ia", "despierta a ella",
                                      "despierta", "activa a muse", "activa muse", "despierta a jarvis muse")):
        await context.bot.send_message(
            chat_id=chat_id,
            text="✨ Listo jefe, JARVIS activo con el combo COMBO JARVIS vía OmniRoute, ya estoy con toda la potencia. Dime qué hacemos."
        )
        print("[MUSE] despertado por comando despierta")
        return

    # Pregunta sobre el modelo activo: responder con el estado real
    if any(f in texto_bajo for f in ("con que modelo", "con qué modelo",
                                     "que modelo eres", "qué modelo eres",
                                     "estas trabajando con", "estás trabajando con",
                                     "que modelo estas", "qué modelo estás",
                                     "modelo estas usando", "modelo estás usando",
                                     "con que ia", "con qué ia")):
        rta_modelo = ("Estoy trabajando con el combo COMBO JARVIS "
                      "vía OmniRoute (omniroute/COMBO JARVIS), con el agente "
                      "doctor de opencode, herramientas y estados en vivo.")
        await context.bot.send_message(chat_id=chat_id, text=rta_modelo)
        print("[MODELO] consulta: COMBO JARVIS via OmniRoute")
        return

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
            text="🧹 Listo, jefe. Conversación nueva: empiezo de cero, sin historial y con sesiones frescas."
        )
        print("[SESION] conversacion renovada por pedido del jefe")
        return

    # Marcar como escribiendo...
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    # Estados en vivo por Telegram (no congelan el bot) + tracking de actividad
    # para filtrar el fallback "no me respondio" cuando SI hubo actividad REAL.
    # Los estados automaticos ("Consultando..." / "Pensando y trabajando...") se envian
    # SIEMPRE aunque el modelo falle: NO cuentan como actividad (fix 31/08/2026).
    loop_bot = asyncio.get_running_loop()
    actividad = {"estados": 0, "textos": 0, "ultimo_ts": 0.0}
    ESTADOS_AUTOMATICOS = ("🛰️ Consultando a", "Consultando a", "🧠 Pensando", "🔄 Reintentando")

    def on_estado(estado):
        if estado and not estado.startswith(ESTADOS_AUTOMATICOS):
            actividad["estados"] += 1
            actividad["ultimo_ts"] = time.time()
        app = context.application
        try:
            loop_bot.call_soon_threadsafe(
                lambda: asyncio.ensure_future(
                    app.bot.send_message(chat_id=chat_id, text=estado)
                )
            )
            print(f"[ESTADO->TG] {estado}")
        except Exception as e:
            print(f"[ERROR estado->TG] {e!r}")

    # Textos intermedios del asistente: se envian EN VIVO con prefijo.
    # FIX EMOJI SUELTO (01/09/2026): nunca enviar "🗣️" solo. Si el texto
    # intermedio llega vacio o con espacios se descarta (Telegram lo
    # mostraria como emoji gigante e innecesario); el emoji siempre va
    # al INICIO del comentario (prefijo), nunca suelto.
    def on_texto(texto):
        if not texto or not texto.strip():
            print("[TEXTO->TG] descartado (vacio/espacios)")
            return
        actividad["textos"] += 1
        actividad["ultimo_ts"] = time.time()
        app = context.application
        try:
            for parte in dividir_respuesta(texto):
                if not parte.strip():
                    continue
                loop_bot.call_soon_threadsafe(
                    lambda p=parte: asyncio.ensure_future(
                        app.bot.send_message(
                            chat_id=chat_id, text=f"🗣️ {p}"
                        )
                    )
                )
            print(f"[TEXTO->TG] {texto[:120]}")
        except Exception as e:
            print(f"[ERROR texto->TG] {e!r}")

    # Consultar a JARVIS (en hilo para no congelar el bot mientras piensa)
    respuesta = await asyncio.to_thread(responder_jarvis, texto, on_estado, on_texto)

    # FILTRO ANTI-SPAM FALLBACK: si Muse devolvio el fallback pero SI hubo
    # estados o textos en vivo, significa que SI estaba respondiendo/trabajando.
    # En ese caso NO mostrar el mensaje confuso, jefe lo pidio asi.
    # FIX INTERRUPCION: si el jefe interrumpio, NO enviar "Sigo en ello":
    # el freno ya se confirmo con el mensaje de Interrumpido.
    if _interrumpido_por_jefe:
        print("[INTERRUMPIR] respuesta/fallback descartados por freno del jefe")
        return

    es_fallback = (
        respuesta == FALLBACK_MUSE_MSG
        or respuesta == "⏰ El combo JARVIS tardo demasiado, jefe. Intenta de nuevo."
        or respuesta.startswith("El combo JARVIS no respondio")
    )
    if es_fallback:
        hubo_actividad = actividad["estados"] > 0 or actividad["textos"] > 0
        reciente = (time.time() - actividad["ultimo_ts"]) < 30 if actividad["ultimo_ts"] else False
        if hubo_actividad or reciente:
            print(f"[FILTRO FALLBACK] Suprimido, con cierre: hubo actividad estados={actividad['estados']} textos={actividad['textos']} (reciente={reciente}) respuesta={respuesta[:80]}")
            # NUNCA dejar al jefe en silencio: cierre de mayordomo breve.
            # Si hubo trabajo real (estados/textos), se avisa que sigue en ello
            # y se pide reenvio si el informe no llego.
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Sigo en ello, jefe: terminé de procesar y te doy el informe ya mismo. Si no llega en unos segundos, reenvíame el mensaje y te lo completo."
                )
            except Exception as e:
                print(f"[ERROR cierre fallback] {e!r}")
            return

    partes = dividir_respuesta(limpiar_respuesta(respuesta))
    print(f"[JARVIS] {partes[0][:200]}... ({len(partes)} parte/s)")

    for i, parte in enumerate(partes):
        if len(partes) > 1:
            parte = f"📄 Parte {i + 1} de {len(partes)}\n\n{parte}"
        await context.bot.send_message(chat_id=chat_id, text=parte,
                                       reply_markup=_teclado_interrumpir())


async def manejar_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes de texto: si el bot esta ocupado, avisa y encola;
    si no, procesa y luego atiende la cola en orden."""
    if update.effective_chat.id != int(CHAT_ID):
        await update.message.reply_text("🚫 No tengo autorización para hablar con vos.")
        return

    texto = update.message.text
    chat_id = update.effective_chat.id
    hora = datetime.now().strftime("%H:%M:%S")
    print(f"\n[Telegram] Jefe ({hora}): {texto}")

    # TECLADO NATIVO (fix 31/08/2026): si el mensaje es EXACTAMENTE el texto
    # de un boton del menu, se intercepta aqui y se ejecuta como SISTEMA
    # PURO: el modelo nunca lo procesa. Si el jefe MENCIONA "interrumpir" o
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
        # El bot esta trabajando: aviso de mayordomo y el mensaje se encola
        _cola_mensajes.append(texto)
        await update.message.reply_text(
            "⏳ Un momento, jefe. En cuanto acabe con este trabajo, "
            "leo tu próximo mensaje y trabajo con él.",
            reply_markup=_teclado_interrumpir(),
        )
        print(f"[COLA] mensaje encolado ({len(_cola_mensajes)} en espera)")
        return

    global _interrumpido_por_jefe
    _interrumpido_por_jefe = False
    _ocupado = True
    try:
        await _procesar_mensaje(texto, chat_id, context)
    finally:
        _ocupado = False
        # Atender la cola en orden, uno a la vez
        while _cola_mensajes:
            siguiente = _cola_mensajes.pop(0)
            _ocupado = True
            await context.bot.send_message(
                chat_id=chat_id,
                text="✅ OK, ahora sí, jefe. Pasemos con el siguiente mensaje que me enviaste."
            )
            print(f"[COLA] procesando siguiente ({len(_cola_mensajes)} restantes)")
            await _procesar_mensaje(siguiente, chat_id, context)
            _ocupado = False


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
    await update.message.reply_text("🎧 Dame un momento, jefe, estoy escuchando tu nota...")

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

    # Si el bot esta ocupado, avisar y encolar la transcripcion
    global _ocupado
    if _ocupado:
        _cola_mensajes.append(texto)
        await update.message.reply_text(
            "⏳ Un momento, jefe. En cuanto acabe con este trabajo, "
            "leo tu próximo mensaje y trabajo con él.",
            reply_markup=_teclado_interrumpir(),
        )
        print(f"[COLA] nota de voz encolada ({len(_cola_mensajes)} en espera)")
        return

    _ocupado = True
    try:
        await _procesar_mensaje(texto, update.effective_chat.id, context)
    finally:
        _ocupado = False
        while _cola_mensajes:
            siguiente = _cola_mensajes.pop(0)
            _ocupado = True
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="✅ OK, ahora sí, jefe. Pasemos con el siguiente mensaje que me enviaste."
            )
            print(f"[COLA] procesando siguiente ({len(_cola_mensajes)} restantes)")
            await _procesar_mensaje(siguiente, update.effective_chat.id, context)
            _ocupado = False


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
        "✅ JARVIS activo. Escribime, mándame una nota de voz o usa el "
        "botón Interrumpir si necesitas frenarme en seco.",
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
    AL INSTANTE, vacia la cola y deja al jefe libre. El modelo no participa."""
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

    print("[MENU:INTERRUMPIR] freno activado por boton del jefe")
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="🚫 Interrumpido, jefe. Suelto lo que estaba haciendo y quedo "
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
            text="🔄 Reiniciando JARVIS, jefe. En unos segundos vuelvo limpio: "
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
    except Exception as e:
        print(f"[MENU:REINICIAR] error al lanzar reinicio: {e!r}")


def hilo_consola(app):
    """Hilo secundario para enviar mensajes desde la consola hacia Telegram."""

    def loop_consola():
        print("[Consola] Escribi mensajes para enviarselos al jefe por Telegram.")
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


def _abrir_ventana_ajustes():
    """Ventana de AJUSTES de JARVIS Telegram: permite modificar el agente,
    el token de Telegram (ya preestablecido), el chat_id, el modelo y el
    timeout. Guarda en config_jarvis.json; los cambios aplican al reiniciar.
    Se abre en un hilo propio para no bloquear el icono de la bandeja."""
    import threading

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
        # (la misma lista de agentes primarios que usa OpenCode). El jefe
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
        entry_timeout.insert(0, str(valores.get("timeout", 90)))
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

        # Estado de aplicacion
        lbl_estado = ttk.Label(frm, text="", foreground="#16a34a")
        lbl_estado.grid(row=7, column=0, columnspan=2, sticky="w", pady=(6, 0))

        # --- Panel de clic derecho (Copiar / Pegar / Cortar / Seleccionar) en
        # los campos de texto (habilitado por el jefe 01/09/2026) ---
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
            entry_timeout.insert(0, str(DEFAULT_CONFIG.get("timeout", 90)))
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
                try:
                    timeout = int(entry_timeout.get().strip() or "90")
                except ValueError:
                    timeout = 90
                if not token or not chat:
                    lbl_estado.config(text="⚠️ Token y Chat ID son obligatorios",
                                      foreground="#dc2626")
                    return
                datos = {
                    "token": token,
                    "chat_id": chat,
                    "agente": agente,
                    "modelo": modelo,
                    "timeout": timeout,
                    "autostart": bool(var_autostart.get()),
                }
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
        # jefe 01/09/2026). "Cerrar" SOLO cierra esta ventana de Ajustes;
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

    threading.Thread(target=_run_tk, daemon=True).start()


def iniciar_bandeja():
    """Icono de JARVIS en la bandeja del sistema (iconos ocultos), en un hilo.
    Menu: abrir chat de JARVIS, reiniciar, AJUSTES, salir."""
    try:
        import pystray
        from PIL import Image, ImageDraw, ImageFont

        def _imagen_icono():
            # Icono JARVIS estilo arc reactor con la J (diseno 31/08/2026)
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
            hilo real de la conversacion (mensajes del jefe, herramientas,
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

        menu = pystray.Menu(
            pystray.MenuItem("💬 Abrir chat", _abrir_chat),
            pystray.MenuItem("🔄 Reiniciar JARVIS", _reiniciar),
            pystray.MenuItem("⚙️ Ajustes", _ajustes),
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
    await enviar_mensaje_inicio(app)


def main():
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

    # Lock de instancia unica: si ya hay otro bot corriendo, esta instancia sale
    global _lock_socket
    try:
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        _lock_socket.bind(("127.0.0.1", PUERTO_LOCK))
    except OSError:
        print("[ERROR] Ya hay otra instancia del bot corriendo. Esta se cierra.")
        return

    app = ApplicationBuilder().token(TOKEN).concurrent_updates(2).build()

    app.add_handler(CommandHandler("start", comando_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_texto))
    app.add_handler(
        MessageHandler(filters.VOICE | filters.AUDIO | filters.VIDEO_NOTE, manejar_voz)
    )

    # Manejador global de errores: ningun fallo debe tumbar el bot
    app.add_error_handler(error_handler)

    # Icono de JARVIS en la bandeja del sistema (segundo plano, sin ventanas)
    threading.Thread(target=iniciar_bandeja, daemon=True).start()

    # Iniciar hilo de consola
    hilo_consola(app)

    # Enviar mensaje de activacion al iniciar
    app.post_init = lambda app: asyncio.ensure_future(_arranque(app))

    print("[JARVIS] Bot corriendo. Esperando mensajes en Telegram...")
    # drop_pending_updates=True (pedido del jefe 01/09/2026): los mensajes
    # que llegaron mientras JARVIS estaba apagado se DESCARTAN al arrancar.
    # Solo se atienden mensajes nuevos a partir del inicio de esta instancia.
    # La memoria (cerebro, historial, pool de sesiones) vive en archivos
    # locales y NO se pierde: el descarte solo afecta a los updates colgados
    # en el servidor de Telegram.
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
