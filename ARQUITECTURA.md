# ARQUITECTURA DEL SISTEMA JARVIS (Kit Portátil)

> Documento vivo del kit `JARVIS_PORTATIL`. Describe, con detalle, de qué
> está compuesto este sistema, cómo funciona cada pieza y cómo se conectan.
> Si algo está mal puesto o una ruta quedó desactualizada, ESTE documento es
> la referencia para corregirlo.
>
> Creado por JARVIS el 01/09/2026 para el señor Wáscar.
> Versión de arquitectura: 2.1 (sistema Telegram + OmniRoute + arranque/cierre).

---

## 1. IDEA GENERAL (el sistema en una frase)

JARVIS es un asistente que corre **dentro de la PC**. El jefe le escribe por
**Telegram** desde el celular; un **bot** local recibe el mensaje, lo pasa a
**opencode** (el "cuerpo" que me interpreta y ejecuta herramientas), y la
inteligencia la aporta **OmniRoute** (gateway local de modelos, puerto 20128),
que enruta entre varios modelos con el combo "COMBO JARVIS". Las respuestas
vuelven por Telegram.

```
Celular (Telegram)
      │
      ▼
jarvis_telegram_bot.py  ──►  opencode run --agent jarvis  ──►  OmniRoute (127.0.0.1:20128)
      │                                                          │
      └──────────────  respuesta hacia Telegram ◄────────────────┘
```

---

## 2. ESTRUCTURA DE CARPETAS DEL KIT

```
JARVIS_PORTATIL/
├── INICIAR_JARVIS.bat        ← EJECUTAR ESTO en la PC nueva (doble clic)
├── ABRIR_OMNIROUTE.bat       ← doble clic: abre el panel/ajustes de OmniRoute
├── LEEME.txt                 ← instrucciones rápidas para el jefe
├── ARQUITECTURA.md           ← ESTE documento
│
├── jarvis/                   ← EL BOT (la puerta de Telegram)
│   ├── jarvis_telegram_bot.py     bot completo (bandeja, Ajustes, estados)
│   ├── config_jarvis.json         ajustes editables (token, chat_id, agente,
│   │                              modelo, timeout) — se edita en "⚙️ Ajustes"
│   ├── historial_muse.json        historial de conversación (arranca vacío)
│   └── pool_sesiones_jarvis.json  pool de sesiones rotativas de opencode
│
├── setup/                    ← INSTALADOR + configuración que se despliega
│   ├── instalar_jarvis.ps1        instalador automático (lo lanza el .bat)
│   ├── adaptar_rutas.ps1          re-escribe rutas de la PC original → kit
│   ├── requirements.txt           dependencias Python del bot
│   ├── cerebro/                   MI CEREBRO (agentes de opencode)
│   │   ├── jarvis.md              ← identidad, reglas, memoria (YO)
│   │   ├── plan.md                agente planificador
│   │   └── trading.md             agente maestro de bots de trading
│   ├── skills/                    TODAS mis habilidades (skills)
│   └── opencode_config/           opencode.json + proveedores/combos
│
├── omniroute/                ← EL MOTOR DE INTELIGENCIA (portable)
│   └── data/
│       ├── storage.sqlite         BD con combos, modelos, presets y APIs
│       └── .env                   variables/llaves del gateway
│
└── herramientas/             ← MIS MANOS (scripts reutilizables)
    ├── manos/                    herramientas del sistema (diagnóstico, admin,
    │                             ver pantalla, lanzadores, etc.)
    └── scripts_agente/           scripts de acciones (música, YouTube,
                                  WhatsApp, capturas, etc.)
```

---

## 3. COMPONENTES Y CÓMO FUNCIONAN

### 3.1 El bot: `jarvis/jarvis_telegram_bot.py`
- Es un bot de Telegram (python-telegram-bot) que corre local, en segundo plano.
- Al arrancar lee `config_jarvis.json`; si no existe lo crea con valores
  predeterminados (token, chat_id, agente "jarvis", modelo
  "omniroute/COMBO JARVIS", timeout 90).
