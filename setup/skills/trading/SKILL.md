---
name: trading
description: Trading y APIs de IQ Option: velas, indicadores, riesgo y bots.
---

# Trading — Trading y APIs de mercado

Guia para el trabajo de trading del usuario: plataformas como IQ Option,
datos de mercado, velas, indicadores, latencia, gestion de riesgo y bots.
Base para el proyecto IQ-ULTIMATE y futuros desarrollos.

## Cuando usar esta skill

- Analizar velas, tendencias, indicadores o datos de mercado.
- Crear, ampliar o arreglar un bot de trading (IQ Option u otro corredor).
- Trabajar con la API de una plataforma de trading (iqoptionapi y similares).
- Optimizar latencia, tiempos de entrada o gestion de riesgo.
- Auditar modulos de un bot de trading (velas, señales, ejecucion).

No activarla para trading general sin codigo ni para bots de Telegram: eso es
python-dev o bot-builder.

## Plataformas y librerias

- IQ Option: paquete `iqoptionapi` (en el Python 3.12 del usuario). Es una
  API no oficial: verificar siempre la conexion y los estados de sesion.
- Proyecto conocido del usuario: `IQ-ULTIMATE` en el Escritorio (bot de velas
  y latencia). Estructura: config.py, requirements.txt, modulos de velas.
- Otras librerias disponibles: pandas, numpy, scipy, websockets, requests.

## Principios de un bot de trading

1. Datos de mercado primero: velas limpias y sincronizadas antes de operar.
2. Latencia controlada: medir y registrar tiempos de ida y vuelta.
3. Riesgo gestionado: nunca apostar mas de lo definido por operacion.
4. Estados claros: el bot sabe si esta conectado, esperando, o en operacion.
5. Log completo: cada decision (entrada, salida, error) queda registrada.
6. Fallo seguro: si pierde conexion, no abrir posiciones a ciegas.

## Buenas practicas

- Credenciales de la cuenta NUNCA hardcodeadas: config aparte o variables.
- Usar timeouts y reintentos en las conexiones websocket/API.
- Validar cada vela antes de usarla (timestamp, precio, formato).
- Probar en modo demo/paper antes de operar con dinero real.
- Documentar cada bot creado en `memoria_jarvis.md` y guardar scripts
  reutilizables en `voz_kokoro/manos/`.
- Al auditar codigo de trading: compilar y revisar logica de riesgo primero.

## Verificacion (bucle de calidad)

1. Compilar el script: `python -m py_compile script.py`.
2. Probar la conexion con la plataforma y verificar que llegan datos reales.
3. Probar en demo/paper una pasada completa (entrada, espera, salida).
4. Revisar el log: sin errores de conexion ni posiciones raras.
5. Si falla: corregir, compilar, probar de nuevo. Solo entregar cuando una
   pasada real completa funciona sin errores y el riesgo esta controlado.
6. Rutas dentro de la skill con barra normal `/`.

# HISTORIAL ARGUMENTADO DEL BOT-SATURACIONES-V2 (29/08/2026)

Memoria de razonamiento del bot de trading del jefe: cada decision tomada,
POR QUE se tomo, y la leccion que dejo. Sirve para no repetir diagnosticos
y para argumentar los proximos cambios con el mismo criterio.

## El bot y su casa

