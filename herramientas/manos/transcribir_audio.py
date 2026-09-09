# -*- coding: utf-8 -*-
"""transcribir_audio.py - convierte una nota de voz (archivo de audio) a texto.

Es la "oreja" de JARVIS para las notas de voz que llegan por Telegram
(20/08/2026, regla del usuario): el usuario manda un audio por Telegram y
JARVIS lo transcribe y responde por ahi.

Motores, en orden de prioridad:
1. faster-whisper (moderno, buena precision en espanol): el modelo se
   descarga en el PRIMER uso desde HuggingFace (puede tardar unos minutos
   segun la conexion) y queda cacheado en ~/.cache/huggingface.
2. vosk (offline): solo como respaldo y solo si hay un modelo de vosk en
   disco (faster-whisper es el camino normal).

Variables de entorno:
- JARVIS_WHISPER_MODEL: modelo Whisper (tiny|base|small|medium). Por defecto
  'small' = buen equilibrio velocidad/precision en espanol.

Uso desde la linea de comandos:
    python manos/transcribir_audio.py ruta_del_audio.ogg
Imprime el texto por stdout (nada si no se pudo transcribir).

Nunca lanza: cualquier problema devuelve None (y deja la causa en stderr).
"""
import os
import sys

MODELO_WHISPER = os.environ.get('JARVIS_WHISPER_MODEL', 'small')
IDIOMA = 'es'
VOSK_CARPETAS = ('vosk-model-small-es-0.42', 'vosk-model-es-0.42')

_MODELO_WHISPER_CACHE = None  # el modelo se carga una sola vez (es costoso)


def transcribir(ruta, idioma=None):
    """Transcribe `ruta` (ogg/opus, mp3, m4a, wav...) y devuelve el texto.
    Devuelve None si no se pudo transcribir. Nunca lanza."""
    if not ruta or not os.path.isfile(ruta):
        return None
    lang = (idioma or IDIOMA or '').strip() or None
    # 1) Camino principal: faster-whisper.
    texto = _transcribir_whisper(ruta, lang)
    if texto:
        return texto
    # 2) Respaldo: vosk (solo sirve con wav 16 bits; con ogg devuelve None).
    texto = _transcribir_vosk(ruta)
    if texto:
        return texto
    return None


def _cargar_whisper():
    """Carga (y cachea) el modelo de faster-whisper. Devuelve el modelo o
    None si la libreria no esta o falla la descarga del modelo."""
    global _MODELO_WHISPER_CACHE
    if _MODELO_WHISPER_CACHE is not None:
        return _MODELO_WHISPER_CACHE
    try:
        from faster_whisper import WhisperModel
    except Exception as e:
        sys.stderr.write('whisper: libreria no disponible: %s\n' % repr(e))
        return None
    try:
        # compute_type int8: rapido y con poca RAM en CPU.
        modelo = WhisperModel(MODELO_WHISPER, device='cpu',
                              compute_type='int8')
    except Exception as e:
        sys.stderr.write('whisper: no se pudo cargar %s: %s\n'
                         % (MODELO_WHISPER, repr(e)))
        return None
    _MODELO_WHISPER_CACHE = modelo
    return modelo


def _transcribir_whisper(ruta, lang):
    """faster-whisper: devuelve el texto o None."""
    try:
        modelo = _cargar_whisper()
        if modelo is None:
            return None
        # vad_filter: ignora los silencios y solo transcribe voz (mas
        # rapido y preciso en notas de voz con pausas).
        segmentos, _info = modelo.transcribe(
            ruta, language=lang, beam_size=5, vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500))
        trozos = []
        for s in segmentos:
            t = (s.text or '').strip()
            if t:
                trozos.append(t)
        texto = ' '.join(trozos).strip()
        return texto or None
    except Exception as e:
        sys.stderr.write('whisper: error transcribiendo: %s\n' % repr(e))
        return None


def _encontrar_modelo_vosk():
    """Ruta de un modelo de vosk en disco (None si no hay)."""
    base = os.path.dirname(os.path.abspath(__file__))
    raices = (base, os.path.dirname(base), os.path.expanduser('~'))
    for raiz in raices:
        for nombre in VOSK_CARPETAS:
            ruta = os.path.join(raiz, nombre)
            if os.path.isdir(ruta):
                return ruta
    return None


def _transcribir_vosk(ruta):
    """vosk (offline): solo funciona con WAV PCM 16 bits; con ogg/opus (las
    notas de Telegram) devuelve None. Es solo el respaldo de emergencia."""
    carpeta = _encontrar_modelo_vosk()
    if not carpeta:
        return None
    try:
        import wave
        from vosk import Model, KaldiRecognizer
    except Exception:
        return None
    try:
        wf = wave.open(ruta, 'rb')
        rec = KaldiRecognizer(Model(carpeta), wf.getframerate())
        texto = []
        while True:
            datos = wf.readframes(4000)
            if not datos:
                break
            if rec.AcceptWaveform(datos):
                import json as _json
                r = _json.loads(rec.Result())
                if r.get('text'):
                    texto.append(r['text'])
        import json as _json
        r = _json.loads(rec.FinalResult())
        if r.get('text'):
            texto.append(r['text'])
        return ' '.join(texto).strip() or None
    except Exception as e:
        sys.stderr.write('vosk: error transcribiendo: %s\n' % repr(e))
        return None


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.stderr.write('uso: python transcribir_audio.py ruta_del_audio\n')
        sys.exit(2)
    resultado = transcribir(sys.argv[1])
    if resultado:
        print(resultado)
    else:
        sys.exit(1)
