"""
git_control.py — Wrapper de Git/GitHub (status, add, commit, push, clone,
log, branch...). Portado del desmenuzado sin tocar config del usuario.

Uso CLI:
  python cli.py git status [dir]
  python cli.py git commit "mensaje" [dir]
  python cli.py git push [dir]
  python cli.py git log [n] [dir]
  python cli.py git clone "url" "destino"
"""
import subprocess


def _run(comando, cwd=None, timeout=90):
    try:
        r = subprocess.run(comando, shell=True, capture_output=True, text=True,
                           timeout=timeout, cwd=cwd, errors="replace")
        salida = (r.stdout or "") + (r.stderr or "")
        return r.returncode, salida.strip()
    except Exception as e:
        return -1, f"Error: {e!r}"


def git(accion, args, cwd=None):
    if accion == "status":
        return _run("git status", cwd)
    if accion == "add":
        return _run("git add -A", cwd)
    if accion == "commit":
        msg = " ".join(args)
        if not msg:
            return -1, "Falta el mensaje del commit"
        return _run(f'git commit -m "{msg}"', cwd)
    if accion == "push":
        return _run("git push", cwd)
    if accion == "pull":
        return _run("git pull", cwd)
    if accion == "log":
        n = args[0] if args and args[0].isdigit() else 10
        return _run(f"git log --oneline -{n}", cwd)
    if accion == "branch":
        return _run("git branch -a", cwd)
    if accion == "clone":
        if len(args) < 1:
            return -1, "Falta la URL"
        url = args[0]
        destino = args[1] if len(args) > 1 else None
        return _run(f'git clone "{url}" {destino or ""}'.strip(), cwd, timeout=300)
    if accion == "diff":
        return _run("git diff --stat", cwd)
    if accion == "remote":
        return _run("git remote -v", cwd)
    return -1, f"Accion git desconocida: {accion}"


def _main(argv):
    import sys
    if len(argv) < 2:
        print("Acciones: status|add|commit|push|pull|log|branch|clone|diff|remote")
        return 2
    accion = argv[1].lower()
    resto = argv[2:]
    # deteccion de directorio (flag --dir=)
    cwd = None
    args = []
    for a in resto:
        if a.startswith("--dir="):
            cwd = a.split("=", 1)[1]
        else:
            args.append(a)
    code, salida = git(accion, args, cwd)
    print(salida[:4000] if salida else "(sin salida)")
    return 0 if code == 0 else 1


if __name__ == "__main__":
    _main(sys.argv)