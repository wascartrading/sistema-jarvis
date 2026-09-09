"""reproducir_el_mentalista.py - Reproduce "El Mentalista" en YouTube a pantalla completa.
manos de JARVIS (creado 22/08/2026, peticion del jefe).

Flujo:
  1) Cierra las pestanas de YouTube viejas que esten abiertas en Brave.
  2) Busca "El Mentalista" en YouTube y reproduce el primer resultado.
  3) Pone la ventana de Brave a pantalla completa (F11).

Uso:  python reproducir_el_mentalista.py
"""
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import webbrowser

DIR = os.path.dirname(os.path.abspath(__file__))
CONSULTA = "El Mentalista temporada 1 episodio 15 completo"


def _cerrar_pestanas():
    """Ejecuta cerrar_pestanas_youtube.ps1 para limpiar pestanas de YouTube."""
    ps1 = os.path.join(DIR, "cerrar_pestanas_youtube.ps1")
    try:
        cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", ps1]
        r = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='replace', timeout=60)
        print("Pestanas: " + (r.stdout.strip() or r.stderr.strip() or "OK"))
        return True
    except Exception as e:
        print("No se pudieron cerrar pestanas: %s" % e)
        return False


def _abrir_youtube():
    """Busca la serie en YouTube y abre el primer video encontrado."""
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(CONSULTA)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
        ids = re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', html)
        if ids:
            video = "https://www.youtube.com/watch?v=" + ids[0]
            print("Reproduciendo: " + video)
            webbrowser.open(video)
            return True
    except Exception as e:
        print("Busqueda directa fallo (%s), abriendo busqueda" % e)
    webbrowser.open(url)
    return True


def _pantalla_completa():
    """Activa Brave y pulsa F11 para a pantalla completa."""
    ps1 = os.path.join(DIR, "pantalla_grande.ps1")
    try:
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass",
                        "-File", ps1, "Brave"], timeout=40)
    except Exception as e:
        print("Pantalla completa: %s" % e)


if __name__ == "__main__":
    _cerrar_pestanas()
    time.sleep(1)
    _abrir_youtube()
    time.sleep(4)
    _pantalla_completa()
    print("OK listo")