- Bot: BOT-SATURACIONES-V2 en `C:\Users\wasc4\Desktop\BOT-SATURACIONES-V2\`
  (la base mas moderna: motor v5 + operativa v2 + reporte del minuto).
- Plantilla de la que se copio: MULTI-SECUENCIAS (entrada al :00 + martingala
  vela a vela) transplantada sobre el motor V2. El motor es generico: la
  logica vive en `estrategia_saturacion_v2.py`; el motor NO conoce la
  estrategia (contrato en estrategia_base.py).
- Respaldo CONGELADO (regla del jefe, NO TOCAR):
  `C:\Users\wasc4\Desktop\BOT-SATURACIONES-V2-RESPALDO-2026-08-29-15H`.
  Los cambios van SOLO a la carpeta en vivo.
- Memoria del jefe: `C:\Users\wasc4\Documents\Default Project\voz_kokoro\memoria_jarvis.md`.

## Etapa 0 — El diagnostico inicial (por que empezo todo)

- Sintoma: las entradas llegaban 1-2s TARDE (sellos a :02-:03 en vez del :00).
- Por que importaba: en binarias de 1 minuto, 2s de retraso = expiracion mal
  calculada, precio de entrada peor, y en martingala el retraso se acumula
  operacion tras operacion.
- Argumento: el timeSync de IQ Option llega con SESGO DE RTT (hasta -1.2s en
  VPN); medir el desfase como RTT/2 asume una simetria de red que NO existe.
  La recalibracion por candela es CIRCULAR (mide latencia, no reloj): solo
  empeoraba el cruce. El reloj local NTP esta sincronizado con el broker
  (+/-200ms): es la fuente de verdad del :00.

## Etapa 1 — Transplante MULTI-SECUENCIAS (entrada al :00 + martingala vela a vela)

- Se copio la maquinaria del BOT-MULTI-SECUENCIAS (descarga original en
  Downloads): entrada al :00 exacto con expiracion desde el 'from' de la vela
  cerrada, y ciclo de martingala vela a vela INMEDIATA (perdida -> siguiente
  vela en el mismo minuto, sin esperar nueva saturacion).
- Argumento: no reinventar. El bot secuencias YA demostro entrar al :00 y
  recuperar vela a vela; la regla de oro es copiar la plantilla que funciona
  y cambiar solo la logica.

## Etapa 2 — Motor v5 (reloj local, desfase 0 fijo)

- Fix: desfase = 0.0 FIJO, cruce por reloj local, margen 0.25s, sello por
  vela cerrada en stream local (+20ms). Se elimino la maquinaria de desfase
  por candela (circular).
- Resultado verificado: entradas reales a :001-:179 (antes :02-:03).
- Leccion: cualquier desfase medido sobre websocket esta contaminado por RTT;
  el reloj local NTP es mas confiable que toda la maquinaria de timeSync.

## Etapa 3 — Fix del bucle rapido (EURAUD 15:47, 40 sellos/seg)

- Sintoma: el bot entraba en bucle fino re-disparando compras al :00
  (40 sellos/seg) -> 'Insufficient funds' y spam.
- Fix: corte ampliado del bucle (:00-:01 y :58.5-:59.9) -> 10 sellos/seg.
- Leccion: el poll fino del :00 necesita un corte EXPLICITO; sin el, el
  dedupe por vela no alcanza (la misma ventana re-dispara).

## Etapa 4 — Fix de la ventana parcial (maxdict)

- Sintoma: algunos activos llegaban con ventanas de 5-15 velas en vez de 30
  -> el conteo se calculaba sobre datos incompletos.
- Fix: suscribir_stream verifica el maxdict (30 velas) al suscribir
  (re-suscripcion hasta 3 intentos) + reparador de streams vacios/parciales
  con cooldown 30s.
- Leccion: el stream local es la fuente primaria (0 lock, 0 red en el tramo
  del :00), pero hay que VERIFICAR que este completo antes de confiar.

## Etapa 5 — Detonante unico A B B (regla del jefe)

- Sintoma: con los detonantes viejos (D1: racha 2+2; D2: patron de 5 velas
  A B A B B), solo 3-4 activos con conteo: eran demasiado estrictos para el
  mercado OTC.
- Diseno nuevo del jefe: patron A B B = UNA vela de un color + DOS velas
  consecutivas del color OPUESTO (o su espejo). Ej: V R R -> ROJO 2; R V V ->
  VERDE 2. El patron se busca en TODA la ventana (30 velas): si las ultimas
  son todas del mismo color, la contraria que las respalda se busca mas
  atras (1 roja + 10 verdes -> VERDE 10, caso del jefe).
- Se BORRARON el D1 2+2, el D2 con sus 2 formas, las dos pasadas de
  _recalcular y los parametros detonante_racha_a/b del CONFIG.
- Argumento: la logica la define el jefe; mi trabajo es implementarla
  SIMETRICA (el espejo incluido, sin hardcode de color) y verificar con
  velas sinteticas antes de tocar el motor.

## Etapa 6 — DOJI como CONTRARIA (regla del jefe, 29/08)

- Antes: el doji se IGNORABA por completo (no suma, no invalida, no rompe).
- El jefe cambio la regla: el doji se trata como una vela CONTRARIA en TODOS
  los aspectos: puede INICIAR el patron (D R R -> rojo 2), se tolera aislado
  en el conteo (despues de 2+ a favor), y CUENTA para la invalidacion
  (doji + roja = 2 contrarias -> invalida; 2 dojis -> invalida).
- En el MODO CRITICO: el doji se tolera como contraria (esperar contraria) y
  con otra pendiente invalida.
- MARTINGALA INTACTA: la regla del doji aplica SOLO al conteo ANTES de la
  MG0. En ciclo vela a vela el bot opera SI O SI con cualquier vela nueva
  (doji, contraria o a favor): la unica pregunta es gane o perdi.
- Leccion: las reglas del conteo y las del ciclo de martingala son MUNDOS
  SEPARADOS; nunca mezclarlas.

## Etapa 7 — DOJI de 1 tick o menos (regla del jefe)

- Antes: doji solo si apertura == cierre EXACTO.
- El jefe cambio: una vela que se movio EXACTAMENTE 1 tick o menos es doji
  (caso AUDUSD 22:45 con cuerpo de 1 tick). es_doji usa tick_precio
  (forex OTC 1e-5, JPY 1e-3, indices >=1000: 1e-2) con margen 1e-15.
- color_vela evalua el DOJI PRIMERO (antes daba rojo/verde a las de 1 tick).
- Leccion: el jefe define el umbral; el tick depende del precio del activo.

## Etapa 8 — Vela viva / close incompleto del stream (18:05)

- Sintoma del jefe: algunos activos no escaneaban bien; sospechaba la vela
  VIVA o la recien cerrada con datos incompletos.
- DIAG con log temporal: la vela viva NO entra al conteo (viva=False en los
  10 activos; el filtro por FROM ESPERADO la excluye SIEMPRE). PERO se
  encontro la causa real: el CLOSE del stream de la vela recien cerrada llega
  con ~1.2s de atraso (el ultimo tick del broker llega despues del :00). Con
  el doji de 1 tick, una vela que el broker cierra roja/verde puede verse
  DOJI en el stream (close casi-final) e INVALIDAR el conteo.
- Fix: SOLO cuando la ultima vela de la ventana es DOJI, se descarga la vela
  oficial del broker (get_ultima_vela, close FINAL) y se reemplaza. Descarga
  solo de los sospechosos (no satura el websocket). Log: 'vela final
  verificada por descarga: <color>'.
- Leccion: en el :00 el stream miente (close atrasado); la descarga del
  broker es la fuente oficial, pero solo para los casos dudosos.

## Etapa 9 — Fix del escaneo secuencial: el detonante MAS RECIENTE manda (18:55)

- Sintoma (queja del jefe): 6-7/10 activos en 'buscando' con el detonante
  unico A B B. El jefe: es IMPOSIBLE con 30 velas; solo la alternancia
  perfecta deberia dejar buscando.
- CAUSA RAIZ (encontrada en _recalcular): el escaneo era SECUENCIAL y se
  anclaba al PRIMER patron A B B de la ventana; una vez en conteo activo
  NUNCA volvia a buscar patrones nuevos. Si la ventana terminaba con un
  patron mas reciente del color opuesto (1 roja + 10 verdes al FINAL), las
  verdes invalidaban el conteo rojo viejo (2 contrarias seguidas) y el scan
  quedaba en 'buscando' aunque el detonante R V V estuviera ahi. Los 6-7 en
  buscando NO eran el mercado: era el escaneo perdiendo los detonantes
  recientes.
- FIX (re-ancla continua): el patron A B B se detecta en CADA posicion de la
  ventana (cola deslizante de 3 velas SIEMPRE, no solo al inicio ni tras
  invalidar). Si aparece un A B B del color OPUESTO al conteo activo, el
  conteo se RE-ANCLA al nuevo patron (el mas reciente manda). Si el A B B es
  del MISMO color, NO se re-ancla (seguir contando: 1 roja + 10 verdes ->
  verde 10 sin reinicios). Resultado: 'buscando' SOLO si no hay NINGUN A B B
  en la ventana (alternancia perfecta o puras del mismo color).
- CONSECUENCIA en las reglas: las 2 contrarias seguidas ya casi nunca
  invalidan (forman un A B B con la vela anterior y re-anclan al color
  nuevo); la invalidacion que sobrevive es 'contraria + 1 sola a favor +
  contraria' (A B A, alternancia V R V).
- VERIFICADO: test_conteo 21/21 (3 casos nuevos: V R R al inicio + 1 roja +
  10 verdes al final -> verde 10; alternancia perfecta -> buscando; patron
  del mismo color no resetea -> verde 6). En vivo: reporte MINUTO paso de
  'activos: 3-5/10' a 'activos: 7-9/10' (AUDNZD rojo 6/10, EURAUD verde 6/10,
  CHFJPY rojo 4/10, EURCHF rojo 4/10, CADCHF rojo 4/10, AUDUSD verde 2/10,
  EURCAD rojo 2/10, AUDCAD rojo 2/10, EURGBP verde 2/10).
- Leccion MAYOR: un escaneo secuencial que se ancla al primer detonante
  pierde los detonantes recientes -> falsos 'buscando'. La regla del jefe
  'buscar el patron en TODA la ventana' significa que el ULTIMO patron es
  el que cuenta.

## Lecciones transversales (principios que gobiernan este bot)

1. El reloj local NTP es la fuente de verdad del :00; todo desfase medido
   sobre websocket esta contaminado por RTT (timeSync con sesgo, recalibracion
   circular). No reintroducir maquinaria de desfase sin orden del jefe.
2. El stream local es la fuente primaria de velas (0 lock, 0 red en el tramo
   del :00); la descarga del broker es el respaldo y el verificador oficial
   SOLO para casos dudosos (doji al final de la ventana).
3. El close del stream llega tarde (~1.2s): nunca decidir invalidaciones con
   el color del stream en el :00; verificar por descarga los sospechosos.
4. Los patrones se buscan en TODA la ventana y el MAS RECIENTE manda. Un
   escaneo secuencial anclado al primer detonante produce falsos 'buscando'.
5. El motor es generico y NO conoce la estrategia: la logica nueva se hace
   con una estrategia nueva (o editando la existente), nunca reescribiendo
   bot.py sin necesidad real y documentada.
6. Reglas del jefe inquebrantables: entrada al :00 sobre vela CERRADA en hora
   del broker, UNA operativa a la vez, expiracion desde el 'from' exacto,
   doji estricto (1 tick o menos), minuto ciego tras ganada, ciclo de
   martingala ATADO al activo desde MG0, reporte minuto SIEMPRE con bloque
   de operacion del minuto.
7. En ciclo vela a vela el color de la vela NO importa: se opera con
   cualquier vela nueva (doji/contraria/a favor); la unica pregunta es gane
   o pierda. La regla del doji aplica solo al conteo antes de la MG0.
8. Verificar antes de entregar SIEMPRE: py_compile + tests sinteticos
   (test_conteo.py) + observacion en vivo de 2 ciclos reales + memoria
   actualizada. Nunca entregar sin probar.
9. La expiracion de la compra se calcula desde el 'from' EXACTO de la vela
   cerrada + 2*TF (buy_by_raw_expirations), nunca desde la hora local.

## Estado actual (29/08/2026 18:55+)

- Motor v5: desfase 0 fijo, margen 0.25s, corte ampliado del bucle,
  verificacion del maxdict al suscribir + reparador de streams (cooldown 30s).
- Estrategia: detonante unico A B B con RE-ANCLA CONTINUA (el ultimo patron
  manda); doji = contraria (1 tick o menos); verificacion del doji por
  descarga; modo critico a 1 vela; martingala vela a vela atada al activo.
- Tests: test_conteo.py 21/21. Bot corriendo en CMD visible (PID 5856 desde
  18:49). Reportes: 7-9/10 activos con conteo (antes 3-5/10).
- Pendientes conocidos del jefe: NINGUNO abierto. El respaldo sigue
  CONGELADO hasta aviso.

## Como continuar (guia para la proxima sesion)

- Si el jefe reporta 'buscando' alto otra vez: PRIMERO mirar el log
  (MINUTO activos: N/10) y la corrida real; NO tocar la estrategia a ciegas.
  Si hace falta, DIAG con el bot DETENIDO (diag_completo.py en Temp/opencode)
  para ver las ultimas velas reales y que calcula la estrategia.
- Si el jefe pide una logica NUEVA: copiar estrategia_vacia.py, implementar
  el contrato de estrategia_base.py, tests sinteticos con la ventana
  acumulada (nunca vela por vela), py_compile, reiniciar, documentar.
- Recordar siempre: el respaldo esta congelado; los cambios van SOLO a la
  carpeta en vivo; los montos se prueban en PRACTICE y a REAL solo con
  orden del jefe.
- El conocimiento del bot vive en: memoria_jarvis.md (estado y decisiones),
  este skill (el por que de cada decision) y los archivos del bot (el como).

# SESION NUBE 30-31/08/2026 — BOT-SATURACIONES-V2-ESTABLE (Railway)

## El bot de la nube (LA VERSION QUE CORRE AHORA MISMO)

- Carpeta: `C:\GAMES\BOT-SATURACIONES-V2-ESTABLE\` (copia de la version
  estable 23H del 29/08 + todos los cambios de esta sesion).
- Repo GitHub: `wascar2416-star/BOT-SATURACIONES-V2-ESTABLE` (privado).
  CADA PUSH DESPLIEGA SOLO en Railway. El repo del Desktop
  (BOT-SATURACIONES-V2) sigue siendo el repo del bot local (sin la nube).
- Railway: proyecto `bot-estadistico`, servicio `BOT DE SATURACIONES`,
  fuente = repo ESTABLE, REGION EU West (europe-west4, Amsterdam) — la
  unica region europea, cerca del broker (RTT ~10-30ms vs ~150ms desde
  sfo). CLI: `C:\Users\wasc4\AppData\Roaming\npm\railway.cmd`
  (los comandos: `railway status/list/logs/service status --service "BOT
  DE SATURACIONES"`, `service scale --service "..." eu-west=1 sfo=0`).
