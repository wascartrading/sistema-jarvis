Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinAPI {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder lpString, int nMaxCount);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
  public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
}
"@

$TOKEN="8306558302:AAFNm0IH6Hc-nldoLgYm6PzUZGXSAq0Vz54"
$CHAT_ID="8456515934"

function CaptureAndSend($caption) {
  $bounds=[System.Windows.Forms.SystemInformation]::VirtualScreen
  $bmp=New-Object System.Drawing.Bitmap $bounds.Width,$bounds.Height
  $g=[System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($bounds.X,$bounds.Y,0,0,$bounds.Size)
  $path="$env:TEMP\capture_rainer_$(Get-Date -Format 'HHmmss').png"
  $bmp.Save($path,[System.Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose(); $bmp.Dispose()
  Write-Host "Capture $path caption=$caption"
  curl.exe -s -F "chat_id=$CHAT_ID" -F "photo=@$path" -F "caption=$caption" "https://api.telegram.org/bot$TOKEN/sendPhoto" | Write-Host
  return $path
}

Write-Host "=== VERIFICACION PESTANAS ==="
# Buscar ventana Brave con título Compartir en Whatsapp
$braveHwnd = 0
[WinAPI]::EnumWindows({ param($hWnd,$lParam)
  $sb = New-Object System.Text.StringBuilder 512
  [WinAPI]::GetWindowText($hWnd,$sb,512) | Out-Null
  $t = $sb.ToString()
  if ($t -like "*Compartir en Whatsapp*") { $script:braveHwnd = $hWnd; Write-Host "Encontrada Whatsapp hWnd=$hWnd title=$t" }
  return $true
}, [IntPtr]::Zero) | Out-Null

# fallback: buscar cualquier Brave visible
if ($braveHwnd -eq 0) {
  [WinAPI]::EnumWindows({ param($hWnd,$lParam)
    $sb = New-Object System.Text.StringBuilder 512
    [WinAPI]::GetWindowText($hWnd,$sb,512) | Out-Null
    $t = $sb.ToString()
    if ($t -like "*Brave*") { $script:braveHwnd = $hWnd }
    return $true
  }, [IntPtr]::Zero) | Out-Null
}
Write-Host "hWnd final=$braveHwnd"

if ($braveHwnd -ne 0) {
  [WinAPI]::ShowWindow($braveHwnd, 9) | Out-Null
  [WinAPI]::SetForegroundWindow($braveHwnd) | Out-Null
  Start-Sleep -Seconds 1
}

# CAPTURE 1: estado actual - verificación pestañas con Whatsapp
CaptureAndSend "Verificacion pestanas jefe - Pestaña Whatsapp activa (Compartir en Whatsapp - Brave) - antes de buscar Rainer"

Start-Sleep -Seconds 1

# Ahora buscar Rainer Gamers en el buscador
# Usar Ctrl+L para ir a barra direcciones, escribir busqueda
try {
  $wshell = New-Object -ComObject wscript.shell
  if ($braveHwnd -ne 0) { $wshell.AppActivate("Brave") | Out-Null }
  Start-Sleep -Milliseconds 700
  # Ctrl+L
  [System.Windows.Forms.SendKeys]::SendWait("^l")
  Start-Sleep -Milliseconds 600
  [System.Windows.Forms.SendKeys]::SendWait("Rainer Gamers")
  Start-Sleep -Milliseconds 500
  [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
  Write-Host "Busqueda Rainer Gamers enviada via Ctrl+L"
} catch { Write-Host "Error SendKeys: $_" }

Start-Sleep -Seconds 4

# O tambien abrir directo por si falla el SendKeys
Start-Process 'https://www.google.com/search?q=Rainer+Gamers'
Start-Sleep -Seconds 3
# Traer Brave al frente otra vez
if ($braveHwnd -ne 0) { [WinAPI]::SetForegroundWindow($braveHwnd) | Out-Null }

Start-Sleep -Seconds 2
CaptureAndSend "Rainer Gamers abierto jefe - busqueda completada"

Write-Host "Listo verificacion completa"
