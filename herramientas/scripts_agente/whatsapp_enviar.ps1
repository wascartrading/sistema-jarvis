# JARVIS - Enviar mensaje de WhatsApp
# Uso: .\whatsapp_enviar.ps1 -Para "Rainer" -Mensaje "Hola que tal"
#      .\whatsapp_enviar.ps1 -Para "51999999999" -Mensaje "Hola"
param(
    [Parameter(Mandatory=$true)][string]$Para,
    [Parameter(Mandatory=$true)][string]$Mensaje
)
$body = @{ destino = $Para; mensaje = $Mensaje } | ConvertTo-Json
$r = Invoke-RestMethod -Uri "http://127.0.0.1:20130/api/enviar" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 20
if ($r.ok) {
    Write-Host "OK enviado a $($r.chatId): $($r.mensaje)"
} else {
    Write-Host "ERROR: $($r.error)"
    exit 1
}