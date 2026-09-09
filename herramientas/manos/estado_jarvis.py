# -*- coding: utf-8 -*-
"""estado_jarvis.py — Informe de estado completo de JARVIS (01/09/2026, Telegram).

Creado a petición del jefe: cuando pregunte "cómo estás", JARVIS debe dar el
estado de TODO: memoria, código, modelo/proveedor, puertos y sistema.

Ejecuta con el PYTHON OBLIGATORIO del proyecto:
  C:\\Users\\wasc4\\AppData\\Local\\Programs\\Python\\Python312\\python.exe estado_jarvis.py

Arquitectura actual (01/09/2026): sistema Telegram (jarvis_telegram_bot.py) con
opencode run directo, gateway OmniRoute en 127.0.0.1:20128 sirviendo el combo
COMBO JARVIS. No existe sistema de voz.
"""
import json
import os
import subprocess
import sys
import time

# 04/09/2026 (KIT PORTATIL): rutas derivadas de este archivo (manos -> kit).
_KIT_BASE = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..'))
PROYECTOS = os.path.join(_KIT_BASE, 'jarvis')
ASISTENTE = os.path.join(_KIT_BASE, 'herramientas')
PYTHON = r'C:\Users\wasc4\AppData\Local\Programs\Python\Python312\python.exe'
MEMORIA = os.path.join(ASISTENTE, 'memoria_jarvis.md')
BOT = os.path.join(PROYECTOS, 'jarvis_telegram_bot.py')
JSONS = ['historial_muse.json', 'pool_sesiones_jarvis.json', 'config_jarvis.json']
PUERTOS_CLAVE = [20128, 20131, 20132, 9123]


def correr(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, capture_output=True, encoding='utf-8', errors='replace', timeout=timeout)
        return (r.stdout or '').strip()
    except Exception as e:
        return 'ERROR: %s' % e


def seccion(titulo):
    print('\n== %s ==' % titulo)


def estado_memoria():
    if not os.path.exists(MEMORIA):
        return 'NO EXISTE memoria_jarvis.md'
    lineas = sum(1 for _ in open(MEMORIA, encoding='utf-8'))
    bytes_ = os.path.getsize(MEMORIA)
    estim = bytes_ // 4
    if bytes_ < 200000:
        cargo = 'LIGERA, sin sobrecarga'
    elif bytes_ < 500000:
        cargo = 'MODERADA'
    else:
        cargo = 'PESADA, convendría compactar'
    return '%d lineas, %.1f KB (~%d tokens), carga: %s' % (
        lineas, bytes_ / 1024.0, estim, cargo)


def estado_codigo():
    if not os.path.exists(PYTHON):
        return 'PYTHON 3.12 no encontrado en la ruta esperada'
    codigo = ('import os\n'
              'base=r"__BASE__"\n'
              'ok=0; fail=[]; total=0\n'
              'for root,_,fs in os.walk(base):\n'
              '    if "__pycache__" in root or "respaldo" in root \\\n'
              '            or "backup" in root:\n'
              '        continue\n'
              '    for f in fs:\n'
              '        if not f.endswith(".py"):\n'
              '            continue\n'
              '        total += 1\n'
              '        p = os.path.join(root, f)\n'
              '        try:\n'
              '            with open(p, encoding="utf-8", errors="replace") as fh:\n'
              '                compile(fh.read(), p, "exec")\n'
              '            ok += 1\n'
              '        except Exception:\n'
              '            fail.append(p)\n'
              'print("TOTAL %d OK %d FALLOS %d" % (total, ok, len(fail)))\n'
              'print("\\n".join(fail[:10]))\n'
              ).replace('__BASE__', ASISTENTE)
    return (correr([PYTHON, '-c', codigo], timeout=120) or 'sin datos').strip()


def estado_proveedor():
    try:
        with open(os.path.join(PROYECTOS, 'config_jarvis.json'), encoding='utf-8') as f:
            cfg = json.load(f)
        return 'config_jarvis.json leido (%d claves)' % len(cfg)
    except Exception as e:
        return 'config_jarvis.json ilegible (%s)' % e


def estado_procesos():
    out = correr(['powershell', '-NoProfile', '-Command',
                  'Get-CimInstance Win32_Process | Where-Object { $_.CommandLine '
                  '-match "jarvis_telegram_bot|omniroute" } | '
                  'ForEach-Object { $p = Get-Process -Id $_.ProcessId '
                  '-ErrorAction SilentlyContinue; $mem = [math]::Round('
                  '$p.WorkingSet64/1MB); "{0} | {1} | {2} MB" -f $_.ProcessId, '
                  '$_.Name, $mem }'])
    return out or 'ninguno relevante encontrado'


def estado_puertos():
    out = correr(['powershell', '-NoProfile', '-Command',
                  '$p = Get-NetTCPConnection -State Listen -ErrorAction '
                  'SilentlyContinue | Where-Object { $_.LocalPort -in '
                  '20128,20131,20132,9123 } | '
                  'Sort-Object LocalPort; if ($p) { $p | ForEach-Object { '
                  '"{0}:{1} LISTENING (PID {2})" -f $_.LocalAddress, '
                  '$_.LocalPort, $_.OwningProcess } } else { '
                  '"ninguno de los clave escuchando" }'], timeout=30)
    lineas = [l for l in out.splitlines() if l.strip()]
    if not lineas:
        return 'ninguno de los clave escuchando'
    expuestos = [l for l in lineas if l.startswith('0.0.0.0:')]
    res = ' | '.join(lineas)
    if expuestos:
        res += ' | ATENCION: %d abierto a TODA la red (%s)' % (
            len(expuestos), ', '.join(x.split(' ')[0] for x in expuestos))
    return res


def estado_json():
    out = []
    for f in JSONS:
        p = os.path.join(PROYECTOS, f)
        try:
            if not os.path.isfile(p):
                out.append('%s: NO EXISTE' % f)
                continue
            with open(p, encoding='utf-8') as fh:
                data = json.load(fh)
            out.append('%s: OK (%d bytes)' % (f, os.path.getsize(p)))
        except Exception as e:
            out.append('%s: CORRUPTO (%s)' % (f, e))
    return '\n'.join(out) or 'sin JSON'


def estado_sistema():
    out = correr(['powershell', '-NoProfile', '-Command',
                  '$os = Get-CimInstance Win32_OperatingSystem; '
                  '"RAM libre: {0:F1} GB de {1:F1} GB" -f '
                  '($os.FreePhysicalMemory/1MB), ($os.TotalVisibleMemorySize/1MB); '
                  '$d = Get-PSDrive C; '
                  '"Disco C libre: {0:F0} GB" -f ($d.Free/1GB)'])
    return out or 'sin datos'


def main():
    print('INFORME DE ESTADO JARVIS - %s' % time.strftime('%d/%m/%Y %H:%M:%S'))
    seccion('MEMORIA (memoria_jarvis.md)')
    print(' ', estado_memoria())
    seccion('CODIGO (todos los .py del proyecto)')
    print(' ', estado_codigo())
    seccion('MODELO / PROVEEDOR')
    print(' ', estado_proveedor())
    seccion('PROCESOS (bot, gateway)')
    print(estado_procesos())
    seccion('PUERTOS CLAVE')
    print(' ', estado_puertos())
    seccion('JSON DEL BOT')
    print(estado_json())
    seccion('SISTEMA')
    print(' ', estado_sistema())
    print('\nFIN')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('FALLO GLOBAL: %s' % e)
        sys.exit(1)
