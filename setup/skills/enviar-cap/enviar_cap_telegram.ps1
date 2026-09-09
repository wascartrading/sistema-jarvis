# ============================================================================
#  enviar_cap_telegram.ps1 — Habilidad de JARVIS: cap de pantalla -> Telegram
# ----------------------------------------------------------------------------
#  Toma una captura de la pantalla (o de una ventana concreta) y la envia
#  INMEDIATAMENTE al chat de Telegram del jefe. Incluye deteccion de pantalla
#  en reposo/bloqueada para NUNCA mandar un cap en negro.
#
#  Uso:
#    powershell -NoProfile -ExecutionPolicy Bypass -File enviar_cap_telegram.ps1
#    powershell ... -File enviar_cap_telegram.ps1 -Ventana "IQ Option"
#    powershell ... -File enviar_cap_telegram.ps1 -ForzarGlobal
#
#  Parametros:
#    -Ventana      Filtra la ventana por parte del titulo (ej: "IQ Option").
#                  Si se omite, captura la ventana activa (o la global).
#    -ForzarGlobal Fuerza la captura global (todo el escritorio).
#    -SinLimpiar   No borra el PNG temporal al terminar.
#
#  Estrategia anti-negro:
#    1) Despierta la pantalla (SetThreadExecutionState + nudge de mouse).
#    2) Intenta captura GLOBAL (CopyFromScreen).
#    3) Si falla o sale plana, intenta PrintWindow de la ventana objetivo
#       (funciona aunque la pantalla fisica este en reposo).
#    4) Si todo falla, NO envia nada y devuelve motivo claro.
# ============================================================================

param(
    [string]$Ventana = "",
    [switch]$ForzarGlobal,
    [switch]$SinLimpiar
)

$ErrorActionPreference = 'Stop'

# ---------- Credenciales del bot (mismas que jarvis_telegram_bot.py) ----------
$TOKEN = "8306558302:AAFNm0IH6Hc-nldoLgYm6PzUZGXSAq0Vz54"
$CHAT_ID = "8456515934"

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
public class ECap {
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode)] public static extern uint SetThreadExecutionState(uint esFlags);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
    [DllImport("user32.dll")] public static extern bool GetCursorPos(out POINT p);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hwnd, IntPtr hdc, uint flags);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hwnd, out RECT r);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr h, StringBuilder t, int c);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint p);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr lParam);
    [DllImport("user32.dll")] public static extern int GetWindowLong(IntPtr h, int i);
    public delegate bool EnumProc(IntPtr hWnd, IntPtr lParam);
    public struct POINT { public int X; public int Y; }
    public struct RECT { public int Left; public int Top; public int Right; public int Bottom; }
}
"@

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$tmp = Join-Path $env:TEMP ("cap_telegram_" + $stamp + ".png")
$PW_RENDERFULLCONTENT = 0x00000002

function Test-ImagenUtil($bmp) {
    # Muestreo de colores: si la imagen es practicamente un solo color -> no sirve
    $colors = @{}
    $sx = [Math]::Max(1, [int]($bmp.Width / 40))
    $sy = [Math]::Max(1, [int]($bmp.Height / 40))
    for ($y = 0; $y -lt $bmp.Height; $y += $sy) {
        for ($x = 0; $x -lt $bmp.Width; $x += $sx) {
            $c = $bmp.GetPixel($x, $y)
            $k = "$($c.R),$($c.G),$($c.B)"
            if ($colors.ContainsKey($k)) { $colors[$k]++ } else { $colors[$k] = 1 }
        }
    }
    return [pscustomobject]@{ Utiles = ($colors.Count -gt 1); Colores = $colors.Count }
}

function Tomar-Global {
    $b = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $bmp = New-Object System.Drawing.Bitmap($b.Width, $b.Height)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
    $g.Dispose()
    return $bmp
}

