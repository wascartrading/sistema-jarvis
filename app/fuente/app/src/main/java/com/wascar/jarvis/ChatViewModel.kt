package com.wascar.jarvis

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.wascar.jarvis.data.JarvisClient
import com.wascar.jarvis.data.Preferencias
import com.wascar.jarvis.data.TelegramManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/** Un mensaje del chat. de = "jefe" | "jarvis" | "sistema". fecha = epoch seg (0 = ahora). */
data class Mensaje(val de: String, val texto: String, val fecha: Long = 0L)

/**
 * Estado de la app (UDF). Dos puentes posibles:
 *  - TELEGRAM (MTProto/TDLib): Telegram es el puente real (elegido por el jefe).
 *  - PC (WebSocket): el puente propio, para la red local.
 */
class ChatViewModel(app: Application) : AndroidViewModel(app) {

    private val _mensajes: MutableStateFlow<List<Mensaje>> = MutableStateFlow(emptyList())
    val mensajes: StateFlow<List<Mensaje>> = _mensajes.asStateFlow()

    private val _estado: MutableStateFlow<String> = MutableStateFlow("desconectado")
    val estado: StateFlow<String> = _estado.asStateFlow()

    private val _servidor: MutableStateFlow<String> = MutableStateFlow(Preferencias.servidor(app))
    val servidor: StateFlow<String> = _servidor.asStateFlow()

    private val _usandoTelegram: MutableStateFlow<Boolean> = MutableStateFlow(false)
    val usandoTelegram: StateFlow<Boolean> = _usandoTelegram.asStateFlow()

    private val _tgEstado: MutableStateFlow<String> = MutableStateFlow("apagado")
    val tgEstado: StateFlow<String> = _tgEstado.asStateFlow()

    /** "" | "telefono" | "codigo" | "clave" */
    private val _tgRequiere: MutableStateFlow<String> = MutableStateFlow("")
    val tgRequiere: StateFlow<String> = _tgRequiere.asStateFlow()

    /** true mientras JARVIS esta trabajando en un pedido (antes de responder). */
    private val _trabajando: MutableStateFlow<Boolean> = MutableStateFlow(false)
    val trabajando: StateFlow<Boolean> = _trabajando.asStateFlow()

    /** Imagenes a pintar en el chat (19.0): (rol, rutaLocal, id). */
    private val _imagenes: MutableStateFlow<List<Triple<String, String, Long>>> = MutableStateFlow(emptyList())
    val imagenes: StateFlow<List<Triple<String, String, Long>>> = _imagenes.asStateFlow()

    private val _apiIdTxt: MutableStateFlow<String> =
        MutableStateFlow(if (Preferencias.apiId(app) > 0) Preferencias.apiId(app).toString() else "")
    val apiIdTxt: StateFlow<String> = _apiIdTxt.asStateFlow()

    private val _apiHashTxt: MutableStateFlow<String> = MutableStateFlow(Preferencias.apiHash(app))
    val apiHashTxt: StateFlow<String> = _apiHashTxt.asStateFlow()

    private val _botTxt: MutableStateFlow<String> = MutableStateFlow(Preferencias.botUsuario(app))
    val botTxt: StateFlow<String> = _botTxt.asStateFlow()

    /** Telefono guardado (orden del jefe 04/10/2026, panel de acceso). */
    private val _telefonoTxt: MutableStateFlow<String> = MutableStateFlow(Preferencias.telefono(app))
    val telefonoTxt: StateFlow<String> = _telefonoTxt.asStateFlow()

    private val cliente = JarvisClient(
        onMensaje = { txt: String ->
            // OJO: recibir una respuesta NO termina el trabajo (el combo manda
            // varias). El estado "trabajando" se apaga solo con el "fin".
            _mensajes.value = _mensajes.value + Mensaje("jarvis", txt)
        },
        onEstado = { e: String -> if (!_usandoTelegram.value) _estado.value = e },
        onFin = { _trabajando.value = false },
        onEstadoProgreso = { txt ->
            // Progreso en vivo del combo: se muestra como linea de estado.
            _mensajes.value = _mensajes.value + Mensaje("sistema", txt)
        }
    )

    // SESION UNICA de la app (orden 04/10/2026): el ViewModel NO crea su propio
    // TDLib; usa el compartido con el servicio de fondo (AsistenteService).
    private val telegram = TelegramManager.obtener(app)

    /** Ultimos mensajes traidos del chat al abrir: recargan la pantalla. */
    val recarga = telegram.recarga

