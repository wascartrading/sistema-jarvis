"""
texto_a_voz.py - Convierte texto a audio (nota de voz) de forma RAPIDA.

JARVIS (Telegram) usa este script cuando el jefe pide una respuesta en audio:
"responde en nota de voz", "dime un cuento en audio", "explícamelo hablado".

Motores (en orden):
  1) edge-tts  -> Microsoft Edge TTS, natural, es-MX, genera MP3 en segundos
     (requiere internet). Libreria ya instalada: edge-tts.
  2) pyttsx3   -> SAPI5 de Windows, OFFLINE, genera WAV al instante (respaldo
     si no hay internet o falla edge-tts).

Uso:
  python texto_a_voz.py "El texto a convertir"
  python texto_a_voz.py "El texto" --telegram        # genera y ENVIA nota de voz
  python texto_a_voz.py --texto "..." --salida "C:\\ruta\\audio.mp3"
  echo "texto largo..." | python texto_a_voz.py --stdin --telegram

La ruta del audio generado se imprime en la ultima linea (para que JARVIS lo
pueda capturar y reenviar).
"""
import argparse
import asyncio
import os
import sys
import tempfile
import time

# Forzar UTF-8 (acentos/emojis en consola de Windows)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

VOZ_EDGE = "es-MX-JorgeNeural"     # voz masculina natural (es-MX)
VOZ_PYTTSX3 = None                  # voz por defecto del sistema (SAPI5)

CARPETA_SALIDA = os.path.join(os.environ.get("TEMP", tempfile.gettempdir()),
                              "opencode")

TOKEN_TELEGRAM = "8306558302:AAFNm0IH6Hc-nldoLgYm6PzUZGXSAq0Vz54"
CHAT_ID_TELEGRAM = "8456515934"


def ruta_salida(nombre="voz_jarvis"):
    os.makedirs(CARPETA_SALIDA, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    return os.path.join(CARPETA_SALIDA, f"{nombre}_{stamp}.mp3")


def synth_edge(texto, salida):
    """Sintetiza con edge-tts (MP3, rapido, natural). Requiere internet."""
    import edge_tts

    async def _gen():
        tts = edge_tts.Communicate(texto, VOZ_EDGE)
        await tts.save(salida)

    asyncio.run(_gen())
    return os.path.exists(salida) and os.path.getsize(salida) > 0


def synth_pyttsx3(texto, salida_wav):
    """Sintetiza con pyttsx3 (SAPI5 de Windows, offline). Devuelve WAV."""
    import pyttsx3

    motor = pyttsx3.init()
    if VOZ_PYTTSX3:
        motor.setProperty("voice", VOZ_PYTTSX3)
    motor.setProperty("rate", 185)   # un poco mas rapido que el default
    motor.save_to_file(texto, salida_wav)
    motor.runAndWait()
    return os.path.exists(salida_wav) and os.path.getsize(salida_wav) > 0


def enviar_nota_voz(ruta_audio):
    """Envia el audio como NOTA DE VOZ por Telegram (sendVoice)."""
    try:
        import requests
    except Exception:
        print("[ERROR] falta requests para enviar por Telegram")
        return False
    url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendVoice"
    with open(ruta_audio, "rb") as f:
        resp = requests.post(
            url,
            files={"voice": f},
            data={"chat_id": CHAT_ID_TELEGRAM},
            timeout=120,
        )
    if resp.status_code == 200:
        print("[ENVIO] nota de voz enviada por Telegram.")
        return True
    # Respaldo: enviar como audio
    url2 = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendAudio"
    with open(ruta_audio, "rb") as f:
        resp2 = requests.post(
            url2,
            files={"audio": f},
            data={"chat_id": CHAT_ID_TELEGRAM},
            timeout=120,
        )
    if resp2.status_code == 200:
        print("[ENVIO] nota enviada como audio por Telegram.")
        return True
    print(f"[ERROR] fallo el envio: {resp.status_code} / {resp2.status_code}")
    return False


def main():
    parser = argparse.ArgumentParser(description="Texto a voz rapido (JARVIS)")
    parser.add_argument("texto", nargs="?", default="",
                        help="texto a convertir (o usar --stdin)")
    parser.add_argument("--texto", dest="texto_opt", default="",
                        help="texto alternativo")
    parser.add_argument("--stdin", action="store_true",
                        help="leer el texto desde stdin (textos largos)")
    parser.add_argument("--salida", default="",
                        help="ruta del audio generado (opcional)")
    parser.add_argument("--telegram", action="store_true",
                        help="enviar la nota de voz por Telegram al terminar")
    args = parser.parse_args()

    texto = args.texto_opt or args.texto or ""
    if args.stdin:
        texto = sys.stdin.read().strip()
    texto = texto.strip()
    if not texto:
        print("[ERROR] no hay texto que convertir")
        sys.exit(1)

    # Fragmentar textos muy largos (~4000 chars por nota) si se envia por
    # Telegram; si no, edge-tts genera todo junto sin problema.
    fragmentos = []
    max_chars = 4000
    for i in range(0, len(texto), max_chars):
        fragmentos.append(texto[i:i + max_chars])

    ultima_ruta = ""
    for idx, frag in enumerate(fragmentos, start=1):
        salida = args.salida or ruta_salida()
        if len(fragmentos) > 1:
            base, ext = os.path.splitext(salida)
            salida = f"{base}_{idx}{ext}"
        ok = False

        # 1) edge-tts (rapido, natural)
        try:
            ok = synth_edge(frag, salida)
        except Exception as e:
            print(f"[EDGE] no disponible: {e!r}")

        # 2) respaldo offline con pyttsx3
        if not ok:
            try:
                wav = salida.rsplit(".", 1)[0] + ".wav"
                if synth_pyttsx3(frag, wav):
                    salida = wav
                    ok = True
            except Exception as e:
                print(f"[PYTTSX3] no disponible: {e!r}")

        if not ok:
            print("[ERROR] no se pudo generar el audio")
            sys.exit(1)

        print(f"[OK] audio generado: {salida}")
        ultima_ruta = salida

        if args.telegram:
            enviar_nota_voz(salida)

    # Ultima linea = ruta del audio (para que JARVIS la capture)
    print(ultima_ruta)


if __name__ == "__main__":
    main()