<#
============================================================
 adaptar_rutas.ps1 - Re-escribe rutas absolutas de la PC
 original hacia la ubicacion del KIT en la PC nueva.
============================================================
Detecta el nombre de usuario original y las rutas viejas
conocidas, y las sustituye por la ubicacion actual del kit.
Se ejecuta sobre las COPIES dentro del kit (cerebro, skills),
no sobre el sistema original de la otra PC.
#>
param(
    [string]$Antigua = "C:\Users\wasc4",
    [string]$KitDir = "",
    [string]$UserProfile = ""
)

$ErrorActionPreference = 'Continue'
if ($KitDir -eq "") { $KitDir = (Get-Location).Path }
if ($UserProfile -eq "") { $UserProfile = $env:USERPROFILE }
$KitDir = $KitDir.TrimEnd('\')

# Rutas que se re-escriben. Clave = ruta ORIGINAAL (de la PC original),
# Valor = ruta de destino relativa al perfil/kit en la PC nueva.
$manos   = "$KitDir\herramientas\manos"
$mapa = [ordered]@{
    "$Antigua\Documents\Default Project\Proyectos de asistente\manos"    = $manos
    "~\Documents\Default Project\Proyectos de asistente\manos"           = $manos
    "$Antigua\Documents\Default Project\Proyectos de asistente\scripts_agente" = "$KitDir\herramientas\scripts_agente"
    "~\Documents\Default Project\Proyectos de asistente\scripts_agente"  = "$KitDir\herramientas\scripts_agente"
    "$Antigua\Documents\Default Project\proyectos"                        = "$KitDir\jarvis"
    "~\Documents\Default Project\proyectos"                               = "$KitDir\jarvis"
    "$Antigua\.config\opencode"                                           = "$UserProfile\.config\opencode"
    "$Antigua\Documents\Default Project\.opencode"                        = "$UserProfile\.config\opencode"
}

# Archivos a adaptar
$archivos = @()
$archivos += Get-ChildItem "$KitDir\setup\cerebro\*.md" -ErrorAction SilentlyContinue
$archivos += Get-ChildItem "$KitDir\setup\skills" -Recurse -Filter "*.md" -ErrorAction SilentlyContinue
# Tambien el bot copiado (rutas auxiliares que apuntaban a la PC original)
if (Test-Path "$KitDir\jarvis\jarvis_telegram_bot.py") {
    $archivos += Get-Item "$KitDir\jarvis\jarvis_telegram_bot.py"
}

# Nota: el historial/pool real vive SOLO en el kit (carpeta jarvis), no hace
# falta reescribirlos; el bot los lee por ruta relativa a su propio directorio.

$total = 0
foreach ($f in $archivos) {
    $contenido = Get-Content -LiteralPath $f.FullName -Raw -ErrorAction SilentlyContinue
    if (-not $contenido) { continue }
    $cambio = $false
    foreach ($clave in $mapa.Keys) {
        $valor = $mapa[$clave]
        if ($contenido -match [regex]::Escape($clave)) {
            $contenido = $contenido.Replace($clave, $valor)
            $contenido = $contenido.Replace($clave.Replace('\','/'), $valor.Replace('\','/'))
            $cambio = $true
        }
    }
    if ($cambio) {
        Set-Content -LiteralPath $f.FullName -Value $contenido -Encoding UTF8
        $total++
        Write-Host "   adaptado: $($f.Name)" -ForegroundColor DarkGray
    }
}
Write-Host "   rutas adaptadas en $total archivo(s)." -ForegroundColor Green
