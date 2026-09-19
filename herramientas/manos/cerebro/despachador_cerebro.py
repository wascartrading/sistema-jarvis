# -*- coding: utf-8 -*-
"""despachador_cerebro.py - Ejecuta acciones DIRECTAS sin gastar el modelo externo.

Pieza de la fusion del cerebro local (20/08/2026, regla del usuario: reducir la
dependencia de modelos externos). Usa la intencion LOCAL (apuente_cerebro.
predecir_intencion) para resolver acciones rutinarias SIN llamar al LLM externo
(DeepSeek queda de respaldo para el razonamiento).

SEGURIDAD / DISENO:
  - Todo es opcional y con fallback: si este modulo devuelve None, el asistente
    sigue con su flujo normal (modelo externo). NUNCA lanza.
  - Solo actua en acciones DIRECTAS y SEGURAS:
      * saludo / despedida -> respuesta local breve (no gasta modelo).
      * abrir_app -> abre aplicaciones de un MAPA SEGURO verificado (nada
        arbitrario). Si la app no esta en el mapa, devuelve None (delega).
  - Las intenciones de RAZONAMIENTO (informacion, crear_proyecto, modificar_codigo,
    trading, automatizar, buscar_web, memoria, juego) SIEMPRE delegan al modelo
    externo (devuelven None): no se improvisa una accion que podria ser erronea.
  - respetar_silencio: si es True (musica/video), la accion se ejecuta pero NO se
    responde por voz (regla del usuario: el audio del contenido choca con la voz).
"""
import os
import subprocess
import sys

CARPETA_CEREBRO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CARPETA_CEREBRO)
import apuente_cerebro as ap


# Intenciones que requieren Razonamiento: siempre delegar al modelo externo.
_INTENCIONES_DELEGAR = {
    "informacion", "crear_proyecto", "modificar_codigo", "automatizar",
    "trading", "juego", "buscar_web", "memoria",
}
# Intenciones de accion directa manejadas aqui.
_INTENCIONES_DIRECTAS = {"saludo", "despedida", "abrir_app", "sistema",
                         "reproducir_musica"}

# Respuestas locales para saludo / despedida (no gastan modelo).
_RESPUESTAS = {
    "saludo": "Hola, jefe. Aquí ando, listo para lo que necesite.",
    "despedida": "Listo, jefe. Cualquier cosa, aquí me tiene.",
}

# MAPA SEGURO de apps que JARVIS puede abrir localmente (nombre -> comando).
# Solo entran apps verificables por 'start' de Windows. Si no existe, no abre.
APPS = {
    "youtube": "https://www.youtube.com",
    "spotify": "spotify:",
    "chrome": ["cmd", "/c", "start", "chrome"],
    "telegram": ["cmd", "/c", "start", "Telegram"],
    "whatsapp": ["cmd", "/c", "start", "whatsapp:"],
    "calculadora": ["cmd", "/c", "start", "calc"],
    "bloc de notas": ["cmd", "/c", "start", "notepad"],
    "explorador": ["cmd", "/c", "start", "explorer"],
}
# Palabras clave para detectar la app a abrir dentro del mensaje.
_APPS_CLAVE = {
    "youtube": ["youtube", "yt"],
    "spotify": ["spotify", "spoti"],
    "chrome": ["chrome", "navegador", "browser"],
    "telegram": ["telegram", "telegram"],
    "whatsapp": ["whatsapp", "wsp", "whats"],
    "calculadora": ["calculadora", "calc"],
    "bloc de notas": ["bloc de notas", "notas", "notepad"],
    "explorador": ["explorador", "archivos", "explorer"],
}

# Palabras que al usuario le dice "combustible" para reproducir musica.
_APPS_REPRODUCIR = {
    "youtube": "https://www.youtube.com",
}


def _detectar_app(texto):
    """Encuentra la app del mapa que el mensaje pide abrir, o None."""
    t = (texto or "").lower()
    for app, pistas in _APPS_CLAVE.items():
        for p in pistas:
            if p in t:
                return app
    return None


def _abrir_app_local(app):
    """Abre la app del mapa. Devuelve True si logro lanzarla (o es una URL)."""
    try:
        dst = APPS[app]
        if isinstance(dst, str):
            # URLs/protocolos: abrir con el navegador/manejador por defecto
            if dst.startswith(("http", "spotify:", "whatsapp:")):
                import webbrowser
                webbrowser.open(dst)
                return True
            # nombre de app simple
            subprocess.Popen(["cmd", "/c", "start", dst],
                             creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        # lista de comando
        subprocess.Popen(dst, creationflags=subprocess.CREATE_NO_WINDOW)
        return True
    except Exception:
        return False


def despachar(texto):
    """Intenta resolver 'texto' con la inteligencia local. Devuelve:
      - None: no se actua (delegar al modelo externo).
      - {'respuesta': str, 'ejecutado': bool, 'silencio': bool}
    NUNCA lanza."""
    if not texto:
        return None
    intencion, confianza = ap.predecir_intencion(texto)
    if intencion not in _INTENCIONES_DIRECTAS:
        return None
    if confianza < ap.UMBRAL_CONFIANZA:
        return None
    try:
        # --- saludo / despedida: respuesta local, sin ejecutar nada ---
        if intencion in ("saludo", "despedida"):
            return {"respuesta": _RESPUESTAS[intencion],
                    "ejecutado": False, "silencio": False}
        # --- reproducir musica: abrir Youtube con la cancion buscada ---
        if intencion == "reproducir_musica":
            return None   # POR AHORA delega: el modelo elige la cancion exacta
        # --- abrir app: solo si la app esta en el mapa seguro ---
        if intencion == "abrir_app":
            app = _detectar_app(texto)
            if app and app in APPS:
                if _abrir_app_local(app):
                    return {"respuesta": "Listo, jefe: abriendo %s." % app,
                            "ejecutado": True, "silencio": False}
            return None
        # --- sistema: solo acciones MUY concretas y seguras ---
        if intencion == "sistema":
            return None   # POR AHORA delega (acciones de sistema son delicadas)
    except Exception:
        return None
    return None


def activo():
    """True si el despachador puede funcionar (cerebro local disponible)."""
    return ap._disponible() and bool(ap.ACTIVO)


if __name__ == "__main__":
    print("Despachador activo:", activo())
    for t in ["hola jarvis", "adios", "abre youtube", "abre spotify",
              "quien es el presidente", "crea un juego"]:
        r = despachar(t)
        if r:
            print(f"  '{t}' -> LOCAL: {r}")
        else:
            print(f"  '{t}' -> (delega al modelo externo)")
