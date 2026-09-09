# ============================================================
#  autostart_jarvis.ps1 - Iniciador de JARVIS con Windows
#  Generado por la ventana Ajustes de JARVIS Telegram (01/09/2026).
#  Vive junto al bot: se mueve con el kit USB. Arranca OmniRoute
#  si hace falta y luego el bot en segundo plano, oculto.
#  Para quitarlo: desactiva la casilla en Ajustes.
# ============================================================
$ErrorActionPreference = 'SilentlyContinue'

# Carpeta donde vive este script (= carpeta del bot)
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = 'C:\\Users\\wasc4\\AppData\\Local\\Programs\\Python\\Python312\\python.exe'
$bot = Join-Path $dir 'jarvis_telegram_bot.py'

# 1) OmniRoute: si no responde en 20128, arrancarlo con los datos del
#    kit (si existen) o del perfil del usuario
try {
    $r = Invoke-WebRequest -Uri 'http://127.0.0.1:20128/' -UseBasicParsing -TimeoutSec 2
} catch {
    $r = $null
}
if (-not $r) {
    $dataDir = Join-Path $dir 'omniroute\data'
    if (-not (Test-Path $dataDir)) {
        $dataDir = Join-Path (Split-Path $dir -Parent) 'omniroute\data'
    }
    if (-not (Test-Path $dataDir)) {
        $dataDir = Join-Path $env:USERPROFILE '.omniroute'
    }
    $env:DATA_DIR = $dataDir
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

# 2) Arrancar el bot en segundo plano (sin ventanas)
Start-Process -FilePath $python -ArgumentList @('-u', ('"' + $bot + '"')) -WorkingDirectory $dir -WindowStyle Hidden
