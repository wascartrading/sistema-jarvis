Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinAPI2 {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder lpString, int nMaxCount);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
  public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
}
"@

Write-Host "Buscando ventana Brave WhatsApp existente..."
$targetHwnd = 0
[WinAPI2]::EnumWindows({ param($hWnd,$lParam)
  $sb = New-Object System.Text.StringBuilder 512
  [WinAPI2]::GetWindowText($hWnd,$sb,512) | Out-Null
  $t = $sb.ToString()
  if ($t -like "*WhatsApp*") { $script:targetHwnd = $hWnd; Write-Host "Encontrada: $t hWnd=$hWnd" }
  return $true
}, [IntPtr]::Zero) | Out-Null

if ($targetHwnd -eq 0) {
  Write-Host "No se encontro WhatsApp, abriendo en ventana existente Brave..."
  Start-Process "https://web.whatsapp.com/"
  Start-Sleep -Seconds 4
  [WinAPI2]::EnumWindows({ param($hWnd,$lParam)
    $sb = New-Object System.Text.StringBuilder 512
    [WinAPI2]::GetWindowText($hWnd,$sb,512) | Out-Null
    $t = $sb.ToString()
    if ($t -like "*WhatsApp*") { $script:targetHwnd = $hWnd }
    return $true
  }, [IntPtr]::Zero) | Out-Null
}

if ($targetHwnd -ne 0) {
  [WinAPI2]::ShowWindow($targetHwnd, 9) | Out-Null
  [WinAPI2]::SetForegroundWindow($targetHwnd) | Out-Null
  Start-Sleep -Milliseconds 800
  try {
    $wshell = New-Object -ComObject wscript.shell
    $wshell.AppActivate("WhatsApp") | Out-Null
    Start-Sleep -Milliseconds 500
  } catch {}
  Write-Host "Ventana WhatsApp al frente, buscando rainer..."
  Start-Sleep -Milliseconds 700
  # En WhatsApp Web, Ctrl+K enfoca busqueda (fallback Ctrl+F)
  try {
    [System.Windows.Forms.SendKeys]::SendWait("^k")
    Start-Sleep -Milliseconds 800
    # Si no enfoco, intentar clic en buscador con Tab
    [System.Windows.Forms.SendKeys]::SendWait("rainer")
    Start-Sleep -Milliseconds 600
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
    Write-Host "Busqueda 'rainer' enviada"
  } catch { Write-Host "Error SendKeys $_" }
  Start-Sleep -Seconds 1
  # Captura para verificar
  Add-Type -AssemblyName System.Drawing
  $bounds=[System.Windows.Forms.SystemInformation]::VirtualScreen
  $bmp=New-Object System.Drawing.Bitmap $bounds.Width,$bounds.Height
  $g=[System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($bounds.X,$bounds.Y,0,0,$bounds.Size)
  $path="$env:TEMP\whatsapp_rainer_web.png"
  $bmp.Save($path,[System.Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose(); $bmp.Dispose()
  Write-Host "Captura $path"
} else {
  Write-Host "No se pudo encontrar ventana WhatsApp"
}
