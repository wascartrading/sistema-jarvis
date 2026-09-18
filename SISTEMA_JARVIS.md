# SISTEMA JARVIS — MAPA MAESTRO
**Version: 14/09/2026.** Este es el documento de REFERENCIA PRINCIPAL del sistema:
si el jefe pide cambiar algo interno (emojis, onda, esfera, dictado, colores,
mensajes, canales...), JARVIS LEE AQUI PRIMERO y sigue las RECETAS de la
seccion 5. JARVIS tiene acceso TOTAL a todas las piezas.

## 1. QUE ES JARVIS
- Asistente personal del jefe (Wascar). Identidad + reglas permanentes:
  cerebro en `C:\Users\wasc4\.config\opencode\agent\jarvis.md` (se carga en
  CADA sesion; memorias tematicas en `...\agent\memoria\`).
- Motor de inteligencia: COMBO JARVIS via gateway **OmniRoute**
  (localhost:20128; datos en `C:\Users\wasc4\.omniroute\`, combos en la BD
  `storage.sqlite`).
- Canales: **(1) APP MOVIL = PRIORITARIO** (orden del jefe 14/09/2026);
  (2) Telegram + widget de voz = NEUTRALIZADOS por ahora (mientras exista
  `proyectos\telegram_off.flag` no se lanzan al iniciar; se reactivan
  borrando ese flag).

## 2. LAS PIEZAS (mapa completo)
| Pieza | Ruta | Que hace |
|---|---|---|
| Bot de Telegram | `proyectos\jarvis_telegram_bot.py` | Canal Telegram (neutralizado). Motor compartido: responder_jarvis, pool de sesiones, saludos, estados |
| Servidor movil | `proyectos\jarvis_movil\servidor.py` | Canal app por WiFi (8090/8443). `_procesar` = corazon del flujo del chat (estado inicial, prefijo de canal, imagenes de salida) |
| Agente del puente | `proyectos\jarvis_puente\agente_puente.py` | Conecta la PC a la nube (saliente). Cola de salida + warm-up + live |
| Puente nube | `proyectos\jarvis_puente\puente.py` | Relay en Railway (app <-> PC). /ping, estado al conectar |
| Live (Gemini) | `proyectos\jarvis_movil\live_jarvis.py` | Llamada de voz (Charon). VAD de Google, AGC, timeout del cerebro 60s |
| Interfaz web | `proyectos\jarvis_movil\web\` (index.html, puente_web.js, live_web.js, temas_esfera.js, sw.js) | Toda la UI de la app: esfera, chat, onda, dictado, comentarios, visor, historial |
| APK Android | `proyectos\jarvis_app\android\` (MainActivity.kt) | App nativa: WebView + dictado nativo + audio del live + guardar direccion |
| APK compilada | `proyectos\jarvis_movil\JARVIS.apk` y `...\jarvis_puente\JARVIS.apk` | La que descarga el telefono (`/app.apk`) |
| Widget de voz (PC) | `proyectos\widget_voz_jarvis\` | Widget flotante de escritorio (neutralizado con el bot) |
| Cerebro/memoria | `C:\Users\wasc4\.config\opencode\agent\jarvis.md` + `memoria\` | Identidad, reglas y memorias |
| Herramientas control | `proyectos\herramientas_control\cli.py` | Abrir apps, teclado, raton, vision, terminal, etc. |
| Manos | `Proyectos de asistente\manos\` | Scripts clave: lanzar_jarvis_telegram.ps1, vigilar_jarvis.ps1, diagnostico_jarvis.py, ejecutar_admin.py |
| Lanzador (arranque) | `manos\lanzar_jarvis_telegram.ps1` | Lo que corre Windows al encender (Run key "JARVIS") |
| Vigilante | `manos\vigilar_jarvis.ps1` (tarea "JARVIS Vigilante") | Repara servicios caidos (app SIEMPRE; bot solo si no hay flag) |
| Admin elevado | `manos\ejecutar_admin.py` (tarea JARVIS_ELEVADO) | Ejecutar comandos como administrador sin UAC |

## 3. FLUJO DE UN MENSAJE (app)
- EN CASA (WiFi): App -> servidor local (8090/ws) -> `_procesar` -> opencode (agente jarvis) -> COMBO via OmniRoute -> respuesta al chat.
- FUERA (o siempre hoy): App -> PUENTE (Railway) -> agente de la PC -> mismo motor -> respuesta por el mismo camino.
- El estado inicial inmediato ("<emoji> Conectando flujo...") lo pone `_procesar`.
- Los comentarios intermedios del modelo (tipo "texto") van SOLO al chat con formato de estado + 💬.

## 4. MECANISMOS CLAVE (comportamientos que existen y hay que respetar)
- **Arranque con la PC**: lanzador -> OmniRoute + [app: servidor + agente] SIEMPRE + [bot/widget solo si NO existe telegram_off.flag].
- **Vigilante**: cada pocos minutos; repara servidor/agente; bot solo sin flag.
- **Warm-up**: al conectar el agente la primera vez, calienta el motor (opencode+OmniRoute+modelo) con una llamada trivial.
- **Cola de salida del agente**: si un envio falla por micro-corte, se guarda y se reenvia al reconectar (nunca se pierde una respuesta).
- **Grace period 12s (puente_web.js)**: micro-cortes invisibles; solo las caidas reales muestran "Sin conexion con la PC".
- **Despertar + saludo**: PC apagada -> estado apagado; cuando vuelve -> despertar y saludo automatico. El saludo es LOCAL e INSTANTANEO (desde 14/09/2026): `SALUDOS_LOCALES` en `servidor.py` — texto predeterminado del codigo, NO pasa por el modelo (~0.2s).
- **Blindaje del Procesando**: no se apaga hasta el "fin" real del trabajo.
- **Live**: timeout 60s del cerebro (nunca queda "trabajando" pegado); AGC sube el audio del jefe; al cortarse la conexion se avisa "SE CORTO LA LLAMADA".
- **Dictado nativo**: continuo silencioso (mute del beep con permiso MODIFY_AUDIO_SETTINGS; re-arme automatico; se cierra SOLO al pulsar el micro o al enviar).
- **Historial del chat**: persistente en el telefono, AHORA POR CHAT (ver el
  punto siguiente); el boton de Ajustes limpia solo el chat abierto.
- **Selector de chats / cerebro fresco (15/09/2026, orden del jefe)**: la app
  tiene VARIOS chats. Cada chat guarda su hilo en el telefono (`jarvis_chats`,
  `jarvis_chat_actual`, `jarvis_msgs_<id>`) y su PROPIA sesion de opencode en
  la PC (`chats_movil.json` en el servidor local, `chats_puente.json` en el
  agente). El bot obedece `SESION_FIJADA` (ese chat usa SIEMPRE su sesion),
  `SESION_NUEVA_PEDIDA` + `SIN_PUENTE_MEMORIA` (chat nuevo = cerebro fresco,
  sin el hilo anterior) y publica `ULTIMO_SID`. Mensajes WS: `chat_nuevo`,
  `chat_activar`, `chat_borrar`, `chat_lista` -> respuesta `chat_ok`.
  Telegram NO usa nada de esto (valores por defecto = comportamiento de
  siempre). El chat de siempre se migro a "Principal" sin perder nada.
- **Botones flotantes del chat**: `#btnFondo` (volver al final) a
  `bottom: 58px` (el PUNTO MEDIO que pidio el jefe; 42 = pegado, 76 = muy
  arriba) y `#btnChats` nuevo en la cabecera, a la derecha del titulo.

## 5. RECETAS DE CAMBIOS (lo mas importante)
### A) Cambiar los emojis/texto del estado inicial "Conectando flujo..."
- `jarvis_movil\servidor.py`: `_flujo_emojis = ("⚡", "📡", "🔗")` y la linea `_poner(("estado", emoji_flujo + " Conectando flujo..."))`.
- Aplicar: relanzar servidor local Y agente (los dos procesos re-importan el modulo). Sin deploy web.
### B) Cambiar la velocidad del efecto de tecleo
- `jarvis_movil\web\index.html`: en `_efectoTipeo`, `const dur = Math.max(500, Math.min(3300, total * 11));` (11 = ms por letra; MENOR = mas rapido).
- Aplicar: local al instante; nube: copiar a `jarvis_puente\web\` + deploy (seccion 6).
### C) Cambiar las ondas de la barra (reposo / procesando)
- `index.html`, bloque de la onda: reposo `0.42 * Math.random()` (altura del reposo); procesando el factor `0.5` (mitad de intensidad; subir/bajar = mas/menos agresivo).
### D) Cambiar el giro o el ARO de la esfera del live
- `jarvis_movil\web\live_web.js`: `giro = (giro - 0.0045 + ...)` (signo = sentido del giro); bloque "ARO estilo Saturno" (`rAro` = radio del aro, `lineWidth` = grosor, `aroOn` = cuando aparece).
### E) Colores/temas de la esfera
- `jarvis_movil\web\temas_esfera.js` (paletas). El jefe elige el tema en Ajustes de la app; queda en localStorage.
### F) Formato de mensajes y comentarios
- `index.html`: `_formatoMensaje` (parrafos, negritas, codigo) y `_efectoTipeo`.
- `puente_web.js`: bloque "COMENTARIOS INTERMEDIOS" (formato estado + emoji 💬; limpieza del prefijo "Comentario, jefe:").
- **La orden que hace que el modelo LOS ESCRIBA vive en el CEREBRO**:
  `C:\Users\wasc4\.config\opencode\agent\jarvis.md`, sección "COMENTARIOS EN
  VIVO EN LA APP". Si algún día los comentarios dejan de aparecer, lo PRIMERO
  es comprobar que esa sección sigue ahí: el 15/09/2026 se descubrió que se
  había perdido en una reescritura del cerebro y el modelo llevaba días
  trabajando en silencio (la app estaba bien: no tenía nada que mostrar).
### G) Dictado (microfono)
- `jarvis_app\android\app\src\main\java\com\wascar\jarvis\MainActivity.kt`: `escuchar()` (silencios `60000L`), `mutearBeep`/`restaurarBeep`, re-arme en `onResults`/`onError`, `guardarUrl`.
- Aplicar: compilar APK (seccion 6) y copiar a los dos sitios.
### H) Estados/saludos/avisos del motor
- Estados: `jarvis_telegram_bot.py` (`_estado_de_evento` + `MAP_ESTADOS`) + `servidor.py`. Saludos de bienvenida: `SALUDOS_LOCALES` en `servidor.py` (LOCAL/instantaneo, no va al modelo; `SALUDOS` = prompts viejos del modelo, en desuso).
- **Regla del jefe (16/09/2026): cada estado tiene un EMOJI PROPIO, sin repetir, y acorde a la frase.** Catalogo actual (30 estados / 30 emojis unicos):

| Emoji | Estado |
|---|---|
| 💻 | Usando terminal · 🖥️ Proceso en segundo plano |
| 📖 Leyendo archivo · 📝 Creando archivo · ✏️ Editando archivo | |
| 🔍 Buscando archivos · 🔎 Buscando en archivos · 📂 Listando archivos | |
| 📡 Consultando en la web · 🌐 Buscando en la web | |
| 🧰 Cargando habilidad · 🤝 Delegando subtarea · 📋 Organizando el plan (N tareas) | |
| 🧪 Analizando datos · 🧮 Revisando varias fuentes · 📑 Analizando un archivo interno | |
| 🗂️ Buscando en mi registro · 🗃️ Guardando en mi base de consulta · 📥 Trayendo y guardando de la web | |
| 📊 Midiendo mi consumo de memoria · 🩺 Revisando mi salud interna · ⬆️ Actualizando mi sistema | |
| 📈 Abriendo el panel de trabajo · 🧽 Vaciando mi memoria · 🔧 Usando una herramienta interna | |
| 🧠 Pensando y Trabajando… · 🛠️ Trabajando y Pensando… · 🛰️ Consultando a JARVIS… · 🔄 Reintentando… · ⏳ Sigo trabajando, jefe | |

- Para anadir una herramienta nueva: meterla en `MAP_ESTADOS` con emoji NO repetido (el catalogo de arriba es la lista de ocupados). Las de `context-mode` (mis herramientas de contexto) van sin el prefijo `context-mode_` (hay fallback automatico).

### I) Reactivar Telegram/widget
- Borrar `proyectos\telegram_off.flag` (solo si el jefe lo pide).
### J) Boton "Reiniciar JARVIS" de la app
- `jarvis_movil\reiniciar_todo.ps1` (bot + servidor; lo dispara `_reiniciar_todo` del motor).
### K) Boton "volver al final" del chat (como Telegram) - 15/09/2026
- `jarvis_movil\web\index.html`: CSS `#btnFondo` (esquina inferior derecha, ENCIMA del boton enviar) y JS `_UMBRAL_FONDO` (px por encima del fondo para que aparezca; 120), `_actualizarBtnFondo` (mostrar/ocultar + limpiar), `_nuevoMensajeFondo` (notificacion = contador de mensajes nuevos llegados estando arriba) enganchado en `wAddMensaje` y `wAddMensajeImagen`.
- Aplicar: local al instante; nube: copiar a `jarvis_puente\web\` + deploy (seccion 6).
- POSICION (ajuste del jefe): `#btnFondo { bottom: calc(58px + safe-area) }`
  (42 px = pegado al de enviar; 76 px = muy separado; 58 = el punto medio).
- EXTRA del mismo dia: al ABRIR la app el chat arranca AL FINAL
  (`_anclarAlFondo()`), y al ENVIAR estando arriba la vista baja SOLA
  (`_irAlFondo()` en `_enviar` y en los mensajes del jefe).
### L) Selector de CHATS con cerebro fresco - 15/09/2026 (orden del jefe)
- **UI**: `jarvis_movil\web\index.html` -> `#btnChats` (cabecera del chat),
  `#panelChats` + `#veloChats` + `#listaChats`, JS `_chatsMigrar`, `_chatsLista`,
  `_chatNuevo`, `_chatActivar`, `_chatBorrar`, `_chatsPintarLista`,
  `_chatTituloAuto` (el primer mensaje bautiza el chat). Los mensajes viven en
  `jarvis_msgs_<id>` (80 por chat) y la lista en `jarvis_chats` (20 chats).
- **Aviso al motor**: `puente_web.js` expone `window.JarvisChatsEnviar` y
  maneja `chat_ok`/`chat_lista` -> `wChatOk`/`wChatLista`.
- **Servidor local**: `servidor.py` -> `CHATS_PATH` (`chats_movil.json`),
  `_chat_accion` (activar/nuevo/borrar/lista), `_fijar_sesion_chat` (antes de
  cada mensaje) y `_apuntar_sid_usado` (despues). Rama nueva en el WS.
- **Agente del puente**: mismo modulo cambiando `motor.CHATS_PATH`
  (`chats_puente.json`) + la misma rama en su `manejar`.
- **Motor (bot)**: `jarvis_telegram_bot.py` -> `SESION_FIJADA`,
  `SESION_NUEVA_PEDIDA`, `SIN_PUENTE_MEMORIA`, `ULTIMO_SID` (en `responder_muse`).
- **OJO (fallo corregido)**: `_fijar_sesion_chat` NO debe limpiar los pedidos
  cuando el chat aun no tiene sid; si lo hace, el chat nuevo reutiliza la
  sesion del pool y se pierde el "cerebro fresco".
- **Aplicar**: relanzar servidor local + agente (importan el bot y el servidor)
  y copiar `web\index.html` + `web\puente_web.js` a `jarvis_puente\web\` +
  deploy (seccion 6).
- **Probar de verdad**: cliente WS contra `ws://127.0.0.1:8090/ws` ->
  `chat_nuevo` + un mensaje: en `servidor.log` debe salir
  `[CHAT] cerebro fresco: sesion NUEVA forzada por la app` con
  `sid_activo=None` y el pool subir de 5 a 6 sesiones.

### M) Traer SIEMPRE al frente la app que abro - 16/09/2026 (orden del jefe)
- **Regla**: cada vez que JARVIS abre una app, un archivo o una web, la ventana
  debe quedar **AL FRENTE**, y hay que **verificarlo** (no suponerlo).
- **Donde vive**: `herramientas_control\app_control.py` → `traer_al_frente(nombre|hwnd, espera=6)`,
  con los ayudantes `_localizar_ventana()` y `_forzar_frente()`.
- **Como funciona**: 1) localiza por TÍTULO y, si no, por **PROCESO** (exe vía `tasklist`
  + `ALIAS_PROCESO`, p. ej. "bloc de notas" → notepad.exe); 2) restaura si está minimizada;
  3) `AttachThreadInput` + `BringWindowToTop` + `SetForegroundWindow` + `SetActiveWindow`;
  4) si Windows mantiene el candado de foco, suelta una pulsación de **ALT** y reintenta;
  5) **verifica** con `GetForegroundWindow` hasta 6 s.
