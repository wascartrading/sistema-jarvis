# -*- coding: utf-8 -*-
"""
clima_control.py — Clima enriquecido para JARVIS (Telegram).
Usa Open-Meteo (gratis, SIN API key) + geocoding de Open-Meteo.
Portado del desmenuzado JARVIS-HRZ (actions/clima_panel) con codigo limpio.

Uso:
  python cli.py clima "Lima"
  python cli.py clima ""            -> ubicacion por IP
"""
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

# Consola Windows (cp1252): nunca revienta por caracteres Unicode.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_UA = {"User-Agent": "JARVIS/1.0"}
_GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# codigo WMO -> (descripcion es, emoji)
_WMO = {
    0: ("Despejado", "☀️"), 1: ("Mayormente despejado", "🌤️"),
    2: ("Parcialmente nublado", "⛅"), 3: ("Nublado", "☁️"),
    45: ("Niebla", "🌫️"), 48: ("Niebla con escarcha", "🌫️"),
    51: ("Llovizna ligera", "🌦️"), 53: ("Llovizna moderada", "🌦️"),
    55: ("Llovizna intensa", "🌧️"), 56: ("Llovizna helada", "🌧️"),
    57: ("Llovizna helada intensa", "🌧️"),
    61: ("Lluvia ligera", "🌧️"), 63: ("Lluvia moderada", "🌧️"),
    65: ("Lluvia fuerte", "🌧️"), 66: ("Lluvia helada", "🌧️"),
    67: ("Lluvia helada fuerte", "🌧️"),
    71: ("Nieve ligera", "❄️"), 73: ("Nieve moderada", "❄️"),
    75: ("Nieve intensa", "❄️"), 77: ("Granos de nieve", "❄️"),
    80: ("Chubascos ligeros", "🌦️"), 81: ("Chubascos moderados", "🌧️"),
    82: ("Chubascos violentos", "⛈️"), 85: ("Chubascos de nieve", "❄️"),
    86: ("Chubascos de nieve intensos", "❄️"),
    95: ("Tormenta electrica", "⛈️"), 96: ("Tormenta con granizo", "⛈️"),
    99: ("Tormenta con granizo fuerte", "⛈️"),
}

_DIAS = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]


def _pedir(url, timeout=12):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _ciudad_por_ip():
    """Ubicacion aproximada por IP (ip-api, gratis)."""
    try:
        d = _pedir("http://ip-api.com/json/?lang=es", timeout=8)
        if d.get("status") == "success":
            return {
                "ciudad": d.get("city", ""),
                "pais": d.get("country", ""),
                "lat": d.get("lat"),
                "lon": d.get("lon"),
            }
    except Exception:
        pass
    return None


def geocodificar(ciudad):
    """Devuelve dict con lat/lon/nombre o None."""
    q = urllib.parse.quote(ciudad.strip())
    d = _pedir(f"{_GEO_URL}?name={q}&count=1&language=es&format=json", timeout=10)
    res = (d or {}).get("results") or []
    if not res:
        return None
    r = res[0]
    admin = r.get("admin1") or ""
    pais = r.get("country") or ""
    nombre = r.get("name") or ciudad
    if admin and admin != nombre:
        nombre = f"{nombre}, {admin}"
    if pais:
        nombre = f"{nombre} ({pais})"
    return {"ciudad": nombre, "lat": r["latitude"], "lon": r["longitude"]}


def _wmo(codigo):
    return _WMO.get(codigo, ("Estado desconocido", "🌡️"))


def _recomendaciones(temp, sensacion, precip, viento, codigo, humedad):
    """Recomendaciones sencillas segun condiciones (estilo desmenuzado)."""
    rec = []
    if codigo in (95, 96, 99):
        rec.append("tormenta en la zona: mejor quedarse en casa")
    if precip > 0.5:
        rec.append("lleva paraguas, hay precipitaciones")
    if temp < 12:
        rec.append("frio: abrigate bien")
    elif temp < 18 and sensacion < temp:
        rec.append("sensacion termica baja: una chaqueta ligera no sobra")
    elif temp >= 28:
        rec.append("calor: hidratate y evita el sol fuerte")
    if humedad >= 85:
        rec.append("ambiente muy humedo")
    if viento >= 25:
        rec.append("viento notable, cuidado con objetos sueltos")
    if not rec:
        rec.append("condiciones agradables, dia tranquilo")
    return " · ".join(rec[:3])


