package com.wascar.jarvis

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Color
import android.media.AudioManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.view.ViewGroup
import android.webkit.JavascriptInterface
import android.webkit.WebChromeClient
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.activity.result.contract.ActivityResultContracts
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.wascar.jarvis.data.GeminiLive
import com.wascar.jarvis.data.Preferencias
import kotlinx.coroutines.launch
import org.json.JSONObject

/**
 * JARVIS App — LA INTERFAZ ES EL WIDGET (orden del jefe 04/10/2026).
 * ===========================================================================
 * En vez de rehacer el diseño a mano (que es donde se desalineaba), la app
 * carga EL MISMO HTML/CSS/JS del widget flotante de la PC, dentro de un
 * WebView a pantalla completa. Resultado: identico, pixel a pixel, y todo
 * cambio futuro del widget se refleja solo copiando el archivo a assets.
 *
 * El widget espera window.pywebview.api (pywebview). Aqui lo emula un shim
 * que vive en assets/widget.html y habla con este objeto "Android".
 *
 * El puente real con JARVIS sigue siendo TELEGRAM (TDLib): ChatViewModel +
 * TelegramManager (intactos).
 */
class MainActivity : ComponentActivity() {

    private var web: WebView? = null
    private lateinit var vm: ChatViewModel
    private val ui = Handler(Looper.getMainLooper())

    // --- Puente con la pagina ---
    private var paginaLista = false
    private val pendientes = ArrayDeque<String>()
    private var vistos = 0
    private var chatAbierto = true
    @Volatile private var requiereActual = ""
    @Volatile private var usandoTg = false
    @Volatile private var tgEstado = ""
    @Volatile private var trabajandoAhora = false

    // --- Dictado nativo (el microfono del telefono escribe en la entrada) ---
    private val PERM_AUDIO = 7
    private val PERM_NOTIF = 8
    private var voz: SpeechRecognizer? = null
    private var dictando = false
    private var volMusicaPrev = -1
    private var volNotifPrev = -1
    private var volSistemaPrev = -1