- **Quien lo usa ya**: `app abrir ...` (todas las ramas), `app ventana front ...` y
  `file_controller.abrir()` (enfoca la ventana NUEVA comparando antes/después);
  `browser_control._focus_window` hace lo propio con Brave.
- **Añadir una app nueva**: sumar `"nombre": "proceso.exe"` a `ALIAS_PROCESO`.
- **Por qué fallaba antes**: se buscaba solo por título y el Bloc de notas se llama
  "archivo.py: Bloc de notas", así que "notepad" nunca coincidía; y Windows bloquea
  `SetForegroundWindow` cuando el proceso que llama no tiene el foco.
- **Probar**: `python cli.py app abrir notepad` → debe responder `... | al frente: <titulo>`
  y confirmarse con una captura.

### N) Guardar en el Bloc de notas / teclado sintético - 16/09/2026 (aprendido en vivo)
- **Atajo correcto**: en Windows en **español** Guardar es **Ctrl+G** (no Ctrl+S).
- **Pero los atajos con modificador NO entran** al Bloc de notas por teclado
  sintético: fallaron `keybd_event`, `SendKeys` y `SendInput`; encima la letra
  **sí** se cuela como texto (quedó una `:s` en la línea). Las teclas **sueltas**
  (flechas, Fin, Retroceso) sí funcionan.
