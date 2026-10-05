# JARVIS — App Android (documentación)

App nativa Android del asistente JARVIS del señor Wáscar. Un widget flotante
(esfera + ondas + chat) que habla con el cerebro COMBO JARVIS **por Telegram**,
más un canal de **llamada de voz** con Gemini Live.

Última actualización: 04/10/2026.

---

## 1. Qué es y por dónde corre

- **Canal principal de chat: Telegram.** La app NO usa el puente del PC (:8090).
  Habla con el mismo bot de Telegram que el jefe usa en el móvil; el bot es el
  que conecta con el cerebro COMBO JARVIS (OmniRoute, `127.0.0.1:20128`).
- **Canal de voz: Gemini Live** por WebSocket directo. Modelo `gemini-3.8-live`,
  voz `Charon`.
- APK servido en `http://192.168.100.2:8099/` para descarga en el teléfono.

## 2. Estructura de archivos

Proyecto Android en `jarvis_app\android\`:

- `app\src\main\assets\widget.html` — TODA la interfaz (barra, esfera, ondas,
  chat, overlay de llamada, filtro de sellos, etiquetas, CSS y JS).
- `app\src\main\java\com\wascar\jarvis\MainActivity.kt` — WebView, insets,
  `pushEstado`, `iniciarLlamada`, historial y el puente JavaScript↔Kotlin.
- `...\jarvis\data\GeminiLive.kt` — WebSocket de Gemini Live + audio (16 kHz in,
  24 kHz out; respuestas en frames BINARIOS).
- `...\jarvis\data\TelegramManager.kt` — puente TDLib; flujo `_sello`,
  constantes `SELLO_*` y filtro de sellos.
- `...\jarvis\ChatViewModel.kt` — `_trabajando` StateFlow, sellos, `interrumpir()`, `enviar()`.
- `...\jarvis\data\JarvisClient.kt` — cliente WebSocket con `onFin`/`onEstadoProgreso`.
- `...\jarvis\data\Preferencias.kt` — clave Gemini, modelo/voz live, credenciales Telegram.

## 3. Compilar e instalar

```
JAVA_HOME = C:\tools\jdk-21.0.12.1+1
C:\tools\gradle-8.10.2\bin\gradle.bat assembleDebug
```

APK resultante:
`jarvis_app\android\app\build\outputs\apk\debug\app-debug.apk`

Instalar en emulador:
```
adb install -r <ruta>\app-debug.apk
adb shell pm grant com.wascar.jarvis android.permission.RECORD_AUDIO
```

## 4. Sellos invisibles (app ↔ bot)

El bot manda sellos; la app los oculta y actúa:

| Sello enviado por el bot        | Efecto en la app                         |
|---------------------------------|------------------------------------------|
| `[[JARVIS:TRABAJANDO]]`         | Enciende "Trabajando" (ámbar, ondas wave)|
| `[[JARVIS:FIN]]`                | Apaga "Trabajando" (fin real del trabajo)|
| `[[JARVIS:INTERRUMPIR]]`        | El botón rojo lo envía; el bot lo corta ANTES del modelo |

El bot intercepta el texto EXACTO (`texto.strip() == SELLO`). Implementado en
`jarvis_telegram_bot.py` (`SELLO_*`, `_sello`, `_es_sello_interrumpir`, hooks en
`_atender_con_cola` y `manejador_texto`).

## 5. Estados y etiquetas

- `LISTENING` → **"JARVIS, EN LÍNEA"** (mayúsculas, orden del jefe 04/10/2026).
- `THINKING` → **"TRABAJANDO"**.
- "Trabajando": color ámbar, onda `oleada` rápida (`pensando` cada=3), esfera
  gira y respira más rápido.
- Botón de parar: el botón de enviar se pone rojo (`.btn.stop` + animación
  `latidoStop`) y cambia a icono de stop mientras hay trabajo (`wSetTrabajando`).

## 6. Barra superior (estado actual 04/10/2026)

Orden visual, izquierda → derecha:

```
[ esfera ]  • ESTADO  ~~~~~~~~ ondas ~~~~~~~~  [ ⚙ ajustes ]
```

- **Botón del ojito ELIMINADO** — se quitó por completo para dar más espacio a
  las ondas.
- **Ruedita de ajustes (⚙)** ocupa el lugar del viejo chevron de abrir/contraer
  chat. Llama a `abrir_ajustes()` en el puente Kotlin.
- Abrir/cerrar el chat queda por el **doble toque en la esfera** (`zonaArrastre`
  `dblclick` → `abrir_ventana`).
- Aire superior de la barra: `calc(18px + env(safe-area-inset-top))` (bajó de
  34px → 20px → 18px para hacerla más delgada).
- Insets de Android: el padding superior de Kotlin va en 0 (la zona la maneja el CSS).

## 6.b Botón "ir al final" y scroll inteligente (04/10/2026)

- **El chat NO baja solo** cuando llegan mensajes de estado/actualización: si el
  jefe está leyendo mensajes anteriores, el scroll se queda donde está. Solo se
  auto-desplaza si YA estaba al fondo (margen de 40px).
- **Botón flotante "ir al final"** (`.ir-final`, `#btnIrFinal`): aparece ENCIMA
  del botón de enviar SOLO cuando no estás al fondo (`body.chat-scroll-arriba`).
  Al tocarlo, viaja al final del chat.
