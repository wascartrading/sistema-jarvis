package com.wascar.jarvis.data

import android.content.Context
import io.github.tdlibandroid.ktx.TdClient
import io.github.tdlibandroid.ktx.authStateFlow
import io.github.tdlibandroid.ktx.updatesOf
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.drinkless.tdlib.TdApi
import java.io.File

/** Mensaje releido del chat: rol, texto, id y fecha (epoch en segundos). */
data class NuevoMsg(val rol: String, val texto: String, val id: Long, val fecha: Long)

/** Mensaje para RECARGAR la pantalla al abrir: rol, texto y fecha (epoch seg). */
data class RecargaMsg(val de: String, val texto: String, val fecha: Long)

/**
 * Puente Telegram REAL (MTProto / TDLib) — orden del jefe 04/10/2026.
 *
 * La app entra a Telegram COMO LA CUENTA DEL JEFE (via api_id/api_hash) y
 * conversa con el bot @jarvis_asistent_kilo_bot, que en la PC habla con el
 * COMBO JARVIS. Asi Telegram es el unico puente: no hace falta exponer la PC
 * ni depender de la red local.
 *
 * Flujo: arrancar() -> estado de autorizacion (telefono -> codigo -> clave)
 * -> buscar el bot -> enviar/recibir mensajes.
 */
class TelegramManager private constructor(private val ctx: Context) {

    private var cliente: TdClient? = null
    private val alcance = CoroutineScope(Dispatchers.IO + SupervisorJob())

    /**
     * SESION UNICA DE LA APP (orden del jefe 04/10/2026, servicio de fondo A+B).
     * TDLib vive en UN solo objeto compartido por Activity, Service y avisos,
     * para que el proceso pueda seguir conectado aunque la app este en segundo
     * plano o cerrada. Sin esto, cada pantalla tendria su propia sesion.
     */
    companion object {
        const val SELLO_TRABAJANDO = "[[JARVIS:TRABAJANDO]]"
        const val SELLO_FIN = "[[JARVIS:FIN]]"
        const val SELLO_INTERRUMPIR = "[[JARVIS:INTERRUMPIR]]"
        const val SELLO_REINICIAR = "[[JARVIS:REINICIAR]]"

        // Preferencias compartidas y clave donde se guarda la fecha del ultimo
        // mensaje conocido (fix 05/10/2026: sobrevive al cierre de la app).
        const val PREF = "jarvis_app"
        const val K_FECHA = "tg_ultima_fecha"

        @Volatile private var instancia: TelegramManager? = null

        fun obtener(ctx: Context): TelegramManager {
            val app = ctx.applicationContext
            return instancia ?: synchronized(this) {
                instancia ?: TelegramManager(app).also { instancia = it }
            }
        }
    }

    private val _estado = MutableStateFlow("apagado")
    val estado = _estado.asStateFlow()

    /** Que dato pide Telegram: "" | "telefono" | "codigo" | "clave". */
    private val _requiere = MutableStateFlow("")
    val requiere = _requiere.asStateFlow()

    private val _mensajes = MutableStateFlow<List<Pair<String, String>>>(emptyList())
    val mensajes = _mensajes.asStateFlow()

    /**
     * SELLOS invisibles del bot (04/10/2026): "trabajando" | "fin" | "interrumpir".
     * El bot los manda por el MISMO chat; la app NO los muestra y los usa para
     * encender/apagar el estado. Se emiten por este flujo.
     */
    private val _sello = MutableStateFlow("")
    val sello = _sello.asStateFlow()

    @Volatile private var chatId: Long = 0L

    /** Teléfono guardado (con país): se envia SOLO al arrancar si Telegram lo pide. */
    @Volatile private var telefonoInicial = ""
    @Volatile private var telefonoEnviado = false