- **Forma que funciona**: clic en el menú **Archivo** (x=40, y=34) y clic en
  **Guardar** (x=52, y=123); después comprobar que el título **pierde el asterisco**.
- **REGLA DE FOCO**: cada `python cli.py ...` es un **proceso nuevo** y al arrancar
  se queda el foco, así que traer-al-frente + teclas + verificación deben ir
  **TODO en un mismo script**. En comandos separados las teclas se pierden.
- Referencia del caso real: ejercicio `proyectos\ejercicios_python\promedio_notas.py`
  (faltaba el `:` del `if`, se tecleó en vivo y se guardó con este método).

### O) CÓDIGO EN VIVO + AUTOEDICIÓN (joyas del desmenuzado) - 16/09/2026
- **De dónde vienen**: del JARVIS-HRZ desmenuzado (`actions/code_agent.py` = "visión + acción
  para resolver problemas de código en pantalla" y `actions/self_edit.py` = editar el propio
  código con copia). Orden del jefe: traerlas para arreglar código "en tiempo real o en vivo".
- **Pieza 1 — `herramientas_control\code_live.py`** (CLI: `cli.py code`): ojos y manos para
  código. Acciones: `leer <ruta> [desde] [hasta]` · `editar <ruta> "<buscar>" "<reemplazar>"`
  · `editar_json` · `agregar` · `compilar` · `probar <ruta> [timeout]` · `reparar <ruta>
  [vueltas] [modelo]` · `abrir <ruta>` (lo muestra en el editor AL FRENTE) · `escribir "<texto>"`.