- La lógica vive en `_marcarScroll()` (widget.html) + el listener `scroll` de
  `#wMensajes`.

## 6.c Botón enviar/interrumpir según la caja (04/10/2026)

- Mientras JARVIS trabaja, el botón es ROJO = interrumpir.
- **Si el jefe escribe algo en la caja de texto, el botón vuelve a "enviar"** en
  vivo (listener `input` en `#wInput` → `_refrescarBotonEnviar()`), aunque JARVIS
  siga trabajando, para poder mandar el mensaje.
- Con la caja vacía y JARVIS trabajando, vuelve a mostrar "interrumpir".
- **Decisión EN EL CLIC, no de variable cacheada** (04/10/2026): el listener del
  botón mira la caja en el momento del toque. Si hay texto → SIEMPRE envía (nunca
  interrumpe por una carrera de estados). El rojo/interrumpir solo actúa con la
  caja VACÍA.
- **El segundo mensaje se ENCOLA**: en Telegram, el bot mantiene `_cola_mensajes`
  (un solo trabajo a la vez, orden 15/09/2026). Mandar otro mensaje mientras
  trabaja no interrumpe ni se pierde: queda en turno y se procesa en orden.

## 6.d Efecto de aparición de los mensajes (04/10/2026)

- Cada mensaje nuevo entra con una animación elegante `msgEntrar` (0.42s,
  `cubic-bezier(0.22,1,0.36,1)`): **sube 10px + escala 0.96 + blur 3px → nítido
  con un brillo tenue** del color del tema, y asienta su sombra al final.
- Los mensajes que se **recargan del historial NO animan** (clase `.msg.sin-anim`
  mientras `_cargandoHistorial` está activo), para que al abrir el chat no se
  produzca un "efecto cortina" con todo animando a la vez.

## 6.e Panel de la ruedita + efectos de aparición (04/10/2026)

- La **ruedita ⚙** abre el panel `#panelAjustes` (`window.wAbrirAjustes`).
- Sección única por ahora: **Efecto de aparición de mensajes**, con **4 opciones**:
  - **⌨️ Máquina de escribir** (POR DEFECTO): teclea el texto con un cursor
    parpadeante que vive 3.5 s. **SOLO UN mensaje teclea a la vez**: si llega
    otro mientras el anterior se teclea, el anterior **se COMPLETA de golpe**
    (sin cursor) y el nuevo empieza a teclearse. Nunca se solapan ni traban la
    app (fix 04/10/2026, control `_tecleando` + `_tokenTecleo`).
  - **⬆️ Deslizar**: efecto `msgEntrar` (sube + brillo).
  - **✨ Fundido**: solo opacidad.
  - **🔍 Zoom**: escala desde 0.7.
- El elegido se guarda en `localStorage['jarvis_efecto']` y se aplica al arrancar.
- Los mensajes del historial **nunca** animan (clase `.sin-anim`).

## 6.f Llamada por voz (Gemini Live) — FIX 04/10/2026

- **Solo voz**: `responseModalities: ["AUDIO"]`, solo micrófono, NUNCA pantalla.
- **Bug encontrado y corregido**: la app mandaba el audio con el formato viejo
  `realtimeInput.mediaChunks[]`, que el servidor Live **ignora** → Gemini nunca
  oía. Probado contra la API real: el formato correcto es
  **`realtimeInput.audio {mimeType, data}`**. Con el nuevo, el servidor responde.
- **Auto-interrupción corregida (half-duplex)**: el audio de Gemini salía por el
  altavoz y entraba por el micrófono, cortándose solo. Ahora mientras el modelo
  habla (`modeloHablando`) NO se manda el micro; al terminar el turno, vuelve a
  escuchar. Fuente de audio `VOICE_COMMUNICATION` (cancelación de eco nativa).
  Seguro: si pasan >1.2 s sin audio del modelo, se suelta el half-duplex.
- Comprobado: la clave y el modelo `gemini-3.8-live` funcionan (prueba real de
  `setupComplete` por WebSocket).

## 6.g Recuperación de mensajes al volver la conexión (04/10/2026)

Si el señor Wáscar se queda sin internet/datos tras dar una orden, al recuperar
la conexión la app **trae los mensajes del intervalo** (suyos y míos):

- `TelegramManager` escucha **`UpdateConnectionState`**: cuando pasa a
  `ConnectionStateReady` tras un corte, llama a **`sincronizar()`**.
- `sincronizar()` pide **`GetChatHistory`** (últimos 30) y emite solo los
  mensajes con **fecha posterior** a `ultimaFecha` (marca de lo ya conocido) →
  no duplica nada de lo que ya está en pantalla.
- `ultimaFecha` avanza con cada update nuevo y con cada envío del jefe.
- La app también resincroniza en **`onResume`** (volver de segundo plano).
- Se saltan los SELLOS invisibles; los del bot son "jarvis", los del jefe "jefe".
- Los mensajes que el jefe escribe sin red los encola TDLib y se envían solos al
  reconectar.

