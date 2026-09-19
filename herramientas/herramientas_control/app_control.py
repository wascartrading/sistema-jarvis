"""
app_control.py — Control de ventanas y aplicaciones.
Portado del desmenuzado: abrir apps/URIs, cerrar apps, minimizar,
maximizar, restaurar, traer al frente.

Uso CLI:
  python cli.py app abrir "spotify" | app abrir "https://..."
  python cli.py app cerrar "chrome"
  python cli.py app ventana "titulo" min|max|restore|front
  python cli.py app listar [filtro]
"""
import ctypes
import os
import subprocess
import time
from ctypes import wintypes

from .browser_control import BRAVE_EXE

user32 = ctypes.windll.user32
SW_MINIMIZE = 6
SW_MAXIMIZE = 3
SW_RESTORE = 9
_EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

RUTAS_COMUNES_APPS = {
    "brave": r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "notepad": r"C:\Windows\notepad.exe",
    "bloc": r"C:\Windows\notepad.exe",
    "explorador": r"C:\Windows\explorer.exe",
    "explorer": r"C:\Windows\explorer.exe",
    "cmd": r"C:\Windows\System32\cmd.exe",
    "powershell": r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    "calculadora": r"C:\Windows\System32\calc.exe",
    "calc": r"C:\Windows\System32\calc.exe",
    "paint": r"C:\Windows\System32\mspaint.exe",
    "discord": os.path.expandvars(r"%LOCALAPPDATA%\Discord\Discord.exe"),
    "whatsapp": os.path.expandvars(r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe"),
    "spotify": os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
}


def _es_uri(t):
    return t.lower().startswith(("http://", "https://", "file://", "mailto:"))


def _buscar_en_start_menu(nombre):
    """Busca un acceso directo (.lnk) por nombre en el menu inicio."""
    import glob
    patrones = []
    base = os.environ.get("APPDATA", "")
    base_prog = os.environ.get("PROGRAMDATA", "")
    if base:
        patrones.append(os.path.join(base, "Microsoft", "Windows", "Start Menu", "Programs", "**", f"*{nombre}*.lnk"))
    if base_prog:
        patrones.append(os.path.join(base_prog, "Microsoft", "Windows", "Start Menu", "Programs", "**", f"*{nombre}*.lnk"))
    for patron in patrones:
        for lnk in glob.glob(patron, recursive=True)[:5]:
            return lnk
    return None


def _try_startfile(target):
    try:
        os.startfile(target)  # type: ignore
        return True
    except Exception:
        return False


def _abierto_al_frente(msg, nombre, espera=6.0):
    """Sella un 'abierto' con el traido-al-frente (orden del jefe 16/09/2026:
    'cada vez que abras una aplicacion, traela SIEMPRE al frente')."""
    ok, _h, titulo = traer_al_frente(nombre, espera=espera)
    if ok:
        return True, "%s | al frente: %s" % (msg, titulo or nombre)
    return True, "%s | AVISO: no pude traerla al frente" % msg


def abrir(target, esperar=True):
    """Abre una app por nombre, ruta o URI y la trae AL FRENTE (siempre)."""
    target = (target or "").strip()
    if not target:
        return False, "Falta el objetivo"
    # URI directa (siempre Brave) -> al frente: brave
    if _es_uri(target):
        subprocess.Popen([BRAVE_EXE, target], shell=False)
        return _abierto_al_frente(f"Abierto: {target}", "brave")
    # ruta exacta
    if os.path.exists(target):
        subprocess.Popen([target], shell=False)
        return _abierto_al_frente(f"Abierto: {target}",
                                  os.path.basename(target))
    # mapa de apps conocidas
    base = target.split("/")[0].split("\\")[0].strip().lower()
    if base in RUTAS_COMUNES_APPS:
        ruta = RUTAS_COMUNES_APPS[base]
        if os.path.exists(ruta):
            subprocess.Popen([ruta], shell=False)
            return _abierto_al_frente(f"Abierta: {target}", base)
    # WhatsApp DESKTOP (app de escritorio Store, NUNCA web) — regla del jefe 11/09/2026
    if base in ("whatsapp", "wa"):
        aumides = [
            "5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App",
        ]
        for aumid in aumides:
            try:
                subprocess.Popen(
                    ["explorer.exe", f"shell:AppsFolder\\{aumid}"], shell=False
                )
                return _abierto_al_frente(
                    "Abierta: WhatsApp (aplicación de escritorio)", "whatsapp")
            except Exception:
                continue
    # buscar en Start Menu
    lnk = _buscar_en_start_menu(target)
    if lnk:
        if _try_startfile(lnk):
            return _abierto_al_frente(f"Abierta: {target} (acceso directo)",
                                      base)
    # intento con startfile directo
    if _try_startfile(target):
        return _abierto_al_frente(f"Abierto: {target}", base)
    return False, f"No encontré la app: {target}"


def _ventanas(con_filtro=None):
    """Lista de (hwnd, titulo, visible) filtrando por texto opcional."""
    resultado = []

    @_EnumWindowsProc
    def _cb(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        largo = user32.GetWindowTextLengthW(hwnd)
        if largo == 0:
            return True
        buf = ctypes.create_unicode_buffer(largo + 1)
        user32.GetWindowTextW(hwnd, buf, largo + 1)
        titulo = buf.value
        if con_filtro and con_filtro.lower() not in titulo.lower():
            return True
        resultado.append((hwnd, titulo))
        return True

    user32.EnumWindows(_cb, 0)
    return resultado


def _buscar_varias(claves):
    """Busca la ventana que contenga alguna de las claves; varios intentos."""
    for intentos in range(8):
        ventanas = _ventanas()
        for hwnd, titulo in ventanas:
            for clave in claves:
                if clave.lower() in titulo.lower():
                    return hwnd, titulo
        time.sleep(0.5)
    return None, None


# ---------------------------------------------------------------------------
# TRAER AL FRENTE  ·  LA FORMA DEFINITIVA (orden del jefe, 16/09/2026)
# ---------------------------------------------------------------------------
# ORDEN: "cada vez que abras una aplicacion, traela SIEMPRE al frente; busca la
# forma definitiva y guardalo". Por que fallaba antes:
#   1) se buscaba la ventana SOLO por el titulo, y el Bloc de notas se llama
#      "promedio_notas.py: Bloc de notas" (asi que 'notepad' no coincidia nunca);
#   2) Windows BLOQUEA SetForegroundWindow cuando el proceso que llama no tiene
#      el foco (devuelve True y no hace nada).
# Aqui se resuelve todo:
#   - localiza por TITULO y, si no, por PROCESO (exe) con alias en espanol;
#   - restaura la ventana si esta minimizada;
#   - AttachThreadInput + BringWindowToTop + SetForegroundWindow + SetActiveWindow;
#   - si aun no entra: suelta una pulsacion de ALT (liberar el candado de foco)
#     y reintenta;
#   - VERIFICA con GetForegroundWindow y reintenta hasta `espera` segundos.
kernel32 = ctypes.windll.kernel32
SW_SHOW = 5
VK_MENU = 0x12
KEYEVENTF_KEYUP = 0x0002
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND,
                                            ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetForegroundWindow.restype = wintypes.HWND

ALIAS_PROCESO = {
    "bloc": "notepad.exe", "bloc de notas": "notepad.exe",
    "notepad": "notepad.exe", "notas": "notepad.exe",
    "calculadora": "calculatorapp.exe", "calc": "calculatorapp.exe",
    "explorador": "explorer.exe", "explorer": "explorer.exe",
    "brave": "brave.exe", "chrome": "chrome.exe", "edge": "msedge.exe",
    "cmd": "cmd.exe", "powershell": "powershell.exe", "paint": "mspaint.exe",
    "discord": "discord.exe", "whatsapp": "whatsapp.exe",
    "spotify": "spotify.exe", "code": "code.exe", "vscode": "code.exe",
    "opencode": "opencode.exe", "terminal": "windowsterminal.exe",
    "word": "winword.exe", "excel": "excel.exe",
}


def _titulo(hwnd):
    """Titulo de una ventana."""
    largo = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(largo + 1)
    user32.GetWindowTextW(hwnd, buf, largo + 1)
    return buf.value


def _pid_de_ventana(hwnd):
    pid = wintypes.DWORD(0)
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return int(pid.value)


def _exe_de_pid(pid):
    """Nombre del exe de un proceso (ctypes puro, sin dependencias nuevas)."""
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(1024)
        tam = wintypes.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(tam)):
            return os.path.basename(buf.value).lower()
    finally:
        kernel32.CloseHandle(h)
    return ""


def _hwnd_de_pid(pid):
    """Primera ventana visible CON titulo de un proceso (su ventana principal)."""
    hallados = []

    @_EnumWindowsProc
    def _cb(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        if _pid_de_ventana(hwnd) == pid and user32.GetWindowTextLengthW(hwnd) > 0:
            hallados.append(hwnd)
        return True

    user32.EnumWindows(_cb, 0)
    return hallados[0] if hallados else None


def _hwnds_de_proceso(exe):
    """Ventanas visibles de un proceso por nombre de exe (via tasklist)."""
    pids = []
    try:
        r = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq " + exe, "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10)
        for linea in (r.stdout or "").splitlines():
            partes = [p.strip('"') for p in linea.split('","')]
            if len(partes) >= 2 and partes[1].strip().isdigit():
                pids.append(int(partes[1].strip()))
    except Exception:
        return []
    salida = []
    for pid in pids:
        h = _hwnd_de_pid(pid)
        if h:
            salida.append(h)
    return salida


def _localizar_ventana(nombre):
    """(hwnd, titulo) de la ventana de `nombre`: primero por TITULO y, si no,
    por PROCESO (es lo que resuelve el caso del Bloc de notas)."""
    if not nombre:
        return None, ""
    clave = str(nombre).strip().lower()
    for hwnd, titulo in _ventanas(clave):      # 1) por titulo
        return hwnd, titulo
    candidatos = []                            # 2) por proceso
    if clave in ALIAS_PROCESO:
        candidatos.append(ALIAS_PROCESO[clave])
    if clave.endswith(".exe"):
        candidatos.append(clave)
    else:
        candidatos.append(clave + ".exe")
    for exe in candidatos:
        for hwnd in _hwnds_de_proceso(exe):
            return hwnd, _titulo(hwnd)
    return None, ""


def _forzar_frente(hwnd):
    """Un empujon completo: restaurar + adjuntar hilos + subir + ALT si hace
    falta. Devuelve True si la ventana acabo siendo la de primer plano."""
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    user32.ShowWindow(hwnd, SW_SHOW)
    fg = user32.GetForegroundWindow()
    hilo_yo = kernel32.GetCurrentThreadId()
    hilo_fg = 0
    if fg:
        pid_dummy = wintypes.DWORD(0)
        hilo_fg = user32.GetWindowThreadProcessId(fg, ctypes.byref(pid_dummy))
    pegado = False
    if hilo_fg and hilo_fg != hilo_yo:
        pegado = bool(user32.AttachThreadInput(hilo_yo, hilo_fg, True))
    try:
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        user32.SetActiveWindow(hwnd)
    finally:
        if pegado:
            user32.AttachThreadInput(hilo_yo, hilo_fg, False)
    if user32.GetForegroundWindow() != hwnd:
        # Truco final: pulsar y soltar ALT libera el candado de foco de Windows
        user32.keybd_event(VK_MENU, 0, 0, 0)
        user32.keybd_event(VK_MENU, 0, KEYEVENTF_KEYUP, 0)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    return user32.GetForegroundWindow() == hwnd


def traer_al_frente(nombre=None, hwnd=None, espera=6.0):
    """FORMA DEFINITIVA de poner al frente una app (orden del jefe 16/09/2026).

    `nombre` puede ser un titulo, un nombre de app ("notepad", "bloc de notas",
    "whatsapp") o un .exe. Reintenta y VERIFICA hasta `espera` segundos.
    Devuelve (ok, hwnd, titulo)."""
    limite = time.time() + max(0.0, float(espera))
    h = hwnd
    titulo = _titulo(hwnd) if hwnd else ""
    while True:
        if not h:
            h, titulo = _localizar_ventana(nombre)
        if h and _forzar_frente(h):
            return True, h, titulo
        if time.time() >= limite:
            break
        time.sleep(0.2)
    return False, h, titulo


def cerrar(nombre):
    """Cierra una app por nombre de proceso (sin forzar, WM_CLOSE)."""
    nombre = nombre.strip()
    if not nombre.endswith(".exe"):
        nombre += ".exe"
    try:
        r = subprocess.run(["taskkill", "/IM", nombre], capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            return True, f"Cierre enviado a {nombre}"
        r2 = subprocess.run(["taskkill", "/IM", nombre, "/F"], capture_output=True, text=True, timeout=15)
        if r2.returncode == 0:
            return True, f"%s cerrado a la fuerza" % nombre
        return False, f"No hay proceso {nombre}"
    except Exception as e:
        return False, f"Error cerrando {nombre}: {e!r}"


def ventana(accion, filtro="", cierre_forzado=False):
    """min|max|restore|front|cerrar sobre la ventana que coincida con filtro.

    'front' va PRIMERO y por su cuenta: usa traer_al_frente(), que busca por
    titulo Y por proceso (aqui se arreglo el caso 'notepad' del 16/09/2026)."""
    if accion in ("front", "frente", "traer"):
        if filtro:
            ok, hwnd, titulo = traer_al_frente(filtro)
            if ok:
                return True, "Al frente: %s" % (titulo or filtro)
            if hwnd:
                return False, ("Encontré '%s' (%s) pero no pude ponerla al frente"
                               % (filtro, titulo))
            return False, f"No encontré ventana con '{filtro}'"
        targets = _ventanas()
        return True, "Al frente %d ventana/s" % sum(
            1 for hwnd, _t in targets[:3] if _forzar_frente(hwnd))
    ventanas = _ventanas(filtro) if filtro else None
    if not ventanas and filtro:
        return False, f"No encontré ventana con '{filtro}'"
    targets = ventanas if ventanas else _ventanas()
    if accion in ("min", "minimizar"):
        estado = SW_MINIMIZE
    elif accion in ("max", "maximizar"):
        estado = SW_MAXIMIZE
    elif accion in ("restore", "restaurar"):
        estado = SW_RESTORE
    elif accion in ("cerrar", "close"):
        for hwnd, titulo in targets:
            user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
            time.sleep(0.2)
        return True, f"Ventanas cerradas: {len(targets)}"
    else:
        return False, f"Accion desconocida: {accion}"
    for hwnd, titulo in targets[:3]:
        user32.ShowWindow(hwnd, estado)
        time.sleep(0.1)
    return True, f"{accion} aplicada a {len(targets[:3])} ventana/s"


def listar(filtro=""):
    ventanas = _ventanas(filtro) if filtro else _ventanas()
    if not ventanas:
        return "Sin ventanas visibles"
    return "\n".join(f"- {t} (hwnd={h})" for h, t in ventanas[:25])


def _main(argv):
    import sys
    import time
    if len(argv) < 2:
        print("Acciones: abrir|cerrar|ventana|listar")
        return 2
    accion = argv[1].lower()
    resto = argv[2:]
    if accion == "abrir":
        if not resto:
            print("Falta la app/URL")
            return 2
        ok, msg = abrir(" ".join(resto))
        print(msg)
        return 0 if ok else 2
    if accion == "cerrar":
        if not resto:
            print("Falta el nombre")
            return 2
        ok, msg = cerrar(resto[0])
        print(msg)
        return 0 if ok else 2
    if accion == "ventana":
        if len(resto) < 1:
            print("Falta accion: min|max|restore|front|cerrar  [filtro]")
            return 2
        sub = resto[0].lower()
        filtro = " ".join(resto[1:]) if len(resto) > 1 else ""
        ok, msg = ventana(sub, filtro)
        print(msg)
        return 0 if ok else 2
    if accion == "listar":
        filtro = " ".join(resto) if resto else ""
        print(listar(filtro))
        return 0
    print(f"Accion desconocida: {accion}")
    return 2


if __name__ == "__main__":
    _main(sys.argv)