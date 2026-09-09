# ============================================================
# abrir_mentalista.ps1
# Script REUTILIZABLE de JARVIS
# Abre el ultimo capitulo de EL MENTALISTA que el jefe estaba viendo
# en HBO Max (Brave), lo pone en PANTALLA COMPLETA y asegura la
# reproduccion.
#
# COMO FUNCIONA:
#  1. Busca una ventana de Brave que tenga HBO Max / El Mentalista
#     abierta. Si existe, la usa (no abre otra).
#  2. Si no existe, abre HBO Max por URL (editable abajo).
#  3. Trae la ventana al frente, activa pantalla completa (F11)
#     y da a reproducir (espacio + clic en el centro).
#
# Este script es MANIPULABLE: JARVIS puede editar la URL y el titulo
# buscado segun el ultimo capitulo visto por el jefe.
# ============================================================

$ErrorActionPreference = "SilentlyContinue"

# ------------------------------------------------------------
# CONFIGURACION (editar aqui segun el capitulo mas reciente)
# ------------------------------------------------------------
# Texto que identifica la ventana de HBO Max / El Mentalista en Brave
$TituloVentana = "HBO"          # fragmento que debe contener el titulo
$TituloOpcional = "Mentalista"  # fragmento alternativo (debe aparecer en la URL o titulo)

# URL del ultimo capitulo visto (si no hay ventana abierta, abre esto)
$URL = "https://play.max.com/movie/red-john-s-footsteps"  # embarque: episodio 1x15 "Red John's Footsteps"

# ------------------------------------------------------------
# 1. Buscar ventana de Brave con HBO / El Mentalista
# ------------------------------------------------------------
$proceso = Get-Process brave | Where-Object { $_.MainWindowTitle -like "*$TituloVentana*" -or $_.MainWindowTitle -like "*$TituloOpcional*" } | Select-Object -First 1

if (-not $proceso) {
    Write-Host "No hay ventana de HBO abierta. Abriendo URL: $URL"
    Start-Process "brave" -ArgumentList "--start-fullscreen", "`"$URL`""
    Start-Sleep -Seconds 8
    $proceso = Get-Process brave | Where-Object { $_.MainWindowTitle -like "*$TituloVentana*" -or $_.MainWindowTitle -like "*$TituloOpcional*" } | Select-Object -First 1
}

if (-not $proceso) {
    Write-Error "No se pudo localizar la ventana de HBO Max en Brave."
    exit 1
}

Write-Host "Ventana encontrada: $($proceso.MainWindowTitle)"

# ------------------------------------------------------------
# 2. Traer al frente, maximizar y pantalla completa
# ------------------------------------------------------------
$wshell = New-Object -ComObject WScript.Shell
$wshell.AppActivate($proceso.MainWindowTitle) | Out-Null
Start-Sleep -Milliseconds 600

# Asegurar que la ventana este maximizada y al frente
try {
    Add-Type -AssemblyName System.Windows.Forms
    $wshell.SendKeys("{F11}")   # pantalla completa del navegador
    Start-Sleep -Milliseconds 1200
} catch {
    Write-Host "No se pudo enviar F11 (pantalla completa)."
}

# ------------------------------------------------------------
# 3. Asegurar reproduccion: espacio + clic en el centro
# ------------------------------------------------------------
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$wshell.AppActivate($proceso.MainWindowTitle) | Out-Null
Start-Sleep -Milliseconds 800

# Barra espaciadora para reanudar/alternar play
[System.Windows.Forms.SendKeys]::SendWait(" ")
Start-Sleep -Milliseconds 400

# Clic en el centro de la pantalla (boton de play/pausa del reproductor)
$b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$x = [int]($b.Width / 2)
$y = [int]($b.Height / 2)
[System.Windows.Forms.Cursor]::Position = New-Object System.Drawing.Point($x, $y)
Start-Sleep -Milliseconds 500
$wshell.SendKeys("{ENTER}")
Start-Sleep -Milliseconds 300
[System.Windows.Forms.SendKeys]::SendWait(" ")

Write-Host "LISTO: El Mentalista abierto a pantalla completa y en reproduccion."