function Tomar-Ventana($hwnd) {
    $r = New-Object ECap+RECT
    [ECap]::GetWindowRect($hwnd, [ref]$r) | Out-Null
    $w = $r.Right - $r.Left; $h = $r.Bottom - $r.Top
    if ($w -le 0 -or $h -le 0) { throw "ventana sin tamano" }
    $bmp = New-Object System.Drawing.Bitmap($w, $h)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $hdc = $g.GetHdc()
    $ok = [ECap]::PrintWindow($hwnd, $hdc, $PW_RENDERFULLCONTENT)
    $g.ReleaseHdc($hdc)
    $g.Dispose()
    if (-not $ok) { throw "PrintWindow fallo" }
    return $bmp
}

function Buscar-Ventana($texto) {
    $match = $null
    $cb = {
        param($hwnd, $lparam)
        $t = New-Object System.Text.StringBuilder 512
        [ECap]::GetWindowText($hwnd, $t, 512) | Out-Null
        if ($t.Length -gt 0 -and $t.ToString() -like "*$texto*") {
            $script:match = $hwnd
            return $false
        }
        return $true
    }
    [ECap]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null
    return $script:match
}

function Lista-Candidatas {
    # Ventanas visibles con titulo, ordenadas por area desc, sin overlays del sistema.
    # El escritorio (Program Manager) se deja de ultimo recurso para no capturar el fondo vacio
    # cuando hay apps reales abiertas.
    $script:excluir = @("Experiencia de entrada de Windows", "MSCTFIME UI", "Default IME", "NvContainer")
    $script:lista = New-Object System.Collections.ArrayList
    $cb = {
        param($hwnd, $lparam)
        if ([ECap]::GetWindowLong($hwnd, -16) -band 0x10000000) {  # WS_VISIBLE
            $t = New-Object System.Text.StringBuilder 512
            [ECap]::GetWindowText($hwnd, $t, 512) | Out-Null
            $nom = $t.ToString()
            if ($nom.Length -gt 0) {
                $skip = $false
                foreach ($e in $script:excluir) { if ($nom -like "*$e*") { $skip = $true; break } }
                if (-not $skip) {
                    $r = New-Object ECap+RECT
                    [ECap]::GetWindowRect($hwnd, [ref]$r) | Out-Null
                    $area = ($r.Right - $r.Left) * ($r.Bottom - $r.Top)
                    [void]$script:lista.Add([pscustomobject]@{ hwnd = $hwnd; titulo = $nom; area = $area })
                }
            }
        }
        return $true
    }
    [ECap]::EnumWindows($cb, [IntPtr]::Zero) | Out-Null
    $apps = @($script:lista | Where-Object { $_.titulo -notlike "*Program Manager*" } | Sort-Object area -Descending)
    if ($apps.Count -eq 0) {
        $apps = @($script:lista | Sort-Object area -Descending)
    }
    return $apps
}

# ---------- 1) Despertar la pantalla ----------
$flags = [uint32]2147483651  # ES_CONTINUOUS | ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED
[ECap]::SetThreadExecutionState($flags) | Out-Null
$p = New-Object ECap+POINT
[ECap]::GetCursorPos([ref]$p) | Out-Null
[ECap]::SetCursorPos([Math]::Min($p.X + 2, 1920), $p.Y) | Out-Null
Start-Sleep -Milliseconds 80
[ECap]::SetCursorPos($p.X, $p.Y) | Out-Null
Start-Sleep -Milliseconds 250

# ---------- 2) Determinar ventana objetivo ----------
$hwnd = [IntPtr]::Zero
$titulo = ""
if ($Ventana -ne "") {
    $hwnd = Buscar-Ventana $Ventana
    if ($hwnd -eq $null) {
        Write-Output '{"ok":false,"motivo":"ventana_no_encontrada","detalle":"No se encontro ventana con ese titulo"}'
        exit 1
    }
    $tb = New-Object System.Text.StringBuilder 512
    [ECap]::GetWindowText($hwnd, $tb, 512) | Out-Null
    $titulo = $tb.ToString()
} else {
    $hwnd = [ECap]::GetForegroundWindow()
    $tb = New-Object System.Text.StringBuilder 512
    [ECap]::GetWindowText($hwnd, $tb, 512) | Out-Null
    $titulo = $tb.ToString()
}

