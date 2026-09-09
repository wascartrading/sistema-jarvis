# Enviar presentacion Wally a chat personal (Wascar)
$TOKEN="8306558302:AAFNm0IH6Hc-nldoLgYm6PzUZGXSAq0Vz54"
$CHAT_ID="8456515934"
$Text="Hola señor Wáscar! 👋`nSoy Wally, tu mayordomo EJECUTOR.`nVivo en tu PC, conectado a Telegram via Kilo + Muse Spark.`nPuedo abrir apps, webs, crear scripts, automatizar y crear proyectos.`nA tus órdenes, jefe! ¿Qué hacemos hoy?"
curl.exe -s -X POST "https://api.telegram.org/bot$TOKEN/sendMessage" --data-urlencode "chat_id=$CHAT_ID" --data-urlencode "text=$Text" | Out-Null
Write-Output "Presentacion enviada a $CHAT_ID"