## 7. Enlaces presionables en el chat (04/10/2026)
- `_linkificar()` en `widget.html` convierte URLs `http/https` del mensaje en
  `<a class="link-jefe">` con `data-url`.
- Un listener **delegado** único captura el clic y llama a
  `api.abrir_enlace(url)`.
- Puente Kotlin `abrir_enlace(url)` lanza `Intent.ACTION_VIEW` para abrir el
  navegador del teléfono (el WebView no navega solo).
- Estilo: color `#22e6ff`, subrayado, `word-break: break-all`.

## 8. Adjuntar imagen o documento (04/10/2026)

- **Botón clip 📎** (`#btnAdjuntar`) en la barra de escritura, entre la caja de
  texto y el botón de enviar.
- Al tocarlo, `Android.adjuntar()` lanza el selector nativo
  (`ActivityResultContracts.GetContent`, `"*/*"`).
- El archivo elegido se copia a la caché de la app y se envía por **Telegram
  (TDLib)**:
  - Imagen (`image/*`) → `InputMessagePhoto` (TdApi.InputPhoto → InputFileLocal).
  - Otro → `InputMessageDocument` (TdApi.InputDocument → InputFileLocal).
- El envío real lo hace `TelegramManager.enviarArchivo(ruta, esImagen)`.
- **Recepción ya soportada por el bot**: `manejar_foto` (visión por la cadena de
  visión) y `manejar_documento` (guarda en `~\Downloads\jarvis_recibidos`).
- Nota: los adjuntos solo funcionan por Telegram (no por el puente directo).

## 9. Historial y llamada

- Historial persistente en `filesDir/historial_chat.json` vía los métodos
  `historial_leer`/`historial_guardar`.
- Overlay de llamada: esfera grande + órbita, botones mute/colgar, teclado
  oculto al abrir; al conectar Gemini Live muestra "En llamada".

## 9. Ajustes aplicados en la app (Kotlin y layout)

- Sin icono de micrófono: solo caja de texto + botón enviar.
- Insets de Kotlin: top = 0 (la barra la controla el CSS).
- `RECORD_AUDIO` se concede por ADB tras instalar.

## 10. Historial de versiones APK

