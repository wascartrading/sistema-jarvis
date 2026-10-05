package com.wascar.jarvis.data

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.AudioTrack
import android.media.MediaRecorder
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * Canal Gemini Live (voz en tiempo real) — orden del jefe 04/10/2026.
 *
 * Habla DIRECTAMENTE con el WebSocket de Google:
 *   wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key=API_KEY
 *
 * Envia:  1) setup  2) audio PCM 16 kHz del microfono (realtimeInput)
 * Recibe: audio PCM 24 kHz de JARVIS + texto (serverContent).
 *
 * La clave y el modelo salen de Preferencias (los mismos del widget de la PC).
 * El microfono se captura en crudo y se emite; la respuesta se reproduce al
 * instante. Sin dependencias nuevas: OkHttp + AudioRecord + AudioTrack.
 */
class GeminiLive(
    private val apiKey: String,
    private val modelo: String = MODELO_DEFECTO,
    private val voz: String = VOZ_DEFECTO,
    private val systemPrompt: String = "",
    private val onEstado: (String) -> Unit = {},
    private val onTexto: (String) -> Unit = {},
) {
    companion object {
        const val MODELO_DEFECTO = "gemini-3.8-live"
        const val VOZ_DEFECTO = "Charon"
        private const val URL_BASE_REAL =
            "wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
        // Gemini Live: entrada 16 kHz mono PCM16; salida 24 kHz mono PCM16.
        const val ENTRADA_HZ = 16000
        const val SALIDA_HZ = 24000
    }

    private val alcance = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val http = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .pingInterval(20, TimeUnit.SECONDS)
        .build()

    @Volatile private var ws: WebSocket? = null
    @Volatile private var escuchando = false
    @Volatile private var mudo = false
    // Half-duplex (fix 04/10/2026): mientras el MODELO habla, no se manda el
    // micro; asi el audio de Gemini (que sale por el altavoz) no vuelve a
    // entrar por el microfono y NO se auto-interrumpe. Cuando termina el turno,
    // vuelve a escuchar. Es lo que arregla las "interrupciones constantes".
    @Volatile private var modeloHablando = false
    // Sello del ultimo audio del modelo: si pasa mas de 1.2 s sin audio nuevo,
    // se suelta el half-duplex (seguro contra un "turnComplete" perdido).
    @Volatile private var ultimoAudioModelo = 0L
    private var grabador: AudioRecord? = null
    private var reproductor: AudioTrack? = null
    private var jobMicro: Job? = null
    private var jobAudio: Job? = null

    fun iniciar() {
        if (ws != null) return
        onEstado("Conectando…")
        val url = "$URL_BASE_REAL?key=$apiKey"
        val peticion = Request.Builder().url(url).build()
        ws = http.newWebSocket(peticion, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                android.util.Log.d("JARVIS-LIVE", "WebSocket abierto, enviando setup")
                enviarSetup(webSocket)
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                android.util.Log.d("JARVIS-LIVE", "texto: " + text.take(200))
                procesarMensaje(text)
            }

            override fun onMessage(webSocket: WebSocket, bytes: okio.ByteString) {
                // El servidor de Live contesta en frames BINARIOS (JSON en UTF-8).
                val texto = bytes.utf8()
                android.util.Log.d("JARVIS-LIVE", "binario: " + texto.take(200))
                procesarMensaje(texto)
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                android.util.Log.e("JARVIS-LIVE", "FALLO: " + t.message + " code=" + response?.code)
                onEstado("Sin conexión")
                cerrarAudio()
                ws = null
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                cerrarAudio()
                ws = null
            }
        })
    }

    private fun enviarSetup(webSocket: WebSocket) {
        val setup = JSONObject().apply {
            put("setup", JSONObject().apply {
                put("model", "models/$modelo")
                put("generationConfig", JSONObject().apply {
                    put("responseModalities", org.json.JSONArray().put("AUDIO"))
                    put("speechConfig", JSONObject().apply {
                        put("voiceConfig", JSONObject().apply {
                            put("prebuiltVoiceConfig", JSONObject().apply {
                                put("voiceName", voz)
                            })
                        })
                    })
                })
                if (systemPrompt.isNotBlank()) {
                    put("systemInstruction", JSONObject().apply {
                        put("parts", org.json.JSONArray().put(JSONObject().put("text", systemPrompt)))
                    })
                }
            })
        }
        webSocket.send(setup.toString())
    }

    private fun procesarMensaje(texto: String) {
        try {
            val o = JSONObject(texto)
            // "setupComplete" -> ya podemos escuchar y hablar.
            if (o.has("setupComplete")) {
                onEstado("En llamada")
                arrancarAudio()
            }
            // Respuesta del modelo: audio y/o texto.
            val sc = o.optJSONObject("serverContent")
            if (sc != null) {
                val modelo = sc.optJSONObject("modelTurn")
                val partes = modelo?.optJSONArray("parts")
                if (partes != null) {
                    for (i in 0 until partes.length()) {
                        val p = partes.getJSONObject(i)
                        val t = p.optString("text", "")
                        if (t.isNotBlank()) onTexto(t)
                        val inline = p.optJSONObject("inlineData")
                        val b64 = inline?.optString("data", "")
                        if (!b64.isNullOrBlank()) {
                            modeloHablando = true
                            ultimoAudioModelo = System.currentTimeMillis()
                            reproducirBase64(b64)
                        }
                    }
                }
                if (sc.optBoolean("turnComplete", false)) {
                    modeloHablando = false
                    onEstado("En llamada")
                }
                if (sc.optBoolean("interrupted", false)) {
                    // El jefe habló encima: se vacía lo pendiente.
                    modeloHablando = false
                    reproductor?.flush()
                }
            }
        } catch (_: Throwable) { }
    }

    // ------------------------------------------------------------- Audio ----
    @SuppressLint("MissingPermission")
    private fun arrancarAudio() {
        if (escuchando) return
        escuchando = true
        abrirReproductor()
        jobMicro = alcance.launch { bucleMicro() }
    }

    private fun abrirReproductor() {
        if (reproductor != null) return
        try {
            val minBuf = AudioTrack.getMinBufferSize(
                SALIDA_HZ, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_16BIT
            )
            val tam = if (minBuf > 0) minBuf * 2 else 8192
            val track = AudioTrack.Builder()
                .setAudioAttributes(
                    android.media.AudioAttributes.Builder()
                        .setUsage(android.media.AudioAttributes.USAGE_MEDIA)
                        .setContentType(android.media.AudioAttributes.CONTENT_TYPE_SPEECH)
                        .build()
                )
                .setAudioFormat(
                    AudioFormat.Builder()
                        .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                        .setSampleRate(SALIDA_HZ)
                        .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                        .build()
                )
                .setBufferSizeInBytes(tam)
                .setTransferMode(AudioTrack.MODE_STREAM)
                .build()
            track.play()
            reproductor = track
        } catch (_: Throwable) { }
    }

    @SuppressLint("MissingPermission")
    private fun bucleMicro() {
        val minBuf = AudioRecord.getMinBufferSize(
            ENTRADA_HZ, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT
        )
        val tam = if (minBuf > 0) minBuf else 4096
        val rec = try {
            AudioRecord(
                MediaRecorder.AudioSource.VOICE_COMMUNICATION,
                ENTRADA_HZ, AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT, tam * 2
            )
        } catch (_: Throwable) { null }
        if (rec == null || rec.state != AudioRecord.STATE_INITIALIZED) {
            onEstado("Sin micrófono")
            return
        }
        grabador = rec
        rec.startRecording()
        val buf = ByteArray(tam)
        while (escuchando) {
            val leidos = try { rec.read(buf, 0, buf.size) } catch (_: Throwable) { -1 }
            // Half-duplex (fix 04/10/2026): no mandar micro mientras el modelo
            // habla -> evita que su propia voz entre por el altavoz y lo corte.
            // Seguro: si llevo >1.2 s sin audio del modelo, suelto el estado
            // (por si el "turnComplete" se perdio) para no quedarme sordo.
            if (modeloHablando &&
                (System.currentTimeMillis() - ultimoAudioModelo) > 1200L) {
                modeloHablando = false
            }
            if (leidos > 0 && !mudo && !modeloHablando) {
                enviarAudio(buf, leidos)
            }
        }
        try { rec.stop() } catch (_: Throwable) { }
        try { rec.release() } catch (_: Throwable) { }
        grabador = null
    }

    private fun enviarAudio(buf: ByteArray, len: Int) {
        val w = ws ?: return
        try {
            val b64 = android.util.Base64.encodeToString(
                buf, 0, len, android.util.Base64.NO_WRAP
            )
            // FIX 04/10/2026 (probado de verdad contra la API): el Live moderno
            // espera realtimeInput.audio {mimeType, data}. El formato viejo
            // mediaChunks[] era IGNORADO por el servidor -> Gemini nunca oia.
            val msg = JSONObject().apply {
                put("realtimeInput", JSONObject().apply {
                    put("audio", JSONObject().apply {
                        put("mimeType", "audio/pcm;rate=$ENTRADA_HZ")
                        put("data", b64)
                    })
                })
            }
            w.send(msg.toString())
        } catch (_: Throwable) { }
    }

    private fun reproducirBase64(b64: String) {
        val track = reproductor ?: return
        try {
            val datos = android.util.Base64.decode(b64, android.util.Base64.DEFAULT)
            track.write(datos, 0, datos.size)
        } catch (_: Throwable) { }
    }

    /** Manda un texto como si lo hubiera dicho el jefe (util para el chat). */
    fun enviarTexto(texto: String) {
        val w = ws ?: return
        try {
            val msg = JSONObject().apply {
                put("clientContent", JSONObject().apply {
                    put("turns", org.json.JSONArray().put(JSONObject().apply {
                        put("role", "user")
                        put("parts", org.json.JSONArray().put(JSONObject().put("text", texto)))
                    }))
                    put("turnComplete", true)
                })
            }
            w.send(msg.toString())
        } catch (_: Throwable) { }
    }

    fun setMudo(m: Boolean) { mudo = m }

    fun cerrar() {
        escuchando = false
        try { jobMicro?.cancel() } catch (_: Throwable) { }
        try { ws?.close(1000, null) } catch (_: Throwable) { }
        cerrarAudio()
        try { alcance.cancel() } catch (_: Throwable) { }
        ws = null
    }

    private fun cerrarAudio() {
        try { reproductor?.stop() } catch (_: Throwable) { }
        try { reproductor?.release() } catch (_: Throwable) { }
        reproductor = null
    }
}
