# -*- coding: utf-8 -*-
"""
consola_chat_jarvis.py - Consola visible del chat de JARVIS Telegram
Creado por el Doctor 31/08/2026.

ABRE UNA VENTANA DE TERMINAL que muestra EN VIVO la conversacion de
Telegram (mensajes del jefe, estados y respuestas de JARVIS, tal como
fluyen por el bot en segundo plano) y permite ESCRIBIR mensajes que se
envian directamente al chat del jefe por la API de Telegram.

- Ve: sigue el log del bot (jarvis_bot_out.log) en tiempo real.
- Escribe: cualquier linea que escribas se envia al chat de JARVIS.
- Comandos: 'salir', 'exit' o 'quit' cierran la consola.
- Usa el TOKEN y CHAT_ID de config_jarvis.json (la ventana Ajustes).
"""
import json
import os
import sys
import threading
import time
import urllib.request
import urllib.parse

# --- Forzar UTF-8 en la consola (ventana cmd/powershell en Windows) ---
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PROYECTOS = r"C:\Users\wasc4\Documents\Sistema Jarvis\proyectos"
CONFIG_PATH = os.path.join(PROYECTOS, "config_jarvis.json")
LOG_PATH = os.path.join(os.environ.get("TEMP", os.environ.get("TMP", r"C:\Windows\Temp")),
                        "opencode", "jarvis_bot_out.log")

# Valores por defecto (si no hay config, no deberia pasar)
TOKEN = "8306558302:AAFNm0IH6Hc-nldoLgYm6PzUZGXSAq0Vz54"
CHAT_ID = "8456515934"


def cargar_config():
    """Lee config_jarvis.json si existe (token/chat_id editables)."""
    global TOKEN, CHAT_ID
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            if isinstance(cfg, dict):
                TOKEN = str(cfg.get("token", TOKEN))
                CHAT_ID = str(cfg.get("chat_id", CHAT_ID))
    except Exception as e:
        print(f"[CONSOLA] aviso: no pude leer config: {e!r}")


def enviar_telegram(texto):
    """Envia un mensaje al chat del jefe por la API de Telegram."""
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": CHAT_ID,
            "text": texto,
        }).encode("utf-8")
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=15) as r:
            r.read()
        return True
    except Exception as e:
        print(f"  [CONSOLA] error al enviar: {e!r}")
        return False


def hilo_ver_log():
    """Muestra en vivo el log del bot (mensajes del jefe, estados,
    respuestas). Espera a que el archivo exista si aun no se creo."""
    pos = 0
    esperado = 0.0
    while True:
        try:
            if not os.path.exists(LOG_PATH):
                time.sleep(1)
                continue
            tam = os.path.getsize(LOG_PATH)
            if tam < pos:
                pos = 0  # el log se roto/reinicio
            if tam > pos:
                with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(pos)
                    bloque = f.read()
                pos = f.tell()
                for linea in bloque.splitlines():
                    if linea.strip():
                        print(f"  {linea}")
                esperado = time.time()
        except Exception:
            pass
        time.sleep(0.4)


def main():
    cargar_config()
    print("=" * 60)
    print("  CONSOLA DEL CHAT - JARVIS Telegram")
    print("=" * 60)
    print("  Muestro en vivo la conversacion de Telegram.")
    print("  Escribi un mensaje y ENTER para enviarlo al chat.")
    print("  'salir' / 'exit' / 'quit' cierra esta consola.\n")

    threading.Thread(target=hilo_ver_log, daemon=True).start()

    try:
        while True:
            try:
                linea = input(">> ")
            except (EOFError, KeyboardInterrupt):
                print("\n[CONSOLA] cerrando...")
                break
            texto = linea.strip()
            if not texto:
                continue
            if texto.lower() in ("salir", "exit", "quit"):
                print("[CONSOLA] cerrando...")
                break
            print(f"  [PC -> Telegram] {texto}")
            enviar_telegram(texto)
    except Exception as e:
        print(f"[CONSOLA] error: {e!r}")


if __name__ == "__main__":
    main()