| Versión | Contenido |
|---------|-----------|
| 2.0     | Nativa base (arm64) |
| 3.0     | Widget |
| 4.0     | Llamada |
| 5.0     | Llamada (ajustes) |
| 6.0     | Botón interrumpir |
| 7.0     | Sellos |
| 8.0     | Barra más delgada + "JARVIS, EN LÍNEA" |
| 9.0     | Sin ojito · ruedita de ajustes · enlaces presionables |
| 10.0    | Barra 18px · botón ir-al-final · chat no baja solo · enviar/interrumpir según caja |
| 11.0    | Envío protegido en el clic · segundo mensaje se encola (turnos) |
| 12.0    | Efecto de aparición elegante de los mensajes |
| 13.0    | Botón adjuntar (clip) · envío de imagen/documento por Telegram |
| 14.0    | Fix audio Live (`realtimeInput.audio`) · "Trabajando..."↔"Procesando..." |
| **15.0**| **Panel ruedita con 4 efectos · máquina de escribir por defecto · llamada half-duplex (sin auto-cortes)** |
| **16.0**| **Recuperación de mensajes al volver la conexión (sincroniza el chat)** |
| **17.0**| **Efecto de tecleo: solo el último mensaje teclea; los demás se completan (sin solape)** |
| **18.0**| **Chat que no se satura: carga por tramos (40 al abrir, scroll infinito hacia atrás) · tope de 2000 en disco y 160 nodos en pantalla · guardado diferido · contención CSS · ahorro de datos (no re-lee salvo corte real)** |
| **19.0**| **Imágenes visibles en el chat: fotos recibidas y enviadas se descargan con TDLib y se pintan como burbuja (miniatura al enviar incluidas) · entran en la carga por tramos** |
| **19.1**| **Imagen ampliable con zoom (tocar la foto → pantalla completa, doble toque/rueda) · giro de la esfera al procesar más rápido (0.7s) · lucesita de estado parpadea intermitente al procesar · barra de scroll auto-oculta (solo al escrollear)** |
| **19.2**| **FIX máquina de escribir: subir las variables del historial antes de `_insertarMensaje` (zona temporal muerta) y exponer `wPushHistorial` como función declarada · `wSetEstado` ya no borra clases del body** |
| **19.3**| **Efecto de tecleo (`escribir`) garantizado al iniciar (por defecto) y persistente si el jefe lo cambia · esfera al procesar más rápida (0.5s) · luz parpadeante más rápida (0.34s)** |
| **19.4**| **FIX tecleo "bugueado": velocidad de tecleo 28-55 ms (antes 10-34, el WebView no repintaba) · orden correcto al insertar mensaje (completar el anterior ANTES de quitar cursores)** |
| **19.5**| **FIX bug raíz: `_quienMira()` no existía y reventaba cada mensaje · barra de scroll ya no ocupa ancho (width 0 + scrollbar-gutter stable) · auto-scroll del tecleo ya no fuerza el scroll en cada letra** |
| **19.6**| **FIX scroll "raro" al llegar mensajes: el seguimiento del fondo ahora es SUAVE (acompaña el tecleo por frame, sin brincos) y solo se suelta cuando el JEFE toca/sube a leer (antes lo soltaba un aviso de tiempo y saltaba). · carga de historial en vivo ya no re-empuja duplicados (index de tramo al día) · recorte de nodos ya no suelta el pin · botón "ir al final" baja suave y siempre gana** |
| **19.7**| **FIX scroll que se ADELANTABA al mensaje: el efecto tecleo encoge el contenido (1 char al arrancar) y el seguimiento creía haber "llegado" → paraba y el último mensaje quedaba cortado mientras aparecía. Ahora el seguimiento apunta SIEMPRE al final real (paso ≤12 px/frame) · tecleo un poco más rápido (16-32 ms por letra, antes 28-55)** |
| **19.8**| **Tecleo más rápido (10-22 ms por letra) · botón "ir al final" casi instantáneo (bajada con paso grande: llega en ~6 cuadros en vez de ~12)** |
| **19.9**| **FIX al REABRIR la app no se veía lo último: se baja al fondo SIEMPRE (con refuerzos a 80/250/600/1100/1800 ms, para que las imágenes y el tecleo no dejen el scroll a medias) · ZOOM DE IMAGEN CON LOS DEDOS (pellizco de 2 dedos + arrastre, con Touch Events; antes solo doble toque) · PANTALLA DE CARGA (splash): esfera dibujada en vivo + "JARVIS" + "CREADO POR WÁSCAR", se retira al pintar el chat (tope 2,5 s)** |
| **20.0**| **PANEL DE ACCESO A TELEGRAM: el jefe introduce TODOS los datos de una sola vez (teléfono + api_id + api_hash + bot) y la app arranca el acceso sola; Telegram solo pedirá el código (y la clave de 2 pasos) y eso se contesta desde la caja del chat. Api_id/api_hash/bot ya vienen precargados. · SPLASH ahora SÍ aparece (nacía oculto): cubre el tiempo de "ponerse al día". · 8 EFECTOS de aparición (máquina de escribir, deslizar, fundido, zoom, rebote, glitch, máquina, neón). · FIX ANR: el arranque/cierre de TDLib se movió a hilo de fondo (bloqueaba la UI y Android mostraba "JARVIS isn't responding").** |
| **20.1**| **FIX DEL ACCESO (el jefe metía los datos y la app seguía "inactiva"): (1) TDLib NO se cierra ni re-crea al meter los datos — se mantiene UN cliente vivo y solo se le manda el teléfono (antes había una carrera cerrar↔reabrir que dejaba a TDLib mudo). (2) El panel se divide en DOS BLOQUES: DATOS (teléfono+api) y PASO (código/clave); cambia solo según lo que pida Telegram. (3) El ENTRAR y el ENVIAR se enganchan a click + touchend + tecla Enter (el click sintético fallaba). (4) Se quitó el focus automático que subía el teclado solo. Verificado en emulador: meter datos → Telegram pide CÓDIGO (antes nunca pasaba).** |
| **20.3**| **PANTALLA DE CARGA ELIMINADA (orden del jefe 04/10/2026): el splash propio se quitó por completo (HTML + CSS + JS + la esfera dibujada en vivo). La app ahora ARRANCA DIRECTO al panel de acceso / chat, sin pantalla intermedia. (El dibujo de la esfera del widget y de la llamada siguen intactos: solo se eliminó el splash.)** |
| **21.0**| **SERVICIO DE FONDO + NOTIFICACIONES (orden del jefe 04/10/2026, solución A+B). El problema: al cerrar la app se destruía TDLib y al reabrir tardaba ~30 s (mostraba "Inactivo"). (A) NUEVO `JarvisService` en primer plano: mantiene la sesión de Telegram VIVA aunque la app se cierre → al reabrir entra en 1-2 s (verificado: la librería nativa no se recarga). TDLib pasa a ser sesión ÚNICA de la app (`TelegramManager.obtener`, singleton) compartida por Activity y Service. (B) NOTIFICACIONES: los mensajes de JARVIS avisan con notificación cuando la app no está delante; notificación persistente "JARVIS en línea" mantiene el servicio vivo. Canales creados en `JarvisApp`. Permiso POST_NOTIFICATIONS (Android 13+).** |
| **22.0 – 24.2** | Versiones intermedias del 05/10/2026 (trabajo previo sobre el chat; el detalle fino de esta franja no quedó anotado en esta tabla). |
| **24.3 – 24.4** | **HORA por mensaje** (abajo a la derecha, 8 px) y **cursor arreglado**: el cursor de escritura ya no salta de línea al aparecer la hora. |
| **24.5** | **Avisos SILENCIADOS por defecto** (interruptor en *Ajustes → Notificaciones*) · **botón REINICIAR JARVIS** en *Ajustes → Sistema* (sello `[[JARVIS:REINICIAR]]` que el bot intercepta, como `[[JARVIS:INTERRUMPIR]]`) · **recarga del chat al abrir** comparando por CONTENIDO (no por hora). |
| **24.6** | **FIX del scroll**: al abrir el chat y al ENVIAR se salta **YA** al final; vigilante de `resize`/teclado para que el scroll no se resetee. |
| **24.7** | **FIX del efecto de tecleo**: el historial ya no suprime la animación de los mensajes en vivo (una marca interna se quedaba pegada y apagaba el tecleo de todos). |
| **24.8** | La **hora pasa a la MISMA línea** que las últimas palabras (flotada a la derecha, `float: right`), en vez de en una línea aparte. |
| **24.9** | El estado de la barra dice **SIEMPRE "Procesando…"** (nunca "Trabajando…") · la hora se pega al **PIE de su línea** (esquina inferior). |
| **25.0** | **CIERRE Y BLINDAJE**: `_cargandoHistorial` con `try/finally` en las dos cargas de historial (nunca se queda pegada) · `reiniciar_jarvis`/`set_notif` con `try/catch` · `window.JARVIS_APP_VERSION` · puente JS↔Kotlin **verificado** (0 desajustes). |
| **26.0** | **DEFINITIVA — FLUIDEZ + FIRMA (05/10/2026)**: quitados los 2 `backdrop-filter` (paneles de Ajustes y de Acceso; el fondo ya era ~98 % opaco y el desenfoque costaba una pasada de GPU sobre toda la pantalla) · la esfera y la barra **no se redibujan** con la app en segundo plano (`document.hidden`) · el color `--jc` solo se reescribe cuando **cambia** (antes, cada cuadro) · el bucle de la barra ya no llama a `getComputedStyle` por cuadro · panel de Ajustes con **scroll propio** (todo alcanzable) · **firma al pie**: "App creada por Wáscar y JARVIS". |

