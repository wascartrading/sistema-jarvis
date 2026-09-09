# -*- coding: utf-8 -*-
"""aprender_dia.py - Consolidacion diaria del cerebro local de JARVIS.

Uso (lo llama JARVIS al final del dia o cuando acumula lecciones):
  python aprender_dia.py                 # consolida memoria + resumen
  python aprender_dia.py --epocas 60     # con mas epocas

QUE HACE:
  1. Consolida el cerebro 'memoria' (lecciones) -> aprende de lo que JARVIS
     registro durante el dia (gustos, estilo, trabajo, habitos).
  2. Recoge la experiencia de las sesiones/logs y reentrena el cerebro de
     intenciones local para que generalice mejor cada vez.
  3. Muestra un resumen del estado de la fusion (intenciones + lecciones).

Es el corazon del autoaprendizaje diario: registrar -> consolidar -> mejorar.
Todo con fallback: si algo falla, se reporta y no rompe nada.
"""
import argparse
import os
import sys

# Directorios
CARPETA_CEREBRO = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "cerebro")
sys.path.insert(0, CARPETA_CEREBRO)


def _consolidar_memoria(epocas, silencioso):
    """Entrena el cerebro 'memoria' con las lecciones acumuladas."""
    import apuente_cerebro as ap
    ok, detalle = ap.consolidar(epocas=epocas)
    print(("OK: " if ok else "Memoria: ") + detalle)
    print("\nLecciones por categoria:")
    st = ap.estado()
    for cat, n in (st.get("categorias") or {}).items():
        print(f"  - {cat}: {n}")
    return ok


def _recoger_y_entrenar_intenciones(epocas):
    """Recoge experiencia real (memoria/sesion/log) y reentrena el cerebro
    de intenciones local. Solo si hay experiencia nueva."""
    try:
        import recoger_experiencia as rec
        from red_neuronal import CerebroJarvis, inferir_intencion
        textos, fuentes = rec.recoger_textos()
        if not textos:
            print("\nIntenciones: no hay experiencia nueva que recoger.")
            return
        print(f"\nIntenciones: recogidos {len(textos)} textos de experiencia.")
        intenciones = [inferir_intencion(t) for t in textos]
        print("Reentrenando cerebro de intenciones...")
        cerebro = CerebroJarvis()
        perdida, precision = cerebro.entrenar(textos, intenciones, epocas=epocas)
        cerebro.guardar()
        print(f"  Intenciones: perdida {perdida:.4f} | precision {precision:.2%}")
    except Exception as e:
        print(f"\nIntenciones: no se pudo reentrenar: {repr(e)[:120]}")


def main():
    parser = argparse.ArgumentParser(prog="aprender_dia",
                                     description="Consolidacion diaria del cerebro local")
    parser.add_argument("--epocas", type=int, default=40)
    parser.add_argument("--solo-memoria", action="store_true",
                        help="Solo consolidar lecciones, no reentrenar intenciones")
    parser.add_argument("--silencioso", action="store_true")
    args = parser.parse_args()

    print("=== JARVIS: aprendizaje diario ===")
    _consolidar_memoria(args.epocas, args.silencioso)
    if not args.solo_memoria:
        _recoger_y_entrenar_intenciones(args.epocas)
    print("\n=== Listo. JARVIS aprendio un poco mas de ti. ===")


if __name__ == "__main__":
    main()
