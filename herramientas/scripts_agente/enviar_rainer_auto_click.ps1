Add-Type -AssemblyName System.Windows.Forms
$mensaje = "Hola Rainer! Soy Wally, el mayordomo AI del señor Wascar. Estoy en su PC para ayudarle. Un gusto saludarte! 👋"
$encoded = [System.Net.WebUtility]::UrlEncode($mensaje)
$url = "https://wa.me/18097491997?text=$encoded"
Write-Host "Abriendo WhatsApp Web con mensaje..."
Start-Process $url
Write-Host "Esperando que cargue WhatsApp Web (10s)..."
Start-Sleep -Seconds 10
try {
  $wshell = New-Object -ComObject wscript.shell
  # Intentar activar ventana de Brave/Chrome con WhatsApp
  $wshell.AppActivate("WhatsApp") | Out-Null
  Start-Sleep -Milliseconds 500
  $wshell.AppActivate("Brave") | Out-Null
  Start-Sleep -Milliseconds 500
  $wshell.AppActivate("Chrome") | Out-Null
  Start-Sleep -Milliseconds 500
  Write-Host "Enviando Enter para click en Enviar..."
  [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
  Start-Sleep -Milliseconds 800
  Write-Host "Enter enviado - mensaje deberia estar enviado."
} catch { Write-Host "Error auto-click: $_" }
