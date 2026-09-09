
## 27/08/2026 - BOT ESTADISTICO: descarga de velas estilo 9-maximus + IP bloqueada
- PROBLEMA: IQ Option bloqueo la IP de la PC temporalmente (exceso de
  llamadas al websocket de la auditoria). El jefe cambio de IP con VPN.
- FIX (copiado del bot de nubes 9-maximus / cache_maximos_cloud):
  1. _get_candles_seguro: activo NO registrado en OP_code.ACTIVES -> NO
     llamar (evita el bucle 'get_candles need reconnect' / 'is_ssl').
     TIMEOUT -> NO se reintenta (la libreria quedo colgada). ERROR ->
     _reconectar_api (websocket con SSID) + reintento.
  2. _reconectar_api: api.api.connect() a nivel websocket (reutiliza el
     SSID, sin el bucle de balance_id del connect completo).
  3. _reconectar_completa: primero el connect a nivel websocket, solo si
     falla el connect completo.
- FIXES ANTERIORES MANTENIDOS: limitador de ritmo global (0.25s entre
  llamadas), enfriamiento 15s tras reconexion fallida, max 3 reconexiones
  por auditoria, ritmo 0.3s entre bloques, DIAS_AUDITAR 15.
- VERIFICADO: compila, imports OK, conexion OK con la IP nueva
  (balance_id 1246570019). BOT LANZADO LOCAL (17:45, PID 7380), polling
  OK. SIN PUSH a GitHub (orden del jefe).

## 27/08/2026 - BOT MULTI-SECUENCIAS: fix STREAM CONGELADO en martingala
- PROBLEMA (log nube 20:18-20:21): EURAUD perdio MG0 a las 20:19 y el
  MG1 NUNCA se ejecuto (silencio total). El stream de velas de EURAUD se
  congelo tras la rafaga de desuscripciones del ciclo (ultima vela
  20:18); la recuperacion vela a vela necesita vela NUEVA (nuevo_cierre)
  y no llego ninguna. El canal de resultados (position-changed) seguia
  vivo (el resultado del MG0 llego).
- REGLA DEL JEFE: el hilo del activo en martingala debe permanecer VIVO
  (nunca se desuscribe, solo los otros 9). La reconstruccion de
  conexiones solo aplica al GANAR.
- FIX (bot.py): frescura de streams con auto-re-suscripcion:
  _registrar_avance_local (trackea el ultimo 'from' por activo) +
  _reparar_stream_si_muerto (si no avanza en ~90s en el bucle principal,
  o ~10s en el reintento inmediato, re-suscribe al instante). Las
  desuscripciones ahora se ESPACIAN 0.3s para no congelar el canal de
  velas del activo que opera.
- VERIFICADO: py_compile OK, prueba de frescura OK (fresco no
  re-suscribe, congelado si). PUSHEADO a GitHub (f811e9d).

## 27/08/2026 - BOT MULTI-SECUENCIAS: MINUTO CIEGO post-ganada
- REGLA DEL JEFE: tras una operacion GANADA, el bot entra en MINUTO CIEGO
  hasta el proximo :00: NO toma operativas (ni de otros activos) y NO
  envia el reporte top 5. Se recupera: re-suscribe los 9 streams y
  reconstruye todas las estrategias con el panorama completo.
- IMPLEMENTADO (bot.py): _pausa_post_ganada_hasta = proximo :00 al ganar;
  check de omision en _ejecutar_operativa ('minuto ciego post-ganada') y
  check de pausa en hilo_reporte (sin top 5). Mensajes de GANADA y
  PERDIDA se envian de INMEDIATO (antes de la recuperacion de 20-30s).
- ORDEN DE RECUPERACION (fix del jefe): en ganada, perdida completa y sin
  resultado, la recuperacion (re-suscribir + reconstruir) va PRIMERO y
  solo despues se liberan los flags del ciclo (los hilos nunca vuelven
  con datos viejos - era la causa de las dos operativas seguidas).
- EMPATE: se mantiene como PERDIDA (regla del jefe, sin cambios).
- PUSHEADO a GitHub (81ece62). NO se toco la plantilla ni el respaldo.

## 27/08/2026 - BOT MULTI-SECUENCIAS: fix REINICIOS EN LA NUBE (zombies del fix profundo)
- PROBLEMA (reportado por el jefe): reinicios constantes cada 2-3 minutos
  en la nube. Log: 'WATCHDOG: websocket muerto (9 zombies nuevos)'.
- CAUSA: el fix profundo desuscribia con stop_candles_stream, que duerme
  self.suspend*10 = 5s POR ITERACION esperando la confirmacion del
  servidor; con timeout de 5s la llamada SIEMPRE se colgaba -> 9 zombies
  por ciclo (uno por activo desuscrito) -> el watchdog reiniciaba el bot
  en medio del ciclo (perdiendo la operativa).
- FIX: desuscripcion DIRECTA fire-and-forget (api.api.unsubscribe con el
  active_id de OP_code.ACTIVES) - envia UNA peticion y vuelve al instante,
  sin bucle de espera. Timeout 3s. Import agregado: iqoptionapi.constants
  como OP_code (es el MODULO, no un nombre dentro).
- PUSHEADO a GitHub (c7c2ae8). La nube toma el deploy automatico.

## 27/08/2026 - BOT MULTI-SECUENCIAS: FIX PROFUNDO (streams desuscritos en ciclo)
- REGLA DEL JEFE: durante el ciclo vela a vela se DESUSCRIBEN los streams
  de los demas activos (websocket solo con el activo que opera, ~1 vela/seg
  en vez de 10). Al cerrar el ciclo (ganada, perdida completa o sin
  resultado) se RE-SUSCRIBEN (~2-4s por activo, ~20-30s los 9, cabe en el
  minuto hasta el proximo :00) y se reconstruyen las estrategias ANTES de
  liberar la pausa de los hilos.
- IMPLEMENTADO (bot.py): _pausar_streams_ajenos (hilo de fondo, timeout 5s
  por activo, si falla se omite) lanzado al EJECUTAR la primera operativa
  del ciclo; _reanudar_streams_ajenos (suscribir_stream + resync) en los
  cierres de ciclo. NO se aplico a la plantilla ni al respaldo (orden del
  jefe).
- RECONSTRUCCION VERIFICADA (pregunta del jefe): al re-suscribir, el bot
  reconstruye las estrategias con las velas frescas y TOMA EN CUENTA las
  secuencias que se formaron durante la pausa: si el final parcial
  coincide queda 'activo' con progreso; si no coincide aun, queda
  'buscando' y dispara apenas se completa la ultima vela; si la secuencia
  se completo durante la pausa y sigue presente, dispara en el siguiente
  alimentar. Probado con velas sinteticas (parcial 3/4 y completa).
- PUSHEADO a GitHub (3f1784e). La nube toma el deploy automatico.

## 27/08/2026 - BOT MULTI-SECUENCIAS: pausa desde la EJECUCION + ventana de reintento
- REGLA DEL JEFE (con ~10 secuencias activas en la nube): la pausa de los
  demas hilos debe empezar desde que se EJECUTA la primera operativa
  (MG0), NO desde la primera perdida. Si gana -> se reabren los hilos;
  si pierde -> el ciclo vela a vela continua en ese activo.
- IMPLEMENTADO (bot.py): al ejecutar la operativa con tipo_martingala
  'vela' se setea _ciclo_vela_activo + _ciclo_martingala_activo (log una
  sola vez). El check de omision y la pausa de hilos ya NO exigen
  plan.nivel >= 1 (aplican desde el MG0). El handler de perdida solo
  mantiene los flags (idempotente, sin log duplicado).
- FIX SALTOS EURCHF (18:31/18:33 en la nube): la vela nueva tardaba mas
  de 3s en llegar al stream (websocket congestionado con muchas
  secuencias) y el reintento inmediato rompia; ventana ampliada a ~50s
  (100 reintentos x 0.5s, rompe solo si seg >= 50).
- PUSHEADO: BOT-MULTI-SECUENCIAS (e32edb8 + 9c63aca) y PLANTILLA
  (fc18952). La nube toma el deploy automatico.

## 27/08/2026 - BOT ESTADISTICO: fix RECONEXION COMPLETA (websocket muerto)
- PROBLEMA (log del jefe): en la auditoria el websocket de IQ murio
  ('get_candles need reconnect', 'NoneType is_ssl', WinError 10060,
  'Connection is already closed') y las descargas de USDPHP/CHFJPY
  fallaron con 0 velas. La reconexion de la libreria (connect) NO arregla
  un websocket roto: get_candles entra en bucle infinito esperando
  balance_id.
- FIX (calculador_historicos.py): _reconectar_completa() cierra el
  websocket roto, fuerza api.api = None (recrea el objeto IQOptionAPI
  desde cero) y reconecta con timeout. _descargar_historial_largo ahora
  tiene 2 intentos GLOBALES por activo; entre intentos hace la
  reconexion completa y reinicia la descarga desde cero (los datos
  parciales no sirven). auditar_activo simplificado (la descarga maneja
  su propia reconexion).
- VERIFICADO: py_compile OK, prueba de _reconectar_completa con mocks
  (ok tupla True, fail tupla False, ok bool True).
- BOT REINICIADO (14:35, PID 3104). PUSHEADO a GitHub (dd0103b).

## 27/08/2026 - BOT ESTADISTICO: revision + fixes + 10 activos + inicio local
- REVISION completa (10 modulos compilan, simulador probado con velas
  sinteticas). Fixes aplicados (regla del jefe):
  1. auditor.py: el ciclo incompleto al final de la serie ahora RESTA sus
     perdidas del profit (antes optimista) y reporta 'perdidas_pendientes'.
  2. calculador_historicos.py: calcular_maximo_para_patron salta tras cada
     aparicion (una operativa a la vez), consistente con el simulador
     (antes contaba solapadas y daba valores mas altos).
  3. auditor.py: la espera (ESPERA_TRAS_PATRON) ahora aplica tambien en
     modo vela_a_vela (antes se ignoraba).
  4. telegram_utils.py: eliminada enviar_mensaje_telegram (codigo muerto,
     usaba un solo chat).
  5. BOT_ESTADISTICO.py: _Tee.write acepta cualquier tipo (str()).
  6. calculador_historicos.py: bloques ordenados ascendente (la API puede
     devolverlos en cualquier orden).
  7. telegram_ui.py: offset de Telegram PERSISTENTE en archivo (al
     reiniciar no se reprocesan mensajes viejos).
  8. auditor.py: reconexion automatica a IQ con un reintento de descarga
     si la conexion cae.
- ACTIVOS: 10, los mismos que BOT MULTI-SECUENCIAS (EURCAD, EURCHF,
  AUDUSD, CHFJPY, GBPNZD, NZDUSD, USDCAD, AUDNZD, EURAUD, USDPHP - OTC).
  ACTIVO_DEFECTO = EURUSD-OTC.
- VERIFICADO: py_compile 10 modulos OK, pruebas de logica OK (profit
  -3.74 con pendientes 3.74, max_fallos 2 consistente, espera en vela).
- INICIADO LOCAL (14:24, PID 6256) con lanzar_bot.bat nuevo.
- PUSHEADO a GitHub (wascar2416-star/bot-estadistico, commit 4f423c1).

## 27/08/2026 - PLANTILLA IQ OPTION v2: actualizada con las mejoras del motor
- REGLA DEL JEFE: portar a la PLANTILLA (fuera de la estrategia) los
  puntos 1 (motor), 2 (robustez) y 3 (eficiencia) aprendidos con el
  BOT MULTI-SECUENCIAS. Actualizadas las TRES copias: Desktop
  (PLANTILLA-IQ-OPTION), Downloads y GitHub (wascar2416-star/
  PLANTILLA-IQ-OPTION, push 0496f2e conservando el historial previo).
- MOTOR: esperar_resultado rapido (expiracion exacta + poll 0.3s/1s),
  tg.enviar_async (la entrada es lo primero), contrato con
  reintento_inmediato() y ciclo_enfocado() (estrategia_base +
  estrategia_vacia), bucle de reintento inmediato con espera de vela
  nueva (evita saltos), reporte pausado durante todo el ciclo,
  ciclo de martingala ATADO al activo (flag _ciclo_atado_activo,
  omitir senales ajenas + pausar hilos).
- ROBUSTEZ: watchdog no reinicia con sesion cerrada (dormido), regla
  del doji respeta reintento_inmediato (no mata el ciclo).
- EFICIENCIA: contador de llamadas WS (timeout_utils + log minuto),
  cache global de saldo para monto auto (SALDO_AUTO_TTL 60s),
  refresco_desfase 300s.
- VERIFICADO: py_compile OK, import OK (estrategia picos intacta,
  reintento/ciclo default False = comportamiento clasico).
- NOTA: el fix del nivel ganada (capturar nivel antes de plan.gana)
  tambien se porto. El seguro de detencion y el boton dinamico NO van
  (son del panel de secuencias, no del motor generico).

## 27/08/2026 - BOT MULTI-SECUENCIAS: fix WATCHDOG (reinicios en la nube)
- PROBLEMA (reportado por el jefe): en la nube (Railway) el bot se
  reiniciaba cada ~5 minutos aunque estuviera DETENIDO (operativas
  apagadas), pareciendo un inicio nuevo.
- CAUSA: el watchdog de congelamiento (_hilo_watchdog_congelamiento)
  reinicia el bot si lleva >180s sin logs. Con operativas DETENIDAS el
  bot no escribe nada (sin reporte, sin operaciones, sin transiciones),
  asi que el watchdog lo reiniciaba cada ~3-4 min (mismo caso local de
  las 12:02:25).
- FIX: el watchdog ahora NO reinicia si secuencias.operativas_activas()
  es False (el silencio es legitimo con el bot detenido). Solo aplica
  con operativas ACTIVAS.
- PUSHEADO a GitHub (commit 4900f67) para que la nube lo tome en el
  proximo deploy.
- RESPALDO: actualizado UNA VEZ por orden del jefe (27/08/2026, unica
  excepcion a la regla de congelado) con la version del fix watchdog.
  Vuelve a quedar CONGELADO hasta nueva orden.

## 27/08/2026 - BOT MULTI-SECUENCIAS: DESPLIEGUE EN LA NUBE + RESPALDO CONGELADO
- REGLA DEL JEFE: el bot se desplego en la NUBE (Railway/Heroku) via
  GitHub (repo wascar2416-star/BOT-MULTI-SECUENCIAS). La instancia de la
  PC esta APAGADA; solo corre la de la nube.
- RESPALDO CONGELADO: C:\Users\wasc4\Desktop\BOT-MULTI-SECUENCIAS-BACKUP
  quedo actualizado con la ULTIMA version (27/08/2026). NO volver a
  actualizarlo a menos que el jefe lo pida explicitamente.
- El proyecto local sigue en Documents/python projects/BOT-SECUENCIAS
  (con su .git apuntando al repo de GitHub).

## 27/08/2026 - BOT MULTI-SECUENCIAS: fix SALTO DE ACTIVO en vela a vela
- PROBLEMA (reportado por el jefe, log 12:52-12:56): USDPHP perdio MG0 a
  las 12:52 y el MG1 lo tomo EURCAD a las 12:54 (salto de activo). El
  objetivo: el ciclo vela a vela queda ATADO al activo que perdio hasta
  ganar o perder completo.
- CAUSA: el flag _ciclo_vela_activo se activaba revisando
  est.reintento_inmediato() (estado interno _ciclo_vela), pero en la
  PRIMERA perdida del ciclo ese estado aun no se habia puesto (la
  estrategia acababa de disparar el patron), asi que el flag NUNCA se
  activaba en la primera perdida y el ciclo quedaba sin atar: otros
  activos seguian escaneando y podian tomar el nivel siguiente (race en
  el :00: EURCAD gano el turno y USDPHP quedo omitido).
- FIX: el ciclo se ata por el MODO de la estrategia
  (est.tipo_martingala == 'vela'), no por el estado interno. Ahora el
  flag se activa desde la PRIMERA perdida: los demas hilos se pausan y
  sus senales con nivel de martingala se omiten.
- BOT REINICIADO (13:01) con el fix, sin errores.

## 27/08/2026 - BOT MULTI-SECUENCIAS: velas cerradas + respaldo + estado en reporte
- VELAS CERRADAS (verificado): get_velas_stream (velas.py) filtra SOLO
  velas cerradas (la vela en formacion no cuenta), el bucle del motor
  espera el cierre (cierre <= hora_broker) antes de alimentar, y el
  match de la secuencia exige que la ultima vela sea del color deseado.
  Las operativas SIEMPRE se toman sobre velas cerradas.
- RESPALDO: copia completa del bot en
  C:\Users\wasc4\Desktop\BOT-MULTI-SECUENCIAS-BACKUP (sin pycache ni log).
