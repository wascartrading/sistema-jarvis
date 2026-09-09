# -*- coding: utf-8 -*-
"""Diagnostico rapido del sistema JARVIS (01/09/2026, sistema Telegram).
Ejecuta: python diagnostico_jarvis.py
Devuelve un informe completo para que el DOCTOR diagnostique: procesos,
puertos, estado de OmniRoute, JSON del bot y sesiones del pool.
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

# 04/09/2026 (KIT PORTATIL): ruta derivada de este archivo (manos -> kit\jarvis).
_KIT_BASE = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..'))
PROYECTOS = os.path.join(_KIT_BASE, 'jarvis')
BOT_PATRON = 'jarvis_telegram_bot'
OMNIROUTE_URL = 'http://127.0.0.1:20128/'
PUERTOS_CLAVE = [20128, 20131, 20132, 9123]
JSONS = ['historial_muse.json', 'pool_sesiones_jarvis.json', 'config_jarvis.json']


def ps_bot():
    try:
        r = subprocess.run(['powershell', '-NoProfile', '-Command',
            'Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match '
            '"%s" } | ForEach-Object { $p = Get-Process -Id $_.ProcessId '
            '-ErrorAction SilentlyContinue; Write-Output ("PID {0} [{1}] '
            'desde {2}" -f $_.ProcessId, $_.Name, $p.StartTime) }' % BOT_PATRON],
            capture_output=True, encoding='utf-8', errors='replace', timeout=15)
        return (r.stdout or '').strip()
    except Exception as e:
        return 'ERROR: %s' % e


def puertos():
    try:
        r = subprocess.run(['powershell', '-NoProfile', '-Command',
            '$p = Get-NetTCPConnection -State Listen -ErrorAction '
            'SilentlyContinue | Where-Object { $_.LocalPort -in '
            '20128,20131,20132,9123 } | Sort-Object LocalPort; '
            'if ($p) { $p | ForEach-Object { "{0}:{1} LISTENING (PID {2})" -f '
            '$_.LocalAddress, $_.LocalPort, $_.OwningProcess } } else { '
            '"ninguno de los clave escuchando" }'],
            capture_output=True, encoding='utf-8', errors='replace', timeout=15)
        return (r.stdout or '').strip()
    except Exception as e:
        return 'ERROR: %s' % e


def omniroute_http():
    try:
        t0 = time.time()
        r = urllib.request.urlopen(OMNIROUTE_URL, timeout=6)
        lat = (time.time() - t0) * 1000
        cuerpo = r.read().decode('utf-8', errors='replace')
        return 'HTTP %d en %.0f ms | %s' % (r.status, lat, cuerpo[:200].replace('\n', ' '))
    except Exception as e:
        return 'ERROR: %s' % e


def json_bot():
    out = []
    for f in JSONS:
        p = os.path.join(PROYECTOS, f)
        try:
            if not os.path.isfile(p):
                out.append('%s: NO EXISTE' % f)
                continue
            with open(p, encoding='utf-8') as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                extra = ', %d claves' % len(data)
            elif isinstance(data, list):
                extra = ', %d elementos' % len(data)
            else:
                extra = ''
            out.append('%s: VALIDO (%d bytes%s)' % (f, os.path.getsize(p), extra))
        except Exception as e:
            out.append('%s: CORRUPTO (%s)' % (f, e))
    return '\n'.join(out)


def sesiones_pool():
    try:
        with open(os.path.join(PROYECTOS, 'pool_sesiones_jarvis.json'), encoding='utf-8') as fh:
            data = json.load(fh)
        sesiones = data if isinstance(data, list) else data.get('sesiones', [])
        vivas = 0
        for s in sesiones:
            pid = s.get('pid') if isinstance(s, dict) else None
            if pid:
                vivas += 1
        return '%d sesiones en pool (con pid: %d)' % (len(sesiones), vivas)
    except Exception as e:
        return 'ERROR: %s' % e


print('=' * 60)
print('INFORME DE DIAGNOSTICO JARVIS - %s' % time.strftime('%d/%m/%Y %H:%M:%S'))
print('=' * 60)
print('\n[1] PROCESO DEL BOT (jarvis_telegram_bot.py):')
print(ps_bot() or '  ninguno encontrado')
print('\n[2] PUERTOS CLAVE (OmniRoute 20128/20131/20132, lock 9123):')
print(puertos() or '  ninguno escuchando')
print('\n[3] OMNIROUTE HTTP (127.0.0.1:20128):')
print(' ', omniroute_http())
print('\n[4] JSON DEL BOT:')
print(json_bot())
print('\n[5] SESIONES DEL POOL:')
print(' ', sesiones_pool())
print('\n' + '=' * 60)
print('FIN DEL INFORME')