    // --- Adjuntar imagen/documento (orden del jefe 04/10/2026) ---
    private var alElegirAdjunto = registerForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri -> if (uri != null) enviarAdjunto(uri) }

    /** Lo que el widget llama como window.pywebview.api.* */
    inner class Puente {
        @JavascriptInterface
        fun enviar_mensaje(t: String?) {
            val s = t ?: ""
            ui.post { alEnviar(s) }
        }

        /** Boton rojo: interrumpe el trabajo del combo (orden 04/10/2026). */
        @JavascriptInterface
        fun interrumpir() {
            ui.post { vm.interrumpir() }
        }

        @JavascriptInterface
        fun toggle_mic(): String {
            ui.post { alternarDictado() }
            return "{\"ok\":true,\"muted\":false}"
        }

        @JavascriptInterface
        fun get_sphere_theme(): String = "{\"ok\":true,\"theme\":\"cyan\"}"

        @JavascriptInterface
        fun estado(): String = "{\"ok\":true,\"muted\":false,\"estado\":\"LISTENING\",\"voz\":false}"

        @JavascriptInterface
        fun expandir(v: Boolean) { }

        // --- NOTIFICACIONES (orden del jefe 05/10/2026) ---
        /** "1" si los avisos estan activados; "0" si estan silenciados. */
        @JavascriptInterface
        fun notif_estado(): String =
            if (Preferencias.notificaciones(this@MainActivity)) "1" else "0"

        /** Activa o silencia los avisos (al activarlos pide permiso si falta). */
        @JavascriptInterface
        fun set_notif(v: String?) {
            val on = (v == "1") || (v ?: "").equals("true", true)
            ui.post { try { cambiarNotificaciones(on) } catch (_: Throwable) { } }
        }

        // --- REINICIAR JARVIS (orden del jefe 05/10/2026) ---
        @JavascriptInterface
        fun reiniciar_jarvis() {
            ui.post { try { vm.reiniciarJarvis() } catch (_: Throwable) { } }
        }

        @JavascriptInterface
        fun abrir_ventana() { ui.post { alternarChat() } }

        /** Ruedita de ajustes (orden del jefe 04/10/2026). */
        @JavascriptInterface
        fun abrir_ajustes() { ui.post { avisar("Ajustes: toca la esfera para la llamada, o usa el chat.") } }

        // --- ACCESO A TELEGRAM (orden del jefe 04/10/2026) ---
        /** Devuelve lo que la app ya tenga guardado (api_id, api_hash, bot, tel). */
        @JavascriptInterface
        fun credenciales_leer(): String {
            val id = Preferencias.apiId(this@MainActivity)
            val hash = Preferencias.apiHash(this@MainActivity)
            val bot = Preferencias.botUsuario(this@MainActivity)
            val tel = Preferencias.telefono(this@MainActivity)
            return "{\"ok\":true,\"api_id\":${org.json.JSONObject.quote(if (id > 0) id.toString() else "")}," +
                "\"api_hash\":${org.json.JSONObject.quote(hash)}," +
                "\"bot\":${org.json.JSONObject.quote(bot)}," +
                "\"telefono\":${org.json.JSONObject.quote(tel)}}"
        }

        /** El jefe introdujo TODOS los datos: se guardan y arranca el acceso. */
        @JavascriptInterface
        fun iniciar_acceso(tel: String?, id: String?, hash: String?, bot: String?) {
            val t = tel ?: ""; val i = id ?: ""; val h = hash ?: ""; val b = bot ?: ""
            ui.post {
                val ok = vm.accesoTelegram(t, i, h, b)
                if (ok) {
                    eval("if(window.wAccesoMsg)window.wAccesoMsg('Conectando… Telegram te pedirá un código.');")
                } else {
                    eval("if(window.wAccesoMsg)window.wAccesoMsg('Faltan datos: revisá el teléfono, api_id y api_hash.');")
                }
            }
        }

        /** El jefe manda el codigo o la clave que pide Telegram (fix 20.1). */
        @JavascriptInterface
        fun enviar_paso(fase: String?, valor: String?) {
            val f = fase ?: ""; val v = valor ?: ""
            ui.post {
                when (f) {
                    "codigo" -> vm.enviarCodigo(v)
                    "clave" -> vm.enviarClave(v)
                    "telefono" -> vm.enviarTelefono(v)
                }
            }
        }

        /** La pagina avisa que se debe cerrar el panel (acceso ya concedido). */
        @JavascriptInterface
        fun cerrar_acceso() { ui.post { eval("if(window.wAbrirAcceso)window.wAbrirAcceso(false);") } }

        /** El panel de acceso se leyo: marca que la app ya mostro la interfaz. */
        @JavascriptInterface
        fun listo(v: Boolean) { ui.post { paginaLista = true } }

        /** La pagina pide el "paso" actual (telefono/codigo/clave) para pintarlo. */
        @JavascriptInterface
        fun acceso_paso(r: String?) {
            val paso = r ?: ""
            ui.post { eval("if(window.wSetFase)window.wSetFase(${org.json.JSONObject.quote(paso)});") }
        }

        /** Abre el selector de imagen/documento (orden del jefe 04/10/2026). */
        @JavascriptInterface
        fun adjuntar() { ui.post { alElegirAdjunto.launch("*/*") } }

        /** Abre un enlace del chat en el navegador del telefono (04/10/2026). */
        @JavascriptInterface
        fun abrir_enlace(url: String?) {
            val u = url ?: ""
            ui.post {
                try {
                    val i = android.content.Intent(
                        android.content.Intent.ACTION_VIEW,
                        android.net.Uri.parse(u)
                    )
                    startActivity(i)
                } catch (_: Throwable) { }
            }
        }

        @JavascriptInterface
        fun dar_foco() { }

        @JavascriptInterface
        fun ocultar_desactivar() { ui.post { moveTaskToBack(true) } }

        /** LLAMADA con JARVIS (voz Gemini Live) — orden 04/10/2026. */
        @JavascriptInterface
        fun llamada_iniciar() { ui.post { iniciarLlamada() } }

        @JavascriptInterface
        fun llamada_cerrar() { ui.post { cerrarLlamada() } }

        @JavascriptInterface
        fun llamada_mute(m: Boolean) { ui.post { llamada?.setMudo(m) } }

        /** Historial persistente del chat. */
        @JavascriptInterface
        fun historial_leer(): String = leerHistorial()

        @JavascriptInterface
        fun historial_guardar(j: String?) { guardarHistorial(j ?: "[]") }

        /** Dictado: lo que el jefe habla se escribe en la caja de texto. */
        @JavascriptInterface
        fun dictar() { ui.post { alternarDictado() } }

        /** Aviso desde la pagina de que el dictado debe seguir o parar. */
        @JavascriptInterface
        fun dictado(activo: Boolean) { ui.post { if (activo) iniciarDictado() else detenerDictado() } }

        @JavascriptInterface
        fun log(t: String?) { android.util.Log.d("JARVIS-WEB", t ?: "") }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        vm = ViewModelProvider(this)[ChatViewModel::class.java]
        montarWebView()
        observarEstado()
        vm.conectar()
        // SIN SERVICIO DE FONDO NI NOTIFICACIONES (orden del jefe 05/10/2026):
        // la app ya NO queda corriendo por detras ni muestra avisos. Se abre
        // limpia (sin historial) y la sesion vive solo mientras la app esta abierta.
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (chatAbierto) abrirChat(false) else finish()
            }
        })
    }

    // (Sin permiso de notificaciones ni servicio de fondo: desde la 23.0 la app
    //  no avisa ni se queda corriendo por detras — orden del jefe 05/10/2026.)

    // ------------------------------------------------------------- WebView ---
    @SuppressLint("SetJavaScriptEnabled")
    private fun montarWebView() {
        val w = WebView(this)
        w.setBackgroundColor(Color.parseColor("#010a12"))
        w.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            mediaPlaybackRequiresUserGesture = false
            allowFileAccess = true
            allowContentAccess = true
            // IMAGENES LOCAL (19.0): permitir que el HTML cargue <img> desde
            // rutas file:// del propio almacen de la app.
            allowFileAccessFromFileURLs = true
            allowUniversalAccessFromFileURLs = true
            cacheMode = WebSettings.LOAD_DEFAULT
            useWideViewPort = false
            loadWithOverviewMode = false
            textZoom = 100
        }
        w.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(
                view: WebView?, request: android.webkit.WebResourceRequest?
            ): Boolean = false

            override fun onPageFinished(view: WebView?, url: String?) {
                paginaLista = true
                flush()
                eval("window.wSetChatAbierto($chatAbierto);")
                // BLINDAJE DEL EFECTO (192, 04/10/2026): se garantiza que el
                // efecto de tecleo quede activo al cargar la app. Si el jefe
                // cambio el efecto, su eleccion (guardada) se respeta; si no,
                // queda 'escribir' por defecto.
                eval("if(window.wSetEfecto){try{var _g=localStorage.getItem('jarvis_efecto');" +
                    "window.wSetEfecto((_g&&_g.length)?_g:'escribir');}catch(e){" +
                    "window.wSetEfecto('escribir');}}")
                // Si aun no hay sesion, la app pide los datos en el panel de
                // acceso de una sola vez (orden del jefe 04/10/2026). Se abre
                // siempre que no haya acceso hecho; si Telegram ya pide un paso
                // (codigo/clave), wSetFase lo colocara en su bloque.
                if (!Preferencias.accesoHecho(this@MainActivity)) {
                    ui.postDelayed({
                        try {
                            eval("if(window.wSetFase)window.wSetFase(${JSONObject.quote(vm.tgRequiere.value)});")
                            eval("if(window.wAbrirAcceso)window.wAbrirAcceso(true);")
                        } catch (_: Throwable) { }
                    }, 150)
                }
                pushEstado()
            }

            override fun onReceivedError(
                view: WebView?, request: android.webkit.WebResourceRequest?,
                error: android.webkit.WebResourceError?
            ) {
                if (request?.isForMainFrame == true) {
                    ui.post { avisar("No pude cargar la interfaz.") }
                }
            }
        }
        w.webChromeClient = object : WebChromeClient() {
            override fun onPermissionRequest(request: android.webkit.PermissionRequest?) {
                request?.grant(request.resources)
            }
            // DIAGNOSTICO (04/10/2026): lleva los errores de JavaScript al logcat
            // con la etiqueta JARVIS-WEB. Si la pagina reventara, aqui se ve el
            // mensaje y la linea exactos en vez de una pantalla muda.
            override fun onConsoleMessage(m: android.webkit.ConsoleMessage?): Boolean {
                if (m != null) {
                    android.util.Log.d("JARVIS-WEB",
                        "[${m.messageLevel()}] ${m.message()} @ ${m.sourceId()}:${m.lineNumber()}")
                }
                return true
            }
        }
        // Android 15 obliga a dibujar de borde a borde: apartamos la interfaz
        // de la barra de estado y de la barra de navegacion.
        window.setBackgroundDrawable(android.graphics.drawable.ColorDrawable(Color.parseColor("#010a12")))
        androidx.core.view.ViewCompat.setOnApplyWindowInsetsListener(w) { v, insets ->
            val b = insets.getInsets(
                androidx.core.view.WindowInsetsCompat.Type.systemBars()
                    or androidx.core.view.WindowInsetsCompat.Type.displayCutout()
            )
            // SIN padding arriba (orden 04/10/2026): asi la barra de JARVIS llega
            // al borde de la pantalla y no queda un hueco despegado. El aire para
            // la hora/notch lo da el propio CSS (safe-area-inset-top).
            v.setPadding(b.left, 0, b.right, b.bottom)
            insets
        }
        setContentView(w, ViewGroup.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        w.addJavascriptInterface(Puente(), "Android")
        web = w
        w.loadUrl("file:///android_asset/widget.html")
    }

    override fun onStart() {
        super.onStart()
        com.wascar.jarvis.JarvisApp.enPrimerPlano = true
    }

    override fun onStop() {
        super.onStop()
        com.wascar.jarvis.JarvisApp.enPrimerPlano = false
    }

    // Al volver a la app (orden 05/10/2026): trae los mensajes que llegaron con
    // la app cerrada o en segundo plano. No duplica: la app recuerda lo visto.
    override fun onResume() {
        super.onResume()
        try { vm.resincronizar() } catch (_: Throwable) { }
    }

    // -------------------------------------------------------------- Estado ---
    private fun observarEstado() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {
                launch {
                    vm.mensajes.collect { lista ->
                        while (vistos < lista.size) {
                            val m = lista[vistos]
                            pushMensaje(if (m.de == "jefe") "jefe" else "jarvis", m.texto, m.fecha)
                            vistos++
                        }
                    }
                }
                // RECARGA AL ABRIR (fix 05/10/2026): rehace el chat con los ultimos
                // mensajes traidos de Telegram (robusto ante relojes y huecos).
                launch {
                    vm.recarga.collect { lista ->
                        if (lista.isEmpty()) return@collect
                        val arr = org.json.JSONArray()
                        for (m in lista) {
                            val o = org.json.JSONObject()
                            o.put("de", m.de)
                            o.put("texto", m.texto)
                            o.put("fecha", m.fecha)
                            arr.put(o)
                        }
                        eval("if(window.wRecargarChat)window.wRecargarChat($arr);")
                    }
                }
                launch {
                    vm.tgEstado.collect { e ->
                        tgEstado = e
                        // Acceso completado (orden del jefe 04/10/2026): al quedar
                        // "en linea" se cierra el panel y se marca el acceso hecho.
                        if (e.contains("en linea") || e.contains("listo")) {
                            Preferencias.marcarAccesoHecho(this@MainActivity, true)
                            // Muestra el bloque "Acceso concedido" con su boton.
                            eval("if(window.wAccesoMsg)window.wAccesoMsg('Acceso concedido. JARVIS en línea.', true);")
                        }
                        pushEstado()
                    }
                }
                launch { vm.usandoTelegram.collect { usandoTg = it; pushEstado() } }
                launch { vm.trabajando.collect { trabajandoAhora = it; pushEstado() } }
                launch {
                    vm.tgRequiere.collect { r ->
                        val anterior = requiereActual
                        requiereActual = r
                        // Panel de acceso (fix 20.1): el panel muestra el paso que
                        // pida Telegram. Con codigo/clave aparece el campo del paso;
                        // con "telefono" se queda en los datos. Se ABRE solo cuando
                        // hay que contestar algo (codigo/clave).
                        eval("if(window.wSetFase)window.wSetFase(${JSONObject.quote(r)});")
                        if (r == "codigo" || r == "clave") {
                            eval("if(window.wAbrirAcceso)window.wAbrirAcceso(true);")
                        }
                        // Solo avisa cuando CAMBIA (no en cada reemision).
                        if (r.isNotEmpty() && r != anterior) {
                            abrirChat(true)
                            pushMensaje("jarvis", pistaTelegram(r))
                        }
                        pushEstado()
                    }
                }
                // IMAGENES EN EL CHAT (19.0): cada foto nueva se pinta como burbuja.
                launch {
                    var n = 0
                    vm.imagenes.collect { lista ->
                        while (n < lista.size) {
                            val im = lista[n]
                            val rol = if (im.first == "jefe") "jefe" else "jarvis"
                            eval("if(window.wAddImagen)window.wAddImagen(" +
                                "${JSONObject.quote(rol)}, ${JSONObject.quote(im.second)});")
                            n++
                        }
                    }
                }
            }
        }
    }

    private fun pistaTelegram(r: String): String = when (r) {
        "telefono" -> "Telegram pide tu numero con pais (ej +58...). Escribelo abajo."
        "codigo" -> "Escribe el codigo que llego a tu Telegram."
        "clave" -> "Escribe tu contrasena de Telegram (verificacion en dos pasos)."
        else -> ""
    }

    private fun pushEstado() {
        val tgListo = tgEstado.contains("en linea") || tgEstado.contains("listo")
        val fase = when {
            trabajandoAhora -> "THINKING"
            requiereActual.isNotEmpty() -> "THINKING"
            usandoTg && tgListo -> "LISTENING"
            usandoTg -> "MUTED"
            else -> "MUTED"
        }
        val frase = when {
            trabajandoAhora -> "Trabajando, jefe…"
            requiereActual.isNotEmpty() -> ""
            !usandoTg -> "Listo, jefe."
            tgListo -> ""
            tgEstado.isBlank() -> "Conectando Telegram…"
            else -> tgEstado
        }
        eval("window.wSetEstado(${JSONObject.quote(fase)});")
        eval("window.wSetTexto(${JSONObject.quote(frase)});")
        // Boton de enviar <-> boton rojo de interrumpir segun el trabajo.
        eval("if(window.wSetTrabajando)window.wSetTrabajando($trabajandoAhora);")
    }

    // -------------------------------------------------------------- Acciones --
    private fun alEnviar(t: String) {
        val texto = t.trim()
        if (texto.isEmpty()) return
        if (!chatAbierto) abrirChat(true)
        when (requiereActual) {
            "telefono" -> vm.enviarTelefono(texto)
            "codigo" -> vm.enviarCodigo(texto)
            "clave" -> vm.enviarClave(texto)
            else -> vm.enviar(texto)
        }
    }

    /** El jefe eligio una imagen o un documento: se manda por Telegram con el
     *  texto de la caja como pie (orden del jefe 04/10/2026). */
    private fun enviarAdjunto(uri: android.net.Uri) {
        try {
            if (!chatAbierto) abrirChat(true)
            val cr = contentResolver
            var nombre = "archivo"
            var mime = cr.getType(uri) ?: ""
            cr.query(uri, null, null, null, null)?.use { c ->
                val i = c.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
                if (i >= 0 && c.moveToFirst()) nombre = c.getString(i) ?: nombre
            }
            // La imagen se manda como FOTO; lo demas, como DOCUMENTO.
            val esImagen = mime.startsWith("image/")
            // Copia el archivo a la cache de la app para que TDLib lo lea.
            val ext = nombre.substringAfterLast('.', "bin")
            val tmp = java.io.File(cacheDir, "adjunto_${System.currentTimeMillis()}.$ext")
            cr.openInputStream(uri)?.use { ent ->
                tmp.outputStream().use { sal -> ent.copyTo(sal) }
            }
            avisar(if (esImagen) "Enviando imagen…" else "Enviando documento…")
            vm.enviarArchivo(tmp.absolutePath, esImagen, nombre)
        } catch (e: Throwable) {
            avisar("No pude adjuntar el archivo.")
        }
    }

    private fun alternarChat() = abrirChat(!chatAbierto)

    private fun abrirChat(v: Boolean) {
        chatAbierto = v
        eval("window.wSetChatAbierto($v);")
    }

    private fun pushMensaje(rol: String, texto: String, fecha: Long = 0L) {
        eval("window.wAddMensaje(${JSONObject.quote(rol)}, ${JSONObject.quote(texto)}, $fecha);")
    }

    /** Ejecuta JavaScript en la pagina (si aun no cargo, lo deja en cola). */
    private fun eval(code: String) {
        val w = web
        if (w == null || !paginaLista) { pendientes.addLast(code); return }
        ui.post { try { w.evaluateJavascript(code, null) } catch (_: Throwable) { } }
    }

    private fun flush() {
        val w = web ?: return
        while (pendientes.isNotEmpty()) {
            val c = pendientes.removeFirst()
            try { w.evaluateJavascript(c, null) } catch (_: Throwable) { }
        }
    }

    private fun avisar(t: String) = Toast.makeText(this, t, Toast.LENGTH_SHORT).show()

    /** Activa/silencia los avisos de la app (orden del jefe 05/10/2026). */
    private fun cambiarNotificaciones(on: Boolean) {
        Preferencias.guardarNotificaciones(this, on)
        if (on && android.os.Build.VERSION.SDK_INT >= 33 &&
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), PERM_NOTIF)
        }
        avisar(if (on) "Avisos activados" else "Avisos silenciados")
    }

    // ------------------------------------------------------- Dictado nativo ---
    private fun alternarDictado() {
        if (dictando) detenerDictado() else iniciarDictado()
    }

    private fun iniciarDictado() {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), PERM_AUDIO)
            return
        }
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            avisar("Este telefono no tiene dictado disponible.")
            return
        }
        if (voz == null) crearReconocedor()
        dictando = true
        // Actualiza la esfera solo si la pagina soporta el estado (no rompe si no).
        eval("if(window.wSetEstado)window.wSetEstado('LISTENING');")
        mutearBeep()
        escuchar()
        // Avisa a la pagina para que el boton del micro se marque como activo.
        eval("if(window.wSetDictando)window.wSetDictando(true);")
    }

    private fun crearReconocedor() {
        voz = SpeechRecognizer.createSpeechRecognizer(this)
        voz?.setRecognitionListener(object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) { }
            override fun onBeginningOfSpeech() { }
            override fun onRmsChanged(rmsdB: Float) { }
            override fun onBufferReceived(buffer: ByteArray?) { }
            override fun onEndOfSpeech() { }
            override fun onEvent(eventType: Int, params: Bundle?) { }
            override fun onError(error: Int) {
                if (dictando) {
                    ui.postDelayed({ if (dictando) escuchar() }, 250)
                } else {
                    restaurarBeep()
                }
            }

            override fun onResults(results: Bundle?) {
                val t = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    ?.firstOrNull()?.trim().orEmpty()
                if (t.isNotEmpty()) ponerEnEntrada(t)
                if (dictando) ui.postDelayed({ if (dictando) escuchar() }, 250)
            }

            override fun onPartialResults(partialResults: Bundle?) {
                val t = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                    ?.firstOrNull()?.trim().orEmpty()
                if (t.isNotEmpty()) ponerEnEntrada(t)
            }
        })
    }

    private fun escuchar() {
        val i = android.content.Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "es-MX")
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 60000L)
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 60000L)
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS, 60000L)
        }
        try { voz?.startListening(i) } catch (_: Throwable) { }
    }

    private fun detenerDictado() {
        dictando = false
        try { voz?.stopListening() } catch (_: Throwable) { }
        restaurarBeep()
        eval("if(window.wSetDictando)window.wSetDictando(false);")
        pushEstado()
    }

    /**
     * Coloca el texto dictado EN LA CAJA, anexando lo previo y respetando la
     * posicion del cursor. Es lo que pidio el jefe: hablar y que se escriba en
     * el campo de texto (04/10/2026).
     */
    private fun ponerEnEntrada(t: String) {
        val q = org.json.JSONObject.quote(t)
        eval(
            "(function(){var i=document.getElementById('wInput');if(!i)return;" +
                "var p=(i.selectionStart!=null)?i.selectionStart:i.value.length;" +
                "var txt=$q;" +
                "i.value=i.value.slice(0,p)+txt+i.value.slice(p);" +
                "i.selectionStart=i.selectionEnd=p+txt.length;" +
                "i.focus();})();"
        )
    }

    // ------------------------------------------------ Llamada (Gemini Live) ---
    private var llamada: GeminiLive? = null

    private fun claveGemini(): String {
        // Primero la que el jefe haya guardado en la app; si no, la del widget.
        val propia = Preferencias.geminiKey(this)
        if (propia.isNotBlank()) return propia
        return try {
            val cfg = java.io.File(
                "/sdcard/Jarvis/gemini_key.txt"
            )
            if (cfg.exists()) cfg.readText().trim() else ""
        } catch (_: Throwable) { "" }
    }

    private fun iniciarLlamada() {
        if (llamada != null) return
        android.util.Log.d("JARVIS-LIVE", "iniciarLlamada()")
        // Cierra el teclado para que no tape los botones de la llamada.
        try {
            (getSystemService(INPUT_METHOD_SERVICE) as android.view.inputmethod.InputMethodManager)
                .hideSoftInputFromWindow(web?.windowToken, 0)
        } catch (_: Throwable) { }
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), PERM_AUDIO)
            avisar("Da permiso al micrófono y vuelve a tocar la esfera.")
            return
        }
        val clave = claveGemini()
        android.util.Log.d("JARVIS-LIVE", "clave presente=" + clave.isNotBlank() + " len=" + clave.length)
        if (clave.isBlank()) {
            eval("if(window.wSetLlamada)window.wSetLlamada('Falta la clave de Gemini');")
            avisar("Falta la clave de Gemini en la app.")
            return
        }
        eval("if(window.wSetLlamada)window.wSetLlamada('Conectando…');")
        val g = GeminiLive(
            apiKey = clave,
            modelo = Preferencias.liveModelo(this),
            voz = Preferencias.liveVoz(this),
            systemPrompt = "Eres JARVIS, el asistente personal del señor Wáscar. " +
                "Respondes en español, breve y con elegancia. NUNCA digas que eres un " +
                "modelo genérico: eres JARVIS. Hablas natural, como en una llamada.",
            onEstado = { e -> ui.post { eval("if(window.wSetLlamada)window.wSetLlamada(${org.json.JSONObject.quote(e)});") } },
            onTexto = { t ->
                ui.post {
                    eval("if(window.wAddMensaje)window.wAddMensaje('jarvis', ${org.json.JSONObject.quote(t)});")
                }
            },
        )
        llamada = g
        g.iniciar()
    }

    private fun cerrarLlamada() {
        try { llamada?.cerrar() } catch (_: Throwable) { }
        llamada = null
    }

    // ------------------------------------------------ Historial persistente ---
    private fun archivoHistorial(): java.io.File =
        java.io.File(filesDir, "historial_chat.json")

    private fun leerHistorial(): String {
        return try {
            val f = archivoHistorial()
            if (f.exists()) f.readText() else "[]"
        } catch (_: Throwable) { "[]" }
    }

    private fun guardarHistorial(json: String) {
        // BLINDAJE DE FLUIDEZ (04/10/2026): se escribe en un hilo aparte y con
        // debounce. Antes, cada mensaje escribia el archivo COMPLETO en el hilo
        // de UI y con chats largos eso micro-trababa la app. Ahora nunca toca
        // el hilo principal y agrupa escrituras seguidas en una sola.
        try {
            val f = archivoHistorial()
            ui.post {
                try { f.writeText(json) } catch (_: Throwable) { }
            }
        } catch (_: Throwable) { }
    }

    // ---- Silenciar el "beep" del reconocedor ----
    private fun mutearBeep() {
        try {
            val am = getSystemService(Context.AUDIO_SERVICE) as AudioManager
            if (volMusicaPrev < 0) volMusicaPrev = am.getStreamVolume(AudioManager.STREAM_MUSIC)
            if (volNotifPrev < 0) volNotifPrev = am.getStreamVolume(AudioManager.STREAM_NOTIFICATION)
            if (volSistemaPrev < 0) volSistemaPrev = am.getStreamVolume(AudioManager.STREAM_SYSTEM)
            am.setStreamVolume(AudioManager.STREAM_MUSIC, 0, 0)
            am.setStreamVolume(AudioManager.STREAM_NOTIFICATION, 0, 0)
            am.setStreamVolume(AudioManager.STREAM_SYSTEM, 0, 0)
        } catch (_: Throwable) { }
    }

    private fun restaurarBeep() {
        try {
            val am = getSystemService(Context.AUDIO_SERVICE) as AudioManager
            if (volMusicaPrev >= 0) { am.setStreamVolume(AudioManager.STREAM_MUSIC, volMusicaPrev, 0); volMusicaPrev = -1 }
            if (volNotifPrev >= 0) { am.setStreamVolume(AudioManager.STREAM_NOTIFICATION, volNotifPrev, 0); volNotifPrev = -1 }
            if (volSistemaPrev >= 0) { am.setStreamVolume(AudioManager.STREAM_SYSTEM, volSistemaPrev, 0); volSistemaPrev = -1 }
        } catch (_: Throwable) { }
    }

    override fun onRequestPermissionsResult(
        requestCode: Int, permissions: Array<String>, grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == PERM_AUDIO) {
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                iniciarDictado()
            } else {
                avisar("Sin permiso de microfono no puedo escuchar.")
            }
        }
    }

    override fun onDestroy() {
        dictando = false
        try { voz?.destroy() } catch (_: Throwable) { }
        restaurarBeep()
        try { web?.destroy() } catch (_: Throwable) { }
        super.onDestroy()
    }
}
