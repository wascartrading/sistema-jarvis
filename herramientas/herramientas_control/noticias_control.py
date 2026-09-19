# -*- coding: utf-8 -*-
"""
noticias_control.py — Noticias para JARVIS (Telegram).
Usa Google News RSS (gratis, SIN API key). Portado del desmenuzado
JARVIS-HRZ (actions/noticias) con codigo limpio.

Uso:
  python cli.py noticias [categoria] [pais]
  categoria: general | deportes | finanzas | tecnologia   (default: general)
  pais: codigo ISO 2 letras, ej. PE, CO, MX, AR, ES       (default: PE)
"""
import base64
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"}
_BASE = "https://news.google.com/rss/headlines/section/topic/{TOPIC}"
_BASE_GENERAL = "https://news.google.com/rss"

_TOPICS = {
    "deportes": "SPORTS", "deporte": "SPORTS", "sports": "SPORTS",
    "finanzas": "BUSINESS", "finanza": "BUSINESS", "business": "BUSINESS",
    "economia": "BUSINESS", "negocios": "BUSINESS",
    "tecnologia": "TECHNOLOGY", "tecnología": "TECHNOLOGY",
    "tech": "TECHNOLOGY", "technology": "TECHNOLOGY",
    "general": "GENERAL",
}
# locales por pais (tomados del desmenuzado)
_NOMBRES = {"GENERAL": "General", "SPORTS": "Deportes", "BUSINESS": "Finanzas",
            "TECHNOLOGY": "Tecnologia"}
_PAISES = {
    "PE": ("es-419", "es-419"), "CO": ("es-419", "es-419"),
    "MX": ("es-419", "es-419"), "AR": ("es-419", "es-419"),
    "CL": ("es-419", "es-419"), "VE": ("es-419", "es-419"),
    "EC": ("es-419", "es-419"), "BO": ("es-419", "es-419"),
    "PY": ("es-419", "es-419"), "UY": ("es-419", "es-419"),
    "CR": ("es-419", "es-419"), "PA": ("es-419", "es-419"),
    "GT": ("es-419", "es-419"), "HN": ("es-419", "es-419"),
    "NI": ("es-419", "es-419"), "SV": ("es-419", "es-419"),
    "DO": ("es-419", "es-419"), "PR": ("es-419", "es-419"),
    "CU": ("es-419", "es-419"), "ES": ("es-ES", "es-ES"),
    "US": ("en-US", "en-US"), "GB": ("en-GB", "en-GB"),
    "BR": ("pt-BR", "pt-BR"), "FR": ("fr-FR", "fr-FR"),
}


def _fetch(url, timeout=15):
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _decode_google_news_url(url):
    """Convierte el enlace de redireccion del RSS en la URL real."""
    try:
        m = re.search(r"/articles/([^?]+)", url)
        if not m:
            return url
        payload = m.group(1)
        # formato nuevo: CBM... = base64 de JSON con 'url'
        try:
            raw = base64.urlsafe_b64decode(payload + "===")
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("url"):
                return data["url"]
        except Exception:
            pass
        # formato antiguo: AU_yq... base64url -> bytes -> find http
        try:
            raw = base64.urlsafe_b64decode(payload + "===")
            s = raw.decode("utf-8", "replace")
            m2 = re.search(r"https?://[^\x00-\x1f\"'<>\\^`{|}]+", s)
            if m2:
                return m2.group(0)
        except Exception:
            pass
    except Exception:
        pass
    return url


def _hace(t):
    """Tiempo relativo en espanol: 'hace 2 h'."""
    try:
        dt = parsedate_to_datetime(t)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        ahora = datetime.now(timezone.utc)
        seg = max(0, int((ahora - dt).total_seconds()))
        if seg < 60:
            return "hace 1 min"
        if seg < 3600:
            return f"hace {seg // 60} min"
        if seg < 86400:
            return f"hace {seg // 3600} h"
        return f"hace {seg // 86400} d"
    except Exception:
        return ""


def obtener_noticias(categoria="general", pais="PE", maximo=8):
    cat = _TOPICS.get((categoria or "general").strip().lower(), "GENERAL")
    pais = (pais or "PE").strip().upper()
    hl, ceid = _PAISES.get(pais, ("es-419", "es-419"))
    qs = urllib.parse.urlencode({"hl": hl, "gl": pais, "ceid": f"{pais}:{ceid}"})
    if cat == "GENERAL":
        url = f"{_BASE_GENERAL}?{qs}"
    else:
        url = f"{_BASE.format(TOPIC=cat)}?{qs}"
    try:
        xml = _fetch(url)
    except Exception as e:
        return {"error": f"No pude obtener las noticias ({type(e).__name__})."}
    raiz = ET.fromstring(xml)
    salida = []
    for item in raiz.iter("item"):
        titulo = (item.findtext("title") or "").strip()
        fuente_el = item.find("source")
        fuente = (fuente_el.text or "").strip() if fuente_el is not None else ""
        # limpiar titulo si viene "Titulo - Fuente"
        limpio = re.sub(r"\s+-\s*$", "", titulo)
        if not limpio:
            continue
        link = _decode_google_news_url(item.findtext("link") or "")
        pub = item.findtext("pubDate") or ""
        salida.append({
            "titulo": limpio, "fuente": fuente,
            "hace": _hace(pub), "link": link,
        })
        if len(salida) >= maximo:
            break
    if not salida:
        return {"error": "No encontre noticias para esa categoria/pais."}
    return {"categoria": _NOMBRES.get(cat, cat.lower()), "pais": pais, "noticias": salida}


def formatear(datos):
    if "error" in datos:
        return datos["error"]
    n = datos["noticias"]
    lineas = [f"Noticias · {datos['categoria'].capitalize()} · {datos['pais']}", ""]
    for i, x in enumerate(n, 1):
        t = x["titulo"] if len(x["titulo"]) <= 160 else x["titulo"][:157] + "..."
        fu = f" — {x['fuente']}" if x["fuente"] else ""
        h = f" · {x['hace']}" if x["hace"] else ""
        lineas.append(f"{i}) {t}{fu}{h}")
    return "\n".join(lineas)


def _main(argv):
    args = list(argv)
    categoria = args[1] if len(args) > 1 else "general"
    pais = args[2] if len(args) > 2 else "PE"
    datos = obtener_noticias(categoria, pais)
    print(formatear(datos))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv))