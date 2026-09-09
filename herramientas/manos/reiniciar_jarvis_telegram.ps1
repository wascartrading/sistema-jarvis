# ============================================================
#  reiniciar_jarvis_telegram.ps1 - REINICIO QUIRURGICO de JARVIS Telegram
#  Creado por el Doctor 31/08/2026. Disparado por el BOTON "Reiniciar"
#  del menu inline de Telegram (accion directa del sistema, el modelo
#  no participa).
#  1) Espera 3s (para que el mensaje de confirmacion llegue al jefe)
#  2) Mata TODAS las instancias del bot en segundo plano
#  3) Libera el lock de instancia unica (puerto 9123)
#  4) Elimina procesos/puertos zombie de opencode run que el bot dejo
#  5) Verifica que no queden instancias dobles ni puertos colgados
#  6) Relanza el bot limpio (oculto, con logs)
#  OmniRoute (20128/20131/20132) NO se toca: es el proveedor del cerebro.
# ============================================================
$ErrorActionPreference = 'SilentlyContinue'

# 04/09/2026 (KIT PORTATIL): rutas DERIVADAS del propio script.
$kit = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$python = 'C:\Users\wasc4\AppData\Local\Programs\Python\Python312\python.exe'
$proyectos = Join-Path $kit 'jarvis'
$script_bot = Join-Path $proyectos 'jarvis_telegram_bot.py'
$logDir = Join-Path $env:TEMP 'opencode'
$logOut = Join-Path $logDir 'jarvis_bot_out.log'
$logErr = Join-Path $logDir 'jarvis_bot_err.log'
$lockPort = 9123

# Patron ofuscado (evita que este script se mate a si mismo por el filtro)
$patron = 'jarvis_' + 'telegram' + '_bot'

Write-Output '=== REINICIO QUIRURGICO JARVIS TELEGRAM ==='
Start-Sleep -Seconds 3

# 1) Matar TODAS las instancias del bot (python/pythonw con el fuente)
Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
    Where-Object { $_.CommandLine -match $patron } |
    ForEach-Object {
        Write-Output "  matando bot PID $($_.ProcessId)"
        Stop-Process -Id $_.ProcessId -Force
    }
Start-Sleep -Seconds 2

# 2) Liberar el lock de instancia unica (9123) si quedo colgado
$duenoLock = Get-NetTCPConnection -State Listen -LocalPort $lockPort -ErrorAction SilentlyContinue |
    Select-Object -First 1 -ExpandProperty OwningProcess
if ($duenoLock) {
    Write-Output "  lock 9123 ocupado por PID $duenoLock, liberando..."
    Stop-Process -Id $duenoLock -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}

# 3) Matar procesos opencode run HUERFANOS que el bot dejo colgados
#    (opencode run / opencode.exe run / node con opencode). NO toca
#    omniroute (20128) ni kilo (4096).
Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -match 'opencode.*\brun\b|opencode\.exe.*\brun\b' } |
    ForEach-Object {
        Write-Output "  matando opencode run huerfano PID $($_.ProcessId)"
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
Start-Sleep -Seconds 2

# 4) Verificar que no queden instancias del bot (doble check)
$restantes = @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
    Where-Object { $_.CommandLine -match $patron })
if ($restantes.Count -gt 0) {
    Write-Output "  ATENCION: quedaban $($restantes.Count) instancia(s), matando de nuevo..."
    $restantes | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
    Start-Sleep -Seconds 2
} else {
    Write-Output '  OK: 0 instancias del bot'
}

# 5) Verificar el lock quedo libre
if (Get-NetTCPConnection -State Listen -LocalPort $lockPort -ErrorAction SilentlyContinue) {
    Write-Output '  ATENCION: lock 9123 sigue ocupado, forzando liberacion...'
    $pidLock = Get-NetTCPConnection -State Listen -LocalPort $lockPort -ErrorAction SilentlyContinue |
        Select-Object -First 1 -ExpandProperty OwningProcess
    if ($pidLock) { Stop-Process -Id $pidLock -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
} else {
    Write-Output '  OK: lock 9123 libre'
}

# 6) Relanzar el bot limpio (oculto, sin ventanas, con logs)
Write-Output '  relanzando JARVIS Telegram...'
Start-Process -FilePath $python -ArgumentList @('-u', ('"' + $script_bot + '"')) `
    -WorkingDirectory $proyectos -WindowStyle Hidden `
    -RedirectStandardOutput $logOut -RedirectStandardError $logErr

Start-Sleep -Seconds 12

# 7) Verificacion final
$nuevo = @(Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
    Where-Object { $_.CommandLine -match $patron })
if ($nuevo.Count -eq 1) {
    Write-Output "  PACIENTE SANO: 1 instancia del bot (PID $($nuevo[0].ProcessId))"
} elseif ($nuevo.Count -gt 1) {
    Write-Output "  ATENCION: $($nuevo.Count) instancias, revisar"
} else {
    Write-Output '  ATENCION: el bot no arranco, revisar log'
}
Write-Output '=== REINICIO COMPLETADO ==='