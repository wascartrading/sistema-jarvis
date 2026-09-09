# -*- coding: utf-8 -*-
"""supabase.py — Nube de JARVIS sobre Supabase Storage.

Permite subir, listar, descargar y borrar archivos en la nube usando la
API REST de Supabase (Storage). No requiere el SDK: usa urllib/requests.

Credenciales en: supabase_config.json (junto a este archivo, en Proyectos de asistente)
{
  "url": "https://XXXX.supabase.co",
  "apikey": "eyJ...",
  "bucket": "jarvis"
}

Uso desde consola:
  python supabase.py subir ruta\archivo.txt [carpeta/remota]
  python supabase.py listar [prefijo]
  python supabase.py bajar ruta/remota.txt destino\archivo.txt
  python supabase.py borrar ruta/remota.txt
"""

import json
import os
import sys

try:
    import requests
except ImportError:
    print("ERROR: falta la libreria requests. Instalarla con: pip install requests")
    sys.exit(1)

PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(PROYECTO, "supabase_config.json")
DEFAULT_BUCKET = "jarvis"


def cargar_config():
    if not os.path.isfile(CONFIG_FILE):
        print("ERROR: no existe %s" % CONFIG_FILE)
        print("Crear la cuenta en supabase.com y poner url y apikey en ese archivo.")
        sys.exit(1)
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    if not cfg.get("url") or not cfg.get("apikey"):
        print("ERROR: falta 'url' o 'apikey' en %s" % CONFIG_FILE)
        sys.exit(1)
    return cfg


def _headers(cfg):
    return {
        "apikey": cfg["apikey"],
        "Authorization": "Bearer " + cfg["apikey"],
    }


def _base(cfg):
    return cfg["url"].rstrip("/") + "/storage/v1/object"


def subir(ruta_local, ruta_remota, bucket=None):
    cfg = cargar_config()
    bucket = bucket or cfg.get("bucket", DEFAULT_BUCKET)
    if not os.path.isfile(ruta_local):
        print("ERROR: no existe el archivo %s" % ruta_local)
        return False
    ruta_remota = ruta_remota.replace("\\", "/").lstrip("/")
    url = "%s/%s/%s" % (_base(cfg), bucket, ruta_remota)
    with open(ruta_local, "rb") as f:
        r = requests.post(url, headers=_headers(cfg), data=f)
    if r.status_code in (200, 201):
        print("Subido OK: %s -> %s (%d bytes)" % (ruta_local, ruta_remota, os.path.getsize(ruta_local)))
        return True
    print("ERROR al subir (%s): %s" % (r.status_code, r.text[:300]))
    return False


def listar(prefijo="", bucket=None):
    cfg = cargar_config()
    bucket = bucket or cfg.get("bucket", DEFAULT_BUCKET)
    url = "%s/list/%s" % (_base(cfg), bucket)
    r = requests.post(url, headers=_headers(cfg),
                      json={"prefix": prefijo, "limit": 1000, "offset": 0})
    if r.status_code != 200:
        print("ERROR al listar (%s): %s" % (r.status_code, r.text[:300]))
        return None
    datos = r.json()
    if not datos:
        print("(vacio: no hay archivos en la nube)")
        return []
    for item in datos:
        meta = item.get("metadata") or {}
        print("- %s  (%s bytes)" % (item.get("name"), meta.get("size", "?")))
    return datos


def bajar(ruta_remota, destino_local, bucket=None):
    cfg = cargar_config()
    bucket = bucket or cfg.get("bucket", DEFAULT_BUCKET)
    ruta_remota = ruta_remota.replace("\\", "/").lstrip("/")
    url = "%s/%s/%s" % (_base(cfg), bucket, ruta_remota)
    r = requests.get(url, headers=_headers(cfg))
    if r.status_code != 200:
        print("ERROR al bajar (%s): %s" % (r.status_code, r.text[:300]))
        return False
    os.makedirs(os.path.dirname(os.path.abspath(destino_local)), exist_ok=True)
    with open(destino_local, "wb") as f:
        f.write(r.content)
    print("Descargado OK: %s -> %s (%d bytes)" % (ruta_remota, destino_local, len(r.content)))
    return True


def borrar(ruta_remota, bucket=None):
    cfg = cargar_config()
    bucket = bucket or cfg.get("bucket", DEFAULT_BUCKET)
    ruta_remota = ruta_remota.replace("\\", "/").lstrip("/")
    url = "%s/%s" % (_base(cfg), bucket)
    r = requests.delete(url, headers=_headers(cfg), json={"prefixes": [ruta_remota]})
    if r.status_code == 200:
        print("Borrado OK: %s" % ruta_remota)
        return True
    print("ERROR al borrar (%s): %s" % (r.status_code, r.text[:300]))
    return False


def crear_bucket(nombre, publico=False):
    """Crea un bucket nuevo (necesita la service_role key, no la anon)."""
    cfg = cargar_config()
    url = cfg["url"].rstrip("/") + "/storage/v1/bucket"
    r = requests.post(url, headers=_headers(cfg),
                      json={"id": nombre, "name": nombre,
                            "public": publico, "file_size_limit": None,
                            "allowed_mime_types": None})
    if r.status_code in (200, 201):
        print("Bucket creado OK: %s" % nombre)
        return True
    print("ERROR al crear bucket (%s): %s" % (r.status_code, r.text[:300]))
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    accion = sys.argv[1].lower()
    if accion == "subir" and len(sys.argv) >= 3:
        remota = sys.argv[3] if len(sys.argv) >= 4 else os.path.basename(sys.argv[2])
        subir(sys.argv[2], remota)
    elif accion == "listar":
        listar(sys.argv[2] if len(sys.argv) >= 3 else "")
    elif accion == "bajar" and len(sys.argv) >= 4:
        bajar(sys.argv[2], sys.argv[3])
    elif accion == "borrar" and len(sys.argv) >= 3:
        borrar(sys.argv[2])
    elif accion == "crear-bucket" and len(sys.argv) >= 3:
        crear_bucket(sys.argv[2], "--publico" in sys.argv)
    else:
        print(__doc__)
        sys.exit(1)