- Cada mensaje del jefe: lanza `opencode run --agent <agente> --model <modelo>`
  (directo, sin servidor intermedio), con un **pool de sesiones rotativas**
  (hasta 4, para que ninguna se llene de contexto) y **historial local** en
  `historial_muse.json`.
- Tiene un icono en la bandeja del sistema (pystray) con menú:
  - 💬 Abrir chat (abre la TUI de opencode con la sesión activa)
  - 🔄 Reiniciar JARVIS (reinicio quirúrgico)
  - ⚙️ Ajustes (ventana Tkinter para editar token/chat_id/agente/modelo/timeout;
    incluye botón "Restaurar ajustes predeterminados", selección de agente por
    desplegable, menú de clic derecho copiar/pegar)
  - ⏻ Cerrar completamente (apaga TODO JARVIS de forma limpia, ver abajo)
- **Ventana Ajustes (⚙️)** también tiene una **casilla "Iniciar JARVIS con
  Windows"**: al activarla genera `autostart_jarvis.ps1` junto al bot y crea
  `JARVIS.lnk` en la carpeta de Inicio de Windows, de modo que el bot arranca
  solo en segundo plano cada vez que la PC enciende. Al desactivarla, quita el
  acceso directo (habrá que iniciarlo con el iniciador). El valor se guarda en
  `config_jarvis.json` como `autostart`. **Por defecto viene ACTIVADA**.
- **Botón "Cerrar" de la ventana Ajustes**: SOLO cierra esa ventana de
  ajustes. NO apaga JARVIS (el apagado total es exclusivo del menú de la
  bandeja: "⏻ Cerrar completamente").
- **Arranque con Windows**: el `autostart_jarvis.ps1` vive junto al bot (se
  mueve con el kit) — arranca OmniRoute si no responde en 20128 (datos del
  kit `omniroute/data` o del perfil) y luego lanza el bot oculto.
- Envía estados en vivo: "🧠 Pensando y trabajando..." mientras el modelo piensa,
  y mensajes de herramientas mientras trabaja.
- Variables clave: `TOKEN` (bot de Telegram), `CHAT_ID` (id del jefe),
  `MUSE_MODEL` (combo), `MUSE_AGENT_JARVIS` (agente), `TIMEOUT_MUSE`,
  `autostart` (arranque con Windows).

### 3.2 opencode (el cuerpo que me interpreta)
- Es una CLI (npm global: `opencode`) que ejecuta agentes con herramientas
  reales (leer/escribir archivos, ejecutar comandos, navegar, etc.).
- El agente que se usa es `jarvis`, definido en el cerebro `jarvis.md`.
- Configuración: `~/.config/opencode/opencode.json` (proveedores y modelos)
  + `~/.config/opencode/agent/*.md` (cerebros) + `~/.config/opencode/skills/*`
  (habilidades).

### 3.3 OmniRoute (el motor de inteligencia, puerto 20128)
- Gateway local de modelos (Node.js, npm global: `omniroute`).
- Sirve en `http://127.0.0.1:20128`. También escucha en 20131/20132.
- Su **carpeta de datos vive DENTRO del kit** (`omniroute/data/`), por eso es
  portable: contiene `storage.sqlite` (combos, modelos, presets, claves) y
  `.env`. Arranca apuntando a esa carpeta (variable de entorno `DATA_DIR`).
- El combo principal es **COMBO JARVIS** (registrado en la BD y en
  opencode.json como `omniroute/COMBO JARVIS`), con estrategia de prioridad
  entre varios modelos.
- **Check de salud**: `Invoke-WebRequest http://127.0.0.1:20128/` debe dar 200.

### 3.4 Mi cerebro: `setup/cerebro/jarvis.md`
- Es MI identidad y MI memoria: personalidad, reglas, estilo, canal, memoria
  del jefe y protocolos. Se despliega a `~/.config/opencode/agent/jarvis.md`.
- El kit incluye una sección "CONCIENCIA DE IDENTIDAD Y ACTUALIZACION":
  sé que mi jefe es el señor Wáscar, que esta copia puede estar desactualizada
  respecto al original, y debo ser honesto y ofrecer actualizarme.

