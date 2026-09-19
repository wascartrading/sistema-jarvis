"""lecciones.py - Memoria de aprendizaje de JARVIS sobre el usuario.

Esta es la herramienta que JARVIS usa a diario para convertir lo que aprende
del usuario en conocimiento de su red neuronal (el cerebro). Cada leccion es
un par (texto, categoria): por ejemplo ("le gusta el reggaeton", "gustos") o
("prefiere respuestas cortas", "estilo").

Flujo de uso (lo que JARVIS hace cada dia):
  1. registrar  -> guarda una leccion nueva en lecciones.json
  2. entrenar   -> entrena la red con TODAS las lecciones acumuladas
  3. predecir   -> dado un texto, dice a que categoria pertenece
  4. estado     -> cuantas lecciones hay y por categoria

La red aprende de forma continua: cada vez que se entrena, se reentrena la
tarea 'lecciones' con el dataset completo, y las demas tareas del cerebro se
conservan (replay + EWC + destilacion).

Uso:
  python lecciones.py registrar --texto "le gusta el cafe" --categoria gustos
  python lecciones.py entrenar [--epocas 40]
  python lecciones.py predecir --texto "le gusta el cafe"
  python lecciones.py estado
"""
import argparse
import json
import os
import sys

import torch

import continuo
import memoria
from red_neuronal import vectorizar

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAIZ = os.path.dirname(os.path.abspath(__file__))
RUTA_LECCIONES = os.path.join(RAIZ, "datos", "lecciones.json")
CEREBRO = "memoria"  # cerebro dedicado a las lecciones (entrada 4096)
TAREA = "lecciones"
DIM = 4096  # mismo DIM_VOCAB que red_neuronal


def _cargar_lecciones():
    if os.path.exists(RUTA_LECCIONES):
        with open(RUTA_LECCIONES, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _guardar_lecciones(lecciones):
    os.makedirs(os.path.dirname(RUTA_LECCIONES), exist_ok=True)
    with open(RUTA_LECCIONES, "w", encoding="utf-8") as f:
        json.dump(lecciones, f, ensure_ascii=False, indent=2)


def _categorias(lecciones):
    """Lista ordenada de categorias presentes."""
    cats = []
    for l in lecciones:
        if l["categoria"] not in cats:
            cats.append(l["categoria"])
    return cats


def cmd_registrar(args):
    lecciones = _cargar_lecciones()
    lecciones.append({
        "texto": args.texto,
        "categoria": args.categoria,
        "fecha": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    _guardar_lecciones(lecciones)
    print(f"Leccion registrada: '{args.texto}' -> {args.categoria} "
          f"(total {len(lecciones)})")


def cmd_entrenar(args):
    lecciones = _cargar_lecciones()
    if not lecciones:
        print("No hay lecciones registradas. Usa 'registrar' primero.")
        return
    cats = _categorias(lecciones)
    idx_cat = {c: i for i, c in enumerate(cats)}
    X = torch.stack([torch.tensor(vectorizar(l["texto"], DIM)) for l in lecciones])
    y = torch.tensor([idx_cat[l["categoria"]] for l in lecciones], dtype=torch.long)
    if not memoria.existe(CEREBRO):
        continuo.crear_cerebro(CEREBRO, entrada=DIM, salida=len(cats),
                               capas=6, ancho=128, dropout=0.05)
    modelo, config, metricas = continuo.aprender_datos(
        CEREBRO, TAREA, X, y, epocas=args.epocas, lr=args.lr, batch=args.batch,
        umbral=args.umbral, semilla=args.semilla, silencioso=args.silencioso,
        lam_ewc=args.lam_ewc)
    print(f"Cerebro '{CEREBRO}' entreno la tarea '{TAREA}': "
          f"precision {metricas['precision_va']:.2%}, "
          f"{len(lecciones)} lecciones, {len(cats)} categorias "
          f"({', '.join(cats)}).")


def cmd_predecir(args):
    lecciones = _cargar_lecciones()
    if not lecciones:
        print("No hay lecciones. Entrena primero.")
        return
    cats = _categorias(lecciones)
    vec = torch.tensor(vectorizar(args.texto, DIM))
    clase, probs = continuo.predecir_vector(CEREBRO, vec, TAREA)
    print(f"'{args.texto}' -> {cats[clase]} "
          f"(confianza {probs[clase]:.2%})")
    if args.detalle:
        for c, p in zip(cats, probs):
            print(f"  {c}: {p:.2%}")


def cmd_estado(args):
    lecciones = _cargar_lecciones()
    if not lecciones:
        print("No hay lecciones registradas.")
        return
    cats = _categorias(lecciones)
    print(f"Lecciones: {len(lecciones)} en {len(cats)} categorias:")
    for c in cats:
        n = sum(1 for l in lecciones if l["categoria"] == c)
        print(f"  - {c}: {n}")
    if memoria.existe(CEREBRO):
        est = continuo.estado(CEREBRO)
        print(f"Cerebro '{CEREBRO}': {est['capas']} capas, "
              f"{est['parametros']} parametros, tareas: "
              f"{', '.join(t['tarea'] for t in est['tareas'])}")


def main():
    parser = argparse.ArgumentParser(prog="lecciones", description="Memoria de JARVIS")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("registrar", help="Guarda una leccion nueva")
    p.add_argument("--texto", required=True)
    p.add_argument("--categoria", required=True)
    p.set_defaults(fn=cmd_registrar)

    p = sub.add_parser("entrenar", help="Entrena la red con las lecciones")
    p.add_argument("--epocas", type=int, default=40)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--batch", type=int, default=32)
    p.add_argument("--umbral", type=float, default=0.90)
    p.add_argument("--semilla", type=int, default=0)
    p.add_argument("--lam-ewc", type=float, default=2.0)
    p.add_argument("--silencioso", action="store_true")
    p.set_defaults(fn=cmd_entrenar)

    p = sub.add_parser("predecir", help="Clasifica un texto")
    p.add_argument("--texto", required=True)
    p.add_argument("--detalle", action="store_true")
    p.set_defaults(fn=cmd_predecir)

    p = sub.add_parser("estado", help="Resumen de lecciones")
    p.set_defaults(fn=cmd_estado)

    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()