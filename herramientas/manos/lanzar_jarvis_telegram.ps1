# ============================================================
#  lanzar_jarvis_telegram.ps1 - Orquestador de JARVIS Telegram
#  Creado por JARVIS 22/08/2026. Version 4 (01/09/2026).
#  1) Reactiva el vigilante (si quedo desactivado por "Cerrar completamente")
#  2) Asegura OmniRoute (puerto 20128) si no esta corriendo
#  3) Mata instancias previas del bot
#  4) Lanza el bot jarvis_telegram_bot.py OCULTO (sin ventanas) con logs
#  El icono de JARVIS vive en la bandeja. OmniRoute usa los datos del
#  perfil del usuario (~/.omniroute).
# ============================================================
$ErrorActionPreference = 'SilentlyContinue'

# 04/09/2026 (KIT PORTATIL): rutas DERIVADAS del propio script (funciona
# desde el USB en cualquier PC): kit = dos niveles arriba de manos.
$kit = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$proyectos = Join-Path $kit 'jarvis'
# Python del host (el kit no trae python portable; en esta PC es este).
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

# 3) Matar instancias anteriores del bot
Write-Output 'Deteniendo instancias anteriores del bot...'
Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
    Where-Object { $_.CommandLine -match 'jarvis_telegram_bot' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Seconds 2

# 4) Lanzar el bot de Telegram en segundo plano (sin ventanas)
Write-Output 'Lanzando el bot de Telegram en segundo plano (sin ventanas)...'
$script_bot = Join-Path $proyectos 'jarvis_telegram_bot.py'
Start-Process -FilePath $python -ArgumentList @('-u', ('"' + $script_bot + '"')) `
    -WorkingDirectory $proyectos -WindowStyle Hidden `
    -RedirectStandardOutput $logOut -RedirectStandardError $logErr

Write-Output 'Listo. JARVIS en linea (segundo plano, icono en la bandeja).'