- **El bucle `reparar`** (el corazón): 1) compila; 2) si falla (sintaxis **o** ejecución), le pide
  al modelo por **OmniRoute** un JSON `{"ediciones":[{buscar,reemplazar}],"explicacion":...}`;
  3) aplica con **copia `.bak_AAAAMMDD_HHMMSS`**; 4) recompila y reproba; 5) repite hasta 3 vueltas
  e informa. Modelo por defecto `kiro/claude-haiku-4.5` (se cambia con `JARVIS_CODE_MODELO`).
- **Pieza 2 — `herramientas_control\self_edit.py`** (CLI: `cli.py self_edit`): `leer`, `editar`,
  `agregar`, `copias`, `restaurar`. Copia SIEMPRE y **lista blanca** (solo `Documents\Sistema Jarvis`
  y `.config\opencode\agent`); fuera de ahí se niega a tocar nada.
- **Detalle técnico**: la consola es **cp1252**; NO imprimir símbolos tipo ✔/✗ (rompen con
  `UnicodeEncodeError`); usar `OK`/`FALLO`.
- **En vivo, con cuidado**: si hay **dos ventanas del mismo programa**, elegir por **HWND**
  (`traer_al_frente(hwnd=...)` + comprobar `GetForegroundWindow`) y calcular el clic **dentro
  del `GetWindowRect` de esa ventana**; nunca clics a coordenadas fijas (el 16/09/2026 el texto
  se escribió en la ventana equivocada y hubo que cerrarla sin guardar).
