# ============================================================
#  vigilar_jarvis.ps1 - Vigilante de JARVIS (tarea programada)
#  Si el bot de Telegram de JARVIS no esta corriendo, lo relanza
#  con el orquestador (mata instancias y levanta todo).
#  Creado por JARVIS 22/08/2026.
# ============================================================
$ErrorActionPreference = 'SilentlyContinue'

$bot = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
    Where-Object { $_.CommandLine -match 'jarvis_telegram_bot' }

if (-not $bot) {
    $fecha = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path "$env:TEMP\opencode\jarvis_vigilante.log" -Value "[$fecha] Bot caido, relanzando JARVIS..."
    # 04/09/2026 (KIT PORTATIL): el lanzador vive junto a este script.
    & (Join-Path $PSScriptRoot 'lanzar_jarvis_telegram.ps1')
} else {
    # Solo el bot COMBO JARVIS activo: no verificar kilo
    # $server check desactivado porque ahora solo Muse via Opencode
}