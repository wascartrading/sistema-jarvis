"""
web_search.py — Busqueda web rapida (DuckDuckGo) con resumen de primeros
resultados. Portado del desmenuzado (sin API key).

Uso CLI:
  python cli.py web_search "consulta" [n=5]
"""
import re
import urllib.parse
import urllib.request
from html import unescape

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")


def _texto_limpio(t):
    return unescape(re.sub(r"<[^>]+>", "", t or "")).strip()


def buscar(query, n=5):
    """Devuelve lista de (titulo, url, snippet) desde DuckDuckGo HTML."""
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return [], f"Error buscando: {e!r}"
    resultados = []
    bloques = re.findall(
        r'<div class="result[^"]*">(.*?)</div>\s*</div>', html, re.S)
    if not bloques:
        bloques = re.findall(r'<div class="result[^"]*">(.*?)</div>', html, re.S)
    for bloque in bloques[:n]:
        m_titulo = re.search(r'<a[^>]*class="result__a"[^>]*>(.*?)</a>', bloque, re.S)
        m_url = re.search(r'href="([^"]+)"', bloque, re.S)
        m_snip = re.search(r'class="result__snippet"[^>]*>(.*?)</a>', bloque, re.S)
        if not m_titulo:
            continue
        titulo = _texto_limpio(m_titulo.group(1))
        url_r = unescape(m_url.group(1)) if m_url else ""
        if url_r.startswith("//"):
            url_r = "https:" + url_r
        snippet = _texto_limpio(m_snip.group(1)) if m_snip else ""
        resultados.append((titulo, url_r, snippet))
    if not resultados:
        # fallback: extraer enlaces directos
        for m in re.finditer(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
            titulo = _texto_limpio(m.group(2))
            url_r = unescape(m.group(1))
            if url_r.startswith("//"):
                url_r = "https:" + url_r
            resultados.append((titulo, url_r, ""))
    return resultados, None


def resumir(query, n=5):
    """Texto plano listo para mostrar en Telegram."""
    resultados, err = buscar(query, n)
    if err:
        return err
    if not resultados:
        return f"Sin resultados para: {query}"
    lineas = [f"Resultados de: {query}", ""]
    for i, (titulo, url, snip) in enumerate(resultados[:n], 1):
        lineas.append(f"{i}. {titulo}")
        if snip:
            lineas.append(f"   {snip[:160]}")
        lineas.append(f"   {url}")
    return "\n".join(lineas)


def _main(argv):
    import sys
    if len(argv) < 2:
        print("Uso: web_search.py <consulta> [n]")
        return 2
    q = " ".join(argv[1:-1]) if len(argv) > 2 and argv[-1].isdigit() else " ".join(argv[1:])
    n = int(argv[-1]) if argv[-1].isdigit() else 5
    print(resumir(q, n))
    return 0


if __name__ == "__main__":
    _main(sys.argv)