- REPORTE: 'Sin nivel' sustituido por '└ Estado: <estado>' con la lupita
  🔍 al final cuando el estado es 'buscando' (ej. 'Estado: Buscando
  secuencia 🔍'); otros estados muestran su texto real sin lupita.
- BOT RELANZADO (12:46): instancia anterior eliminada, nueva corriendo
  sin errores.

## 27/08/2026 - BOT MULTI-SECUENCIAS: fixes vela saltada + doji en ciclo + log
- PROBLEMA (reportado por el jefe con log de EURAUD 12:28-12:31): en medio
  de una martingala vela a vela el bot se SALTO una vela (MG3 se tomo a
  las 12:29 en vez de 12:28) y logueaba 'NIVEL DESCARTADO: sin motivo'.
- CAUSA 1 (vela saltada): el reintento inmediato leia las velas apenas
  llegaba el resultado y, si la vela nueva aun no habia llegado al stream
  (race con el push del websocket), nuevo_cierre=False -> no disparaba y
  rompia; el MG caia al proximo :00 (una vela despues).
  FIX: en el reintento inmediato, si alimentar devuelve None y la ventana
  no esta cerrando (seg < 50), esperar 0.3s y REINTENTAR (max 10).
- CAUSA 2 (doji mataba el ciclo): la regla del DOJI del motor reiniciaba
  la estrategia (reconstruir) aunque el ciclo vela a vela estuviera en
  curso, cancelando la recuperacion. REGLA DEL JEFE: la doji descarta la
  SECUENCIA, pero NO el ciclo ya iniciado. FIX: en la regla del doji, si
  reintento_inmediato() es True (ciclo vela activo), NO se reinicia la
  estrategia (solo se salta esa vela y el ciclo continua en la siguiente).
- CAUSA 3 (log enganoso): 'NIVEL DESCARTADO: sin motivo' era el DISPARO
  (transicion activo->buscando del registrador de la plantilla). FIX: la
  estrategia marca _ultimo_motivo_invalida ('disparada', 'disparada (vela
  a vela)', 'rota') y el registrador loguea 'SECUENCIA: <motivo>' para la
  estrategia secuencias (nunca mas 'NIVEL DESCARTADO').
- VERIFICADO: py_compile OK, prueba de los 3 motivos OK, bot reiniciado
  (12:43) sin errores. secuencias.json recreado (V,V,V,V->R + inversa).

## 27/08/2026 - BOT MULTI-SECUENCIAS: seguro de detencion + limpieza
- SEGURO DE DETENCION (regla del jefe): el boton 'Detener operativas' NO
  detiene el bot si hay una operacion en curso (reporte_pausado) o un
  ciclo de martingala pendiente (_ciclo_martingala_activo). Responde
  '⛔ NO SE PUEDE DETENER AHORA' y solo se detiene sin operaciones
  abiertas. Implementado en el handler de iniciar/detener operativas.
- LIMPIEZA: eliminados __pycache__ y bot.log (el bot los regenera solo).
  secuencias.json se CONSERVA (datos del usuario: V,V,V,V->R + inversa,
  operativas activas).
- BOT REINICIADO (12:31) con el seguro, sin errores.

## 27/08/2026 - BOT MULTI-SECUENCIAS: nombre nuevo + mensaje de inicio v2
- REGLA DEL JEFE: el bot se llama BOT MULTI-SECUENCIAS (mayusculas).
  Aplicado en: mensaje del panel, mensaje de inicio, log de arranque,
  titulo de la ventana (lanzar_bot.bat) y README.
- MENSAJE DE INICIO v2: arbol conectado (Estrategia con rama ├ y sus
  hijos 🔍/⚡ al mismo nivel, sin lineas sueltas) y emojis INVERTIDOS:
  correo con 👤 y cuenta con 📧.
- OPERACION EJECUTADA: el emoji ➡️ de proximo paso va DESPUES de los dos
  puntos ('PRÓXIMO PASO: ➡️ verificando resultado al cierre (1 min).').
- BOT REINICIADO (12:18) con el nombre nuevo, sin errores.

## 27/08/2026 - BOT DE SECUENCIAS: boton dinamico Iniciar/Detener operativas
- REGLA DEL JEFE: el boton superior del panel es DINAMICO - si el bot esta
  DETENIDO dice '▶️ Iniciar operativas'; si esta OPERANDO dice '⏹️ Detener
  operativas'. Implementado en telegram_reporte.teclado_principal(operativas)
  y en todos los call sites (bot.py + ui_secuencias.py) pasando
  secuencias.operativas_activas(). El handler acepta ambos textos.
- APLICADO SIN REINICIO (orden del jefe): el cambio queda en el codigo y
  toma efecto en el proximo reinicio del bot.

## 27/08/2026 - BOT DE SECUENCIAS: cambios visuales + fix reporte en ciclo
- FORMATO SECUENCIA (regla del jefe): en 'operacion ejecutada' la
  DIRECCION va AL LADO de la secuencia (fin de la ultima fila), con
  soporte para secuencias largas (20+ velas, filas de 10).
  telegram_reporte._formato_secuencia.
- FIX NIVEL GANADA (bug del jefe): plan.gana() resetea plan.nivel a 0
  ANTES de armar el mensaje, asi 'Nivel alcanzado' siempre salia MG 0.
  Ahora se captura nivel_ganada antes de plan.gana() y el mensaje
  reporta el MG real (ej. MG 4).
- EMOJI PARAMS: 'Velas a esperar' salia sin emoji en el panel de
  configuraciones; ahora todos los params llevan '⚙️'.
- FUEGUITO 🔥 (regla del jefe): SOLO aparece cuando falta UNA vela para
  completar una secuencia activa (progreso = largo - 1); ⚡ cuando esta
  completa/operada o en recuperacion vela a vela.
- FIX REPORTE EN CICLO (bug detectado en log de CHFJPY 11:55): el
  reporte minuto se enviaba en el hueco entre operativas del ciclo de
  martingala (tras perder MG0 y antes de tomar MG1). Ahora hilo_reporte
  tambien se pausa mientras _ciclo_martingala_activo no sea None (desde
  la primera perdida hasta ganar o perdida completa).
- AUDITORIA: revisados bot.py, operativa.py, estrategia, telegram_reporte,
  ui_secuencias, secuencias, timeout_utils. Sin otros bugs escondidos.
- BOT REINICIADO (11:58) con todos los cambios, sin errores.

## 27/08/2026 - BOT DE SECUENCIAS: RESULTADO RAPIDO + CICLO ENFOCADO (al :00)
- REGLA DEL JEFE: TODAS las operativas (MG0 y martingalas) al segundo
  cero. Antes el resultado llegaba a los :05-:10 (espera fija de 65s +
  poll 5s) y los MG1/2/3 se tomaban con retraso.
- FIX 1 (operativa.py esperar_resultado): calcula la EXPIRACION exacta
  (proximo :00 desde la compra), duerme hasta ella + 0.2s y consulta
  check_win_v3 cada 0.5s (primeros 5s) y luego cada 1s. El resultado
  llega a los :00-:01.5 en vez de :05-:10.
- FIX 2 (bot.py, SOLO vela a vela, regla del jefe): CICLO ENFOCADO.
  Flag _ciclo_vela_activo: cuando un activo pierde en vela a vela, el
  ciclo queda ATADO a ese activo (log 'CICLO VELA A VELA: atado a X
  hasta ganar'); los demas hilos esperan (sleep 2s) y sus senales con
  nivel de martingala se omiten (_ejecutar_operativa). Al ganar o
  perdida definitiva se cierra el ciclo y todos vuelven a escanear.
  Patron a patron queda GLOBAL (sin cambios, decision del jefe).
- VERIFICADO EN LOGS REALES (11:14-11:18): MG0 entrada :002 (segundo
  cero), perdida MG0 a los :01, MG1 entrada :568, perdida MG1 a los :00,
  MG2 entrada :881, ganada MG2 -> ciclo cerrado, nueva MG0 en NZDUSD
  entrada :004. Sin rechazos de ventana, sin arrastre, sin senales
  cruzadas de otros activos.
- BOT REINICIADO y operando (secuencia V,V,V,V->R + inversa, operativas
  activas, cuenta PRACTICE).

## 27/08/2026 - BOT DE SECUENCIAS: REINTENTO INMEDIATO vela a vela
- REGLA DEL JEFE: cuando el patron aparece y el bot ejecuta MG0, si MG0 se
  pierde, MG1 debe tomarse DE INMEDIATO (mismo minuto): los dos mensajes de
  Telegram llegan seguidos (perdida MG0 + ejecutada MG1). Operativas minuto
  a minuto.
- IMPLEMENTADO: estrategia_base.reintento_inmediato() (contrato, default
  False) + estrategia_secuencias.reintento_inmediato() (True si _ciclo_vela
  y _direccion_ciclo). bot.py hilo_activo: tras _ejecutar_operativa, while
  reintento_inmediato (max 10): lee velas frescas, alimentar, si dispara
  ejecuta AL INSTANTE (sin dormir_hasta_cero). La regla de ventana sigue
  protegiendo (si el resultado llega con seg >= 50, difiere al :00).
- LOGS VERIFICADOS (corrida 10:00-10:19, con el fix de ventana pero SIN el
  inmediato): la martingala funciono sin rechazos de ventana (entradas
  :000-:008), pero MG1 se tomo ~56s despues de la perdida (perdida 10:05:06
  -> MG1 10:06:02). Con el fix nuevo sera inmediato.
- HALLAZGO: rechazo 'Insufficient funds' en MG4 ($26.42) - el saldo de la
  cuenta PRACTICE no cubria la escalera completa (1.18+2.56+5.58+12.14+
  26.42+57.50 = ~105). Con vela a vela inmediata la escalera sube mas
  rapido: revisar saldo o bajar niveles_max si hace falta.
- OJO: las pruebas de verificacion borraron secuencias.json (las secuencias
  del jefe se perdieron; hay que recrearlas desde Telegram).
- BOT REINICIADO (10:28) con el fix, corriendo sin errores.

## 27/08/2026 - BOT DE SECUENCIAS: fix VENTANA DE EXPIRACION (vela a vela)
- PROBLEMA (reportado por el jefe): en vela a vela, las operativas MG1/MG2/
  MG3 se rechazaban con 'ventana de expiracion cerrandose' y el bot entraba
  en ARRASTRE (SE QUEDA) aunque el activo estuviera disponible.
- CAUSA RAIZ (diagnosticada en bot.log): el stream solo entrega velas
  CERRADAS (velas.py get_velas_stream filtra la vela en formacion). El
  bucle despierta a los :59.55 (dormir_hasta_cero con anticipo 0.45s) y el
  poll rompe al instante (la ultima vela cerrada tiene cierre en el
  pasado). alimentar disparaba la senal a los :59.55 con el proximo :00 a
  <10s -> buy_seguro rechaza 'ventana de expiracion cerrandose' -> arrastre
  -> reconstruir -> vuelve a disparar a los :59.55 -> bucle de rechazos
  cada minuto (log: EURGBP 08:35:59, USDJPY 08:37:59, AUDUSD 08:38:59...).
- FIX (estrategia_secuencias.py): regla de VENTANA DE EXPIRACION. La
  estrategia recibe el desfase del broker via configurar(desfase=...) y NO
  dispara si _seg_broker() >= 50.0 (faltan <10s para el :00): difiere la
  senal al proximo cierre de vela (estado 'activo'), donde la compra tiene
  la ventana completa de 60s. Aplica a los DOS disparos (vela a vela y
  patron). Con esto MG1 cae en la vela 6, MG2 en la 7, etc. (como pidio el
  jefe: entrada vela 5, martingalas 6,7,8,9,10).
- VERIFICADO: 11 pruebas de ventana (difiere a 59.5/50.0, dispara a
  0.5/49.9, vela a vela y patron) PASAN. py_compile OK, import OK.
- BOT REINICIADO en ventana visible con el fix.

## 27/08/2026 - BOT DE SECUENCIAS: cambios v2 (10 activos + tipo de martingala)
- REGLA DEL JEFE: reducir a 10 activos. Los 6 del BOT ESTADISTICO ACTIVOS:
  GBPUSD-OTC, EURGBP-OTC, EURJPY-OTC, GBPJPY-OTC, NZDUSD-OTC, EURUSD-OTC.
  + 4 MÍOS DESACTIVADOS (activables desde 📊 Activos): AUDCAD-OTC, USDJPY-OTC,
  AUDUSD-OTC, CADJPY-OTC. (El config del estadístico tiene 7 con AUDCAD; se
  dejó AUDCAD como desactivado.)
- TIPO DE MARTINGALA (regla del jefe, igual que el BOT ESTADISTICO):
  config.json "tipo_martingala": "vela" (defecto) | "patron". Selector en
  Configuraciones -> '🧩 Tipo de martingala' (bot.py menu 'tipomg').
  * vela: si la entrada se pierde, el siguiente nivel se opera en la
    SIGUIENTE vela (misma direccion): patron 4 velas -> entrada vela 5,
    martingala velas 6,7,8,9,10... hasta ganar o agotar niveles.
  * patron: tras perder, espera a que la secuencia REAPAREZCA.
  Implementado en estrategia_secuencias.py (_ciclo_vela/_direccion_ciclo,
  registrar_resultado decide el modo; configurar recibe tipo_martingala).
- ARRANQUE DETENIDO + REPORTE (regla del jefe): el bot arranca con
  operativas DETENIDAS y NO envia el reporte minuto a minuto (hilo_reporte
  salta si not secuencias.operativas_activas()). 'Iniciar operativas' con
  CERO secuencias activas -> mensaje 'NO HAY SECUENCIAS PARA OPERAR' y NO
  inicia; con >=1 secuencia -> inicia y escanea con ella.
- VERIFICADO: py_compile OK, import OK (tipo_martingala vela, 10 activos,
  6 activos_activos), 17 pruebas de martingala (vela y patron) PASAN.
- BOT REINICIADO en ventana visible (lanzar_bot.bat). El jefe probo los
  botones desde Telegram (volver, principal, secuencias activas) OK.

## 27/08/2026 - BOT NUEVO: BOT DE SECUENCIAS (base creada y verificada)
- Regla del jefe: crear un bot tipo BOT ESTADISTICO pero EN VIVO: se crean
  secuencias de velas (R/V) con direccion esperada y el bot las opera cuando
  aparecen en el mercado. Proyecto: `Documents/python projects/BOT-SECUENCIAS/`
  (copia de la PLANTILLA-IQ-OPTION del Escritorio, la universal).
- PANEL TELEGRAM (4 botones, regla del jefe): '▶️ Iniciar operativas' arriba,
  '➕ Crear secuencias' y '📋 Secuencias activas' al lado, '⚙️ Configuraciones'
  debajo. Implementado en telegram_reporte.teclado_principal().
- `patrones.py` (NUEVO): modelo Patron del BOT ESTADISTICO adaptado (id,
  activa, persistencia). `secuencias.py` (NUEVO): almacen global con lock +
  secuencias.json (persiste secuencias y el flag de operativas).
- `estrategia_secuencias.py` (NUEVO): maquina por activo. Compara las ultimas
  velas CERRADAS contra las secuencias activas (incluye inversas). UNA
  aparicion = UNA operativa (espera a que la secuencia se ROMPA para
  re-disparar). Parametro 'espera_velas' (0-5, default 0). CONFIRMAR_CIERRE
  = False: la coincidencia exacta del patron es la confirmacion (la
  confirmacion pre-buy de la plantilla pide la vela CONTRARIA y no aplica).
- `ui_secuencias.py` (NUEVO): wizard de creacion (rojo/verde vela a vela,
  direccion, inversa, nombre) + gestion (activar/desactivar, borrar una/
  todas). bot.py le delega los mensajes mientras el wizard esta activo.
- CREDENCIALES: WASCARFLOW3 (wascarflow3@gmail.com / 24WASCAR16...) + token
  @NuevaIdeaBot (8753037105, chat 8456515934), PRACTICE. config.json:
  estrategia "secuencias".
- VERIFICADO: py_compile 13 modulos OK, import bot OK, 16 pruebas de logica
  (disparo, no re-disparo, romper y re-disparar, inversa, espera_velas,
  persistencia) y 25 pruebas del wizard (mock Telegram) TODAS PASAN.
- PENDIENTE: probar en vivo (python bot.py) y crear secuencias desde
  Telegram. El bot arranca con operativas DETENIDAS (boton Iniciar
  operativas para encender).

## 23/08/2026 - BOT NUEVO: PICOS DE MECHAS (creado, verificado, SIN desplegar)
- Estrategia nueva del jefe: PICOS DE MECHAS. Proyecto:
  `Documents/python projects/PICOS DE MECHAS/` (copia de la base de IQ EL
  PUNTO 3 / IQ alternaciones: velas.py, sincronizacion.py, riesgo.py,
  operativa.py, timeout_utils.py, telegram_reporte.py, iqoptionapi parcheada).
- `estrategia_picos.py` (NUEVO): maquina por activo. El AREA nace de una
  vela pico con mecha >= picos_mecha_min_ticks (2): area = [max(open,close),
  high] (caso A: cierra del color contrario -> base = apertura; caso B:
  cierra del mismo color -> base = cierre). Espejo inferior (soporte) con
  picos_usar_soporte. TOQUE VALIDO: vela entra al area con su mecha y cierra
  POR DEBAJO (sale por donde vino). INVALIDA: vela que cierra DENTRO del
  area o la ATRAVIESA. Al llegar a picos_toques (4) -> NIVEL SOLIDO; punto de
  entrada = PROMEDIO de penetracion de los toques. Senal: vela VIVA toca el
  punto promedio DENTRO del margen de compra (picos_margen_compra_seg, 30s);
  si toca fuera del margen ESA senal se descarta (se espera si o si una vela
  que toque el punto dentro del margen). Direccion: PUT si resistencia,
  CALL si soporte (a favor del rebote).
- `bot.py` (NUEVO, reescrito sobre la base): martingala GLOBAL (riesgo.py,
  RLock), una operativa a la vez, disparo INTRABAR (vigila la vela viva con
  poll 0.5s cuando el nivel esta solido), expiracion al proximo :00
  (buy_seguro con exp_base=None), watchdogs (congelamiento 3min, zombies,
  conexion), reporte Telegram minuto a minuto (reporte_picos en
  telegram_reporte.py: area, toques X/Y, punto de entrada), teclado
  Telegram (martingala, objetivo, monto auto, cuenta, activos, sesion).
- config.json: picos_toques=4, picos_mecha_min_ticks=2,
  picos_margen_compra_seg=30, picos_usar_soporte=true. Cuenta PRACTICE
  wasc4r24@gmail.com. TOKEN TELEGRAM = PONER_AQUI (regla: no dobles tokens;
  el jefe debe asignar uno nuevo o liberar uno).
- VERIFICADO: py_compile OK (PY312), imports OK, tests unitarios 28/28 OK
  (Temp/opencode/test_picos.py), simulacion con datos reales
  (Temp/opencode/simulacion_picos.py): 51,720 areas en 60 dias, 1,276
  niveles solidos (2.47% de las areas, ~2 senales/activo/dia). NOTA: los
  datos de velas no traen high/low; se estimaron (mecha = 40% del cuerpo);
  validacion real pendiente en PRACTICE.
- PENDIENTE: token Telegram, prueba en PRACTICE, push a GitHub/despliegue
  cuando el jefe lo ordene. NO tocar IQ alternaciones ni el respaldo.

## 23/08/2026 (noche) - PICOS DE MECHAS: panel, auditoria y regla del 3%
- PANEL CONFIGURACIONES Y ESTADO actualizado (telegram_reporte.py
  mensaje_configuraciones + teclado_configuraciones): ahora lista TODOS los
  parametros con emoji UNICO por parametro (Activos N/M, MG abreviado,
  Porcentaje de zona, Zona ajustable, Toques, Tiempo de analisis, Ganancia
  objetivo, Proximo monto, Monto auto). El boton 'Porcentaje de zona' cambio
  de 🎯 a 🎚️ (el 🎯 quedaba duplicado con Martingala). Saldo Real paso a 🏦
  y Proximo monto a 💸 (des-duplicar 💵/💰). 'Martingala' abreviado a 'MG'
  para no romper el arbol. bot.py pasa los valores vivos en las 4 llamadas.
- AUDITORIA (log real): 0 errores, 0 rechazos, 19 operativas, martingala
  global OK. HALLAZGO: hubo DOBLE INSTANCIA ~21:05-21:13 (reportes y
  operativas duplicadas, MG por separado); resuelto (hoy 1 solo proceso).
  FIX aplicado: el reporte minuto/completo/resincronizacion recalculaban el
  area con DEFAULTS (10%/NO/20min) sin la config viva; ahora observar_estado
  y estado_observado reciben entrada_porcentaje, zona_ajustable,
  tiempo_analisis_min y penetracion_min_pct (bot.py:436, 1224, 1701).
- REGLA NUEVA DEL JEFE (23/08/2026): PENETRACION MINIMA DEL TOQUE. Un toque
  valido debe penetrar al menos el 3% de la zona (picos_penetracion_min_pct,
  default 3.0, configurable 0-100 en config.json, SIN boton de Telegram por
  ahora): resistencia -> high >= base + 3%*(tope-base); soporte -> low <=
  base - 3%*(base-tope). Menos no cuenta. Implementado en
  estrategia_picos.py (_evaluar_vela_area) + config viva + tests.
- VERIFICADO: py_compile OK (todos los .py), tests 58/58 OK
  (Temp/opencode/test_picos.py, 6 nuevos de penetracion). PENDIENTE DE
  REINICIO: el bot corre con el codigo viejo; reiniciar para aplicar.

## 23/08/2026 (madrugada) - PICOS DE MECHAS: reporte con maquina real + aviso nivel solido
- FENOMENO INVESTIGADO (EURGBP 23:47): el bot tomo una entrada valida
  (4/4 toques, GANADA) que NUNCA se mostro en el top 5. Causas: (1) el
  reporte minuto RECONSTRUIA el area con velas frescas (observar_estado) y
  esa reconstruccion DIVERGIA de la maquina real (caducidad evaluada contra
  la hora actual, pico distinto); (2) la entrada ocurrio entre reportes
  (solidifico 23:47:00, entro 23:47:24); (3) el reporte del minuto de la
  entrada se PAUSA por la operativa en curso. La entrada fue 100% valida.
- FIX 1: el reporte minuto y el reporte completo ahora muestran el estado
  de la MAQUINA REAL (est.estado, est.descripcion(), est.area_info()) en
  vez de la reconstruccion observada; las velas y el precio siguen frescos
  del stream. La caducidad de 20 min la maneja la maquina, no se muestran
  areas viejas. observar_estado/estado_observado quedan SOLO para
  _resincronizar_escaneo.
- FIX 2: aviso breve por Telegram al detectarse NIVEL SOLIDO (solo en la
  transicion, en _log_transicion_estrategia): '⚡ NIVEL SÓLIDO: activo
  (nivel para vender/comprar) — X/Y toques. Punto de entrada: Z'.
- FIX 3: log de toques: _ult_toques_log se resetea cuando el area cambia
  (ts_pico distinto), para que el primer toque de cada area nueva SIEMPRE
  se registre en bot.log.
- PENDIENTE DE REINICIO (el jefe pidio NO reiniciar aun): aplicar los 3
  fixes + los anteriores (regla 3%, fuego derivado, orden por toques,
  panel) en el proximo reinicio.

## 24/08/2026 (madrugada) - PICOS DE MECHAS: cuenta wascarflow3, tiempo 15, emojis, GitHub y NUBE
- CUENTA: credenciales.py ahora usa CUENTA_ACTIVA = "WASCARFLOW3"
  (wascarflow3@gmail.com, password 24WASCAR16..., la de IQ-ULTIMATE /
  BOT-ALTERNACIONES-DEPLOY). Token de Telegram se MANTIENE el de PICOS DE
  MECHAS (@NuevaIdeaBot 8753037105, chat 8456515934). Tipo PRACTICE.
- TIEMPO DE ANALISIS: presets del teclado ahora 10/15/20/25/30/60 min
  (10 minimo) y DEFAULT cambiado a 15 min (config.json + todos los
  defaults de bot.py, estrategia_picos.py y telegram_reporte.py).
- EMOJIS DE DIRECCION: '⬇ Nivel para vender' (PUT/resistencia) y
  '⬆ Nivel para comprar' (CALL/soporte) en reporte_picos y en
  descripcion()/descripcion_estado (aviso de nivel solido incluido).
- BLINDAJE DE RECHAZOS verificado: rechazo del broker (activo cerrado /
  sin expiracion) -> OPERACION RECHAZADA por Telegram, turno liberado y
  los demas activos siguen operando; con MG1+ usa el protocolo de
  arrastre (se queda reintentando ese activo).
- GITHUB: repo privado creado y subido: wascar2416-star/PICOS-DE-MECHAS
  (branch main, gh autenticado). .gitignore excluye logs/__pycache__/
  credenciales.json; credenciales.py va en el codigo (estilo del jefe).
- NUBE (RAILWAY): el proyecto impartial-compassion tenia 2 servicios
  OFFLINE (IQ-EL-PUNTO-3 e IQ-ULTIMATE-SPECIAL). Se REEMPLAZO
  IQ-EL-PUNTO-3: railway link -p impartial-compassion -s IQ-EL-PUNTO-3 +
  railway up desde PICOS DE MECHAS. El bot corre en la nube (logs OK:
  conectado PRACTICE, aviso de inicio, streams suscritos). IQ-ULTIMATE-
  SPECIAL queda intacto.
- OJO DOBLE INSTANCIA: la nube y el bot LOCAL usan el MISMO token de
  Telegram -> si ambos corren, duplican avisos. Decidir: detener el
  local o la nube. El bot local aun corre con el codigo viejo (cuenta
  wasc4r24, tiempo 20, sin emojis) -> reiniciar o detener segun el jefe.
- VERIFICADO: py_compile OK, tests 58/58 OK, 13 teclados OK, panel OK
  (wascarflow3, 15 min), render con emojis OK.

## 24/08/2026 (mañana) - RESPALDO CORRIENDO + REGLA DEL JEFE
- RESPALDO: _backup_PICOS_DE_MECHAS (copia del proyecto al 24/08 07:22,
  79 archivos). Configurado por el jefe: cuenta WASCAR (wasc4r24@gmail.com,
  la ANTERIOR), token de Telegram de IQ ULTIMATE (@ElPunto3Bot
  8755149629:AAGxNI-h38f3C6pYgWPYz-6yEGKmUAkhgF0, para no duplicar con la
  nube), picos_entrada_porcentaje=20, picos_penetracion_min_pct=20, y
  OPERATIVAS INVERTIDAS (nivel para vender -> COMPRAR, nivel para comprar
  -> VENDER; la senal se detecta con las reglas normales, solo la compra
  y los mensajes van invertidos; log marca '(INVERTIDA)'). CORRIENDO en la
  PC (bot.py del respaldo, ventana visible).
- REGLA DEL JEFE (24/08/2026): NO TOCAR el bot de respaldo por ahora.
  De aqui en adelante se trabaja UNICAMENTE con el bot ORIGINAL (PICOS DE
  MECHAS, el activo, desplegado en la nube Railway). El respaldo solo se
  toca si el jefe lo pide EXPLICITAMENTE.
- NOTA: wally_telegram_bot.py (resto de WALY) reaparecio corriendo en la
  PC (07:16); el jefe no pidio cerrarlo en ese momento.

## 24/08/2026 (tarde) - V2: MODULOS DIVIDIDOS + REPO NUEVO + NUBE
- REFACTOR V2 (regla del jefe: modulos mas chicos y faciles de editar):
  - bot.py (1988 lineas) dividido en: estado.py (416, estado global +
    config viva + saldos + sesion + activos + log), ejecucion.py (376,
    operativa: ejecutar, vigilar, resincronizar), telegram_bot.py (724,
    hilo Telegram + menus + reporte completo), bot.py (479, hilos de
    activo + reporte minuto + vigilantes + main).
  - telegram_reporte.py (1074) dividido en: tg_utils.py (80), tg_teclados
    (137), tg_selectores (212), tg_reportes (311), telegram_reporte (55,
    re-exporta).
  - CODIGO MUERTO ELIMINADO (~350 lineas): reporte_velas, _emoji_estado,
    _emoji_estado_picos, _linea_profit, _linea_profit_global,
    _linea_proximo_paso, teclado_alternancia, mensaje_alternancia,
    enviar_teclado, bot_iniciado, _confirmar_contraria, VENTANA_CONFIRMA,
    _saldo_cuenta.
  - PATRON V2: estado.py es el punto unico de verdad; las variables que se
    REASIGNAN en runtime (config, _API_GLOBAL, _plan_global, _TG_TOKEN,
    _TG_CHAT, _EMAIL_ACTUAL, _profit_season, _ciclo_martingala_activo,
    _mudanza_pendiente, _activos_activos, _obj_monto_auto_global,
    _ultima_linea_log, _resultado_global) se leen SIEMPRE como estado.X;
    las mutaciones de dicts usan 'from estado import *' (con __all__ al
    final de estado.py). log() y _rotar_log() viven en estado.py.
- GITHUB: repo NUEVO privado wascar2416-star/PICOS-DE-MECHAS-V2 (la V1
  PICOS-DE-MECHAS queda intacta como respaldo). El proyecto local apunta
  al V2.
- NUBE: el V2 se desplego en Railway SUSTITUYENDO la V1 (servicio
  IQ-EL-PUNTO-3, proyecto impartial-compassion). Verificado: aviso de
  inicio, panel, reporte minuto, 0 errores. Fixes en el camino: import
  requests en telegram_bot, tg_token/tg_chat -> estado._TG_TOKEN.
- VERIFICADO: py_compile OK (16 modulos), tests 63/63, import bot OK,
  nube operando sin errores.

## 24/08/2026 - Tarea escolar: operadores logicos JS (PDF de respuestas)
- El usuario tenia en Descargas `ejercicios_operadores_logicos_javascript.pdf` (tarea de 20 ejercicios de operadores logicos en JavaScript: &&, ||, !).
- Le genere `C:\Users\wasc4\Downloads\ejercicios_operadores_logicos_respuestas.pdf`: mismo estilo que la tarea (encabezado + numero de pagina), 20 respuestas enumeradas, cada una con su enunciado y el codigo en bloque monoespaciado con fondo gris.
- Herramientas: pypdf (leer PDF) y reportlab (generar PDF). Script de generacion en `C:\Users\wasc4\AppData\Local\Temp\opencode\generar_respuestas.py`.
- Aprendizaje: el modelo no lee PDFs directo; extraer texto con pypdf a un .txt UTF-8. Para crear PDFs con formato usar reportlab (Platypus + Preformatted para codigo).

## 24/08/2026 - PROTOCOLO DE PLAN (regla del usuario, OBLIGATORIA)
- REGLA: cada vez que el jefe pida implementar/crear/hacer una tarea ("Jarvis quiero implementar esto", "quiero hacer esto", "realizame esta tarea", "verifica y hazlo"), JARVIS debe PRIMERO presentar un plan breve de lo que va a hacer: objetivo, pasos esenciales, preguntas necesarias, y al final recordar SIEMPRE: "Si quieres, dime sin plan y lo hago directo."
- Si el jefe dice "sin plan" (o "hazlo directo", "procede"), ejecutar de inmediato sin plan, con la misma inteligencia de siempre.
- El plan es BREVE (2-4 frases, formato de voz, sin markdown). Las preguntas van DENTRO del plan como texto; nunca preguntas interactivas que bloqueen.
- Agente de referencia: cree `C:\Users\wasc4\.config\opencode\agent\plan.md` (estilo doctor.md) como plantilla de planificacion. El agente doctor vive en la misma carpeta.
- Aplica a CUALQUIER tarea de trabajo, no a conversacion simple ni preguntas de informacion.

## 24/08/2026 - CAMBIO DE MODELO: opencode-go -> opencode-zen (por pago)
- El proveedor opencode-go (Console Go) empezo a fallar: endpoint no encontrado y luego "No payment method" (exige metodo de pago en opencode.ai/workspace).
- SOLUCION APLICADA: cambie el modelo principal y small_model en `C:\Users\wasc4\.config\opencode\opencode.json` de `opencode-go/deepseek-v4-flash` a `opencode-zen/deepseek-v4-flash-free` (gratuito, sin tarjeta).
- Tambien actualice el modelo en los agentes: jarvis.md (global y proyecto), doctor.md y plan.md -> opencode-zen/deepseek-v4-flash-free.
- PENDIENTE: reiniciar opencode para que tome efecto. Si opencode-zen pide OPENCODE_API_KEY y no esta definida, definirla o verificar que el modelo free funcione sin key.
- Nota (01/09/2026): el sistema de voz completo fue eliminado (asistente_voz.py,
  carpeta voz_kokoro, motores de voz); el sistema activo es solo Telegram.

## 24/08/2026 - Albot Picos de Mechas: riesgos latentes (medios) resueltos
- Retome la sesion 'Configurar y ejecutar Albot localmente' (Albot de Picos de Mechas, repo wascar2416-star/PICOS-DE-MECHAS-3, rama master, carpeta C:\Users\wasc4\Downloads\PICOS-DE-MECHAS-main).
- Resolvi los 6 riesgos latentes (medios) de la auditoria 30 dias, commit 2a8f1b4, push OK (auto-deploy Railway):
  1) check_win_v3 (stable_api.py): while True sin sleep -> sleep 0.2s (evita hilos zombie 100% CPU).
  2) order_async: se purga tras check_win (pop del id) para que la memoria no crezca en 30 dias.
  3) Desfase: bidireccional (antes solo subia, umbral 50ms) + hilo_reporte re-mide el desfase en vivo (antes fijo del arranque).
  4) Saldo: _leer_saldo_panel con TTL 25s en los paneles de teclado (antes llamada de red en cada pulsacion).
  5) Reinicios: _reiniciar_con_backoff con minimo 10 min entre os.execv (3 puntos: zombies, vigilante, congelamiento).
  6) Rama mg: acotada a menu_actual=='mg' y rango 0-10 (antes texto libre 'mg 5' desde cualquier menu).
