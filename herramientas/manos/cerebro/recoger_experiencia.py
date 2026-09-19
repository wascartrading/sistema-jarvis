# -*- coding: utf-8 -*-
"""
RECOGEDOR DE EXPERIENCIA - Alimenta el cerebro de JARVIS
========================================================
Escanea la memoria, las sesiones y los logs del asistente, extrae las
peticiones del usuario, las etiqueta por intencion y entrena el cerebro
para que JARVIS aprenda de cada interaccion.

Uso:
  python recoger_experiencia.py            # recoge y entrena
  python recoger_experiencia.py --solo     # solo recoge, no entrena
"""

import argparse
import os
import re
import sys

# Permitir importar red_neuronal desde este mismo directorio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from red_neuronal import CerebroJarvis, inferir_intencion  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
RUTA_MEMORIA = os.path.join(RAIZ, "Proyectos de asistente", "memoria_jarvis.md")
RUTA_SESION = os.path.join(RAIZ, "proyectos", "historial_muse.json")
RUTA_LOG = os.path.join(os.environ.get("TEMP", RAIZ), "opencode", "jarvis_bot_out.log")

# Frases que NO son peticiones (ruido del sistema)
RUIDO = [
    "jarvis", "sistema", "pensando", "respondiendo", "escuchando",
    "reposo", "error", "traceback", "exception", "warn", "info",
    "http", "127.0.0.1", "password", "token", "api", "websocket",
]


def limpiar_linea(linea):
    """Limpia una linea y devuelve texto util o None."""
    texto = linea.strip()
    if not texto or len(texto) < 4 or len(texto) > 500:
        return None
    if any(r in texto.lower() for r in RUIDO):
        return None
    # Quitar marcas de tiempo y prefijos de log
    texto = re.sub(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}[^ ]* ?", "", texto)
    texto = re.sub(r"^\[[^\]]*\] ?", "", texto)
    texto = re.sub(r"^(usuario|user|yo|jefe|wascar|wáscar)[: ]+", "", texto, flags=re.I)
    texto = texto.strip(" -–—|")
    if len(texto) < 4:
        return None
    return texto


def recoger_textos():
    """Recoge peticiones del usuario desde memoria, sesion y log."""
    textos = []
    fuentes = []

    def agregar(texto, fuente):
        texto = limpiar_linea(texto)
        if texto and texto not in textos:
            textos.append(texto)
            fuentes.append(fuente)

    # 1. Memoria: lineas que parecen peticiones del usuario
    if os.path.exists(RUTA_MEMORIA):
        with open(RUTA_MEMORIA, "r", encoding="utf-8", errors="ignore") as f:
            for linea in f:
                if linea.startswith("#") or linea.startswith("-") or linea.startswith("|"):
                    continue
                agregar(linea, "memoria")

    # 2. Sesion activa
    if os.path.exists(RUTA_SESION):
        with open(RUTA_SESION, "r", encoding="utf-8", errors="ignore") as f:
            for linea in f:
                agregar(linea, "sesion")

    # 3. Log del asistente (lineas de usuario)
    if os.path.exists(RUTA_LOG):
        with open(RUTA_LOG, "r", encoding="utf-8", errors="ignore") as f:
            for linea in f:
                if re.search(r"(usuario|user|peticion|petición|orden|comando)", linea, re.I):
                    agregar(linea, "log")

    return textos, fuentes


def main():
    parser = argparse.ArgumentParser(description="Recoge experiencia y entrena el cerebro de JARVIS")
    parser.add_argument("--solo", action="store_true", help="Solo recoger, sin entrenar")
    parser.add_argument("--epocas", type=int, default=25, help="Epocas de entrenamiento")
    args = parser.parse_args()

    textos, fuentes = recoger_textos()
    if not textos:
        print("No encontre experiencia nueva para aprender.")
        return

    intenciones = [inferir_intencion(t) for t in textos]
    print(f"Recogidas {len(textos)} experiencias:")
    conteo = {}
    for i in intenciones:
        conteo[i] = conteo.get(i, 0) + 1
    for k, v in sorted(conteo.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")

    if args.solo:
        return

    print("Entrenando el cerebro...")
    cerebro = CerebroJarvis()
    perdida, precision = cerebro.entrenar(textos, intenciones, epocas=args.epocas)
    ruta = cerebro.guardar()
    print(f"Listo. Perdida {perdida:.4f} | Precision {precision:.2%}")
    print(f"Checkpoint: {ruta}")
    print(f"Resumen: {cerebro.resumen()}")


if __name__ == "__main__":
    main()