    // SINCRONIZACION AL RECUPERAR CONEXION (orden del jefe 04/10/2026):
    // si el jefe se queda sin internet, al volver se releen del chat los
    // ultimos mensajes y se emiten los que aun no se habian visto. Asi NO se
    // pierde nada de lo enviado/recibido durante el corte.
    private val _nuevos = MutableStateFlow<List<NuevoMsg>>(emptyList())
    val nuevos: StateFlow<List<NuevoMsg>> = _nuevos.asStateFlow()

    // RECARGA AL ABRIR (fix 05/10/2026): los ultimos mensajes traidos del chat
    // para REHACER la pantalla al abrir la app. Robusto ante relojes desfasados.
    private val _recarga = MutableStateFlow<List<RecargaMsg>>(emptyList())
    val recarga: StateFlow<List<RecargaMsg>> = _recarga.asStateFlow()

    /**
     * IMAGENES VISIBLES EN EL CHAT (orden del jefe 04/10/2026, version 19.0):
     * cuando llega (o se envia) una FOTO, se descarga a la cache de la app y se
     * emite su ruta local como un evento (rol + ruta). La interfaz la pinta.
     * Tripe = (rol, rutaArchivo, idMensaje). idMensaje 0 = imagen propia ya pintada.
     */
    private val _imagenes = MutableStateFlow<List<Triple<String, String, Long>>>(emptyList())
    val imagenes: StateFlow<List<Triple<String, String, Long>>> = _imagenes.asStateFlow()
    // IDs de mensajes ya emitidos (evita duplicados entre updates y releidos).
    private val vistos = java.util.Collections.synchronizedSet(HashSet<Long>())
    private var ultimaConexion = ""
    @Volatile private var usuarioBot = ""
    // Fecha (segundos) del ultimo mensaje ya conocido: sincronizar() solo emite
    // los mas NUEVOS que esto -> nunca duplica lo que ya esta en pantalla.
    // PERSISTENTE (fix 05/10/2026): se guarda en preferencias para que al abrir
    // la app se traigan SOLO los mensajes que llegaron mientras estaba cerrada.
    @Volatile private var ultimaFecha: Long =
        ctx.getSharedPreferences(PREF, Context.MODE_PRIVATE).getLong(K_FECHA, 0L)

    /** Avanza la marca de fecha y la PERSISTE (siempre que sea mas nueva). */
    private fun fijarFecha(f: Long) {
        if (f <= ultimaFecha) return
        ultimaFecha = f
        try {
            ctx.getSharedPreferences(PREF, Context.MODE_PRIVATE).edit()
                .putLong(K_FECHA, f).apply()
        } catch (_: Throwable) { }
    }

    /** Marca que la app ya conoce hasta este instante (se llama al cargar el
     *  historial local, con la fecha del ultimo mensaje guardado). */
    fun marcarConocidoHasta(epochSegundos: Long) {
        fijarFecha(epochSegundos + 1)
    }

