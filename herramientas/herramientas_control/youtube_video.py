"""
youtube_video.py — Obtiene el primer video de una busqueda de YouTube y abre.
Portado del desmenuzado (_get_first_video_id). Sin API key: parsea el HTML
de resultados de YouTube.

Uso CLI:
  python cli.py youtube_video "nombre cancion"
"""
import re
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")


def _get_first_video_id(query, intentos=2):
    """Devuelve el videoId del primer resultado de YouTube o None."""
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(query)
    for _ in range(intentos):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=12) as r:
                html = r.read().decode("utf-8", errors="ignore")
            m = re.search(r'"videoId":"([A-Za-z0-9_-]{11})"', html)
            if m:
                return m.group(1)
        except Exception:
            time.sleep(1)
    return None


def obtener_video_url(query):
    """URL directa del video encontrado (o None)."""
    video_id = _get_first_video_id(query)
    if not video_id:
        return None
    return f"https://www.youtube.com/watch?v={video_id}"


def _main(argv):
    import sys
    import time
    if len(argv) < 2:
        print("Uso: youtube_video.py <busqueda>")
        return 2
    q = " ".join(argv[1:])
    vid = _get_first_video_id(q)
    if vid:
        print(f"videoId={vid}")
        print(f"url=https://www.youtube.com/watch?v={vid}")
        return 0
    print("No se encontro el video")
    return 2


if __name__ == "__main__":
    _main(sys.argv)