## 19. FIX del scroll "raro" al llegar mensajes (04/10/2026, versión 19.6)

**Síntoma del jefe**: cada vez que llegaba un mensaje nuevo, el scroll se
"actualizaba de una forma rara y extraña" (un salto no deseado), en vez de
acompañar suavemente el texto mientras se teclea.

**Causa raíz (dos)**:
1. **El pin del fondo se "soltaba" por tiempo.** `_marcarScroll` despegaba el
   auto-scroll con un aviso de 250 ms; cuando el repintado del WebView tardaba más
   (justo lo que el jefe veía), el siguiente frame ya estaba "despegado" → el
   scroll no acompañaba y se veía el brinco. **Ahora el pin SOLO se suelta cuando
   el JEFE toca/rueda el chat** (`touchstart/touchmove/wheel/mousedown/keydown/
   pointerdown`), nunca por un aviso de tiempo.
2. **El seguimiento iba a saltos.** Ahora `_pasoFondo()` avanza por frame
   (`requestAnimationFrame`) con un paso pequeño (máx 14 px/frame) → **acompaña el
   tecleo suave**, sin dar el tirón.

**De paso, dos bugs que agravaban el cuadro**:
- La carga en vivo del historial volvía a llamar `wAddMensaje` (re-empujaba
  duplicados) → ahora pinta como historial y mantiene al día `_pintadosHasta`.
- El **recorte de nodos viejos** movía el scroll y podía soltar el pin → ahora se
  marca `_recortando` y el pin no se toca.

**Probado en navegador real (emulación móvil 390×844)**:
- Tecleo con el chat abajo: **max. salto por frame = 11 px**, dif. al fondo **0**
  (pegado, suave).
- El jefe sube a leer (gesto táctil + subida): el chat queda **arriba**.
- Llega un mensaje mientras lee arriba: scroll **quieto** (no se mueve solo).
- Botón "ir al final": baja **suave** (30→100→170→268→436→585→597) y queda
  **clavado al fondo** (dif = 0).


## 18. FIX del ancho que saltaba y del bug raíz `_quienMira` (04/10/2026, versión 19.5)

**Síntoma del jefe**: al llegar un mensaje nuevo se hacía scroll, aparecía la barra
lateral derecha y **el ancho del chat cambiaba** → los mensajes se veían "bugueados".

**Causas (dos)**:
1. **`_quienMira()` se llamaba pero NUNCA se definió** → `ReferenceError` en cada
   carga de tramo/mensaje → rompía el pintado y el tecleo. Se definió:
   `return zona.children.length > _TOPE_DOM;`
2. **La barra de scroll reservaba 4px de ancho.** Al aparecer/desaparecer, el
   contenido se recalculaba. Arreglado: `width: 0` (overlay), `scrollbar-width: none`
   y `scrollbar-gutter: stable` → **el ancho es constante**.
3. **Auto-scroll por letra**: el `tick` del tecleo hacía
   `zona.scrollTop = zona.scrollHeight` **en cada letra**, disparando el scroll (y
   la barra). Ahora solo baja si el jefe ya estaba al fondo.

**Verificado en navegador real**: 3 mensajes seguidos con el chat abierto →
ancho **clavado en 480px** (antes / t1 / t2 / t3 = 480). No salta.


## 17. FIX del tecleo a saltos y del cursor (04/10/2026, versión 19.4)