    /**
     * Relee los ultimos mensajes del chat desde Telegram y emite los que no se
     * habian visto. Se llama SOLO al recuperar la conexion (nunca en cada
     * apertura): asi se ahorra red/datos cuando la app vuelve a primer plano.
     * (Ajuste 04/10/2026: antes se llamaba tambien en cada onResume -> gastaba
     * datos sin motivo aunque no hubiera habido corte.)
     */
    fun sincronizar(cantidad: Int = 30) {
        val c = cliente ?: return
        if (chatId == 0L) return
        // Primer arranque tras actualizar (fix 05/10/2026): si aun no hay fecha
        // guardada, se toma la del historial local para NO repetir lo ya visto.
        if (ultimaFecha == 0L) {
            try {
                val f = java.io.File(ctx.filesDir, "historial_chat.json")
                if (f.exists()) fijarFecha(f.lastModified() / 1000L)
            } catch (_: Throwable) { }
        }
        alcance.launch {
            try {
                val hist = c.send(TdApi.GetChatHistory(chatId, 0L, 0, cantidad, false))
                val msgs = (hist as? TdApi.Messages)?.messages ?: return@launch
                // Del mas viejo al mas nuevo.
                val orden = msgs.sortedBy { it.id }
                for (m in orden) {
                    if (vistos.contains(m.id)) continue
                    vistos.add(m.id)
                    // Solo los posteriores a lo que la app ya conocia.
                    if (m.date.toLong() <= ultimaFecha) continue
                    // FOTO: se descarga y se pinta (no pasa por el texto).
                    // Las fotos PROPIAS (isOutgoing) ya se pintaron al enviarlas
                    // (miniatura local en el ViewModel): no se re-emiten aqui para
                    // no duplicarlas.
                    val foto = fotoDe(m.content)
                    if (foto != null) {
                        if (!m.isOutgoing) descargarFoto(foto, "jarvis", m.id)
                        fijarFecha(m.date.toLong())
                        continue
                    }
                    // Salta los SELLOS invisibles (no son contenido real).
                    val t = textoDe(m.content).trim()
                    if (t.isBlank() || t == SELLO_TRABAJANDO || t == SELLO_FIN ||
                        t == SELLO_INTERRUMPIR || t == SELLO_REINICIAR) continue
                    // Los del bot son "jarvis"; los que envia el jefe, "jefe".
                    val rol = if (m.isOutgoing) "jefe" else "jarvis"
                    val visible = t.replace(SELLO_TRABAJANDO, "").replace(SELLO_FIN, "").trim()
                    if (visible.isBlank()) continue
                    fijarFecha(m.date.toLong())
                    _nuevos.value = _nuevos.value + NuevoMsg(rol, visible, m.id, m.date.toLong())
                }
            } catch (_: Throwable) { }
        }
    }

    /**
     * RECARGA AL ABRIR (fix 05/10/2026): trae los ULTIMOS mensajes del chat y los
     * emite para que la app rehaga la pantalla. NO depende del reloj ni de
     * fechas: la app decide que falta comparando por contenido.
     */
    fun recargarChat(cantidad: Int = 25) {
        val c = cliente ?: return
        if (chatId == 0L) return
        alcance.launch {
            try {
                try { c.send(TdApi.OpenChat(chatId)) } catch (_: Throwable) { }
                val hist = c.send(TdApi.GetChatHistory(chatId, 0L, 0, cantidad, false))
                val msgs = (hist as? TdApi.Messages)?.messages ?: return@launch
                val orden = msgs.sortedBy { it.id }
                val lista = ArrayList<RecargaMsg>()
                for (m in orden) {
                    val t = textoDe(m.content).trim()
                    if (t.isBlank() || t == SELLO_TRABAJANDO || t == SELLO_FIN ||
                        t == SELLO_INTERRUMPIR || t == SELLO_REINICIAR) continue
                    val rol = if (m.isOutgoing) "jefe" else "jarvis"
                    val visible = t.replace(SELLO_TRABAJANDO, "").replace(SELLO_FIN, "").trim()
                    if (visible.isBlank()) continue
                    vistos.add(m.id)
                    lista.add(RecargaMsg(rol, visible, m.date.toLong()))
                }
                if (lista.isNotEmpty()) _recarga.value = lista
            } catch (_: Throwable) { }
        }
    }