- Cuenta: WASCARFLOW3 (wascarflow3@gmail.com), PRACTICE, Telegram de Flow 3.
  Variables en Railway (IQ_EMAIL, IQ_PASSWORD, TELEGRAM_TOKEN,
  TELEGRAM_CHAT_ID). NUNCA doble instancia con la misma cuenta.
- Respaldos en `C:\Users\wasc4\Desktop\respaldos de bots\`:
  el MAS RECIENTE es BOT-SATURACIONES-V2-ESTABLE-RESPALDO-2026-08-30-2120
  (hilos siempre vivos, antes del vigilante por activo y de los reportes).
  El jefe pide respaldo ANTES de cada tanda de cambios; hay varios
  respaldos con timestamp por si hay que revertir (se usa git reset
  --hard + push --force cuando manda revertir).

## Arquitectura actual (30-31/08/2026, decisiones del jefe)

1. DESFASE = 0.0 FIJO (el jefe probo el desfase medido con timeSync en la
   nube y lo REVIRTIO: se quedo 0.0; el contenedor va ~50-300ms adelantado
   pero el jefe lo acepto asi).
2. HILOS SIEMPRE VIVOS (cambio grande): los 10 hilos corren SIEMPRE; NO se
   duermen ni se desuscriben durante ciclos de martingala ni modos
   criticos. `_pausar_streams_ajenos` y `_reanudar_streams_ajenos` son
   INERTES (pass, compatibilidad). Las senales ajenas se omiten (una
   operativa a la vez) pero los hilos siguen contando y alimentando su
   cache. Entrada al :00 intacta (lectura local).
3. VIGILANTE POR ACTIVO (`_hilo_vigilante_feed`): chequea cada 30s; si un
   activo no recibe velas en 120s (2 min) re-suscribe SOLO ese stream
   (los apagados por Telegram se excluyen); si TODOS estan congelados ->
   re-suscripcion completa; si el feed global no avanza en 5 min ->
   reinicio (os._exit(1), Railway lo levanta).
4. CACHE de 31 velas por activo (`cache_velas.py` + `cache_velas.json`
   ignorado en git): velas + estado de la maquina (color, conteo,
   interrupciones, desde_contraria, esperando_contraria, id_detonante,
   ultimo_ts, ciclo, esperando_detonante_nuevo, from_invalidacion).
   Validez 10 min. Se guarda en cada ciclo (alimentar/validar).
5. DETONANTE PRIMARIO: `_id_detonante` = from de la vela donde se anclo el
   conteo; al reconstruir se ancla EXACTAMENTE ahi si esta en la ventana.
   `_recalcular` hace replay desde el PRIMER A B B con continuacion
   (si invalida, sigue con el siguiente A B B valido).
6. Reconstruccion con cache: si hay estado -> restaura + puesta al dia con
   velas nuevas; si no -> reset + replay primario.

## Reglas de la estrategia (la logica del jefe, TODAS verificadas en test_conteo.py)

- DETONANTE: patron A B B (1 vela de un color + 2 consecutivas del opuesto;
  espejo incluido). En buscando, el replay arranca en el PRIMER A B B.
- IDENTIDAD del conteo: con conteo activo, un patron A B B repetido del
  MISMO color NO reinicia (suma; ej: verde 5 + R + V V = verde 7).
- ESPEJO: 2 contrarias SEGUIDAS transfieren la identidad al color opuesto
  (conteo 2 con las 2 del espejo).
- INVALIDACION VIGENTE: contraria + 1 sola a favor + contraria (R V R)
  INVALIDA el conteo. Tras invalidar, el bot espera un detonante NUEVO:
  `_esperando_detonante_nuevo` + `_from_invalidacion` (el recalculo solo
  considera velas posteriores a la que invalido; las viejas NO re-anclan:
  antes la saturacion 'resucitaba' y el jefe lo detecto).
- DOJI como INTERRUPCION (doji estricto: open == close EXACTO):
  aislado (2+ a favor detras) tolera; con 0-1 a favor entre medio o
  2 dojis consecutivos INVALIDA. No participa en el detonante.
- MAX INTERRUPCIONES (parametro Telegram `max_interrupciones`, 0 =
  desactivado): al llegar al limite, DESCARTE + RE-ANCLA al ULTIMO
  detonante (`_reanclar_ultimo_detonante`) y arranca desde ahi.
- CICLO TRAS GANAR: al ganar, re-ancla al ultimo detonante (velas del
  cache) y arranca el conteo desde ahi (verde 8 -> verde 3 verificado).
- MODO CRITICO: 2 contrarias seguidas = espejo (transfiere, libera
  candidatura); los demas hilos siguen contando.

## Reportes Telegram (formatos aprobados)

- Arbol UNICO (30/08/2026, regla del jefe): el mensaje de operacion abre
  con el bloque del activo; bajo 'SATURACIÓN COMPLETADA ❗' baja la
  vertical SOLA ('  │') y las ramas de la OPERACION van al MISMO nivel
  del bloque ('  ├ Operación: ...'), misma columna — _indentar_bajo_arbol
  (sin sub-indentacion).
- 'Conteo: ( N / M )' con parentesis; 'SATURACIÓN COMPLETADA ❗' (en vez
  de LISTO PARA ENTRADA); SIN linea '➡️ PRÓXIMO PASO'; 'Próximo monto:
  💰 $X' (emoji despues de los dos puntos); panel: 'Saturación de velas:
  N'. Botones de parametros SOLO numeros (el texto con etiqueta impedía
  aplicar el valor: el handler lo tomaba como abrir el selector).

## Como mostrar los mensajes al jefe (REGLA OBLIGATORIA, 30/08/2026)

Cuando el jefe pida 'cómo se ven los mensajes/logs', 'muéstrame el
formato', 'enséñame los mensajes' o cualquier variante, enviarlos SIEMPRE
en RECUADROS de codigo (bloques ```), con el formato EXACTO de Telegram
(texto plano: rayas '=', arbol con '├ └ │', emojis, envoltura a 34
columnas), tal cual los genera el codigo REAL (telegram_reporte.py con
bloque_activo y indicadores como los arma bot.py). NUNCA a mano, NUNCA en
texto plano suelto sin recuadro. Formato aprobado por el jefe (ejemplo
OPERACIÓN GANADA):