# ---------- 3) Capturar ----------
$bmp = $null
$metodo = ""

function Intentar-Ventana($hwnd) {
    try {
        $bmpT = Tomar-Ventana $hwnd
        $check = Test-ImagenUtil $bmpT
        if ($check.Utiles) {
            $tb = New-Object System.Text.StringBuilder 512
            [ECap]::GetWindowText($hwnd, $tb, 512) | Out-Null
            return [pscustomobject]@{ Bmp = $bmpT; Titulo = $tb.ToString() }
        }
        $bmpT.Dispose()
    } catch { try { if ($bmpT) { $bmpT.Dispose() } } catch {} }
    return $null
}

try {
    if (-not $ForzarGlobal -and $Ventana -eq "") {
        # Flujo normal: global primero, ventanas como respaldo
        try {
            $bmp = Tomar-Global
            $check = Test-ImagenUtil $bmp
            if ($check.Utiles) { $metodo = "global" }
            else { $bmp.Dispose(); $bmp = $null }
        } catch { try { if ($bmp) { $bmp.Dispose() } } catch {}; $bmp = $null }

        if (-not $bmp) {
            $candidatos = New-Object System.Collections.ArrayList
            if ($hwnd -ne [IntPtr]::Zero) { [void]$candidatos.Add([pscustomobject]@{ hwnd = $hwnd; titulo = $titulo; area = 0 }) }
            foreach ($c in (Lista-Candidatas)) { [void]$candidatos.Add($c) }
            foreach ($c in ($candidatos | Select-Object -Unique -Property hwnd)) {
                $res = Intentar-Ventana $c.hwnd
                if ($res) {
                    $bmp = $res.Bmp; $metodo = "ventana"; $titulo = $res.Titulo
                    break
                }
            }
        }
    } elseif ($ForzarGlobal) {
        $bmp = Tomar-Global
        $check = Test-ImagenUtil $bmp
        if ($check.Utiles) { $metodo = "global" }
        else { $bmp.Dispose(); $bmp = $null }
    } else {
        $res = Intentar-Ventana $hwnd
        if ($res) { $bmp = $res.Bmp; $metodo = "ventana"; $titulo = $res.Titulo }
    }
} catch {
    try { if ($bmp) { $bmp.Dispose() } } catch {}
    $bmp = $null
}

if (-not $bmp) {
    Write-Output '{"ok":false,"motivo":"pantalla_no_capturable","detalle":"El escritorio no es capturable ahora (monitor en reposo o sin superficie visible) y la ventana tampoco respondio a PrintWindow. Pide al jefe tocar una tecla o mover el mouse y reintenta."}'
    exit 2
}

$bmp.Save($tmp, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
$bytes = (Get-Item $tmp).Length

# ---------- 4) Enviar por Telegram ----------
$caption = "Cap JARVIS [$stamp] metodo=$metodo"
if ($titulo -ne "") { $caption += " | ventana: $titulo" }
$resp = curl.exe -s -F "chat_id=$CHAT_ID" -F "photo=@$tmp" -F "caption=$caption" "https://api.telegram.org/bot$TOKEN/sendPhoto" 2>&1 | Out-String
$json = $null
try { $json = $resp | ConvertFrom-Json } catch {}

if ($json -and $json.ok -eq $true) {
    Write-Output ("{{""ok"":true,""metodo"":""{0}"",""bytes"":{1},""ventana"":""{2}""}}" -f $metodo, $bytes, ($titulo -replace '"','\"'))
} else {
    $det = ($resp -replace '"', '\"') 
    if ($det.Length -gt 300) { $det = $det.Substring(0, 300) }
    Write-Output ("{{""ok"":false,""motivo"":""telegram_fallo"",""detalle"":""{0}""}}" -f $det)
    exit 3
}

# ---------- 5) Limpieza ----------
if (-not $SinLimpiar) {
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
}