- Verificado: py_compile OK (bot.py, stable_api.py) + smoke test 4/4 (check_win_v3, backoff, desfase, rama mg).
- Los hallazgos ALTOS (A1-A7) siguen pendientes para cuando el jefe los pida.

## 24/08/2026 - Albot Picos de Mechas: 3 peligrosos (A1, A2, A6) resueltos
- Copia de seguridad previa en el escritorio: 'Pico de mechas respaldo 2026-08-25_00-01-07' (79 archivos, sin .git ni __pycache__).
- Resolvi los 3 hallazgos ALTOS mas peligrosos, commit 6a35bf3, push OK (auto-deploy Railway):
  A1) Heartbeat cada 30s en esperar_resultado (operativa.py): alimenta _ultima_linea_log para que el watchdog de congelamiento (180s) NO reinicie a mitad de operacion (antes operacion huerfana + martingala reseteada).
  A2) Sin resultado (timeout) ya NO marca falso ciclo cerrado: nuevo metodo registrar_sin_resultado() en estrategia_picos.py (antes registrar_resultado(True) con resultado desconocido). bot.py usa registrar_sin_resultado() en el branch None.
  A6) config.json con escritura ATOMICA (tmp + os.replace) en _guardar_config_viva + cargar_config (riesgo.py) con try/except que devuelve {} (antes crash-loop al arrancar si quedaba corrupto).
- Verificado: py_compile OK (bot, operativa, estrategia_picos, riesgo) + smoke test 3/3.
- Pendientes de la auditoria: A3 (ciclo martingala stale), A4 (gana() suma bruto), A5 (stream muerto en nivel solido), A7 (log sin poda). El jefe dijo que son ajustes delicados, no resolverlos por ahora.

## 24/08/2026 - Albot Picos de Mechas: DOS AREAS EN PARALELO por activo
- Regla del jefe: un activo puede tener DOS niveles (resistencia/put y soporte/call). El bot escanea AMBOS en paralelo; la PRIMERA que llegue a nivel solido se opera (sin esperar a la otra). La otra queda OCULTA como respaldo y se promueve si la principal se invalida. Empate de toques: gana la que se formo primero (ts_pico menor). El reporte solo muestra la elegida.
- Implementado en estrategia_picos.py: self.area_oculta + metodos _crear_area_contraria, _promover_oculta, _evaluar_oculta, _evaluar_vela_area_sobre, _ajustar_area_sobre, _area_caduca. _invalidar_area promueve la oculta si existe. bot.py: resets manuales (rechazo operativa, DOJI) tambien resetean area_oculta.
- Commit 551f246, push OK (auto-deploy Railway). Verificado: py_compile + smoke test 5/5 + test de integracion con velas simuladas (soporte oculta llega a solida y se promueve).

## 24/08/2026 - CAMBIO DE MODELO: opencode-zen free NO funciona -> omniroute/openrouter
- Diagnostico: opencode-zen/deepseek-v4-flash-free responde 'Model is unavailable' (el free no esta disponible para generar en el proveedor Console). El de pago (deepseek-v4-flash) pide metodo de pago. opencode-go sin cuota (403). El endpoint zen ademas bloquea con Cloudflare 1010 si no se usa User-Agent de navegador.
- SOLUCION: modelo principal y small_model -> `omniroute/openrouter/deepseek/deepseek-v4-flash` (proxy local OmniRoute en localhost:20128, que enruta a OpenRouter donde deepseek-v4-flash es GRATUITO). Anadido a la lista de models del proveedor omniroute en opencode.json. Agentes jarvis/doctor/plan actualizados al mismo modelo.
- Verificado: prueba real de generacion via omniroute -> 'OK' (funciona). JSON valido.
- PENDIENTE: reiniciar opencode para que tome efecto.

