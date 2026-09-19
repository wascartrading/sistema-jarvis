"""
system_control.py — Monitor y control del sistema: CPU/RAM/disco, volumen,
brillo, plan de energia, foco. Portado del desmenuzado.

Uso CLI:
  python cli.py system info                       (CPU/RAM/disco)
  python cli.py system volumen up|down|mute|N
  python cli.py system brillo 50                  (0-100)
  python cli.py system energia balanced|max|saving
  python cli.py system papelera
"""
import ctypes
import os
import subprocess
from ctypes import wintypes

# ---- CPU/RAM/disco ----
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def info():
    mem = MEMORYSTATUSEX()
    mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
    ram_total = mem.ullTotalPhys / (1024 ** 3)
    ram_libre = mem.ullAvailPhys / (1024 ** 3)
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average"],
            capture_output=True, text=True, timeout=15)
        cpu_val = (r.stdout or r.stderr or "").strip()
        cpu_txt = (f"{float(cpu_val):.0f}%" if cpu_val.replace(".", "").isdigit() else "?")
    except Exception:
        cpu_txt = "?"
    discos = []
    import shutil
    for letra in "CDE":
        try:
            uso = shutil.disk_usage(letra + ":\\")
            discos.append(f"{letra}: {uso.used / (1024**3):.1f}G de {uso.total / (1024**3):.1f}G ({uso.used / uso.total * 100:.0f}%)")
        except Exception:
            pass
    linea = [f"CPU: {cpu_txt} | RAM: {ram_total-mem.dwMemoryLoad/100*ram_total:.1f}G usados de {ram_total:.1f}G"]
    linea.append(f"RAM libre: {ram_libre:.1f}G")
    linea.extend(discos)
    return "\n".join(linea)


# ---- Volumen (teclas multimedia, sin dependencias) ----
VK_VOL_MUTE = 0xAD
VK_VOL_DOWN = 0xAE
VK_VOL_UP = 0xAF


def volumen(accion, valor=None):
    if accion in ("up", "subir", "+"):
        ctypes.windll.user32.keybd_event(VK_VOL_UP, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_VOL_UP, 0, 2, 0)
        return "Volumen arriba"
    if accion in ("down", "bajar", "-"):
        ctypes.windll.user32.keybd_event(VK_VOL_DOWN, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_VOL_DOWN, 0, 2, 0)
        return "Volumen abajo"
    if accion in ("mute", "silenciar"):
        ctypes.windll.user32.keybd_event(VK_VOL_MUTE, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_VOL_MUTE, 0, 2, 0)
        return "Silencio alternado"
    if accion in ("set", "fijar") and valor is not None:
        # Escala aproximada: 100 pasos de tecla desde 0 hasta valor
        pasos = max(0, min(int(valor), 100)) // 2
        ctypes.windll.user32.keybd_event(VK_VOL_MUTE, 0, 0, 0)
        ctypes.windll.user32.keybd_event(VK_VOL_MUTE, 0, 2, 0)
        for _ in range(50):
            ctypes.windll.user32.keybd_event(VK_VOL_DOWN, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_VOL_DOWN, 0, 2, 0)
        for _ in range(pasos):
            ctypes.windll.user32.keybd_event(VK_VOL_UP, 0, 0, 0)
            ctypes.windll.user32.keybd_event(VK_VOL_UP, 0, 2, 0)
        return f"Volumen hacia {valor}"
    return "Accion de volumen desconocida"


# ---- Brillo (WMI/powercfg via PowerShell) ----
def brillo(valor):
    try:
        script = (
            "$m = Get-CimInstance -Namespace root/WMI -ClassName "
            "WmiMonitorBrightnessMethods; if ($m) { "
            f"$m.WmiSetBrightness(1,{int(valor)}) }} else {{ 'sin soporte' }}"
        )
        r = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                            capture_output=True, text=True, timeout=15)
        salida = (r.stdout or r.stderr or "").strip()
        return f"Brillo -> {valor}" if "sin soporte" not in salida else "Brillo no soportado en este equipo"
    except Exception as e:
        return f"Error brillo: {e!r}"


# ---- Plan de energia ----
def energia(plan):
    planes = {
        "balanced": "381b4222-f694-41f0-9685-ff5bb260df2e",
        "max": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
        "saving": "a1841308-3541-4fab-bc81-f71556f20b4a",
        "alto": "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c",
        "ahorro": "a1841308-3541-4fab-bc81-f71556f20b4a",
        "economico": "a1841308-3541-4fab-bc81-f71556f20b4a",
    }
    guid = planes.get(str(plan).lower())
    if not guid:
        return f"Plan desconocido: {plan}"
    r = subprocess.run(["powercfg", "/setactive", guid], capture_output=True, text=True, timeout=15)
    return "Plan de energia cambiado" if r.returncode == 0 else f"Error: {r.stderr.strip()}"


def _main(argv):
    import sys
    if len(argv) < 2:
        print("Acciones: info|volumen|brillo|energia")
        return 2
    accion = argv[1].lower()
    resto = argv[2:]
    if accion == "info":
        print(info())
        return 0
    if accion in ("volumen", "vol"):
        if not resto:
            print("Falta: up|down|mute|set <N>")
            return 2
        valor = resto[1] if len(resto) > 1 else None
        print(volumen(resto[0].lower(), valor))
        return 0
    if accion == "brillo":
        if not resto:
            print("Falta el valor 0-100")
            return 2
        print(brillo(resto[0]))
        return 0
    if accion == "energia":
        if not resto:
            print("Falta: balanced|max|saving")
            return 2
        print(energia(resto[0]))
        return 0
    if accion == "papelera":
        from .file_controller import vaciar_papelera
        print(vaciar_papelera())
        return 0
    print(f"Accion desconocida: {accion}")
    return 2


if __name__ == "__main__":
    _main(sys.argv)