# ejecutar_admin.py - Ejecuta un comando como ADMINISTRADOR via la tarea
# programada JARVIS_ELEVADO (privilegios maximos, sin ventanas de UAC).
#
# Uso (desde JARVIS):
#   python ejecutar_admin.py "comando"
# Devuelve por stdout la salida del comando (con EXIT=... al inicio).
#
# Como funciona:
#   1. Escribe el comando en jarvis_admin_in.txt (temp).
#   2. Lanza la tarea JARVIS_ELEVADO (schtasks /run).
#   3. Espera a que aparezca jarvis_admin_out.txt (polling).
#   4. Lee y devuelve la salida.
#
# REGLA DEL USUARIO (16/08/2026): usar SOLO para acciones que requieran
# administrador o que puedan afectar la PC. Para acciones simples o que no
# afectan el sistema, ejecutar directamente sin elevar. Si la accion es
# peligrosa (borrar, instalar, tocar servicios, etc.), preguntar antes.
import os
import subprocess
import sys
import tempfile
import time

TEMP = os.path.join(tempfile.gettempdir(), 'opencode')
IN = os.path.join(TEMP, 'jarvis_admin_in.txt')
OUT = os.path.join(TEMP, 'jarvis_admin_out.txt')


def ejecutar_admin(comando, timeout=60):
    """Ejecuta 'comando' como administrador y devuelve su salida."""
    os.makedirs(TEMP, exist_ok=True)
    with open(IN, 'w', encoding='utf-8') as f:
        f.write(comando)
    if os.path.exists(OUT):
        os.remove(OUT)
    subprocess.run(['schtasks', '/run', '/tn', 'JARVIS_ELEVADO'],
                   capture_output=True, timeout=15)
    fin = time.time() + timeout
    while time.time() < fin:
        if os.path.exists(OUT):
            with open(OUT, 'r', encoding='utf-8-sig') as f:
                return f.read()
        time.sleep(0.5)
    return 'ERROR=Timeout esperando la salida del comando administrador'


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Uso: python ejecutar_admin.py "comando"')
        sys.exit(1)
    print(ejecutar_admin(sys.argv[1]))
