# ver_pantalla_xy.ps1 - OCR con coordenadas (bounding boxes) de cada palabra en pantalla.
# Devuelve JSON con la ventana activa y una lista de words: {texto, x, y, w, h, cx, cy}
# Uso: powershell -ExecutionPolicy Bypass -File ver_pantalla_xy.ps1
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

# ---------- Ventana activa ----------
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class VA {
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, System.Text.StringBuilder t, int c);
}
"@
$hwnd = [VA]::GetForegroundWindow()
$titulo = New-Object System.Text.StringBuilder 512
[VA]::GetWindowText($hwnd, $titulo, 512) | Out-Null

# ---------- Captura ----------
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$g.Dispose()
$path = "$env:TEMP\jarvis_pantalla_xy.png"
$bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()

# ---------- OCR ----------
$words = @()
try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $null = [Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
    $null = [Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
    $null = [Windows.Graphics.Imaging.BitmapDecoder,Windows.Foundation,ContentType=WindowsRuntime]
    $null = [Windows.Storage.Streams.RandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime]
    function Esperar([object]$op, [Type]$tipo) {
        $m = [System.WindowsRuntimeSystemExtensions].GetMethods() |
            Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 }
        $asTask = $m[0].MakeGenericMethod($tipo)
        $task = $asTask.Invoke($null, @($op))
        return $task.GetAwaiter().GetResult()
    }
    $opFile = [Windows.Storage.StorageFile]::GetFileFromPathAsync($path)
    $file = Esperar $opFile ([Windows.Storage.StorageFile])
    $opStream = $file.OpenAsync([Windows.Storage.FileAccessMode]::Read)
    $stream = Esperar $opStream ([Windows.Storage.Streams.IRandomAccessStream])
    $opDec = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)
    $decoder = Esperar $opDec ([Windows.Graphics.Imaging.BitmapDecoder])
    $opBmp = $decoder.GetSoftwareBitmapAsync()
    $bitmap = Esperar $opBmp ([Windows.Graphics.Imaging.SoftwareBitmap])
    $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
    if ($engine) {
        $opRes = $engine.RecognizeAsync($bitmap)
        $result = Esperar $opRes ([Windows.Media.Ocr.OcrResult])
        if ($result) {
            foreach ($linea in $result.Lines) {
                foreach ($w in $linea.Words) {
                    $r = $w.BoundingRect
                    $words += @{
                        texto = $w.Text
                        x = [int]$r.X; y = [int]$r.Y
                        w = [int]$r.Width; h = [int]$r.Height
                        cx = [int]($r.X + $r.Width/2); cy = [int]($r.Y + $r.Height/2)
                    }
                }
            }
        }
    }
} catch {
    $words += @{ texto = "ERROR OCR: " + $_.Exception.Message; x=0;y=0;w=0;h=0;cx=0;cy=0 }
}
$salida = @{ ventana_activa = $titulo.ToString(); resolucion = "$($bounds.Width)x$($bounds.Height)"; words = $words }
$salida | ConvertTo-Json -Compress -Depth 5