### 3.5 Skills: `setup/skills/*`
- Son guías de conocimiento especializado (web-dev, python-dev, game-dev,
  bot-builder, trading, automation, etc.). Se despliegan a
  `~/.config/opencode/skills/`.

### 3.6 Herramientas: `herramientas/manos` y `herramientas/scripts_agente`
- `manos/`: herramientas de sistema (diagnostico_jarvis.py, estado_jarvis.py,
  ver_pantalla.ps1, ejecutar_admin.py, admin_bridge.ps1/cmd, lanzadores,
  vigilar_jarvis.ps1, supabase.py, transcribir_audio.py, etc.).
- `scripts_agente/`: scripts de acciones reutilizables (música, YouTube,
  WhatsApp, capturas de pantalla, audio, etc.).

### 3.7 Lanzador del kit: `manos/lanzar_jarvis_telegram.ps1`
- Usa **rutas relativas** (deriva `KIT` desde la ubicación del script), por lo
  que funciona desde cualquier USB con cualquier letra de unidad y usuario.
- Pasos: 1) reactiva el vigilante si quedó desactivado; 2) arranca OmniRoute
  portable (datos del kit) si no responde en 20128; 3) mata instancias previas
  del bot; 4) lanza el bot oculto.
- También hay una copia del sistema en `Proyectos de asistente\manos\` con el
  bot de la PC original.

### 3.8 Iniciador OmniRoute: `ABRIR_OMNIROUTE.bat`
- Doble clic abre el **panel/ajustes de OmniRoute** en el navegador de la PC
  actual. Llama a `herramientas/manos/abrir_omniroute.ps1`.
- Es **totalmente autónomo** (no usa rutas fijas de la PC original):
  1) detecta el puerto de OmniRoute ACTIVO en ese momento (prueba
  20128/20131/20132 y el `--port` del proceso si existe); 2) si OmniRoute
  está caído, lo arranca con los datos del kit (`omniroute/data`) o del
  perfil del usuario y espera a que responda; 3) abre el navegador en
  `http://127.0.0.1:<puerto>/`.

### 3.9 Apagado completo: `manos/cerrar_jarvis_completo.ps1`
- Lo lanza el botón **"⏻ Cerrar completamente"** del menú de la bandeja
  (clic derecho sobre el icono oculto). Deja a JARVIS **completamente dormido**:
  1) mata TODAS las instancias del bot; 2) mata los procesos `opencode run`
  huérfanos; 3) libera el lock de instancia única (9123); 4) apaga OmniRoute
  (20128/20131/20132); 5) desactiva y detiene el vigilante.
- El botón **"Cerrar"** de la ventana Ajustes NO apaga nada: solo cierra la
  ventana de ajustes.
- El proximo arranque con `lanzar_jarvis_telegram.ps1` (o el autostart)
  reactiva el vigilante y OmniRoute y levanta el bot limpio.
- Es portable: solo usa el patrón `jarvis_telegram_bot` y puertos, sin rutas
  fijas, así que sirve igual en el kit USB.

---

## 4. FLUJO DE UN MENSAJE (paso a paso)

1. El jefe escribe por Telegram → llega a `jarvis_telegram_bot.py`.
2. El bot valida que el remitente sea `CHAT_ID` (solo el jefe).
3. El bot busca/crea una sesión del pool y lanza:
   `opencode run --agent jarvis --model omniroute/COMBO JARVIS ...`
4. opencode carga el cerebro `jarvis.md`, el modelo lo pide a OmniRoute
   (127.0.0.1:20128), que enruta al modelo que corresponda del combo.
5. El modelo (con herramientas) ejecuta lo que haga falta en la PC y produce
   la respuesta.
6. El bot limpia el markdown, envía la respuesta al jefe por Telegram y guarda
   el turno en `historial_muse.json`.

**Puntos que obstruyen el flujo** (verificar si algo falla):
- OmniRoute caído o puerto 20128 ocupado → el modelo no responde.
- Pool lleno/corrupto → el bot expulsa y crea sesiones nuevas.
- JSON corruptos → el bot los regenera o hay que borrarlos.
- Sin internet → no llega Telegram ni los modelos.