## 26/08/2026 - SERVIDOR LLAMA.CPP: modelo ToMoE de Nichonauta (implementado y CORRIENDO)
- El jefe quiere un modelo de nicho de Nichonauta (Hugging Face) para su asistente de Telegram, corriendo en su GPU (NVIDIA RTX 3070, 8GB).
- Elegido: `LFM2.5-350M-ToMoE-BF16.gguf` (678 MB, en `C:\Users\wasc4\Downloads\`), el menos degradado de la serie ToMoE (conversiones MoE de LiquidAI LFM2.5; el 1.2B-Thinking NO es usable como chat segun el autor, el 230M esta muy degradado).
- llama.cpp del usuario: `C:\Users\wasc4\Downloads\LLAMACPP\` (build 10590, con CUDA: ggml-cuda.dll, cublas64_13.dll).
- Script de arranque creado: `C:\Users\wasc4\Downloads\LLAMACPP\iniciar_tomoe.bat` (llama-server con -ngl 99, puerto 8080, ctx 4096, alias LFM2.5-350M-ToMoE-BF16).
- VERIFICADO: servidor corriendo en http://127.0.0.1:8080, /v1/models OK (354M params, BF16), generacion real OK (41 tokens, responde en espanol).
- USO: navegador -> http://127.0.0.1:8080 (web UI de llama.cpp); Telegram/bot -> API OpenAI-compatible http://127.0.0.1:8080/v1/chat/completions con model "LFM2.5-350M-ToMoE-BF16".
- PENDIENTE: conectar el asistente de Telegram del jefe a esta API (el jefe indicara cual bot/proyecto).

## 26/08/2026 - CAMBIO DE MODELO LOCAL: LFM2.5-1.2B-Thinking-ToMoE-BF16 (2.34 GB)
- El jefe pidio probar el modelo de razonamiento de Nichonauta: `LFM2.5-1.2B-Thinking-ToMoE-BF16.gguf` (2.34 GB, en Downloads). Es el ToMoE del LiquidAI LFM2.5-1.2B-Thinking (razonamiento RL).
- `iniciar_tomoe.bat` actualizado: llama-server con -ngl 99, puerto 8080, ctx 4096, alias LFM2.5-1.2B-Thinking-ToMoE-BF16. Se detuvo el servidor del 350M y se lanzo el nuevo.
- VERIFICADO: /v1/models OK (1.17B params, BF16). Generacion real OK con max_tokens >= 1024: el modelo piensa (reasoning_content en ingles) y luego emite la respuesta final en espanol (281 tokens, finish stop). CON max_tokens bajos (200) se corta en el pensamiento y el content llega VACIO (finish length) -> el bot de Telegram necesita presupuesto alto de tokens (usa 4096, OK).
- BOT TELEGRAM (wally_telegram_bot.py, PID en segundo plano): espera LFM_MODELO="LFM2.5-2.6B" en el puerto 8080; llama.cpp ignora el nombre y usa el cargado, pero conviene actualizar LFM_MODELO a "LFM2.5-1.2B-Thinking-ToMoE-BF16" y reiniciar el bot para que quede limpio. PENDIENTE de confirmacion del jefe.
- OJO: el autor advierte que este ToMoE de razonamiento tiende a repetirse y NO es un asistente de chat usable; el 350M era mas estable para conversacion. El jefe quiere probarlo igual.

## 26/08/2026 - FIX RECHAZO EN MARTINGALA (VELAS-DOJIS y DOJIS-FAMILY)
- Problema reportado por el jefe: con martingala pendiente (MG1+), un activo que cumple las condiciones y esta operable era rechazado con 'sin tiempo de expiracion disponible' y el bot guardaba arrastre. La entrada inicial nunca fallaba.
- CAUSA (verificada en logs): la senal de martingala puede aparecer en el segundo 50-59 del minuto; `_expiry_valido()` calculaba la expiracion al proximo :00, que caia a <10s (ventana cerrandose) -> `_comprar_principal` devolvia 'ventana de expiracion cerrandose' -> rechazo. Todos los rechazos del log ocurren a las :59.
- FIX (operativa.py, `_comprar_principal`): si la ventana se esta cerrando, el bot ESPERA al :00 (max ~10s) y compra con la expiracion del :00 siguiente: la entrada cae en el segundo 0 del minuto nuevo (lo mas cerca del :00, como pide el jefe). Si tras esperar sigue sin expiracion valida, recien ahi rechaza (fallback seguro).
- VELAS-DOJIS (nube/Railway): fix aplicado, py_compile OK, commit 0841381 PUSHEADO a GitHub (master). Railway se actualiza con el deploy automatico. Copia local nueva: `Documents/python projects/VELAS-DOJIS/`.
- DOJIS-FAMILY (local): mismo fix aplicado en operativa.py, py_compile OK. PENDIENTE de commit/push (el jefe pidio push UNICAMENTE a Velas Dojis). Tambien sigue pendiente el cambio del emoji al lado del nombre del activo (telegram_reporte.py, ya editado en working tree).
- LECCION: los rechazos 'sin tiempo de expiracion' a las :59 son falsos rechazos por ventana cerrandose; la solucion es esperar al :00, nunca rechazar la operativa si el activo esta operable.

## 26/08/2026 - ROBUSTEZ ANTI-CAIDAS + PERSISTENCIA DE MARTINGALA (VELAS-DOJIS y DOJIS-FAMILY)
- Problema: el bot se reiniciaba solo en plena martingala. Diagnostico en logs de Railway: el websocket con IQ Option se degrada (timeSync falla en todos los activos, buys con timeout) -> se acumulan zombies -> el watchdog `_aviso_zombies` (umbral 3+ zombies nuevos) reiniciaba TODO el proceso con os.execv, borrando el estado de martingala en memoria. El 26/08 17:33 el bot se reinicio justo tras perder MG0 en EURGBP (estaba buscando MG1).
- FIX 1 (watchdogs con reconexion suave): `_aviso_zombies(api)` y `_hilo_vigilante_conexion` ahora llaman `reconectar(api)` (repara websocket + re-suscribe streams SIN perder estado) antes de os.execv; el reinicio completo queda solo si la reconexion falla. `_hilo_watchdog_congelamiento` se mantiene (ultimo recurso).
- FIX 2 (desfase compartido): nuevo `_hilo_medir_desfase(api)` mide el desfase del broker UNA vez cada 60s y lo comparte (`_desfase_global` + `_leer_desfase_global()`); los hilos de activo ya NO miden por su cuenta (antes 20 mediciones -> 20 timeouts en cascada al degradarse el websocket).
- FIX 3 (persistencia): nuevo `persistencia_estado.py` guarda `estado_martingala.json` (escritura atomica tmp+os.replace) con nivel, perdidas_acumuladas, resultado_dia, ciclo_activo, mudanza_pendiente, activo_casado, profit_season, stats, stats_por_activo. Se guarda tras cada operativa resuelta y en el reporte minuto; se restaura en main() si es reciente (<12h). Se borra al cambiar de cuenta. NO se persiste _pausa_definitiva (el reinicio es el mecanismo para reactivar).
- NO se toco: estrategia, senales, puntos de entrada, expiracion, compra, martingala (riesgo.py).
- VELAS-DOJIS: commit 4acf4de PUSHEADO a GitHub (Railway redespliega solo). Verificado: py_compile OK, test_persistencia 5/5, test_reinicio (MG2 -> reinicio -> MG2, monto $7.06 correcto).
- DOJIS-FAMILY: mismos cambios aplicados en local (bot.py, persistencia_estado.py, .gitignore), py_compile OK, test_dojis_family 5/5 (MG4 -> reinicio -> MG4, monto $24.71). SIN commit/push (regla del jefe: push unicamente a Velas Dojis). PENDIENTE: reiniciar el bot local para que tome los cambios + commit/push cuando el jefe lo ordene. Tambien siguen pendientes en working tree: fix rechazo martingala (operativa.py) y quitar emoji (telegram_reporte.py).

## 26/08/2026 - FIX CAMBIO DE CUENTA (VELAS-DOJIS, commit afeca66 PUSHEADO)
- Problema detectado: al cambiar de cuenta con martingala pendiente, `_cambiar_tipo_cuenta` reiniciaba el plan (nivel, perdidas, resultado, profit, stats, casamiento, estado persistido) PERO dejaba dos residuos: `_ciclo_martingala_activo` (el activo seguia 'casado': no se podia apagar desde Telegram) y `_mudanza_pendiente` (la primera operativa de la cuenta nueva adoptaba el monto arrastrado de la cuenta vieja).
- Fix: en `_cambiar_tipo_cuenta` se limpian tambien `_ciclo_martingala_activo = None` y `_mudanza_pendiente = None` (con global). La cuenta nueva entra 100% limpia.
- Aplicado SOLO en VELAS-DOJIS (regla del jefe), commit afeca66, push a GitHub OK, Railway redesplegado (arranque 22:03 UTC, operando normal).
- VERIFICACION DE INTEGRIDAD COMPLETA (bot 100% para cuenta real): 14 modulos py_compile 0 fallos, imports OK, fix rechazo martingala presente en operativa.py, persistencia tests OK, config 20 activos OTC + estrategia dojis, credenciales por env vars en Railway (IQ_EMAIL, IQ_PASSWORD, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID), Railway Online conectado al repo, sin errores en logs. Para pasar a REAL: boton del panel de Telegram (cambia balance, limpia todo y opera en real).

## 26/08/2026 - ENTRADA AL :00 BLINDADA + 17 ACTIVOS (VELAS-DOJIS, commit b4dc5d2 PUSHEADO)
- Problema (caso CADCHF 22:11 UTC): la operativa se abrio a los 41s del :00 (19s de vida). Causa: websocket degradado + fix 0841381 (esperar al :00 cuando la ventana se cierra) que usa el metodo principal con timeout 20s x2 = 40s muertos antes del fallback. Comparacion con la copia de seguridad (Desktop/Velas dojis respaldo, version 11:41): la degradacion del websocket YA existia el 25/08 (zombies y watchdogs con los 20 activos), pero el respaldo rechazaba la ventana cerrada AL INSTANTE y caia rapido al fallback api.buy (entradas de 1-2s). El problema NO era la cantidad de activos ni los hilos: era el flujo de compra nuevo + websocket lento.
- FIXES aplicados (solo VELAS-DOJIS): 1) timeout de compra 20s -> 5s por intento (2 principal + 2 fallback: el respaldo entra en ~13s). 2) Reconexion proactiva antes de comprar si hay zombies recientes (tmu.abandonados() > _ult_zombies_buy). 3) Si la compra falla por 'Sin respuesta del broker', NO se pierde la doji: _dormir_hasta_cierre + reintento al proximo :00 (expiracion recalculada, operativa con 60s completos). 4) seg_envio se calcula DESPUES de comprar (log y Telegram muestran el segundo REAL, antes era enganoso). 5) config.json: se eliminan USDJPY-OTC, GBPNZD-OTC, GBPJPY-OTC -> 17 activos (menos carga del websocket).
- Verificado: 14 modulos compilan, tests persistencia OK, import OK. Push b4dc5d2, Railway redesplegado (22:33 UTC, 17 activos, PRACTICE).
- PENDIENTE: Dojis Family NO recibio estos cambios (timeout 5s, reconexion proactiva, reintento al :00) - solo Velas Dojis. Si el jefe quiere, replicar en local.

## 26/08/2026 - RECORTE DE LLAMADAS AL WEBSOCKET (VELAS-DOJIS, commit 398ba63 PUSHEADO)
- Objetivo del jefe: reducir las llamadas al websocket y priorizar SIEMPRE el stream de velas (deteccion de doji y entradas intactas).
- De ~58 a ~23 llamadas/min (17 son los streams de velas, esenciales e intactos):
  1) Reporte: hora del broker UNA vez por minuto (hora_b_ref) reutilizada para los 17 activos (antes 2 timeSync por activo = 34/min).
  2) _resincronizar_escaneo: lee del stream local (get_velas_stream), red solo como respaldo (antes 17 llamadas de red por evento).
  3) Arranque: hilos leen _leer_desfase_global() (el hilo medidor mide 1 vez); medicion propia solo como respaldo (antes 17 timeSync en rafaga).
  4) _conexion_ok: cache subido de 30s a 60s.
  5) _hilo_medir_desfase: intervalo de 60s a 90s.
- NO se toco: stream de velas, estrategia_dojis.py (deteccion de doji y mecha), poll del cierre al :00, recalibracion del desfase con la vela cerrada (desfase_candela), compra blindada (timeout 5s + reconexion proactiva + reintento al :00).
- Verificado: 14 modulos compilan, tests persistencia OK, import OK. Push 398ba63, Railway redesplegado (22:47 UTC, 17 activos, buscando doji normal, sin errores).

## 26/08/2026 - FIX EXPIRACION CON DESFASE RECALIBRADO (VELAS-DOJIS, commit f1f1a64 PUSHEADO)
- Caso CADJPY 22:54 UTC: el bot rechazo 'sin tiempo de expiracion disponible' con el activo disponible. Log: senal 22:53:59, buy devolvio (False, 'ventana de expiracion cerrandose') a las 22:54:00.
- CAUSA: inconsistencia de relojes. El DISPARO de entrada usa el desfase recalibrado (local + desfase, derivado del 'from' exacto de la vela cerrada, preciso); pero _expiry_valido (operativa.py) usaba el timeSync DIRECTO del websocket como fuente principal, que llega con latencia (hasta 400ms) y puede estar ATRASADO: decia segundo 59 cuando ya era el :00 real -> la expiracion calculada caia en la ventana cerrada (<10s) -> falso rechazo. El fix 0841381 (esperar al :00) esperaba con el desfase pero luego _expiry_valido volvia a usar el timeSync atrasado y fallaba.
- FIX: _expiry_valido ahora usa hora_broker(desfase) (desfase recalibrado) como fuente PRINCIPAL; el timeSync directo queda como respaldo solo si el desfase no da expiracion valida. Consistente con el disparo.
- Verificado: simulacion del caso con mock (timeSync atrasado en segundo 59.5): compra ejecutada con expiracion valida a 44.8s de la hora real. 14 modulos compilan, tests OK. Push f1f1a64, Railway redesplegado (22:56 UTC, 17 activos, normal).

## 26/08/2026 - FILTROS DE VELAS CON HORA DEL BROKER (VELAS-DOJIS, commit 8e2ada2 PUSHEADO)
- Auditoria de integridad completa (14 modulos, sintaxis OK): se encontro la ULTIMA inconsistencia de desfase. velas.py (get_velas_stream, get_velas, get_vela_viva) comparaba el 'from' de la vela (timestamp del BROKER) contra el RELOJ LOCAL (time.time()) sin desfase. Con desfase de cientos de ms (logs: -121 a -880ms): con desfase negativo el bot podia tratar una vela EN FORMACION como cerrada (datos no finales); con desfase positivo no veia la recien cerrada. bot.py compensaba en el loop principal (filtro from >= cierre_objetivo) pero NO en _confirmar_contraria ni _vigilar_entrada.
- FIX: velas.py ahora tiene `_desfase` global + `set_desfase()`; los filtros usan time.time() + desfase = HORA DEL BROKER. bot.py inyecta el desfase en 3 puntos: hilo medidor unico (cada 90s), recalibracion con la vela cerrada (desfase_candela) y arranque de cada hilo.
- Verificado: simulacion del caso borde del :00 (vela que el broker aun no cerro NO se incluye; desfase positivo incluye la cerrada), test CADJPY OK, persistencia OK, 14 modulos compilan. Push 8e2ada2, Railway redesplegado (23:01 UTC, 17 activos, normal).
- LECCION GENERAL: NUNCA mezclar reloj local con timestamps del broker: todo calculo de tiempo de velas/expiracion usa hora_broker(desfase) o time.time()+desfase. El timeSync directo solo para visual (reporte, mensajes) o respaldo.

## 28/08/2026 - BOT SATURACION: estrategia de saturacion con plantilla IQ
- Proyecto nuevo en C:\Users\wasc4\Desktop\BOT-SATURACION (copia de PLANTILLA-IQ-OPTION del 24/08). Estrategia pedido del jefe: saturacion por conteo de velas.
- Reglas: inicia con 2 velas iguales (verde o rojo) define color de saturacion. Se cuentan todas las del color saturado. Entre bloques se permite 1 sola vela contraria aislada. Invalida si: 2 contrarias seguidas o bloque del color sat con <2 velas entre contrarias. Hasta X velas (velas_saturacion, default 10) y opera EN CONTRA (verde->PUT, rojo->CALL) a 1 min. Doji reinicia.
- Implementado: estrategia_saturacion.py (clase EstrategiaSaturacionActivo, CONFIG velas_saturacion 3..50 paso 1, estados buscando/activo/listo, alimentar incremental con racha_sat/racha_contra, reconstruir por replay, telegram reporte lineas con contador y direccion, indicadores fuego/rayo, prioridad por total).
- Integracion plantilla: config.json estrategia=saturacion params velas_saturacion=10, bot.py log y mensaje inicio adaptados (bot_iniciado_saturacion), telegram_reporte.py funcion nueva bot_iniciado_saturacion. Verificado: py_compile OK (3 modulos), test_saturacion.py 8 casos (valido 10 verdes PUT, invalido 2 rojas, invalido bloque 1, saturacion roja CALL, doji, X=4 early, reconstruir, observar).
- Uso: python bot.py en BOT-SATURACION, Telegram boton Velas Saturacion (3..50) editable tambien escribiendo numero. Martingala global (riesgo.py), una operativa a la vez.
- Pendiente: backtest historico y prueba en demo.

## 28/08/2026 - BOT SATURACION v2: martingala VELA A VELA
- Pedido del jefe: martingala vela a vela (al perder, siguiente vela inmediata misma direccion, sin esperar nuevo patron) y ciclo ATADO al activo.
- Actualizado estrategia_saturacion.py: agregados _ciclo_vela, _direccion_ciclo, desfase, _seg_broker, reintento_inmediato()=True y ciclo_enfocado()=True cuando hay ciclo, alimentar con rama prioritaria de recuperacion vela a vela (nuevo_cierre + ventana 50s), registrar_resultado activa ciclo en perdida con sigue=True y lo cierra en ganada/perdida definitiva, indicadores/prioridad/descripcion para recuperacion, reconstruir conserva ciclo.
- Verificado: test vela a vela 3/3 (saturacion 4 PUT, perdida-> MG1 inmediato PUT, 2da perdida-> MG2 inmediato, ganada cierra ciclo y vuelve a patron; doji en ciclo no mata). py_compile OK.

## 28/08/2026 - BOT SATURACION v3: FIX DELAY CONTADOR
- Reporte del jefe: contador 8/10 retrasado, no contaba todas las velas desde el inicio.
- Causa: alimentar() solo procesaba velas[-1], si el hilo despertaba un segundo antes del cierre o se colgaba un minuto se perdia una vela y el total quedaba atrasado.
- Fix: alimentar() ahora detecta todas las velas nuevas desde ultimo_ts y las procesa en orden con _alimentar_una(), sin perdidas. Tambien se agrego en lineas_reporte la secuencia real (ultimas 12) para verificar visualmente que el conteo coincide con el grafico.
- Reiniciado en visible (09:01) con credenciales WASCAR2416/ElPunto3Bot, vela a vela ya activo.

## 28/08/2026 - Tarea de operadores logicos (JavaScript)
- El jefe pidio convertir las respuestas de la practica de operadores logicos (PDFs en Descargas) en un documento Word editable.
- Generado: C:\Users\wasc4\Downloads\Practica_Operadores_Logicos_Respuestas.docx (20 ejercicios, con enunciado + codigo + comentario de resultado).
- Script reutilizable: C:\Users\wasc4\AppData\Local\Temp\opencode\generar_tarea_word.py (python-docx).
- Aprendizaje: el modelo no lee PDFs; extraer texto con pypdf a un .txt UTF-8 y leerlo con Read.

## 29/08/2026 - BOT SATURACIONES V2: refactor desde cero (conteo nuevo, entrada VACIA)
- Proyecto nuevo: C:\Users\wasc4\Desktop\BOT-SATURACIONES-V2 (copia de BOT-SATURACION pelada a plantilla). Pedido del jefe: refactorizar desde cero, NO copiar la obtencion de velas ni el conteo viejos; el sistema de ENTRADA queda VACIO (el bot NO opera, solo cuenta para validar).
- ELIMINADO: estrategia_saturacion.py (conteo viejo), estrategia_picos.py, chequear_cierre_velas.py, deteccion de patrones de velas.py (detectar_alternancia, alinear_nivel, fuerza_alternancia, etc.), opciones de estrategia (estrategia_params vacio, CONFIG=[]).
- OBTENCION NUEVA: velas.get_velas_ventana() - descarga periodica directa con get_candles bajo timeout real (timeout_utils), filtro de cerradas por hora del broker (from+tf <= hora_broker+1s), sin streams. LECCION: get_candles devuelve 'min'/'max' (NO high/low); validar_vela y el mapeo aceptan ambos formatos (fix que destrabo el conteo: devolvia 0 velas).
- CONTEO NUEVO (estrategia_saturacion_v2.py, regla del jefe): detonante = 2+ velas consecutivas del mismo color (dominante); suma cada vela del color; UNA contraria aislada se tolera (conteo espera); invalida SOLO con contrarias cerca: 2 seguidas o contraria + 1 sola a favor + contraria; doji = contraria. Recalculo DESDE CERO por ventana cada minuto (sin maquina incremental). alimentar() devuelve SIEMPRE None (nunca opera), estado nunca 'listo'.
- bot.py: hilo_activo simplificado a conteo puro (dormir hasta cierre + get_velas_ventana + alimentar + reportar), sin motor de entrada (las funciones viejas quedan inertes, no se tocan). hilo_reporte toma precio de est.ultimo_precio (sin streams). _toggle_activo sin suscribir/desuscribir streams.
- VERIFICADO: test_conteo.py 16/16 casos (detonante, tolerancia, invalidaciones, doji, simetria, idempotencia) + simulacion ventana deslizante; py_compile OK; prueba real 2 ciclos: 10 activos contando (ej. CHFJPY 7->8 verde, AUDUSD 6->7 verde, EURCHF 4 verde invalidado correctamente), reportes Telegram OK, WS 12-26 llamadas/min.
- Uso: lanzar_bot_visible.bat o python bot.py. Cuenta WASCAR2416 PRACTICE, 10 activos OTC iguales al bot viejo.
- PENDIENTE: el jefe definira la logica de ENTRADA nueva (cuando operar) en un proximo mensaje; el bot ya esta listo para integrarla.

## 29/08/2026 - BOT SATURACIONES V2: DETONANTE NUEVO (2A + 2B) + reporte sincronizado
- Cambio de planes del jefe: el detonante del conteo ya NO es "2+ del mismo color" simple. Ahora es: racha A de 2+ velas del mismo color (ej. 2 rojas) y DESPUES racha B de 2+ velas del color OPUESTO (ej. 2 verdes); a partir de ahi EMPIEZA el conteo contando las B. Si la racha B no llega a 2 (vuelve el color A), el detonante falla y se reinicia. La racha A puede extenderse (3+ rojas siguen siendo A).
- Configurable: CONFIG de la estrategia con detonante_racha_a y detonante_racha_b (default 2, editables por Telegram, en config.json estrategia_params). El jefe pidio "abrir un segundo detonante" que definira en el proximo mensaje: el codigo de _recalcular() esta organizado para agregarlo sin tocar el resto.
- Reporte sincronizado al 100% con el conteo: lineas_reporte() SIEMPRE devuelve lineas (nunca None): precio actual (formato segun magnitud), conteo + color, contrarias toleradas, estado de la racha (viva/esperando) o "buscando detonante". El precio se toma de est.ultimo_precio (sin streams). La puerta de frescura del reporte espera a que los 10 hilos procesen el cierre antes de enviar.
- Verificado: test_conteo.py 14/14 casos (detonante 2A+2B, racha A extendida, simetria, tolerancia, invalidaciones, doji, idempotencia) + simulacion ventana deslizante. Bot reiniciado en ventana visible (proceso nuevo), primer ciclo real: AUDUSD 3 verde, CHFJPY 2 verde, EURCAD 5 rojo, AUDNZD 3 verde, resto buscando (el detonante 2A+2B es mas estricto, correcto). Reporte Telegram OK.
- PENDIENTE: DETONANTE 2 (el jefe lo definira); sistema de ENTRADA sigue VACIO.

## 29/08/2026 - BOT SATURACIONES V2: DETONANTE 2 implementado + su ESPEJO
- Detonante 2 (regla del jefe): patron de 5 velas A B A B B. Alcista: roja, verde, roja, verde, verde -> conteo de verdes desde las 2 finales. Bajista (ESPEJO, pedido del jefe): verde, roja, verde, roja, roja -> conteo de rojas. El espejo se implemento SIMETRICO desde el inicio (a2 != b2, cola[0]==cola[2]==A, cola[1]==cola[3]==cola[4]==B), asi que ya estaba activo; se agrego la verificacion con 6 casos de prueba del espejo.
- Ambos detonantes (D1: racha A 2+ + racha B 2+; D2: patron A B A B B) estan ACTIVOS a la vez: el conteo se dispara con el primero que se cumpla. El doji rompe ambos patrones. La logica de saturacion (contraria aislada tolerada, invalidacion con contrarias cerca) es identica para los dos.
- Verificado: test_conteo.py 31/31 casos (14 D1 + 10 D2 + 6 D2 espejo + idempotencia). Bot corriendo en ventana visible (proceso 15516) con ambos detonantes; primer ciclo real: CADJPY 2 verde, AUDCAD 2 rojo, EURGBP 6 verde.
- PENDIENTE: sistema de ENTRADA sigue VACIO (el jefe definira cuando operar).

## 29/08/2026 - BOT SATURACIONES V2: formato del bot 1 + activo USDPHP
- Regla del jefe: copiar el formato del log minuto a minuto del Bot de Saturaciones 1. Cambios en estrategia_saturacion_v2.py:
  * ELIMINADA la linea de Precio del reporte (lineas_reporte ya no la muestra; _fmt_precio eliminado).
  * lineas_reporte() copia el formato del bot 1: 'SATURACION VERDE 🟢:' / 'SATURACION ROJA 🔴:', 'N / 10 velas', 'Interr: N', 'Racha: N color (min 2)' o 'Racha: 1 contraria (min 2)', 'Faltan N | dir: PUT ⬇/CALL ⬆'. None cuando buscando (muestra 'Sin nivel').
  * descripcion() copia el formato del bot 1: 'saturando verde 3/10 (1 contraria) interr 1' o 'buscando saturacion'.
  * Motivo de invalidacion con formato del bot 1: '2 contrarias seguidas' o 'contraria + 1 a favor + contraria'.
  * Nuevo parametro velas_saturacion (default 10, CONFIG 3..50, editable por Telegram): el conteo objetivo N/10. La logica de OPERAR al completar 10 se implementara cuando se pongan los puntos de entrada (pendiente).
- config.json: velas_saturacion=10 en estrategia_params; CADJPY-OTC REEMPLAZADO por USDPHP-OTC (activos y activos_activos).
- LECCION: al editar config.json con PowerShell Set-Content -Encoding UTF8 se agrega BOM y json.load falla ('Unexpected UTF-8 BOM'); reescribir con Python (encoding='utf-8' sin BOM) o utf-8-sig al leer.
- Verificado: test_conteo.py 31/31 OK, formato de reporte identico al bot 1 (prueba manual), bot reiniciado en ventana visible (proceso 10292): log real 'saturando rojo 8/10 (1 contraria) interr 3', 'saturando verde 4/10', USDPHP-OTC contando 'saturando verde 2/10'. Reporte Telegram OK.

## 29/08/2026 - BOT SATURACIONES V2: FIX DOJI (caso AUDUSD 22:45)
- El jefe reporto que AUDUSD llevaba 11/10 y el conteo desaparecio sin razon aparente. Investigacion con velas REALES descargadas del broker (script verificar_velas_audusd.py en Temp):
  * 22:43 roja (vela 11, conteo 11/10), 22:44 VERDE (vela 12, interrupcion, tolerada: log '11/10 (1 contraria) interr 5'), 22:45 DOJI EXACTO (open == close, 0.71830), 22:46 roja.
  * El bug: el DOJI se trataba como CONTRARIA (regla copiada del bot 1). El doji de 22:45 llego con desde_contraria=0 (tras la interrupcion verde) -> '2 contrarias seguidas' FALSAS -> invalidacion. La vela 12 SI se tolero bien; el problema fue la vela 13 (doji).
- FIX (regla del jefe): el DOJI se IGNORA por completo en _recalcular: no suma, no invalida, no interrumpe y no rompe el detonante (continue al inicio del loop). Con el fix, el caso AUDUSD habria seguido contando (el doji no afecta).
- INFORME DE INVALIDACION (unica forma, verificada en codigo lineas 210-234): (a) DOS contrarias consecutivas (la 2a llega con 0 velas a favor desde la anterior contraria); (b) una contraria + UNA sola a favor + otra contraria (la 2a llega con 1 a favor). Una contraria aislada (despues de 2+ a favor) se tolera y el conteo espera. Nada mas invalida.
- Verificado: test_conteo.py 33/33 (5 casos de doji: se ignora en detonante, en conteo, tras interrupcion NO invalida, en patron D2). Bot reiniciado (proceso 2292).

## 29/08/2026 - BOT SATURACIONES V2: FIX DOJI REAL (regla del jefe, caso AUDUSD 22:45)
- El jefe aclaro: la vela 22:45 de AUDUSD NO fue doji, fue una vela ROJA por exactamente 1 tick. Verificado con precision: open=0.71830500 close=0.71829500 (diff=-0.00001). Mi primera verificacion con %.5f me engano (redondeaba ambos a 0.71830).
- CAUSA RAIZ: es_doji usaba umbral de 1 tick (|close-open| <= tick) y una vela roja por 1 tick se marcaba doji -> el bot la trataba como contraria -> invalidacion falsa '2 contrarias seguidas' (verde 22:44 + 'doji' 22:45).
- REGLA DEL JEFE (definitiva): doji SOLO si la APERTURA es EXACTAMENTE el mismo precio que el CIERRE (cuerpo de 0 ticks). Si el cuerpo es de 1 tick o mas (aunque sea minimo), la vela es de SU COLOR (roja/verde) segun su direccion.
- FIX 1: velas.es_doji ahora devuelve c == o (comparacion exacta). color_vela ya evaluaba es_roja/es_verde primero, asi que la vela de 1 tick roja sale 'rojo' y SUMA al conteo.
- FIX 2: bot._dormir_hasta_cierre despierta a las :00+3s (antes :00+1s): el retraso garantiza que get_candles devuelva el CLOSE FINALIZADO (el broker ajusta el close en los primeros segundos; a las :01 una vela roja por 1 tick podia leerse con close==open provisional).
- Verificado: test_conteo.py 33/33 + 3 casos de la regla del doji (roja 1 tick -> rojo, verde 1 tick -> verde, open==close -> doji). Bot reiniciado (proceso 5084), hilos procesando a las :03.

## 29/08/2026 - BOT SATURACIONES V2: ENTRADAS + MARTINGALA VELA A VELA (regla del jefe)
- El jefe activo el sistema de TOMAS DE OPERATIVAS: cuando el conteo llega a velas_saturacion (10), el bot opera EN EL SEGUNDO :00 o lo mas cerca posible, SIEMPRE sobre velas YA CERRADAS, EN CONTRA del color dominante (verde->PUT, rojo->CALL). Martingala VELA A VELA como el bot 1: al perder, la siguiente vela se opera de inmediato en la misma direccion hasta ganar o agotar niveles; ciclo ATADO al activo (ciclo_atado_siempre=True).
- Estrategia v2 (estrategia_saturacion_v2.py reescrita): estados buscando/activo/listo; alimentar() devuelve ('operar', dir) cuando conteo >= velas_saturacion; dedupe por vela (_ultimo_ts) para no re-disparar la misma ventana; registrar_resultado activa/cierra el ciclo vela a vela; reintento_inmediato() y ciclo_enfocado() True en ciclo; descripcion 'recuperando vela a vela put/call' y 'listo para venta/compra (N/10)'.
- bot.py: hilo_activo con MOTOR AL :00 (sinc.dormir_hasta_cero 450ms antes + poll fino 20ms, procesa en el :00 exacto, lectura de la vela cerrada en <1s); _ejecutar_operativa_v2 (turno unico, confirmacion pre-buy con la ventana descargada _confirmar_cierre_v2, buy_seguro, esperar_resultado, ganada/empate/perdida con reportes Telegram, ciclo atado); _dormir_hasta_cierre REVERTIDO a :00+1s (el jefe rechazo el retraso de 3s: lectura profesional en <1s).
- Reporte Telegram (regla del jefe): ELIMINADA la linea de Racha; solo queda 'Interr: N' (se va contando). Sin Precio. Formato: SATURACION VERDE/ROJA + emoji, N/10 velas, Interr, Faltan/dir o LISTO PARA ENTRADA.
- Verificado: test_conteo.py 33/33 + 7 casos de entradas/martingala (10 verdes->put, 10 rojas->call, dedupe, perdida activa ciclo, vela nueva opera, ganada cierra, perdida definitiva resetea). Bot reiniciado (proceso 8616), hilos procesando en el :00 (log 23:14:00), reporte OK.

## 29/08/2026 - BOT SATURACIONES V2: FIX SALTO DE CONTEO (EURCHF 7->9)
- El jefe reporto que EURCHF salto de 7/10 a 9/10 sin pasar por 8. CAUSA RAIZ encontrada en el motor al :00: sinc.dormir_hasta_cero despierta 450ms ANTES del cierre (seg broker = 59.55), y el poll fino solo esperaba al :00 si seg < 0.5 -> con seg = 59.55 se saltaba la espera y procesaba la vela AUN VIVA con su close PROVISIONAL. El recálculo por ventana luego 'saltaba' cuando el close se finalizaba (7 -> 9 de golpe).
- FIX: el poll fino ahora espera SIEMPRE al :00 (hora_broker % 60 < 0.01, limite 3s), sin condicion de seg. El bot lee la vela YA CERRADA (close final) en el :00, como pide el jefe (lectura profesional en <1s), y el conteo avanza vela a vela sin saltos.
- Verificado: py_compile OK, bot reiniciado (proceso 12068), hilos procesando en el :00 (log 23:24:00-01).

## 29/08/2026 - BOT SATURACIONES V2: reporte sin abreviar + RESPALDO
- Regla del jefe: 'Interr' deja de estar abreviado en el reporte de Telegram -> 'Interrupcion: 1' (singular) / 'Interrupciones: N' (plural). Y la linea de listo: se elimino el rayo ⚡, queda '❗ LISTO PARA ENTRADA' (mayusculas, emoji de exclamacion).
- RESPALDO creado: C:\Users\wasc4\Desktop\BOT-SATURACIONES-V2-RESPALDO (copia completa: 144 archivos, iqoptionapi 126, sin bot.log/__pycache__). Verificado: import bot OK.
- LECCION: Copy-Item -Recurse de una carpeta a un destino inexistente copia el CONTENIDO en la raiz (estructura rota); crear el destino primero y copiar cada elemento con Join-Path.
- Bot reiniciado (proceso 9416) con el reporte nuevo.

## 29/08/2026 - BOT SATURACIONES V2: ENTRADA CERCA DEL :00 + DORMIR HILOS (regla del jefe)
- El jefe pidio: operativas lo mas cerca del :00, SIEMPRE despues de verificar la ultima vela YA CERRADA (nunca vela viva ni close provisional). Mejoras aplicadas SOLO a BOT-SATURACIONES-V2 (NO al respaldo):
  * hilo_activo: la ventana de velas se descarga ANTES del :00 (escalonada por indice); en el :00 solo se descarga la ULTIMA vela (get_ultima_vela, count=2, timeout 5s, la llamada mas rapida). En el :00 los hilos con conteo mas alto descargan primero (stagger por conteo: los mas cerca de operar ejecutan lo mas pegado al :00). Recalibracion del desfase por candela (from de la vela recien cerrada + tf = :00 exacto del broker).
  * FIX FILTRO (critico): el filtro por tolerancia (hora_broker + 0.01s) fallaba si el desfase tenia error (excluia la vela recien cerrada y congelaba el conteo); con tolerancia 1.0s incluia la vela VIVA. Ahora se filtra por FROM ESPERADO: la recien cerrada tiene from = inicio del minuto anterior al :00 del broker; la vela viva se descarta SIEMPRE (robusto a cualquier desfase).
  * FIX count=1: get_candles con count=1 devuelve la vela VIVA (la mas reciente) y el filtro la excluye -> nunca llegaba la cerrada; con count=2 llegan ambas y el filtro selecciona la cerrada.
  * DORMIR HILOS AJENOS (como el bot 1, respuesta a la pregunta del jefe): cuando un activo entra en ciclo de martingala (_ciclo_martingala_activo), los hilos de los demas activos se duermen (time.sleep(1), no descargan, no cuentan) hasta que el ciclo gana o se cierra (perdida definitiva). El hilo del activo en ciclo sigue procesando la recuperacion vela a vela.
- PRIMERA OPERATIVA REAL del bot v2: AUDNZD CALL .18 (entrada :068 = 68ms del :00) y AUDUSD CALL .18 (entrada :650) -> GANADA +.00 (neto dia +.00). Flujo completo verificado: conteo -> listo -> confirmacion -> buy -> resultado -> plan -> reporte Telegram.
- Verificado: py_compile OK, test 33/33, bot reiniciado (proceso 8812).

## 29/08/2026 - BOT SATURACIONES V2: MODO CRITICO (regla del jefe)
- REGLA DEL JEFE: cuando un activo queda a UNA vela de completar la saturacion (candidato), el bot se concentra en el: se desuscriben los streams de los demas activos (como en la martingala) y solo el candidato espera la vela final al :00. Si la vela sale del color necesario, COMPRA INMEDIATO al :00 (el hilo de compra va PRIMERO sin interrupciones; reportes y logs de estado van DESPUES). Asi se reduce el estres del sistema (menos llamadas al websocket, una sola entrada limpia al :00) y la entrada queda lo mas pegada posible al segundo cero.
- REGLAS DEL JEFE (aclaradas): (1) el candidato con contraria tolerada SIGUE siendo candidato hasta ganar o perder completo; (2) prioridad por ORDEN DE LLEGADA (todos los candidatos llegan con el mismo conteo N-1, no hay "mayor conteo"); (3) tras ganar, se rearma todo (minuto ciego) y el mismo activo puede volver a ser candidato si su racha sigue viva.
- IMPLEMENTADO (SOLO en BOT-SATURACIONES-V2, NO en el respaldo):
  * estrategia_saturacion_v2.py: es_candidato() (conteo == velas_saturacion - 1, con o sin contraria tolerada; False en ciclo vela a vela) + validar_vela_critica(vela) -> ('operar',dir) si la vela es del color dominante, ('esperar','doji') si doji, ('esperar','contraria') si contraria aislada (tolera y sigue), ('invalidar',motivo) si 2 contrarias seguidas, ('esperar','repetida') si dedupe. SIN recalcular la ventana de 30: usa el estado ya conocido (decision FINA e INMEDIATA). Reporte: bloque 'MODO CRITICO 🎯' + prioridad -1500.
  * bot.py: coordinador _declarar_candidato/_liberar_modo_critico (orden de llegada con _modo_critico_lock; apaga streams ajenos con _pausar_streams_ajenos; rearma con _reanudar_streams_ajenos). hilo_activo: hilos ajenos se apagan (sleep 2 + marcar procesado); el candidato en el :00 lee SOLO la ultima vela (1 llamada local, sin ventana de 30) y la valida; si opera: _ejecutar_operativa_v2(critico=True) -> OMITE la confirmacion pre-buy (la vela ya se valido con su color exacto + sello oficial) -> COMPRA INMEDIATA, reporte despues. Minuto ciego respetado. config.json: "modo_critico": true.
  * _ejecutar_operativa_v2: nuevo parametro critico=False (True = sin confirmacion pre-buy, compra al instante).
- FLUJO COMPLETO: conteo 9/10 -> candidato -> streams ajenos apagados -> al :00 se lee 1 vela -> color necesario -> COMPRA INMEDIATA -> resultado -> ganada: minuto ciego + rearmar todo; perdida con niveles: martingala vela a vela sigue concentrada; perdida definitiva/invalidacion: rearmar y siguiente candidato por orden de llegada.
- Verificado: py_compile OK, test_conteo.py 33/33 + 8 casos nuevos del modo critico (candidato, vela final verde->operar, doji espera, contraria tolera y sigue candidato, a favor tras tolerada completa, 2 contrarias invalidan, dedupe, ciclo vela a vela no es candidato). PENDIENTE DE REINICIO: el bot debe reiniciarse para aplicar el modo critico (preguntar al jefe cuando reiniciar).

## 29/08/2026 - B3-SATURACIONES: transplante de logica V2 al BOT MULTI-SECUENCIAS (regla del jefe)
- REGLA DEL JEFE: crear una copia del Bot Multisecuencias (la version mas actualizada = Documents\python projects\BOT-SECUENCIAS) llamada B3-SATURACIONES en el Desktop, y trasplantarle UNICAMENTE la logica del Bot de Saturaciones V2 (estrategia_saturacion_v2.py del 29/08). Todo lo demas queda identico: deteccion de velas, conteo del stream, punto de entrada al :00, UI, Telegram, panel de secuencias, operativa, riesgos. Autorizado quitar la regla del doji del motor.
- UBICACION: C:\Users\wasc4\Desktop\B3-SATURACIONES (copia limpia sin __pycache__ ni logs).
- CAMBIOS REALIZADOS (solo 3):
  1. estrategia_saturacion_v2.py copiado VERBATIM del V2 + atributo de clase tipo_martingala = 'vela' (el motor del multisecuencias activa el ciclo vela a vela enfocado con esa marca; sin ella no pausaria los hilos ajenos durante la recuperacion).
  2. config.json: "estrategia": "saturacion_v2" con estrategia_params {velas_saturacion: 10, detonante_racha_a: 2, detonante_racha_b: 2, margen_compra_seg: 30.0} (se quito espera_velas de secuencias).
  3. bot.py: ELIMINADA la REGLA DEL DOJI del motor (reconstruia/reseteaba la maquina con cada doji; la logica V2 ignora el doji por completo). Es el UNICO toque al motor; el resto del flujo (dormir_hasta_cero, poll fino, confirmacion pre-buy, buy_seguro, martingala, reportes) intacto.
- LOGICA TRANSPLANTADA (verificada con prueba funcional, TODO OK): detonante 1 (racha A 2+ del mismo color + racha B 2+ del opuesto -> conteo de las B), detonante 2 (patron A B A B B -> conteo de las 2 B finales), AMBOS con espejo incluido (logica simetrica, sin hardcode de color), se dispara con el primero que se cumpla; conteo suma cada vela del dominante; contraria aislada se tolera (espera); invalida solo con contrarias cerca (2 seguidas o contraria + 1 a favor + contraria); doji ignorado (no suma, no invalida, no rompe); entrada al llegar a 10 velas (configurable) EN CONTRA del dominante (verde -> PUT, rojo -> CALL) al :00 sobre vela cerrada; martingala vela a vela (perdida -> siguiente vela inmediata misma direccion, ciclo atado al activo).
- NOTA: el sistema de secuencias (panel, botones, secuencias.json, ui_secuencias) queda INTACTO por orden del jefe; el reporte minuto solo se envia si secuencias.operativas_activas() es True (secuencias.json viene con operativas: true). La estrategia V2 no depende de secuencias para operar.
- Verificado: py_compile OK (bot.py, estrategias, operativa, velas, etc.), JSON valido, prueba funcional 10/10 (D1, D2, espejos, doji, tolerancia, invalidaciones, martingala, ganada). PENDIENTE: el jefe debe lanzar el bot para probarlo en vivo.

## 29/08/2026 - B3-SATURACIONES: reporte minuto a minuto del V2 (regla del jefe)
- REGLA DEL JEFE: el B3 debe tener tambien los logs de minuto a minuto del Bot de Saturaciones V2 (el fix del Doctor del 29/08: bloque de OPERACION EN EL MINUTO en el reporte). El B3 ya tenia el log local MINUTO (activos/listos/MG), el REPORTE enviado y el contador WS; faltaba el bloque de operacion.
- IMPLEMENTADO en C:\Users\wasc4\Desktop\B3-SATURACIONES\bot.py:
  * Variables globales _ultima_operacion_ts y _ultima_operacion_info (junto a _pausa_post_ganada_hasta).
  * Funcion _bloque_operacion_minuto() (formato compacto IQ-ULTIMATE: activo, direccion, monto, MG, resultado ejecutada/ganada/perdida/empate).
  * _ejecutar_operativa: marca el minuto al EJECUTAR (despues del buy OK) y al RESULTADO (ganada con ganancia, perdida con perdida, empate). Global _ultima_operacion_ts anadido.
  * hilo_reporte: el reporte SIEMPRE se envia; si hubo operacion en los ultimos 60s se ANEXA el bloque de operacion del minuto + log 'REPORTE con operacion del minuto incluida'.
- lanzar_bot.bat actualizado con identidad B3-SATURACIONES.
- Verificado: py_compile OK, import bot OK, prueba del bloque (ejecutada/ganada/perdida/sin operacion) TODO OK. LANZADO en CMD visible (Start-Process cmd /k lanzar_bot.bat).

## 29/08/2026 - B3-SATURACIONES ELIMINADO (regla del jefe)
- REGLA DEL JEFE: eliminar el B3-SATURACIONES (la copia multisecuencias con logica V2 creada hoy). El jefe se queda SOLO con dos versiones de saturaciones: la V1 original (Desktop\BOT-SATURACION, con estrategia_saturacion.py) y la V2 (Desktop\BOT-SATURACIONES-V2). El respaldo BOT-SATURACIONES-V2-RESPALDO sigue existiendo.
- HECHO: procesos del B3 detenidos (taskkill /T /F sobre el cmd lanzador), carpeta C:\Users\wasc4\Desktop\B3-SATURACIONES eliminada con Remove-Item -Recurse -Force.
- LANZADA la V2 en CMD visible (lanzar_bot_visible.bat): conectada a IQ Option PRACTICE, 10 activos, streams suscritos, aviso de inicio por Telegram. LECCION: el transplante de logica V2 al multisecuencias quedo descartado por el jefe; si vuelve a pedirlo, la logica donante es estrategia_saturacion_v2.py del V2 y el receptor era Documents\python projects\BOT-SECUENCIAS.

## 29/08/2026 - AGENTE TRADING creado (regla del jefe)
- REGLA DEL JEFE: crear un agente de opencode llamado Trading, maestro exclusivo de bots de trading: crea, clona, modifica y repara bots en base a la estructura existente, conoce la libreria iqoptionapi a fondo y ordena correctamente cada estilo de bot.
- UBICACION: C:\Users\wasc4\.config\opencode\agent\trading.md (mode primary, modelo deepseek-v4-flash, color dorado #f59e0b). Vive junto a doctor.md y plan.md.
- CONTENIDO: (1) taller del jefe (BOT-SATURACION V1, BOT-SATURACIONES-V2 base mas moderna, BOT-SATURACIONES-V2-RESPALDO, BOT-SECUENCIAS, memoria); (2) arquitectura de la plantilla modulo por modulo (bot.py motor, estrategia_<nombre>.py logica, estrategia_base.py contrato, operativa.py, velas.py, riesgo.py, sincronizacion.py, timeout_utils.py, telegram_reporte.py, credenciales, config.json, lanzador); (3) el CONTRATO de estrategia completo (estados, alimentar, CONFIG, dedupe por from, CONFIRMAR_CIERRE, tipo_martingala='vela', ciclo_atado_siempre, es_candidato/validar_vela_critica, reintento_inmediato); (4) los 4 estilos existentes (saturaciones V1, V2 con sus 2 detonantes + espejo + modo critico, secuencias con la regla del doji del motor, picos); (5) comportamiento completo del bot Telegram (arranque, hilo_activo, operativa, martingala IQ-ULTIMATE, hilo_reporte con bloque de operacion del minuto, hilo_telegram, vigilantes, streams); (6) libreria iqoptionapi (instalacion websocket-client==0.56, IQ_Option, connect, change_balance, get_candles ~30s atrasado y se cuelga, streams reales, buy, buy_by_raw_expirations, check_win_v2 inestable, OP_code.ACTIVES, timeSync, peligros conocidos); (7) protocolo de creacion (inventario, plan con opcion sin plan, crear copiando plantilla, verificar py_compile + prueba funcional con velas sinteticas, lanzar en CMD visible, documentar); (8) reglas de oro.
- PENDIENTE: reiniciar opencode para que el agente Trading quede disponible (los agentes se cargan al arrancar).

## 29/08/2026 - BOT SATURACIONES V2: TRANSPLANTE MULTI-SECUENCIAS (entradas al :00 + martingala vela a vela exquisita)
- PEDIDO DEL JEFE: el V2 entraba con 1-2 segundos de retraso (:300-:989, incluso :960/:989) y la martingala vela a vela saltaba velas (USDPHP perdio MG0 13:09 y MG1 se tomo 13:11). El jefe pidio transplantar del BOT MULTI-SECUENCIAS (Documents/python projects/BOT-SECUENCIAS) la forma de tomar operativas (entrada al SEGUNDO CERO) y la martingala vela a vela.
- CAUSAS RAIZ: (1) el motor al :00 del V2 esperaba el sello dual (push de la vela nueva o descarga directa con tope 1s) -> entradas 300-1000ms tarde; el secuencias espera la vela CERRADA del stream local (poll 20ms, cierre <= hora_broker + 0.01) -> entradas 0-20ms. (2) el reintento inmediato del V2 era debil (10 reintentos x 0.3s = 3s, rompia sin velas, sin reparar stream congelado); el secuencias usa 100 reintentos x 0.5s (~50s), respaldo get_velas_seguro, _registrar_avance_local + _reparar_stream_si_muerto(max_seg=10) y solo rompe si seg >= 50.
- CAMBIOS (SOLO BOT-SATURACIONES-V2, bot.py + estrategia_saturacion_v2.py):
  1. hilo_activo: MOTOR AL :00 METODO SECUENCIAS (poll fino 20ms esperando la vela cerrada del stream, recalibracion por candela 1 vez/minuto con abs<0.4, tope anti-giro 1s como respaldo). Eliminado el sello dual (push + descarga paralela) y _descarga_sello. El branch modo critico usa descarga directa como respaldo si el sello no llego.
  2. hilo_activo: REINTENTO INMEDIATO EXQUISITO (100 reintentos, get_velas_seguro de respaldo, sin romper por falta de velas, _registrar_avance_local + _reparar_stream_si_muerto max_seg=10, rompe solo seg>=50, sleep 0.5).
  3. _ejecutar_operativa_v2: CICLO VELA A VELA ATADO DESDE LA EJECUCION con tipo_martingala=='vela' -> _ciclo_vela_activo=True + _ciclo_martingala_activo=activo + _pausar_streams_ajenos en hilo de fondo (websocket limpio).
  4. _ejecutar_operativa_v2: MINUTO CIEGO post-ganada (una vela ciega, _pausa_post_ganada_hasta) + RECUPERACION PRIMERO (_reanudar_streams_ajenos antes de liberar flags) en ganada, perdida definitiva y sin resultado.
  5. _ejecutar_operativa_v2: branch SIN RESULTADO separado (antes el None caia en perdida: plan.pierde() a ciegas); ahora es como el secuencias (registrar_resultado(True), aviso, recuperacion + liberar).
  6. _ejecutar_operativa_v2: PROTOCOLO DE RECHAZO MG1+ completo (arrastre: fuego, est.reconstruir([]), 2 mensajes SE QUEDA reintentando).
  7. bot.py: nueva global _ciclo_vela_activo. estrategia_saturacion_v2.py: atributo de clase tipo_martingala = 'vela' (marca del motor, como el B3).
- NO TOCADO: modo critico (joya del V2, entradas :001-:005), expiracion exacta desde el from (fix Doctor), bloque de operacion del minuto, desfase robusto, empate = reembolso (regla del jefe del V2).
- VERIFICADO: py_compile OK (10 modulos), import bot OK, test_conteo.py 33/33, test_transplante_v2.py 23/23 (ciclo vela a vela, dedupe, sin resultado, modo critico intacto, reintento 100/repara/respaldo, ciclo atado, minuto ciego, arrastre).
- PENDIENTE: probar en vivo (reinicio) y confirmar entradas :000-:020 + martingala sin saltos.

## 29/08/2026 - BOT SATURACIONES V2: FIX DESFASE REAL (entradas 1s tarde) + MG SIN CICLOS LIBRES
- PROBLEMA DEL JEFE: las operativas se seguian tomando 1 segundo despues (el bot interpretaba el :00 como :01) y en la martingala la MG1 esperaba todo un ciclo.
- INVESTIGACION PROFUNDA (medicion en vivo con el script Temp/opencode/medir_desfase.py):
  1) TIMESYNC VICIADO: 12 muestras de get_server_timestamp dieron -238 a -793 ms CRECIENDO ~50ms por muestra (cola de peticiones). El desfase NO es real: es sesgo de RTT/2 + cola (la VPN de la PC). El fix anterior del Doctor usaba el MINIMO = la muestra MAS ENCOLADA (la peor, -793ms) -> hora_broker atrasada ~1s -> el poll del :00 disparaba 1s tarde EN EL BROKER (el bot reportaba :001 engañoso porque su hora_broker estaba atrasada).
  2) RELOJ LOCAL SANO: w32tm muestra sincronizacion NTP OK (offset -165ms). El reloj local es confiable: la hora del broker se puede derivar del FROM de las velas (timestamp exacto del broker, SIN sesgo de red).
- FIX 1 (sincronizacion.py): medir_desfase usa el MAXIMO (la muestra menos encolada) en vez del minimo. ANTICIPO_SEGUNDOS 0.45 -> 1.5 (cubre el sesgo del timeSync hasta ~1.2s).
- FIX 2 (bot.py, MOTOR AL :00 v3): el DISPARADOR ya NO es hora_broker: es el FROM de la vela viva del stream (get_realtime_candles local). Cuando el minuto actual tiene EDAD < 1s (time.time() - from_vela_viva), el :00 del broker acaba de ocurrir -> sello -> entrada al :00 REAL del broker (nunca 1s tarde). Recalibracion del desfase con el from real (desfase = from - now = -latencia push, autocorregido minuto a minuto, 1 vez por minuto). Tope 1s sin sello -> NO dispara a ciegas (espera el flujo normal). El modo critico usa el mismo sello (sin cambios de logica).
- FIX 3 (bot.py, REINTENTO INMEDIATO SIN CICLOS LIBRES): si la vela nueva no llega al stream tras ~2s (4 reintentos), se DESCARGAN las velas del broker (get_velas_seguro, fuente oficial) y se alimenta con ellas: la MG1/MG2 se toma en el MISMO minuto aunque el push se pierda (caso EURAUD 14:09: perdida MG0 -> la vela 14:08 no llego al stream -> la MG1 espero al 14:10; con el fix se toma a las 14:09:03).
- VERIFICADO: py_compile OK, test_sello_edad 6/6 (logica del sello por edad), test_conteo 33/33, test_transplante 23/23. BOT REINICIADO para prueba en vivo: esperado entradas :000-:100 reales del broker + MG en el mismo minuto.

## 29/08/2026 - BOT SATURACIONES V2: FIX DEFINITIVO DEL DESFASE (motor v5) - ENTRADAS AL :00 REAL
- DESPUES de la investigacion del desfase (medicion en vivo + DEBUG del sello), se confirmo con datos:
  1) El FROM de las velas es EXACTO (la vela nueva de las 14:40 llego con from=1788028800=14:40:00.000).
  2) El PUSH del websocket tarda ~1.2-1.27s en esta red (VPN): la vela viva nueva llega al stream con edad 1.27s.
  3) El timeSync mide -238 a -793ms (sesgo RTT/2 + cola de peticiones creciente): el MINIMO (fix del Doctor) tomaba la muestra MAS ENCOLADA.
  4) El RELOJ LOCAL esta sincronizado con NTP (w32tm: offset -165ms, capa 2): el :00 del broker = el :00 local (+/- 200ms).
- MOTOR v5 (bot.py): cruce del :00 por RELOJ LOCAL (time.time() % 60 >= margen_cierre_seg 0.25, configurable) + confirmacion de la vela recien cerrada en el STREAM LOCAL (0 lock, 0 red, sin descargas en el :00 que saturaban el websocket con colas de 3-12s). desfase = 0.0 FIJO (se elimino la medicion periodica del timeSync y la recalibracion circular por candela). El buy_seguro (fix 0841381 del Doctor) espera al :00 si la ventana esta cerrando -> la compra cae en el segundo 0 real.
- RESULTADO EN VIVO: sellos de cierre +20-46ms, entradas :001, :011, :168, :500 (antes :300-:989 reportadas = :01.0 reales en el broker). CADCHF escalera MG0-MG5 con SE.AL INMEDIATA y entradas :484-:500 en el MISMO minuto (martingala vela a vela sin ciclos libres). GANADAS con minuto ciego + re-suscripcion OK. 2 perdidas seguidas de racha (mercado, no bug).
- REINTENTO INMEDIATO: descarga directa (get_velas_seguro) cada 2 reintentos si la vela nueva no llego al stream (push perdido) -> la MG se toma en el mismo minuto (fix de ciclos libres).
- LECCION: el seg_envio del log ahora es REAL (desfase 0): 'entrada :001' = segundo 0.001 del broker. Antes (hora_broker viciada) reportaba :001 cuando el broker la veia a :01.0.
- LECCION BOM: PowerShell Set-Content -Encoding UTF8 anade BOM y rompe json.load (config.json) -> el bot no arranca; reescribir con python encoding='utf-8'.
- VERIFICADO: py_compile OK, test_conteo 33/33, test_transplante 23/23, test_sello_edad 6/6, prueba en vivo completa. BOT CORRIENDO (motor v5, PRACTICE).

## 29/08/2026 - BOT SATURACIONES V2: MG SIN CICLOS LIBRES + ORDEN DE MENSAJES (15:00)
- RESPALDO: C:\Users\wasc4\Desktop\BOT-SATURACIONES-V2-RESPALDO-2026-08-29-15H (estado con motor v5, entradas :001-:179, sellos +20ms). INTACTO.
- PROBLEMA DEL JEFE: el bot dejaba pasar ciclos de martingala: tras una perdida, la MG siguiente a veces esperaba 1 minuto completo. En el ciclo vela a vela debe ejecutar SI O SI (la unica pregunta es gane o perdi).
- CAUSA: DOS caminos ejecutan operativas: flujo normal (con bucle de reintento inmediato) y MODO CRITICO (el mas comun: candidato a 1 vela). El branch critico hacia continue tras la operativa y SE SALTABA el bucle de reintento -> la MG siguiente esperaba al proximo ciclo del hilo (1 minuto = ciclo libre). Confirmado en log: EURCHF perdida MG0 14:42:00 (por critico) -> MG1 recien 14:43:02.
- FIX (bot.py): se extrajo el bucle de reintento inmediato a la funcion compartida _reintento_vela_a_vela() y se llama TANTO en el flujo normal como en el branch del MODO CRITICO (tras _liberar_modo_critico, antes del continue). En el ciclo la estrategia YA dispara con CUALQUIER vela nueva (direccion del ciclo manda, no descarta por color): la confirmacion pre-buy nunca bloquea (obligatoria). El bucle reintenta hasta ~50s, descarga cada 2 reintentos si el push no llega, solo rompe si la ventana cierra (<10s al :00) o el ciclo termino.
- ORDEN DE MENSAJES (telegram_reporte.py): ENVIO_LOCK (RLock global) serializa los envios HTTP: PERDIDA llega SIEMPRE antes que EJECUTADA (antes dos hilos podian invertir el orden).
- VERIFICADO: py_compile OK, test_mg_sin_ciclos 9/9 (bucle ejecuta la MG si o si, direccion del ciclo, critico llama al reintento despues de la operativa, lock de envio). En vivo: AUDCAD :015, CADCHF :179, sellos +20ms, ganadas con minuto ciego OK. BOT CORRIENDO.

## 29/08/2026 - RESPALDO ACTUALIZADO Y CONGELADO (15:3x)
- C:\Users\wasc4\Desktop\BOT-SATURACIONES-V2-RESPALDO-2026-08-29-15H actualizado en ESPEJO (/MIR) con la version actual: motor v5 (entradas al :00 real), MG sin ciclos libres (_reintento_vela_a_vela compartida normal+critico), ENVIO_LOCK (perdida->ejecutada en orden), desfase 0 fijo, ANTICIPO 1.5. Verificado: bot.py con _reintento_vela_a_vela, telegram_reporte con ENVIO_LOCK, sincronizacion con ANTICIPO 1.5.
- REGLA DEL JEFE: NO TOCAR esta copia hasta nuevo aviso. Los proximos cambios van SOLO a C:\Users\wasc4\Desktop\BOT-SATURACIONES-V2 (en vivo).

## 29/08/2026 - BOT SATURACIONES V2: DETONANTE UNICO A B B + DOJI COMO CONTRARIA (17:55)
- DIAGNOSTICO FINAL del 'sin foco': la causa era el DETONANTE ESTRICTO (2+2 y patron 5 velas): las rachas simples y las alternancias no detonaban -> solo 3-4 activos con conteo. El bucle rapido (EURAUD 15:47) se fixeo con el corte ampliado (tramo :58.5-:59.9). La ventana parcial se fixeo con verificacion del maxdict (30 velas) al suscribir + reparador de streams vacios/parciales con cooldown 30s.
- NUEVO DISENO (regla del jefe, se BORRARON el D1 2+2, el D2 con sus 2 formas, las dos pasadas de _recalcular y los parametros detonante_racha_a/b del CONFIG):
  DETONANTE UNICO: patron A B B (UNA vela de un color + DOS velas consecutivas del color opuesto) o su espejo. Ej: V R R -> conteo ROJO 2 (las 2 rojas del patron); R V V -> conteo VERDE 2; D R R (doji como la vela contraria) -> ROJO 2. El patron se busca en TODA la ventana (30 velas): si las ultimas son todas del mismo color, la contraria que las respalda se busca mas atras (1 roja + 10 verdes -> conteo VERDE 10, caso del jefe).
  DOJI COMO CONTRARIA (regla del jefe 29/08): el doji se trata como una vela CONTRARIA en todos los aspectos (NO se ignora): puede iniciar el patron (D R R), se tolera aislado en el conteo (despues de 2+ a favor), y cuenta para la invalidacion (doji + roja = 2 contrarias -> invalida; 2 dojis -> invalida). En el MODO CRITICO: el doji se tolera como contraria (esperar contraria) y con otra pendiente invalida.
  MARTINGALA INTACTA (regla del jefe): la regla del doji aplica SOLO al conteo ANTES de la MG0. Una vez en ciclo vela a vela, el bot opera SI O SI con cualquier vela nueva (doji, contraria o a favor): la unica pregunta es gane o perdi. Verificado con test: doji/contraria/a-favor en ciclo -> todas disparan ('operar').
- VERIFICADO: test_conteo 18/18 + secciones de modo critico y doji; casos reales del diagnostico (AUDCAD VVRVVV RVVR -> verde 5 con el detonante unico); compilacion OK; BOT REINICIADO a las 17:54 con todo el codigo nuevo.

## 29/08/2026 - FIX VELA VIVA/CLOSE INCOMPLETO + DOJI DE 1 TICK (18:05)
- PROBLEMA DEL JEFE: algunos activos no escaneaban bien; sospechaba que se contaba la vela VIVA (1s de vida) o la recien cerrada con datos incompletos.
- VERIFICACION con log temporal (DIAG): la vela viva NO entra al conteo (viva=False en los 10 activos; el filtro de get_velas_stream la excluye). PERO se encontro la causa real: el CLOSE del STREAM de la vela recien cerrada llega con ~1.2s de atraso (el ultimo tick del broker llega despues del :00): a las :00.30 el stream tiene el tick de ~:59.1. Con el DOJI DE 1 TICK, una vela que el broker cierra roja/verde puede verse DOJI en el stream (close casi-final) e invalidar el conteo.
- FIX: SOLO cuando la ultima vela de la ventana es DOJI, se descarga la vela oficial del broker (get_ultima_vela, close FINAL) y se reemplaza: el conteo usa el color definitivo. Descarga solo de los sospechosos (no satura el websocket). Log: 'vela final verificada por descarga: <color>' (visto en vivo 18:04 EURCHF).
- DOJI DE 1 TICK O MENOS (regla del jefe 29/08): es_doji ahora es |close-open| <= 1 tick (tick_precio: forex 1e-5, JPY 1e-3, indices 1e-2, con margen 1e-15 por flotacion). color_vela evalua el DOJI PRIMERO (antes rojo/verde): una vela de 1 tick es gris. Antes era apertura==cierre exacto. El caso AUDUSD 22:45 (1 tick) AHORA es doji (el jefe cambio la regla).
- VERIFICADO: DIAG viva=False en 10/10, 'vela final verificada' en vivo, test_conteo 18/18 + casos doji (1 tick -> doji, 2 ticks -> rojo), compilacion OK. BOT CORRIENDO con el detonante unico A B B: reportes con 4-5 activos con conteo (antes 3-4); conteos vistos: EURGBP rojo 8/10, CHFJPY verde 6/10.

## 29/08/2026 - FIX ESCANEO SECUENCIAL: EL DETONANTE MAS RECIENTE MANDA (18:55)
- QUEJA DEL JEFE: el bot seguia mostrando 6-7/10 activos en 'buscando' con el detonante unico A B B; segun el jefe es IMPOSIBLE con 30 velas (solo la alternancia perfecta deberia dejar buscando).
- CAUSA RAIZ (encontrada en _recalcular de estrategia_saturacion_v2.py): el escaneo era SECUENCIAL y se anclaba al PRIMER patron A B B de la ventana; una vez en conteo activo NUNCA volvia a buscar patrones nuevos. Si la ventana terminaba con un patron mas reciente del color opuesto (ej. el caso del jefe: 1 roja + 10 verdes al FINAL de la ventana), las verdes invalidaban el conteo rojo viejo (2 contrarias seguidas) y el scan quedaba en 'buscando' aunque el detonante R V V estuviera ahi. Los 6-7 en buscando NO eran el mercado: era el escaneo perdiendo los detonantes recientes.
- FIX (re-ancla continua): el patron A B B se detecta en CADA posicion de la ventana (cola deslizante de 3 velas SIEMPRE, no solo al inicio ni tras invalidar). Cuando aparece un A B B del color OPUESTO al conteo activo, el conteo se RE-ANCLA al nuevo patron (el detonante MAS RECIENTE manda). Si el A B B es del MISMO color que el conteo activo, NO se re-ancla (seguir contando: caso 1 roja + 10 verdes -> verde 10 sin reinicios). Resultado: 'buscando' SOLO si no hay NINGUN A B B en la ventana (alternancia perfecta o puras del mismo color), la regla exacta que pidio el jefe.
- CONSECUENCIA en las reglas: las 2 contrarias seguidas ya casi nunca invalidan (forman un A B B con la vela anterior y re-anclan al color nuevo); la invalidacion que sobrevive es 'contraria + 1 sola a favor + contraria' (A B A, alternancia V R V).
- VERIFICADO: test_conteo 21/21 (3 casos nuevos: V R R al inicio + 1 roja + 10 verdes al final -> verde 10; alternancia perfecta -> buscando; patron del mismo color no resetea -> verde 6). BOT REINICIADO 18:49 (PID 5856): primer ciclo real 7/10 con conteo, segundo ciclo 9/10 con conteo (AUDNZD rojo 6/10, EURAUD verde 6/10, CHFJPY rojo 4/10, EURCHF rojo 4/10, CADCHF rojo 4/10, AUDUSD verde 2/10, EURCAD rojo 2/10, AUDCAD rojo 2/10, EURGBP verde 2/10). El reporte MINUTO paso de 'activos: 3-5/10' a 'activos: 7-9/10'.

## 29/08/2026 (noche) - BOT SATURACIONES V2: FREEZE EN MODO CRITICO + RESTAURACION RESPALDO 15H
- SINTOMA (reportado por el jefe): el bot (PID 5856, lanzado 18:49) se FRIZO: quedo atrapado en modo critico con EURAUD-OTC y no hacia nada mas.
- CAUSA (verificada en bot.log, 19:25:59): bucle infinito de poll fino en el MODO CRITICO con EURAUD-OTC: miles de lineas por segundo '[EURAUD-OTC] MODO CRITICO: vela doji (repetida): sigue esperando la vela final' + 'sello de cierre +20ms'. La vela cerrada se veia doji REPETIDA (mismo from) y el modo critico esperaba la 'vela final' que nunca cambiaba -> log de 2.5MB en minutos y bot ciego al resto. Los cambios de la tarde (estrategia 18:48, velas 18:00, bot 18:02) introdujeron el bucle.
- ORDEN DEL JEFE: volver a la version guardada a las 15:00 H (el ultimo respaldo): BOT-SATURACIONES-V2-RESPALDO-2026-08-29-15H (archivos hasta 15:07).
- RESTAURACION: bot frizado DETENIDO (PID 5856), carpeta en vivo BOT-SATURACIONES-V2 reemplazada COMPLETA con el contenido del respaldo 15H (22 archivos; el respaldo queda intacto). Log del freeze guardado en Temp/opencode/bot_v2_frizado_29ago.log para diagnostico futuro.
- VERIFICADO: py_compile 12 modulos OK, import estrategia OK, test_conteo.py del respaldo 33/33 PASAN. BOT RELANZADO (19:27, PID 14908): conectado PRACTICE, aviso Telegram OK, 10 streams suscritos, hilos de conteo iniciados.
- LIMPIEZA DEL ESCRITORIO (orden del jefe): creada 'C:\Users\wasc4\Desktop\respaldos de bots\' y movidas DENTRO las 10 carpetas de bots esparcidas: BOT ESTADISTICO - RESPALDO, BOT-MULTI-SECUENCIAS-BACKUP, BOT-SATURACION (V1), BOT-SATURACIONES-V2-RESPALDO, BOT-SATURACIONES-V2-RESPALDO-2026-08-29-15H, IQ Alternaciones - Version Especial de Respaldo, Pico de mechas Respaldo estable, PLANTILLA-IQ-OPTION, Velas dojis respaldo, Velas martillos respaldo. En el escritorio quedan SOLO: BOT-SATURACIONES-V2 (en vivo) + respaldos de bots. Belastoglish no se toco (no es bot).
- LECCION: la version 15H es la ESTABLE conocida; los cambios de la tarde (18:00-18:48) frizaron el bot en modo critico con vela doji repetida. Si se retoman esos cambios, revisar el bucle del modo critico ANTES (la 'vela final' nunca llega si la vela cerrada se repite como doji).

## 29/08/2026 (noche) - BOT SATURACIONES V2: DETONANTE 3 (patron A B B) + D1/D2 PAUSADOS
- ORDEN DEL JEFE: añadir un TERCER detonante de conteo y PAUSAR los dos primeros (no borrarlos: "estos no se van a utilizar").
- DETONANTE 3 (ACTIVO, regla del jefe): patron A B B. Una vela de un color + DOS velas consecutivas del color OPUESTO -> el conteo EMPIEZA con esas 2 B ya asignadas y cada B nueva suma (3, 4, 5... hasta velas_saturacion). Espejo incluido (V R R -> conteo de rojas; R V V -> conteo de verdes). El doji se IGNORA (no rompe el patron ni el conteo).
- IMPLEMENTACION (estrategia_saturacion_v2.py): _recalcular ahora DESPACHA: detonante_activo='d3' (default) -> _recalcular_d3 (nuevo); 'd1_d2' -> _recalcular_d1_d2 (logica vieja D1 racha A+B y D2 A B A B B movida tal cual, PAUSADA pero reactivable). config.json: "detonante_activo": "d3" en estrategia_params. configurar() acepta detonante_activo en vivo.
- LECCION DE LA ETAPA 9 APLICADA: el patron A B B se busca en TODA la ventana y el MAS RECIENTE manda (re-ancla): si al final hay un A B B del color opuesto, el conteo se re-ancla al patron nuevo (ej. 1 roja + 11 verdes -> VERDE 11). Esto evita los falsos 'buscando' del escaneo secuencial anclado al primer detonante. Desde el ultimo A B B se cuentan las B con las reglas normales (contraria aislada tolerada, contrarias cerca invalidan: '2 contrarias seguidas' / 'contraria + 1 a favor + contraria').
- VERIFICADO: py_compile OK; test_conteo.py ampliado: 56/56 PASAN (33 casos D1/D2 con detonante_activo='d1_d2' marcados como PAUSADOS + 21 casos D3 nuevos: patron basico, espejo, rachas hasta 10, patron en toda la ventana, re-ancla, contraria tolerada, invalidacion, alternancia perfecta -> buscando, dojis ignorados). Import OK, configurar OK (d3, velas_saturacion 6).
- BOT REINICIADO (19:36, PID 2524) con el D3 activo: primera operativa EURAUD-OTC en modo critico GANADA +$1.00, ciclo cerrado, sin errores.
- NOTA OPERATIVA: al reiniciar el bot se detuvo por error el proceso wally_telegram_bot.py (filtro 'bot.py' lo matcheo); se relanzo con lanzar_wally_telegram.ps1 (kilo en 4096 + wally PID 14560). OJO para el futuro: filtrar procesos por 'bot.py' EXACTO ('python -u bot.py'), nunca por substring.
- PENDIENTE: el jefe decide si el D3 necesita mas ajustes (velas_saturacion sigue en 6). D1/D2 reactivables con detonante_activo='d1_d2' en config.json.

## 29/08/2026 (noche, 20H) - RESPALDO ACTUALIZADO: BOT-SATURACIONES-V2-RESPALDO-2026-08-29-20H
- ORDEN DEL JEFE: el bot con la version actual (15H restaurada + DETONANTE 3) esta funcionando perfectamente; ANTES de tocar nada mas, actualizar la copia de respaldo con fecha 20:00 H.
- CREADO: C:\Users\wasc4\Desktop\respaldos de bots\BOT-SATURACIONES-V2-RESPALDO-2026-08-29-20H (copia completa de la carpeta en vivo, 22 archivos, SIN __pycache__; incluye .git e iqoptionapi). Contiene: estrategia_saturacion_v2.py con _recalcular_d3 (19:35), test_conteo.py 56 casos (19:36), config.json con velas_saturacion=10 y detonante_activo=d3 (19:39), bot.py motor 15H (15:07), operativa/velas/telegram_reporte 15H.
- NOTA CONFIG: el config.json en vivo fue reescrito por el bot (19:39): velas_saturacion paso de 6 a 10 (guardado de config viva, probablemente ajuste del jefe por Telegram). El respaldo 20H captura esa config real (10 + d3). El log del respaldo llega hasta 20:14 (corrida en vivo).
- REGLA: el respaldo 20H queda CONGELADO (nueva version estable de referencia). El respaldo 15H se conserva intacto como historico. Los cambios futuros van SOLO a la carpeta en vivo y se actualiza el respaldo SOLO con orden del jefe.
- DIAGNOSTICO PENDIENTE (NO tocado, orden del jefe): el modo critico hace spam de validaciones 'repetida' en el tramo :58-:00 del minuto (decenas de lineas por segundo en el log, caso CHFJPY 19:42:59) porque el corte del bucle rapido solo cubre seg_b < 1.0. El bot funciona bien (el jefe lo confirmo); si algun dia molesta, el fix seria ampliar el corte a todo el tramo final + descarga del broker cuando la vela nueva no llega al stream.

## 29/08/2026 (noche, 20:25) - BOT SATURACIONES V2: MARTINGALA HONESTA + PAYOFF EDITABLE + VELAS 5-25 + D1/D2 ELIMINADOS
ORDEN DEL JEFE (respaldo 20H NO tocado; cambios SOLO en la carpeta en vivo):
1. MARTINGALA HONESTA (riesgo.py + bot.py): el neto del dia NO deduce las perdidas parciales de la martingala; la UNICA deduccion es la PERDIDA COMPLETA del ciclo. Al ganar suma la ganancia neta (objetivo), no el bruto (antes gana() sumaba monto x payoff: con perdidas acumuladas el neto quedaba INFLADO). Aplicado en: PlanMartingala.gana() (riesgo.py) y _profit_season en _ejecutar_operativa_v2 (bot.py: solo deduce si not sigue). El motor viejo ya tenia la regla (1776).
2. PORCENTAJE FIJO EDITABLE (payoff): boton '💹 Porcentaje fijo' en Configuraciones -> teclado_payoff (presets 80/82/85/87/90/95 + texto libre 50-100) -> actualiza _config_vivo['payoff_fijo'] + plan.actualizar_payoff() en vivo. Nuevas funciones: teclado_payoff/mensaje_payoff (telegram_reporte.py), rama 'payoff' en _teclado_menu_actual y handler en hilo_telegram (bot.py). El panel muestra '💹 Porcentaje fijo: 85%'.
3. VELAS DE SATURACION: el teclado generico usa 'presets': [5..25] del CONFIG (21 botones en vez de 50) + texto libre validado 3-50 (min/max del CONFIG). teclado_parametro soporta el campo 'presets'.
4. D1/D2 ELIMINADOS POR COMPLETO (orden del jefe): borrados _recalcular_d1_d2, detonante_racha_a/b, detonante_activo, del CONFIG y del config.json; _recalcular es directamente el detonante A B B. test_conteo.py: solo casos D3 (23/23 OK).
FIXES DE VERIFICACION (hallazgos arreglados): plan.objetivo ahora se actualiza en vivo al cambiar la ganancia objetivo por Telegram (antes el panel mostraba el nuevo pero el monto seguia con el del arranque); _multiplicador_perdida_total y los 'proximo monto' usan _config_vivo (seguian al payoff/niveles nuevos); mensaje de perdida muestra las perdidas acumuladas REALES del ciclo (antes mostraba solo el monto de la operacion).
HALLAZGOS PENDIENTES PARA EL JEFE: (a) el mensaje de perdida muestra 'MG n' con el nivel YA incrementado (al perder MG2 muestra MG 3): solo numeracion, no afecta montos; (b) el spam del modo critico (documentado arriba) sigue presente si algun dia molesta.
VERIFICADO: py_compile 12/12 OK, test_conteo 23/23, smoke riesgo (3 perdidas parciales no tocan neto, gana suma +1.0, payoff 0.87 cambia monto), import bot OK, teclados OK (21 botones velas, presets payoff, panel con %). BOT REINICIADO (20:25, PID 2592): conectado, 10/10 activos, reportes normales. Wally relanzado con su orquestador (kilo 4096 + wally PID 14364) tras detectarlo caido.

## 29/08/2026 (noche, 20:47) - REPORTE SIN MODO CRITICO (regla del jefe)
- ORDEN DEL JEFE: eliminar del reporte minuto de Telegram la linea 'MODO CRITICO: <activo>' y el bloque especial del candidato; el activo en modo critico se muestra IGUAL que los demas (saturacion, conteo, interrupciones, faltan/direccion) y la UNICA diferencia es el rayo ⚡ al lado del foguito 🔥 en su nombre.
- IMPLEMENTADO: bot.py (hilo_reporte): ELIMINADO el prefijo '🎯 MODO CRITICO: <activo> (falta 1 vela para operar al :00)' que se anteponia al reporte. estrategia_saturacion_v2.py: lineas_reporte() ya NO tiene el bloque especial del candidato (cae al bloque normal SATURACION X con N/10, interrupciones, faltan/dir); indicadores() devuelve ['🔥','⚡'] cuando es_candidato() (antes solo 🔥). El log LOCAL sigue mostrando 'MODO CRITICO: falta 1 vela' en descripcion() (diagnostico, no llega a Telegram).
- VERIFICADO: py_compile OK, smoke test: candidato 9/10 -> indicadores ['🔥','⚡'] y lineas normales (SATURACION VERDE 9/10, Interrupciones 0, Faltan 1 | dir: PUT). BOT REINICIADO (20:47, PID 17288) con los cambios; wally intacto (14364).

## 29/08/2026 (noche, 21:49) - DIAGNOSTICO: ACTIVOS CONGELADOS EN EL REPORTE (AUDUSD/EURGBP 4/8) + REINICIO
- SINTOMA DEL JEFE: AUDUSD y EURGBP congelados en la parte superior del reporte con conteo 4 (4/8), sin avanzar.
- CAUSA RAIZ (log): 21:06:00 CHFJPY entro en MODO CRITICO, ejecuto CALL $1.22 y el CICLO VELA A VELA quedo atado a CHFJPY -> se DESUSCRIBIERON los streams de los otros 9 activos (AUDUSD y EURGBP incluidos). 21:07:00 el resultado fue EMPATE (reembolso): el codigo cierra _ciclo_martingala_activo PERO NO llama _reanudar_streams_ajenos (HALLAZGO-BUG: el branch de empate en _ejecutar_operativa_v2 no re-suscribe los streams ajenos). Resultado: los 9 activos quedaron SIN STREAM -> sus hilos seguian 'vivos' (sellos por descarga) pero el conteo CONGELADO en el ultimo estado (AUDUSD rojo 4/8, EURGBP rojo 4/8 desde 21:05); CHFJPY quedo en bucle de reintento/validacion (spam de sellos, MG1 rechazado 'Sin tiempo de expiracion disponible' 21:07:58). El bot NO operaba nada mas (ciclo atado).
- ACCION: BOT REINICIADO (21:49, PID 7704): 10 streams re-suscritos, conteos reconstruidos, AUDUSD/EURGBP avanzando normal (verde 2/8 -> 3/8). Wally intacto.
- FIX PENDIENTE (con luz verde del jefe): en _ejecutar_operativa_v2 el branch de EMPATE (resultado == 'empate') debe llamar _reanudar_streams_ajenos(...) igual que el branch de ganada (las lineas 2470-2472 solo cierran el ciclo sin re-suscribir). Tambien revisar el reintento vela a vela: si el broker rechaza el MG1, el bot martilla sin avanzar (deberia soltar el ciclo tras N rechazos o re-suscribir igualmente).

## 29/08/2026 (noche, 21:52) - REGLA DEL EMPATE: REINTENTO VELA A VELA CON EL MISMO MONTO (fix CHFJPY)
- ORDEN DEL JEFE: cuando una operacion sale EMPATE (reembolso), el bot debe REINTENTAR en la siguiente vela con el MISMO monto, uno detras de otro (como martingala vela a vela), hasta obtener resultado definido (ganada o perdida). El empate no cierra el ciclo y no toca el plan (nivel y monto iguales).
- IMPLEMENTADO (bot.py, branch 'empate' de _ejecutar_operativa_v2): el empate ya NO hace _ciclo_martingala_activo = None; en su lugar activa el reintento inmediato con est.registrar_resultado(False, direccion, sigue=True) (que pone la estrategia en vela a vela con la misma direccion) y mantiene el ciclo atado al activo. El plan no se toca: mismo nivel, mismo monto. Cuando el reintento gana -> ciclo se cierra y re-suscribe (flujo normal de ganada); cuando pierde -> plan.pierde() sube nivel (martingala normal). Esto ADEMAS arregla el bug del 21:06 (el empate ya no deja los streams ajenos desuscritos para siempre: el ciclo se mantiene durante el reintento y se cierra con resultado definido).
- Mensaje de Telegram de empate actualizado (telegram_reporte.py operacion_empate): 'Reintento en la siguiente vela con el mismo monto...'.
- VERIFICADO: py_compile OK; smoke test completo: saturacion -> operar; EMPATE -> reintento_inmediato True (mismo monto $1.18, nivel 0); siguiente vela -> ('operar','put'); 2do EMPATE -> reintenta otra vez; reintento PERDIDO -> plan sube a nivel 1 ($2.56); reintento GANADO -> +$1.00, nivel 0, ciclo cerrado. BOT REINICIADO (21:52, PID 1840) con el fix; wally intacto (14364).

## 29/08/2026 (noche, 21:56) - DETALLES DE INTERFAZ (reglas del jefe)
1. PAYOFF CON %: los presets llegan como '82%' (o '✅ 82%'); el handler de 'payoff' ahora limpia los caracteres no numericos antes de parsear (join de digitos/punto/comma). Antes float('82%') fallaba y el preset parecia no detectarse.
2. FUEGO/RAYO INTERCAMBIADOS (indicadores de la estrategia): LISTO -> 🔥 (fuego solo); conteo con faltan <= 2 (incluido el candidato de modo critico) -> ⚡ (rayo solo); ciclo de recuperacion vela a vela -> 🔥⚡ (sin cambio).
3. EMOJI DE VELAS DE SATURACION: el CONFIG declara 'emoji': 🕯️ (vela) y el teclado de configuraciones + el titulo del selector usan el emoji propio del parametro (p.get('emoji') or '⚙️'). Se evita el ⚙️ repetido.
4. EMOJIS CORREO/CUENTA INTERCAMBIADOS en el panel de configuraciones: correo -> 👤, tipo de cuenta -> 📧 (antes al reves).
5. 'Interrupciones' SIEMPRE en plural en el reporte minuto (antes 'Interrupcion: 1' con 1 sola).
- VERIFICADO: py_compile OK; smoke: '82%'->82.0, '86.5'->86.5; listo->['🔥'], faltan<=2->['⚡']; 'Interrupciones: 1'; boton '🕯️ Velas de saturacion'; panel con '👤 correo' y '📧 PRACTICE'. BOT REINICIADO (21:56, PID 3516); wally intacto (14364).

## 29/08/2026 (noche, 22:04) - FIX MONTO AUTOMATICO (estaba muerto: nadie llamaba las funciones)
- HALLAZGO (pedido del jefe: revisar el boton de monto auto con el payoff modificable): las funciones _actualizar_objetivo_auto / _aplicar_objetivo_monto_auto EXISTIAN pero NADIE las llamaba (ni el arranque, ni un hilo, ni el handler). El boton solo encendia modo_monto_auto en la config viva y el plan seguia con el objetivo MANUAL para siempre. El monto auto no hacia nada funcional.
- FIX: (1) handler de ACTIVAR: llama _actualizar_objetivo_auto(api, _plan_global) al instante; (2) handler de DESACTIVAR: restaura plan.objetivo = objetivo_neto manual + limpia _obj_monto_auto_global y plan._objetivo_monto_auto (antes quedaba congelado con el ultimo objetivo auto); (3) NUEVO hilo _hilo_objetivo_auto (daemon, cada 60s) que recalcula el objetivo con el saldo fresco; (4) llamada inicial al arranque (despues de conectar); (5) _actualizar_objetivo_auto ahora usa _config_vivo (payoff/niveles/base/margen/umbral vivos) en vez de config estatica: todo cuadra con el PORCENTAJE FIJO MODIFICABLE (k = multiplicador de perdida total con payoff vivo; MG0 = objetivo/payoff vivo).
- VERIFICADO: py_compile OK; smoke: payoff 0.85 -> k=105.30, saldo 500 -> objetivo $4.65, MG0 $5.47; payoff 0.87 -> k=97.61 -> objetivo $5.02, MG0 $5.77 (el payoff mas alto da montos mayores: sincronizado); desactivar vuelve a objetivo manual (MG0 $1.15 con 0.87). BOT REAL al arrancar (22:04:50): 'MONTO AUTO: saldo total $9873.97 -> objetivo $91.90 (MG0 $108.12, k=105.3)' -> el monto auto aplica al plan y al panel. BOT REINICIADO (22:04, PID 15920); wally intacto (14364).

## 29/08/2026 (noche, 22:27) - SISTEMA DE ARRASTRE (mudanza por rechazo del broker)
- REGLA DEL JEFE: si el broker RECHAZA una operativa en un MG del ciclo vela a vela (mercado cerrado, tiempo de expiracion cambiado, etc. — causas del BROKER, no del bot), el bot ABANDONA ese activo, suelta el ciclo atado, re-suscribe TODOS los streams (todo el mercado vuelve a escanear) y el ARRASTRE (nivel + monto) queda guardado en el plan GLOBAL. La PRIMERA saturacion nueva de CUALQUIER activo retoma la martingala con ese nivel y monto (ej. venia en MG2 $5.58 -> el primer activo que complete saturacion entra en MG2 $5.58). Si vuelve a ser rechazada: se repite la mudanza y el arrastre sigue.
- IMPLEMENTADO (bot.py, _ejecutar_operativa_v2, bloque de rechazo): reemplazado el viejo 'se queda reintentando en cada senal' (que dejaba el ciclo atado y paralizaba el bot, caso CHFJPY 21:06) por el ARRASTRE: suelta _ciclo_martingala_activo/_ciclo_vela_activo, resetea la estrategia SIN ciclo (est._ciclo_vela=False + reconstruir([])), re-suscribe los streams ajenos (_reanudar_streams_ajenos), log + mensaje Telegram 'ARRASTRE guardado: MGn ($monto)'. Tambien cubre el rechazo en MG0 con ciclo atado (se suelta el ciclo sin arrastre). El plan NO se toca: conserva nivel y perdidas_acumuladas (monto = (perdidas+objetivo)/payoff). El reporte ya muestra 'Buscando martingala N' y 'Proximo monto MG' durante el arrastre.
- RESPALDO ACTUALIZADO ANTES DEL CAMBIO (orden del jefe, congelado): C:\Users\wasc4\Desktop\respaldos de bots\BOT-SATURACIONES-V2-RESPALDO-2026-08-29-22H (22 archivos, version sin el arrastre).
- VERIFICADO: py_compile OK; smoke completo: ciclo MG2 ($5.58) -> rechazo -> estrategia buscando sin reintento, plan conserva nivel 2 y $5.58 -> nueva saturacion en OTRO activo opera MG2 $5.58 -> otro rechazo: el arrastre sigue -> perdida: sube a MG3 $12.14 -> ganada: +$1.00, nivel 0. BOT REINICIADO (22:27, PID 13540) con el arrastre activo; wally intacto (14364).

## 29/08/2026 (noche, 22:38) - DEFAULTS 82%/10 VELAS + FIX PERSISTENCIA PAYOFF + VERIFICACION CUENTA
- ORDEN DEL JEFE: porcentaje fijo por defecto 82% y velas de saturacion por defecto 10 (ambos editables por Telegram). Verificar el boton de cambiar cuenta (para el paso a REAL sin problemas). Verificacion de integridad + busqueda de bugs/bloqueos de teclados.
- CAMBIOS: config.json -> payoff_fijo 0.82 y velas_saturacion 10 (el CONFIG de la estrategia ya tenia default 10). Todos los fallbacks 0.85 del codigo pasan a 0.82 (bot.py 12 lugares, riesgo.py 2, telegram_reporte.py mensaje 'ej. 82% = $1.22 -> $1.00 neto'). El teclado_payoff ya tenia el preset 82%.
- FIX DE VERIFICACION (bug real): el payoff cambiado por Telegram NO persistia (vivia solo en memoria; al reiniciar volvia al default) y el panel ignoraba el payoff_fijo del config.json (mostraba 85 aunque el archivo dijera 0.82). Ahora _sincronizar_config_viva carga 'payoff_fijo' (y 'tipo_cuenta') a la config viva y _guardar_config_viva lo persiste en config.json.
- FIX CAMBIO DE CUENTA (verificado): _cambiar_tipo_cuenta ahora tambien resetea la cache de saldo del MONTO AUTO (_saldo_auto_cache) y actualiza _config_vivo['tipo_cuenta']: al pasar a REAL, el monto auto usa el saldo de la cuenta nueva de inmediato (antes podia usar el saldo de PRACTICE hasta 60s). El flujo del boton: change_balance con timeout real (15s), guarda config.json, resetea saldo/profit. Wizard de login: para cambiar de cuenta REAL primero hay que CERRAR SESION (flujo existente).
- VERIFICADO: py_compile 12/12 OK, tests 23/23, import OK, los 10 teclados responden (principal, config, estado, mg, objetivo, payoff, montoauto, cuenta, activos, parametro), presets payoff con 82 marcado, botones de cuenta (Practica/Real/Volver), persistencia probada (0.87 guardado y restaurado a 0.82). Sin bloqueos de teclado: todo texto libre responde (menus numericos con ValueError -> teclado de nuevo; el resto re-renderiza el menu actual). BOT REINICIADO (22:38, PID 12056): MONTO AUTO con 82% -> saldo $9874.79, k=118.5, objetivo $81.63, MG0 $99.55; conteos /10; wally intacto (14364).

## 29/08/2026 (noche, 22:46) - NOMBRE DEL BOT + CREDENCIALES FLOW 3 + PUSH GITHUB
- NOMBRE: el bot se llama 'BOT DE SATURACIONES'. Aplicado en: titulo del reporte minuto (era 'BOT IQ OPTION'), pie del panel de configuraciones, y aviso de arranque (bot_iniciado_saturacion: '🔥 BOT DE SATURACIONES INICIADO ✅', estrategia 'SATURACION V2', descripcion del detonante actualizada: 'Buscando patron A B B (1 contraria + 2 iguales)').
- CREDENCIALES (orden del jefe): el bot pasa a la cuenta WASCARFLOW3 (wascarflow3@gmail.com). El dict _CUENTAS_IQ del credenciales.py ya tenia la cuenta; solo se cambio CUENTA_ACTIVA = 'WASCARFLOW3' (antes WASCAR2416). BOT REINICIADO (22:46, PID 7240): conectado con Flow 3, PRACTICE, aviso Telegram OK (token de la cuenta Flow 3).
- PUSH GITHUB (orden del jefe: al repo que ya existe, con la CLI/credenciales autenticadas): origin = https://github.com/wascar2416-star/BOT-SATURACIONES-V2.git, push main 4c88ff6..410c023 EXITOSO. El repo rastrea SOLO codigo (verificado con git ls-files: bot.py, estrategias, config.json, iqoptionapi, requirements, Procfile, README, tests...); sin logs, sin backups, sin credenciales, sin .bat (todo en .gitignore) -> la nube genera lo demas.
- NOTA: se intento primero con la URL wascar-flow/BOT-SATURACIONES-V2 (no existe el repo); el jefe aclaro que el push va a la cuenta que ya esta (wascar2416-star).

## 29/08/2026 (noche, 23:26) - MENSAJES DE OPERACION REDISENADOS (bloque del activo + arbol conectado)
- REGLA DEL JEFE (aprobo el mockup): los mensajes de operacion (ejecutada, ganada, perdida, empate, rechazada) muestran PRIMERO el bloque del activo igual que en el reporte minuto: '🔹 ACTIVO 🔥⚡' + saturación/conteo/interrupciones/faltan-direccion, y el ARBOL BAJA CONECTADO: la ultima rama del bloque pasa de └ a ├ y una vertical ' │ ' desciende por el espacio hasta los datos de la operacion (monto, nivel, ganancia, perdidas, motivo).
- IMPLEMENTADO: telegram_reporte.py: nuevo helper _bloque_encabezado_activo(activo, bloque_activo, indicadores) usado por las 5 funciones operacion_*. bot.py (_ejecutar_operativa_v2): el bloque se captura AL EJECUTAR (est.lineas_reporte() + est.indicadores() antes de registrar_resultado) y se pasa a ejecutada/ganada/perdida/empate; en el rechazo se captura en el momento. El motor viejo no se toco (no se usa).
- VERIFICADO: py_compile OK; smoke: mensajes generados con la estrategia real (saturacion verde 7/10) -> bloque arriba, ' │' conectando, datos de la operacion abajo, PROFIT al final. BOT REINICIADO (23:26, PID 5944). PUSH GITHUB: 5d6d5f9..ef3d8fe main -> main (wascar2416-star/BOT-SATURACIONES-V2). Wally intacto.

## 30/08/2026 (madrugada, 00:10) - FIX BUCLE RAPIDO EN LA NUBE + SIN CONTADOR EN OPERACIONES
- DIAGNOSTICO NUBE (pedido del jefe, solo lectura): en Railway, la MG2 de EURCAD entro a las 03:45:13 con entrada :047 (13 SEGUNDOS tarde): 'stream sin avance (10s): re-suscribiendo' -> el stream se CONGELO. Causa raiz: spam masivo de 'sello de cierre +20 ms' en el tramo :58-:60 (Railway: 'rate limit of 500 logs/sec reached... Messages dropped: 248'). El corte del bucle rapido solo cubria seg_b < 1.0; el tramo :58-:60 quedaba descubierto y los hilos martillaban el sello, congestionando el websocket y congelando streams. NO era desfase (sellos +20ms perfectos).
- FIX (bot.py, los 3 cortes del bucle): corte AMPLIADO a TODO el tramo :58.5-:01.5 (si _seg_b >= 58.5: sleep((60-seg)+1.5+0.05); si < 1.5: sleep(1.5-seg+0.05)). Cada hilo procesa el cruce del :00 UNA vez por minuto -> se acaba el spam, los streams no se congelan y las senales vela a vela vuelven al :00.
- SIN CONTADOR EN OPERACIONES (regla del jefe): _bloque_encabezado_activo (telegram_reporte.py) filtra la linea 'N / M velas' SOLO en los mensajes de operacion (ejecutada/ganada/perdida/empate/rechazada); el reporte MINUTO conserva el contador siempre (lineas_reporte() intacta).
- RESPALDO ACTUALIZADO ANTES DEL FIX: C:\Users\wasc4\Desktop\respaldos de bots\BOT-SATURACIONES-V2-RESPALDO-2026-08-29-23H (22 archivos, congelado).
- VERIFICADO: py_compile OK; smoke: lineas_reporte con '│ 11 / 10 velas' (reporte OK), mensaje de operacion SIN contador (SATURACION VERDE, Interrupciones, LISTO, datos de la operacion). BOT REINICIADO (23:51, PID 13760). PUSH GITHUB: 8761bfb..f4041f2 (wascar2416-star/BOT-SATURACIONES-V2). Wally intacto.

## 30/08/2026 (madrugada, 00:30) - FIX SELLO CON CANDADO DE FRESCURA (nube) + MONTO AUTO OFF DEFAULT
- DIAGNOSTICO NUBE (pedido del jefe): operativas rechazadas en bucle con 'ventana de expiracion cerrandose' (EURGBP/CADCHF 03:54:58, 03:55:58...) aunque los activos estaban disponibles. CAUSA: el stream en la nube llega ATRASADO (la 'ultima vela cerrada' era la del minuto ANTEpasado); el sello se aceptaba con ella (from + TF <= now se cumple todo el minuto) y la expiracion (from + 2*TF) caia a ~2s del cierre -> el chequeo <10s (operativa._expiry_valido) omitia la operativa. No era el activo ni el desfase: era la vela base vieja.
- FIX (bot.py, sello): candado de FRESCURA: el sello SOLO vale si int(_from_viva) == (minuto_actual - 60) (la vela que acaba de cerrar). Con stream atrasado el sello no llega en el tope (3s) y el flujo normal descarga la vela OFICIAL del broker para calcular la expiracion fresca. operativa.py no se toco (su chequeo <10s es correcto y defensivo).
- MONTO AUTO OFF POR DEFAULT (regla del jefe): config.json -> modo_monto_auto false (el bot local sigue corriendo con su config en memoria; el cambio aplica al proximo arranque/redeploy; la config viva ya usa default false en _sincronizar_config_viva).
- NO se relanzo el bot local (orden del jefe: solo push). PUSH GITHUB: f4041f2..7a4b27f (wascar2416-star/BOT-SATURACIONES-V2), listo para que Railway redepliegue.

## 31/08/2026 - FIX DOJI = INTERRUPCION (regla del jefe, BOT DE SATURACIONES V2)
- PROBLEMA (reportado por el jefe): las velas doji se contaban como velas de color (4 rojas + doji = 5, disparaba la entrada). Causa raiz DOBLE: (1) es_doji exigia open == close EXACTO y el broker entrega dojis de grafico con ruido de precision flotante (diferencias ~1e-13 o menos de medio tick) -> se clasificaban rojas/verdes; (2) color_vela evaluaba el COLOR antes que el doji, asi que aunque es_doji fuera True la vela salia roja/verde.
- REGLA NUEVA (orden del jefe): la doji es una INTERRUPCION exacta: no suma, rompe el detonante A B B (V D R R ya no forma patron), una doji aislada se tolera (el conteo espera) y 2 interrupciones seguidas (doji+doji, doji+contraria, contraria+doji) INVALIDAN, tambien en modo critico (antes la doji se ignoraba por completo).
- FIX: velas.py -> es_doji con tolerancia de MEDIA unidad de tick (tick_precio: 0.00001 forex / 0.001 JPY / 0.01 indices); color_vela evalua es_doji PRIMERO. La regla AUDUSD 29/08 queda intacta: una vela con cuerpo real de 1 tick o mas es de SU COLOR. estrategia_saturacion_v2.py -> _recalcular incluye dojis en la secuencia (el detonante exige 3 velas consecutivas no-doji; la doji se trata como interrupcion con las mismas reglas de invalidacion que las contrarias); validar_vela_critica (modo critico) -> doji aislada tolera, con interrupcion pendiente invalida.
- VERIFICADO: py_compile OK; test_conteo.py actualizado y pasando 27/27 (incluye el caso exacto del jefe: 4 rojas + doji con ruido -> rojo 4 sin senal; 5 rojas reales -> opera call; doji aislada + roja -> completa la saturacion; 2 dojis, doji+contraria y contraria+doji -> invalidan; modo critico coherente; vela de 1 tick sigue siendo de su color).
- RESPALDO ANTES DEL CAMBIO (orden del jefe): C:\Users\wasc4\Desktop\BOT-SATURACIONES-V2-RESPALDO-31082026 (copia completa de la carpeta).
- PUSH GITHUB: 8e34c67..56dde39 main -> main (wascar2416-star/BOT-SATURACIONES-V2). Bot local NO relanzado (orden del jefe: solo fix + push).

## 31/08/2026 (noche) - FIX PRECISION DOJI EN LA VERSION ESTABLE (nube)
- CONTEXTO: el jefe pidio aplicar el fix del doji a la version que corre en la NUBE: repo wascar2416-star/BOT-SATURACIONES-V2-ESTABLE (rama main, ultimo commit fcccf1e 31/08: margen de cierre 280ms). Es una rama hermana MAS avanzada que el bot local (defensa autonoma del monto auto, vigilante por activo, detonante primario, identidad/espejo, max interrupciones, invalidacion vigente, cache por activo).
- PROBLEMA (reportado por el jefe, confirmado con prueba sintetica sobre el codigo real): (1) dojis de grafico con RUIDO de precision (open/close casi iguales, 1e-13 o medio tick) se clasificaban ROJAS/VERDES y SUMABAN al conteo (4 rojas + doji = 5, disparaba entrada); (2) velas pequenas reales a favor con open==close en los datos se marcaban doji/interrupcion y NO sumaban. Causa: es_doji exigia open == close EXACTO y color_vela evaluaba el color ANTES que el doji.
- REGLA CONFIRMADA (jefe): doji = INTERRUPCION exacta (igual que una contraria): aislada tolera (el conteo espera); 2 interrupciones seguidas (doji+doji, doji+contraria, contraria+doji) DESCARTAN el conteo; interrupcion + 1 a favor + interrupcion invalida. MODO CRITICO: la doji ya NO se ignora, es interrupcion (tolera 1, con pendiente descarta). La doji NO participa en el detonante A B B (V D R R -> rojo 2, orden 30/08 intacta).
- FIX APLICADO (3 archivos): velas.py -> es_doji con umbral |close-open| <= 0.5*tick + holgura de representacion (tick*1e-6: la resta de flotantes excede el medio tick por ~1e-16; 6 ordenes menor que 1 tick real, jamas convierte una vela de 1 tick en doji); color_vela evalua el doji PRIMERO. estrategia_saturacion_v2.py -> nuevo flag _pendiente_doji (persistido en cache y reconstruccion) para distinguir el tipo de interrupcion pendiente: si la pendiente es doji y llega otra interrupcion se DESCARTA; solo 2 contrarias REALES seguidas transfieren identidad por ESPEJO (regla 30/08 intacta). Aplicado en _recalcular, _procesar_incremental y validar_vela_critica (modo critico). test_conteo.py -> seccion PRECISION DEL DOJI + casos nuevos de modo critico (doji+contraria, 2 dojis, contraria+doji).
- VERIFICADO: py_compile OK; suite completa ESTABLE 23/23 (incluye: doji con ruido 1e-13 -> doji; medio tick 0.718300->0.718295 -> doji; 1 tick real -> color y SUMA; 2 ticks -> color; 4 rojas + doji ruido -> rojo 4 sin senal; 4 verdes + 1 tick real -> verde 5; doji+contraria y contraria+doji descartan; identidad/espejo/cache/max interrupciones/invalidacion vigente intactos).
- RESPALDO (orden del jefe): copia fisica C:\Users\wasc4\Desktop\BOT-SATURACIONES-V2-ESTABLE-RESPALDO-31082026 + tag git respaldo-31082026-predoji (pusheado al repo ESTABLE; restaurar: git checkout respaldo-31082026-predoji).
- PUSH GITHUB: fcccf1e..3952a45 main -> main (wascar2416-star/BOT-SATURACIONES-V2-ESTABLE), listo para que Railway redepliegue la nube. El bot local (BOT-SATURACIONES-V2) quedo con su propio fix del doji (commit 56dde39) con la misma deteccion (umbral medio tick) pero con la regla local (doji rompe el detonante); si el jefe quiere alinearlo con la ESTABLE, es otro cambio.