    /**
     * Arranca TDLib UNA sola vez. Si ya hay cliente vivo NO crea otro: solo
     * actualiza el telefono (asi, cuando el jefe mete los datos en el panel, no
     * hay carrera entre cerrar y volver a arrancar — era el fallo de 20.0).
     * Fix 20.1 (04/10/2026).
     */
    fun arrancar(apiId: Int, apiHash: String, botUsuario: String, telefono: String = "") {
        usuarioBot = botUsuario
        // Si ya hay cliente, NO se recrea: se le manda el telefono si hace falta.
        if (cliente != null) {
            if (telefono.isNotBlank() && !telefonoEnviado) {
                telefonoInicial = telefono.trim()
                telefonoEnviado = true
                enviarTelefono(telefono.trim())
            }
            return
        }
        telefonoInicial = telefono.trim()
        telefonoEnviado = false
        try {
            System.loadLibrary("tdjni")
        } catch (t: Throwable) {
            _estado.value = "sin libreria nativa"
            return
        }
        val dir = File(ctx.filesDir, "tdlib").absolutePath
        val c = TdClient(
            filesDir = dir,
            verbosityLevel = 1,
            apiId = apiId,
            apiHash = apiHash,
            dispatcher = Dispatchers.IO
        )
        cliente = c
        _estado.value = "iniciando"
        c.init()

        alcance.launch {
            try {
                c.authStateFlow().collect { s ->
                    when (s) {
                        is TdApi.AuthorizationStateWaitPhoneNumber -> {
                            _requiere.value = "telefono"; _estado.value = "pide telefono"
                            // ACCESO AUTOMATICO (orden del jefe 04/10/2026): si ya
                            // hay telefono guardado y aun no se envio en este
                            // arranque, se manda solo (una vez) para no re-pedirlo.
                            if (telefonoInicial.isNotBlank() && !telefonoEnviado) {
                                telefonoEnviado = true
                                try {
                                    cliente?.send(
                                        TdApi.SetAuthenticationPhoneNumber(telefonoInicial, null)
                                    )
                                } catch (_: Throwable) { }
                            }
                        }
                        is TdApi.AuthorizationStateWaitCode -> {
                            _requiere.value = "codigo"; _estado.value = "pide codigo"
                        }
                        is TdApi.AuthorizationStateWaitPassword -> {
                            _requiere.value = "clave"; _estado.value = "pide clave"
                        }
                        is TdApi.AuthorizationStateReady -> {
                            _requiere.value = ""; _estado.value = "en linea"; abrirBot(botUsuario)
                        }
                        is TdApi.AuthorizationStateLoggingOut -> _estado.value = "saliendo"
                        is TdApi.AuthorizationStateClosed -> _estado.value = "cerrado"
                        else -> { }
                    }
                }
            } catch (_: Throwable) { }
        }

        alcance.launch {
            try {
                c.updatesOf<TdApi.UpdateNewMessage>().collect { u ->
                    val m = u.message
                    // (fix 05/10/2026) Solo se marca como "visto" lo de NUESTRO
                    // chat. Los mensajes que TDLib entrega al arrancar ANTES de
                    // resolver el chatId NO se marcan: asi sincronizar() los trae
                    // al abrir (antes se perdian: se marcaban vistos sin pintarse).
                    val esNuestro = chatId != 0L && m.chatId == chatId
                    if (esNuestro) {
                        vistos.add(m.id)
                        fijarFecha(m.date.toLong())
                    }
                    if (esNuestro && !m.isOutgoing) {
                        // FOTO entrante: se descarga y se pinta en el chat.
                        val foto = fotoDe(m.content)
                        if (foto != null) {
                            descargarFoto(foto, "jarvis", m.id)
                            return@collect
                        }
                        val t = textoDe(m.content)
                        if (t.isNotBlank()) {
                            val limpio = t.trim()
                            // SELLO invisible: no se muestra; se emite como señal.
                            when (limpio) {
                                SELLO_TRABAJANDO -> _sello.value = "trabajando"
                                SELLO_FIN -> _sello.value = "fin"
                                SELLO_INTERRUMPIR -> _sello.value = "interrumpir"
                                else -> {
                                    // Si el texto TRAE un sello embebido, se quita
                                    // antes de mostrarlo (defensa por si viniera junto).
                                    val visible = limpio
                                        .replace(SELLO_TRABAJANDO, "")
                                        .replace(SELLO_FIN, "")
                                        .trim()
                                    if (visible.isNotBlank()) {
                                        _mensajes.value = _mensajes.value + ("jarvis" to visible)
                                        // Aviso (silencio por defecto): solo si el
                                        // jefe activo los avisos y la app no se ve.
                                        com.wascar.jarvis.JarvisApp.avisar(ctx, visible)
                                    }
                                }
                            }
                        }
                    }
                }
            } catch (_: Throwable) { }
        }

        // RECUPERACION AL VOLVER LA CONEXION (orden del jefe 04/10/2026): cuando
        // el estado pasa a "listo" tras haber perdido la red, se relee el chat y
        // se emiten los mensajes que no se habian visto.
        alcance.launch {
            try {
                c.updatesOf<TdApi.UpdateConnectionState>().collect { u ->
                    val nuevo = when (u.state) {
                        is TdApi.ConnectionStateReady -> "listo"
                        is TdApi.ConnectionStateConnecting -> "conectando"
                        is TdApi.ConnectionStateUpdating -> "actualizando"
                        is TdApi.ConnectionStateWaitingForNetwork -> "sin red"
                        else -> "otro"
                    }
                    if (nuevo == "listo" && ultimaConexion != "listo" &&
                        ultimaConexion.isNotEmpty()) {
                        // Venimos de un corte: trae lo que falte.
                        sincronizar()
                    }
                    ultimaConexion = nuevo
                }
            } catch (_: Throwable) { }
        }
    }

