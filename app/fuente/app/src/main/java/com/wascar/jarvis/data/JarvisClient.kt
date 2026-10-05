package com.wascar.jarvis.data

import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * Cliente del puente de JARVIS.
 *
 * Habla el MISMO protocolo WebSocket JSON del servidor de la PC
 * (jarvis_movil/servidor.py):  envia  {"tipo":"texto","texto":...}
 * y recibe {"tipo":"respuesta","texto":...}. Asi la app nativa reemplaza
 * al WebView sin tocar el cerebro del otro lado.
 */
class JarvisClient(
    private val onMensaje: (String) -> Unit,
    private val onEstado: (String) -> Unit,
    private val onFin: () -> Unit = {},
    private val onEstadoProgreso: (String) -> Unit = {}
) {
    private val http = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)   // WebSocket: sin timeout de lectura
        .pingInterval(25, TimeUnit.SECONDS)
        .build()

    @Volatile private var ws: WebSocket? = null

    fun conectar(host: String) {
        desconectar()
        val limpio = host.trim()
            .removePrefix("http://").removePrefix("https://")
            .removePrefix("ws://").removePrefix("wss://")
            .trimEnd('/')
        if (limpio.isEmpty()) { onEstado("sin direccion"); return }
        val url = "ws://$limpio/ws"
        onEstado("conectando...")
        val peticion = Request.Builder().url(url).build()
        ws = http.newWebSocket(peticion, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                onEstado("en linea")
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                try {
                    val o = JSONObject(text)
                    when (o.optString("tipo")) {
                        "respuesta" -> {
                            val t = o.optString("texto")
                            if (t.isNotBlank()) onMensaje(t)
                        }
                        "respuesta_imagen" -> {
                            // La app nativa aun no pinta imagenes del puente: se
                            // muestra al menos el aviso para no perder el dato.
                            val t = o.optString("texto")
                            if (t.isNotBlank()) onMensaje(t)
                        }
                        "estado" -> {
                            // Progreso en vivo (cola, pensando, etc.). NO termina.
                            val t = o.optString("texto")
                            if (t.isNotBlank()) onEstadoProgreso(t)
                        }
                        "fin" -> {
                            // El trabajo del combo TERMINO de verdad (orden 04/10/2026).
                            onFin()
                        }
                    }
                } catch (_: Exception) { /* mensaje no-JSON: se ignora */ }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                onEstado("sin conexion")
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                onEstado("desconectado")
            }
        })
    }

    fun enviarTexto(texto: String): Boolean {
        val w = ws ?: return false
        return try {
            w.send(JSONObject().put("tipo", "texto").put("texto", texto).toString())
        } catch (_: Exception) {
            false
        }
    }

    /** Pide al combo que se detenga (boton rojo de la app, orden 04/10/2026). */
    fun interrumpir(): Boolean {
        val w = ws ?: return false
        return try {
            w.send(JSONObject().put("tipo", "interrumpir").toString())
        } catch (_: Exception) {
            false
        }
    }

    fun desconectar() {
        try { ws?.close(1000, null) } catch (_: Exception) { }
        ws = null
    }
}