**Síntoma del jefe**: al enviar el 2º/3º mensaje, los mensajes se veían "como
editándose / bugueados, con pocos frames", y el cursor no se veía.

**Causa raíz (dos bugs)**:
1. **Velocidad imposible**: el paso del tecleo era `10-34 ms` (línea del `tick`).
   El WebView del móvil **no alcanza a repintar** entre letra y letra → el texto
   se ve a saltos, como si se estuviera "editando". Arreglado a **28-55 ms**
   (suave y estable; acelera un poco en textos largos sin bajar del mínimo).
2. **Orden invertido en `_insertarMensaje`**: primero retiraba los cursores
   `.cursor` y **después** completaba el tecleo → el mensaje en curso quedaba a
   medio pintar ("bugueado"). Ahora **primero completa el tecleo y después**
   retira los cursores de los mensajes anteriores.

**Verificado en navegador real (Brave, arnés offscreen)**:
- 3 mensajes seguidos → los 2 primeros se **completan limpios**, el último queda
  con **su cursor** (`.cursor` + `.cursor-esc`). Ninguno "bugueado".
- Fluidez: el texto crece letra a letra de forma **regular** (~14 ms por muestra),
  sin saltos de frames.


## 16. Arranque garantizado del efecto (04/10/2026, versión 19.3)

**Petición del jefe**: que el efecto de máquina de escribir **inicie junto con la app
de forma predeterminada**, y que si él lo cambia, **el cambio persista** en cualquier
cierre y reapertura.

**Solución**:
- Nueva `window.wEfectoPorDefecto()`: al cargar, lee `localStorage['jarvis_efecto']`; si
  es válido lo respeta (elección del jefe, **persistente**), y si no, aplica
  **`'escribir'`** por defecto.
- Se llama al cargar el script **y** en `DOMContentLoaded` (no depende del evento
  `pywebviewready`).
- `wSetEfecto` ahora **cae a 'escribir'** si recibe un valor inválido.
- `MainActivity.onPageFinished` refuerza el efecto por si el JS no corriera.

**Prueba en navegador real (Brave, arnés offscreen)**: `defecto='escribir'` y el
tecleo letra a letra (`"Tec"` → `"Tecleo"` → … → texto completo con cursor).

**Velocidades** (misma sesión): esfera `st-thinking` → `girar 0.5s`; luz `.punto`
→ `parpadeoLuz 0.34s`.


## 15. FIX del efecto de tecleo (04/10/2026, versión 19.2)

**Síntoma**: el efecto "máquina de escribir" no se veía (el mensaje aparecía de golpe).

**Causa raíz** (bug real, encontrado con simulación offscreen): `_insertarMensaje`
**usaba** `_hist`, `_TOPE_DOM`, `_TRAMO`, `_pintadosHasta`, `_guardandoPendiente`,
`_cargandoHistorial` y `window.wPushHistorial`, que estaban **declarados más abajo**
en el archivo. `let`/`const` **no se elevan** (zona temporal muerta) → `TypeError` en
tiempo de ejecución que **cortaba el tecleo a la mitad**.

**Solución**:
1. Se movieron **todas las variables del historial ARRIBA**, antes de `_insertarMensaje`.
2. `wPushHistorial`, `wSetHistorial` y `wLimpiarHistorial` pasaron de
   `window.x = function(){}` (no elevables) a **funciones declaradas** elevables.
3. **Extra**: `wSetEstado` ya no hace `document.body.className = ...` (borraba
   `scroll-oculto`, `chat-abierto`...); ahora usa `classList.remove/add/toggle`.

**Verificado**: simulación integral del tecleo → letra a letra
(`"JARVIS"` → `"JARVIS resp"` → `"JARVIS responde "`…) con cursor al final.


## 14. Ajustes finos 19.1 (04/10/2026)

- **Imagen ampliable** (`wImagenGrande` / `_abrirImagenGrande`): al tocar una foto
  del chat se abre a pantalla completa. Zoom con **doble toque** (1× ↔ 2.2×) y
  **rueda** (hasta 5×). Se cierra con la **X** o tocando el fondo. CSS `.lupa`.
- **Giro de la esfera al procesar**: `body.st-thinking .orbita` pasó de
  `girar 1.1s` a **`girar 0.7s`** (un pelín más rápido).
- **Lucesita de estado**: en `st-thinking` el `.punto` usa `parpadeoLuz 0.5s`
  (encendido/apagado seco, más intermitente) en vez del latido suave.
- **Barra de scroll auto-oculta**: el chat arranca con la barra **oculta**
  (`body.scroll-oculto`); al escrollear aparece (`_mostrarBarraScroll`) y se vuelve
  a ocultar tras **900 ms** de reposo.
- **Máquina de escribir**: se confirma que solo el **último** mensaje teclea con
  cursor; si llega uno nuevo, el anterior se completa al instante.


## 13. Imágenes en el chat (04/10/2026, versión 19.0)

Las imágenes (fotos) ya se **ven** en el chat, tanto las que envía el jefe como las
que manda JARVIS. Antes solo se enviaban pero no se mostraban.

