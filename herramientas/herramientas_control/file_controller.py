"""
file_controller.py — Buscar, abrir, mover y borrar archivos (a la papelera),
limpiar temporales y organizar duplicados por MD5. Portado del desmenuzado.

Uso CLI:
  python cli.py files buscar "nombre" [carpeta]
  python cli.py files abrir "ruta"
  python cli.py files papelera "ruta"
  python cli.py files limpiar_temp
  python cli.py files duplicados "carpeta"
  python cli.py files vaciar_papelera
"""
import ctypes
import hashlib
import os
import shutil
import time
from ctypes import wintypes

CARPETAS = {
    "escritorio": lambda: os.path.join(os.path.expanduser("~"), "Desktop"),
    "desktop": lambda: os.path.join(os.path.expanduser("~"), "Desktop"),
    "documentos": lambda: os.path.join(os.path.expanduser("~"), "Documents"),
    "documents": lambda: os.path.join(os.path.expanduser("~"), "Documents"),
    "descargas": lambda: os.path.join(os.path.expanduser("~"), "Downloads"),
    "downloads": lambda: os.path.join(os.path.expanduser("~"), "Downloads"),
    "musica": lambda: os.path.join(os.path.expanduser("~"), "Music"),
    "music": lambda: os.path.join(os.path.expanduser("~"), "Music"),
    "videos": lambda: os.path.join(os.path.expanduser("~"), "Videos"),
    "imagenes": lambda: os.path.join(os.path.expanduser("~"), "Pictures"),
    "home": lambda: os.path.expanduser("~"),
}


def _ruta_base(nombre):
    nombre_l = (nombre or "").lower()
    if nombre_l in CARPETAS:
        return CARPETAS[nombre_l]()
    return nombre


def _buscar(nombre, carpeta, maximo=30):
    hits = []
    raiz = _ruta_base(carpeta) if carpeta else os.path.expanduser("~")
    if not os.path.isdir(raiz):
        return [], f"No existe la carpeta: {raiz}"
    nombre_l = (nombre or "").lower()
    for dirpath, dirnames, filenames in os.walk(raiz):
        for f in filenames:
            if nombre_l in f.lower():
                hits.append(os.path.join(dirpath, f))
                if len(hits) >= maximo:
                    return hits, None
        if len(hits) >= maximo:
            break
    return hits, None


def buscar(nombre, carpeta=None, maximo=15):
    hits, err = _buscar(nombre, carpeta, maximo)
    if err:
        return err
    if not hits:
        return f"Sin resultados para '{nombre}'"
    lineas = [f"Encontré {len(hits)} archivo/s:"]
    for h in hits[:maximo]:
        try:
            tam = os.path.getsize(h)
            lineas.append(f"- {h} ({tam:,} bytes)")
        except Exception:
            lineas.append(f"- {h}")
    return "\n".join(lineas)


def abrir(ruta):
    """Abre un archivo y trae AL FRENTE la ventana que lo muestra (orden del
    jefe, 16/09/2026: "cada vez que abras una aplicacion, traela SIEMPRE al
    frente"). Como no se sabe que programa abrira el archivo, se comparan las
    ventanas de ANTES y de DESPUES y se enfoca la nueva (verificando de verdad
    con GetForegroundWindow via app_control.traer_al_frente)."""
    if not os.path.exists(ruta):
        return False, f"No existe: {ruta}"
    try:
        from . import app_control as ac
    except Exception:
        ac = None
    antes = set(h for h, _t in ac._ventanas()) if ac else set()
    os.startfile(ruta)  # type: ignore
    if ac is None:
        return True, f"Abierto: {ruta}"
    limite = time.time() + 6.0
    while time.time() < limite:
        for hwnd, titulo in ac._ventanas():
            if hwnd not in antes:
                ok, _h, tit = ac.traer_al_frente(hwnd=hwnd, espera=2.0)
                if ok:
                    return True, "Abierto al frente: %s" % (tit or titulo)
        time.sleep(0.25)
    return True, "Abierto: %s (no detecté ventana nueva que enfocar)" % ruta


