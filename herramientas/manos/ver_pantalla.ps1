# Ver pantalla de JARVIS: captura la pantalla actual, extrae el texto con el
# OCR de Windows (Windows.Media.Ocr) y detecta la ventana activa.
# Devuelve un JSON con: ventana activa, titulo, proceso y texto reconocido.
# Uso: powershell -ExecutionPolicy Bypass -File ver_pantalla.ps1
# Requiere Windows 10/11 (WinRT OCR). Rapido: ~2-4 segundos.

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

# ---------- Ventana activa ----------
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class VentanaActiva {
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll", CharSet=CharSet.Unicode)]
    public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);
    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
}
"@

$hwnd = [VentanaActiva]::GetForegroundWindow()
$titulo = New-Object System.Text.StringBuilder 512
[VentanaActiva]::GetWindowText($hwnd, $titulo, 512) | Out-Null
$pidVentana = 0
[VentanaActiva]::GetWindowThreadProcessId($hwnd, [ref]$pidVentana) | Out-Null
$proceso = ''
if ($pidVentana -gt 0) {
    try { $proceso = (Get-Process -Id $pidVentana -ErrorAction Stop).ProcessName } catch {}
}

# ---------- Captura de pantalla ----------
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$g.Dispose()
$path = "$env:TEMP\jarvis_pantalla.png"
$bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()

# ---------- OCR con Windows.Media.Ocr ----------
$textoOcr = ''
try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $null = [Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
    $null = [Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
    $null = [Windows.Graphics.Imaging.BitmapDecoder,Windows.Foundation,ContentType=WindowsRuntime]
    $null = [Windows.Storage.Streams.RandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime]

    # Helper: espera una operacion WinRT (IAsyncOperation) devolviendo su Result
    # usando AsTask generico (en PS 5.1 no se resuelve la sobrecarga sola).
    function Esperar([object]$op, [Type]$tipo) {
        $m = [System.WindowsRuntimeSystemExtensions].GetMethods() |
            Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and
                           $_.GetParameters().Count -eq 1 }
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
            $lineas = @()
            foreach ($linea in $result.Lines) { $lineas += $linea.Text }
            $textoOcr = $lineas -join " | "
        }
    } else {
        $textoOcr = 'ERROR: no se pudo crear el motor OCR'
    }
} catch {
    $textoOcr = 'ERROR OCR: ' + $_.Exception.Message
}

# ---------- Salida JSON ----------
$salida = @{
    ventana_activa = $titulo.ToString()
    proceso = $proceso
    resolucion = "$($bounds.Width)x$($bounds.Height)"
    texto = $textoOcr
}
$salida | ConvertTo-Json -Compress
