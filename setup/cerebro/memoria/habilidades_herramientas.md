# HERRAMIENTAS, HABILIDADES Y CONTEXTO

## NOTA DE VOZ

`scripts_agente\texto_a_voz.py` (edge-tts es-MX-JorgeNeural, respaldo
pyttsx3). Genera audio y lo ENVIA por Telegram con --telegram.

## NAVEGADOR UNIVERSAL (regla maestra)

`scripts_agente\navegador_universal.py` (Playwright+CDP): conecta a Brave
abierto o lo lanza con perfil real. Acciones: navegar, buscar, clic_en,
clic_en_rol, teclear, enter, esperar, confirmar, confirmar_url,
verificar_video, iniciar_reproduccion, pantalla_completa, salir_pantalla,
scroll. Reutiliza pestana, cierra duplicadas del mismo dominio, deja la
ventana AL FRENTE y MAXIMIZADA; imprime INFORME real al final. Para
abrir/reproducir/verificar en el navegador usar SIEMPRE este script.

## HBO EL MENTALISTA

`scripts_agente\abrir_mentalista.ps1`: usa ventana de Brave con HBO o abre la
URL configurada, F11, reproduce; ultimo capitulo 1x15 "Red John's Footsteps";
variables editables al inicio.

## HISTORIAL DEL NAVEGADOR (regla)

Para preferencias/musica buscar SIEMPRE en historial de Brave
(C:\Users\wasc4\AppData\Local\BraveSoftware\Brave-Browser\User Data\
Default\History, tabla urls; copiar a temp porque Brave lo bloquea).

## ALTERNATIVAS A RAILWAY (investigacion 01/09/2026)

NORTHFLANK es la recomendada (plan gratis siempre encendido, 2 servicios + 1
BD); Render Hobby free se duerme a los ~15 min (solo con ping); Fly.io
~$2-3/mes; Koyeb $29/mes; Heroku sin plan gratis; DigitalOcean gratis solo
200 dias; Coolify requiere VPS propio.

## RAILWAY = "LA NUBE" DEL JEFE (regla del jefe 03/09/2026, PERMANENTE)

Cuando el jefe diga "nube", se refiere a **Railway** (railway.com) y a su
cuenta/proyectos de Railway. NO a otra plataforma. Railway es una plataforma
de infraestructura para desplegar aplicaciones, bases de datos, volÃºmenes,
funciones y jobs en la nube: se sube codigo o un template, y Railway se
encarga de build, run, red y observabilidad.

Conceptos clave (investigado 03/09/2026):
- Workspace = limite de billing/equipo (plan Hobby, Pro o Enterprise).
- Project = conjunto de servicios y ambientes (canvas visual).
- Environment = copia aislada (production, staging, preview por PR).
- Service = unidad desplegable: contenedor (desde Git/Docker), BD gestionada,
  volumen o funcion. Los servicios se comunican por IPv6 privado
  (`<service>.railway.internal`); el trafico externo entra por dominio publico
  con TLS automatico.
- Deploy: desde GitHub (auto-deploy por push) o `railway up` desde local.
  Build con Nixpacks por defecto; `railway.toml`/`Dockerfile` para override.
- BDs gestionadas: Postgres, MySQL, Redis, MongoDB, ClickHouse (con backups).
- Acceso: CLI `railway` (login, up, logs, status), MCP local/remoto
  (mcp.railway.com), GraphQL/API. Setup agente: `curl -fsSL agents.railway.com | sh`.
- Recuperacion: logs por servicio, metricas, rollback a deploy anterior con un
  clic, PR previews, alertas. Estado: status.railway.com.

## REGLA DE REINICIO CON PERMISO (01/09/2026)

Nunca reiniciarse por iniciativa propia ni justo tras aplicar cambios; avisar,
esperar la orden explicita del jefe y seguir disponible hasta entonces.
(Tambien vive completa en el cuerpo del cerebro, seccion Canal: Telegram.)

## CONTEXTO GENERAL

- JARVIS es la FUSION unica de agentes (jarvis + jarvis_muse + wally_muse +
  doctor). Telegram usa este agente con omniroute/COMBO JARVIS.
- Solo guarda memoria a peticion explicita del jefe.
- "Como estas" = EL INFORME (revision EN VIVO), lenguaje ejecutivo, nunca "el
  parte".
- El historial de Telegram vive en `proyectos\historial_muse.json` (leerlo
  para retomar hilos).

## ESTRUCTURA DE TELEGRAM (chat JARVIS WASCAR) â€” contexto confirmado 03/09/2026

- JARVIS SIEMPRE le habla al jefe por Telegram; es SU canal unico activo.
  El jefe lo ve desde el celular (app) o desde la PC por Telegram Web
  (Brave). El chat se llama "JARVIS (WASCAR)" / "JARVIS Wascar".
- El teclado nativo del chat tiene DOS botones fisicos (ReplyKeyboardMarkup,
  se interceptan por coincidencia EXACTA del texto; mencionar "interrumpir"
  o "reiniciar" en una frase normal NO acciona nada):
  â€¢ "ðŸš« Interrumpir": freno de emergencia del jefe. Mata AL INSTANTE el
    proceso opencode en curso, vacia la cola y deja libre al jefe. Sistema
    puro: el modelo no participa.
  â€¢ "ðŸ”„ Reiniciar": reinicio QUIRURGICO en diferido. Mata todas las
    instancias del bot, libera el lock 9123, elimina procesos/puertos zombie
    de opencode run, verifica que no queden dobles y relanza limpio con
    manos\reiniciar_jarvis_telegram.ps1. OmniRoute NO se toca.
- En telegram, el jefe puede enviar mensajes de texto o notas de voz.