    private fun abrirBot(usuario: String) {
        alcance.launch {
            try {
                val limpio = usuario.trim().removePrefix("@")
                val chat = cliente?.send(TdApi.SearchPublicChat(limpio))
                if (chat is TdApi.Chat) {
                    chatId = chat.id
                    _estado.value = "en linea con @$limpio"
                    // AL ABRIR (fix 05/10/2026): trae los mensajes que llegaron
                    // mientras la app estaba cerrada. Se ABRE el chat para que
                    // TDLib cargue su historial y se REINTENTA: la primera lectura
                    // puede volver vacia mientras TDLib termina de cargar.
                    // Recarga la pantalla con los ultimos mensajes del chat
                    // (robusto: no depende del reloj) y reintenta por si la
                    // primera lectura vuelve antes de cargar el historial.
                    recargarChat()
                    delay(2500); recargarChat()
                    delay(4500); recargarChat()
                }
            } catch (_: Throwable) {
                _estado.value = "no encontre el bot"
            }
        }
    }

    fun enviarTelefono(t: String) {
        val tel = t.trim()
        if (tel.isBlank()) return
        telefonoInicial = tel
        telefonoEnviado = true
        alcance.launch { try { cliente?.send(TdApi.SetAuthenticationPhoneNumber(tel, null)) } catch (_: Throwable) { } }
    }

    /** true si TDLib ya tiene cliente vivo (arranco bien). */
    fun vivo(): Boolean = cliente != null

    fun enviarCodigo(c: String) {
        alcance.launch { try { cliente?.send(TdApi.CheckAuthenticationCode(c.trim())) } catch (_: Throwable) { } }
    }

    fun enviarClave(p: String) {
        alcance.launch { try { cliente?.send(TdApi.CheckAuthenticationPassword(p)) } catch (_: Throwable) { } }
    }

    fun enviar(texto: String): Boolean {
        val c = cliente ?: return false
        if (chatId == 0L) return false
        // Lo que el jefe acaba de escribir ya se pinta: mueve la marca para que
        // la sincronizacion posterior no lo repita.
        fijarFecha(System.currentTimeMillis() / 1000L)
        alcance.launch {
            try {
                val fam = TdApi.FormattedText()
                fam.text = texto
                val cont = TdApi.InputMessageText()
                cont.text = fam
                val m = TdApi.SendMessage()
                m.chatId = chatId
                m.inputMessageContent = cont
                c.send(m)
            } catch (_: Throwable) { }
        }
        return true
    }

    private fun textoDe(content: TdApi.MessageContent): String = when (content) {
        is TdApi.MessageText -> content.text?.text ?: ""
        else -> ""
    }

