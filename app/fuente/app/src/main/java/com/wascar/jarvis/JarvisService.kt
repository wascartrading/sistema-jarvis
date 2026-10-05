package com.wascar.jarvis

import android.app.Notification
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.wascar.jarvis.data.Preferencias
import com.wascar.jarvis.data.TelegramManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

/**
 * SERVICIO DE FONDO DE JARVIS (orden del jefe 04/10/2026) — solucion A + B.
 *
 * A) MANTIENE LA SESION VIVA: arranca TDLib en un servicio en primer plano, de
 *    modo que el proceso NO muere al cerrar la app. Al reabrir, la sesion ya
 *    esta conectada -> la app entra en 1-2 s (antes tardaba ~30 s porque TDLib
 *    arrancaba de cero cada vez).
 *
 * B) AVISA DE LOS MENSAJES: cuando llega un mensaje de JARVIS y la app NO esta
 *    en primer plano, lanza una NOTIFICACION (con el texto), para que el jefe
 *    se entere sin abrir la app.
 *
 * La notificacion persistente ("JARVIS en linea") es la que le dice al sistema
 * operativo que el servicio es importante y no debe matarlo.
 */
class JarvisService : Service() {

    private val alcance = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private lateinit var telegram: TelegramManager

    /** true mientras la app esta en primer plano (para no avisar de mensajes). */
    @Volatile private var appEnPrimerPlano = false

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        telegram = TelegramManager.obtener(this)
        arrancarForeground()
        engancharFlujos()
        arrancarTdlibSiHaceFalta()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        // Si el servicio se reinicia solo (START_STICKY), recuerda el estado.
        if (intent?.action == ACCION_APP_PRIMER_PLANO) {
            appEnPrimerPlano = true
        } else if (intent?.action == ACCION_APP_SEGUNDO_PLANO) {
            appEnPrimerPlano = false
        }
        arrancarTdlibSiHaceFalta()
        return START_STICKY
    }

    /** Arranca TDLib si aun no esta vivo (idempotente). */
    private fun arrancarTdlibSiHaceFalta() {
        val id = Preferencias.apiId(this)
        val hash = Preferencias.apiHash(this)
        if (id > 0 && hash.isNotBlank() && !telegram.vivo()) {
            alcance.launch {
                telegram.arrancar(id, hash, Preferencias.botUsuario(this@JarvisService), Preferencias.telefono(this@JarvisService))
            }
        }
    }

    /** Escucha los mensajes y el estado para actualizar la notificacion. */
    private fun engancharFlujos() {
        // Cada mensaje nuevo de JARVIS -> notificacion (solo si la app no esta
        // delante; si el jefe esta mirando el chat, no hace falta avisar).
        alcance.launch {
            var n = telegram.mensajes.value.size
            telegram.mensajes.collect { lista ->
                while (n < lista.size) {
                    val (rol, texto) = lista[n]
                    if (rol == "jarvis" && !appEnPrimerPlano) {
                        notificarMensaje(texto)
                    }
                    n++
                }
            }
        }
        // El estado de la sesion se refleja en la notificacion del servicio.
        alcance.launch {
            telegram.estado.collect { _ ->
                actualizarNotificacionServicio()
            }
        }
    }

    private fun destino(): PendingIntent {
        val i = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val flags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M)
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        else PendingIntent.FLAG_UPDATE_CURRENT
        return PendingIntent.getActivity(this, 0, i, flags)
    }

    /** Notificacion PERSISTENTE del servicio (la que mantiene JARVIS vivo). */
    private fun arrancarForeground() {
        val n = NotificationCompat.Builder(this, JarvisApp.CANAL_SERVICIO)
            .setContentTitle("JARVIS en línea")
            .setContentText("Conectado a Telegram · listo para ayudarte")
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .setContentIntent(destino())
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
        startForeground(ID_SERVICIO, n)
    }

    private fun actualizarNotificacionServicio() {
        val listo = telegram.estado.value.contains("en linea") || telegram.estado.value.contains("listo")
        val texto = if (listo) "Conectado a Telegram · listo para ayudarte" else "Conectando con Telegram…"
        val n = NotificationCompat.Builder(this, JarvisApp.CANAL_SERVICIO)
            .setContentTitle("JARVIS en línea")
            .setContentText(texto)
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .setContentIntent(destino())
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
        val nm = getSystemService(android.app.NotificationManager::class.java)
        nm?.notify(ID_SERVICIO, n)
    }

    /** Notificacion de un mensaje concreto de JARVIS (solucion B). */
    private fun notificarMensaje(texto: String) {
        val corto = if (texto.length > 120) texto.take(120) + "…" else texto
        val n = NotificationCompat.Builder(this, JarvisApp.CANAL_MENSAJES)
            .setContentTitle("JARVIS")
            .setContentText(corto)
            .setStyle(NotificationCompat.BigTextStyle().bigText(texto))
            .setSmallIcon(android.R.drawable.stat_notify_chat)
            .setContentIntent(destino())
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .build()
        val nm = getSystemService(android.app.NotificationManager::class.java)
        nm?.notify(ID_MENSAJE_BASE + (System.currentTimeMillis() % 1000).toInt(), n)
    }

    override fun onDestroy() {
        alcance.cancel()
        super.onDestroy()
    }

    companion object {
        const val ACCION_APP_PRIMER_PLANO = "com.wascar.jarvis.PRIMER_PLANO"
        const val ACCION_APP_SEGUNDO_PLANO = "com.wascar.jarvis.SEGUNDO_PLANO"
        private const val ID_SERVICIO = 1001
        private const val ID_MENSAJE_BASE = 2000

        fun iniciar(ctx: Context) {
            val i = Intent(ctx, JarvisService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) ctx.startForegroundService(i)
            else ctx.startService(i)
        }

        fun avisarPrimerPlano(ctx: Context) { enviarAccion(ctx, ACCION_APP_PRIMER_PLANO) }
        fun avisarSegundoPlano(ctx: Context) { enviarAccion(ctx, ACCION_APP_SEGUNDO_PLANO) }

        private fun enviarAccion(ctx: Context, accion: String) {
            try {
                val i = Intent(ctx, JarvisService::class.java).setAction(accion)
                ctx.startService(i)
            } catch (_: Throwable) { }
        }
    }
}