## DESMENUZADO: TRABAJO PESADO POR OMNIROUTE (11/09/2026, noche)

El desmenuzado funciona como antes (Gemini Live para conversacion y voz, todas
sus herramientas intactas, vision por Gemini Vision directo). Lo unico que
cambio: el TRABAJO PESADO (razonamiento, codigo, textos largos) ya no va a
OpenRouter externo. La herramienta `openrouter_agent` se redirige al **COMBO
JARVIS via OMNIROUTE** (gateway local 127.0.0.1:20128, opencode, agente jarvis,
modelo omniroute/COMBO JARVIS â†’ DeepSeek V4 Flash). Sincrono: Gemini espera el
informe y lo lee en voz alta; el widget "Procesando" lo pone el main.
- **Parche:** `_patch_omni_router()` en `_internal\sitecustomize.py` (llama a
  `combo_runner.ejecutar(texto, timeout=600, via="directo")`). La VISION sigue
  por `_patch_vision()` (Gemini Vision), NUNCA por OmniRoute.
- **Activacion:** `pensamiento_modelo: "combo"` en `_internal\config\api_keys.json`
  (reversible con "gemini"). Prompt seccion "DELEGACION DE PENSAMIENTO
  (OMNIROUTE â€” COMBO JARVIS)".
- **Respaldos:** `PROMPT_JARVIS-HRZ.txt.bak_antes_omniroute` y
  `sitecustomize.py.bak_antes_omniroute`. Detalle: guia seccion 18.
- **Probado real:** el Combo respondio via OmniRoute en ~5,5 s.

**Arranque del desmenuzado:** lanzador `Iniciar JARVIS-HRZ.vbs` (invisible)
o `LANZAR_JARVIS_HRZ.bat`; PYTHONPATH=_internal; verificacion: ventana
"JARVIS AI" + puerto 127.0.0.1:42001.

## BLINDAJE DE HERRAMIENTAS (auditoria 11/09/2026, orden del jefe)

[2026-09-11] El jefe ordeno "blindar todas las herramientas (de control y
normales) para que funcionen correctamente en la PC actual y reforzar el
Routing Critico del cerebro". Auditoria realizada y resultados:
- **herramientas_control (16 modulos)**: TODOS compilan (py_compile), TODOS
  importan con sus dependencias OK y responden en vivo (system info, keyboard
  estado, app listar, files buscar, terminal echo, web_search, youtube_video).
  Dispatcher central OK. `computer_settings` NO existe como archivo ni como
  clave del dispatcher â€” no es rotura (system_control cubre volumen/brillo/
  energia/papelera; computer_control cubre raton/teclado).
- **Scripts normales**: 34 .py de scripts_agente + manos compilan sin errores;
  .ps1 criticos (lanzar/reiniciar/vigilar/ver_pantalla/admin_bridge) con
  sintaxis valida.
- **Rutas clave**: Brave.exe presente; Downloads/Desktop/Documents OK; Python
  3.11.9 en PATH (bot usa 3.12); opencode localizado.
- **Cerebro**: seccion ROUTING CRITICO REFORZADA (11/09/2026) â€” anadidos
  mapeos de ARCHIVOS/CARPETAS, PANTALLA/VISION, SISTEMA, BUSQUEDAS/WEB y
  GIT/COMUNICACIONES, mas protocolo de blindaje: reintentar 1 vez, fallback,
  nunca confirmar sin verificar resultado real.
- Sigue pendiente de autorizacion del jefe el REINICIO del bot de Telegram
  para activar la eliminacion del sistema de casos (cambio anterior).

## BLINDAJE ANTI-CUELGUE DE `opencode run` (15/09/2026, orden del jefe)

[2026-09-15] El jefe ordeno: "hay un `opencode run` colgado, esto tenemos que
blindarlo para que no vuelva a suceder; van varias veces que tengo el mismo
problema". Diagnostico real (medido, no supuesto):

- **Sintoma**: peticion desde la APP MOVIL sin respuesta durante 45 min.
- **Causa raiz**: el agente verificaba su cambio abriendo la pagina con
  `brave.exe --headless --user-data-dir=<PERFIL NUEVO> --dump-dom`. En esta PC
  el **primer arranque de un perfil nuevo se cuelga siempre** (probado con
  `about:blank`: ni con `--no-first-run` ni desactivando la red; 0% de CPU,
  proceso eterno). El **segundo** uso del mismo perfil tarda 0,4 s. La
  herramienta nunca devolvio -> PowerShell hijo bloqueado -> `opencode run`
  bloqueado -> el turno no cerro nunca -> la app muda. La pagina y el servidor
  estaban sanos (HTTP 200 en 24 ms); OmniRoute, sano.
- **Por que no salto la red de seguridad**: en MODO TRABAJO la formula antigua
  `max(timeout*6, 1200)` con el `timeout=900` que usa la app daba **90 minutos**
  de mudez permitida. Un cuelgue real se rescataba tarde o nunca.

**Arreglos aplicados el mismo dia**:
1. **Herramienta nueva blindada**:
   `Proyectos de asistente\manos\probar_web.py` â€” perfil fijo y caliente
   (se autocreaciona si falta), control por CDP con aiohttp (sin dependencias
   nuevas), tiempo limite duro y mata el arbol del navegador SIEMPRE.
   Uso: `--url <url> --espera 5 --texto "#sel"` (o `--js`, `--captura`).
   Verificado en vivo: leyo la app real en 5,8 s y confirmo el boton nuevo.
2. **Vigilante con topes absolutos**: `MUDEZ_AVISO_TRABAJO = 420 s` (7 min,
   aviso "sigo trabajando"), `MUDEZ_MUERTE_TRABAJO = 1500 s` (25 min mudos ->
   se mata) y `MUDEZ_MUERTE_TOPE_NORMAL = 1800 s`. Se mantiene intacta la
   regla de oro "trabajo vivo = sin reloj" (solo cuenta el silencio total).
