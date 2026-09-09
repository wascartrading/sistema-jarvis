$w = (Get-CimInstance Win32_OperatingSystem).DesktopWidth
$h = (Get-CimInstance Win32_OperatingSystem).DesktopHeight
$s = $w * $h
$bmp = New-Object System.Drawing.Bitmap($w, $h)
[System.Runtime.InteropServices.Marshal]::CopyHwndTo($bmp, [System.Windows.Forms.Screen]::FromMouse().Handle, $s)
$path = Join-Path $PSScriptRoot ("screenshot_" + (Get-Date -Format 'yyyyMMdd_HHmmss') + ".png")
$bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Host "Captura guardada en: $path"