def obtener_clima(ciudad=None):
    """Devuelve dict listo para imprimir."""
    if ciudad and ciudad.strip():
        geo = geocodificar(ciudad)
        if not geo:
            return {"error": f"No encontre la ciudad '{ciudad}'. Revisa el nombre."}
    else:
        geo = _ciudad_por_ip()
        if not geo:
            return {"error": "No pude detectar tu ubicacion. Dime una ciudad."}
    params = urllib.parse.urlencode({
        "latitude": geo["lat"], "longitude": geo["lon"],
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                   "weather_code,wind_speed_10m,precipitation,is_day",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                 "precipitation_probability_max",
        "timezone": "auto", "forecast_days": 3,
    })
    d = _pedir(f"{_FORECAST_URL}?{params}", timeout=15)
    cur = d.get("current", {})
    daily = d.get("daily", {})
    desc, emoji = _wmo(cur.get("weather_code"))
    temp = cur.get("temperature_2m")
    sens = cur.get("apparent_temperature", temp)
    hum = cur.get("relative_humidity_2m")
    viento = cur.get("wind_speed_10m")
    precip = cur.get("precipitation", 0)
    rec = _recomendaciones(temp, sens, precip, viento, cur.get("weather_code"), hum)
    hoy = datetime.now().date()
    dias = []
    for i in range(3):
        fecha = hoy + timedelta(days=i)
        ddesc, demoji = _wmo((daily.get("weather_code") or [0] * 3)[i])
        dias.append({
            "dia": _DIAS[fecha.weekday()],
            "fecha": fecha.strftime("%d/%m"),
            "desc": ddesc, "emoji": demoji,
            "max": (daily.get("temperature_2m_max") or [None] * 3)[i],
            "min": (daily.get("temperature_2m_min") or [None] * 3)[i],
            "lluvia": (daily.get("precipitation_probability_max") or [None] * 3)[i],
        })
    return {
        "ciudad": geo["ciudad"],
        "ahora": {"temp": temp, "sensacion": sens, "humedad": hum,
                  "viento": viento, "precip": precip, "desc": desc, "emoji": emoji},
        "recomendacion": rec,
        "dias": dias,
    }


def formatear(clima):
    if "error" in clima:
        return clima["error"]
    a = clima["ahora"]
    t = clima["ciudad"]
    l1 = f"{a['emoji']} Clima ahora en {t}: {a['desc'].lower()}, {a['temp']:g}°C"
    if a["sensacion"] is not None and abs(a["sensacion"] - a["temp"]) >= 1:
        l1 += f" (sensacion {a['sensacion']:g}°C)"
    extras = []
    if a["humedad"] is not None:
        extras.append(f"humedad {a['humedad']:g}%")
    if a["viento"] is not None:
        extras.append(f"viento {a['viento']:g} km/h")
    if a["precip"] and a["precip"] > 0:
        extras.append(f"lluvia {a['precip']:g} mm")
    lineas = [l1]
    if extras:
        lineas.append(" | ".join(extras))
    lineas.append("")
    lineas.append("Pronostico 3 dias:")
    for d in clima["dias"]:
        ll = ""
        if d["lluvia"] is not None:
            ll = f"  lluvia {d['lluvia']:g}%"
        lineas.append(f"{d['emoji']} {d['dia']} {d['fecha']}: {d['desc'].lower()}, "
                      f"min {d['min']:g}° / max {d['max']:g}°{ll}")
    lineas.append("")
    lineas.append(f"Consejo: {clima['recomendacion']}")
    return "\n".join(lineas)


def _main(argv):
    args = list(argv)
    ciudad = args[1] if len(args) > 1 else ""
    clima = obtener_clima(ciudad)
    print(formatear(clima))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))