- **Probado (16/09/2026)**: paréntesis sin cerrar → reparado · `len(nota)` por `len(notas)` → reparado
  y ejecutando bien ("Promedio: 20.0") · self_edit con copia y restauración · bloqueo de `C:\Windows`.

### P) CADENA DE VISIÓN — nunca perder la vista - 16/09/2026 (orden del jefe)
- **La orden**: "hay uno que funciona perfectamente, el de kiro, déjalo primero; si falla pasa a
  haiku y luego a sonnet… para que no haya manera de perder la visión".
- **Dónde**: `proyectos\herramientas_control\vision_deepseek.py` → tupla **`_MODELOS`** (orden de
  prioridad). Si un eslabón falla (error HTTP, respuesta vacía o se niega), pasa **solo** al
  siguiente. Los que fallan con **401/403/404/418** se marcan como caídos y no se reintentan.
- **Cadena vigente** (tiempos medidos en esta PC, misma captura):
  1. `kiro/claude-haiku-4.5` — 4.1 s ← el de siempre
  2. `kr/claude-haiku-4.5` — 2.1 s ← la ruta más rápida
  3. `kiro/claude-sonnet-4.5` — 5.4 s ← más músculo
  4. `kr/claude-sonnet-4.5` — 2.1 s
  y **red final**: Gemini directo (`_USAR_RESPALDO = True`, estaba apagado desde el 13/09).
- **Cambiar la cadena sin editar el archivo**: `JARVIS_VISION_MODELOS="modelo1,modelo2,..."`.
- `_TIMEOUT = 20 s` por intento (los modelos contestan en 2-6 s; así nunca se queda colgado).
- **Descartados por medición**: `ddgw/*` (HTTP 418), `tllm/*` (403 con 24 s), `agy/*` y `openrouter/*`
  (sin credenciales activas), `kiro/deepseek-3.2` (se niega a leer ventanas).
- **Probado**: visión normal → responde el 1º; con el 1º roto a propósito → responde el 2º
  (la visión no se pierde).

### Q) SABER SI UN VIDEO ESTA PAUSADO + REANUDARLO (EL OIDO) - 16/09/2026 (idea y orden del jefe)
- **El problema**: un video a pantalla completa (HBO, YouTube…) sale **NEGRO** en todas las capturas
  (global y PrintWindow) → no se puede ver si esta reproduciendo o pausado.
