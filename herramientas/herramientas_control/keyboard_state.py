"""
keyboard_state.py — Estado y control de Bloq Mayus / Bloq Num.
Portado del desmenuzado (user32 GetKeyState / keybd_event).

Uso CLI:
  python cli.py keyboard_state estado
  python cli.py keyboard_state set caps=1|0|toggle  num=1|0|toggle
"""
import ctypes

user32 = ctypes.windll.user32

VK_CAPITAL = 0x14
VK_NUMLOCK = 0x90


def _activo(vk):
    """True si la tecla de bloqueo esta activa."""
    estado = user32.GetKeyState(vk)
    return bool(estado & 1)


def _pulsar(vk):
    """Simula la pulsacion de una tecla de bloqueo."""
    user32.keybd_event(vk, 0, 0, 0)
    user32.keybd_event(vk, 0, 2, 0)  # KEYEVENTF_KEYUP


def caps_activo():
    return _activo(VK_CAPITAL)


def num_activo():
    return _activo(VK_NUMLOCK)


def set_caps(valor):
    """valor: True/False para fijar, 'toggle' para invertir."""
    if valor == "toggle":
        _pulsar(VK_CAPITAL)
        return caps_activo()
    if caps_activo() != bool(valor):
        _pulsar(VK_CAPITAL)
    return caps_activo()


def set_num(valor):
    if valor == "toggle":
        _pulsar(VK_NUMLOCK)
        return num_activo()
    if num_activo() != bool(valor):
        _pulsar(VK_NUMLOCK)
    return num_activo()


def teclado_limpio():
    """Alias de compatibilidad (implementacion real en text_input)."""
    from .text_input import teclado_limpio as _tl
    return _tl()


def _parse_bool(v):
    v = str(v).strip().lower()
    if v in ("1", "true", "si", "sí", "on", "activar", "encender"):
        return True
    if v in ("0", "false", "no", "off", "apagar", "desactivar"):
        return False
    return "toggle"


def _main(argv):
    if len(argv) < 2:
        print(f"Caps={caps_activo()} Num={num_activo()}")
        return
    accion = argv[1]
    if accion == "estado":
        print(f"Caps={caps_activo()} Num={num_activo()}")
    elif accion == "set":
        caps = num = None
        for arg in argv[2:]:
            if "=" in arg:
                k, v = arg.split("=", 1)
                if k in ("caps", "mayus"):
                    caps = _parse_bool(v)
                elif k in ("num", "numlock"):
                    num = _parse_bool(v)
        if caps is not None:
            set_caps(caps)
        if num is not None:
            set_num(num)
        print(f"Caps={caps_activo()} Num={num_activo()}")
    else:
        print(f"Accion desconocida: {accion}")


if __name__ == "__main__":
    import sys
    _main(sys.argv)