    init {
        viewModelScope.launch {
            telegram.estado.collect { _tgEstado.value = it }
        }
        viewModelScope.launch {
            telegram.requiere.collect { _tgRequiere.value = it }
        }
        viewModelScope.launch {
            var vistos = 0
            telegram.mensajes.collect { lista ->
                while (vistos < lista.size) {
                    val par = lista[vistos]
                    if (par.first == "jarvis") {
                        // OJO: recibir un mensaje NO apaga "trabajando"; eso lo
                        // hace el sello [[JARVIS:FIN]] (el combo manda varias).
                        _mensajes.value = _mensajes.value + Mensaje("jarvis", par.second)
                    }
                    vistos++
                }
            }
        }
        // SELLOS invisibles del bot (04/10/2026): encienden/apagan el estado
        // "Trabajando" y atienden el boton rojo, sin mostrarse en el chat.
        viewModelScope.launch {
            telegram.sello.collect { s ->
                when (s) {
                    "trabajando" -> _trabajando.value = true
                    "fin" -> _trabajando.value = false
                    "interrumpir" -> _trabajando.value = false
                }
            }
        }
        // RECUPERACION TRAS CORTE (04/10/2026): los mensajes releidos del chat
        // al volver la conexion se pintan en orden, sin duplicar.
        viewModelScope.launch {
            var n = 0
            telegram.nuevos.collect { lista ->
                while (n < lista.size) {
                    val item = lista[n]
                    _mensajes.value = _mensajes.value +
                        Mensaje(if (item.rol == "jefe") "jefe" else "jarvis", item.texto, item.fecha)
                    n++
                }
            }
        }
        // IMAGENES EN EL CHAT (19.0): las fotos que llegan o se envian se pintan
        // como burbuja de imagen. Se reenvian a la interfaz por el flujo _imagenes.
        viewModelScope.launch {
            var n = 0
            telegram.imagenes.collect { lista ->
                while (n < lista.size) {
                    val item = lista[n]
                    _imagenes.value = _imagenes.value +
                        Triple(if (item.first == "jefe") "jefe" else "jarvis", item.second, item.third)
                    n++
                }
            }
        }
        val id = Preferencias.apiId(app)
        val hash = Preferencias.apiHash(app)
        if (id > 0 && hash.isNotBlank()) {
            _usandoTelegram.value = true
            // Arranque en hilo de fondo (fix ANR 20.0): loadLibrary + init de
            // TDLib bloquean; en el hilo de UI congelaban la app al abrir.
            viewModelScope.launch(Dispatchers.IO) {
                telegram.arrancar(id, hash, Preferencias.botUsuario(app), Preferencias.telefono(app))
            }
        }
    }

    fun conectar() {
        cliente.conectar(_servidor.value)
    }

    /** Al volver la app a primer plano: trae lo que falte del chat (04/10/2026). */
    fun resincronizar() {
        if (_usandoTelegram.value) telegram.recargarChat()
    }

    fun reconectar() {
        conectar()
    }

    /** Boton rojo: interrumpe el trabajo del combo (orden 04/10/2026).
     *
     * Por Telegram se manda el SELLO [[JARVIS:INTERRUMPIR]] como un mensaje mas:
     * el bot lo intercepta ANTES de pasarselo al combo (igual que su boton
     * Interrumpir) y frena el proceso. El combo nunca lo ve.
     */
    fun interrumpir() {
        if (_usandoTelegram.value) {
            telegram.enviar(TelegramManager.SELLO_INTERRUMPIR)
        } else {
            cliente.interrumpir()
        }
        _trabajando.value = false
    }

    /** Reiniciar JARVIS desde la app (orden 05/10/2026): manda el SELLO de
     *  reinicio; el bot lo intercepta y reinicia de forma quirurgica. */
    fun reiniciarJarvis() {
        if (_usandoTelegram.value) telegram.enviar(TelegramManager.SELLO_REINICIAR)
    }

    fun guardarServidor(valor: String) {
        val v: String = valor.trim()
        _servidor.value = v
        Preferencias.guardarServidor(getApplication(), v)
        _usandoTelegram.value = false
        conectar()
    }

