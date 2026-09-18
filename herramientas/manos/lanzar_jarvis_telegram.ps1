# ============================================================
#  lanzar_jarvis_telegram.ps1 - Orquestador de JARVIS Telegram
#  Creado por JARVIS 22/08/2026. Version 4 (01/09/2026).
#  Version 5 (05/09/2026): lock de arranque anti-carrera (evita
#  dobles instancias cuando dos lanzadores corren a la vez).
#  1) Reactiva el vigilante (si quedo desactivado por "Cerrar completamente")
#  2) Asegura OmniRoute (puerto 20128) si no esta corriendo
#  3) Mata instancias previas del bot
#  4) Lanza el bot jarvis_telegram_bot.py OCULTO (sin ventanas) con logs
#  El icono de JARVIS vive en la bandeja. OmniRoute usa los datos del
#  perfil del usuario (~/.omniroute).
# ============================================================
$ErrorActionPreference = 'SilentlyContinue'

# Lock de arranque (FIX 05/09/2026): impide que DOS lanzadores corran a la
# vez (p.ej. tarea de inicio + vigilante al encender la PC) y dejen 2 bots.
$lockLanzador = Join-Path $env:TEMP 'jarvis_lanzador.lock'
$fsLanzador = $null
try {
    $fsLanzador = [System.IO.File]::Open($lockLanzador,
        [System.IO.FileMode]::OpenOrCreate,
        [System.IO.FileAccess]::ReadWrite,
        [System.IO.FileShare]::None)
} catch {
    Write-Output 'Otro lanzador de JARVIS ya esta corriendo. Saliendo para evitar doble instancia.'
    exit 0
}

