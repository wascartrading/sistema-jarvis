# ============================================================
#  reinicio_diferido_jarvis.ps1 - Reinicio de JARVIS pedido por
#  JARVIS desde su propio turno (16/09/2026).
#
#  POR QUE EXISTE: el reinicio tiene que ser EN DIFERIDO (si mata al
#  bot al instante, mata tambien la respuesta que JARVIS esta escribiendo).
#  Antes se lanzaba con Start-Process -Command '...' con la ruta del script
#  entre comillas: PowerShell las PIERDE al reenviar los argumentos y, como
#  "Proyectos de asistente" tiene espacios, el comando no se ejecutaba nunca
#  (el reinicio "no pasaba" y nadie se enteraba). Comprobado el 16/09/2026:
#  con ruta con espacios falla; con EncodedCommand funciona.
#
#  COMO LANZARLO (desde JARVIS):
#    $cmd = 'Start-Sleep -Seconds 12; & "<ruta>\reinicio_diferido_jarvis.ps1"'
#    $b64 = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($cmd))
#    Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -EncodedCommand $b64" -WindowStyle Hidden
#
#  Uso directo:
#    powershell -File reinicio_diferido_jarvis.ps1 [-Segundos 12] [-Simulacion]
# ============================================================
param(
    [int]$Segundos = 12,
    [switch]$Simulacion
)
$ErrorActionPreference = 'SilentlyContinue'

$python = 'C:\Users\wasc4\AppData\Local\Programs\Python\Python312\python.exe'
$proyectos = 'C:\Users\wasc4\Documents\Sistema Jarvis\proyectos'
$reiniciador = 'C:\Users\wasc4\Documents\Sistema Jarvis\Proyectos de asistente\manos\reiniciar_jarvis_telegram.ps1'

# 1) Espera: deja que la respuesta de JARVIS llegue a Telegram antes de cortar.
Start-Sleep -Seconds $Segundos

# 2) Constancia en la CAJA NEGRA (asi el reinicio queda registrado con su hora,
#    y se puede confirmar despues si ocurrio o no).
$motivo = if ($Simulacion) { 'prueba en simulacion (no reinicia)' } else { 'orden del jefe (diferido)' }
& $python -c "import sys; sys.path.insert(0, r'$proyectos'); import registro_jarvis as RJ; RJ.evento('reinicio', motivo='$motivo', diferido=$Segundos, simulacion=$(if ($Simulacion) {1} else {0}))"

if ($Simulacion) {
    Write-Output "SIMULACION: no se reinicia nada. Registro anotado."
    exit 0
}

# 3) Reinicio quirurgico (el mismo que usa el boton "Reiniciar" del menu,
#    que si funciona): mata instancias, libera el lock, limpia zombies,
#    rota los logs y relanza limpio.
& $reiniciador