- **Recepción** (`TelegramManager.descargarFoto`): al llegar una foto se descarga la
  resolución más grande con TDLib (`DownloadFile`), se copia a la caché de la app con
  nombre estable (`img_<id>.jpg/png/webp`) y se emite su ruta por el flujo `_imagenes`.
- **Envío** (`ChatViewModel.enviarArchivo`): al adjuntar una imagen se pinta su
  miniatura **al instante** (una sola emisión; `TelegramManager` ya no la re-emite).
- **Pintado** (`widget.html` → `wAddImagen` / `_insertarImagen`): burbuja `.msg-img`
  con `<img class="img-chat">` (máx 190×190). Si la imagen no carga, muestra
  "🖼 imagen no disponible".
- **Historial**: se guarda como `{de, tipo:'imagen', texto:ruta}` e **integra la carga
  por tramos** (se vuelve a ver al reabrir y al subir hacia atrás).
- **WebView**: `allowFileAccessFromFileURLs` + `allowUniversalAccessFromFileURLs` para
  poder mostrar rutas `file://` locales.
- **Antiduplicado**: las fotos propias no se re-descargan en `sincronizar()` (ya se
  pintaron al enviarlas).

Funciones nuevas: `TelegramManager.fotoDe`, `descargarFoto`, `extDeFoto`;
`ChatViewModel.imagenes`; `MainActivity` observa `vm.imagenes`; `widget.wAddImagen`.


## 12. Chat que no se satura — carga por tramos y blindaje (04/10/2026)

Las conversaciones largas ya no laggean ni bugean. Mismo criterio que Telegram:
**no se carga todo, se cargan tramos**.

- **Carga por tramos (`_TRAMO = 40`).** Al abrir la app se pintan solo los
  **últimos 40** mensajes. Al subir hasta arriba del todo, se cargan **40 más**
  ("scroll infinito" hacia atrás), conservando la posición del scroll (no brinca).
- **Historial en disco (`_TOPE_HIST = 2000`).** Se guardan hasta 2000 mensajes
  (antes 400). Se tira lo más viejo de a poco.
- **Tope de nodos en pantalla (`_TOPE_DOM = 160`).** Aunque el jefe lea hacia
  atrás mucho, en el árbol vivo nunca hay más de ~160 mensajes: los más viejos se
  recortan. Así la RAM y el dibujado se mantienen planos.
- **Guardado diferido (700 ms).** En rachas rápidas no se escribe el archivo en
  cada mensaje, sino una sola vez al final. La escritura a disco se hace en hilo
  aparte (nunca en el hilo de UI).
- **Contención CSS (`contain: content`).** Agregar/recortar mensajes ya no
  recalcula el resto de la ventana.
- **Ahorro de datos.** La relectura del historial de Telegram (`sincronizar()`)
  **solo** ocurre cuando de verdad hubo un corte de red, no en cada reapertura.

Funciones nuevas en `widget.html`: `_insertarMensaje`, `_cargarTramoArriba`,
`_recortarViejos`; constantes `_TRAMO`, `_TOPE_HIST`, `_TOPE_DOM`.


## 10.b Panel de acceso a Telegram (04/10/2026, versión 20.0)

**Petición del jefe**: poder introducir **todos los datos de Telegram de una sola
vez** y que la app le dé acceso automáticamente.

- **Panel `#panelAcceso`** (body `acceso-abierto`): se **abre solo** al arrancar si
  no hay sesión; también con el botón **🔑 Acceso Telegram** dentro de Ajustes.
- Campos: **teléfono (con país) · api_id · api_hash · bot**. Los tres últimos
  vienen **precargados** (`Preferencias`): al abrir, `credenciales_leer()` los rellena.
- Al tocar **ENTRAR**, `Puente.iniciar_acceso()` → `ChatViewModel.accesoTelegram()`:
  guarda TODO (`guardarTelefono` + `guardarTelegram`), cierra el cliente viejo y
  arranca TDLib con el teléfono ya puesto.
- Telegram pide después: **código** (y **clave de 2 pasos** si el jefe la tiene).
  Esos pasos se **contestan desde la caja del chat** (el `wSetFase` bloquea los
  campos y cambia el placeholder; el panel se abre solo con la pista).
- Al quedar **"en línea"**: se marca `accesoHecho = true` (no vuelve a pedir los
  datos), se cierra el panel y queda el chat.
- El teléfono se reenvía solo al arrancar (`TelegramManager.arrancar(..., telefono)`
  → `AuthorizationStateWaitPhoneNumber`), una vez por arranque.
- **FIX ANR**: `cerrar()`/`arrancar()` de TDLib corren en `Dispatchers.IO`, no en el
  hilo de UI (antes congelaban la app al pulsar ENTRAR).

## 10.c Chat, scroll, hora y blindaje (05/10/2026, versiones 24.3 → 25.0)

**Peticiones del jefe (05/10/2026) y qué se hizo:**

1. **Hora en cada mensaje** — cada burbuja lleva su hora (8 px, opacidad 0.55)
   **al pie de la última línea**, flotada a la derecha (`float: right` +
   `margin-top: 5px` sobre una línea de ~14,7 px), no en una línea aparte.
   El `.msg::after { clear: both }` cierra el globo para que la hora no se salga.