    /** Si el contenido es una FOTO, devuelve su objeto Photo; si no, null. */
    private fun fotoDe(content: TdApi.MessageContent): TdApi.Photo? =
        (content as? TdApi.MessagePhoto)?.photo

    /** Sufijo del archivo de una foto (jpg por defecto; Telegram usa jpg/webp). */
    private fun extDeFoto(foto: TdApi.Photo): String {
        // El objeto File de TDLib no trae mimeType; el nombre del archivo remoto
        // suele terminar en .jpg/.png/.webp. Si no se puede saber, se usa jpg.
        val rutaRemota = foto.sizes.maxByOrNull { it.width * it.height }
            ?.photo?.remote?.id ?: ""
        val r = rutaRemota.lowercase()
        if (r.endsWith(".png")) return "png"
        if (r.endsWith(".webp")) return "webp"
        return "jpg"
    }

    /**
     * Descarga una FOTO a la cache de la app y emite su ruta local para que el
     * chat la pinte. Defensivo: cualquier fallo no rompe el resto. (19.0)
     */
    private fun descargarFoto(foto: TdApi.Photo, rol: String, idMsg: Long) {
        val c = cliente ?: return
        alcance.launch {
            try {
                // La resolucion mas grande disponible.
                val size = foto.sizes.maxByOrNull { it.width * it.height } ?: return@launch
                val fileId = size.photo.id
                val destino = File(ctx.cacheDir, "img_${idMsg}.${extDeFoto(foto)}").absolutePath
                val req = TdApi.DownloadFile()
                req.fileId = fileId
                req.priority = 1
                req.offset = 0
                req.limit = 0
                req.synchronous = true
                val f = c.send(req) as? TdApi.File
                val ruta = f?.local?.path ?: destino
                // Copia a un nombre propio y estable (la ruta de TDLib cambia).
                var final = ruta
                try {
                    val src = File(ruta)
                    if (src.exists()) {
                        val dst = File(destino)
                        src.copyTo(dst, overwrite = true)
                        final = dst.absolutePath
                    }
                } catch (_: Throwable) { }
                if (File(final).exists()) {
                    _imagenes.value = _imagenes.value + Triple(rol, final, idMsg)
                }
            } catch (_: Throwable) { }
        }
    }

    /** Manda una imagen (Foto) o un documento por Telegram (orden jefe 04/10/2026). */
    fun enviarArchivo(ruta: String, esImagen: Boolean): Boolean {
        val c = cliente ?: return false
        if (chatId == 0L) return false
        // OJO (19.0): la miniatura local la emite el ViewModel UNA sola vez. Aqui
        // NO se emite (evita pintar la imagen dos veces en el chat).
        alcance.launch {
            try {
                val m = TdApi.SendMessage()
                m.chatId = chatId
                val archivo = TdApi.InputFileLocal(ruta)
                if (esImagen) {
                    val foto = TdApi.InputPhoto()
                    foto.photo = archivo
                    foto.thumbnail = null
                    foto.video = null
                    foto.addedStickerFileIds = IntArray(0)
                    foto.width = 0
                    foto.height = 0
                    val cont = TdApi.InputMessagePhoto()
                    cont.photo = foto
                    cont.caption = TdApi.FormattedText("", null)
                    cont.showCaptionAboveMedia = false
                    cont.selfDestructType = null
                    cont.hasSpoiler = false
                    m.inputMessageContent = cont
                } else {
                    val doc = TdApi.InputDocument()
                    doc.document = archivo
                    doc.thumbnail = null
                    doc.disableContentTypeDetection = false
                    val cont = TdApi.InputMessageDocument()
                    cont.document = doc
                    cont.caption = TdApi.FormattedText("", null)
                    m.inputMessageContent = cont
                }
                c.send(m)
            } catch (_: Throwable) { }
        }
        return true
    }
    fun cerrar() {
        try { cliente?.close() } catch (_: Throwable) { }
        cliente = null
    }
}
