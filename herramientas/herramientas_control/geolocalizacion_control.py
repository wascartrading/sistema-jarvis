# -*- coding: utf-8 -*-
"""
geolocalizacion_control.py — Geolocalizacion para JARVIS (Telegram).
Portado del desmenuzado JARVIS-HRZ (actions/geolocation) con codigo limpio.
Servicios GRATIS sin API key: Nominatim (geocode/reverse), ipapi.co e
ipinfo.io (por IP), Photon (sugerencias de ciudades/estados).

Uso:
  python cli.py geo                    -> mi ubicacion por IP
  python cli.py geo <ciudad>           -> geocodificar y mostrar detalle
  python cli.py geo reverse <lat> <lon>
  python cli.py geo fijar <ciudad>     -> guardar ubicacion manual preferida
  python cli.py geo info               -> ubicacion guardada
  python cli.py geo paises [texto]     -> listar/buscar paises
  python cli.py geo ciudades <estado>  -> sugerir ciudades de un estado
  python cli.py geo quitar             -> borrar ubicacion manual
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_UA = {"User-Agent": "JARVIS/1.0 (asistente personal)"}
_NOMINATIM = "https://nominatim.openstreetmap.org"
_PHOTON = "https://photon.komoot.io/api"
_CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
_CFG = os.path.join(_CONFIG_DIR, "geo_ubicacion.json")


# ---------- helpers ----------
def _get(url, timeout=12):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _sin(t):
    return t if not t else "".join(
        c for c in t.lower() if c.isalnum() or c.isspace())


def _read_cfg():
    try:
        with open(_CFG, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_cfg(d):
    os.makedirs(_CONFIG_DIR, exist_ok=True)
    with open(_CFG, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)


# ---------- por IP ----------
def detectar_por_ip():
    """Ubicacion por IP: ipapi.co con respaldo ipinfo.io."""
    for url in ("https://ipapi.co/json/", "https://ipinfo.io/json"):
        try:
            d = _get(url, timeout=8)
            if d.get("status") == "fail":
                continue
            ciudad = d.get("city") or d.get("region") or ""
            pais = d.get("country_name") or d.get("country") or ""
            lat = d.get("latitude") or (d.get("loc") or "").split(",")[0]
            lon = d.get("longitude") or (d.get("loc") or "").split(",")[1]
            pais_codigo = d.get("country_code") or d.get("country") or ""
            if lat and lon:
                return {"ciudad": ciudad, "pais": pais, "lat": float(lat),
                        "lon": float(lon), "pais_codigo": str(pais_codigo).upper(),
                        "via": url.split("/")[2]}
        except Exception:
            continue
    return None


# ---------- geocodificar ----------
def geocode_text(texto, limit=3):
    """Geocodifica texto libre (Nominatim). Devuelve lista de candidatos."""
    q = urllib.parse.quote(texto.strip())
    d = _get(f"{_NOMINATIM}/search?q={q}&format=json&addressdetails=1&limit={limit}",
             timeout=12)
    res = []
    for r in d or []:
        res.append({
            "nombre": r.get("display_name", ""),
            "lat": float(r.get("lat", 0)), "lon": float(r.get("lon", 0)),
            "tipo": r.get("type", ""),
            "ciudad": (r.get("address") or {}).get("city")
                      or (r.get("address") or {}).get("town")
                      or (r.get("address") or {}).get("village") or "",
            "estado": (r.get("address") or {}).get("state") or "",
            "pais": (r.get("address") or {}).get("country") or "",
        })
    return res


def reverse_geocode(lat, lon):
    d = _get(f"{_NOMINATIM}/reverse?lat={lat}&lon={lon}&format=json"
             "&addressdetails=1", timeout=12)
    a = d.get("address", {})
    return {"nombre": d.get("display_name", ""),
            "ciudad": a.get("city") or a.get("town") or a.get("village") or "",
            "estado": a.get("state") or "", "pais": a.get("country") or "",
            "codigo": a.get("country_code") or ""}


# ---------- sugerencias (Photon) ----------
def _buscar_photon(query, tipo=None):
    qs = {"q": query.strip(), "limit": 6, "lang": "es"}
    if tipo:
        qs["osm_tag"] = f"place:{tipo}"
    url = f"{_PHOTON}?{urllib.parse.urlencode(qs)}"
    try:
        d = _get(url, timeout=10)
    except Exception:
        return []
    res = []
    for f in (d.get("features") or []):
        props = f.get("properties", {})
        geo = f.get("geometry", {}).get("coordinates", [0, 0])
        res.append({"nombre": props.get("name", ""),
                    "estado": props.get("state", ""),
                    "pais": props.get("country", ""),
                    "tipo": props.get("osm_type", props.get("type", "")),
                    "lon": geo[0], "lat": geo[1]})
    return res


def listar_paises(texto=""):
    """Todos los paises (ISO 3166 embebido) filtrados por coincidencia."""
    paises = [
        ("PE", "Peru"), ("CO", "Colombia"), ("MX", "Mexico"), ("AR", "Argentina"),
        ("CL", "Chile"), ("VE", "Venezuela"), ("EC", "Ecuador"), ("BO", "Bolivia"),
        ("PY", "Paraguay"), ("UY", "Uruguay"), ("BR", "Brasil"), ("ES", "Espana"),
        ("US", "Estados Unidos"), ("GB", "Reino Unido"), ("FR", "Francia"),
        ("DE", "Alemania"), ("IT", "Italia"), ("PT", "Portugal"), ("CA", "Canada"),
        ("CN", "China"), ("JP", "Japon"), ("IN", "India"), ("AU", "Australia"),
    ]
    t = _sin(texto)
    lista = [(c, n) for c, n in paises if not t or t in _sin(n) or t == c.lower()]
    return ", ".join(f"{n} ({c})" for c, n in lista)


# ---------- ubicacion guardada ----------
def _ubicacion_guardada():
    cfg = _read_cfg()
    if cfg.get("lat") and cfg.get("lon"):
        return cfg
    return None


def guardar_ubicacion(lat, lon, nombre="", ciudad="", pais=""):
    _write_cfg({"lat": lat, "lon": lon, "nombre": nombre, "ciudad": ciudad,
                "pais": pais, "guardada": time.strftime("%Y-%m-%d %H:%M")})
    return _ubicacion_guardada()


def ubicacion_actual():
    """Prioridad: manual guardada -> por IP."""
    g = _ubicacion_guardada()
    if g:
        return g
    ip = detectar_por_ip()
    if ip:
        return ip
    return None


def formatear_ubicacion(u):
    if not u:
        return "No pude determinar la ubicacion."
    nombre = u.get("nombre")
    ciudad = u.get("ciudad")
    pais = u.get("pais")
    lat, lon = u.get("lat"), u.get("lon")
    linea = f"Lat {lat:.4f}, Lon {lon:.4f}"
    if nombre:
        linea = nombre
    elif ciudad or pais:
        linea = " ".join(x for x in (ciudad, pais) if x)
    return f"{linea}"


# ---------- CLI ----------
def _main(argv):
    args = list(argv)  # argv[0]=alias
    accion = args[1].lower() if len(args) > 1 else ""
    resto = args[2:]

    if accion in ("", "mi", "ip", "actual"):
        u = ubicacion_actual()
        if u and "nombre" not in u and u.get("via"):
            rev = reverse_geocode(u["lat"], u["lon"])
            u.update(rev)
        print(formatear_ubicacion(u))
        return 0

    if accion in ("geocode", "donde", "donde_esta", "buscar"):
        if not resto:
            print("Uso: python cli.py geo <ciudad>")
            return 2
        cand = geocode_text(" ".join(resto))
        if not cand:
            print(f"No encontre '{' '.join(resto)}'.")
            return 0
        for i, c in enumerate(cand, 1):
            print(f"{i}) {c['nombre']}")
            print(f"   Lat {c['lat']:.4f} · Lon {c['lon']:.4f} · {c['tipo']}")
        return 0

    if accion == "reverse":
        if len(resto) < 2:
            print("Uso: python cli.py geo reverse <lat> <lon>")
            return 2
        try:
            r = reverse_geocode(float(resto[0]), float(resto[1]))
            print(r["nombre"] or "Sin resultados")
        except Exception as e:
            print(f"Error: {e}")
        return 0

    if accion in ("fijar", "guardar", "set"):
        if resto:
            cand = geocode_text(" ".join(resto), limit=1)
            if cand:
                c = cand[0]
                guardar_ubicacion(c["lat"], c["lon"], c["nombre"],
                                  c["ciudad"], c["pais"])
                print(f"Ubicacion fijada: {c['nombre']}")
                return 0
            print(f"No encontre '{' '.join(resto)}'.")
            return 0
        u = detectar_por_ip()
        if u:
            rev = reverse_geocode(u["lat"], u["lon"])
            guardar_ubicacion(u["lat"], u["lon"], rev["nombre"],
                              rev["ciudad"], rev["pais"])
            print(f"Ubicacion fijada (IP): {rev['nombre']}")
        else:
            print("No pude detectar la ubicacion por IP.")
        return 0

    if accion in ("quitar", "borrar", "reset"):
        if os.path.exists(_CFG):
            os.remove(_CFG)
        print("Ubicacion manual eliminada. Volvi a usar la IP.")
        return 0

    if accion == "info":
        g = _ubicacion_guardada()
        if g:
            print("Ubicacion guardada: " + formatear_ubicacion(g))
        else:
            print("Sin ubicacion manual guardada. Uso IP.")
        return 0

    if accion in ("paises", "countries"):
        print(listar_paises(" ".join(resto) if resto else ""))
        return 0

    if accion in ("ciudades", "estados", "sugerir"):
        if not resto:
            print("Uso: python cli.py geo ciudades <estado o texto>")
            return 2
        sugs = _buscar_photon(" ".join(resto))
        if not sugs:
            print("Sin sugerencias.")
            return 0
        for s in sugs[:6]:
            loc = " ".join(x for x in (s["nombre"], s["estado"], s["pais"]) if x)
            print(f"- {loc} ({s['tipo']})")
        return 0

    # Sin subcomando -> se trata como nombre de lugar a geocodificar.
    cand = geocode_text(" ".join([accion] + resto), limit=3)
    if cand:
        for i, c in enumerate(cand, 1):
            print(f"{i}) {c['nombre']}")
            print(f"   Lat {c['lat']:.4f} · Lon {c['lon']:.4f} · {c['tipo']}")
        return 0

    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))