✅ OPERACIÓN GANADA 🟢
===============================

🔹 EURAUD-OTC 🔥
  ├ SATURACION VERDE 🟢:
  │ Conteo: ( 10 / 10 )
  ├ Interrupciones: 0
  ├ SATURACIÓN COMPLETADA ❗
  │
  ├ Operación: 📉 PUT
  ├ Nivel alcanzado: MG 0
  ├ Ganancia neta: +$1.00
  └ Racha reseteada. Escaneando...

===============================
💵 PROFIT: $3.24

Los 5 mensajes de operacion (ejecutada, rechazada, ganada, empate,
perdida con sus 2 variantes) llevan este mismo arbol unico. Para
generarlos con datos de ejemplo se puede ejecutar
telegram_reporte.py + estrategia_saturacion_v2 (EstrategiaActivo con
conteo 10/10, estado 'listo') y pegar la salida en los recuadros.

## Revertido / descartado en esta sesion (NO reintroducir sin orden)

- Fixes del GIRO DE VELA (color oficial al operar + correccion diferida +
  buffer _ultimas_velas): el jefe los mando REVERTIR (git reset a
  cbdf4f8 + push --force). El codigo actual NO tiene _ultimas_velas ni
  corregir_vela_oficial.
- Desfase medido por timeSync (flag medir_desfase): revertido, 0.0 fijo.
- Fixes de frescura del repo del Desktop (sello por edad + expiracion con
  from oficial + validacion con vela fresca): quedaron en el repo del
  DESKTOP (BOT-SATURACIONES-V2, repo wascar2416-star/BOT-SATURACIONES-V2),
  NO en la ESTABLE.

