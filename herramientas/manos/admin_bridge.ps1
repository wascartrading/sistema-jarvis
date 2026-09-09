# admin_bridge.ps1 - Puente de JARVIS para ejecutar comandos como ADMINISTRADOR
# (via la tarea programada JARVIS_ELEVADO que corre con privilegios maximos).
#
# PORTABLE (kit 01/09/2026): usa la carpeta temp del USUARIO ACTUAL, no una
# ruta fija de la PC original, para funcionar en cualquier maquina.
#
# Como funciona:
#   1. JARVIS escribe el comando en el archivo de entrada (temp).
#   2. JARVIS lanza la tarea:  schtasks /run /tn JARVIS_ELEVADO
#   3. Este script (ejecutado como admin por la tarea) lee el comando,
#      lo ejecuta y guarda la salida en el archivo de salida.
#   4. JARVIS lee la salida y la reporta.

$dir = Join-Path $env:TEMP 'opencode'
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
$in = Join-Path $dir 'jarvis_admin_in.txt'
$out = Join-Path $dir 'jarvis_admin_out.txt'

try {
    if (-not (Test-Path $in)) {
        'ERROR=No hay comando de entrada' | Set-Content $out -Encoding UTF8
        exit 1
    }
    $cmd = Get-Content $in -Raw
    Remove-Item $in -Force -ErrorAction SilentlyContinue
    $salida = Invoke-Expression $cmd 2>&1 | Out-String
    $code = if ($null -ne $LASTEXITCODE) { $LASTEXITCODE } else { 0 }
    if (-not $salida) { $salida = '(sin salida)' }
    $outTxt = "EXIT=$code`r`n$salida"
    Set-Content -Path $out -Value $outTxt -Encoding UTF8
} catch {
    "ERROR=$($_.Exception.Message)" | Set-Content $out -Encoding UTF8
    exit 1
}