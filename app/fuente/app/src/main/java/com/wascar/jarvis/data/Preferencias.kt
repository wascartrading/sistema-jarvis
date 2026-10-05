package com.wascar.jarvis.data

import android.content.Context

/** Ajustes persistentes de la app (puente y credenciales de Telegram). */
object Preferencias {
    private const val ARCHIVO = "jarvis_app"
    private const val K_SERVIDOR = "servidor"
    private const val K_APIID = "api_id"
    private const val K_APIHASH = "api_hash"
    private const val K_BOT = "bot_usuario"
    private const val K_GEMINI = "gemini_api_key"
    private const val K_LIVE_MODELO = "live_modelo"
    private const val K_LIVE_VOZ = "live_voz"

    // Valor por defecto del puente WebSocket: la PC del jefe en la red de casa.
    const val SERVIDOR_DEFECTO = "192.168.100.2:8090"
    const val BOT_DEFECTO = "jarvis_asistent_kilo_bot"

    // Credenciales de la app de Telegram del jefe (my.telegram.org, 04/10/2026).
    // Uso privado del senor Wascar; se puede cambiar desde Ajustes.
    const val API_ID_DEFECTO = 36846359
    const val API_HASH_DEFECTO = "8af3fc4adb26e5e3afe067bd331fa0cc"

    private fun prefs(ctx: Context) =
        ctx.getSharedPreferences(ARCHIVO, Context.MODE_PRIVATE)

    fun servidor(ctx: Context): String =
        prefs(ctx).getString(K_SERVIDOR, SERVIDOR_DEFECTO) ?: SERVIDOR_DEFECTO

    fun guardarServidor(ctx: Context, valor: String) {
        prefs(ctx).edit().putString(K_SERVIDOR, valor).apply()
    }

    fun apiId(ctx: Context): Int = prefs(ctx).getInt(K_APIID, API_ID_DEFECTO)

    fun apiHash(ctx: Context): String =
        prefs(ctx).getString(K_APIHASH, API_HASH_DEFECTO) ?: API_HASH_DEFECTO

    fun botUsuario(ctx: Context): String = prefs(ctx).getString(K_BOT, BOT_DEFECTO) ?: BOT_DEFECTO

    fun guardarTelegram(ctx: Context, apiId: Int, apiHash: String, bot: String) {
        prefs(ctx).edit()
            .putInt(K_APIID, apiId)
            .putString(K_APIHASH, apiHash)
            .putString(K_BOT, bot)
            .apply()
    }

    // --- Panel de acceso (orden del jefe 04/10/2026) ---
    private const val K_TELEFONO = "telefono"
    private const val K_ACCESO_HECHO = "acceso_hecho"

    /** Teléfono (con país) que el jefe introdujo en el panel de acceso. */
    fun telefono(ctx: Context): String = prefs(ctx).getString(K_TELEFONO, "") ?: ""

    fun guardarTelefono(ctx: Context, valor: String) {
        prefs(ctx).edit().putString(K_TELEFONO, valor.trim()).apply()
    }

    /** true cuando el acceso ya se completo (sesion de Telegram lista). */
    fun accesoHecho(ctx: Context): Boolean = prefs(ctx).getBoolean(K_ACCESO_HECHO, false)

    fun marcarAccesoHecho(ctx: Context, valor: Boolean) {
        prefs(ctx).edit().putBoolean(K_ACCESO_HECHO, valor).apply()
    }

    // --- Exencion de bateria (fix 05/10/2026) ---
    private const val K_BATERIA_PEDIDA = "bateria_pedida"

    /** true si ya se le pidio la exencion de bateria (se pide UNA sola vez). */
    fun bateriaPedida(ctx: Context): Boolean = prefs(ctx).getBoolean(K_BATERIA_PEDIDA, false)

    fun marcarBateriaPedida(ctx: Context, valor: Boolean) {
        prefs(ctx).edit().putBoolean(K_BATERIA_PEDIDA, valor).apply()
    }

    // --- Notificaciones (orden del jefe 05/10/2026) ---
    private const val K_NOTIF = "notificaciones"

    /** true = la app puede mostrar avisos. Por defecto, SILENCIADAS (false). */
    fun notificaciones(ctx: Context): Boolean = prefs(ctx).getBoolean(K_NOTIF, false)

    fun guardarNotificaciones(ctx: Context, valor: Boolean) {
        prefs(ctx).edit().putBoolean(K_NOTIF, valor).apply()
    }

    // --- Gemini Live (voz de la llamada, orden 04/10/2026) ---

    /** Clave de Gemini usada por la llamada de voz. Por SEGURIDAD no se guarda
     *  en el repositorio: escribala en Ajustes de la app (o rellene aqui la suya
     *  antes de compilar). Sin clave, la llamada de voz queda pidiendo la clave. */
    const val GEMINI_DEFECTO = ""

    fun geminiKey(ctx: Context): String =
        prefs(ctx).getString(K_GEMINI, GEMINI_DEFECTO) ?: GEMINI_DEFECTO

    fun guardarGeminiKey(ctx: Context, valor: String) {
        prefs(ctx).edit().putString(K_GEMINI, valor.trim()).apply()
    }

    fun liveModelo(ctx: Context): String =
        prefs(ctx).getString(K_LIVE_MODELO, GeminiLive.MODELO_DEFECTO)
            ?: GeminiLive.MODELO_DEFECTO

    fun liveVoz(ctx: Context): String =
        prefs(ctx).getString(K_LIVE_VOZ, GeminiLive.VOZ_DEFECTO) ?: GeminiLive.VOZ_DEFECTO

    fun guardarLive(ctx: Context, modelo: String, voz: String) {
        prefs(ctx).edit()
            .putString(K_LIVE_MODELO, modelo.trim())
            .putString(K_LIVE_VOZ, voz.trim())
            .apply()
    }
}