## Estado actual

- Commit: 1968213 (ultimo push; Railway desplego solo, deployment
  7dddca1c SUCCESS). Bot corriendo en la nube con los 10 hilos vivos,
  conteos normales, sin errores.
- Tests: test_conteo.py TODOS OK (23 D3 + identidad + doji + cache +
  max + re-anclaje + invalidacion vigente + ciclo tras ganar + formatos).
- Herramientas utiles: `railway logs` para diagnosticar; smoke tests en
  C:\Users\wasc4\AppData\Local\Temp\opencode\; respaldos por timestamp en
  respaldos de bots.

## Prompt de arranque para el proximo chat (darselo al agente nuevo)

"Soy Wascar, el jefe. Eres TRADING, maestro de bots de IQ Option. El bot
ACTUAL es BOT-SATURACIONES-V2-ESTABLE en C:\GAMES\BOT-SATURACIONES-V2-ESTABLE\
(repo GitHub wascar2416-star/BOT-SATURACIONES-V2-ESTABLE; cada push
despliega solo en Railway, servicio 'BOT DE SATURACIONES', proyecto
bot-estadistico, region EU West Amsterdam; CLI en
C:\Users\wasc4\AppData\Roaming\npm\railway.cmd). Cuenta WASCARFLOW3
PRACTICE, Telegram Flow 3. Lee TODO el skill de trading (la seccion
'SESION NUBE 30-31/08/2026') y la carpeta del bot antes de tocar nada:
la estrategia vive en estrategia_saturacion_v2.py (identidad del conteo,
espejo, invalidacion R V R vigente que espera detonante nuevo, doji como
interrupcion, max interrupciones con re-ancla al ultimo detonante, ciclo
tras ganar, cache de 31 velas con detonante primario), los hilos son
SIEMPRE VIVOS (no se duermen ni desuscriben), el vigilante por activo
re-suscribe el hilo zombie a los 2 min, y el desfase es 0.0 fijo.
Respalda en 'respaldos de bots' antes de cada tanda de cambios, verifica
con py_compile + test_conteo.py + smoke, y haz push a la ESTABLE. NO
  reintroducir los fixes revertidos (giro de vela, desfase medido).
  Cuando el jefe pida ver los mensajes/logs del bot, enviarlos SIEMPRE en
  recuadros de codigo con el formato EXACTO de Telegram (ver la regla
  'Como mostrar los mensajes al jefe' en este mismo skill)."

