# cerrar_pestanas_youtube.ps1 - cierra TODAS las pestanas de YouTube en Brave.
# Creado 22/08/2026 (manos de JARVIS).
#
# Usa UI Automation de Windows para:
#   1) Encontrar la ventana de Brave en primer plano.
#   2) Listar las pestanas (elementos con rol TabItem) y su titulo.
#   3) Cerrar SOLO las pestanas cuyo titulo contenga "YouTube".
#
# Uso:  powershell -ExecutionPolicy Bypass -File cerrar_pestanas_youtube.ps1
# No cierra otras pestanas (solo las de YouTube). Seguro y no destructivo.

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

# Buscar la PRIMERA instancia de Brave que tenga una ventana principal real
# (con MainWindowHandle != 0). Brave lanza muchos procesos auxiliares sin
# ventana; el que tiene la UI es el que trae MainWindowTitle.
$brave = Get-Process -Name "brave" -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowHandle -ne 0 } |
    Select-Object -First 1
if (-not $brave) {
    Write-Output '{"ok":false,"razon":"Brave no esta abierto"}'
    exit 0
}

# Traer Brave al frente y enfocar su ventana.
$hwnd = $brave.MainWindowHandle
if ($hwnd -ne 0) {
    try {
        Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Foco {
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
}
"@
        [Foco]::SetForegroundWindow($hwnd) | Out-Null
    } catch {}
}
Start-Sleep -Milliseconds 500

# Raiz de la ventana de Brave.
$root = [System.Windows.Automation.AutomationElement]::FromHandle($hwnd)
if (-not $root) {
    Write-Output '{"ok":false,"razon":"No se pudo obtener la ventana de Brave"}'
    exit 0
}

# Recorrer descendientes buscando TabItems (las pestanas del navegador).
$cond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::TabItem)
$tabs = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cond)

$cerradas = 0
$tbody = @()
$youtube = @()

foreach ($tab in $tabs) {
    $titulo = $tab.Current.Name
    $tituloLimpio = ($titulo -replace '\s+', ' ').Trim()
    $tbody += $tituloLimpio
    if ($tituloLimpio -match 'YouTube') {
        $youtube += $tab
    }
}

# Cerrar cada pestana de YouTube con Ctrl+W tras activarla.
$wshell = New-Object -ComObject wscript.shell
foreach ($yt in $youtube) {
    try {
        # Click en la pestana para activarla (SelectionItemPattern).
        $sel = $null
        try { $sel = $yt.GetCurrentPattern(
            [System.Windows.Automation.SelectionItemPattern]::Pattern) } catch { $sel = $null }
        if ($sel) { $sel.Select() } 
        Start-Sleep -Milliseconds 300
        # Ya con la pestana activa, cerrar con Ctrl+W.
        $wshell.AppActivate($hwnd) | Out-Null
        Start-Sleep -Milliseconds 200
        $wshell.SendKeys('^w')
        Start-Sleep -Milliseconds 400
        $cerradas++
    } catch {}
}

# Salida JSON con el detalle.
$out = @{ ok = $true; cerradas = $cerradas; total_pestanas = $tbody.Count
          pestanas = $tbody; youtube_encontradas = $youtube.Count }
$out | ConvertTo-Json -Compress
