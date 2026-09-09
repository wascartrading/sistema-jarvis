# ============================================================
#  cerrar_jarvis_completo.ps1 - APAGADO COMPLETO de JARVIS
#  Creado por JARVIS 01/09/2026 (boton "Cerrar completamente"
#  de la ventana Ajustes y del menu de la bandeja).
#  Deja a JARVIS COMPLETAMENTE DORMIDO:
#   1) Mata TODAS las instancias del bot
#   2) Mata los procesos opencode run huerfanos que el bot dejo
#   3) Libera el lock de instancia unica (puerto 9123)
#   4) Apaga OmniRoute (puertos 20128/20131/20132) y sus procesos
#   5) Desactiva y detiene el vigilante (para que no lo despierte)
#  El proximo arranque con lanzar_jarvis_telegram.ps1 lo reactiva
#  todo (vigilante + OmniRoute) y levanta el bot limpio.
# ============================================================
$ErrorActionPreference = 'SilentlyContinue'

$lockPort  = 9123
$omniPorts = 20128, 20131, 20132
$patron    = 'jarvis_' + 'telegram' + '_bot'

Write-Output '=== APAGADO COMPLETO DE JARVIS ==='

# 1) Bot: matar TODAS las instancias
Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
    Where-Object { $_.CommandLine -match $patron } |
    ForEach-Object {
        Write-Output "  matando bot PID $($_.ProcessId)"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
Start-Sleep -Seconds 2

# 2) opencode run huerfanos (NO toca omniroute ni otras apps)
Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -match 'opencode.*\brun\b|opencode\.exe.*\brun\b' } |
    ForEach-Object {
        Write-Output "  matando opencode run huerfano PID $($_.ProcessId)"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
Start-Sleep -Seconds 1

# 3) Liberar el lock de instancia unica (9123)
$duenoLock = Get-NetTCPConnection -State Listen -LocalPort $lockPort -ErrorAction SilentlyContinue |
    Select-Object -First 1 -ExpandProperty OwningProcess
if ($duenoLock) {
    Write-Output "  lock 9123 ocupado por PID $duenoLock, liberando..."
    Stop-Process -Id $duenoLock -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 1
} else {
    Write-Output '  OK: lock 9123 libre'
}

# 4) OmniRoute: apagar puertos y procesos
foreach ($p in $omniPorts) {
    $owner = Get-NetTCPConnection -State Listen -LocalPort $p -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty OwningProcess
    if ($owner) {
        Write-Output "  puerto $p -> matando PID $owner"
        Stop-Process -Id $owner -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 800
    }
}
# barrido extra: procesos node con omniroute que hayan quedado
Get-CimInstance Win32_Process -Filter "Name='node.exe'" |
    Where-Object { $_.CommandLine -match 'omniroute' } |
    ForEach-Object {
        Write-Output "  matando proceso omniroute PID $($_.ProcessId)"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

# 5) Vigilante: detenerlo y desactivarlo para que JARVIS quede dormido
schtasks /end /tn "JARVIS Vigilante" 2>$null | Out-Null
schtasks /change /tn "JARVIS Vigilante" /disable 2>$null | Out-Null

Start-Sleep -Seconds 2

# Verificacion final
$restantes = @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
    Where-Object { $_.CommandLine -match $patron })
if ($restantes.Count -eq 0) {
    Write-Output '  OK: 0 instancias del bot'
} else {
    Write-Output "  ATENCION: quedan $($restantes.Count) instancia(s) del bot"
}
$omni = @(Get-NetTCPConnection -State Listen -LocalPort 20128 -ErrorAction SilentlyContinue)
if ($omni.Count -eq 0) {
    Write-Output '  OK: OmniRoute apagado (puerto 20128 libre)'
} else {
    Write-Output '  ATENCION: el puerto 20128 sigue ocupado'
}
Write-Output '=== JARVIS DORMIDO. PROXIMO ARRANQUE LIMPIO ==='
