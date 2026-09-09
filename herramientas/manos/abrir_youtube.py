"""abrir_youtube.py - abre YouTube con una busqueda (manos de JARVIS).
Uso: python abrir_youtube.py "texto a buscar"
Abre la URL de resultados de YouTube en el navegador por defecto."""
import sys
import urllib.parse
import webbrowser


def main():
    query = ' '.join(sys.argv[1:]) or 'musica'
    url = 'https://www.youtube.com/results?search_query=' + urllib.parse.quote(query)
    print('Abriendo YouTube: ' + url)
    webbrowser.open(url)


if __name__ == '__main__':
    main()
