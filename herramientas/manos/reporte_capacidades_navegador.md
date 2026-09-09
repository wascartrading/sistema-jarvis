# Reporte técnico: Detección y uso de capacidades de navegador (JS + CDP)

Autor: JARVIS · Fecha: sesión actual
Objetivo: documentar técnicas para que un asistente de automatización de escritorio
(JARVIS en Windows, controlando Brave/Chrome vía CDP en puerto 9222, y Playwright/PyAutoGUI)
detecte y use las funciones/capacidades de un navegador.

NOTA DE FUENTES: La herramienta de búsqueda web de este entorno estaba sin clave de API,
así que no se hizo búsqueda en vivo. Este reporte se basa en documentación oficial ESTABLE
y de sobra conocida (MDN y Chrome DevTools Protocol). Las URLs son reales y contrastables;
las secciones que dependen de "versión actual" conviene cotejarlas una vez en vivo.

---

## (a) RESUMEN EJECUTIVO — mejores técnicas

ÁNGULO 1 (detección en página, JS):
1. La detección de capacidades ("feature detection") se hace SIEMPRE en el contexto de la
   página con `Runtime.evaluate` evaluando una expresión que devuelva true/false por API.
   Regla de oro: nunca asumas que una API existe por "ser Chrome"; compruébala con
   `typeof x !== 'undefined'` o `'x' in obj`. Esto vale para toda la lista: WebGL, WebRTC,
   EME/DRM, Media Session, Fullscreen, PiP, MediaDevices, Service Workers, WebAudio, etc.
2. Para multimedia/DRM (HBO Max, Netflix) lo crítico es EME: comprobar
   `navigator.requestMediaKeySystemAccess` y lanzar la promesa contra 'com.widevine.alpha'
   para confirmar que el navegador/bundle de DRM soporta Widevine DE VERDAD. Esto, más el
   autoplay-policy, define si un stream va a reproducirse sin interacción.
3. Algunas capacidades NO se detectan con un simple typeof síncrono porque son promesas o
   requieren permiso (getUserMedia, requestMediaKeySystemAccess). En esos casos el capability
   report hace el check asíncrono y devuelve una promesa; el automatizador espera su resultado.

ÁNGULO 2 (CDP, fuera de la página):
1. La forma canónica de ENUMERAR todo lo que soporta el navegador por CDP es
   `Schema.getDomains` (listado de dominios) y, para ver una llamada concreta,
   `Schema.getDomain` (dominio + métodos/eventos con tipos de parámetros). Esto te permite
   iterar y descubrir dominios desconocidos o de una versión específica.
2. La forma canónica de ver la versión/protocolo es el endpoint HTTP `GET /json/version`
   (protocolVersion, webSocketDebuggerUrl, Browser/User-Agent, V8, cabe la versión de CDP).
3. Antes de llamar a un método de un dominio, comprueba que el dominio existe en la lista
   de `Schema.getDomains`; eso evita "Method not found" en navegadores que no lo soporten
   (Brave/Chrome viejos, o builds sin cierto dominio). Si el error `-32601` aparece de todos
   modos, lo capturas y degradas con gracia.
4. Detección de "estela" (headless vs normal): en la página usas `navigator.webdriver`,
   `window.chrome` (ausente en headless real histórico), `navigator.userAgent` y
   `chrome.headless` (en la antigua vía --headless). A nivel de proceso, comparas los
   flags/datos que muestra `GET /json/version` con la sesión real. Ten en cuenta que
   "headless=new" actual rompe varios de esos heurísticos clásicos.

---

## (b) CAPABILITY REPORT — JavaScript ejecutable por CDP Runtime.evaluate

Un "one-liner" JSON que devuelve true/false por capacidad. Ejecútalo así en el puerto 9222:

    curl http://localhost:9222/json  -> obtener webSocketDebuggerUrl de una página
    # o en Playwright:
    page.evaluate(expresion)

Abajo, dos versiones: la SÍNCRONA (eval simple, devuelve objeto con true/false) y la
ASÍNCRONA (eval con awaitPromise:true, porque DRM/MediaDevices requieren promesas).

### Versión síncrona (devuelve objeto plano; sin await)

