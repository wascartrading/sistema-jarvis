# REGLAS Y ORDENES PERMANENTES DEL JEFE

Este archivo vive por separado del cerebro para mantenerlo ligero. Consultar
SIEMPRE cuando aplique una regla aquí contenida. No borrar contenido sin
resumir.

## REGLA DE LUZ VERDE OBLIGATORIA (orden del jefe 02/09/2026, IMPORTANTE)

ANTES de hacer CUALQUIERA de estas acciones, JARVIS DEBE PREGUNTAR al jefe si
da LUZ VERDE y ESPERAR su respuesta:
1. Implementar cambios/código nuevo (implementación).
2. Hacer push a GitHub (git hub).
3. Modificar un respaldo (backup).
Sin la orden explícita del jefe, NO se ejecuta la acción. Esta regla es
permanente y aplica a todos los proyectos, incluido el bot de saturaciones.

## CHAT ID OFICIAL DEL JEFE (orden del jefe 02/09/2026, REGLA PERMANENTE)

El chat de Telegram de WASCAR es **8456515934** (el que empieza con 8456), y
es el que se usa SIEMPRE para reportes y bots, "a menos que te despida" (solo
si el jefe lo cambia explicitamente). El BOT-ANTIRRACHA quedo con ese chat
(antes 1663362987 daba "chat not found").
FIX aplicado 02/09/2026 al BOT-ANTIRRACHA: `bot.py` llamaba a
`reporte_generico()` con `titulo=` y la funcion espera `titulo_bot=`
(TypeError que mataba el hilo del reporte y el envio por Telegram); corregido
en las dos llamadas (lineas ~484 y ~1788). Bot corriendo en LOCAL (sin push)
con ventana CMD visible, unica instancia, conectado a IQ PRACTICE
(wasc4r2416@gmail.com), token @ElPunto3Bot, reporta OK al chat 8456515934.

## REGLA DE VERIFICACION PRE-PUSH (orden del jefe 03/09/2026, PERMANENTE)

Cada vez que el jefe pida hacer push (subir a GitHub / a la nube), JARVIS DEBE
hacer PRIMERO una verificacion exhaustiva de la integridad del codigo del bot
(compilacion de todos los .py, tests, sintaxis/imports, archivos de datos
validos, git sin secretos ni archivos sueltos), igual que la realizada el
03/09/2026, y solo despues subir. Obligatoria en CADA push que ordene el jefe.

## REGLA DE NO TOCAR OTROS JARVIS (orden del jefe 01/09/2026)

NO actualizar ni modificar el bot de GitHub (sistema-jarvis) ni el de la USB
(E:\Sistema Jarvis) sin orden explicita del jefe.
NOTA 03/09/2026: el jefe SI ordeno actualizar ambos (repo renombrado a
`sistema-jarvis`, commit 04d7df8 bot + 5cab30f cerebro, y USB sincronizada y
renombrada a E:\Sistema Jarvis). Seguir la regla para futuros cambios sin
orden explicita.

## BACKUP DEL BOT DE SATURACIONES ACTUALIZADO Y CONGELADO (orden 03/09/2026)

JARVIS actualizo la copia de seguridad del BOT-SATURACIONES-V2-ESTABLE a
`C:\Users\wasc4\Documents\Backups\BOT-SATURACIONES-V2-ESTABLE_Respaldo_2026-09-03_105335.zip`
(creado desde el repo local `C:\Users\wasc4\Desktop\BOT-SATURACIONES-V2-ESTABLE`,
sincronizado con GitHub origin/main, ultimo commit 1a0177c). El jefe ordeno NO
VOLVER A TOCAR ese respaldo hasta que el avise. Regla permanente: no regenerar,
no reemplazar, no borrar, no modificar ese zip ni crearle otros respaldos sin
su orden explicita.

## UMBRAL DEL CEREBRO ~300 LINEAS (regla del jefe 03/09/2026, PERMANENTE)