def _a_papelera_shell(ruta):
    """Mueve a la papelera via SHFileOperationW (sin borrado definitivo)."""
    try:
        shell32 = ctypes.windll.shell32
        SHFILEOPSTRUCT = ctypes.c_void_p
        from ctypes import Structure

        class SHFILEOPSTRUCTW(Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("wFunc", wintypes.UINT),
                ("pFrom", wintypes.LPCWSTR),
                ("pTo", wintypes.LPCWSTR),
                ("fFlags", ctypes.c_ushort),
                ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", ctypes.c_void_p),
                ("lpszProgressTitle", wintypes.LPCWSTR),
            ]

        FO_DELETE = 3
        FOF_ALLOWUNDO = 0x40
        FOF_NOCONFIRMATION = 0x10
        FOF_SILENT = 0x4
        op = SHFILEOPSTRUCTW()
        op.wFunc = FO_DELETE
        op.pFrom = ruta + "\0\0"
        op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT
        res = shell32.SHFileOperationW(ctypes.byref(op))
        return res == 0
    except Exception as e:
        print(f"[files] papelera shell error: {e!r}")
        return False


def papelera(ruta, forzar=False):
    if not os.path.exists(ruta):
        return False, f"No existe: {ruta}"
    if _a_papelera_shell(ruta):
        return True, f"A la papelera: {ruta}"
    # fallback
    try:
        if forzar:
            shutil.rmtree(ruta) if os.path.isdir(ruta) else os.remove(ruta)
            return True, f"Borrado definitivo: {ruta}"
        destino = os.path.join(os.environ.get("TEMP", r"C:\Windows\Temp"), "jarvis_papelera", os.path.basename(ruta))
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        shutil.move(ruta, destino)
        return True, f"Movido a respaldo temporal: {destino}"
    except Exception as e:
        return False, f"Error: {e!r}"


def limpiar_temp():
    import tempfile
    borrados = 0
    for base in [tempfile.gettempdir(), r"C:\Windows\Temp"]:
        for root, dirs, files in os.walk(base):
            for f in files:
                try:
                    os.remove(os.path.join(root, f))
                    borrados += 1
                except Exception:
                    pass
            break  # solo la raiz, para no tardar
    return f"Limpieza temp: {borrados} archivos borrados"


def vaciar_papelera():
    try:
        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0)
        return "Papelera vaciada"
    except Exception as e:
        return f"Error: {e!r}"


def duplicados(carpeta):
    """Busca archivos duplicados por MD5 dentro de la carpeta."""
    carpeta = _ruta_base(carpeta) if carpeta else None
    if not carpeta or not os.path.isdir(carpeta):
        return f"Carpeta inválida: {carpeta}"
    hash_map = {}
    total = 0
    for dirpath, _d, filenames in os.walk(carpeta):
        for f in filenames:
            ruta = os.path.join(dirpath, f)
            try:
                with open(ruta, "rb") as fh:
                    md5 = hashlib.md5(fh.read(1 << 20)).hexdigest()  # primeros 1MB
                hash_map.setdefault(md5, []).append(ruta)
                total += 1
            except Exception:
                pass
    dups = {k: v for k, v in hash_map.items() if len(v) > 1}
    if not dups:
        return f"Sin duplicados en {total} archivos"
    lineas = [f"{len(dups)} grupo/s de duplicados:"]
    for k, v in list(dups.items())[:10]:
        lineas.append(f"- {len(v)} copias:")
        for r in v:
            lineas.append(f"    {r}")
    return "\n".join(lineas)


def _main(argv):
    import sys
    if len(argv) < 2:
        print("Acciones: buscar|abrir|papelera|limpiar_temp|duplicados|vaciar_papelera")
        return 2
    accion = argv[1].lower()
    resto = argv[2:]
    if accion == "buscar":
        if not resto:
            print("Falta el nombre")
            return 2
        nombre = resto[0]
        carpeta = resto[1] if len(resto) > 1 else None
        print(buscar(nombre, carpeta))
        return 0
    if accion == "abrir":
        if not resto:
            print("Falta la ruta")
            return 2
        ok, msg = abrir(resto[0])
        print(msg)
        return 0 if ok else 2
    if accion == "papelera":
        if not resto:
            print("Falta la ruta")
            return 2
        ok, msg = papelera(resto[0])
        print(msg)
        return 0 if ok else 2
    if accion == "limpiar_temp":
        print(limpiar_temp())
        return 0
    if accion == "vaciar_papelera":
        print(vaciar_papelera())
        return 0
    if accion == "duplicados":
        carpeta = resto[0] if resto else None
        print(duplicados(carpeta))
        return 0
    print(f"Accion desconocida: {accion}")
    return 2


if __name__ == "__main__":
    _main(sys.argv)