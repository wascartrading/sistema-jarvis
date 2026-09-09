# JARVIS - Ultimos mensajes entrantes de WhatsApp
# Uso: .\whatsapp_ultimos.ps1 -N 30
param([int]$N = 30)
$r = Invoke-RestMethod -Uri "http://127.0.0.1:20130/api/ultimos?n=$N" -TimeoutSec 10
foreach ($m in $r.mensajes) {
    $hora = [DateTimeOffset]::FromUnixTimeSeconds($m.timestamp).ToLocalTime().ToString("dd/MM HH:mm")
    $dir = if ($m.de -eq 'yo') { 'YO ->' } else { '->' }
    Write-Host "[$hora] $($m.chatNombre) | $dir $($m.de): $($m.texto)"
}