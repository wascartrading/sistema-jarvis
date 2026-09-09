# abrir_hbo_max.py - reanuda la serie vista en HBO Max (El Mentalista) y la
# deja en PANTALLA COMPLETA (F11). Creado 17/08/2026 (manos de JARVIS).
#
# ACTUALIZADO 22/08/2026 (jefe): el jefe va por el CAPITULO 13, no el 10.
# METODO DE PANTALLA COMPLETA CORREGIDO: F11 UNA SOLA VEZ tras activar
# Brave (antes se pulsaba dos veces y se cancelaban entre si).
#
# Uso:  python abrir_hbo_max.py
# Abre en el navegador por defecto (Brave) el ultimo video visto en
# play.hbomax.com, espera a que cargue y pulsa F11 UNA vez para pantalla
# completa.
import subprocess
import time
import webbrowser

# Episodio en curso del jefe: CAPITULO 15 de El Mentalista ("Scarlett Fever").
# URL del ultimo video visto (del historial de Brave).
URL = ('https://play.hbomax.com/video/watch/'
       '94ccaf5c-0be6-4d5d-906a-1a476ac96f51')
NAVEGADOR = 'Brave'


def _f11(titulo=NAVEGADOR):
    """F11 sobre la ventana del navegador (UNA sola vez) => pantalla completa."""
    try:
        ps = ("$wshell = New-Object -ComObject wscript.shell; "
              "Start-Sleep -Milliseconds 800; "
              "$ok = $wshell.AppActivate('%s'); "
              "Start-Sleep -Milliseconds 400; "
              "$wshell.SendKeys('{F11}')" % titulo)
        subprocess.run(['powershell', '-NoProfile', '-Command', ps],
                       capture_output=True, timeout=25)
        return True
    except Exception:
        return False


def main():
    print('Abriendo HBO Max (El Mentalista, capitulo 13) y pantalla completa...')
    webbrowser.open(URL, new=2)
    time.sleep(8)          # dejamos cargar la pagina / el reproductor
    _f11()
    print('Listo: serie abierta y en pantalla completa (F11 una vez).')


if __name__ == '__main__':
    main()