# PROYECTOS Y PLANES (memoria de trabajo)

## BOT-ANTIRRACHA ROJA / VELAS AISLADAS (PLAN V2, implementar cuando el jefe ordene)

DEFINICION "vela aislada": una vela (roja o verde) que esta SOLA, sin importar
cuantas velas del otro color haya alrededor.
SECUENCIA DE SEÑAL:
1) aparece 1 roja aislada (primera mitad),
2) aparecen 2 rojas CONSECUTIVAS aisladas juntas (escalon de 2 = SEÑAL COMPLETA),
3) el bot espera que aparezca UNA sola roja mas,
4) sobre ESA roja dispara la operativa hacia el lado contrario (minuto a minuto).
MARTINGALA (max. 3 operativas por ciclo, 1 martingala cada dos): operativa #1
hacia VERDE (CALL); si pierde, operativa #2 hacia VERDE (CALL, martingala); si
pierde, operativa #3 hacia ROJA (PUT, ultima). Objetivo: que el precio NO forme
3 velas aisladas (rojas) consecutivas.
ESTADO 02/09/2026: CREADO el proyecto `C:\Users\wasc4\Documents\PROYECTOS
PYTHON\BOT-ANTIRRACHA` (base PLANTILLA IQ OPTION; bot.py sin secuencias;
estrategia_antirracha.py con la logica V2 VALIDADA en simulacion; direcciones
por nivel call/call/put via direccion_para_nivel; martingala vela a vela;
reporte + avisos por evento con el FORMATO EXACTO del BOT-SECUENCIAS).
SIN token de Telegram y SIN cuenta del broker (el jefe los dara para
activarlo; hasta entonces el bot no conecta). Montos por defecto: objetivo
$1.00 -> MG0 ~$1.18 (payoff 0.85). NO se hizo push (regla de luz verde).
PENDIENTE aclarar: "50 dicuations" del jefe (no se capto: monto inicial?
50 operaciones? 50/50?).

## BOT DE SATURACIONES (BOT-SATURACIONES-V2-ESTABLE)

