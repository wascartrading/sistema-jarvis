# JARVIS - Leer mensajes de un contacto de WhatsApp
# Uso: .\whatsapp_leer.ps1 -Para "Rainer" [-N 40]
param(
    [Parameter(Mandatory=$true)][string]$Para,
    [int]$N = 40
)
$base = "http://127.0.0.1:20130/api"
# Buscar el chat por nombre en /api/contactos
$contactos = Invoke-RestMethod -Uri "$base/contactos" -TimeoutSec 10
if (-not $contactos.ok) { Write-Host "ERROR: $($contactos.error)"; exit 1 }
$chat = $contactos.contactos | Where-Object { $_.nombre -ieq $Para.Trim() } | Select-Object -First 1
if (-not $chat) {
    Write-Host "No encontre el contacto '$Para'. Estos son algunos:"
    $contactos.contactos | Select-Object -First 20 | ForEach-Object { Write-Host "  - $($_.nombre) [$($_.id)]" }
    exit 1
}
$encoded = [uri]::EscapeDataString($chat.id)
$r = Invoke-RestMethod -Uri "$base/mensajes?chat=$encoded&limite=$N" -TimeoutSec 15
Write-Host "=== $($r.chat.nombre) ($($r.chat.id)) ==="
foreach ($m in ($r.mensajes | Select-Object -Last $N)) {
    $hora = [DateTimeOffset]::FromUnixTimeSeconds($m.timestamp).ToLocalTime().ToString("dd/MM HH:mm")
    $quien = if ($m.yo) { 'YO' } else { $m.de }
    Write-Host "[$hora] $($quien): $($m.texto)"
}