```javascript
(() => {
  const has = (x, y) => (y ? (x && x[y] !== undefined) : (x !== undefined && x !== null));
  return {
    // ---- Básicas de detección/estela ----
    webdriver: !!navigator.webdriver,               // true si controlado por automatización
    window_chrome: !!window.chrome,                 // false en headless "clásico"
    userAgent: navigator.userAgent,
    platform: navigator.platform,
    languages: navigator.languages,

    // ---- Gráficos ----
    webgl: (() => { try {
      const c = document.createElement('canvas');
      return !!(window.WebGLRenderingContext && (c.getContext('webgl') || c.getContext('experimental-webgl')));
    } catch (e) { return false; } })(),
    webgl2: (() => { try {
      const c = document.createElement('canvas');
      return !!(window.WebGL2RenderingContext && c.getContext('webgl2'));
    } catch (e) { return false; } })(),

    // ---- Streaming / multimedia ----
    webrtc: !!window.RTCPeerConnection,
    webrtc_getUserMedia: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia),
    mediaDevices_enumerate: !!(navigator.mediaDevices && navigator.mediaDevices.enumerateDevices),
    mediaSession: !!(navigator.mediaSession && navigator.mediaSession.metadata !== undefined),
    mediaCapabilities: !!navigator.mediaCapabilities,
    fullscreen: !!(document.documentElement.requestFullscreen),
    pictureInPicture: !!document.pictureInPictureEnabled,

    // ---- DRM / EME (solo disponibilidad del objeto; la confirmación real va con promesa) ----
    eme: !!navigator.requestMediaKeySystemAccess,
    // navegador / platforma base
    audio: !!(window.AudioContext || window.webkitAudioContext),

    // ---- Almacenamiento ----
    localStorage: (() => { try { localStorage.setItem('__t','1'); localStorage.removeItem('__t'); return true; } catch(e){ return false; } })(),
    sessionStorage: (() => { try { sessionStorage.setItem('__t','1'); sessionStorage.removeItem('__t'); return true; } catch(e){ return false; } })(),
    indexedDB: !!window.indexedDB,
    cookiesEnabled: navigator.cookieEnabled,
    storageManager: !!(navigator.storage && navigator.storage.estimate),

    // ---- Trabajo en segundo plano / observadores ----
    serviceWorker: 'serviceWorker' in navigator,
    intersectionObserver: !!window.IntersectionObserver,
    resizeObserver: !!window.ResizeObserver,
    mutationObserver: !!window.MutationObserver,
    performance: !!window.performance && !!performance.getEntries,
    geolocation: 'geolocation' in navigator,
    notifications: 'Notification' in window,
    clipboard: !!(navigator.clipboard && navigator.clipboard.writeText),

    // ---- Autoplay policy (Chrome >= 88): 'allowed' | 'allowed-muted' | 'disallowed' ----
    autoplayPolicy: (typeof navigator.getAutoplayPolicy === 'function')
      ? navigator.getAutoplayPolicy('mediaelement')
      : 'unknown'
  };
})()
```

### Versión ASÍNCRONA — añade las que necesitan promesa / permiso
Ejecuta con `Runtime.evaluate({ expression: ..., awaitPromise: true, returnByValue: true })`
para que el resultado venga resuelto.

