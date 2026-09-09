# reproducir_musica.py - reproduce la MUSICA FAVORITA de JARVIS (Wáscar).
# Creado 22/08/2026 (manos de JARVIS).
#
# MUSICA FAVORITA detectada al ver la pantalla del jefe: CITIZEN - OVER IT
# (Official Music Video) en YouTube. Se abre en el navegador por defecto
# (Brave) con la URL del video (y la lista/radio activa), en silencio.
#
# Uso:  python reproducir_musica.py
import webbrowser

# CITIZEN - OVER IT (Official Music Video), con la lista/radio de YouTube.
# El jefe la tenia sonando con list=RD... (modo radio automatico).
URL = 'https://www.youtube.com/watch?v=6mAkNvfz114'
# Mejor reproducir en una pestaña nueva del navegador por defecto.

def main():
    webbrowser.open(URL, new=2)
    print('Reproduciendo musica favorita: CITIZEN - Over It (YouTube)')

if __name__ == '__main__':
    main()
