Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Buscar ventana de WhatsApp
$whatsapp = Get-Process | Where-Object { $_.MainWindowTitle -like "*WhatsApp*" -or $_.ProcessName -like "*WhatsApp*" } | Select-Object -First 1

if ($whatsapp) {
    # Traer ventana al frente
    $sig = @"
[DllImport("user32.dll")]
public static extern bool SetForegroundWindow(IntPtr hWnd);
[DllImport("user32.dll")]
public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
"@
    $t = Add-Type -MemberDefinition $sig -Name WinAPI -Namespace Activate -PassThru
    $hwnd = $whatsapp.MainWindowHandle
    $t::ShowWindow($hwnd, 9) # SW_RESTORE
    $t::SetForegroundWindow($hwnd)
    Start-Sleep -Milliseconds 500
}

# Capturar pantalla completa
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)

$path = "$env:TEMP\whatsapp_last_message.png"
$bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$bmp.Dispose()

Write-Output $path