MEJORAS PENDIENTES DESCARTADAS por orden del jefe el 03/09/2026 ("descarta
todo eso que teniamos apuntado"). Ya NO son pendientes: NO implementar el
ajuste de punto de entrada, ni el re-anclaje exacto tras ganar, ni el sistema
de activos no disponibles. En su lugar el jefe pidio un NUEVO plan (pendiente
de luz verde): tras tomar una operativa en un activo, INHABILITAR las
restricciones de maximas interrupciones (max_interrupciones) para ESE activo.

## NUBE DE BOTS (Railway)

CORRECCION VERIFICADA 12/09/2026 (al verificar el bot de Rainer por orden
del jefe): los nombres REALES actuales del proyecto en Railway son:
- PROYECTO: **BOTS 24/7** (Project ID 3e9aba2e-ef94-4531-9c2e-c10bbdc188d5,
  region sfo, workspace wascartrading's Projects). NUNCA "impartial-compassion"
  ni "BOTS PARA 24/7" (nombres viejos que ya no se usan).
- Servicios: **BOT-MULTI-SECUENCIAS-VERSION-RAINER** (la cuenta RAINER
  PRACTICE; repo wascartrading/BOT-MULTI-SECUENCIAS-VERSION-RAINER) y
  **BOT-SATURACIONES-WASCAR**. NO "MULTI-SECUENCIAS" ni "BOT DE SATURACIONES".
- Enlace local: `railway link` desde la carpeta del repo
  `C:\Users\wasc4\Documents\PROYECTOS PYTHON\BOT-SECUENCIAS` con
  `-p "BOTS 24/7" -s BOT-MULTI-SECUENCIAS-VERSION-RAINER -e production`
  (se relinko el 12/09/2026 porque el enlace se habia perdido).
- ESTADO 12/09/2026 (verificado en vivo): BOT-MULTI-SECUENCIAS-VERSION-RAINER
  ● Online, cuenta RAINER PRACTICA, balance $161.80, 4 operativas (2G/2P,
  winrate 50%), reportes minuto a minuto OK, sin errores. BOT-SATURACIONES-
  WASCAR también ● Online.
- FIX FEED SIN AVANCE APLICADO 12/09/2026 (orden del jefe "conexion sin
  matar + configurable", commit 507ae74, deploy 06e8bc18 SUCCESS):
  el `_hilo_vigilante_feed` de bot.py ahora, ante feed global sin avance,
  primero RECONECTA el websocket sin matar (operativa.reconectar, que
  re-suscribe todo en paralelo) y solo tras `feed_reconexiones_max`
  (default 3) intentos fallidos hace os._exit(1) (Railway lo levanta).
  Umbral configurable en config.json: `feed_sin_avance_max_seg` (default
  300 = 5 min) y `feed_reconexiones_max` (default 3). Verificado: compila,
  deploy OK, bot arranco con 40 activos y las 19 secuencias activas.
- SSH A RAILWAY (12/09/2026): la CLI `railway ssh` se cuelga en esta PC;
  el método que FUNCIONA es ssh.exe directo contra ssh.railway.com con el
  bloque de `railway ssh config --dry-run -i <privada>`: User
  9d07a83e-d239-4675-9138-4b0121e4e703@ssh.railway.com (puerto 22),
  StrictHostKeyChecking=accept-new, UserKnownHostsFile=railway_known_hosts.
  Llave registrada en Railway: `jarvis_railway` (~/.ssh/jarvis_railway.pub).
  Para comandos con comillas usar stdin: `Get-Content script.sh | ssh ... "bash -s"`.

CORRECCION IMPORTANTE (03/09/2026, aviso del jefe por informe impreciso):
- El BOT DE SATURACIONES (servicio Online del proyecto "BOTS PARA 24/7") NO usa
  la cuenta IQ "RAINER". JAMAS afirmar eso en informes.
- RAINER (Rainerfgamers@gmail.com, PRACTICE) es la cuenta del MULTI-SECUENCIAS
  (proyecto "BOTS DE TRADING", repo local BOT-SECUENCIAS).
- Proyectos Railway verificados: "BOTS PARA 24/7" = ESPACIO VACIO (offline) +
  BOT DE SATURACIONES (online); "BOTS DE TRADING" = MULTI-SECUENCIAS (online,
  cuenta RAINER) + BOT-ESTADISTICO (online).
- REGLA DE PRECISION EN INFORMES (03/09/2026): verificar SIEMPRE el dato
  (proyecto, servicio, cuenta) antes de afirmarlo; si no esta verificado, no
  afirmarlo y ofrecer verificarlo.

Los bots de trading del jefe corren 24/7 en la NUBE (Railway), no en su PC.
El codigo vive en GitHub y Railway lo despliega automatico.
FLUJO: 1) editar el codigo localmente en la carpeta del bot (ej.
`C:\Users\wasc4\Documents\PROYECTOS PYTHON\BOT-SECUENCIAS`), 2) `git commit`
del cambio, 3) `git push origin master` -> GitHub, 4) Railway detecta el push
y hace deploy automatico (nuevo deployment ID), 5) el bot arranca en la nube
con el codigo nuevo. Verificar con `railway status` y `railway logs`.
ADMINISTRACION: CLI `railway` instalada y enlazada al proyecto
impartial-compassion (servicios: MULTI-SECUENCIAS y BOT-ESTADISTICO). No tiene
llaves SSH (railway ssh no funciona; railway run solo ejecuta local).
`railway variables` muestra las variables de entorno (en MULTI-SECUENCIAS NO
hay IQ_EMAIL ni IQ_PASSWORD: las credenciales van en credenciales.py del repo).
CREDENCIALES: prioridad = variables de entorno -> credenciales.json ->
credenciales.py (import). En BOT-SECUENCIAS nunca subir credenciales.json
(esta en .gitignore); la cuenta se cambia editando CUENTA_ACTIVA en
credenciales.py y haciendo push.
ESTADO ACTUAL (confirmado 02/09/2026 y NO SE TOCA MAS — orden del jefe):
MULTI-SECUENCIAS ● Online, cuenta IQ = RAINER (Rainerfgamers@gmail.com,
PRACTICE), chat de Telegram UNICO = 1663362987 (mensaje de inicio, reportes y
paneles solo a ese chat, sin multi-chat), bot.py identico al original (commit
revert), deployment d5c498bf. PRÓXIMO: plan para un BOT NUEVO (estrategia
antirracha/velas aisladas, arriba).

## IDEA FUTURA: DOBLE COPIA -> OPERAR TODAS POR MAYORIA (08/09/2026, pendiente implementar)

IDEA DEL JEFE (guardada 08/09/2026 para implementar en el futuro, sin luz
verde aun): cuando ocurren 2 COPIAS seguidas — p.ej. la copia del cuadrante
1 y luego la copia del cuadrante 1 repetida en el cuadrante 2 — si en una de
las copias se cuentan las velas y la MINORIA es verde, se operaran TODAS las
velas en el cuadrante 3 hacia VERDE. Es una idea conceptual; falta definir
la logica exacta de conteo y confirmar antes de implementar.

