# ocr_preciso.ps1 - OCR de WINDOWS con MEJORA de PRECISION y COORDENADAS exactas.
# Mejoras sobre ver_pantalla_xy.ps1:
#  1) UPSAMPLE de la captura (escalado 2x/3x) antes del OCR: Windows Media OCR lee
#     mucho mejor texto pequeno cuando se amplia (lee digitos tipo E13/E12/E14).
#  2) RECORTE de una sola region (opcional) para concentrar el OCR y evitar ruido.
#  3) MODO DIGITOS: binariza y aumenta contraste para numeros pequenos.
#  4) Devuelve JSON con palabras {texto, x, y, w, h, cx, cy} ya escaladas a las
#     coordenadas ORIGINALES de pantalla.
#
# Uso:
#   # Pantalla completa con upscale 2x y contraste:
#   powershell -ExecutionPolicy Bypass -File ocr_preciso.ps1 -Escala 2 -Contraste 1.4 -Mode normal
#   # Solo una region (ej. x=100,y=200,ancho=400,alto=150), ampliada 3x y modo digitos:
#   powershell -ExecutionPolicy Bypass -File ocr_preciso.ps1 -RegX 100 -RegY 200 -RegW 400 -RegH 150 -Escala 3 -Mode digitos
#
# Requiere Windows 10/11 (Windows.Media.Ocr). Los parametros son opcionales.

param(
    [double]$Escala = 2,        # factor de ampliacion de la imagen antes del OCR (1,2,3...)
    [float]$Contraste = 1.35,   # multiplicador de contraste (>1 sube contraste)
    [ValidateSet('normal','digitos','grayscale')]
    [string]$Mode = 'normal',
    [int]$RegX = -1, [int]$RegY = -1, [int]$RegW = -1, [int]$RegH = -1  # region opcional
)

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

# ---------- Ventana activa ----------
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class VA2 {
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, System.Text.StringBuilder t, int c);
}
"@
$hwnd = [VA2]::GetForegroundWindow()
$titulo = New-Object System.Text.StringBuilder 512
[VA2]::GetWindowText($hwnd, $titulo, 512) | Out-Null

# ---------- Captura de pantalla (completa o region) ----------
$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmpFull = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
$g = [System.Drawing.Graphics]::FromImage($bmpFull)
$g.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
$g.Dispose()

# Si se pide region, recortar
if ($RegX -ge 0 -and $RegW -gt 0) {
    $srcRect = New-Object System.Drawing.Rectangle($RegX, $RegY, $RegW, $RegH)
    $bmpRegion = $bmpFull.Clone($srcRect, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $bmpFull.Dispose()
    $origenX = $RegX; $origenY = $RegY   # desplazamiento de la region en pantalla
} else {
    $bmpRegion = $bmpFull
    $origenX = 0; $origenY = 0
}

# ---------- Preprocesamiento: convertir a grises, contraste, binarizar ----------
function Preprocesar([System.Drawing.Bitmap]$src, [float]$ctr, [string]$mode) {
    # 1) Convertir a 8-bpp en escala de grises
    $gris = New-Object System.Drawing.Bitmap($src.Width, $src.Height, [System.Drawing.Imaging.PixelFormat]::Format8bppIndexed)
    $pal = $gris.Palette
    for ($i = 0; $i -lt 256; $i++) { $pal.Entries[$i] = [System.Drawing.Color]::FromArgb(255,$i,$i,$i) }
    $gris.Palette = $pal
    $gr = [System.Drawing.Graphics]::FromImage($gris)
    $cm = New-Object System.Drawing.Imaging.ColorMatrix
    # Matriz para luminancia (pondera RGB a gris)
    $cm.Matrix00 = 0.299; $cm.Matrix01 = 0.299; $cm.Matrix02 = 0.299
    $cm.Matrix10 = 0.587; $cm.Matrix11 = 0.587; $cm.Matrix12 = 0.587
    $cm.Matrix20 = 0.114; $cm.Matrix21 = 0.114; $cm.Matrix22 = 0.114
    $ia = New-Object System.Drawing.Imaging.ImageAttributes
    $ia.SetColorMatrix($cm)
    $gr.DrawImage($src, (New-Object System.Drawing.Rectangle(0,0,$src.Width,$src.Height)), 0,0,$src.Width,$src.Height, [System.Drawing.GraphicsUnit]::Pixel, $ia)
    $gr.Dispose()

    # 2) Contraste (solo en modo normal/grayscale; en digitos lo dejamos para binarizar)
    $resultado = $gris
    if ($ctr -gt 1.0) {
        $resultado = New-Object System.Drawing.Bitmap($gris.Width, $gris.Height)
        for ($x = 0; $x -lt $gris.Width; $x++) {
            for ($y = 0; $y -lt $gris.Height; $y++) {
                $p = $gris.GetPixel($x,$y).R
                $n = [int](128 + ($p - 128) * $ctr)
                if ($n -lt 0) { $n = 0 }; if ($n -gt 255) { $n = 255 }
                $resultado.SetPixel($x,$y,[System.Drawing.Color]::FromArgb($n,$n,$n))
            }
        }
    }
    return $resultado
}

$bmpProc = Preprocesar $bmpRegion $Contraste $Mode
$bmpRegion.Dispose()

# ---------- Upscale (ampliar) antes del OCR ----------
$nuevoW = [int]($bmpProc.Width * $Escala)
$nuevoH = [int]($bmpProc.Height * $Escala)
$bmpEscalado = New-Object System.Drawing.Bitmap($nuevoW, $nuevoH)
$ge = [System.Drawing.Graphics]::FromImage($bmpEscalado)
$ge.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
$ge.DrawImage($bmpProc, 0, 0, $nuevoW, $nuevoH)
$ge.Dispose()
$bmpProc.Dispose()

$path = "$env:TEMP\jarvis_ocr_preciso.png"
$bmpEscalado.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
$bmpEscalado.Dispose()

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
                    # Convertir coordenadas ESCALADAS de vuelta a pantalla original
                    $ox = [int](($r.X / $Escala) + $origenX)
                    $oy = [int](($r.Y / $Escala) + $origenY)
                    $ow = [int]($r.Width / $Escala)
                    $oh = [int]($r.Height / $Escala)
                    $words += @{
                        texto = $w.Text
                        x = $ox; y = $oy; w = $ow; h = $oh
                        cx = [int]($ox + $ow/2); cy = [int]($oy + $oh/2)
                    }
                }
            }
        }
    }
} catch {
    $words += @{ texto = "ERROR OCR: " + $_.Exception.Message; x=0;y=0;w=0;h=0;cx=0;cy=0 }
}
$salida = @{
    ventana_activa = $titulo.ToString()
    resolucion = "$($bounds.Width)x$($bounds.Height)"
    escala_usr = $Escala
    modo = $Mode
    region = $(if ($RegX -ge 0) { "x=$RegX y=$RegY w=$RegW h=$RegH" } else { "completa" })
    words = $words
}
$salida | ConvertTo-Json -Compress -Depth 5