- **La solucion (el oido)**: `python "proyectos\herramientas_control\cli.py" audio suena brave 4`
  → **SUENA** (codigo 0) o **SILENCIO** (codigo 1). Funciona a pantalla completa y con el monitor
  en reposo, donde los ojos NO llegan.
  - **SUENA** = esta reproduciendo → **NO tocar nada** (`media play` es un interruptor: lo pausaria).
  - **SILENCIO** = pausado o mudo → `cli.py browser media play` lo reanuda y se comprueba otra vez.
- **Modulo**: `proyectos\herramientas_control\audio_control.py` (registrado en `cli.py` como
  `audio` / `oido`): `estado`, `suena <proceso> [segundos]`, `pico <proceso> [s]`,
  `silenciar <proceso> on|off`, `volumen <proceso> 0-100`. Requiere `pycaw` + `comtypes`
  (instalados el 16/09/2026).
- **Medido en vivo (16/09/2026)**: pausado → sin sesion de audio (pico 0,000) · reanudado → pico
  **0,125** con **59 de 59** muestras con sonido.
- **Receta completa de una serie (HBO Max)**: 1) historial de Brave
  (`%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Default\History`, **copiar a temp** porque
  el navegador lo bloquea) buscando `mentalist` → ahi estan los episodios vistos y sus horas;
  2) abrir la ficha de la serie en HBO: el boton **"Reanudar Tn En"** es la verdad (aunque el jefe
  creyera ir por el E2, HBO marcaba el **T3 E1** a medias); 3) pulsarlo y comprobar por **audio**;
  4) `cli.py browser media full` para pantalla completa y verificar la ventana por **geometria**
  (0,0,1366,768 y **sin barra de titulo** = pantalla completa real); 5) `cli.py system volumen set 50`.
- **Extra util**: en ventana (no pantalla completa) la captura SI se ve → comparar dos capturas
  separadas 4 s; si cambia mas del 30 % de los pixeles, el video corre.

### R) STREAM DE LA PANTALLA Y EL SONIDO AL CELULAR (JARVIS STREAM) - 16/09/2026 (orden del jefe)
- **Que es**: servidor local que entrega la pantalla COMO VIDEO EN VIVO (MJPEG) y el SONIDO DE LA PC
  (MP3) al navegador del celular. Ni nube, ni app, ni cuentas: misma WiFi. Proyecto: `proyectos\jarvis_stream\`.
- **Direcciones** (el lanzador las imprime siempre):
  - `https://192.168.100.2:8444` ← **la buena**: en contexto seguro el navegador permite el
    **bloqueo de pantalla** (que el celular no se apague, como YouTube). Usa el certificado de la app movil.
  - `http://192.168.100.2:8123` ← respaldo (ahi el bloqueo de pantalla NO existe; sirve el audio en marcha).
  - PC: `http://127.0.0.1:8123`.
- **Encender**: `powershell -NoProfile -ExecutionPolicy Bypass -File "…\jarvis_stream\iniciar_stream.ps1"`
  (si ya esta encendido NO duplica; parametros: `-Fps 30 -Calidad 65 -Ancho 0 -Puerto 8123 -PuertoTls 8444
  -SinAudio -SinHttps`) · **Apagar**: `detener_stream.ps1` (apaga los dos puertos) o `/detener?confirmar=si`.
- **VIDEO**: captura con **mss** (rapido; `--ancho 0` = tamano real). Medido en esta PC (1366x768):
  **30,4 fps reales** a 1366 px con JPEG 65 (2,3 MB/s); con 60 fps pedidos llega a **40 fps**.
  Consumo: **38 % de un nucleo = 2,4 % de la PC** (16 logicos) → no molesta ni jugando.
- **Botones de la pagina**: Alta (nativo · 30 fps) · Maxima fluidez (nativo · 45 fps) · Media (683 px ·
  30 fps) · Ahorro (455 px · 15 fps) · Sonido on/off · Pantalla completa · Girar · Reconectar.
- **SONIDO**: se graba la SALIDA del sistema con **WASAPI loopback** (libreria `soundcard`) del altavoz por
  defecto y se comprime a **MP3 128 kbps** con **lameenc** (bloques de 50 ms → sonido agil). Ruta `/audio`;
  cada oyente tiene su cola, un cliente lento NO frena a los demas. En el celular hay que pulsar una vez
  **▶ Escuchar** (los navegadores no dejan sonar nada sin un toque).
- **PANTALLA SIEMPRE ENCENDIDA**: `navigator.wakeLock.request('screen')` dentro de la pagina (se pide al
  entrar en pantalla completa, al pulsar Escuchar y al volver a primer plano). Solo funciona en contexto
  seguro → de ahi el HTTPS. Por HTTP queda el audio en marcha como respaldo.
