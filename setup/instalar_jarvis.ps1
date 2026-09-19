<#
============================================================
 instalar_jarvis.ps1 - Instalador del KIT PORTATIL de JARVIS
============================================================
Creado por JARVIS 01/09/2026.
Su trabajo, en una PC NUEVA (o en esta misma):
  1) Verifica/instala Python y Node.js
  2) Instala dependencias de Python (pip) del bot
  3) Instala opencode y omniroute (npm global)
  4) Despliega cerebro, skills y config de opencode en ~/.config/opencode
  5) Crea la tarea JARVIS_ELEVADO (poder de ADMINISTRADOR)
  6) Re-escribe las rutas absolutas de la maquina anterior -> rutas del kit
  7) Prepara OmniRoute portable (DATA_DIR -> kit/omniroute/data) y lo arranca
  8) Lanza el bot de Telegram de JARVIS
Solo necesita INTERNET la primera vez (para instalar dependencias).
#>

param(
    [string]$KitDir = ""
)

$ErrorActionPreference = 'Continue'
$Host.UI.RawUI.WindowTitle = "JARVIS Portatil - Instalacion"

if ([string]::IsNullOrWhiteSpace($KitDir)) { $KitDir = (Get-Location).Path }
# Quitar barra final si existe
$KitDir = $KitDir.TrimEnd('\')

Write-Host ""
Write-Host "=== JARVIS PORTATIL - INSTALADOR ===" -ForegroundColor Cyan
Write-Host "Kit en: $KitDir" -ForegroundColor Gray
Write-Host ""

$python = $null
$node = $null

# ---------- PASO 1: Python ----------
Write-Host "[1/7] Buscando Python..." -ForegroundColor Yellow
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
# Ruta comun de instalacion local de la PC original
$pyLocal = "C:\Users\$env:USERNAME\AppData\Local\Programs\Python"
if (-not $py -and (Test-Path $pyLocal)) {
    $found = Get-ChildItem "$pyLocal" -Directory -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending | Select-Object -First 1
    if ($found) { $python = Join-Path $found.FullName 'python.exe' }
}
if ($py -and -not $python) { $python = (Get-Command python).Source }
if ($python -and (Test-Path $python)) {
    Write-Host "   Python encontrado: $python" -ForegroundColor Green
} else {
    Write-Host "   Python NO encontrado. Descargando instalador..." -ForegroundColor Yellow
    $inst = Join-Path $env:TEMP 'python-setup.exe'
    try {
        Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe" -OutFile $inst -UseBasicParsing
        Write-Host "   Instalando Python 3.12 (silencioso)..."
        Start-Process -Wait -FilePath $inst -ArgumentList '/quiet','InstallAllUsers=0','PrependPath=1','Include_pip=1'
        $python = "C:\Users\$env:USERNAME\AppData\Local\Programs\Python\Python312\python.exe"
        if (-not (Test-Path $python)) {
            # buscar de nuevo
            $new = Get-ChildItem "C:\Users\$env:USERNAME\AppData\Local\Programs\Python" -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending | Select-Object -First 1
            if ($new) { $python = Join-Path $new.FullName 'python.exe' }
        }
    } catch {
        Write-Host "   ERROR instalando Python: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

# ---------- PASO 2: Node.js ----------
Write-Host "[2/7] Buscando Node.js..." -ForegroundColor Yellow
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    Write-Host "   Node no encontrado. Detectando winget..." -ForegroundColor Yellow
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        Write-Host "   Instalando Node.js LTS via winget..."
        winget install -e --id OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements --silent | Out-Null
        $node = Get-Command node -ErrorAction SilentlyContinue
    }
}
if ($node) {
    Write-Host "   Node.js: $((& $node.Source --version))" -ForegroundColor Green
} else {
    Write-Host "   ADVERTENCIA: no se pudo instalar Node. opencode/omniroute lo necesitan." -ForegroundColor Red
}

# ---------- PASO 3: dependencias Python ----------
Write-Host "[3/7] Instalando dependencias Python del bot..." -ForegroundColor Yellow
& $python -m pip install --upgrade pip --quiet
& $python -m pip install -r "$KitDir\setup\requirements.txt" --quiet
if ($LASTEXITCODE -eq 0) {
    Write-Host "   Dependencias instaladas." -ForegroundColor Green
} else {
    Write-Host "   ERROR instalando dependencias." -ForegroundColor Red
}

# ---------- PASO 4: opencode + omniroute (npm global) ----------
Write-Host "[4/7] Verificando opencode y omniroute..." -ForegroundColor Yellow
$npm = Get-Command npm -ErrorAction SilentlyContinue
if ($npm) {
    $oc = & $npm root -g 2>$null
    if (-not (Test-Path (Join-Path $oc 'opencode'))) {
        Write-Host "   Instalando opencode (npm global)..."
        & $npm install -g opencode-ai --quiet
    } else { Write-Host "   opencode ya presente." -ForegroundColor Green }
    if (-not (Test-Path (Join-Path $oc 'omniroute'))) {
        Write-Host "   Instalando omniroute (npm global)..."
        & $npm install -g omniroute --quiet
    } else { Write-Host "   omniroute ya presente." -ForegroundColor Green }
} else {
    Write-Host "   npm no disponible, no se pudo instalar opencode/omniroute." -ForegroundColor Red
}

# ---------- PASO 5: desplegar config, cerebro y skills ----------
Write-Host "[5/7] Desplegando cerebro, skills y config de opencode..." -ForegroundColor Yellow
$ocConfig = Join-Path $env:USERPROFILE '.config\opencode'
$ocAgent  = Join-Path $ocConfig 'agent'
$ocSkills = Join-Path $ocConfig 'skills'
New-Item -ItemType Directory -Force -Path $ocConfig | Out-Null
New-Item -ItemType Directory -Force -Path $ocAgent  | Out-Null
New-Item -ItemType Directory -Force -Path $ocSkills | Out-Null

# Cerebro (agentes)
Copy-Item "$KitDir\setup\cerebro\*.md" $ocAgent -Force
# Memoria de reglas/preferencias (agentes)
$ocMemoria = Join-Path $ocAgent 'memoria'
New-Item -ItemType Directory -Force -Path $ocMemoria | Out-Null
Copy-Item "$KitDir\setup\cerebro\memoria\*.md" $ocMemoria -Force

# Config de opencode (solo si no existe, para no pisar config de otra maquina)
if (-not (Test-Path (Join-Path $ocConfig 'opencode.json'))) {
    Copy-Item "$KitDir\setup\opencode_config\opencode.json" $ocConfig -Force
}
Copy-Item "$KitDir\setup\opencode_config\opencode.jsonc" $ocConfig -Force -ErrorAction SilentlyContinue
Copy-Item "$KitDir\setup\opencode_config\package.json"  $ocConfig -Force -ErrorAction SilentlyContinue

# Skills (copia y fusiona)
Get-ChildItem "$KitDir\setup\skills" -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    $dest = Join-Path $ocSkills $_.Name
    if (-not (Test-Path $dest)) { Copy-Item $_.FullName $ocSkills -Recurse -Force }
}
Write-Host "   Desplegado en $ocConfig" -ForegroundColor Green

