"""
visual_click.py — Clic inteligente: captura la pantalla, localiza el elemento
(UI Automation o coordenadas) y hace clic. Portado del desmenuzado (version
ligera sin vision por API).

Uso CLI:
  python cli.py visual_click clic "texto del boton"          (UI Automation)
  python cli.py visual_click clic x=500 y=400                (coords directas)
"""
import time


def _con_uiautomation():
    try:
        import uiautomation
        return uiautomation
    except Exception:
        return None


def _rect_valido(elem):
    """True si el control tiene rectangulo visible (no virtualizado)."""
    try:
        r = elem.BoundingRectangle
        if r is None:
            return False
        w = getattr(r, "width", None)
        h = getattr(r, "height", None)
        ancho = w() if callable(w) else (r.right - r.left)
        alto = h() if callable(h) else (r.bottom - r.top)
        return ancho > 2 and alto > 2
    except Exception:
        return False


def _centro_rect(elem):
    try:
        r = elem.BoundingRectangle
        return int(r.left + (r.right - r.left) / 2), int(r.top + (r.bottom - r.top) / 2)
    except Exception:
        return None


def clic_en_texto(texto, doble=False, timeout=12):
    """Busca el control cuyo Name contenga `texto` y hace clic.
    Filtra controles sin rectangulo (virtualizados) y usa el clic fisico
    como respaldo si UI Automation no puede invocar."""
    uia = _con_uiautomation()
    if not uia:
        return False, "uiautomation no instalado; usa coordenadas (x=, y=)"
    root = uia.GetRootControl()
    try:
        win = uia.GetForegroundControl()
    except Exception:
        win = root
    controles = []

    def _walk(elem, prof=0):
        if prof > 40:
            return
        try:
            name = elem.Name
        except Exception:
            name = ""
        if name and texto.lower() in name.lower() and _rect_valido(elem):
            controles.append(elem)
        try:
            for hijo in elem.GetChildren():
                _walk(hijo, prof + 1)
        except Exception:
            pass

    try:
        _walk(win)
    except Exception:
        pass
    if not controles:
        try:
            _walk(root)
        except Exception:
            pass
    if not controles:
        return False, f"No encontré elemento visible con '{texto}'"
    c = controles[0]
    try:
        c.Click(simulateMove=False)
        return True, f"Clic UI en '{c.Name}'"
    except Exception:
        pass
    # respaldo: clic fisico en el centro del rectangulo (con activacion de ventana)
    from .computer_control import click
    centro = _centro_rect(c)
    if centro:
        click(centro[0], centro[1], doble=doble)
        return True, f"Clic físico en '{c.Name}' ({centro[0]},{centro[1]})"
    return False, f"No pude clicar '{texto}'"


def clic_coordenadas(x, y, doble=False):
    from .computer_control import click
    click(x, y, doble=doble)
    return True, f"Clic en ({x}, {y})"


def _main(argv):
    import sys
    if len(argv) < 2:
        print("Acciones: clic <texto> | clic x=500 y=400")
        return 2
    accion = argv[1].lower()
    resto = argv[2:]
    if accion != "clic":
        print(f"Accion desconocida: {accion}")
        return 2
    kwargs = {}
    texto = []
    for arg in resto:
        if "=" in arg:
            k, v = arg.split("=", 1)
            kwargs[k] = v
        else:
            texto.append(arg)
    if kwargs and ("x" in kwargs or "y" in kwargs):
        try:
            x = int(kwargs.get("x", 0))
            y = int(kwargs.get("y", 0))
        except Exception:
            print("Coordenadas invalidas")
            return 2
        ok, msg = clic_coordenadas(x, y, doble=(kwargs.get("doble", "0") == "1"))
        print(msg)
        return 0 if ok else 2
    if texto:
        ok, msg = clic_en_texto(" ".join(texto), doble=(kwargs.get("doble", "0") == "1"))
        print(msg)
        return 0 if ok else 2
    print("Necesito texto del elemento o x/y")
    return 2


if __name__ == "__main__":
    _main(sys.argv)