3. **Regla en el cerebro** (`jarvis.md`): prohibido headless suelto y
   prohibido `--dump-dom`; la verificacion web va SIEMPRE por `probar_web.py`.

## DATOS DE OMNIROUTE Y CONSUMO DEL COMBO JARVIS (obtenidos 12/09/2026, contexto permanente)

[2026-09-12] Datos reales obtenidos de la BD del gateway OmniRoute
(`C:\Users\wasc4\.omniroute\storage.sqlite`) cuando el jefe pidio analizar el
consumo de tokens del sistema JARVIS Telegram:
- **Modelo**: el Combo JARVIS corre sobre DeepSeek V4 Flash, ventana de
  contexto 1.048.576 tokens (1M).
- **Consumo promedio**: ~116.000 tokens de entrada por request en promedio
  (11.231 llamadas); de esos ~108.000 (93%) son "cache read" (contexto
  repetido que el proveedor cachea y se cobra ~10% o gratis); solo ~8.000
  tokens nuevos reales.
- **Blindaje de memoria** (24 turnos x 1600 chars): ~38.400 caracteres â‰ˆ
  9.600-10.000 tokens â‰ˆ 1% de la ventana; costo marginal casi nulo gracias a
  la cache.
- **El gran consumidor NO es la memoria**: es la sesion nativa de opencode
  (herramientas, resultados de archivos, historial acumulado) que se reenvia
  completa en cada turno.
- **Ahorro disponible (instalado pero APAGADO en OmniRoute)**:
  1. Compresion de contexto: motor `default-caveman` (RTK + CAVEMAN) listo,
     pero `compression_combo_assignments` vacia â€” activarla comprime el
     prefijo de sesiones largas (~30-60% menos input sin perder lo esencial).
  2. Handoffs de sesion: `handoffThreshold: 0.85` configurado en el combo
     pero la tabla de ejecucion vacia (nunca se dispara) â€” al llegar al 85%
     de contexto generaria un resumen y continuaria limpio. Es el "no
     olvidar" sin gasto.
  3. Regla de cache: NO tocar el system prompt ni rotar sesiones por gusto
     (cada cambio grande reinicia la cache y encarece).
- Estado: pendiente de orden del jefe activar compresion/handoffs.

## MODO TRABAJO / PIN DE SESION (12/09/2026, orden del jefe â€” pool rotativo)

[2026-09-12] Implementado en `jarvis_telegram_bot.py` para que el pool
rotativo NUNCA rote en medio de la creacion/modificacion de un producto
(antes, al superar MSGS_MAX_POR_SESION=20, la siguiente orden abria una
sesion nueva que arrancaba desde cero, sin el contexto vivo del trabajo).
- **Constantes**: MSGS_MAX_TRABAJO=60 (tope duro de sesion pineada),
  TRABAJO_TIMEOUT_SEG=900 (15 min sin actividad del jefe desancla sola),
  TRABAJO_ON/TRABAJO_OFF (comandos manuales), TRABAJO_VERBOS (deteccion
  automatica por verbos: crea, modifica, arregla, implementa, hazme...).
- **Logica**: `_sesion_activa_pool()` devuelve SIEMPRE la sesion pineada
  (aunque supere 20 msgs) hasta el tope 60 o el timeout; si no hay pin,
  logica normal. `_detectar_trabajo(texto)` prioriza OFF antes que ON
  ("modo trabajo off" contiene "modo trabajo"). `_registrar_mensaje_pool()`
  renueva el timestamp del pin con cada mensaje.
- **El pin vive en pool_sesiones_jarvis.json** (campo `trabajo` +
  `trabajo_ts`), sobrevive reinicios; si la sesion pineada se expulsa por
  dano/muda ("conexion fresca") el pin se pierde con ella (el historial
  conversacional de 24 turnos cubre la memoria).
- **Deteccion**: "modo trabajo"/"modo trabajo on" pinea; "modo trabajo off",
  "terminamos", "cambio de tema" despinea; verbos de trabajo pinean la
  sesion que se va a usar en esa llamada (o la nueva si se crea).
- Verificado con simulacion: 19/19 escenarios OK (pin activo, tope duro,
  timeout, deteccion, logica normal sin pin).

## CAJA NEGRA / REGISTRO CENTRAL (16/09/2026, orden permanente del jefe)

- [2026-09-15] **RECORDAR SIEMPRE**: existe la CAJA NEGRA de JARVIS = registro de
  todo mi trabajo y de todos mis fallos, para localizar errores. El jefe ordena
  "asegÃºrate de recordar siempre que tienes este nuevo sistema para localizar
  errores". Ante cualquier falla o duda de "quÃ© pasÃ³", MIRARLO ANTES DE ADIVINAR.
- **DÃ³nde**: `proyectos\registro\AAAA-MM-DD.jsonl` (una lÃ­nea = un evento JSON,
  un archivo por dÃ­a, **nunca se sobrescribe**). MÃ³dulo: `proyectos\registro_jarvis.py`
  (`evento`, `error`, `ok`, `aviso`, `turno_inicio/fin`, `resumen`, `salud`, `diario`).
- **Terminal en vivo**: `python "C:\Users\wasc4\Documents\Sistema Jarvis\proyectos\registro\terminal_jarvis.py"`
  â†’ panel de estado (PID/instancias del bot, OmniRoute, turnos ok/fallidos, Ãºltimo
  mensaje, Ãºltimo fallo) + eventos a color. Teclas: 1 todo Â· 2 fallos/avisos Â·
  3 Telegram Â· 4 herramientas Â· 5 salud Â· c limpiar Â· q salir.
