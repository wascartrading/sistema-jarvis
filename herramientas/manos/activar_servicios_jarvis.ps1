# ============================================================
#  activar_servicios_jarvis.ps1 - REACTIVA los servicios neutralizados
#  Creado por JARVIS 15/09/2026 (orden del jefe): deja TODO listo para
#  volver a activar el widget de voz, el servidor del movil y el agente
#  del puente con un solo comando.
#
#  Uso:
#     & "C:\Users\wasc4\Documents\Sistema Jarvis\Proyectos de asistente\manos\activar_servicios_jarvis.ps1"
#     (opcional) -SoloMovil  -SoloPuente  -SoloWidget   para reactivar uno
#
#  Que hace:
#     1) Borra los flags widget_off.flag / movil_off.flag / puente_off.flag
#     2) Levanta el servidor del movil (8090/8443) si no corre
#     3) Levanta el agente del puente si no corre
#     4) Lanza el widget de voz si no corre
#  NO reinicia el bot de Telegram: no hace falta (los flags se leen en vivo).
# ============================================================
param(
    [switch]$SoloWidget,
    [switch]$SoloMovil,
    [switch]$SoloPuente
)
$ErrorActionPreference = 'SilentlyContinue'

$proyectos = 'C:\Users\wasc4\Documents\Sistema Jarvis\proyectos'
$py311 = 'C:\Users\wasc4\AppData\Local\Programs\Python\Python311\python.exe'

# Si no se pide nada concreto, se reactiva TODO
$todo = -not ($SoloWidget -or $SoloMovil -or $SoloPuente)
$hacerWidget = $todo -or $SoloWidget
$hacerMovil = $todo -or $SoloMovil
$hacerPuente = $todo -or $SoloPuente

Write-Output '=== REACTIVANDO SERVICIOS DE JARVIS ==='

# ---------------- 1) WIDGET DE VOZ ----------------
if ($hacerWidget) {
    Remove-Item (Join-Path $proyectos 'widget_off.flag') -Force
    $w = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -match 'widget_voz_jarvis' }
    if ($w) {
        Write-Output 'Widget de voz: ya estaba corriendo (flag borrado).'
    } else {
        $scriptW = Join-Path $proyectos 'widget_voz_jarvis\widget.py'
        if ((Test-Path $py311) -and (Test-Path $scriptW)) {
            Start-Process -FilePath $py311 -ArgumentList @($scriptW, '--mostrar') `
                -WorkingDirectory (Join-Path $proyectos 'widget_voz_jarvis') -WindowStyle Hidden
            Start-Sleep -Seconds 2
            Write-Output 'Widget de voz: lanzado (flag borrado).'
        } else {
            Write-Output 'Widget de voz: NO encontrado el script o el Python 3.11.'
        }
    }
}

# ---------------- 2) SERVIDOR DEL MOVIL ----------------
if ($hacerMovil) {
    Remove-Item (Join-Path $proyectos 'movil_off.flag') -Force
    $m = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -match 'servidor\.py' }
    if ($m) {
        Write-Output 'Servidor del movil: ya estaba corriendo (flag borrado).'
    } else {
        $dirMov = Join-Path $proyectos 'jarvis_movil'
        if ((Test-Path $py311) -and (Test-Path (Join-Path $dirMov 'servidor.py'))) {
            Start-Process -FilePath $py311 -ArgumentList @('-X','utf8','-u','servidor.py') `
                -WorkingDirectory $dirMov -WindowStyle Hidden
            Start-Sleep -Seconds 2
            Write-Output 'Servidor del movil: lanzado (8090 HTTP / 8443 HTTPS).'
        } else {
            Write-Output 'Servidor del movil: NO encontrado el script o el Python 3.11.'
        }
    }
}

# ---------------- 3) AGENTE DEL PUENTE ----------------
if ($hacerPuente) {
    Remove-Item (Join-Path $proyectos 'puente_off.flag') -Force
    $p = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -match 'agente_puente' }
    if ($p) {
        Write-Output 'Agente del puente: ya estaba corriendo (flag borrado).'
    } else {
        $cmdPuente = Join-Path $proyectos 'iniciar_puente_agente.cmd'
        if (Test-Path $cmdPuente) {
            Start-Process -FilePath $cmdPuente -WindowStyle Hidden
            Start-Sleep -Seconds 2
            Write-Output 'Agente del puente: lanzado.'
        } else {
            Write-Output 'Agente del puente: NO se encontro iniciar_puente_agente.cmd.'
        }
    }
}

Write-Output '=== LISTO. Los flags borrados quedan en la papelera del sistema: nada mas que hacer. ==='
