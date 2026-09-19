<#
============================================================
 adaptar_rutas.ps1 - Re-escribe rutas absolutas de la PC
 original hacia la ubicacion del KIT en la PC nueva.
============================================================
Detecta el nombre de usuario original y las rutas viejas
conocidas, y las sustituye por la ubicacion actual del kit.
Se ejecuta sobre UNA COPIA DE TRABAJO (por defecto el propio
kit) para NO ensuciar el kit original: asi el kit conserva
las rutas de fabrica y puede usarse en multiples PC.

Parametros:
  -Antigua     ruta de la PC original (ej. C:\Users\wasc4)
  -KitDir      raiz del kit (donde estan jarvis/, herramientas/...)
  -UserProfile perfil de la PC nueva
  -Target      carpeta a adaptar (por defecto = KitDir; si se
               pasa otra, se adapta ESA copia sin tocar el kit)
#>
param(
    [string]$Antigua = "C:\Users\wasc4",
    [string]$KitDir = "",
    [string]$UserProfile = "",
    [string]$Target = ""
)

$ErrorActionPreference = 'Continue'
if ($KitDir -eq "") { $KitDir = (Get-Location).Path }
if ($UserProfile -eq "") { $UserProfile = $env:USERPROFILE }
$KitDir = $KitDir.TrimEnd('\')
if ($Target -eq "") { $Target = $KitDir }
$Target = $Target.TrimEnd('\')

# Rutas que se re-escriben. Clave = ruta ORIGINAL (de la PC original/actual),
# Valor = ruta de destino relativa al perfil/kit en la PC nueva.
$manos   = "$KitDir\herramientas\manos"
$scripts = "$KitDir\herramientas\scripts_agente"
$mapa = [ordered]@{
    "$Antigua\Documents\Default Project\Proyectos de asistente\manos"    = $manos
    "~\Documents\Default Project\Proyectos de asistente\manos"           = $manos
    "$Antigua\Documents\Default Project\Proyectos de asistente\scripts_agente" = $scripts
    "~\Documents\Default Project\Proyectos de asistente\scripts_agente"  = $scripts
    "$Antigua\Documents\Default Project\proyectos"                        = "$KitDir\jarvis"
    "~\Documents\Default Project\proyectos"                               = "$KitDir\jarvis"
    "$Antigua\Documents\Sistema Jarvis\Proyectos de asistente\manos"      = $manos
    "~\Documents\Sistema Jarvis\Proyectos de asistente\manos"             = $manos
    "$Antigua\Documents\Sistema Jarvis\Proyectos de asistente\scripts_agente" = $scripts
    "~\Documents\Sistema Jarvis\Proyectos de asistente\scripts_agente"    = $scripts
    "$Antigua\Documents\Sistema Jarvis\proyectos"                         = "$KitDir\jarvis"
    "~\Documents\Sistema Jarvis\proyectos"                                = "$KitDir\jarvis"
    "$Antigua\Documents\Sistema Jarvis\SISTEMA_JARVIS.md"                 = "$KitDir\SISTEMA_JARVIS.md"
    "~\Documents\Sistema Jarvis\SISTEMA_JARVIS.md"                        = "$KitDir\SISTEMA_JARVIS.md"
    "$Antigua\Documents\Sistema Jarvis\.opencode"                         = "$UserProfile\.config\opencode"
    "~\Documents\Sistema Jarvis\.opencode"                                = "$UserProfile\.config\opencode"
    "$Antigua\.config\opencode"                                           = "$UserProfile\.config\opencode"
    "$Antigua\Documents\Default Project\.opencode"                        = "$UserProfile\.config\opencode"
}

# Archivos a adaptar bajo $Target (md, py, ps1, json, txt), sin ruido
$archivos = @()
$archivos += Get-ChildItem "$Target" -Recurse -File -Include *.md,*.py,*.ps1,*.json,*.txt -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notmatch 'node_modules|__pycache__|\.git' }

$total = 0
foreach ($f in $archivos) {
    $contenido = Get-Content -LiteralPath $f.FullName -Raw -ErrorAction SilentlyContinue
    if (-not $contenido) { continue }
    $cambio = $false
    foreach ($clave in $mapa.Keys) {
        if ($contenido -match [regex]::Escape($clave)) {
            $contenido = $contenido.Replace($clave, $mapa[$clave])
            $contenido = $contenido.Replace($clave.Replace('\','/'), $mapa[$clave].Replace('\','/'))
            $cambio = $true
        }
    }
    if ($cambio) {
        Set-Content -LiteralPath $f.FullName -Value $contenido -Encoding UTF8
        $total++
        Write-Host "   adaptado: $($f.Name)" -ForegroundColor DarkGray
    }
}
Write-Host "   rutas adaptadas en $total archivo(s) (Target: $Target)." -ForegroundColor Green