## DISEÑO DE LOGS DEL BOT ANTIRRACHA (preparado 02/09/2026, pendiente visto bueno)

Reporte minuto a minuto en DOS fases:
(1) VIGILANCIA de velas cerradas con estado de la senal: [hora] VELA HH:MM |
COLOR | racha | estado (buscando aislada / 1-2 SENAL / escalon 2 -> SENAL
LISTA / esperando 3a roja / DISPARO);
(2) CICLO DE OPERATIVAS: OPERATIVA #N | direccion (CALL verde / PUT roja) |
activo | monto | expira, y luego RESULTADO #N | WIN/LOSS | monto | saldo |
ciclo cerrado/PERDIDO.
Al cierre de dia: RESUMEN | senales | operativas | W | L | neto.
Montos configurables (INICIAL, MULTIPLICADOR MARTINGALA, MAX OPERATIVAS=3).

## PENDIENTE: SSL CROSS sobre la PLANTILLA IQ (plan creado 10/09/2026)

ORDEN DEL JEFE (10/09/2026): implementar el indicador SSL CROSS como
estrategia (plugin) del motor PLANTILLA IQ OPTION (repo
wascar2416-star/PLANTILLA-IQ-OPTION.git; carga por config
"estrategia": "<nombre>" -> importa estrategia_<nombre>.py). El jefe pidio
dejar esto como PENDIENTE al apagar la PC ese dia.
PLAN ACORDADO (modo plan, SIN implementar aun):
- Estrategia nueva `estrategia_ssl.py` (base: estrategia_vacia.py). Logica
  SSL: SMA(high,13) y SMA(low,13) -> HLV (1 si close>smaHigh, -1 si
  close<smaLow, si no conserva el anterior) -> sslUp/sslDown -> cruce REAL
  sobre VELA CERRADA: cruce arriba = CALL, cruce abajo = PUT.
- CONFIG: ssl_len (5..50, default 13), filtro EMA opcional (off), una senal
  por vela. Anti-repintado: SIEMPRE vela cerrada (el motor ya entrega velas
  cerradas al :00).
- Fases: 0) definiciones (bot nuevo desde la plantilla o dentro de ella;
  cuenta/chat; estrategia sola o filtro; demo local vs nube); 1) modulo
  estrategia_ssl.py; 2) config del bot; 3) pruebas test_ssl.py + py_compile +
  simulacion en seco; 4) despliegue con luz verde (demo primero).
  Entregable: bot con SSL sobre el motor IQ, probado y en repo.
- Preguntas abiertas al jefe: bot nuevo vs plantilla; cuenta
  (@NuevaIdeaBot/WASCARFLOW3/8456515934 o nueva); filtro EMA si/no; demo
  local o nube.

## PENDIENTES WIDGET FLOTANTE JARVIS TELEGRAM (anotados 12/09/2026)

ORDEN DEL JEFE (12/09/2026): "ya con esto acabamos por ahora... unas cuantas
cositas que vamos a dejar en pendientes" — 3 mejoras al widget flotante
(proyectos/widget_voz_jarvis), sistema JARVIS Telegram:
1. BOTON PARA INTERRUMPIR: implementar un boton en el widget para interrumpir
   (cortar la escucha / la respuesta de JARVIS al momento).
2. VISUALIZACION DE ESTADOS DE TRABAJO: que el widget muestre cuando JARVIS
   use herramientas, trabaje en la terminal o cree archivos, igual como se
   visualizan los estados en Telegram (tipo "Pensando...", herramienta en
   uso, etc.).
3. MEJOR VOZ: IMPLEMENTADO 12/09/2026 (la voz REAL del desmenuzado):
   - Investigacion: el desmenuzado NO usa edge-tts de Charon ni Kokoro local.
     "Charon" es una voz PREBUILT del Live API de Google (google.genai, modelo
     gemini-2.5-flash-native-audio-preview-12-2025). Confirmado en main_dump:
     types.SpeechConfig/VoiceConfig/PrebuiltVoiceConfig(voice_name=),
     response_modalities=AUDIO, audio 24 kHz int16.
   - Implementado en widget_voz_jarvis: modulo voz_gemini.py (conecta al Live
     API con voz Charon, envia el texto redactado, reproduce en streaming con
     sounddevice). voz.py orquesta: Charon (Gemini) principal + respaldo
     edge-tts Jorge (nunca mudo). config.json: gemini_api_key (copiada del
     desmenuzado 07 config) + voz_gemini: "Charon" (+ voz_edge para respaldo).
     SDK google-genai 2.23.0 (async client.aio.live).