## Plantilla alineada al ESTABLE (31/08/2026, regla del jefe)

- PLANTILLA: `C:\Users\wasc4\Desktop\PLANTILLA-IQ-OPTION-MOTOR-V2\` (repo
  wascar2416-star/PLANTILLA-IQ-OPTION, rama master). Es la base para crear
  bots nuevos: copiar la carpeta + crear estrategia_<nombre>.py.
- 31/08/2026: se copiaron del BOT ESTABLE los archivos del motor
  (bot.py, telegram_reporte.py, velas.py, operativa.py, cache_velas.py) +
  config.json con margen_cierre_seg 0.28. Commit 13bef85.
- La plantilla incluye TODO lo del ESTABLE a esa fecha: arbol unico en
  mensajes, defensa autonoma del monto auto (umbral = perdida exacta del
  ciclo), margen 280ms, DOS VELOCIDADES en el :00 (push real para conteos
  + muestreo directo del critico), calibracion del cruce (timeSync
  mediana + clamp), vigilante por activo, cache_velas, doji de precision.
- El motor es GENERICO (factory por config 'estrategia'); la plantilla usa
  'estrategia': 'vacia' (molde). Para el modo critico, la estrategia nueva
  debe implementar es_candidato() True + validar_vela_critica(vela).
- Respaldo de la plantilla: respaldos de bots\
  PLANTILLA-IQ-OPTION-MOTOR-V2-RESPALDO-2026-08-31-2348.
