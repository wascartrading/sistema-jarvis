# Abre DeepSeek Harness: arranca el servidor web oculto si no esta corriendo y abre el navegador.
$port = 3080
# 04/09/2026 (KIT PORTATIL): el vbs vive junto a este script.
$vbs = Join-Path $PSScriptRoot 'dsh_servidor_oculto.vbs'

$listening = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if (-not $listening) {
    Start-Process -FilePath "wscript.exe" -ArgumentList "`"$vbs`"" -WindowStyle Hidden
    # Esperar hasta 30 segundos a que el servidor responda
    $ok = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        try {
            $r = Invoke-WebRequest -Uri "http://127.0.0.1:$port" -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -eq 200) { $ok = $true; break }
        } catch { }
    }
    if (-not $ok) { Write-Output "El servidor no respondio a tiempo. Revisa el log en %USERPROFILE%\.dsh\dsh_web.log" }
}
Start-Process "http://127.0.0.1:$port"