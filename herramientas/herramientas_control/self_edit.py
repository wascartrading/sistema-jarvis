#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""self_edit.py - AUTOEDICION de mi propio sistema (16/09/2026, orden del jefe).

TRAIDO DEL DESMENUZADO (JARVIS-HRZ, actions/self_edit.py), que hacia justo
esto: leer y editar su propio codigo SIEMPRE con copia de seguridad antes
("Backup guardado en: ..."). Aqui queda con una proteccion extra: solo puedo
tocar MIS carpetas (lista blanca), nada del resto de la PC.

Orden del jefe (16/09/2026): "trae tambien el self_edit ... para cuando yo te
pida que modifiques o arregles un codigo en tiempo real o en vivo".

Acciones (via cli.py, modulo "self_edit"):
  python cli.py self_edit leer <ruta> [max]
  python cli.py self_edit editar <ruta> "<buscar>" "<reemplazar>"
  python cli.py self_edit agregar <ruta> "<contenido>"
  python cli.py self_edit copias <ruta>
  python cli.py self_edit restaurar <ruta> [marca]

CADA cambio hace: copia de seguridad -> edicion -> verificacion de sintaxis.
Si el archivo editado es .py y NO compila, se avisa en el momento.
"""
import os
import sys

try:
    from . import code_live as cl
except Exception:                                  # pragma: no cover
    cl = None

_CARPETAS_PERMITIDAS = (
    r"C:\Users\wasc4\Documents\Sistema Jarvis",
    r"C:\Users\wasc4\.config\opencode\agent",
)


def _permitido(ruta):
    """Solo mis carpetas: el resto de la PC queda fuera de mi autoedicion."""
    absoluta = os.path.abspath(ruta)
    for base in _CARPETAS_PERMITIDAS:
        if absoluta.lower().startswith(os.path.abspath(base).lower()):
            return True
    return False


def leer(ruta, maximo=200):
    """Lee un archivo mio (con numeros de linea)."""
    if not _permitido(ruta):
        return "Fuera de mis carpetas; no lo toco: %s" % ruta
    if not os.path.exists(ruta):
        return "No existe: %s" % ruta
    total = sum(1 for _ in open(ruta, encoding="utf-8", errors="replace"))
    if total > maximo:
        return ("%s (%d lineas). Mostrando las primeras %d:\n\n%s\n\n"
                "[... %d lineas mas]"
                % (ruta, total, maximo, cl.leer(ruta, 1, maximo), total - maximo))
    return cl.leer(ruta)


def editar(ruta, buscar, reemplazar, todas=False):
    """Edita un archivo mio con copia previa y verificacion."""
    if not _permitido(ruta):
        return False, "Fuera de mis carpetas; no lo toco: %s" % ruta
    return cl.editar(ruta, buscar, reemplazar, todas=todas)


def agregar(ruta, contenido):
    """Agrega contenido al final de un archivo mio (con copia previa)."""
    if not _permitido(ruta):
        return False, "Fuera de mis carpetas; no lo toco: %s" % ruta
    return cl.agregar(ruta, contenido)


def copias(ruta):
    """Copia de seguridad mas reciente de un archivo mio."""
    if not _permitido(ruta):
        return "Fuera de mis carpetas: %s" % ruta
    lista = cl.copias(ruta)
    if not lista:
        return "Sin copias de %s" % ruta
    return "\n".join("%s  %s" % (m, p) for m, p in lista)


def restaurar(ruta, marca=None):
    """Restaura un archivo mio desde su ultima copia (o la que se indique)."""
    if not _permitido(ruta):
        return False, "Fuera de mis carpetas; no lo toco: %s" % ruta
    return cl.restaurar(ruta, marca)


def _main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    accion = argv[1].lower()
    args = argv[2:]
    if accion == "leer":
        if not args:
            print("Falta la ruta")
            return 2
        print(leer(args[0], int(args[1]) if len(args) > 1 else 200))
        return 0
    if accion == "editar":
        if len(args) < 3:
            print('Uso: editar <ruta> "<buscar>" "<reemplazar>"')
            return 2
        ok, msg = editar(args[0], args[1], args[2])
        print(("OK: " if ok else "FALLO: ") + msg)
        return 0 if ok else 1
    if accion == "agregar":
        if len(args) < 2:
            print('Uso: agregar <ruta> "<contenido>"')
            return 2
        ok, msg = agregar(args[0], args[1])
        print(("OK: " if ok else "FALLO: ") + msg)
        return 0 if ok else 1
    if accion == "copias":
        if not args:
            print("Falta la ruta")
            return 2
        print(copias(args[0]))
        return 0
    if accion == "restaurar":
        if not args:
            print("Falta la ruta")
            return 2
        ok, msg = restaurar(args[0], args[1] if len(args) > 1 else None)
        print(("OK: " if ok else "FALLO: ") + msg)
        return 0 if ok else 1
    print("Acciones: leer|editar|agregar|copias|restaurar")
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
