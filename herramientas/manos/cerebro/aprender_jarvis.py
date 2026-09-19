"""aprender_jarvis.py - Autoaprendizaje autonomo del cerebro de JARVIS.

Ejecuta una sesion de aprendizaje continuo: entrena varias tareas seguidas
(con semillas distintas cada vez para que siempre haya algo nuevo), permite
que la red crezca en capas si no alcanza el umbral, y registra todo en el
diario. Es el modo 'aprende mientras duermo' del asistente.

Uso: python aprender_jarvis.py [--cerebro jarvis] [--tareas espiral,lunas,...]
"""
import argparse
import sys

import continuo
import memoria

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

TAREAS_POR_DEFECTO = ["espiral", "lunas", "circulos", "gaussianas", "4gaussianas"]


def main():
    parser = argparse.ArgumentParser(description="Autoaprendizaje de JARVIS")
    parser.add_argument("--cerebro", default="jarvis")
    parser.add_argument("--tareas", default=",".join(TAREAS_POR_DEFECTO))
    parser.add_argument("--epocas", type=int, default=40)
    parser.add_argument("--umbral", type=float, default=0.90)
    parser.add_argument("--semilla-inicial", type=int, default=0)
    args = parser.parse_args()

    tareas = [t.strip() for t in args.tareas.split(",") if t.strip()]
    if not memoria.existe(args.cerebro):
        print(f"Creando cerebro '{args.cerebro}' con 6 capas de ancho 64...")
        continuo.crear_cerebro(args.cerebro, entrada=2, salida=2, capas=6, ancho=64)

    print(f"=== Sesion de autoaprendizaje de '{args.cerebro}' ===")
    for i, tarea in enumerate(tareas):
        semilla = args.semilla_inicial + i
        print(f"\n--- Tarea {i + 1}/{len(tareas)}: {tarea} (semilla {semilla}) ---")
        try:
            modelo, config, metricas = continuo.aprender_tarea(
                args.cerebro, tarea, epocas=args.epocas, umbral=args.umbral,
                semilla=semilla)
            print(f"OK: precision {metricas['precision_va']:.2%}, "
                  f"{modelo.profundidad()} capas, {modelo.contar_parametros()} parametros")
        except Exception as e:
            print(f"ERROR en {tarea}: {e}")

    est = continuo.estado(args.cerebro)
    print(f"\n=== Resumen final ===")
    print(f"Cerebro '{est['nombre']}': {est['capas']} capas, "
          f"{est['parametros']} parametros, {len(est['tareas'])} tareas aprendidas")
    for t in est["tareas"]:
        print(f"  - {t['tarea']}: {t['precision_va']:.2%}")


if __name__ == "__main__":
    main()