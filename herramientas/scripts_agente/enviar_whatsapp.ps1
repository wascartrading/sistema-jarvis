param(
    [Parameter(Mandatory=$true)][string]$Para,
    [Parameter(Mandatory=$true)][string]$Mensaje
)
# Jarvis - Envio WhatsApp via mudslide
# Uso: .\enviar_whatsapp.ps1 -Para "Rainer" -Mensaje "Hola"
#      .\enviar_whatsapp.ps1 -Para "51999999999" -Mensaje "Hola"
#      .\enviar_whatsapp.ps1 -Para "me" -Mensaje "test"

$contactosPath = Join-Path $PSScriptRoot "whatsapp_contactos.json"
$destino = $Para.Trim()

# Si existe contactos.json, buscar por nombre
if (Test-Path $contactosPath) {
    try {
        $contactos = Get-Content $contactosPath -Raw | ConvertFrom-Json
        # Buscar case-insensitive por nombre
        $encontrado = $null
        foreach ($k in $contactos.PSObject.Properties.Name) {
            if ($k -ieq $destino) { $encontrado = $contactos.$k; break }
        }
        if ($encontrado) {
            $destino = $encontrado
            Write-Host "Contacto '$Para' -> $destino"
        }
    } catch { Write-Host "Aviso: no pude leer contactos.json $_" }
}

# Si es numero puro, mudslide lo acepta tal cual (ej: 51999999999)
# Si ya tiene @s.whatsapp.net o @g.us, dejarlo igual

Write-Host "Enviando a $destino ..."
& mudslide send $destino $Mensaje
if ($LASTEXITCODE -eq 0) {
    Write-Host "OK enviado"
} else {
    Write-Host "Error al enviar (¿logueado? ejecuta whatsapp_login.ps1)"
    exit 1
}
