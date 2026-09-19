# ============================================================================
#  enviar_caps_todas.ps1 — Habilidad de JARVIS: un cap de CADA ventana abierta
# ----------------------------------------------------------------------------
#  Orden permanente del jefe (15/09/2026): cuando pida "un cap", JARVIS debe
#  mandarle una captura de CADA ventana de Windows abierta (Brave, WhatsApp,
#  OpenCode, etc.), no solo del escritorio.
#
#  Reutiliza la habilidad enviar-cap (enviar_cap_telegram.ps1), que ya sabe
#  capturar por PrintWindow (funciona aunque el monitor este en reposo) y
#  enviar la foto por Telegram. Aqui solo se enumeran las ventanas y se
#  llama una vez por ventana.
#
#  Uso:
#    powershell -NoProfile -ExecutionPolicy Bypass -File enviar_caps_todas.ps1
#    ... -Max 8          (limite de ventanas, por defecto 8)
#    ... -IncluirGlobal  (ademas, un cap del escritorio completo)
#
#  Salida: JSON con cuantas ventanas se enviaron y cuales fallaron.
# ============================================================================
param(
    [int]$Max = 8,
    [switch]$IncluirGlobal,
    [switch]$Escritorio
)

$ErrorActionPreference = 'Continue'
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptCap = Join-Path $scriptDir 'enviar_cap_telegram.ps1'

if (-not (Test-Path $scriptCap)) {
    Write-Output '{"ok":false,"motivo":"falta_enviar_cap_telegram"}'
    exit 1
}

# --- Ventanas de nivel superior con titulo (apps reales), sin overlays ---
$excluir = @('Program Manager', 'Experiencia de entrada de Windows', 'MSCTFIME UI',
             'Default IME', 'NvContainer', 'Windows Input Experience',
             'Configuración de entrada de Windows')
$ventanas = Get-Process -ErrorAction SilentlyContinue |
    Where-Object { $_.MainWindowHandle -ne 0 -and $_.MainWindowTitle -ne '' } |
    Select-Object -Property MainWindowTitle, ProcessName |
    Sort-Object MainWindowTitle -Unique

$objetivo = @()
foreach ($v in $ventanas) {
    $t = $v.MainWindowTitle
    $skip = $false
    foreach ($e in $excluir) { if ($t -like "*$e*") { $skip = $true; break } }
    if (-not $skip) { $objetivo += $t }
}
$objetivo = @($objetivo | Select-Object -First $Max)

$enviados = @()
$fallidos = @()

if ($Escritorio) {
    # Solo el escritorio completo (cap global), en un unico envio
    $r = & powershell -NoProfile -ExecutionPolicy Bypass -File $scriptCap -ForzarGlobal
    if ($r -match '"ok":true') { $enviados += 'ESCRITORIO COMPLETO' } else { $fallidos += 'ESCRITORIO COMPLETO' }
} else {
    foreach ($t in $objetivo) {
        $r = & powershell -NoProfile -ExecutionPolicy Bypass -File $scriptCap -Ventana $t
        if ($r -match '"ok":true') { $enviados += $t } else { $fallidos += $t }
        Start-Sleep -Milliseconds 400
    }
    if ($IncluirGlobal) {
        $r = & powershell -NoProfile -ExecutionPolicy Bypass -File $scriptCap -ForzarGlobal
        if ($r -match '"ok":true') { $enviados += 'ESCRITORIO COMPLETO' } else { $fallidos += 'ESCRITORIO COMPLETO' }
    }
}

$resumen = [pscustomobject]@{
    ok               = ($enviados.Count -gt 0)
    enviadas_total   = $enviados.Count
    enviadas         = $enviados
    fallidas         = $fallidos
    total_detectadas = $objetivo.Count
}
$resumen | ConvertTo-Json -Compress -Depth 3