---

## 5. PODER DE ADMINISTRADOR (privilegios elevados)

JARVIS (tanto el original como el del kit) puede ejecutar comandos **como
administrador** sin ventanas de UAC, usando la **tarea programada
JARVIS_ELEVADO**:

- **Mecanismo** (en la PC original):
  1. `python herramientas/manos/ejecutar_admin.py "comando"`
     escribe el comando en `%TEMP%\opencode\jarvis_admin_in.txt`.
  2. Lanza la tarea: `schtasks /run /tn JARVIS_ELEVADO`.
  3. La tarea ejecuta `admin_bridge.cmd` → `admin_bridge.ps1` (como
     administrador, RunLevel=HighestAvailable), lee el comando, lo ejecuta y
     escribe la salida en `%TEMP%\opencode\jarvis_admin_out.txt`.
  4. `ejecutar_admin.py` espera y devuelve la salida.
- **REGLA**: usar privilegios solo para acciones que lo requieran (instalar,
  borrar archivos de sistema, tocar servicios, etc.). Para acciones simples,
  ejecutar directo. Si la acción es peligrosa, preguntar antes al jefe.

**EN EL KIT**: el instalador crea la tarea JARVIS_ELEVADO en la PC nueva
apuntando al `admin_bridge.cmd` del kit (las rutas se adaptan con
`%USERPROFILE%`/variables de entorno, no con rutas fijas de la PC original).

---

## 6. DIAGNÓSTICO Y AUTO-REPARACIÓN

- `python herramientas/manos/diagnostico_jarvis.py`
  Informe en vivo: proceso del bot, puertos clave (20128/20131/20132/9123),
  HTTP de OmniRoute, integridad de los JSON del bot y sesiones del pool.
- `python herramientas/manos/estado_jarvis.py`
  Informe más amplio: memoria, código compilable, modelo/proveedor, procesos,
  puertos, JSON y sistema (RAM/disco).
- Reglas de oro del doctor:
  1. Medir antes de tocar (diagnóstico real, no adivinar).
  2. Corregir y verificar. 3. Nunca inventar resultados.

---

## 7. RUTAS CLAVE (dónde vive cada cosa)

| Componente              | En el kit                            | En la PC desplegada                |
|-------------------------|--------------------------------------|------------------------------------|
| Bot de Telegram         | `jarvis/jarvis_telegram_bot.py`      | (se ejecuta desde el kit)          |
| Config del bot          | `jarvis/config_jarvis.json`          | (se ejecuta desde el kit)          |
| Cerebro (agente)        | `setup/cerebro/jarvis.md`            | `~/.config/opencode/agent/jarvis.md`|
| Skills                  | `setup/skills/*`                     | `~/.config/opencode/skills/*`      |
| Config opencode         | `setup/opencode_config/opencode.json`| `~/.config/opencode/opencode.json` |
| Motor OmniRoute         | `omniroute/data/`                    | (arranca desde el kit, puerto 20128)|
| Manos (herramientas)    | `herramientas/manos/*`               | (se usan desde el kit)             |
| Scripts de acciones     | `herramientas/scripts_agente/*`      | (se usan desde el kit)             |

> El instalador (`setup/adaptar_rutas.ps1`) re-escribe las rutas viejas de la
> PC original (`C:\Users\wasc4\...`) hacia las del kit en la PC nueva.

---

## 8. VERSIÓN Y ACTUALIZACIÓN DEL KIT

- Este kit es un **snapshot** (copia fiel) del sistema original en el momento
  en que se creó. Puede quedar desactualizado respecto al JARVIS original.
- **Cómo ponerse al día**: comparar el kit con el original (cerebro, bot,
  skills, combos de OmniRoute) y copiar lo que falte. El JARVIS del kit debe
  ser honesto: si le faltan datos, decirlo y ofrecer sincronizarse.
- Para actualizar el kit desde la PC original: recopiar
  `setup/cerebro/*.md`, `setup/skills/*`, `jarvis/jarvis_telegram_bot.py`,
  `omniroute/data/*` y `herramientas/*` con las versiones nuevas.