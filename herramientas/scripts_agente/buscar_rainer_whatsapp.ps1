Add-Type -AssemblyName System.Windows.Forms
Start-Process "whatsapp://"
Start-Sleep -Seconds 3
# Traer WhatsApp al frente
try {
  $wshell = New-Object -ComObject wscript.shell
  $wshell.AppActivate("WhatsApp") | Out-Null
  Start-Sleep -Seconds 1
  # Ctrl+F para buscar (si aplica)
  [System.Windows.Forms.SendKeys]::SendWait("^f")
  Start-Sleep -Milliseconds 700
  [System.Windows.Forms.SendKeys]::SendWait("rainer")
  Start-Sleep -Milliseconds 500
} catch { Write-Host $_ }
Write-Host "WhatsApp abierto y busqueda Rainer enviada"
