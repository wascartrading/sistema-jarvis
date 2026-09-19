"""
audio_control.py — EL OIDO de JARVIS.

Mira si un proceso esta emitiendo sonido AHORA MISMO. Sirve para saber si una
pestana de Brave (un video de HBO, YouTube, una serie) esta reproduciendo o
esta pausada, sin necesidad de ver la pantalla (el video a pantalla completa
sale negro en las capturas).

Uso:
  python cli.py audio estado                     -> todas las sesiones de audio
  python cli.py audio suena brave [segundos]     -> SUENA / SILENCIO (codigo 0/1)
  python cli.py audio pico brave [segundos]      -> pico maximo medido (numero)
  python cli.py audio silenciar brave on|off     -> silencia o devuelve el sonido
  python cli.py audio volumen brave 50           -> volumen de esa sesion (0-100)

El nombre del proceso se busca por coincidencia, sin distinguir mayusculas:
"brave" encuentra "brave.exe".
"""
import sys
import time

UMBRAL = 0.002          # por encima de esto se considera que suena
MUESTREO = 0.05         # cada 50 ms


def _titulo(sesion):
    try:
        return (sesion.DisplayName or "").strip()
    except Exception:
        return ""


def _sesiones(filtro=None):
    from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
    lista = []
    for s in AudioUtilities.GetAllSessions():
        try:
            nombre = s.Process.name() if s.Process else "(sistema)"
        except Exception:
            nombre = "?"
        if filtro and filtro.lower() not in nombre.lower():
            continue
        meter = None
        pico = 0.0
        try:
            meter = s._ctl.QueryInterface(IAudioMeterInformation)
            pico = float(meter.GetPeakValue())
        except Exception:
            pass
        mute = False
        try:
            mute = bool(s.SimpleAudioVolume.GetMute())
        except Exception:
            pass
        estado = -1
        try:
            estado = int(s._ctl.GetState())      # 0 inactiva · 1 activa · 2 expirada
        except Exception:
            pass
        lista.append({
            "nombre": nombre,
            "pid": s.ProcessId,
            "pico": pico,
            "mute": mute,
            "estado": estado,
            "titulo": _titulo(s),
            "meter": meter,
            "sesion": s,
        })
    return lista


ESTADOS = {0: "inactiva", 1: "activa", 2: "expirada"}


def _medir(filtro, segundos):
    """Mide el pico maximo durante N segundos."""
    segundos = float(segundos)
    fin = time.time() + segundos
    maximo = 0.0
    muestras = 0
    con_sonido = 0
    while time.time() < fin:
        for s in _sesiones(filtro):
            if s["meter"] is None:
                continue
            try:
                p = float(s["meter"].GetPeakValue())
            except Exception:
                continue
            muestras += 1
            if p > maximo:
                maximo = p
            if p > UMBRAL:
                con_sonido += 1
        time.sleep(MUESTREO)
    return maximo, muestras, con_sonido


def _main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 0
    accion = argv[1].lower()

    if accion in ("estado", "sesiones"):
        filas = _sesiones()
        if not filas:
            print("No hay ninguna sesion de audio.")
            return 0
        print("SESIONES DE AUDIO:")
        for s in filas:
            print("  {:<14} pid {:<7} {:<9} {:<7} pico {:.3f} {}".format(
                s["nombre"], s["pid"], ESTADOS.get(s["estado"], "?"),
                "MUDO" if s["mute"] else "sonido", s["pico"],
                ("· " + s["titulo"]) if s["titulo"] else ""))
        return 0

    if accion in ("suena", "pico", "esperar"):
        if len(argv) < 3:
            print("Falta el nombre del proceso. Ej: audio suena brave 3")
            return 2
        filtro = argv[2]
        segundos = argv[3] if len(argv) > 3 else "3"
        maximo, muestras, con_sonido = _medir(filtro, segundos)
        if accion == "pico":
            print("{:.4f}".format(maximo))
            return 0
        if muestras == 0:
            print("SILENCIO · '{}' no tiene sesion de audio: no esta sonando "
                  "nada (pausado, cerrado o mudo del todo)".format(filtro))
            return 1
        if maximo > UMBRAL:
            print("SUENA · {} · pico {:.3f} · {} de {} muestras con sonido".format(
                filtro, maximo, con_sonido, muestras))
            return 0
        print("SILENCIO · {} · pico {:.4f} en {} muestras · esta pausado o mudo".format(
            filtro, maximo, muestras))
        return 1

    if accion == "silenciar":
        if len(argv) < 4:
            print("Uso: audio silenciar <proceso> on|off")
            return 2
        filtro = argv[2]
        poner = argv[3].lower() in ("on", "1", "si", "sí", "true")
        tocadas = 0
        for s in _sesiones(filtro):
            try:
                s["sesion"].SimpleAudioVolume.SetMute(int(poner))
                tocadas += 1
            except Exception:
                pass
        print("{} sesion(es) de '{}' {}".format(
            tocadas, filtro, "silenciadas" if poner else "con sonido de nuevo"))
        return 0 if tocadas else 3

    if accion == "volumen":
        if len(argv) < 4:
            print("Uso: audio volumen <proceso> <0-100>")
            return 2
        filtro = argv[2]
        valor = max(0, min(100, int(argv[3]))) / 100.0
        tocadas = 0
        for s in _sesiones(filtro):
            try:
                s["sesion"].SimpleAudioVolume.SetMasterVolume(valor, None)
                tocadas += 1
            except Exception:
                pass
        print("{} sesion(es) de '{}' al {} %".format(tocadas, filtro, int(valor * 100)))
        return 0 if tocadas else 3

    print("Accion desconocida: {}. Mira la ayuda.".format(accion))
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv))
