$browsers = @("chrome", "brave", "msedge", "firefox")
$youtubeWindows = @()

foreach ($browser in $browsers) {
    $processes = Get-Process -Name $browser -ErrorAction SilentlyContinue
    foreach ($proc in $processes) {
        if ($proc.MainWindowTitle -match "youtube" -or $proc.MainWindowTitle -match "YouTube") {
            $youtubeWindows += $proc
        }
    }
}

if ($youtubeWindows.Count -eq 0) {
    Write-Host "No se encontraron ventanas de YouTube abiertas."
    exit 0
}

Write-Host "Encontradas $($youtubeWindows.Count) ventana(s) de YouTube. Cerrando..."

foreach ($proc in $youtubeWindows) {
    $title = $proc.MainWindowTitle
    $hwnd = $proc.MainWindowHandle
    
    # Traer al frente
    $wshell = New-Object -ComObject WScript.Shell
    $wshell.AppActivate($title)
    Start-Sleep -Milliseconds 300
    
    # Cerrar con Alt+F4
    $wshell.SendKeys("%{F4}")
    Start-Sleep -Milliseconds 500
    
    Write-Host "Cerrada: $title"
}

Start-Sleep -Seconds 1
Write-Host "Listo, jefe. Ventanas de YouTube cerradas."
