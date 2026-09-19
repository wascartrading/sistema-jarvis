# ============================================================
#  promover_icono_jarvis.ps1 - Saca el icono de JARVIS del panel
#  de "iconos ocultos" y lo deja FIJO en la barra de tareas
#  (orden del senor Wascar, 18/09/2026).
#
#  Windows 11 guarda la preferencia de los iconos de bandeja en
#  HKCU\Control Panel\NotifyIconSettings\<clave>:
#    IsPromoted = 1  -> siempre visible en la barra de tareas
#    IsPromoted = 0  -> oculto dentro del panel "mostrar iconos ocultos"
#  Este script la activa para los iconos de JARVIS (bot y widget)
#  y reinicia Explorer para que el cambio se aplique al momento.
#
#  Uso:  powershell -ExecutionPolicy Bypass -File promover_icono_jarvis.ps1 [-NoExplorer]
# ============================================================
param([switch]$NoExplorer)
$ErrorActionPreference = 'SilentlyContinue'
$base = 'HKCU:\Control Panel\NotifyIconSettings'

Write-Output "=== PROMOVER ICONO DE JARVIS A LA BARRA DE TAREAS ==="
$tot = 0
Get-ChildItem $base | ForEach-Object {
    $k = Get-ItemProperty $_.PSPath
    if ($k.InitialTooltip -match 'JARVIS|Wally') {
        New-ItemProperty -Path $_.PSPath -Name 'IsPromoted' -PropertyType DWord -Value 1 -Force | Out-Null
        Write-Output ("  promovido: [{0}] {1}" -f $_.PSChildName, $k.InitialTooltip)
        $tot++
    }
}
Write-Output "  total promovidos: $tot"

if (-not $NoExplorer) {
    Write-Output "Reiniciando Explorer (la barra parpadea unos segundos)..."
    Stop-Process -Name explorer -Force
    Start-Sleep -Seconds 2
    if (-not (Get-Process explorer)) { Start-Process explorer }
    Start-Sleep -Seconds 3
    $ex = Get-Process explorer | Select-Object -First 1
    Write-Output "  Explorer activo: PID $($ex.Id)"
}

Write-Output "Verificacion:"
Get-ChildItem $base | ForEach-Object {
    $k = Get-ItemProperty $_.PSPath
    if ($k.InitialTooltip -match 'JARVIS|Wally') {
        Write-Output ("  [{0}] IsPromoted={1} | {2}" -f $_.PSChildName, $k.IsPromoted, $k.InitialTooltip)
    }
}
Write-Output "=== FIN ==="
