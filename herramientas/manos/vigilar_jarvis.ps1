# ============================================================
#  vigilar_jarvis.ps1 - Vigilante de JARVIS (tarea programada)
#  Si el bot de Telegram de JARVIS no esta corriendo, lo relanza
#  con el orquestador (mata instancias y levanta todo).
#  Creado por JARVIS 22/08/2026.
# ============================================================
$ErrorActionPreference = 'SilentlyContinue'

# Telegram NEUTRALIZADO (orden del jefe 14/09/2026): mientras exista el flag,
# el vigilante NO revive el bot (ni su widget).
$flagOff = "C:\Users\wasc4\Documents\Sistema Jarvis\proyectos\telegram_off.flag"
if (Test-Path $flagOff) {
    $bot = $null
} else {
    $bot = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" |
        Where-Object { $_.CommandLine -match 'jarvis_telegram_bot' }
}

if ((-not $bot) -and (-not (Test-Path $flagOff))) {
    $fecha = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path "$env:TEMP\opencode\jarvis_vigilante.log" -Value "[$fecha] Bot caido, relanzando JARVIS..."
    & "C:\Users\wasc4\Documents\Sistema Jarvis\Proyectos de asistente\manos\lanzar_jarvis_telegram.ps1"
} else {
    # Solo el bot COMBO JARVIS activo: no verificar kilo
    # $server check desactivado porque ahora solo Muse via Opencode
}

# Agente del PUENTE + servidor del movil (13/09/2026, orden del jefe): si
# faltan (p.ej. tras un corte inesperado), se vuelven a levantar solos.
# NEUTRALIZABLES (orden del jefe 15/09/2026): mientras existan los flags
# "puente_off.flag" / "movil_off.flag", el vigilante NO los revive.
# Reversible: borrar el flag (o usar manos\activar_servicios_jarvis.ps1).
$flagPuente = "C:\Users\wasc4\Documents\Sistema Jarvis\proyectos\puente_off.flag"
$flagMovil = "C:\Users\wasc4\Documents\Sistema Jarvis\proyectos\movil_off.flag"
if (Test-Path $flagPuente) {
    $agente = $null
} else {
    $agente = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -match 'agente_puente' }
}
if ((-not $agente) -and (-not (Test-Path $flagPuente))) {
    $cmdPuente = "C:\Users\wasc4\Documents\Sistema Jarvis\proyectos\iniciar_puente_agente.cmd"
    if (Test-Path $cmdPuente) {
        $fecha = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Add-Content -Path "$env:TEMP\opencode\jarvis_vigilante.log" -Value "[$fecha] Agente del puente caido, relanzando..."
        # FIX 14/09/2026: lanzar el .cmd DIRECTO (con cmd.exe el path con
        # espacios se partia sin comillas y el agente no arrancaba).
        Start-Process -FilePath $cmdPuente -WindowStyle Hidden
    }
}
if (Test-Path $flagMovil) {
    $srvMov = $null
} else {
    $srvMov = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -match 'servidor\.py' }
}
if ((-not $srvMov) -and (-not (Test-Path $flagMovil))) {
    $py311 = 'C:\Users\wasc4\AppData\Local\Programs\Python\Python311\python.exe'
    $dirMov = "C:\Users\wasc4\Documents\Sistema Jarvis\proyectos\jarvis_movil"
    if ((Test-Path $py311) -and (Test-Path "$dirMov\servidor.py")) {
        $fecha = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        Add-Content -Path "$env:TEMP\opencode\jarvis_vigilante.log" -Value "[$fecha] Servidor movil caido, relanzando..."
        Start-Process -FilePath $py311 -ArgumentList @('-X','utf8','-u','servidor.py') -WorkingDirectory $dirMov -WindowStyle Hidden
    }
}