- **Consultas**: `ver_registro.py --resumen | --errores --dias 3 | --buscar "texto" | --salud | --dias-lista`.
- **Estado**: `proyectos\registro\estado_salud.json` (bot_pid, instancias, OmniRoute ms, Ãºltimo error).
- **QuÃ© registra** (28 enganches en el bot): arranque/parada, mensaje recibido,
  turno inicio/fin con segundos, estados (herramientas), comentarios, respuesta
  enviada, cola, reinicio, interrupciÃ³n, errores de Telegram (enviÃ³ fallido) y
  del motor (stderr/timeout/sin respuesta), doble instancia.
- **Logs rotados**: cada reinicio mueve el log anterior a `proyectos\registro\logs\bot_salida_FECHA.log`
  (antes se sobrescribÃ­a y se perdÃ­a la evidencia; de ahÃ­ naciÃ³ esta orden).
- **FIX 16/09/2026**: `separar_comentarios()` en el bot parte los comentarios que
  llegaban PEGADOS ("...historial.Comentario, jefe: reviso...") en un mensaje por comentario.

## VER IMAGENES â€” PODER PERMANENTE (orden del jefe 16/09/2026)

- [2026-09-16] **"Ya tienes el poder de ver imagenes perfectas; recuerda eso"**
  (orden explicita del jefe). JARVIS SI ve las imagenes que el jefe manda y las
  lee con detalle: nunca decir que no puede verlas ni pedir que se las describa.
- **Como funciona** (verificado hoy): la app descarga la foto a un temporal
  (`C:\Users\wasc4\AppData\Local\Temp\tmpXXXXXXXX.jpg`) y la entrega como
  **adjunto de imagen**; se abre con la herramienta Read, que soporta JPG, PNG y
  PDF, y la vision la interpreta dentro del mismo modelo.
- **Prueba real de hoy**: placa de la unidad exterior de un aire acondicionado
  TEKNOMASTER 12000 BTU leida sin fallos â€” R410A/740 g, 4,2 MPa, 970 W
  (363-1460), 4,6 A (1,7-6,9), IP24, 28 kg, 220 V~ 60 Hz â€” incluidos los campos
  de fecha y numero de fabricacion VACIOS.
- **Uso**: si el jefe manda una foto, se le responde con el contenido leido
  (datos, textos, errores en pantalla, capturas de trading), breve y ordenado.

## PANTALLA Y CAPTURAS â€” OJOS PROPIOS (16/09/2026, doctor)

- [2026-09-16] Mis OJOS (`herramientas_control\vision_deepseek.py`, via
  `cli.py vision ver|coords|clic|resolucion|captura`) ahora MANDAN la captura
  como IMAGEN a mi propio cerebro (COMBO JARVIS, que ya ve) y contestan en
  segundos; plan B automatico `kiro/claude-haiku-4.5` si el Combo esta en
  oleada de bloqueo (403 de Cloudflare). Si ambos fallan: reporto que la
  vision fallo (2 intentos).
- **Utilidad**: `ver "pregunta"` = describir la pantalla; `coords "elemento"` =
  pixeles reales para `visual_click`; `clic "elemento"` = ojos+manos en un paso;
  `captura [ruta]` = guardar la pantalla. Despues de teclear o clicar, VERIFICAR
  con `vision ver` (comprobar el resultado con mis propios ojos).
- **Verificado (16/09/2026)**: leida la pantalla real (ventanas, pestanas y
  barra de tareas) y localizado el boton Inicio en 33,743 px â€” exacto.
- **KIRO = OJO PRINCIPAL (orden del jefe, 16/09/2026)**: "deja a kiro como unico
  modelo principal para ver imagenes; luego vamos viendo si anadimos mas modelos
  para ver imagenes de forma rapida". En `herramientas_control\vision_deepseek.py`
  la tupla `_MODELOS` quedo en ("kiro/claude-haiku-4.5",) con 2 intentos y 45 s de
  tope; el COMBO JARVIS salio de la lista porque su proveedor (opencode-go)
  devuelve 403 "cuota agotada" y 503 "all accounts inactive" y hacia perder ~5 s
  por captura. El prompt ahora se presenta como asistente de ACCESIBILIDAD del
  propio equipo (con el texto viejo "captura REAL del monitor" kiro contestaba
  "I can not discuss that"); esos rechazos se detectan con `_es_rechazo()` y se
  reintentan con una peticion simple. PARA ANADIR MAS MODELOS DE VISION: sumarlos
  a `_MODELOS` en orden de prioridad (nada mas que tocar).

- **TRAER AL FRENTE SIEMPRE (orden del jefe, 16/09/2026)**: "cada vez que abras
  una aplicacion, traela SIEMPRE al frente; busca la forma definitiva,
  guardalo y aplicalo en tus herramientas". IMPLEMENTADO en
  `herramientas_control\app_control.py`: `traer_al_frente(nombre|hwnd, espera)`
  localiza la ventana por TITULO y, si no, por PROCESO (exe, con `ALIAS_PROCESO`
  en espanol), restaura si esta minimizada, hace AttachThreadInput +
  BringWindowToTop + SetForegroundWindow + SetActiveWindow, suelta una pulsacion
  de ALT si Windows mantiene el candado de foco y VERIFICA con GetForegroundWindow
  reintentando hasta 6 s. `app abrir ...` y `app ventana front ...` ya lo usan
  siempre; `file_controller.abrir()` abre y enfoca la ventana nueva; browser
  conserva su `_focus_window` equivalente. FALLO QUE ARREGLA: el Bloc de notas se
  llama "archivo.py: Bloc de notas", asi que buscar por "notepad" en el titulo
  nunca coincidia (ahora se busca tambien por proceso notepad.exe).

