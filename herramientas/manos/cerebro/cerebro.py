"""cerebro.py - Interfaz de linea de comandos del cerebro de JARVIS.

Comandos:
  crear      Crea un cerebro nuevo (red profunda con N capas).
  aprender   Entrena una tarea nueva sin olvidar las anteriores.
  evaluar    Mide la precision del cerebro en una tarea.
  predecir   Clasifica un punto (x, y).
  estado     Muestra arquitectura, capas y tareas aprendidas.
  diario     Muestra el historial de aprendizaje.
  listar     Lista los cerebros existentes.

Ejemplos:
  python cerebro.py crear --nombre jarvis --capas 6 --ancho 64
  python cerebro.py aprender --nombre jarvis --tarea espiral --epocas 60
  python cerebro.py aprender --nombre jarvis --tarea lunas --epocas 60
  python cerebro.py predecir --nombre jarvis --x 0.5 --y -0.3
"""
import argparse
import json
import sys

import continuo
import memoria

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def cmd_crear(args):
    modelo, config = continuo.crear_cerebro(
        args.nombre, entrada=args.entrada, salida=args.salida,
        capas=args.capas, ancho=args.ancho, activacion=args.activacion,
        dropout=args.dropout, semilla=args.semilla)
    print(f"Cerebro '{args.nombre}' creado: {modelo.profundidad()} capas, "
          f"{modelo.contar_parametros()} parametros.")


def cmd_aprender(args):
    modelo, config, metricas = continuo.aprender_tarea(
        args.nombre, args.tarea, epocas=args.epocas, lr=args.lr, batch=args.batch,
        umbral=args.umbral, crecer=not args.no_crecer,
        max_crecimientos=args.max_crecimientos, semilla=args.semilla,
        n_puntos=args.puntos, lam_ewc=args.lam_ewc)
    print(f"Tarea '{args.tarea}' aprendida: precision {metricas['precision_va']:.2%}, "
          f"perdida {metricas['perdida_va']:.4f}, {modelo.profundidad()} capas.")


def cmd_evaluar(args):
    precision, perdida = continuo.evaluar_tarea(args.nombre, args.tarea,
                                                semilla=args.semilla)
    print(f"Precision en '{args.tarea}': {precision:.2%} (perdida {perdida:.4f})")


def cmd_predecir(args):
    clase, prob = continuo.predecir(args.nombre, args.x, args.y, tarea=args.tarea)
    print(f"Punto ({args.x}, {args.y}) en '{args.tarea or 'primera tarea'}' "
          f"-> clase {clase} | probabilidades: "
          + ", ".join(f"{p:.3f}" for p in prob))


def cmd_estado(args):
    est = continuo.estado(args.nombre)
    print(f"Cerebro '{est['nombre']}'")
    print(f"  Arquitectura: {' -> '.join(str(d) for d in est['arquitectura'])}")
    print(f"  Capas: {est['capas']} | Parametros: {est['parametros']} | "
          f"Crecimientos: {est['crecimientos']}")
    print(f"  Creado: {est['creado']}")
    if est["tareas"]:
        print("  Tareas aprendidas:")
        for t in est["tareas"]:
            print(f"    - {t['tarea']}: precision {t['precision_va']:.2%} "
                  f"({t['capas']} capas)")


def cmd_diario(args):
    diario = memoria.leer_diario()
    if not diario:
        print("El diario esta vacio.")
        return
    for e in diario[-args.ultimas:]:
        fecha = e.get("fecha", "?")
        print(f"[{fecha}] {e.get('cerebro', '?')} aprendio '{e.get('tarea', '?')}': "
              f"precision {e.get('precision_va', 0.0):.2%}, "
              f"{e.get('capas', '?')} capas, {e.get('parametros', '?')} parametros")


def cmd_listar(args):
    cerebros = memoria.listar()
    if not cerebros:
        print("No hay cerebros creados.")
        return
    print("Cerebros: " + ", ".join(c["nombre"] for c in cerebros))


def main():
    parser = argparse.ArgumentParser(prog="cerebro", description="Cerebro de JARVIS")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("crear", help="Crea un cerebro nuevo")
    p.add_argument("--nombre", required=True)
    p.add_argument("--entrada", type=int, default=2)
    p.add_argument("--salida", type=int, default=2)
    p.add_argument("--capas", type=int, default=6)
    p.add_argument("--ancho", type=int, default=64)
    p.add_argument("--activacion", default="relu", choices=["relu", "silu", "gelu"])
    p.add_argument("--dropout", type=float, default=0.15)
    p.add_argument("--semilla", type=int, default=42)
    p.set_defaults(fn=cmd_crear)

    p = sub.add_parser("aprender", help="Entrena una tarea nueva")
    p.add_argument("--nombre", required=True)
    p.add_argument("--tarea", required=True,
                   choices=["espiral", "lunas", "circulos", "gaussianas", "4gaussianas"])
    p.add_argument("--epocas", type=int, default=60)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--batch", type=int, default=64)
    p.add_argument("--umbral", type=float, default=0.90)
    p.add_argument("--no-crecer", action="store_true")
    p.add_argument("--max-crecimientos", type=int, default=3)
    p.add_argument("--semilla", type=int, default=0)
    p.add_argument("--puntos", type=int, default=2000)
    p.add_argument("--lam-ewc", type=float, default=2.0)
    p.set_defaults(fn=cmd_aprender)

    p = sub.add_parser("evaluar", help="Evalua en una tarea")
    p.add_argument("--nombre", required=True)
    p.add_argument("--tarea", required=True)
    p.add_argument("--semilla", type=int, default=0)
    p.set_defaults(fn=cmd_evaluar)

    p = sub.add_parser("predecir", help="Clasifica un punto")
    p.add_argument("--nombre", required=True)
    p.add_argument("--x", type=float, required=True)
    p.add_argument("--y", type=float, required=True)
    p.add_argument("--tarea", default=None, help="Cabeza a usar (default: primera)")
    p.set_defaults(fn=cmd_predecir)

    p = sub.add_parser("estado", help="Estado del cerebro")
    p.add_argument("--nombre", required=True)
    p.set_defaults(fn=cmd_estado)

    p = sub.add_parser("diario", help="Historial de aprendizaje")
    p.add_argument("--ultimas", type=int, default=10)
    p.set_defaults(fn=cmd_diario)

    p = sub.add_parser("listar", help="Lista cerebros")
    p.set_defaults(fn=cmd_listar)

    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()