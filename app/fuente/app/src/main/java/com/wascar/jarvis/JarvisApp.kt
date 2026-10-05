package com.wascar.jarvis

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import com.wascar.jarvis.data.Preferencias

/**
 * Aplicacion JARVIS (orden del jefe 04/10/2026).
 *
 * Crea los CANALES de notificacion al arrancar el proceso, porque los usan
 * tanto el servicio de fondo (A) como los avisos de mensajes (B). Es el punto
 * comun donde vive todo lo que debe durar mas que una pantalla.
 */
class JarvisApp : Application() {

    override fun onCreate() {
        super.onCreate()
        crearCanales()
    }

    private fun crearCanales() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val nm = getSystemService(NotificationManager::class.java) ?: return

            // Canal del SERVICIO (baja importancia: solo mantiene JARVIS vivo).
            val servicio = NotificationChannel(
                CANAL_SERVICIO,
                "JARVIS en línea",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Mantiene la conexión de JARVIS activa en segundo plano."
                setShowBadge(false)
            }
            nm.createNotificationChannel(servicio)

            // Canal de MENSAJES (importancia alta: avisa cuando JARVIS responde).
            val mensajes = NotificationChannel(
                CANAL_MENSAJES,
                "Mensajes de JARVIS",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Avisos de los mensajes de JARVIS cuando la app está cerrada."
                enableVibration(true)
            }
            nm.createNotificationChannel(mensajes)
        }
    }

    companion object {
        const val CANAL_SERVICIO = "jarvis_servicio"
        const val CANAL_MENSAJES = "jarvis_mensajes"

        /** true cuando la app esta en pantalla (no avisar de lo que ya se ve). */
        @Volatile var enPrimerPlano = false

        /**
         * Aviso de mensaje (orden del jefe 05/10/2026): SILENCIADO por defecto;
         * solo se muestra si el jefe activo los avisos en Ajustes y la app NO
         * esta en primer plano.
         */
        fun avisar(ctx: Context, texto: String) {
            try {
                if (!Preferencias.notificaciones(ctx)) return
                if (enPrimerPlano) return
                if (Build.VERSION.SDK_INT >= 33 &&
                    ctx.checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) !=
                    android.content.pm.PackageManager.PERMISSION_GRANTED
                ) return
                val nm = ctx.getSystemService(NotificationManager::class.java) ?: return
                val n = androidx.core.app.NotificationCompat.Builder(ctx, CANAL_MENSAJES)
                    .setSmallIcon(android.R.drawable.stat_notify_chat)
                    .setContentTitle("JARVIS")
                    .setContentText(texto.take(140))
                    .setStyle(
                        androidx.core.app.NotificationCompat.BigTextStyle().bigText(texto.take(400))
                    )
                    .setAutoCancel(true)
                    .setPriority(androidx.core.app.NotificationCompat.PRIORITY_DEFAULT)
                    .build()
                nm.notify((System.currentTimeMillis() % 100000).toInt(), n)
            } catch (_: Throwable) { }
        }
    }
}
