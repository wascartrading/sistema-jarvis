# Wally - Protocolo Vision + AutoClick - Presentacion a Rainer via WhatsApp
# Motor: Muse Spark 1.2 - 2 Pasos: 1) Vision (capture) 2) AutoClick (enviar)
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

Write-Host "[Wally] Paso 1 - VISION: tomando capture..."

# --- PASO 1: VISION ---
try {
  $bounds=[System.Windows.Forms.SystemInformation]::VirtualScreen
  $bmp=New-Object System.Drawing.Bitmap $bounds.Width,$bounds.Height
  $g=[System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($bounds.X,$bounds.Y,0,0,$bounds.Size)
  $pathVision="$env:TEMP\vision_wally_presentacion.png"
  $bmp.Save($pathVision,[System.Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose(); $bmp.Dispose()
  Write-Host "[Vision] Capture: $pathVision $($bounds.Width)x$($bounds.Height)"
  # Enviar a Telegram para analisis con Muse Spark 1.2
  $TOKEN="8306558302:AAFNm0IH6Hc-nldoLgYm6PzUZGXSAq0Vz54"
  $CHAT_ID="8456515934"
  curl.exe -s -F "chat_id=$CHAT_ID" -F "photo=@$pathVision" -F "caption=Vision Wally: pantalla antes de enviar a Rainer (1366x768) - Muse Spark analizando..." "https://api.telegram.org/bot$TOKEN/sendPhoto" | Out-Null
  Write-Host "[Vision] Enviado a Telegram para analisis Muse Spark"
} catch {
  Write-Host "[Vision] Aviso: capture con detalle: $_"
  $pathVision="$env:TEMP\capture_wally.png"
}

Start-Sleep -Seconds 1

# --- PASO 2: AUTOCLICK - Presentacion Wally ---
$presentacion = @"
Hola Rainer! 👋 Soy Wally, el mayordomo AI del señor Wáscar.

Vivo en su PC y hablo por Telegram via Kilo + Muse Spark 1.2 (Meta).
Soy el modo EJECUTOR: convierto órdenes en hechos.

Qué hago:
• Abro apps, webs, música, archivos
• Creo scripts al instante y los ejecuto
• Automatizo con visión + autoclick (veo la pantalla y hago clic)
• Creo proyectos: webs, apps, juegos desde cero

Puedo controlar la PC completa con visión y clics automáticos.
Un gusto presentarme, Rainer! Quedo a tu orden. 🤖
- Wally, mayordomo del jefe Wáscar
"@

Write-Host "[Wally] Paso 2 - AUTOCLICK: preparando WhatsApp para Rainer..."
$encoded = [System.Net.WebUtility]::UrlEncode($presentacion)
$phone = "18097491997"
$url = "https://wa.me/$phone`?text=$encoded"
Write-Host "[AutoClick] URL: wa.me/$phone"

# Abrir WhatsApp Web
Start-Process $url
Write-Host "[AutoClick] Navegador abierto, esperando carga (10s)..."
Start-Sleep -Seconds 10

# Intentar autoclick - Enviar Enter para pulsar boton Enviar
try {
  Add-Type -AssemblyName System.Windows.Forms
  $wshell = New-Object -ComObject wscript.shell
  # Traer ventana al frente
  $wshell.AppActivate("WhatsApp") | Out-Null
  Start-Sleep -Milliseconds 700
  $wshell.AppActivate("Brave") | Out-Null
  Start-Sleep -Milliseconds 500
  $wshell.AppActivate("Chrome") | Out-Null
  Start-Sleep -Milliseconds 500
  
  Write-Host "[AutoClick] Enviando ENTER para enviar mensaje..."
  [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
  Start-Sleep -Milliseconds 900
  Write-Host "[AutoClick] Mensaje enviado? Verificando..."
  
  # Captura de verificacion post-envio
  try {
    $bounds2=[System.Windows.Forms.SystemInformation]::VirtualScreen
    $bmp2=New-Object System.Drawing.Bitmap $bounds2.Width,$bounds2.Height
    $g2=[System.Drawing.Graphics]::FromImage($bmp2)
    $g2.CopyFromScreen($bounds2.X,$bounds2.Y,0,0,$bounds2.Size)
    $path2="$env:TEMP\vision_wally_post_envio.png"
    $bmp2.Save($path2,[System.Drawing.Imaging.ImageFormat]::Png)
    $g2.Dispose(); $bmp2.Dispose()
    curl.exe -s -F "chat_id=$CHAT_ID" -F "photo=@$path2" -F "caption=Vision post-envio a Rainer - verifica WhatsApp" "https://api.telegram.org/bot$TOKEN/sendPhoto" | Out-Null
    Write-Host "[Vision] Post-envio capture enviado a Telegram"
  } catch { Write-Host "Post capture aviso: $_" }
  
  Write-Host "✅ Presentacion enviada a Rainer via WhatsApp"
  Write-Host "Script: wally_vision_rainer_presentacion.ps1"
} catch {
  Write-Host "❌ Error autoclick: $_"
  Write-Host "Plan B: URL abierta manualmente en wa.me/$phone - pulsa ENVIAR"
}