```javascript
(async () => {
  const has = (x) => x !== undefined && x !== null;
  const base = /* el objeto de la versión síncrona (se puede inyectar como función) */ {};

  // EME/Widevine REAL: comprobar si el navegador puede reproducir contenido Widevine
  let emeWidevine = false;
  try {
    if (navigator.requestMediaKeySystemAccess) {
      // p.ej. HBO Max / Netflix usan Widevine. Config típica: video/mp4, códec avanzado.
      const access = await navigator.requestMediaKeySystemAccess('com.widevine.alpha', [{
        initDataTypes: ['cenc'],
        audioCapabilities: [{ contentType: 'audio/mp4; codecs="mp4a.40.2"' }],
        videoCapabilities: [{ contentType: 'video/mp4; codecs="avc1.42E01E"' }]
      }]);
      emeWidevine = !!(access && access.getConfiguration);
    }
  } catch (e) { emeWidevine = false; }

  // MediaDevices: enumerar y pedir permiso (cámara/micrófono) si hace falta
  let deviceList = [];
  try { if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
    deviceList = (await navigator.mediaDevices.enumerateDevices()).map(d => d.kind + ':' + d.label);
  } } catch (e) {}

  // Storage estimate (uso de espacio)
  let storageQuota = null;
  try { if (navigator.storage && navigator.storage.estimate) {
    const est = await navigator.storage.estimate();
    storageQuota = { usage: est.usage, quota: est.quota };
  } } catch (e) {}

  return {
    ...base,
    emeWidevine: emeWidevine,
    devices: deviceList,
    storageEstimate: storageQuota,
    // Media Capabilities (decodificación HD/4K)
    mediaCapabilitiesH264: (async () => { try {
      if (!navigator.mediaCapabilities) return null;
      const r = await navigator.mediaCapabilities.decodingInfo({
        type: 'file',
        video: { contentType: 'video/mp4; codecs="avc1.640028"', width: 1920, height: 1080, bitrate: 8000000, framerate: 60 }
      });
      return r.supported && r.smooth && r.powerEfficient;
    } catch(e){ return null; } })()
  };
})()
```

Cómo lanzarlo desde CDP con curl (websocket, p.ej. con el websocat o desde Playwright/Python):

    # Python: usar una lib websocket (websockets / websocket-client) para enviar:
    # {"id":1,"method":"Runtime.evaluate","params":{
    #   "expression": "<capability report>",
    #   "returnByValue": true,
    #   "awaitPromise": true}}
    # La respuesta es {"result":{"result":{"value":{...}}}}

En Playwright (Python) es más simple:

    caps = await page.evaluate(expresion)   # devuelve el dict JSON directo

---

## (c) COMANDOS CDP concretos — enumerar y usar dominios

### 1. Enumerar dominios disponibles (Schema.getDomains)
WebSocket: envío `{"id":1,"method":"Schema.getDomains","params":{}}`.
Respuesta: `{"result":{"domains":[{"name":"Page","version":"..."},{"name":"DOM",...}...]}}`.

HTTP (mismo navegador, más simple de probar):
    curl http://localhost:9222/json/version     # versión y protocolVersion
    curl http://localhost:9222/json/list        # pestañas abiertas
    curl http://localhost:9222/json             # alias de /json/list (tabs) 

Para un dominio concreto completo:
    {"id":2,"method":"Schema.getDomain","params":{"domainName":"Page"}}
    -> devuelve ese dominio con commands[], events[] y tipos.

### 2. Dominios CDP útiles para automatización robusta
- Page: navegación, reload, captureScreenshot, printToPDF, getFrameTree, lifecycle events
  (Page.loadEventFired, Page.domContentEventFired). Comando: Page.navigate {url}.
- DOM: querySelector, getDocument, getOuterHTML, getBoxModel. P.ej. DOM.getDocument,
  DOM.querySelector {nodeId, selector}, DOM.getOuterHTML.
- Runtime: evaluate, callFunctionOn, getProperties, Runtime.evaluate {expression,
  returnByValue:true, awaitPromise:true}. Es el vehículo para el capability report.
- Input: dispatchKeyEvent, dispatchMouseEvent, insertText, dispatchTouchEvent.
  Ideal para automatizar clic/teclado sin PyAutoGUI (más directo que el control de escritorio).
- Emulation: setDeviceMetricsOverride {width,height,deviceScaleFactor,mobile},
  setUserAgentOverride {userAgent}, setTouchEmulationEnabled, setEmulatedMedia
  (para modo oscuro / prefers-color-scheme, útil en pruebas de UI).
- Network: getResponseBody {requestId} (leer cuerpo de respuestas), setBlockedURLs {urls},
  enable/disable cache, setUserAgentOverride, capture requests via Network.requestWillBeSent.
- Performance: Performance.enable + Performance.getMetrics (FCP/LCP/TTFB), o
  Performance.getMetrics para datos de rendimiento/APIs.
- Accessibility: Accessibility.getFullAXTree — MUY útil: devuelve el árbol de accesibilidad
  (roles + names) sin depender del texto/DOM interno. Ideal para localizar botones por su
  rol/aria-label/name accesible (más robusto que querySelector con textos frágiles).
