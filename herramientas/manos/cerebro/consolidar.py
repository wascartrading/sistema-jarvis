"""consolidar.py - Consolidacion diaria de la memoria de JARVIS.

JARVIS ejecuta este script (idealmente una vez al dia, o cuando acumule
lecciones) para que su red neuronal aprenda de todo lo que registro durante
el dia. Es el corazon del autoaprendizaje: registrar -> consolidar -> mejorar.

Que hace:
  1. Entrena el cerebro 'memoria' con TODAS las lecciones acumuladas
     (reentrenamiento incremental: no pierde lo anterior).
  2. Muestra un resumen de lo aprendido (categorias y precision).
  3. Si hay pocas lecciones, avisa que conviene acumular mas.

Uso:
  python consolidar.py [--epocas 40] [--silencioso]
"""
import argparse
import sys

import lecciones

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main():
    parser = argparse.ArgumentParser(prog="consolidar", description="Consolidacion diaria")
    parser.add_argument("--epocas", type=int, default=40)
    parser.add_argument("--silencioso", action="store_true")
    args = parser.parse_args()

    lecciones.cmd_estado(argparse.Namespace())
    print()
    lecciones.cmd_entrenar(argparse.Namespace(
        epocas=args.epocas, lr=1e-3, batch=32, umbral=0.90,
        semilla=0, lam_ewc=2.0, silencioso=args.silencioso))
    print()
    print("Memoria consolidada. JARVIS ya sabe un poco mas de ti.")


if __name__ == "__main__":
    main()