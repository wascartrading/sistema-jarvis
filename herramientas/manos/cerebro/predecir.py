# -*- coding: utf-8 -*-
"""
PREDICTOR - Interfaz rapida del cerebro de JARVIS
=================================================
Permite consultar el cerebro desde cualquier script o desde la linea de
comandos. Devuelve la intencion detectada y su confianza.

Uso:
  python predecir.py "abre youtube"
  python predecir.py --json "crea un bot de trading"
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from red_neuronal import CerebroJarvis  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Predice la intencion de un texto con el cerebro de JARVIS")
    parser.add_argument("texto", nargs="?", help="Texto a analizar")
    parser.add_argument("--json", action="store_true", help="Salida en JSON")
    args = parser.parse_args()

    cerebro = CerebroJarvis()
    if not args.texto:
        # Modo resumen: estado del cerebro
        resumen = cerebro.resumen()
        if args.json:
            print(json.dumps(resumen, ensure_ascii=False))
        else:
            print(f"Epoca global: {resumen['epoca_global']}")
            print(f"Ejemplos vistos: {resumen['ejemplos_vistos']}")
            print(f"Parametros: {resumen['parametros']:,}")
            print(f"Ultima perdida: {resumen['ultima_perdida']}")
            print(f"Ultima precision: {resumen['ultima_precision']}")
            print(f"Checkpoint: {'si' if resumen['checkpoint'] else 'no'}")
        return

    resultados = cerebro.predecir(args.texto)
    if args.json:
        print(json.dumps(resultados, ensure_ascii=False))
    else:
        for intencion, confianza in resultados:
            print(f"{intencion}: {confianza:.1%}")


if __name__ == "__main__":
    main()