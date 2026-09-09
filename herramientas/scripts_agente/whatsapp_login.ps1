# Login WhatsApp para Jarvis / mudslide
# Muestra QR en terminal, escanea con WhatsApp > Dispositivos vinculados > Vincular
$cache = "$env:LOCALAPPDATA\mudslide\Data"
Write-Host "Cache: $cache"
Write-Host "Abriendo login QR... escanea con tu celular"
Write-Host "WhatsApp > 3 puntos > Dispositivos vinculados > Vincular dispositivo"
& mudslide login
if ($LASTEXITCODE -eq 0) {
    Write-Host "Login OK"
    & mudslide me
} else {
    Write-Host "Login cancelado o error"
}