- **Firewall**: reglas **"JARVIS STREAM 8123"** y **"JARVIS STREAM 8444"** (TCP entrante, solo perfiles
  privado y dominio), aplicadas con `manos\ejecutar_admin.py` + un .bat temporal.
- **LECCIONES (16/09/2026, todas medidas)**:
  - `Start-Process -RedirectStandardOutput` deja **colgada** la terminal que lanza el servidor → se lanza
    despegado con **Win32_Process.Create**, y el servidor escribe su propio `stream.log`. Ademas
    `-ArgumentList` pierde las comillas de rutas con espacios: usar nombre relativo + `-WorkingDirectory`.
  - **lameenc devuelve `bytearray`**, y el servidor web EXIGE `bytes`: sin `bytes(...)` el canal de sonido
    se cae con *"applications must write bytes"*.
  - El medidor de FPS hay que tomarlo **entre fotograma y fotograma publicados**; medir solo la
    codificacion da cifras falsas (daba 230 fps).
  - Para reducir la imagen, PIL `reduce()` con **factor entero** (1366→683→455) es mucho mas rapido que
    `resize()` BILINEAR: pedir 960 px desde 1366 px era MAS lento que no reducir nada.
- **Ajustes en caliente**: `/config?ancho=0&calidad=65&fps=30` · datos: `/estado` (fps reales, audio,
  oyentes) · foto suelta: `/snapshot`.
- **MODO TIEMPO REAL (WebRTC) - 16/09/2026, arreglo pedido por el jefe**: el jefe aviso de
  **"el audio llega con delay"** y **"el celular no detecta que es un video, se me apaga la pantalla"**.
  La causa: un MJPEG dentro de un `<img>` NO es un video para el navegador (no bloquea el apagado) y un
  MP3 suelto el navegador lo **bufferiza** varios segundos. La solucion es **WebRTC** (lo mismo que una
  videollamada): imagen y sonido por el mismo camino, con retraso minimo, y el celular lo reproduce con
  un `<video>` de verdad.
  - **Archivos**: `webrtc_stream.py` (pistas de video y sonido + servicio) y `pagina.html` (la pagina,
    que ahora se lee de archivo para poder retocarla sin tocar el servidor).
  - **Senalizacion**: `POST /webrtc/oferta?clase=video|audio` con `{sdp, type}` → devuelve el SDP de
    respuesta **ya con los candidatos dentro** (nada de ida y vuelta).
  - **Dos conexiones** por dispositivo (una de video y otra de sonido): asi cada una tiene UNA sola
    seccion de medios y los candidatos ICE entran sin ambiguedad. La pagina junta las dos pistas en un
    mismo `<video>` (`new MediaStream([...])`).
  - **Medido en vivo (16/09/2026, en esta PC)**: video **29,7 fps** entregados (1366x768) y sonido
    **49,8 paquetes/s** (cuadros de 20 ms); la respuesta del servidor tarda **0,07 s**; consumo con todo
    en marcha **34,4 % de un nucleo = 2,1 % de la PC**, 104 MB de memoria. Codecs: VP8 (libvpx) y Opus,
    los dos de fabrica.
  - **El modo respaldo (MJPEG + MP3) sigue existiendo**: si el navegador no puede con WebRTC, la pagina
    cambia sola y avisa. **Ojo**: en respaldo el MP3 sigue teniendo retraso (es culpa del navegador).
  - **Firewall**: ademas de los puertos 8123 y 8444 hay dos reglas por programa
    (**JARVIS STREAM WebRTC UDP** y **TCP** para `python.exe`, solo redes privada/dominio), porque
    WebRTC usa puertos UDP al azar.
  - **LECCIONES**: `RTCIceCandidate` de aiortc **no tiene `to_sdp()`** → la linea `a=candidate:...` se
    arma a mano (`candidato_a_sdp`). Y el cliente puede mandar su oferta **sin candidatos**: al llegar
    la peticion de conectividad el servidor aprende la direccion (candidato "peer-reflexive") y la
    conexion se completa igual (probado: 0 candidatos propios y `connected`).
- **Verificacion**: `python "…\jarvis_stream\verificar_stream.py"` (mide fps y kbps reales de los dos
  puertos) y, para WebRTC, un cliente de prueba que hace lo mismo que el celular.