    fun configurarTelegram(id: String, hash: String, bot: String) {
        val n: Int = id.trim().toIntOrNull() ?: 0
        val h: String = hash.trim()
        val b: String = bot.trim().ifBlank { Preferencias.BOT_DEFECTO }
        _apiIdTxt.value = if (n > 0) n.toString() else ""
        _apiHashTxt.value = h
        _botTxt.value = b
        Preferencias.guardarTelegram(getApplication(), n, h, b)
        if (n > 0 && h.isNotBlank()) {
            _usandoTelegram.value = true
            _mensajes.value = _mensajes.value + Mensaje("sistema", "Conectando con Telegram...")
            // Arranque en hilo de fondo (fix ANR 20.0): loadLibrary + init bloquean.
            viewModelScope.launch(Dispatchers.IO) {
                try { telegram.cerrar() } catch (_: Throwable) { }
                telegram.arrancar(n, h, b, _telefonoTxt.value)
            }
        }
    }

    /**
     * ACCESO A TELEGRAM DE UNA SOLA VEZ (orden del jefe 04/10/2026).
     * Recibe telefono + api_id + api_hash + bot, los GUARDA todos y arranca el
     * acceso. Telegram solo pedira despues el codigo (y la clave de 2 pasos si
     * el jefe la tiene): esos pasos se contestan desde la caja del chat.
     */
    fun accesoTelegram(telefono: String, apiId: String, apiHash: String, bot: String): Boolean {
        val tel: String = telefono.trim()
        val n: Int = apiId.trim().toIntOrNull() ?: 0
        val h: String = apiHash.trim()
        val b: String = bot.trim().ifBlank { Preferencias.BOT_DEFECTO }
        _telefonoTxt.value = tel
        _apiIdTxt.value = if (n > 0) n.toString() else ""
        _apiHashTxt.value = h
        _botTxt.value = b
        Preferencias.guardarTelefono(getApplication(), tel)
        Preferencias.guardarTelegram(getApplication(), n, h, b)
        if (tel.isBlank() || n <= 0 || h.isBlank()) return false
        // Fix 20.1 (04/10/2026): NO se cierra el cliente. Si TDLib ya esta vivo
        // (arranco al abrir la app), solo se le manda el telefono; si no hay
        // cliente, arranca. Antes se cerraba y reabria -> carrera que dejaba a
        // TDLib mudo (ni pedia codigo ni daba acceso).
        _usandoTelegram.value = true
        _mensajes.value = _mensajes.value + Mensaje("sistema", "Conectando con Telegram...")
        viewModelScope.launch(Dispatchers.IO) {
            try {
                if (telegram.vivo()) telegram.enviarTelefono(tel)
                else telegram.arrancar(n, h, b, tel)
            } catch (_: Throwable) { }
        }
        return true
    }

    fun enviarTelefono(t: String) = telegram.enviarTelefono(t)

    /**
     * El jefe adjunto una imagen o un documento: se manda por Telegram (TDLib).
     * La imagen va como FOTO; el resto, como DOCUMENTO (orden jefe 04/10/2026).
     */
    fun enviarArchivo(ruta: String, esImagen: Boolean, nombre: String) {
        if (!_usandoTelegram.value) {
            _mensajes.value = _mensajes.value +
                Mensaje("sistema", "Adjuntos: solo funcionan por Telegram.")
            return
        }
        // La imagen se pinta como burbuja (19.0); el documento, como linea con nombre.
        if (esImagen) {
            _imagenes.value = _imagenes.value + Triple("jefe", ruta, 0L)
        } else {
            _mensajes.value = _mensajes.value + Mensaje("jefe", "📎 $nombre")
        }
        _trabajando.value = true
        telegram.enviarArchivo(ruta, esImagen)
    }

    fun enviarCodigo(c: String) = telegram.enviarCodigo(c)

    fun enviarClave(p: String) = telegram.enviarClave(p)

    fun enviar(texto: String) {
        val t: String = texto.trim()
        if (t.isEmpty()) return
        _mensajes.value = _mensajes.value + Mensaje("jefe", t)
        _trabajando.value = true
        val ok: Boolean =
            if (_usandoTelegram.value) telegram.enviar(t) else cliente.enviarTexto(t)
        if (!ok) {
            _trabajando.value = false
            _mensajes.value = _mensajes.value +
                Mensaje("sistema", "No estoy conectado. Revisa Ajustes.")
        }
    }

    override fun onCleared() {
        // SIN servicio de fondo (version 23.0, orden del jefe 05/10/2026): la
        // sesion de Telegram vive solo mientras la app esta abierta; al cerrarla
        // se cierra tambien para no dejar nada corriendo por detras.
        cliente.desconectar()
        try { telegram.cerrar() } catch (_: Throwable) { }
        super.onCleared()
    }
}
