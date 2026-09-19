# -*- coding: utf-8 -*-
"""
convertir_control.py — Conversor universal de archivos para JARVIS.
Usa CloudConvert (github.com/cloudconvert — el servicio de conversion mas
famoso: 200+ formatos: pdf, docx, xlsx, imagenes, audio, video, etc).
Plan gratis: 25 conversiones/dia, sin tarjeta.

Para activar (UNA vez):
  1) Sacar API key gratis en https://cloudconvert.com/dashboard/api/v2/keys
  2)  python cli.py convertir clave TU_API_KEY

Uso:
  python cli.py convertir <archivo> <formato>   -> convierte en la misma carpeta
  python cli.py convertir clave <API_KEY>       -> guarda la clave
  python cli.py convertir estado                -> clave lista? usos
"""
import json
import os
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_BASE = "https://api.cloudconvert.com/v2"
_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cloudconvert")
_CFG = os.path.join(_DIR, "config.json")


def _read_cfg():
    try:
        with open(_CFG, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_cfg(d):
    os.makedirs(_DIR, exist_ok=True)
    with open(_CFG, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


def _api_key():
    return _read_cfg().get("api_key", "")


def guardar_clave(clave):
    _write_cfg({"api_key": clave.strip(), "guardada": time.strftime("%Y-%m-%d %H:%M")})
    return "Clave de CloudConvert guardada. Ya puedes convertir archivos."


def _cabeceras():
    return {"Authorization": "Bearer " + _api_key(),
            "Content-type": "application/json"}


def convertir(archivo, formato):
    import requests
    if not os.path.isfile(archivo):
        return f"No encuentro el archivo: {archivo}"
    if not _api_key():
        return ("CloudConvert no activado. Saca tu API key gratis en "
                "https://cloudconvert.com/dashboard/api/v2/keys y ejecuta: "
                "python cli.py convertir clave TU_CLAVE")
    ext = os.path.splitext(archivo)[1].lstrip(".").lower()
    fmt = formato.lstrip(".").lower()
    if ext == fmt:
        return "El archivo ya tiene ese formato."

    print(f"[1/4] Creando trabajo de conversion: {ext} -> {fmt} ...")
    payload = {
        "tasks": {
            "upload-x": {"operation": "import/upload"},
            "convert-x": {"operation": "convert", "input": "upload-x",
                          "input_format": ext, "output_format": fmt},
            "export-x": {"operation": "export/url", "input": "convert-x"},
        }
    }
    try:
        r = requests.post(f"{_BASE}/jobs", headers=_cabeceras(),
                          json=payload, timeout=30)
        r.raise_for_status()
    except Exception as e:
        msg = str(e)
        if r.status_code == 401:
            return "Clave no valida. Revisa: python cli.py convertir clave TU_CLAVE"
        return f"Error creando el trabajo: {msg[:200]}"
    data = r.json().get("data", {})
    tasks = data.get("tasks", [])
    t_upload = next((t for t in tasks if t.get("operation") == "import/upload"), None)
    t_export = next((t for t in tasks if t.get("operation") == "export/url"), None)
    if not t_upload:
        return "No pude preparar la subida."

    print("[2/4] Subiendo archivo...")
    te = requests.get(f"{_BASE}/tasks/{t_upload['id']}",
                      headers=_cabeceras(), timeout=30).json()
    task = te.get("data", te)
    form = (task.get("result") or {}).get("form", {})
    if not form:
        return "CloudConvert no entrego el formulario de subida."
    with open(archivo, "rb") as f:
        rr = requests.post(form["url"], data=form.get("fields", {}),
                           files={"file": (os.path.basename(archivo), f)},
                           timeout=300)
    if rr.status_code not in (200, 201, 204):
        return f"Subida fallo (HTTP {rr.status_code})."

    print("[3/4] Convirtiendo... (espera)")
    tid = t_export["id"]
    for _ in range(120):
        time.sleep(3)
        te = requests.get(f"{_BASE}/tasks/{tid}", headers=_cabeceras(),
                          timeout=30).json()
        t = te.get("data", te)
        st = t.get("status")
        if st == "finished":
            break
        if st == "error":
            return ("Error convirtiendo: " +
                    str((t.get("result") or {}).get("message", st))[:200])
    else:
        return "Se agoto el tiempo de espera de CloudConvert."

    files = ((t.get("result") or {}).get("files") or [])
    if not files:
        return "CloudConvert termino pero no devolvio archivo."
    url = files[0].get("url")
    nombre = files[0].get("filename")
    if not url:
        return "Sin URL de descarga."
    print("[4/4] Descargando resultado...")
    base_dir = os.path.dirname(os.path.abspath(archivo))
    salida = os.path.join(base_dir, nombre or
                          (os.path.splitext(os.path.basename(archivo))[0] + "." + fmt))
    with requests.get(url, stream=True, timeout=300) as dr:
        dr.raise_for_status()
        with open(salida, "wb") as f:
            for chunk in dr.iter_content(chunk_size=65536):
                f.write(chunk)
    kb = os.path.getsize(salida) / 1024
    return (f"Convertido: {os.path.basename(archivo)} ({ext}) -> "
            f"{os.path.basename(salida)} ({fmt})\n"
            f"Ubicacion: {salida}  ({kb:.0f} KB)")


def _estado():
    cfg = _read_cfg()
    if cfg.get("api_key"):
        return ("CloudConvert activado (clave guardada el "
                f"{cfg.get('guardada', '?')}). 25 conversiones gratis/dia.")
    return ("CloudConvert SIN activar. Clave gratis en "
            "https://cloudconvert.com/dashboard/api/v2/keys")


def _main(argv):
    args = list(argv)  # argv[0]=alias
    if len(args) < 2:
        print(__doc__)
        return 2
    accion = args[1].lower()
    resto = args[2:]

    if accion == "clave":
        if not resto:
            print("Uso: python cli.py convertir clave TU_API_KEY")
            return 2
        print(guardar_clave(resto[0]))
        return 0
    if accion in ("estado", "status", "activado"):
        print(_estado())
        return 0
    if accion in ("", "convertir", "convert", "a"):
        if len(resto) < 2:
            print("Uso: python cli.py convertir <archivo> <formato>")
            return 2
        print(convertir(resto[0], resto[1]))
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))