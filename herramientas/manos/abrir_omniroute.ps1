# ============================================================
#  abrir_omniroute.ps1 - Abre el panel/ajustes de OmniRoute
#  en el navegador de la PC actual.
#  Creado por JARVIS 01/09/2026 (iniciador "ABRIR OMNIROUTE").
#
#  Totalmente AUTONOMO (funciona desde el kit USB en cualquier
#  PC, sin rutas fijas de la maquina original):
#   1) Detecta el puerto de OmniRoute ACTIVO en ese momento
#      (prueba 20128/20131/20132 y el --port del proceso si existe)
#   2) Si OmniRoute esta CAIDO, lo arranca con los datos del kit
#      (KIT\omniroute\data) o del perfil del usuario, y espera
#   3) Abre el navegador en http://127.0.0.1:<puerto>/
#  Uso:  powershell -ExecutionPolicy Bypass -File abrir_omniroute.ps1
# ============================================================
param(
    [bool]$Open = $true   # abrir el navegador (false solo informa la URL)
)

$ErrorActionPreference = 'SilentlyContinue'

# Ruta de este script: KIT\herramientas\manos -> KIT
$manos = Split-Path -Parent $MyInvocation.MyCommand.Path
$kit   = Split-Path (Split-Path $manos -Parent) -Parent

# Puertos probados en orden (el estandar de OmniRoute es 20128)
$puertos = @(20128, 20131, 20132)

function Test-PuertoOmni($puerto) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$puerto/" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) { return $true }
    } catch {}
    return $false
}

Write-Output "=== ABRIR OMNIROUTE (kit: $kit) ==="

# 1) Buscar el puerto ya activo en esta PC
$puertoActivo = $null
foreach ($p in $puertos) {
    if (Test-PuertoOmni $p) {
        $puertoActivo = $p
        break
    }
}

# 1b) Si no respondio, ver el --port en la linea de comandos de procesos omniroute
if (-not $puertoActivo) {
    Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match 'omniroute' } |
        ForEach-Object {
            if ($_.CommandLine -match '--port[=\s]+(\d+)') {
                $p = [int]$Matches[1]
                if (Test-PuertoOmni $p) { $puertoActivo = $p }
            }
        }
}

# 2) Si sigue sin haber OmniRoute, arrancarlo (datos del kit o del perfil)
if (-not $puertoActivo) {
    Write-Output "OmniRoute no estaba corriendo. Arrancandolo..."
    $dataDir = Join-Path $kit 'omniroute\data'
    if (-not (Test-Path $dataDir)) { $dataDir = Join-Path $env:USERPROFILE '.omniroute' }
    $orCmd = Get-Command omniroute -ErrorAction SilentlyContinue
    if ($orCmd) {
        $node = (Get-Command node -ErrorAction SilentlyContinue).Source
        if ($node) {
            # 13/09/2026 (fix DOCTOR): OmniRoute 3.8.49 admite por defecto solo
            # UNA peticion "estructuralmente pesada" en vuelo. Con opencode
            # (agente + subagentes + compactacion) eso devuelve el 503
            # "Structurally heavy chat request capacity is busy; retry shortly".
            # El valor 2 es el minimo que OmniRoute documenta para clientes
            # tipo opencode; evita el bloqueo del segundo request pesado.
            $env:OMNIROUTE_CHAT_MAX_HEAVY_IN_FLIGHT = '2'
            $env:DATA_DIR = $dataDir
            $mod = Join-Path (Split-Path $orCmd.Source) 'node_modules\omniroute\bin\omniroute.mjs'
            Start-Process -FilePath $node -ArgumentList @($mod, 'serve', '--no-open', '--no-tray') -WindowStyle Hidden
            Write-Output "   arrancando con datos de: $dataDir"
            for ($i = 0; $i -lt 30; $i++) {
                Start-Sleep -Seconds 1
                if (Test-PuertoOmni 20128) { $puertoActivo = 20128; break }
            }
        }
    }
    if (-not $puertoActivo) {
        Write-Output "ERROR: no se pudo levantar OmniRoute (revise que este instalado)."
        Read-Host "Presione Enter para cerrar"
        exit 1
    }
}

$url = "http://127.0.0.1:$puertoActivo/"
Write-Output "OmniRoute activo en el puerto $puertoActivo -> $url"

# 3) Abrir el navegador
if ($Open) {
    Start-Process $url
    Write-Output "Abriendo el panel de OmniRoute en el navegador..."
} else {
    Write-Output "(modo informativo: no se abrio el navegador)"
}

if ($Open) {
    Start-Sleep -Seconds 2
}