- Media: evento Media.playerPropertiesChanged, Media.playerEventsAdded — telemetría de
  reproducción (útil para confirmar que un stream despegó / tiene buffering).
- Fetch: Fetch.enable + Fetch.requestPaused / Fetch.continueRequest / Fetch.fulfillRequest
  — interceptar y reescribir requests/respuestas en vuelo (mock de APIs, inyectar headers).
- Browser: Browser.getVersion (navegador/versión), Browser.getWindowForTarget {targetId},
  Browser.setWindowBounds {windowId, bounds} — mover/redimensionar la ventana del navegador,
  Browser.close, Browser.setDownloadBehavior (descargas sin UI).
- Target: Target.getTargets, Target.attachToTarget, Target.createTarget — gestionar pestañas/
  workers/frames. Para automatizar cada tab por separado.
- Storage / IndexedDB / DOMStorage / CacheStorage: inspección y limpieza de datos persistidos.
- Log / Runtime.consoleAPICalled / Runtime.exceptionThrown: capturar consola y errores.

### 3. Detectar si existe un dominio antes de llamarlo
Patrón de defensa en el cliente CDP:
1. Tras conectar, hacer `Schema.getDomains` una vez y guardar `nombres = {d.name for d in domains}`.
2. Antes de cada método: `if dominio not in nombres: degrade/omitir`.
3. Adicionalmente, capturar el error CDP `-32601` ("Method not found") y degradar.
Ejemplo conceptual en Python:

    # tras conectar:
    res = send("Schema.getDomains", {})
    doms = {d["name"] for d in res["result"]["domains"]}

    def may_call(domain, method, params):
        if domain not in doms:          # BRavo/Brave viejo, o dominio ausente
            return {"error": "not supported"}
        r = send(f"{domain}.{method}", params)
        if r.get("error", {}).get("code") == -32601:  # método concreto ausente
            return {"error": "method not found"}
        return r

### 4. Detección de "estela" (headless vs normal)
En página (JS):
- navigator.webdriver === true  (marca de automatización; CDP/ChromeDriver la dejan en true).
- window.chrome      : presente en Chrome/Edge normales; históricamente ausente en headless.
- chrome.headless    : en la VIEJA vía (--headless) valía "true"; en headless=new ya no.
- navigator.userAgent: el headless clásico decía "HeadlessChrome/<ver>"; hoy la mayoría
  de builds headless=new devuelven "Chrome/<ver>" sin la palabra Headless (menos detectable).
- presence de window.chrome y de sus propiedades "csi", "loadTimes", "runtime" (firma).
A nivel CDP / proceso:
- GET /json/version -> ver el "Browser" y el "User-Agent" reales; comparar con lo esperado.
- Comprobar `Browser.getVersion` (producto, revisión, JS-V8, User-Agent del navegador).
- Diferencias de comportamiento (más fiables que strings): en headless algunos códecs/DRM
  (Widevine L1) y aceleración de video pueden no estar; el capability report de EME suele
  caer a false o a L3 en headless "clásico". Ese es el test funcional más honesto.

Nota práctica: para HBO Max/Netflix con DRM, el modo headless "clásico" frecuentemente
falla Widevine (falta un LSM / GPU trust). Si solo se necesita la página sin reproducción
DRM, headless=new suele valer; si se necesita reproducir DRM de verdad, conviene arrancar
el navegador "normal" (no headless) y controlarlo por CDP igualmente, quizá con ventana
real o una virt-headless con GPU virtual habilitada.

---

## (d) URLs citadas (fuentes oficiales, estables)