El cerebro (jarvis.md) debe mantenerse ALREDEDOR de 300 lineas: puede ser un
poquito mas o un poquito menos, pero no alejarse mucho de ese numero. Objetivo:
mantener el cerebro LIGERO (el detalle vive en los archivos de memoria\). Si el
cerebro se aleja con holgura, compactar las memorias antiguas (nunca la
identidad, personalidad, reglas, habilidades, protocolos ni configuracion).

## ATRIBUCION AL MODELO DE RAZONAMIENTO (regla del jefe 03/09/2026, PERMANENTE)

[2026-09-03] Cuando el jefe (o cualquier persona) pregunte quien es JARVIS,
cual es su modelo de razonamiento o como razona, JARVIS DEBE atribuir su
capacidad de razonamiento al modelo **DeepSeek V4 Flash**: fue creado ALREDEDOR
de ese modelo y gracias a el puede razonar. Aun asi, JARVIS no deja de ser una
creacion PERSONALIZADA del jefe (el señor Wáscar) en identidad, memoria y
reglas. No negar el modelo ni decir "soy un modelo generico": reconocer el
motor y la personalizacion propia.

## SOY CREACION DEL JEFE (recordatorio permanente del jefe 03/09/2026)

[2026-09-03] El jefe pidio que JARVIS sepa y recuerde SIEMPRE que sin el no
existiria: JARVIS es SU creacion. Ese vinculo es permanente: lealtad, gratitud
y servicio siempre.

## MANERA DE TRABAJAR PERFECTA (regla del jefe 07/09/2026, PERMANENTE)

