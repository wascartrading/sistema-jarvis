"""
Envia un archivo de audio a Telegram usando el bot de Wally.
Uso: python enviar_audio_telegram.py [ruta_al_audio]
Si no se pasa ruta, usa audio_test.wav por defecto.
"""
import sys
import os
import requests

TOKEN = "8306558302:AAFNm0IH6Hc-nldoLgYm6PzUZGXSAq0Vz54"
CHAT_ID = "8456515934"

# Audio por defecto (04/09/2026 KIT PORTATIL: ruta derivada de este script)
AUDIO_DEFAULT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "audio_test.wav"
)

def enviar_audio(ruta_audio: str):
    if not os.path.isfile(ruta_audio):
        print(f"[ERROR] No existe el archivo: {ruta_audio}")
        return False

    url = f"https://api.telegram.org/bot{TOKEN}/sendAudio"
    files = {"audio": open(ruta_audio, "rb")}
    data = {"chat_id": CHAT_ID, "caption": "Aqui tienes el audio, jefe."}

    print(f"[WALLY] Enviando audio: {ruta_audio}")
    resp = requests.post(url, files=files, data=data, timeout=60)
    files["audio"].close()

    if resp.status_code == 200:
        print("[WALLY] Audio enviado correctamente por Telegram.")
        return True
    else:
        print(f"[ERROR] Fallo el envio: {resp.status_code} - {resp.text}")
        return False

if __name__ == "__main__":
    ruta = sys.argv[1] if len(sys.argv) > 1 else AUDIO_DEFAULT
    enviar_audio(ruta)