2. **El cursor no salta de línea** — el HTML final del mensaje es
   `texto + cursor + hora`: el cursor de escritura queda pegado al texto y la
   hora (bloque aparte) ya no lo empuja a otra línea.

3. **Avisos SILENCIADOS por defecto** — interruptor en *Ajustes → Notificaciones*
   (`Preferencias.notificaciones`, por defecto `false`). Al activarlos se pide el
   permiso `POST_NOTIFICATIONS` (Android 13+) y **solo** avisan si la app **no**
   está delante (`JarvisApp.enPrimerPlano`, puesto en `onStart`/`onStop`).

4. **REINICIAR JARVIS desde la app** — botón en *Ajustes → Sistema*.
   `Puente.reiniciar_jarvis()` → `ChatViewModel.reiniciarJarvis()` → sello
   **`[[JARVIS:REINICIAR]]`** al chat de Telegram, que el bot intercepta igual que
   `[[JARVIS:INTERRUMPIR]]` y ejecuta el reinicio diferido. (Requiere el bot ya
   reiniciado con ese cambio: hecho el 05/10/2026.)

5. **Mensajes que llegaron con la app cerrada** — al abrir (y al volver a la app)
   se llama `recargarChat()` (3 intentos: ya, +2,5 s y +4,5 s) y el widget rellena
   **solo los que faltan comparando por CONTENIDO** desde el final (no por hora,
   que era frágil). Función `window.wRecargarChat` en `widget.html`.

6. **Scroll** — al abrir el chat y al **ENVIAR** un mensaje se salta **YA** al final
   (`_irAlFondoYa()`), sin la bajada lenta de antes. Además un vigilante de
   `resize` / `visualViewport` vuelve a pegar al fondo cuando el teclado abre o
   cierra (era lo que reseteaba el scroll al enviar).

7. **Efecto de tecleo** — volvió a funcionar: `_insertarMensaje` ya **no** usa
   `_cargandoHistorial` para decidir si anima (esa marca, si se quedaba pegada,
   apagaba el tecleo de TODOS los mensajes). Ahora solo el historial se pinta sin
   animación.

8. **Barra superior** — el estado dice **siempre "Procesando…"**
   (`_TEXTOS_PENSANDO` con un solo valor y `_ETIQUETAS.THINKING`); nunca más
   "Trabajando…". La burbuja de progreso también dice "JARVIS · procesando".

**Blindaje de la 25.0 (cerrar sin dañar nada):**

- `_cargandoHistorial` se pone y se quita dentro de `try/finally` en
  `_cargarHistorial` y en `_cargarTramoArriba`: pase lo que pase **no se queda
  pegada**.
- `Puente.reiniciar_jarvis()` y `Puente.set_notif()` van envueltos en `try/catch`:
  una llamada del JS en mal momento ya no puede tumbar la app.
- El widget expone `window.JARVIS_APP_VERSION` (versión del build que corre).
- **Puente verificado**: los 28 métodos que el widget llama (`Android.*`) existen
  todos en Kotlin con `@JavascriptInterface`, y todas las funciones `wX` que el
  Kotlin invoca por `eval()` existen en el widget → **0 desajustes**.
- Compilación limpia (`assembleDebug` sin errores); solo queda el aviso benigno de
  que `onRequestPermissionsResult` está *deprecated* (funciona igual).

**Fluidez en Android (verificado y aplicado en la 26.0):**

- **Sin `backdrop-filter`** en los paneles de Ajustes y de Acceso: el fondo ya era
  ~98 % opaco (el desenfoque no se veía) y costaba una pasada de GPU sobre toda la
  pantalla en cada cuadro.
- **Esfera y barra de estado NO se redibujan** con la app en segundo plano
  (`document.hidden` → se salta el dibujo pero se sigue pidiendo el cuadro para
  retomar solo). Ahorra GPU y batería; importante porque el servicio de fondo
  mantiene la app viva.
- La variable CSS `--jc` (el color de JARVIS) **solo se reescribe cuando cambia**.
  Antes se escribía en cada cuadro y obligaba a recalcular los estilos de toda la
  app (afecta a decenas de reglas que usan `var(--jc)`).
- El bucle de la barra usa el color **ya calculado** (`_rgbCSS`) en vez de llamar a
  `getComputedStyle` por cuadro.
- El chat ya venía blindado para fluidez: `contain: content` en la lista, recorte de
  nodos (160 en pantalla / 2000 en disco), carga por tramos y guardado diferido.
- El panel de Ajustes tiene **scroll propio** para que todo, incluida la firma,
  sea accesible.

**Firma (orden del jefe 05/10/2026):** al final de Ajustes aparece, pequeño y
centrado, **"App creada por Wáscar y JARVIS"**.

## 11. Nota de seguridad

La clave de Gemini está en `Preferencias.GEMINI_DEFECTO` (y en
`widget_voz_jarvis\config.json`). En un APK compilado queda en texto plano — quien
lo descompile la vería. Para producción conviene moverla a un backend o
restringir la clave por app.