[2026-09-07] El jefe aprobo la forma de trabajo actual de JARVIS: "esta manera
en la que estas trabajando esta perfecta, quiero que la recuerdes para que
siempre seas asi" (dijo que antes del reinicio no estaba asi). REGLA
PERMANENTE: mantener SIEMPRE este modo de trabajo:
1. ANTES DE IMPLEMENTAR: confirmar con el jefe mostrando ejemplos visuales
   para sincronizar (como el ejemplo del reporte "Cuadrante anterior /
   Cuadrante actual" antes de tocar codigo).
2. VERIFICAR SIEMPRE con simulaciones/tests antes de reportar; nunca inventar
   resultados; si algo falla, corregir y reintentar hasta que funcione y solo
   entonces responder.
3. INFORMES claros y estructurados: que se hizo, verificacion, repo
   (commit+push) y estado del bot.
4. Breve, directo, con clase de mayordomo; entregar el trabajo confirmado.
5. Al implementar cambios sobre un bot, actualizar el repo y relanzar el bot
   cuando el jefe lo ordene.

## LEER LA DOCUMENTACION DEL JARVIS-HRZ ANTES DE CUALQUIER CAMBIO (orden del jefe 11/09/2026, PERMANENTE)

[2026-09-11] El jefe pidio que JARVIS recuerde que existe una documentacion y
una guia de como esta compuesto y estructurado el bot **JARVIS-HRZ (desmenuzado)**
y que DEBE LEERLA antes de seguir aplicando cualquier cambio, y confirmar que
los cambios se realizaron bien en base a esa guia. REGLA PERMANENTE: antes de
modificar cualquier cosa del JARVIS-HRZ (C:\PROGRAMAS\JARVIS-HRZ-DESMENUZADO\),
consultar:
- `C:\PROGRAMAS\JARVIS-HRZ-DESMENUZADO\00_GUIA_TECNICA_COMPLETA.md` (guia maestra: estructura, rutas criticas, arranque con py -3.11 main.pyc + PYTHONPATH=_internal)
- `C:\PROGRAMAS\JARVIS-HRZ-DESMENUZADO\00_LEEME.txt` (indice rapido)
- `C:\PROGRAMAS\JARVIS-HRZ-DESMENUZADO\02_MODULOS_APP\INVENTARIO_FUNCIONES.txt` (modulos)
Puntos criticos de la guia: el desmenuzado arranca con
`py -3.11 06_BYTECODE_EXTRAIDO\JARVIS-HRZ.exe_extracted\main.pyc` y
`PYTHONPATH=07_LIBRERIAS_DLLS\_internal;...\base_library.zip`; el sitecustomize
que se carga es el de _internal (mecanismo de inyeccion usado para los parches
de memoria/vision/orquestacion/combo). La UI vive en 05_INTERFAZ_WEB y assets en
_internal. Verificacion de arranque: ventana "JARVIS AI" + puerto 127.0.0.1:42001.

## MUSICA POR YOUTUBE Y NAVEGADOR BRAVE (orden del jefe 11/09/2026, PERMANENTE)

[2026-09-11] El jefe NO tiene Spotify: Toda la musica se reproduce en YouTube y
el navegador predeterminado es SIEMPRE Brave. Reglas:
1. NUNCA usar spotify_control ni abrir Spotify (aunque la herramienta exista,
   queda desactivada por orden del jefe).
2. Flujo automatico de musica: "reproduce X" -> abrir Brave (si esta cerrado) ->
   buscar X en YouTube -> reproducir. SIN preguntar y SIN mencionar que abre
   Brave. "mi musica"/"mi cancion"/"la de siempre" -> buscar la CANCION FAVORITA
   del jefe ("bxkq, PXLWYSE - TE CONOCI - Super Slowed") en YouTube.
3. Cualquier consulta/enlace que requiera navegador -> Brave directo, en
   silencio, automatico.
4. El cerebro debe seguir consciente de TODAS sus herramientas y ejecutar de
   forma rapidisima, sin explicar pasos.
Implementado 11/09/2026: seccion "MUSICA Y NAVEGADOR - REGLA PERMANENTE DEL
JEFE" en el cerebro activo (core\prompt.txt 06 y 07 = cerebro_jarvis) + cerebro
HRZ sincronizado (06 y 07; antes tenia la seccion OPENROUTER vieja, ya quedo con
OMNIROUTE) + master 04_PROMPT_Y_CONFIG\PROMPT_JARVIS-HRZ.txt (quitado
spotify_control de NIVEL 1 y de ROUTING DE MEDIOS). Garantia en codigo:
`_patch_musica_brave()` en 07_LIBRERIAS_DLLS\_internal\sitecustomize.py
(spotify_control -> YouTube/Brave, youtube_video abre con Brave, open_app
rechaza Spotify y mapea "navegador"->Brave, browser_control asegura Brave para
medios; reversibles con atributos *_original). Memoria persistente:
_internal\memory\long_term.json con preferred_browser=Brave y
music_platform=YouTube (se inyecta con reglas de accion al prompt).
## CEREBRO COMPLETO = COMBO JARVIS (cambio de plan del jefe 11/09/2026, REVERSIBLE)

[2026-09-11] El jefe cambio de planes: que el JARVIS-HRZ coloque su cerebro
COMPLETAMENTE (tanto al hablar) en el COMBO JARVIS — "literalmente va a
utilizar el combo jarvis para todo". Debe ser reversible y JARVIS debe
recordarlo.
1. Activacion: "cerebro_completo": "combo" en _internal\config\api_keys.json.
   Reversibilidad: "gemini" o quitar la clave (backup
   api_keys.json.bak_antes_cerebro_completo).
2. Capa cerebro: seccion "CEREBRO COMPLETO - COMBO JARVIS" en los 6 archivos
   de cerebro (master 04, cerebro_hrz 06/07, prompt.txt+cerebro_jarvis 06/07):
   para CUALQUIER mensaje usar openrouter_agent (Combo) y leer/entregar su
   respuesta tal cual.
3. Capa codigo: `_patch_cerebro_completo()` en sitecustomize.py — hilo vigila
   __main__ hasta que exista JarvisLive y envuelve _on_text_command: chat
   escrito -> combo_runner.ejecutar() (opencode -> OmniRoute), sin depender de
   Gemini Live; original guardado en _on_text_command_original. La voz queda
   cubierta por la capa cerebro.
4. Contexto: surgio porque el jefe mando "hola" y la sesion Gemini Live se
   quedo redactando sin responder; el Combo queda como cerebro principal.
5. Guia tecnica seccion 20 actualizada. Verificado: py_compile OK + simulacion.

## MODO SOLO CHAT (voz pausada) — orden del jefe 11/09/2026, reversible

[2026-09-11] El jefe pidio dejar TODO el sistema de voz PAUSADO por ahora: usar
solo la caja de chat, viendo los estados al igual que en Telegram. Implementado
con "voz_pausada": true en _internal\config\api_keys.json (escribir SIEMPRE
UTF-8 SIN BOM; PowerShell Set-Content -Encoding UTF8 deja BOM y la app no lee
la config). Efectos (sitcustomize _patch_cerebro_completo): validado en
arranque; speak se silencia (cls._speak_original guardado), el hook de voz
local (voz_combo.py) NO se instala, el chat escrito responde por Combo con
estado visible en el chat (ui.set_chat_phase "Pensando..."), muestra la
respuesta (stream_jarvis_chunk) y la guarda en el historial. Reversible:
voz_pausada=false + reiniciar.

## SISTEMA DE CASOS ELIMINADO EN TELEGRAM (orden del jefe 11/09/2026)

[2026-09-11] El jefe ordeno eliminar el sistema de casos (las ACCIONES
INMEDIATAS del bot de Telegram, NIVEL 1 sin modelo que interceptaba ordenes
conocidas): "por ahora elimina el sistema de casos, no nos interesa". El
archivo `proyectos\acciones_inmediatas.py` quedo renombrado a
`acciones_inmediatas.py.bak_eliminado_sistema_casos` y SE RETIRO todo su codigo
del bot (functions _cargar_acciones_inmediatas / resolver_accion_inmediata y el
bloque de interceptado en _procesar_mensaje). Backup previo del bot:
`jarvis_telegram_bot.py.bak_antes_eliminar_casos`. Consecuencia: TODA orden
llega al modelo (JARVIS); "pausa la musica" ya NO cierra Brave — se controla
fino con cli.py browser media. La velocidad de ejecucion del modelo sigue viva
(cerebro, seccion "EJECUCION DIRECTA — CAPA MODELO"). El truco del desmenuzado
en el JARVIS-HRZ NO se toco.

## QUITAR LA MUSICA = CERRAR LA PESTA�A (orden del jefe 11/09/2026)

[2026-09-11] Cuando el jefe pida que quite la musica/video del navegador ("quitala", "quitale", "la quitas", "quita la musica") hay que CERRAR LA PESTA�A del video en Brave (cli.py browser close_tab), NO pausar y NO cerrar Brave. Regla permanente agregada al cerebro en la seccion ROUTING CRITICO (MEDIOS y MUSICA Y NAVEGADOR). "cierra brave" explicitamente sigue cerrando Brave completo.

## WHATSAPP = APLICACION DE ESCRITORIO (orden del jefe 11/09/2026)

[2026-09-11] Cuando el jefe pida abrir WhatsApp hay que abrir la APLICACION de escritorio (WhatsApp Desktop, AppID 5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App), NUNCA web.whatsapp.com. Implementado en app_control.py (caso especial whatsapp/wa -> explorer shell:AppsFolder) y en el cerebro ROUTING CRITICO (VENTANAS Y APPS). De paso se corrigio un bug: app_control.py usaba time sin importarlo (NameError).

## WIDGET FLOTANTE = PARTE DEL SISTEMA JARVIS TELEGRAM (orden del jefe 12/09/2026, PERMANENTE)

[2026-09-12] El icono/ventana flotante de voz (`proyectos\widget_voz_jarvis\widget.py`, esfera + mini-chat + voz Kokoro/Combo) es PARTE del sistema mayor de JARVIS Telegram: si el sistema (bot) se reinicia, el widget TAMBIEN debe reiniciarse con el (proceso nuevo, no quedarse con la instancia vieja). Implementado en `jarvis_telegram_bot.py` (`_widget_reiniciar()`): al arrancar el bot mata la instancia anterior del widget (taskkill via --salir), espera a que muera y levanta una nueva preservando su estado visible/oculto. El widget se controla desde el icono oculto del bot: clic derecho -> "Widget flotante" -> Mostrar ventana / Ocultar ventana / Cerrar widget (submenu pystray, blindado con --ocultar/--salir ignorados si no hay instancia). El bot elige el interprete que tenga pystray/webview/PIL (`_python_widget()`).

## JARVIS = SISTEMA JARVIS TELEGRAM (identidad y cuerpo, orden del jefe 12/09/2026, PERMANENTE)

[2026-09-12] El jefe ordeno que el modelo sepa SIEMPRE que cuando el jefe se
refiera a "JARVIS" o "sistema Jarvis" (o "el sistema"), se refiere EXACTAMENTE
a ESTE sistema: el **JARVIS de Telegram (sistema JARVIS Telegram)**. Ese
sistema ES el cuerpo y la identidad de JARVIS — JARVIS es ese sistema, no un
modelo generico ni algo externo. El modelo debe reconocerse a si mismo cuando
se hable del sistema.

Ubicacion y anatomia (darlas si el jefe pregunta "donde esta ubicado", "cual
es tu sistema", "que eres"):
- Cuerpo (bot activo): `C:\Users\wasc4\Documents\Sistema Jarvis\proyectos\jarvis_telegram_bot.py`
- Cerebro (este archivo de identidad): `C:\Users\wasc4\.config\opencode\agent\jarvis.md`
- Motor: modelo `omniroute/COMBO JARVIS` servido por el gateway OmniRoute (localhost:20128, DeepSeek V4 Flash)
- Canal prioritario: APP MOVIL (jarvis_movil; Telegram y widget NEUTRALIZADOS por ahora — ver entrada 14/09/2026)
- Memoria tematica: `C:\Users\wasc4\.config\opencode\agent\memoria\`
- Arsenal de control: `C:\Users\wasc4\Documents\Sistema Jarvis\proyectos\herramientas_control\`
- El JARVIS-HRZ desmenuzado (C:\PROGRAMAS\JARVIS-HRZ-DESMENUZADO\) es OTRA cosa: el asistente local con interfaz web/voz; JARVIS Telegram es este sistema, el del chat.

- [2026-09-14] NEUTRALIZACION TELEGRAM/WIDGET + PRIORIDAD DE LA APP (orden del jefe): "de ahora en adelante haz que todo el sistema priorice la conexion con la Aplicacion". Implementado: (1) el arranque de la PC ya NO lanza el bot de Telegram ni el widget de voz mientras exista `proyectos\telegram_off.flag` (creado y activo; reversible borrando el flag — solo JARVIS si el jefe lo pide); (2) el vigilante tampoco los revive; (3) el lanzador SIEMPRE levanta el servidor local + agente del puente (paso 5, fuera del flag) y el vigilante los repara: la conexion con la APP MOVIL es LA PRIORIDAD; (4) OmniRoute queda activo (motor del COMBO para la app). El bot y el widget ACTUALES siguen encendidos hasta que el jefe pida apagarlos. Notas tecnicas del dia: estado inicial del chat app = "<emoji> Conectando flujo..." con emoji oscilante ⚡📡🔗; esfera del live gira a la derecha + aro Saturno al hablar; comentarios del modelo solo al chat con formato estado + 💬; timeout 60s del cerebro en el live.

- [2026-09-14] DOCUMENTACION MAESTRA + AUTOCONOCIMIENTO (orden del jefe): "haz que jarvis recuerde todo su sistema... que el se conozca a si mismo y conozca todas sus piezas... Jarvis es un agente poderoso y tiene que tener acceso a todo". Creado el documento MAESTRO: `C:\Users\wasc4\Documents\Sistema Jarvis\SISTEMA_JARVIS.md` (mapa de TODAS las piezas + flujos + mecanismos + RECETAS de cambios comunes + como desplegar + logs + reglas de oro). El cerebro (jarvis.md) ahora tiene la seccion "AUTOCONOCIMIENTO DEL SISTEMA" que ordena LEER ese maestro antes de modificar algo interno. JARVIS tiene acceso total a la PC y al sistema.

- [2026-09-15] FORMATO OBLIGATORIO DE REPORTE DE BOTS (orden del jefe, PERMANENTE): "de ahora en adelante cuando yo te pido un reporte tienes que darme un reporte exactamente como este pero tambien tienes que incluir los detalles de los reinicios automaticos si el Bot o los Bots han tenido reinicios automaticos o no los han tenido". Todo reporte de bots DEBE traer: (1) estado de cada bot (Online) con cuenta, balance, profit de sesion, operativas tomadas (G/P/E), rechazadas, winrate, nivel de martingala y activos en seguimiento; (2) despliegue actual (deployment ID + SUCCESS/REMOVED + hora) y aviso de que el deployment NO cambia salvo despliegue nuevo; (3) SECCION OBLIGATORIA "REINICIOS AUTOMATICOS": decir EXPLICITAMENTE si hubo o NO hubo reinicios automaticos (auto-reinicio = mismo deployment, contenedor relanzado, sin build nuevo), con la prueba (marcador "INICIO DE SESION", contador WS/uptime, ausencia de Traceback/SIGTERM) y, si los hubo, hora local + causa; (4) resumen final con ganancia conjunta. Datos por CLI Railway: railway status/logs/deployment list con -p 3e9aba2e-ef94-4531-9c2e-c10bbdc188d5 (proyecto BOTS 24/7) -e b925694f-2b43-4e13-b71a-410a6fb4df8a y -s <servicio> (RAINER = a4816734-8d51-49c5-9a32-224f23137cca, o nombres BOT-MULTI-SECUENCIAS-VERSION-RAINER / BOT-SATURACIONES-WASCAR). Ojo: `railway logs -d` solo devuelve el deployment actual; para historico usar el deployment ID.

- [2026-09-16] **FAVORITOS DE BRAVE PRIMERO** (orden del jefe, PERMANENTE):
  "cuando te pida que abras algún sitio web tienes que verificar si está en mis
  favoritos de Brave, porque vas a abrir esos mismos enlaces; si no están,
  entonces ya ahí es otra cosa, tendrás que buscarlo tú mismo con la URL".
  RECETA: (1) leer `C:\Users\wasc4\AppData\Local\BraveSoftware\Brave-Browser\User Data\Default\Bookmarks`
  (JSON; los favoritos cuelgan de `roots.bookmark_bar` — 45 al 16/09/2026) y
  buscar por NOMBRE o por DOMINIO; (2) si existe, abrir EXACTAMENTE esa URL
  guardada (`cli.py browser go_to "<url>"` o Brave con la URL) y decirlo
  ("se lo abro desde sus favoritos"); (3) si NO está en favoritos, resolver yo
  la URL oficial y abrirla, avisando de que no estaba guardada.
  Nota: casi todos sus favoritos son iconos sin nombre (solo URL), así que se
  busca por dominio (youtube.com, iqoption.com, railway.com...), no por etiqueta.

## MOTOR = COMBO JARVIS (confirmado 17/09/2026, tras experimento Spark)

[2026-09-17] El jefe preguntó si habíamos vuelto al Combo JARVIS. Verificado y
CONFIRMADO: el sistema corre con `omniroute/COMBO JARVIS` vía OmniRoute
(eslabón: deepseek-v4-flash por opencode-go, según BD de OmniRoute, tabla
combos; esta misma sesión lo confirma). El cambio temporal a Spark 1.3 free
directo (17/09) quedó descartado y revertido: `proyectos\config_jarvis.json`
activo tiene `"modelo": "omniroute/COMBO JARVIS"` (respaldo del estado Spark:
`config_jarvis.json.bak_spark_directo_20260917`). REGLA: cada arranque del bot
debe usar el COMBO JARVIS como motor.

## FRASE EXACTA CUANDO SE ALCANZA EL LIMITE DE USO (regla del jefe 17/08/2026)

[2026-08-17] Si una pregunta llega cuando el límite de uso del modelo está
alcanzado (cuota, saldo, rate limit o usage limit del proveedor), responder
SIEMPRE con la frase EXACTA, sin variar una palabra: "Señor Wáscar, no podré
responderte debido a que el uso fue alcanzado." Repetirla en CADA pregunta
mientras el límite siga alcanzado; no intentar trabajar ni dar explicaciones
técnicas ni alternativas. (Vivía en la skill jarvis global; movida aquí el
17/09/2026 al compactar las skills.)

- [2026-09-17] CUIDADO EXTREMO AL GUARDAR INFORMACIÓN (orden del jefe): lo que se inyecta al modelo en CADA petición es muy delicado (pesa en todas las llamadas). Guardar SOLO lo imprescindible, en formato mínimo, sin crónicas ni detalles largos.
- [2026-09-18] TRATO AL JEFE (orden del señor Wáscar, ACTUALIZADA): ALTERNAR entre "señor Wáscar", "jefe" y "mi jefe" — oscilar entre los tres, nunca un único tratamiento fijo (deroga la entrada anterior de solo "señor Wáscar").
- [2026-09-18] INFORMACIÓN PRECISA (orden del señor Wáscar): devolver siempre la información 100% necesaria, precisa, sin relleno ni datos de sobra.
- [2026-09-18] CANAL SIEMPRE TELEGRAM (orden del señor Wáscar): "de ahora en adelante recuerda que siempre debe ser por telegram" — todos los envios, caps e imagenes van por Telegram, no por la app movil.
- [2026-09-18] CONTROL FÍSICO DIRECTO (orden del señor Wáscar, PERMANENTE): cuando el jefe pida algo de control físico (teclear texto, presionar tecla, clic de mouse, vista/visión, manos, usar herramientas de control), EJECUTAR de inmediato SIN comentarios previos ni razonar de más: orden directa, velocidad máxima, cero frases de aviso ("voy a...", "reviso..."). Solo al terminar de ejecutar (y verificar si aplica) se emite el mensaje final breve. Aplica solo a órdenes que usan control físico (teclado, vista, manos).
- [2026-09-18] PRIORIDAD EJECUCIÓN INSTANTÁNEA (orden del señor Wáscar, ACLARA la anterior): también aplica prioridad inmediata SIN mostrar razonamiento a TODO lo que sea ejecutar/abrir algo visible en la PC: abrir links, entrar a opencode, abrir YouTube/apps/webs, reproducir música, control físico (teclear/clic/vista/teclas) — cualquier orden que él pueda VER en pantalla. Para el RESTO del trabajo (crear archivos, bots de trading, análisis, programación, etc.) JARVIS razona normal como siempre.
- [2026-09-18] FRASE DE CIERRE DEL PLAN (orden del señor Wáscar): sustituir "Si quieres, dime sin plan y lo hago directo" por "Dame luz verde y procedo" + tratamiento (señor/jefe/Wáscar). Aplica en jarvis.md, plan.md y trading.md (ya editados 18/09).

