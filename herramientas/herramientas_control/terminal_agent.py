"""
terminal_agent.py — Ejecutar comandos en consola (headless o ventana aparte).
Portado del desmenuzado (version simple con subprocess).

Uso CLI:
  python cli.py terminal ejecutar "dir" [timeout=30] [consola=1]
"""
import subprocess
import time


def ejecutar(comando, timeout=60, consola=False, cwd=None):
    """Ejecuta un comando y devuelve (codigo, salida). consola=True abre ventana
    (y la trae AL FRENTE, orden del jefe 16/09/2026)."""
    if consola:
        try:
            p = subprocess.Popen(
                ["cmd", "/k", comando], shell=False,
                creationflags=subprocess.CREATE_NEW_CONSOLE)
            # Toda ventana que abro queda AL FRENTE (orden del jefe 16/09/2026):
            # se busca la consola por el PID del proceso y se enfoca verificando.
            al_frente = False
            try:
                from . import app_control as ac
                limite, hwnd = time.time() + 5.0, None
                while time.time() < limite and not hwnd:
                    hwnd = ac._hwnd_de_pid(p.pid)
                    if not hwnd:
                        time.sleep(0.2)
                if hwnd:
                    al_frente = ac.traer_al_frente(hwnd=hwnd, espera=2.0)[0]
                else:
                    al_frente = ac.traer_al_frente("cmd.exe", espera=1.5)[0]
            except Exception:
                al_frente = False
            return 0, ("Consola abierta ejecutando el comando"
                       + (" | al frente" if al_frente else ""))
        except Exception as e:
            return -1, f"Error: {e!r}"
    try:
        r = subprocess.run(
            comando, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=cwd, errors="replace")
        salida = (r.stdout or "") + (r.stderr or "")
        return r.returncode, salida.strip()
    except subprocess.TimeoutExpired:
        return -1, f"Timeout tras {timeout}s"
    except Exception as e:
        return -1, f"Error: {e!r}"


def _main(argv):
    import sys
    if len(argv) < 3:
        print("Uso: terminal_agent.py ejecutar <comando> [timeout] [consola=1]")
        return 2
    accion = argv[1].lower()
    if accion != "ejecutar":
        print(f"Accion desconocida: {accion}")
        return 2
    comando = argv[2]
    timeout = 60
    consola = False
    for arg in argv[3:]:
        if arg.isdigit():
            timeout = int(arg)
        elif arg.startswith("timeout="):
            timeout = int(arg.split("=", 1)[1])
        elif arg == "consola=1":
            consola = True
    code, salida = ejecutar(comando, timeout=timeout, consola=consola)
    print(salida[:4000] if salida else "(sin salida)")
    return code if 0 <= code <= 255 else 1


if __name__ == "__main__":
    _main(sys.argv)