4. FIX ESTATICA "TV SIN SEÑAL" (12/09/2026, reporte del jefe): la voz salia
   como television vieja -> miniaudio devolvia el audio en escala de enteros
   (±23000) y en un array plano interleaved; al reproducirlo asi hacia
   clipping y se mezclaban los canales. Fix en voz.py `_hablar_edge`:
   reestructurar a (frames, canales) si es interleaved + normalizar a ±1
   (dividir por 32768 y np.clip). Verificado con señal real; widget relanzado
   PID 1640. NO debe volver a pasar (fix blindado en el codigo).
5. CHARON SOLO LEE EL TEXTO DEL COMBO (12/09/2026, problema del jefe: "el
   modelo responde a su manera"): 
   - Instruccion de sistema ESTRICTA en voz_gemini.py: LiveConnectConfig con
     system_instruction (types.Content/Parts) que ordena a Charon ser SOLO un
     sintetizador: leer LITERALMENTE el texto recibido, prohibido anadir,
     parafrasear, resumir, traducir, opinar o conversar.
   - Ademas el micro del widget NUNCA pasa por Gemini (flujo: esfera -> Vosk
     local -> COMBO JARVIS = contenido; Gemini solo recibe el texto final).
   - Verificado por duracion de audio real: texto de 33 palabras -> ~12,7 s
     de voz (lectura completa y literal, sin inventar).
6. STREAM PERSISTENTE (12/09/2026, adios al retraso de ~5 s):
   - La sesion Live queda CONECTADA SIEMPRE (en silencio, sin escuchar); al
     hablar ya NO se reconecta. El servidor de Google recicla la sesion tras
     cada turno, pero voz_gemini.py la auto-reconecta en ~0,8 s y REINTENTA el
     envio (hasta 5 intentos) si la sesion se estaba reciclando.
   - session.send quedó DEPRECADO en google-genai 2.23.0 -> se usa
     send_client_content(turns=[Content(role="user", Part(text=...))],
     turn_complete=True).
   - El Live API NO siempre envia turn_complete: hay un vigilante de turno
     (_vigia_turno, corrutina del loop) que detecta fin de turno por silencio
     de datos (3 s) o modelo mudo (15 s), y cierra el turno sin cerrar la
     sesion (clave: NO usar wait_for sobre receive().__anext__(), pierde
     audio; usar `async for` puro).
   - Medido real: turnos en 3,0-5,1 s (antes ~17 s). Widget relanzado PID 3876.
   - config.json del widget: "stream_persistente": true.
7. PENDIENTES aun vigentes del widget: (1) boton para interrumpir escucha/
   respuesta; (2) visualizacion de estados de trabajo (herramientas/terminal)
   en el widget, como en Telegram.
Retomar cuando el jefe lo pida.

## APP JARVIS MOVIL (Android) + MODO LIVE — 13/09/2026
Proyecto GRANDE del jefe: una **app Android propia (APK)** para manejar a JARVIS
desde el telefono (Samsung Galaxy S21 FE): en casa por WiFi y desde CUALQUIER red
por un **puente en la nube**.

**DOCUMENTACION COMPLETA (leerla SIEMPRE al retomar este proyecto):**
`C:\Users\wasc4\Documents\Sistema Jarvis\proyectos\jarvis_movil\DOCUMENTACION.md`
Ahí está todo: arquitectura de las 3 piezas, rutas de archivos, links, funciones,
**bitacora de 12 bugs resueltos**, comandos (recompilar APK, reiniciar servidor,
redesplegar el puente) y pendientes.

Las 3 piezas:
- **APP** (`proyectos\jarvis_app\android`, Kotlin): WebView con la interfaz del
  widget + nativo (audio del Live, dictado, galeria). Version actual **v1.8**.
- **SERVIDOR LOCAL** (`proyectos\jarvis_movil\servidor.py`): sirve la interfaz
  (8090/8443), el motor del chat y el **MODO LIVE** (`live_jarvis.py`: Gemini
  Live con voz **Charon** y TODAS las herramientas de JARVIS activas).
- **PUENTE NUBE** (Railway, proyecto NUEVO `jarvis-puente`): `puente.py` (relay)
  + `agente_puente.py` (conexion SALIENTE desde la PC; la PC no abre puertos).

Links: APK `http://192.168.100.2:8090/app.apk` · interfaz local
`http://192.168.100.2:8090` · puente `https://jarvis-puente-production-eaeb.up.railway.app`
· token del puente en `proyectos\jarvis_puente_TOKEN.txt` · auto-arranque en
`proyectos\autostart_jarvis.ps1` (bot + servidor movil + agente).

Reglas que NO hay que romper (aprendidas a golpes):
- Fuente de audio del micro en la APK: **VOICE_RECOGNITION** (VOICE_COMMUNICATION
  devolvia SILENCIO en el S21 FE).
- **Anti-eco del Live**: el micro se pausa mientras JARVIS habla (si no, Gemini
  se oye a si mismo y repite en bucle).
- El `_recibir` del Live se reanuda en bucle: el generador `receive()` de Gemini
  se agota tras un turno (si no, el 2º turno no respondia).
- El agente del puente usa **su propio pool e historial** (no los del servidor
  local: se pisaban las sesiones y los mensajes quedaban "procesando").
- El service worker de la app es **RED PRIMERO** (cache-first servia JS viejo).
- Compresion de contexto (sliding window) + brevedad = fluidez en llamadas
  largas; el VAD forzado de Google se probo y ROMPIA los turnos.
Retomar cuando el jefe lo pida.

## PENDIENTES ACTIVOS (anotados 18/09/2026, el jefe preguntará por ellos)

1. **EJERCICIOS 1**: empezar a tratar y resolver los ejercicios que están en
   un archivo llamado "EJERCICIOS 1" en la carpeta de Descargas (Downloads).
2. **SISTEMA CONFIG-JARVIS**: crear un sistema para aplicar y/o observar la
   configuración de JARVIS (config-jarvis) — hacer cambios al config del
   modelo/motor o aplicar modelos directos.
3. **TECLADO TELEGRAM v2 — menú "Herramientas"** (pendiente, 18/09/2026): el
   botón "Reiniciar" del teclado (que trabaja POR FUERA del modelo) se
   sustituirá por uno llamado "Herramientas"; dentro irá el botón Reiniciar
   + varios botones más (menú abierto a añadir). El jefe aún no define qué
   otros botones poner: por ahora NO tocar el teclado (queda como está:
   Interrumpir/Reiniciar). Regla a mantener: los botones no se envían al
   modelo (ajustes fluidos si JARVIS no funciona); solo teclado y "limpia
   conversación" no pasan al modelo. Retomar cuando el jefe defina los botones.

## FIXES APLICADOS — AUDITORÍA 18/09/2026 (todo verificado y activo)

- [2026-09-18] Ajustes v2 del bot: catálogo completo (106 modelos, fix nonlocal x3), instancia ÚNICA (doble clic = 1 ventana centrada), menos vertical (minimizar restaurado por orden del jefe), "✅ Disponibles" = estado de OmniRoute SIN llamar a modelos (instantáneo; GET /api/models -> campo available), "Guardar y reiniciar" valida el motor y REINICIA AL INSTANTE.
- [2026-09-18] Todo mensaje de texto va al MODELO: eliminados los atajos fijos "despierta" y "¿qué modelo eres?"; del teclado (Interrumpir/Reiniciar) y "limpia conversación" no pasan al modelo.
- [2026-09-18] Modelo dinámico: "[MODELO ACTIVO ...]" inyectado en cada turno + guía en jarvis.md sección 5 (responder EXACTO lo que diga config_jarvis.json).
- [2026-09-18] Iconos oficiales (arc reactor del JARVIS-HRZ desmenuzado) en bandeja FIJA (promover_icono_jarvis.ps1), ventana Ajustes (WM_SETICON + AUMID Jarvis.Telegram.System), panel del widget, lnk de inicio y manos\jarvis.ico. Assets en `proyectos\assets\`.
- [2026-09-18] Widget de voz: cierre blindado de 3 capas (WM_CLOSE -> taskkill -> barrido con _T0_PROCESO) + 1 sola instancia; el bot espera a 0 widgets antes de relanzar. Anti-huérfanos en _probar_modelo (taskkill /T).
- [2026-09-18] Ajustes v2 reorganizada: pestañas Razonamiento/Cerebro/Telegram/General (Cerebro = cambiar el agente activo con Guardar y reiniciar; General = inicio con Windows + restablecer predeterminados); ventana normal sin topmost; título sin emoji; botones depurados (Actualizar/Disponibles/Probar/Guardar). Estados: fix trailing (cambios rápidos no se pierden) + latido con tiempo. Buscador con indicación "Busca tu modelo específico"; Cerebro con TODOS los agentes de opencode (sistema + built-in); identidades propias en doctor/plan/trading (sección "Quien eres").
- [2026-09-18] Detalle COMPLETO de cada fix: `SISTEMA_JARVIS.md` sección 9 (con recetas de auto-reparación). Backups .bak_20260918_* en proyectos\.