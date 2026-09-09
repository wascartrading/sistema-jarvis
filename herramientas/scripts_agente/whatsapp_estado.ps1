# JARVIS - Estado del puente WhatsApp
$r = Invoke-RestMethod -Uri "http://127.0.0.1:20130/api/estado" -TimeoutSec 5
$r | ConvertTo-Json -Depth 4