# ---------- PASO 6: PODER DE ADMINISTRADOR (tarea JARVIS_ELEVADO) ----------
Write-Host "[6/8] Configurando PODER DE ADMINISTRADOR (JARVIS_ELEVADO)..." -ForegroundColor Yellow
$bridgeCmd = "$KitDir\herramientas\manos\admin_bridge.cmd"
if (Test-Path $bridgeCmd) {
    $tarea = schtasks /query /tn "JARVIS_ELEVADO" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   La tarea JARVIS_ELEVADO ya existe (se mantiene)." -ForegroundColor Green
    } else {
        Write-Host "   Creando tarea JARVIS_ELEVADO (privilegios maximos)..."
        schtasks /create /tn "JARVIS_ELEVADO" /tr "`"$bridgeCmd`"" /sc onstart /rl highest /f | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   Tarea creada OK." -ForegroundColor Green
        } else {
            Write-Host "   ERROR creando la tarea. El poder admin necesita permisos de administrador para registrarla." -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "   (no se encontro admin_bridge.cmd; el poder admin no se configura)" -ForegroundColor Gray
}

# ---------- PASO 7: re-escribir rutas de maquina -> copia local ----------
Write-Host "[7/8] Adaptando rutas en la copia de trabajo (el kit queda intacto)..." -ForegroundColor Yellow
$antigua = "C:\Users\wasc4"
$kitScriptPath = "$KitDir\setup\adaptar_rutas.ps1"
# Copia de trabajo en el perfil de la PC nueva (el kit NO se modifica)
$local = Join-Path $env:USERPROFILE 'JARVIS_PORTATIL'
New-Item -ItemType Directory -Force -Path $local | Out-Null
Write-Host "   Copiando bot, herramientas y SISTEMA_JARVIS a $local ..." -ForegroundColor Gray
if (Test-Path "$KitDir\jarvis") {
    Copy-Item "$KitDir\jarvis\*" "$local\" -Recurse -Force
}
if (Test-Path "$KitDir\herramientas") {
    Copy-Item "$KitDir\herramientas\*" (Join-Path $local 'herramientas') -Recurse -Force
}
if (Test-Path "$KitDir\SISTEMA_JARVIS.md") {
    Copy-Item "$KitDir\SISTEMA_JARVIS.md" "$local\" -Force
}
if (Test-Path $kitScriptPath) {
    # Adaptar la copia local (bot + herramientas + cerebro copiado)
    & $kitScriptPath -Antigua $antigua -KitDir $KitDir -UserProfile $env:USERPROFILE -Target $local
    # Adaptar tambien el cerebro/skills DESPLEGADOS en opencode
    if (Test-Path "$ocConfig") {
        & $kitScriptPath -Antigua $antigua -KitDir $KitDir -UserProfile $env:USERPROFILE -Target $ocConfig
    }
} else {
    Write-Host "   (no se encontro helper de rutas, se omite)" -ForegroundColor Gray
}

# ---------- PASO 8: preparar y arrancar OmniRoute portable ----------
Write-Host "[8/8] Preparando OmniRoute portable y el bot..." -ForegroundColor Yellow
$omniData = "$KitDir\omniroute\data"
# Asegurar que el lock del puerto esté libre
$puertoLock = 20128
$conn = Get-NetTCPConnection -State Listen -LocalPort $puertoLock -ErrorAction SilentlyContinue
if ($conn) {
    Write-Host "   OmniRoute ya corriendo en el puerto $puertoLock." -ForegroundColor Green
} else {
    $orCmd = Get-Command omniroute -ErrorAction SilentlyContinue
    if ($orCmd) {
        Write-Host "   Arrancando OmniRoute portable (DATA_DIR=$omniData)..."
        # Variable de entorno que OmniRoute respeta para su carpeta de datos
        $env:DATA_DIR = $omniData
        Start-Process -FilePath (Get-Command node).Source -ArgumentList @(
            (Join-Path (Split-Path $orCmd.Source) 'node_modules\omniroute\bin\omniroute.mjs'),
            'serve','--no-open','--tray'
        ) -WindowStyle Hidden
        Write-Host "   Esperando a que OmniRoute responda en :$puertoLock..."
        $ok = $false
        for ($i=0; $i -lt 30; $i++) {
            Start-Sleep -Seconds 1
            try {
                $r = Invoke-WebRequest -Uri "http://127.0.0.1:$puertoLock/" -UseBasicParsing -TimeoutSec 2
                if ($r.StatusCode -eq 200) { $ok = $true; break }
            } catch {}
        }
        if ($ok) { Write-Host "   OmniRoute OK (HTTP 200)." -ForegroundColor Green }
        else { Write-Host "   OmniRoute no respondio a tiempo; revise logs." -ForegroundColor Yellow }
    } else {
        Write-Host "   omniroute no disponible; no se pudo arrancar el motor." -ForegroundColor Red
    }
}

# Arrancar el bot (desde la copia de trabajo local)
Write-Host ""
Write-Host "Lanzando el bot de Telegram de JARVIS..." -ForegroundColor Cyan
$botProc = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'jarvis_telegram_bot' }
if ($botProc) {
    Write-Host "   El bot ya estaba corriendo (PID $($botProc[0].ProcessId))." -ForegroundColor Green
} else {
    $botPath = "$local\jarvis\jarvis_telegram_bot.py"
    if (-not (Test-Path $botPath)) { $botPath = "$KitDir\jarvis\jarvis_telegram_bot.py" }
    Start-Process -FilePath $python -ArgumentList @('-u', ('"' + $botPath + '"')) `
        -WorkingDirectory (Split-Path $botPath) -WindowStyle Hidden
    Write-Host "   Bot lanzado desde $botPath. Icono de JARVIS en la bandeja." -ForegroundColor Green
}

Write-Host ""
Write-Host "=== INSTALACION COMPLETA ===" -ForegroundColor Green
Write-Host "JARVIS deberia estar en linea por Telegram. Si no responde," -ForegroundColor Gray
Write-Host "revise que esta PC tenga internet y que el puerto 20128 este libre." -ForegroundColor Gray