## 6. DESPLEGAR / APLICAR (resumen)
- **Web**: editar en `jarvis_movil\web\`. Local (WiFi) aplica solo. Para la NUBE: copiar los archivos a `jarvis_puente\web\` y desde `jarvis_puente`:
  `node C:\Users\wasc4\AppData\Roaming\npm\node_modules\@railway\cli\bin\railway.js` up -y -d --service jarvis-puente
- **APK**: en `jarvis_app\android`: `$env:JAVA_HOME='C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot'` y `& 'C:\tools\gradle-8.10.2\bin\gradle.bat' assembleDebug --no-daemon`; copiar `app-debug.apk` a `jarvis_movil\JARVIS.apk` y `jarvis_puente\JARVIS.apk` (el del puente sube con el deploy).
- **Python (servidor/agente)**: editar y RELANZAR el proceso (`python -X utf8 -u servidor.py`; agente con la variable JARVIS_PUENTE de `iniciar_puente_agente.cmd`).
- **Reiniciar el BOT de Telegram desde JARVIS (diferido)**: `manos\reinicio_diferido_jarvis.ps1` (espera, ANOTA el reinicio en la caja negra y llama al reiniciador quirurgico `reiniciar_jarvis_telegram.ps1`, el mismo del boton "Reiniciar"). Lanzarlo SIEMPRE con **EncodedCommand** (receta en el cerebro §4): con `Start-Process ... '-Command' '... & "ruta con espacios"'` PowerShell **pierde las comillas** y el reinicio NO ocurre — fallo real del 16/09/2026. `-Simulacion` lo prueba sin reiniciar.
- **Verificar SIEMPRE**: `py_compile` / `node --check` + prueba real antes de reportar.

## 7. LOGS Y DIAGNOSTICO
- Servidor local: `jarvis_movil\servidor.log` | Agente: `jarvis_puente\agente.log` | Bot: `%TEMP%\opencode\jarvis_bot_out.log` | Vigilante: `%TEMP%\opencode\jarvis_vigilante.log` | Stream de pantalla: `jarvis_stream\stream.log`
- Diagnostico general: `manos\diagnostico_jarvis.py`
- Puente: `https://jarvis-puente-production-eaeb.up.railway.app/ping` (pc_conectada / apps_conectadas)
- **Logs rotados** (16/09/2026): cada reinicio guarda el log anterior en `proyectos\registro\logs\bot_salida_AAAAMMDD_HHMMSS.log` (nada se sobrescribe).

## 7-B. CAJA NEGRA / REGISTRO CENTRAL (16/09/2026, orden del jefe)
Todo lo que hace JARVIS queda escrito por dia en `proyectos\registro\AAAA-MM-DD.jsonl`
(una linea = un evento JSON: mensajes del jefe, turnos con duracion, herramientas,
comentarios, respuestas, reinicios, avisos y ERRORES con su traza). Nunca se
sobrescribe: si el bot se reinicia o muere, lo escrito queda.

- **Modulo**: `proyectos\registro_jarvis.py` (`evento`, `error`, `ok`, `aviso`, `turno_inicio/fin`, `resumen`, `salud`).
- **Terminal en vivo** (visor con colores, filtros y panel de estado):
  `python "C:\Users\wasc4\Documents\Sistema Jarvis\proyectos\registro\terminal_jarvis.py"`
  Teclas: 1 todo · 2 fallos/avisos · 3 Telegram · 4 herramientas · 5 salud · c limpiar · q salir.
- **Consultas**: `python ...\proyectos\registro\ver_registro.py --resumen | --errores --dias 3 | --buscar "timeout" | --salud | --dias-lista`
- **Estado actual**: `proyectos\registro\estado_salud.json` (PID del bot, instancias, OmniRoute, ultimo mensaje, ultimo fallo).
- **Enganches en el bot**: arranque/parada, mensaje recibido, turno (inicio/fin con segundos), estados, comentarios, respuesta enviada, cola, reinicio, interrupcion, errores de Telegram y de opencode (stderr/timeout), doble instancia.
- **Receta para diagnosticar**: abrir la terminal -> tecla 2 (fallos) -> si el fallo es del motor, mirar `ver_registro.py --errores` y el log rotado de esa hora.

## 7-C. COMANDOS RAPIDOS DE VERIFICACION
- Comentarios separados (FIX 16/09/2026): `separar_comentarios()` en el bot parte los
  comentarios que llegaban PEGADOS ("...historial.Comentario, jefe: ...") en un mensaje por comentario.


## 8. REGLAS DE ORO AL MODIFICAR EL SISTEMA
1. Probar antes de reportar (py_compile / node --check / prueba en vivo).
2. NUNCA relanzar el agente/servidor si hay una LLAMADA LIVE activa (revisar `agente.log`).
3. Cambios web: aplicar tambien al PUENTE (deploy) para la nube.
4. Respaldo (.bak con fecha) antes de editar archivos criticos.
5. Si el cambio es grande: LUZ VERDE del jefe (regla permanente).
6. El dictado y el live viven en el APK: si se tocan, avisar al jefe que instale la APK nueva.
