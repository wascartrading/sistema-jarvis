"""memoria_jarvis.py - Interfaz de JARVIS con su red neuronal (el cerebro).

Este es el puente que JARVIS usa a diario para:
  - APRENDER: registrar una leccion sobre el usuario (gusto, habito, preferencia).
  - CONSOLIDAR: entrenar la red con las lecciones acumuladas (mejora continua).
  - RECORDAR: preguntar a la red a que categoria pertenece un texto.

Todo vive en Proyectos de asistente/manos/cerebro/ (el proyecto 'cerebro'). JARVIS lo
invoca con la ruta completa del python.

Uso:
  python memoria_jarvis.py aprender --texto "le gusta el cafe" --categoria gustos
  python memoria_jarvis.py consolidar
  python memoria_jarvis.py recordar --texto "le gusta el cafe"
  python memoria_jarvis.py estado
"""
import argparse
import os
import subprocess
import sys

PYTHON = r"C:\Users\wasc4\AppData\Local\Programs\Python\Python312\python.exe"
CEREBRO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cerebro")


def _run(*args):
    """Ejecuta un comando del proyecto cerebro y devuelve su salida."""
    cmd = [PYTHON, os.path.join(CEREBRO_DIR, args[0])] + list(args[1:])
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    out = (r.stdout or "").strip()
    err = (r.stderr or "").strip()
    if r.returncode != 0:
        return f"ERROR: {err or out}"
    return out


def cmd_aprender(args):
    print(_run("lecciones.py", "registrar", "--texto", args.texto,
               "--categoria", args.categoria))


def cmd_consolidar(args):
    print(_run("consolidar.py", "--silencioso" if args.silencioso else ""))


def cmd_recordar(args):
    cmd = ["lecciones.py", "predecir", "--texto", args.texto]
    if args.detalle:
        cmd.append("--detalle")
    print(_run(*cmd))


def cmd_estado(args):
    print(_run("lecciones.py", "estado"))


def main():
    parser = argparse.ArgumentParser(prog="memoria_jarvis",
                                     description="Memoria neuronal de JARVIS")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("aprender", help="Registra una leccion nueva")
    p.add_argument("--texto", required=True)
    p.add_argument("--categoria", required=True)
    p.set_defaults(fn=cmd_aprender)

    p = sub.add_parser("consolidar", help="Entrena la red con las lecciones")
    p.add_argument("--silencioso", action="store_true")
    p.set_defaults(fn=cmd_consolidar)

    p = sub.add_parser("recordar", help="Clasifica un texto con la red")
    p.add_argument("--texto", required=True)
    p.add_argument("--detalle", action="store_true")
    p.set_defaults(fn=cmd_recordar)

    p = sub.add_parser("estado", help="Resumen de la memoria")
    p.set_defaults(fn=cmd_estado)

    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()