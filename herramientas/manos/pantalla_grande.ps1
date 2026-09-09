# pantalla_grande.ps1 - Fuerza pantalla completa (F11) del navegador donde corre la serie.
# Creado 20/08/2026 (manos de JARVIS). Activa la ventana de Brave/HBO Max,
# la maximiza y pulsa F11 para dejarla a pantalla completa.
$titulo = if ($args.Count -gt 0) { $args[0] } else { 'Brave' }

$wshell = New-Object -ComObject wscript.shell
Start-Sleep -Milliseconds 200
$ok = $wshell.AppActivate($titulo)
Start-Sleep -Milliseconds 400
# Maximizar por si no lo esta
$wshell.SendKeys('{F11}')
Start-Sleep -Milliseconds 200
$wshell.SendKeys('{F11}')
Start-Sleep -Milliseconds 200
Write-Output ("pantalla completa aplicada | ventana activada=" + $ok)