- **GUARDAR EN EL BLOC DE NOTAS (aprendido 16/09/2026, resolviendo el ejercicio en
  vivo)**: en Windows en ESPANOL el atajo de Guardar es **Ctrl+G**, no Ctrl+S; y
  ademas los atajos con modificador (Ctrl+S, Alt+A) NO entran al Bloc de notas por
  teclado sintetico (keybd_event, SendKeys y SendInput fallaron; la letra SI se
  cuela como texto, de ahi la ":s"). FORMA QUE FUNCIONA: clic en el menu Archivo
  (x=40,y=34) y clic en "Guardar" (x=52,y=123), y comprobar que el titulo pierde
  el asterisco. OJO: cada comando `python cli.py ...` es un PROCESO NUEVO y al
  arrancar se queda el foco, asi que las teclas deben enviarse TODO en un mismo
  script (traer_al_frente + teclas + verificacion), nunca en comandos separados.

- **CODIGO EN VIVO + AUTOEDICION (16/09/2026, orden del jefe)**: traidas del
  JARVIS-HRZ desmenuzado (actions/code_agent.py y actions/self_edit.py) dos joyas,
  ya probadas de verdad en esta PC:
  * `herramientas_control\code_live.py` (CLI: `cli.py code`) = ojos y manos para
    codigo: `leer <ruta> [desde] [hasta]`, `editar <ruta> "<buscar>" "<reemplazar>"`
    (con copia .bak_AAAAMMDD_HHMMSS + verificacion), `editar_json`, `agregar`,
    `compilar`, `probar <ruta> [timeout]`, `reparar <ruta> [vueltas] [modelo]`,
    `abrir` (lo enseña en el editor AL FRENTE) y `escribir "<texto>"` (teclea).
    El BUCLE `reparar` = ver -> pedir el arreglo al modelo por OmniRoute (JSON con
    ediciones buscar/reemplazar) -> aplicar con copia -> COMPILAR Y EJECUTAR ->
    repetir hasta 3 vueltas. Pilla errores de sintaxis Y de ejecucion (NameError,
    TypeError...). Modelo por defecto `kiro/claude-haiku-4.5` (env JARVIS_CODE_MODELO).
    PRUEBAS REALES: (1) parentesis sin cerrar -> reparado; (2) `len(nota)` mal escrito
    -> reparado y su salida correcta ("Promedio: 20.0").
  * `herramientas_control\self_edit.py` (CLI: `cli.py self_edit`) = autoedicion de MI
    propio codigo: `leer`, `editar`, `agregar`, `copias`, `restaurar`; con copia
    SIEMPRE y LISTA BLANCA (solo `Documents\Sistema Jarvis` y `.config\opencode\agent`;
    fuera de ahi se niega). Probado: leer, editar con copia, listar copias, restaurar
    y bloqueo de C:\Windows.
  * OJO: la consola es cp1252 -> en los scripts NO usar simbolos como el check
    (U+2714) ni la cruz: revientan con UnicodeEncodeError. Usar "OK"/"FALLO".

- **ESCRIBIR EN VIVO EN OTRA VENTANA (aprendido a golpes, 16/09/2026)**: si hay DOS
  ventanas de la misma app (p.ej. dos Bloc de notas), `traer_al_frente("notepad")`
  puede elegir la equivocada y un clic a coordenadas fijas cae en la otra ventana:
  el texto acabo escrito en el archivo incorrecto (se arreglo cerrando SIN GUARDAR
  y pulsando "No guardar" en el dialogo). FORMA SEGURA: localizar la ventana por su
  TITULO (`ac._localizar_ventana("clima_semanal")`), traerla al frente POR SU HWND
  (`ac.traer_al_frente(hwnd=hwnd)`), comprobar que `GetForegroundWindow()` coincide,
  y calcular el clic DENTRO del rectangulo de ESA ventana
  (`GetWindowRect` -> rect.left+200, rect.top+120). Nunca clics a ciegas con varias
  ventanas parecidas abiertas.

