# reproducir_youtube.py - busca en YouTube y abre el PRIMER video del resultado.
import re
import sys
import urllib.parse
import urllib.request
import webbrowser


def main():
    query = ' '.join(sys.argv[1:]) or 'musica'
    url = 'https://www.youtube.com/results?search_query=' + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    html = urllib.request.urlopen(req, timeout=20).read().decode('utf-8', 'ignore')
    ids = re.findall(r'"videoId":"([A-Za-z0-9_-]{11})"', html)
    if ids:
        video = 'https://www.youtube.com/watch?v=' + ids[0]
        print('Reproduciendo: ' + video)
        webbrowser.open(video)
    else:
        print('No encontre videos, abriendo busqueda')
        webbrowser.open(url)


if __name__ == '__main__':
    main()