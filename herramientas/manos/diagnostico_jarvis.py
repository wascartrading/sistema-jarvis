# -*- coding: utf-8 -*-
"""Diagnostico del sistema JARVIS — version 15/09/2026 (arquitectura REAL).

La version anterior (01/09/2026) buscaba solo el bot de Telegram y el pool
viejo: no conocia la APP MOVIL, ni el puente de la nube, ni OmniRoute como
pieza aparte, y llegaba a dar un PID falso. Esta version mira el sistema que
el jefe usa de verdad y, sobre todo, DETECTA CUELGUES de `opencode run`
(la averia del 15/09/2026: proceso vivo pero con 0% de CPU y una herramienta
hija trabada -> el turno nunca cierra y la app se queda muda).

Ejecutar:  python diagnostico_jarvis.py
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

PERFIL_WEB = os.path.join(os.environ.get("TEMP", r"C:\Windows\Temp"),
                          "jarvis_web_perfil")
MARCAS_CALIENTE = os.path.join(PERFIL_WEB, "jarvis_caliente.ok")

PROYECTOS = r'C:\Users\wasc4\Documents\Sistema Jarvis\proyectos'
MOVIL = os.path.join(PROYECTOS, 'jarvis_movil')
PUENTE = os.path.join(PROYECTOS, 'jarvis_puente')

OMNIROUTE_URL = 'http://127.0.0.1:20128/'
PUERTOS_CLAVE = (20128, 20131, 20132, 8090, 8443, 9123)

JSONS = [
    ('app movil', os.path.join(MOVIL, 'movil_pool.json')),
    ('app movil', os.path.join(MOVIL, 'movil_historial.json')),
    ('puente', os.path.join(PUENTE, 'puente_pool.json')),
    ('puente', os.path.join(PUENTE, 'puente_historial.json')),
    ('telegram', os.path.join(PROYECTOS, 'pool_sesiones_jarvis.json')),
    ('telegram', os.path.join(PROYECTOS, 'config_jarvis.json')),
    ('telegram', os.path.join(PROYECTOS, 'historial_muse.json')),
]

PS = ['powershell', '-NoProfile', '-NonInteractive', '-Command']


def ps(script, timeout=25):
    try:
        r = subprocess.run(PS + [script], capture_output=True,
                           encoding='utf-8', errors='replace', timeout=timeout)
        return (r.stdout or '').strip()
    except Exception as e:
        return 'ERROR: %r' % (e,)


def procesos():
    """Instantanea de procesos con linea de comandos + CPU."""
    script = (
        "$o=@();"
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe' or "
        "Name='pythonw.exe' or Name='node.exe' or Name='opencode.exe' or "
        "Name='brave.exe' or Name='powershell.exe' or Name='chrome.exe'\" |"
        "ForEach-Object { $p=Get-Process -Id $_.ProcessId -ErrorAction "
        "SilentlyContinue; $o+=[pscustomobject]@{pid=$_.ProcessId;"
        "ppid=$_.ParentProcessId;name=$_.Name;cmd=$_.CommandLine;"
        "cpu=$(if($p){$p.CPU}else{$null});"
        "ws=$(if($p){[math]::Round($p.WorkingSet64/1MB,1)}else{$null})} };"
        "$o|ConvertTo-Json -Compress -Depth 3"
    )
    raw = ps(script, timeout=40)
    if not raw or raw.startswith('ERROR'):
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else [data]
    except Exception:
        return []


def clasificar(procs):
    """Reparte los procesos por papel dentro del sistema.

    ORDEN CRITICO: el `opencode run` lleva en su linea de comandos
    `--model "omniroute/COMBO JARVIS"`. Si se comprueba antes la palabra
    "omniroute", el trabajo en curso se confunde con el gateway y el detector
    de cuelgues se queda CIEGO (bug detectado el 15/09/2026 a las 11:26: el
    doctor juro que no habia ningun trabajo en curso y si lo habia). Por eso
    el `opencode run` se comprueba el PRIMERO, y OmniRoute exige node.exe.
    """
    roles = {'motor_app': [], 'puente': [], 'telegram': [], 'omniroute': [],
             'opencode_run': [], 'navegador_headless': [], 'power_shell_tool': []}
    for p in procs:
        cmd = (p.get('cmd') or '')
        nombre = (p.get('name') or '').lower()
        if nombre == 'opencode.exe' and ' run ' in cmd:
            roles['opencode_run'].append(p)
        elif nombre == 'node.exe' and 'omniroute' in cmd.lower():
            roles['omniroute'].append(p)
        elif nombre.startswith('python') and 'servidor.py' in cmd:
            roles['motor_app'].append(p)
        elif nombre.startswith('python') and 'agente_puente.py' in cmd:
            roles['puente'].append(p)
        elif nombre.startswith('python') and 'jarvis_telegram_bot' in cmd:
            roles['telegram'].append(p)
        elif nombre in ('brave.exe', 'chrome.exe') and 'headless' in cmd:
            roles['navegador_headless'].append(p)
        elif nombre == 'powershell.exe' and '.ctx-mode-' in cmd:
            roles['power_shell_tool'].append(p)
    return roles


def _cpus(pids):
    """CPU acumulada (segundos) de esos PID. OJO: en espanol PowerShell
    devuelve la coma decimal ("75,578"), asi que se normaliza a punto."""
    lista = ','.join(str(int(p)) for p in pids)
    script = ("@(%s) | ForEach-Object { $p=Get-Process -Id $_ -ErrorAction "
              "SilentlyContinue; if($p){ \"$_=\" + $p.CPU } }" % lista)
    valores = {}
    for linea in (ps(script) or '').splitlines():
        if '=' in linea:
            clave, valor = linea.split('=', 1)
            try:
                valores[int(clave.strip())] = float(
                    valor.strip().replace(',', '.'))
            except ValueError:
                pass
    return valores


def cpu_delta(pids, espera=3.0):
    """CPU gastada por esos PID durante 'espera' segundos (0 = parado).
    Se mide en Python (dos lecturas + sleep) para no depender de la
    aritmetica de PowerShell, que con la coma decimal devolvia vacio."""
    if not pids:
        return {}
    antes = _cpus(pids)
    time.sleep(espera)
    despues = _cpus(pids)
    return {p: round(despues.get(p, 0.0) - antes.get(p, 0.0), 2)
            for p in pids if p in antes}


def puertos():
    script = (
        "$p=Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |"
        "Where-Object { $_.LocalPort -in %s } | Sort-Object LocalPort;"
        "if($p){$p|ForEach-Object {\"{0}:{1} (PID {2})\" -f "
        "$_.LocalAddress,$_.LocalPort,$_.OwningProcess}} else {'ninguno'}"
        % ','.join(str(p) for p in PUERTOS_CLAVE)
    )
    return ps(script)


def omniroute_http():
    try:
        t0 = time.time()
        r = urllib.request.urlopen(OMNIROUTE_URL, timeout=6)
        ms = (time.time() - t0) * 1000
        r.read(64)
        return 'HTTP %d en %.0f ms  -> gateway SANO' % (r.status, ms)
    except Exception as e:
        return 'CAIDO / NO RESPONDE: %r' % (e,)


def revisar_jsons():
    lineas = []
    for zona, ruta in JSONS:
        nombre = os.path.basename(ruta)
        if not os.path.isfile(ruta):
            lineas.append('  %-18s %-26s NO EXISTE' % (zona, nombre))
            continue
        try:
            with open(ruta, encoding='utf-8') as fh:
                data = json.load(fh)
            if isinstance(data, list):
                extra, n = 'lista', len(data)
            elif isinstance(data, dict):
                extra, n = 'dict', len(data)
            else:
                extra, n = type(data).__name__, 0
            lineas.append('  %-18s %-26s VALIDO (%s, %d entradas)'
                          % (zona, nombre, extra, n))
        except Exception as e:
            lineas.append('  %-18s %-26s ** CORRUPTO ** %r' % (zona, nombre, e))
    return '\n'.join(lineas)


def sesiones_pool(ruta, etiqueta):
    if not os.path.isfile(ruta):
        return '  %s: no hay pool' % etiqueta
    try:
        with open(ruta, encoding='utf-8') as fh:
            pool = json.load(fh)
    except Exception as e:
        return '  %s: CORRUPTO (%r)' % (etiqueta, e)
    if not isinstance(pool, list) or not pool:
        return '  %s: pool vacio' % etiqueta
    salida = ['  %s: %d sesiones' % (etiqueta, len(pool))]
    for s in pool:
        if not isinstance(s, dict):
            continue
        if s.get('last') or s.get('trabajo'):
            salida.append('     - %s msgs=%s%s%s'
                          % (s.get('sid', '?')[:26], s.get('msgs'),
                             '  [ULTIMA]' if s.get('last') else '',
                             '  [MODO TRABAJO]' if s.get('trabajo') else ''))
    return '\n'.join(salida)


def aviso_cuelgues(roles, deltas, procs):
    """Lo importante: distinguir 'trabajando' de 'colgado'."""
    lineas = []
    runs = roles['opencode_run']
    if not runs:
        lineas.append('  (no hay ningun `opencode run` en curso)')
    for p in runs:
        pid = int(p['pid'])
        d = deltas.get(pid)
        hijos = [c for c in procs if c.get('ppid') == pid
                 and (c.get('name') or '').lower() != 'conhost.exe']
        # OJO: una espera deliberada (el agente hace "Start-Sleep 110" para
        # dejar que termine un despliegue) se ve igual que un cuelgue: 0% de
        # CPU con una herramienta debajo. Se distingue por el comando.
        espera = any('start-sleep' in ((h.get('cmd') or '').lower())
                     for h in hijos)
        if d is None:
            estado = 'no pude medir la CPU (revisar a mano)'
        elif d > 0.05:
            estado = 'TRABAJANDO'
        elif espera:
            estado = 'ESPERANDO (pausa deliberada, NO es cuelgue)'
        else:
            estado = '** SIN ACTIVIDAD (posible cuelgue) **'
        lineas.append('  - PID %d  CPU en 3 s = %s s  -> %s'
                      % (pid, 'n/d' if d is None else d, estado))
        cmd = (p.get('cmd') or '')
        sesion = ''
        if '--session' in cmd:
            try:
                sesion = cmd.split('--session')[1].strip().split()[0]
            except Exception:
                sesion = '?'
        lineas.append('     sesion: %s   (RAM %.0f MB)'
                      % (sesion or 'nueva', p.get('ws') or 0))
        if hijos:
            for h in hijos:
                hcmd = (h.get('cmd') or '')[:90].replace('\n', ' ')
                lineas.append('     herramienta hija: %s (PID %s) %s'
                              % ((h.get('name') or '?').lower(), h.get('pid'),
                                 hcmd))
        if d is not None and d <= 0.05 and hijos and not espera:
            lineas.append('     >>> SOSPECHA DE CUELGUE: 0% CPU con una '
                          'herramienta trabada debajo.')
    if roles['navegador_headless']:
        lineas.append('  AVISO: hay %d navegador(es) headless sueltos '
                      '(prohibido: usar manos\\probar_web.py):'
                      % len(roles['navegador_headless']))
        for b in roles['navegador_headless']:
            lineas.append('     - PID %s %s' % (b.get('pid'),
                                                (b.get('cmd') or '')[:80]))
    if roles['power_shell_tool']:
        lineas.append('  AVISO: hay %d PowerShell de herramienta abiertos '
                      '(si llevan mucho rato, son el cuelgue):'
                      % len(roles['power_shell_tool']))
        for s in roles['power_shell_tool']:
            lineas.append('     - PID %s' % s.get('pid'))
    return '\n'.join(lineas)


def main():
    print('=' * 66)
    print('INFORME DE SISTEMAS JARVIS - %s' % time.strftime('%d/%m/%Y %H:%M:%S'))
    print('=' * 66)

    procs = procesos()
    roles = clasificar(procs)
    pids_run = [int(p['pid']) for p in roles['opencode_run']]
    deltas = cpu_delta(pids_run, 3.0) if pids_run else {}

    print('\n[1] MOTOR PRINCIPAL')
    for p in roles['motor_app']:
        print('  app movil  (servidor.py)      PID %-6s RAM %.0f MB'
              % (p.get('pid'), p.get('ws') or 0))
    for p in roles['puente']:
        print('  puente nube (agente_puente.py) PID %-6s RAM %.0f MB'
              % (p.get('pid'), p.get('ws') or 0))
    for p in roles['omniroute']:
        print('  OmniRoute (gateway)           PID %-6s RAM %.0f MB'
              % (p.get('pid'), p.get('ws') or 0))
    telegram_off = os.path.isfile(os.path.join(PROYECTOS, 'telegram_off.flag'))
    if roles['telegram']:
        for p in roles['telegram']:
            print('  bot Telegram                  PID %s' % p.get('pid'))
    elif telegram_off:
        print('  bot Telegram                  APAGADO a proposito '
              '(telegram_off.flag)')
    else:
        print('  bot Telegram                  ** NO ESTA CORRIENDO **')
    if not roles['motor_app'] and not roles['puente']:
        print('  ** OJO: el motor de la app movil no esta levantado **')

    print('\n[2] TRABAJOS EN CURSO Y CUELGUES (lo mas importante)')
    print(aviso_cuelgues(roles, deltas, procs))

    print('\n[3] PUERTOS CLAVE (20128/20131/20132 OmniRoute, 8090/8443 app, '
          '9123 lock)')
    print('  ' + (puertos() or 'ERROR al consultar'))

    print('\n[4] OMNIROUTE (127.0.0.1:20128)')
    print('  ' + omniroute_http())

    print('\n[5] FICHEROS DE ESTADO (JSON)')
    print(revisar_jsons())

    print('\n[6] SESIONES')
    print(sesiones_pool(os.path.join(PUENTE, 'puente_pool.json'),
                        'puente (app movil)'))
    print(sesiones_pool(os.path.join(PROYECTOS, 'pool_sesiones_jarvis.json'),
                        'telegram (bot)'))

    print('\n[7] VERIFICACION WEB (blindaje anti-cuelgue)')
    if os.path.isfile(MARCAS_CALIENTE):
        print('  perfil de navegador CALIENTE ok -> probar_web.py listo')
    else:
        print('  perfil de navegador sin calentar (probar_web.py lo hara '
              'solo en su primer uso)')
    nav = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       'probar_web.py')
    print('  herramienta probar_web.py: %s'
          % ('presente' if os.path.isfile(nav) else '** FALTA **'))

    print('\n' + '=' * 66)
    print('FIN DEL INFORME')
    return 0


if __name__ == '__main__':
    sys.exit(main())
