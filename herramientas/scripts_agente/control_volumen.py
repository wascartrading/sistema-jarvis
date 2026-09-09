from pycaw.pycaw import AudioUtilities
import sys

def get_volume():
    dev = AudioUtilities.GetSpeakers()
    vol = dev.EndpointVolume
    level = vol.GetMasterVolumeLevelScalar()
    mute = vol.GetMute()
    return level, mute

def set_volume(level):
    dev = AudioUtilities.GetSpeakers()
    vol = dev.EndpointVolume
    vol.SetMasterVolumeLevelScalar(level, None)
    print(f"Volumen establecido al {int(level*100)}%")

def toggle_mute():
    dev = AudioUtilities.GetSpeakers()
    vol = dev.EndpointVolume
    mute = vol.GetMute()
    vol.SetMute(not mute, None)
    state = "activado" if not mute else "desactivado"
    print(f"Silencio {state}")

def change_volume(delta):
    dev = AudioUtilities.GetSpeakers()
    vol = dev.EndpointVolume
    level = vol.GetMasterVolumeLevelScalar()
    new_level = max(0.0, min(1.0, level + delta))
    vol.SetMasterVolumeLevelScalar(new_level, None)
    print(f"Volumen: {int(level*100)}% -> {int(new_level*100)}%")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        level, mute = get_volume()
        print(f"Volumen actual: {int(level*100)}% | Silencio: {'Si' if mute else 'No'}")
        sys.exit(0)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "get":
        level, mute = get_volume()
        print(f"{int(level*100)}|{int(mute)}")
    elif cmd == "set":
        if len(sys.argv) < 3:
            print("Uso: control_volumen.py set <0-100>")
            sys.exit(1)
        set_volume(int(sys.argv[2]) / 100.0)
    elif cmd == "mute":
        toggle_mute()
    elif cmd == "up":
        change_volume(0.05)
    elif cmd == "down":
        change_volume(-0.05)
    else:
        print("Comandos: get, set <0-100>, mute, up, down")
