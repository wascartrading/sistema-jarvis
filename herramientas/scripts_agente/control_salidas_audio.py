import os
import subprocess
import sys

# 04/09/2026 (KIT PORTATIL): ruta derivada de este archivo (scripts_agente).
SOUNDVOLUMEVIEW = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "audio_tools", "soundvolumeview", "SoundVolumeView.exe")

def list_devices():
    try:
        result = subprocess.run(
            [SOUNDVOLUMEVIEW, "/stab"],
            capture_output=True,
            check=True
        )
        # Decodificar como UTF-16 (formato nativo de SoundVolumeView)
        text = result.stdout.decode('utf-16-le', errors='replace')
        lines = text.strip().split('\n')
        if not lines:
            return []
        
        headers = lines[0].split('\t')
        devices = []
        for line in lines[1:]:
            if not line.strip():
                continue
            parts = line.split('\t')
            row = dict(zip(headers, parts))
            
            if row.get('Type') == 'Device' and row.get('Direction') == 'Render':
                devices.append({
                    'name': row.get('Device Name', 'Unknown'),
                    'id': row.get('Command-Line Friendly ID', ''),
                    'state': row.get('Device State', ''),
                    'default': row.get('Default', '')
                })
        return devices
    except Exception as e:
        return [{'error': str(e)}]

def get_default_device():
    devices = list_devices()
    for d in devices:
        if d.get('default') == 'Render':
            return d
    return None

def set_default_device(device_name):
    try:
        subprocess.run(
            [SOUNDVOLUMEVIEW, "/SetDefault", device_name, "1"],
            capture_output=True,
            check=True
        )
        return True, f"Dispositivo cambiado a: {device_name}"
    except subprocess.CalledProcessError as e:
        return False, f"Error: {e.stderr.decode()}"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: control_salidas_audio.py list | get | set <nombre_dispositivo>")
        sys.exit(0)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "list":
        devices = list_devices()
        for d in devices:
            if 'error' in d:
                print(d['error'])
            else:
                default_mark = " [ACTUAL]" if d['default'] == 'Render' else ""
                print(f"{d['name']}{default_mark}")
    elif cmd == "get":
        dev = get_default_device()
        if dev:
            print(f"{dev['name']} | {dev['id']}")
        else:
            print("No se pudo obtener el dispositivo actual")
    elif cmd == "set":
        if len(sys.argv) < 3:
            print("Uso: control_salidas_audio.py set <nombre_dispositivo>")
            sys.exit(1)
        success, msg = set_default_device(sys.argv[2])
        print(msg)
    else:
        print("Comandos: list, get, set <nombre_dispositivo>")