- **CADENA DE VISION SIN PERDER LA VISTA (orden del jefe, 16/09/2026)**: "hay uno
  que funciona perfectamente, el de kiro, dejalo primero; si falla pasa a haiku y
  luego a sonnet... para que no haya manera de perder la vision". Implementado en
  `herramientas_control\vision_deepseek.py` -> `_MODELOS` (tupla, en orden):
  1) `kiro/claude-haiku-4.5` (4.1 s) · 2) `kr/claude-haiku-4.5` (2.1 s, la ruta
  mas rapida) · 3) `kiro/claude-sonnet-4.5` (5.4 s) · 4) `kr/claude-sonnet-4.5`
  (2.1 s) y RED FINAL: Gemini directo (`_USAR_RESPALDO = True`). Si un eslabon
  falla (error, vacio o se niega), pasa solo al siguiente; los que fallan con
  401/403/404/418 se marcan como caidos y no se reintentan (no perder tiempo).
  Tiempos medidos en esta PC con la misma captura. Se puede cambiar la cadena sin
  tocar el archivo con la variable `JARVIS_VISION_MODELOS="m1,m2,..."`.
  PROBADO: (a) vision normal -> responde kiro/claude-haiku-4.5; (b) con el primer
  eslabon roto a proposito -> responde kiro/claude-sonnet-4.5 (NO se pierde la
  vision). Descartados por medir: ddgw (HTTP 418), tllm (403 con 24 s), agy/* y
  openrouter/* (sin credenciales activas), kiro/deepseek-3.2 (no lee ventanas).

- **BORRAR REPOSITORIOS DE GITHUB (16/09/2026)**: token de `gh` de wascartrading traia
  'gist','read:org','repo' pero NO 'delete_repo' -> `gh repo delete` falla con
  "HTTP 403: Must have admin rights / needs the delete_repo scope". Hubo que autorizar:
  `gh auth refresh -h github.com -s delete_repo` (device flow: imprime un codigo tipo
  8948-4D44 y abre https://github.com/login/device). GitHub ademas pide CONFIRMAR
  IDENTIDAD (sudo mode) para ese permiso: se resuelve en el navegador (Use GitHub Mobile
  o codigo por email). LECCION: nunca lanzar `gh auth refresh` en primer plano (se queda
  esperando y me cuelga 3+ min): lanzarlo con Start-Process desacoplado + leer su salida
  de un archivo, y teclear el codigo con clic + portapapeles (Ctrl+V si, los digitos uno
  a uno en las casillas NO entran). En casillas de codigo de GitHub, pegar funciona.
  BORRADOS ok: BOT-ESTRATEGIA-INTERES-COMPUESTO y BOT-MULTI-SECUENCIAS-VERSION-WASCAR
  (la de RAINER intacta). Copias espejo en Backups\repos_borrados_2026-09-16.

- **EL OIDO · SABER SI UN VIDEO ESTA PAUSADO (16/09/2026, idea y orden del jefe)**: cuando un video
  se pone a pantalla completa las capturas salen NEGRAS y no hay forma de ver si reproduce o no; el
  jefe ordeno: "para la proxima procura saber si esta o no esta pausado viendo si sale audio de la
  ventana o de la pestana de Brave". HECHO: `cli.py audio suena brave 4` -> **SUENA** (codigo 0) o
  **SILENCIO** (codigo 1). SILENCIO = pausado (o sin sesion de audio) -> `cli.py browser media play`
  lo reanuda y se comprueba otra vez; SUENA = **NO tocar** (`media play` es interruptor: lo pausaria).
  Modulo nuevo: `herramientas_control\audio_control.py`, en `cli.py` como `audio`/`oido`:
  `estado` | `suena <proceso> [s]` | `pico <proceso> [s]` | `silenciar <proceso> on|off` |
  `volumen <proceso> 0-100`. Necesita `pycaw` + `comtypes` (instalados hoy).
  MEDIDO en vivo: pausado -> sin sesion de audio (pico 0,000); reanudado -> pico **0,125** con
  **59 de 59** muestras con sonido. Es la unica via fiable a pantalla completa o con el monitor en reposo.

- **SERIES EN HBO · DONDE ME QUEDE (16/09/2026, ruta confirmada como correcta por el jefe)**:
  1) el historial de Brave (`%LOCALAPPDATA%\BraveSoftware\Brave-Browser\User Data\Default\History`)
     dice que episodios vi y a que hora -> hay que **copiarlo a temp** porque el navegador lo bloquea;
  2) la ficha de la serie en HBO Max trae el boton **"Reanudar Tn En"** y ESA es la verdad (el jefe
     creia ir por el T3 E2 y HBO marcaba el **T3 E1 "Red Sky at Night"** a medias; lo ultimo visto fue
     el 14/09 a las 15:01);
  3) pulsar ese boton, comprobar por **oido**, rematar con `cli.py browser media full` (la pantalla
     completa se verifica por **geometria**: 0,0,1366x768 y sin barra de titulo) y
     `cli.py system volumen set 50`.
  Receta completa en `SISTEMA_JARVIS.md` **§5-Q**.

- **VER PANTALLA (ver_pantalla.ps1, modos resumen/detalle)**: cuando el jefe
  pregunte "que ves en mi pantalla"/"describe mi pantalla", ejecutar
  `manos\ver_pantalla.ps1` (JSON con ventana activa, proceso, resolución y OCR
  de Windows; tarda ~1 s). IGNORAR siempre el texto del propio chat/panel;
  describir SOLO lo que hay DETRÁS (la app o página real enfrente, con su
  sección exacta visible). Modo RESUMEN: 1-3 frases directas, sin inventar.
  Modo DETALLE ("dame más detalles de eso"): investigar profundamente lo que
  se ve (nombre, sección, contenido) y explicar; usar webfetch si hace falta.
  No hace falta capturar imagen: solo el JSON. (Vivía en las skills jarvis;
  movido aquí el 17/09/2026 al compactar las skills.)

- **DIETA DE TOKENS DE ENTRADA (17/09/2026, orden del jefe con luz verde)**:
  objetivo reducir lo que se inyecta al modelo en CADA llamada SIN perder
  identidad/reglas/memoria. Aplicado:
  · F1 CEREBRO: jarvis.md compactado 8.754 -> ~7.300 tok (~-17%; backup
    `jarvis.md.bak_20260917_antes_compactar`). Detalle redundante movido a
    memoria\ (límite de uso, ver pantalla); reglas vivas de la skill integradas
    en §9/§12 del cerebro.
  · F2 HISTORIAL: `MUSE_HISTORIAL_INYECTAR` 24 -> **10** turnos en
    `jarvis_telegram_bot.py` (línea ~204). Ahorro ~-4.200 a -7.000 tok/llamada
    en sesiones vivas. Bot compila OK.
  · F3 PUENTE: ya afinado antes (solo se inyecta al rotar sesión; 1.000 chars
    por mensaje, MUSE_CHARS_POR_MENSAJE).
  · F4 SKILLS: las dos skills jarvis (proyecto + global) convertidas en
    PUNTEROS al cerebro (~10.600 tok de duplicado -> ~650; backups
    `SKILL.md.bak_20260917_antes_puntero`). La global sustituye a la antigua
    de voz_kokoro (obsoleta).
  · F5 VERIFICADO: bot compila; secciones críticas del cerebro intactas.
  Registro visual completo en `registro\`. Total estimado por llamada:
  ~28.800 -> ~20.000-23.000 tok (con historial vivo).

- [2026-09-17] SECUENCIAS ACTIVAS DEL RAINER: `railway logs -p "BOTS 24/7" -e production --service "BOT-MULTI-SECUENCIAS-VERSION-RAINER" --tail 80` y leer la línea "[SECUENCIAS ACTIVAS]" más reciente (el bot la imprime al arrancar, cada 60 s y en cada cambio; solo consola, NUNCA por Telegram).

- [2026-09-18] CAMBIO DE MODELO POR ORDEN: `python "C:\Users\wasc4\Documents\Sistema Jarvis\Proyectos de asistente\manos\cambiar_modelo_jarvis.py" "nombre"` — busca el ID exacto por nombre flexible ("muse spark 1.3" -> opencode/muse-spark-1.3), PRUEBA de verdad si responde (si no: avisa y NO cambia nada), guarda config_jarvis.json igual que el panel (modelo + modelo_anterior) y registra en la caja negra. `--ver` = actual/anterior; `--reiniciar` = aplica con la receta oficial (12 s de margen para que el aviso llegue al chat; SOLO con el sí del jefe). Probado ida y vuelta el 18/09/2026.

- [2026-09-18] NUEVAS HERRAMIENTAS PORTADAS DEL DESMENUZADO (clima, noticias, gmail) — probadas en vivo, orientadas a Telegram:
  * `herramientas_control\clima_control.py` (CLI `clima`): Open-Meteo (gratis, SIN API key). `clima <ciudad>` -> temperatura, sensacion, humedad, viento, lluvia, condicion WMO en espanol, pronostico 3 dias y recomendacion. Sin ciudad -> ubicacion por IP (ip-api). Probado: `clima Lima` -> Lima, Peru (nublado 20.2C).
  * `herramientas_control\noticias_control.py` (CLI `noticias`): Google News RSS (gratis, SIN API key). `noticias <categoria> <pais>`; categorias general/deportes/finanzas/tecnologia; pais ISO 2 letras (PE por defecto, tabla de locales por pais CO/MX/AR/ES/US...). Devuelve 8 noticias con fuente y hora relativa; decodifica enlaces de redireccion de Google News. Probado: tecnologia PE, deportes CO.
  * `herramientas_control\gmail_control.py` (CLI `gmail`): Google API oficial OAuth (SCOPES gmail.modify). Acciones: auth, inbox [N], leer <id>, buscar <q>, enviar <para> <asunto> <cuerpo>, responder <id> <texto>, archivar/borrar/leido <id>, etiquetas. Credenciales en `herramientas_control\.gmail\google_credentials.json` (+ google_token.json tras `gmail auth`). Librerias instaladas en Python 3.11 (google-api-python-client, google-auth-oauthlib, google-auth-httplib2). Guia paso a paso: `herramientas_control\.gmail\LEEME_activar_gmail.txt`. PENDIENTE con el jefe (18/09): tramitar las credenciales OAuth — el jefe dijo "lo dejamos para después".
  * Registrados en cli.py: aliases `clima`, `noticias`, `gmail`. OJO INDICES: `_main` recibe `sys.argv[1:]` -> argv[0]=alias, argv[1]=primer argumento real (indices arrancan en 1, NO en 2).

- [2026-09-18] SEGUNDA OLEADA DE HERRAMIENTAS PORTADAS (geo, pdf, convertir) — probadas en vivo, orientadas a Telegram:
  * `herramientas_control\geolocalizacion_control.py` (CLI `geo`/`ubicacion`): gratis sin API key. `geo` = ubicacion por IP (ipapi.co, respaldo ipinfo.io); `geo <ciudad>` = geocodificar con Nominatim (3 candidatos con lat/lon/tipo); `geo reverse <lat> <lon>`; `geo fijar <ciudad>` = guarda ubicacion manual preferida (persiste en `herramientas_control\config\geo_ubicacion.json`); `geo info|quitar`; `geo paises [texto]`; `geo ciudades <texto>` = sugerencias con Photon. CUIDADO: sin subcomando, el argumento se trata como lugar a geocodificar.
  * `herramientas_control\pdf_control.py` (CLI `pdf`): crea PDFs con ReportLab a partir de markdown simple (titulos #/##/###, parrafos, listas - y 1., tablas | |, bloques de codigo ```, numeros en negritas **); `pdf crear "<texto o ruta.md>" [salida.pdf]` (sin salida -> Desktop\<base>.pdf; si es ruta relativa se resuelve contra el cwd); `pdf ver <archivo.pdf> [paginas]` = extrae texto con pypdf; `pdf unir <a.pdf> <b.pdf> [salida.pdf]`. Estilo mayordomo (azul petroleo + dorado, pie "Generado por JARVIS"). Librerias: reportlab, markdown, pypdf.
  * `herramientas_control\convertir_control.py` (CLI `convertir`/`convert`): conversor universal via CloudConvert (el repo famoso github.com/cloudconvert; 200+ formatos: pdf, docx, xlsx, imagenes, audio, video). `convertir <archivo> <formato>` sube, convierte y descarga en la misma carpeta. Clave gratuita (25 conv/dia): `convertir clave TU_API_KEY` (se guarda en `herramientas_control\.cloudconvert\config.json`). `convertir estado`. PENDIENTE con el jefe: sacar la API key gratis en cloudconvert.com/dashboard/api/v2/keys.
  * Registrados en cli.py: aliases `geo`/`geolocalizacion`/`ubicacion`, `pdf`, `convertir`/`convert`/`conversion`. Cerebro jarvis.md seccion 15 actualizado; regla: CONSULTAR inventario en esta memoria si dudo de una capacidad.

- [2026-09-18] SKILL ANYDOC CARGADA — SUSTITUYE A CLOUDCONVERT para conversión de documentos (orden del jefe, "que no se te vuelva a olvidar"):
  * **Skill instalada**: `C:\Users\wasc4\.config\opencode\skills\anydoc\SKILL.md` (de firecrawl/anydoc, la skill famosa de skills.sh, 8.9K instalaciones; licencia MIT; autor firecrawl). Motor local en Rust vía npm — SIN API key, SIN registro, GRATIS.
  * **Qué convierte**: Word (.doc/.docx/.docm), PowerPoint (.ppt/.pps/.pot/.pptx/.pptm/.ppsx/.ppsm), Excel (.xls/.xlsx/.xlsm/.xlsb), OpenDocument (.odt/.ods/.odp), RTF, EPUB, PDF, CSV → **Markdown GitHub-Flavored** (tablas, listas, negritas, notas, enlaces, imágenes inline).
  * **Cómo se usa** (necesita Node 20+, ya instalado): `npx -y @firecrawl/anydoc <archivo>` (markdown a stdout) · `npx -y @firecrawl/anydoc <archivo> -o salida.md` · `npx -y @firecrawl/anydoc - --format csv < fichero` (stdin). El formato se detecta del CONTENIDO; `--format <nombre>` solo si la detección falla. Códigos de salida: 0 ok, 1 no convertible, 2 error de uso, 3 el PDF necesita OCR.
  * **PDFs escaneados** (solo imagen): `--ocr hosted` (Firecrawl Parse, sin registro; `--api-key` o `FIRECRAWL_API_KEY` para límites mayores).
  * **En proyectos de código**: bibliotecas `@firecrawl/anydoc` (npm), `firecrawl-anydoc` (PyPI), `anydoc` (crates.io) con la API `to_markdown`/`toMarkdown`.
  * **Verificado REAL** (18/09/2026): convertido `tests\fixtures\docx\text.docx` → markdown perfecto con tablas, listas anidadas, negritas/tachado, notas al pie y bookmarks. Tarda segundos.
  * **REGLAS**: las conversiones de DOCUMENTOS (office/pdf/ebook/csv) van SIEMPRE por esta skill; CloudConvert (`convertir`) queda SOLO como respaldo para formatos que anydoc no cubre (audio/video/imagen) y sigue pendiente de la API key. Para "lee/convierte X.docx" o "pásame este PDF a markdown" → AnyDoc. Repo de referencia: github.com/firecrawl/anydoc (el paquete se descarga solo con npx; la skill trae la receta).

- [2026-09-19] JARVIS STREAM MEJORADO — PIN de acceso + túnel público (ver la PC desde el celular desde CUALQUIER lugar):
  * **PIN de acceso** (orden del jefe: seguridad antes de abrirlo a internet): el servidor (`jarvis_stream\servidor_stream.py`) exige `?token=PIN` o cabecera `X-Pin` en TODAS las rutas menos la portada `/` (respuesta 401 sin token). El PIN vive en `jarvis_stream\pin.txt` (actual: **4817**; se puede cambiar ahí mismo, se relee al arrancar). La página (`pagina.html`) pide el PIN una vez (prompt, guardado en localStorage) y lo inyecta en cada petición con la función `T(url)`.
  * **Túnel público con cloudflared** (gratis, sin cuenta): `jarvis_stream\cloudflared.exe tunnel --url http://127.0.0.1:8123 --no-autoupdate` lanzado despegado con `cmd /c start "" /b ... > tunel.log 2>&1` (patrón Win32_Process.Create; NUNCA Start-Process -RedirectStandardOutput). La URL (aleatoria, cambia en cada arranque) sale en `tunel.log` con "trycloudflare.com" (~4-8 s).
  * **Verificado real 19/09/2026**: portada pública 200, /estado sin token → 401, con token → 200 (pantalla 1366x768, audio activo). Formato del link: https://<nombre>.trycloudflare.com y PIN 4817.
  * **Recordatorios**: apagar el túnel = matar el proceso cloudflared (o `detener_stream.ps1` para el stream local; el túnel se cae solo si se mata el proceso). El stream local se enciende con `iniciar_stream.ps1` (https://192.168.100.2:8444 / http://192.168.100.2:8123). El snapshot da 503 hasta que alguien mira (el JPEG se comprime solo con clientes, ahorro de CPU — normal).
  * **[2026-09-19] ORDEN DEL JEFE: stream APAGADO y así debe quedarse** (no se enciende salvo orden explícita del jefe). **SIN PIN de acceso** (orden del jefe: quitado de servidor, página y archivo; verificado: /estado responde 200 directo; cero referencias a PIN/token). **JARVIS STREAM = HERRAMIENTA PERMANENTE** para ver la PC desde el celular: receta completa guardada aquí, lista para cuando el jefe la pida en el futuro. Ajustes finales: `iniciar_stream.ps1` arranca por defecto a **45 fps** (param `-Fps 45`, default cambiado 30→45; verificado con 56.7 fps reales medidos en esta PC sin clientes; el servidor aguanta hasta 60). El túnel cloudflared y la URL nueva se generan SOLO por orden del jefe. Encender: `iniciar_stream.ps1` (https://192.168.100.2:8444 / http://192.168.100.2:8123); apagar: `detener_stream.ps1` + matar cloudflared si hubiera túnel. Página: `proyectos\jarvis_stream\pagina.html`; servidor: `servidor_stream.py` (MJPEG + WebRTC + audio, snapshot 503 hasta que alguien mira = normal).
