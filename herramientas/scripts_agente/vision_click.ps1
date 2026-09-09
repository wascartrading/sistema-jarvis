# Wally Vision Click - PowerShell nativo sin dependencias
# Uso: .\vision_click.ps1 -X 680 -Y 450
#      .\vision_click.ps1 -Capture
param(
    [int]$X = -1,
    [int]$Y = -1,
    [switch]$Capture
)
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# C# para click
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class MouseClick {
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int X,int Y);
  [DllImport("user32.dll")] public static extern void mouse_event(int dwFlags,int dx,int dy,int cButtons,int dwExtraInfo);
  public const int MOUSEEVENTF_LEFTDOWN=0x02;
  public const int MOUSEEVENTF_LEFTUP=0x04;
  public static void Click(int x,int y){
    SetCursorPos(x,y);
    System.Threading.Thread.Sleep(200);
    mouse_event(MOUSEEVENTF_LEFTDOWN,0,0,0,0);
    System.Threading.Thread.Sleep(80);
    mouse_event(MOUSEEVENTF_LEFTUP,0,0,0,0);
  }
}
"@

if($Capture){
    $bounds=[System.Windows.Forms.SystemInformation]::VirtualScreen
    $bmp=New-Object System.Drawing.Bitmap $bounds.Width,$bounds.Height
    $g=[System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($bounds.X,$bounds.Y,0,0,$bounds.Size)
    $path="$env:TEMP\vision_capture.png"
    $bmp.Save($path,[System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $bmp.Dispose()
    Write-Output "Capture: $path $($bounds.Width)x$($bounds.Height)"
    # Enviar por Telegram
    $TOKEN="8306558302:AAFNm0IH6Hc-nldoLgYm6PzUZGXSAq0Vz54"
    $CHAT_ID="8456515934"
    curl.exe -s -F "chat_id=$CHAT_ID" -F "photo=@$path" "https://api.telegram.org/bot$TOKEN/sendPhoto" | Out-String | Write-Output
    exit
}
if($X -ge 0 -and $Y -ge 0){
    Write-Output "Wally click en $X,$Y ..."
    [MouseClick]::Click($X,$Y)
    Write-Output "Click hecho jefe"
} else {
    Write-Output "Uso: .\vision_click.ps1 -X 680 -Y 450"
    Write-Output "     .\vision_click.ps1 -Capture  (toma y envia capture)"
}