try {
    $proyectos = 'C:\Users\wasc4\Documents\Sistema Jarvis\proyectos'
    $python = 'C:\Users\wasc4\AppData\Local\Programs\Python\Python312\python.exe'
    $logDir = Join-Path $env:TEMP 'opencode'
    $logOut = Join-Path $logDir 'jarvis_bot_out.log'
    $logErr = Join-Path $logDir 'jarvis_bot_err.log'
    # 1) Vigilante activo (por si "Cerrar completamente" lo desactivo)
    schtasks /change /tn "JARVIS Vigilante" /enable 2>$null | Out-Null

    # 2) OmniRoute: si no responde en 20128, arrancarlo con los datos del usuario
    try {
        $r = Invoke-WebRequest -Uri 'http://127.0.0.1:20128/' -UseBasicParsing -TimeoutSec 2
    } catch {
        $r = $null
    }
    if (-not $r) {
        Write-Output 'OmniRoute caido, arrancando...'
        $env:DATA_DIR = Join-Path $env:USERPROFILE '.omniroute'
        $orCmd = Get-Command omniroute -ErrorAction SilentlyContinue
        if ($orCmd) {
            $node = (Get-Command node -ErrorAction SilentlyContinue).Source
            if ($node) {
                $mod = Join-Path (Split-Path $orCmd.Source) 'node_modules\omniroute\bin\omniroute.mjs'
                Start-Process -FilePath $node -ArgumentList @($mod, 'serve', '--no-open', '--no-tray') -WindowStyle Hidden
                Start-Sleep -Seconds 4
            }
        }
    }

    # 3-4) Bot de Telegram + widget: NEUTRALIZADOS por ahora (orden del jefe
    # 14/09/2026): mientras exista el archivo telegram_off.flag, el bot (y con
    # el, el widget de voz) NO se lanzan al iniciar la PC. Para reactivarlos:
    # borrar el archivo (o pedirselo a JARVIS).
    $flagTelegramOff = Join-Path $proyectos 'telegram_off.flag'
    if (Test-Path $flagTelegramOff) {
        Write-Output 'Telegram neutralizado (telegram_off.flag presente): no se lanza el bot ni el widget.'
    } else {
        # 3) Matar instancias anteriores del bot
        Write-Output 'Deteniendo instancias anteriores del bot...'
        Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
            Where-Object { $_.CommandLine -match 'jarvis_telegram_bot' } |
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 2

        # 3-bis) ROTACION DE LOGS (16/09/2026, orden del jefe): DESPUES de matar
        # al bot (el archivo estaba en uso y el Move fallaba en silencio, por eso
        # la primera version no guardaba nada). El log anterior se conserva en
        # proyectos\registro\logs\ para diagnosticar reinicios y cortes.
        $dirLogsBot = Join-Path $proyectos 'registro\logs'
        if (-not (Test-Path $dirLogsBot)) {
            New-Item -ItemType Directory -Path $dirLogsBot -Force | Out-Null
        }
        Start-Sleep -Milliseconds 600
        foreach ($par in @(@($logOut, 'salida'), @($logErr, 'errores'))) {
            $archivo = $par[0]
            $etiqueta = $par[1]
            if (Test-Path $archivo) {
                $item = Get-Item $archivo
                if ($item.Length -gt 0) {
                    $sello = $item.LastWriteTime.ToString('yyyyMMdd_HHmmss')
                    $destino = Join-Path $dirLogsBot ("bot_" + $etiqueta + "_" + $sello + ".log")
                    Move-Item -LiteralPath $archivo -Destination $destino -Force -ErrorAction SilentlyContinue
                } else {
                    Remove-Item -LiteralPath $archivo -Force -ErrorAction SilentlyContinue
                }
            }
        }

        # 4) Lanzar el bot de Telegram en segundo plano (sin ventanas)
        Write-Output 'Lanzando el bot de Telegram en segundo plano (sin ventanas)...'
        $script_bot = Join-Path $proyectos 'jarvis_telegram_bot.py'
        Start-Process -FilePath $python -ArgumentList @('-u', ('"' + $script_bot + '"')) `
            -WorkingDirectory $proyectos -WindowStyle Hidden `
            -RedirectStandardOutput $logOut -RedirectStandardError $logErr
    }

    # 5) Servidor del movil + Agente del PUENTE (13/09/2026, orden del jefe):
    #    la app del telefono usa SIEMPRE la nube; sin esto, tras encender la PC
    #    la app se quedaba sin PC y sin "despertar". Idempotente: si ya corren,
    #    no hace nada.
    # NEUTRALIZABLES (orden del jefe 15/09/2026): si existen los flags
    # "movil_off.flag" / "puente_off.flag", cada servicio NO se lanza.
    # Reversible: borrar el flag (o usar manos\activar_servicios_jarvis.ps1).
    $flagMovil = Join-Path $proyectos 'movil_off.flag'
    $flagPuente = Join-Path $proyectos 'puente_off.flag'
    $py311 = 'C:\Users\wasc4\AppData\Local\Programs\Python\Python311\python.exe'
    $dir_movil = Join-Path $proyectos 'jarvis_movil'
    $srv_movil = Join-Path $dir_movil 'servidor.py'
    if (Test-Path $flagMovil) {
        Write-Output 'Servidor del movil NEUTRALIZADO (movil_off.flag): no se lanza.'
    } elseif ((Test-Path $py311) -and (Test-Path $srv_movil)) {
        $ya = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
            Where-Object { $_.CommandLine -match 'servidor\.py' }
        if (-not $ya) {
            Start-Process -FilePath $py311 -ArgumentList @('-X','utf8','-u','servidor.py') `
                -WorkingDirectory $dir_movil -WindowStyle Hidden
        }
    }
    $cmdPuente = Join-Path $proyectos 'iniciar_puente_agente.cmd'
    if (Test-Path $flagPuente) {
        Write-Output 'Agente del puente NEUTRALIZADO (puente_off.flag): no se lanza.'
    } elseif (Test-Path $cmdPuente) {
        $ya = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
            Where-Object { $_.CommandLine -match 'agente_puente' }
        if (-not $ya) {
            # FIX 14/09/2026: el .cmd se lanza DIRECTO (-FilePath). Con
            # "cmd.exe /c <ruta>" sin comillas, el path con espacios
            # ("Sistema Jarvis") se partia y el agente NO arrancaba al
            # encender la PC (lo detecto el jefe en su reinicio).
            Start-Process -FilePath $cmdPuente -WindowStyle Hidden
        }
    }

    Write-Output 'Listo. JARVIS en linea (segundo plano, icono en la bandeja).'
} finally {
    if ($fsLanzador) { $fsLanzador.Close() }
    Remove-Item $lockLanzador -Force -ErrorAction SilentlyContinue
}