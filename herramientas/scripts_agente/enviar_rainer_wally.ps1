$mensaje = "Hola Rainer! Soy Wally, el mayordomo AI del señor Wascar. Estoy en su PC para ayudarle. Un gusto saludarte! 👋"
$encoded = [System.Net.WebUtility]::UrlEncode($mensaje)
$url = "https://wa.me/18097491997?text=$encoded"
Write-Host "Abriendo chat con Rainerf Gamers..."
Start-Process $url
# Alternativa directa a WhatsApp Desktop si esta instalado:
# Start-Process "whatsapp://send?phone=18097491997&text=$encoded"