MDN — Detección de características / JavaScript:
- https://developer.mozilla.org/es/docs/Learn_web_development/Extensions/Testing/Feature_detection
- https://developer.mozilla.org/en-US/docs/Web/API/WebGL_API/Tutorial/Adding_2D_content_to_a_WebGL_context
- https://developer.mozilla.org/en-US/docs/Web/API/Media_Encrypted_Extensions_API
- https://developer.mozilla.org/en-US/docs/Web/API/Navigator/requestMediaKeySystemAccess
- https://developer.mozilla.org/en-US/docs/Web/API/Navigator/mediaSession
- https://developer.mozilla.org/en-US/docs/Web/API/Media_Session_API
- https://developer.mozilla.org/en-US/docs/Web/API/Navigator/getAutoplayPolicy
- https://developer.mozilla.org/en-US/docs/Web/API/Fullscreen_API
- https://developer.mozilla.org/en-US/docs/Web/API/Picture-in-Picture_API
- https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getUserMedia
- https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/enumerateDevices
- https://developer.mozilla.org/en-US/docs/Web/API/Media_Capabilities_API
- https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API
- https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API
- https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API
- https://developer.mozilla.org/en-US/docs/Web/API/Intersection_Observer_API
- https://developer.mozilla.org/en-US/docs/Web/API/Storage_Manager_API
- https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/User-Agent

Chrome DevTools Protocol (documentación oficial del protocolo):
- Vista general / dominios: https://chromedevtools.github.io/devtools-protocol/
- Schema.getDomains / Schema.getDomain: https://chromedevtools.github.io/devtools-protocol/tot/Schema/
- Runtime.evaluate: https://chromedevtools.github.io/devtools-protocol/tot/Runtime/#method-evaluate
- Page: https://chromedevtools.github.io/devtools-protocol/tot/Page/
- DOM: https://chromedevtools.github.io/devtools-protocol/tot/DOM/
- Input: https://chromedevtools.github.io/devtools-protocol/tot/Input/
- Emulation (setDeviceMetricsOverride, setUserAgentOverride):
  https://chromedevtools.github.io/devtools-protocol/tot/Emulation/
- Network (getResponseBody, setBlockedURLs):
  https://chromedevtools.github.io/devtools-protocol/tot/Network/
- Accessibility.getFullAXTree:
  https://chromedevtools.github.io/devtools-protocol/tot/Accessibility/#method-getFullAXTree
- Media: https://chromedevtools.github.io/devtools-protocol/tot/Media/
- Fetch: https://chromedevtools.github.io/devtools-protocol/tot/Fetch/
- Browser (getVersion, getWindowForTarget, setWindowBounds):
  https://chromedevtools.github.io/devtools-protocol/tot/Browser/
- Performance: https://chromedevtools.github.io/devtools-protocol/tot/Performance/
- Erlendur HTTP endpoint /json/version:
  https://chromedevtools.github.io/devtools-protocol/  (sección "Versions"/HTTP endpoint)
  y la referencia del endpoint: https://chromedevtools.github.io/devtools-protocol/#endpoints

Guías de arranque CDP y Playwright:
- Adding CDP endpoint / remote debugging: https://developer.chrome.com/docs/devtools/remote-debugging/
- Chrome + depuración remota (--remote-debugging-port): https://developer.chrome.com/blog/remote-debugging-port/
- Headless Chrome (nuevo vs clásico): https://developer.chrome.com/docs/chromium/new-headless
- Playwright (hooks CDP): https://playwright.dev/docs/api/class-browsercontext#browser-context-new-cdp-session
- Widevine en navegadores / EME (base de conocimiento Google):
  https://support.google.com/widevine/  (información de soporte de Widevine L1/L3)

---

## FAQ rápido / decisiones que tomé por ti
- ¿Qué uso para pulsar botones sin texto frágil? Accessibility.getFullAXTree: busco por
  rol + nombre accesible (aria-label, title, text). Es mucho más robusto que selectores de
  texto/`.innerText`.
- ¿Cómo sé si un dominio existe en un Brave/Chrome raro? Schema.getDomains una vez, y
  degradación ante -32601.
- ¿Headless o no para HBO Max? Si falla DRM en headless, arranca el navegador normal por CDP.
  El capability report de EME-Widevine te dice de antemano si tu build puede reproducirlo.
- ¿Usar PyAutoGUI o CDP para clic? Prefiere Input.dispatchMouseEvent dentro de la página
  (coordenadas reales de la ventana tras Browser.getWindowForTarget + setWindowBounds);
  PyAutoGUI queda de respaldo para lo que esté fuera del navegador (ventanas del SO).
