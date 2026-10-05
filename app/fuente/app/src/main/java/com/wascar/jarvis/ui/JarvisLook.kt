package com.wascar.jarvis.ui

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt
import kotlin.random.Random

/**
 * ESTILO 1 — el ADN visual del JARVIS-HRZ / widget, reconstruido en Compose
 * (orden del jefe 04/10/2026). Sin WebView: puro dibujo nativo.
 *
 *  - Esfera de partículas (espiral de Fibonacci) que gira y "respira".
 *  - Onda de barras suavizada (26 barras) tipo medidor de voz.
 *  - Paleta cian sobre azul profundo.
 */

// Cian "reactor" — el --jc del widget.
val Cian = Color(0xFF00FFFF)
val CianSuave = Color(0xFF7DE8FF)

/** Estado visual para la esfera/onda/borde. */
enum class Fase { INACTIVO, ESCUCHANDO, PROCESANDO, RESPONDIENDO }

/** Colores base del fondo (gradiente del #app del widget). */
fun fondoArriba(): Color = Color(0xFF061A2C)
fun fondoAbajo(): Color = Color(0xFF010A12)

// ---------------------------------------------------------------------------
// ESFERA
// ---------------------------------------------------------------------------

private data class Particula(val x: Float, val y: Float, val z: Float, val r: Float, val f: Float)

private fun crearParticulas(n: Int, radio: Float): List<Particula> {
    val aureo = PI * (3.0 - sqrt(5.0))
    val list = ArrayList<Particula>(n)
    for (i in 0 until n) {
        val y = 1.0 - (i / (n - 1).toDouble()) * 2.0            // +1 -> -1
        val rr = sqrt((1.0 - y * y).coerceAtLeast(0.0))
        val th = aureo * i
        list.add(
            Particula(
                x = (radio * cos(th) * rr).toFloat(),
                y = (radio * y).toFloat(),
                z = (radio * sin(th) * rr).toFloat(),
                r = 0.5f + Random.nextFloat() * 0.55f,
                f = Random.nextFloat() * (2f * PI.toFloat())
            )
        )
    }
    return list
}

/**
 * Esfera viva. `ladoDp` es el tamaño en dp del recuadro.
 * Gira y late; el color vive en cian.
 */
@Composable
fun EsferaJarvis(fase: Fase, modificador: Modifier = Modifier) {
    val transicion = rememberInfiniteTransition(label = "esfera")
    // Giro continuo.
    val giro by transicion.animateFloat(
        initialValue = 0f, targetValue = (2f * PI.toFloat()),
        animationSpec = infiniteRepeatable(tween(9000, easing = LinearEasing)),
        label = "giro"
    )
    // Respiración para "respirar" y procesando.
    val latido by transicion.animateFloat(
        initialValue = 0f, targetValue = 1f,
        animationSpec = infiniteRepeatable(tween(1400), RepeatMode.Reverse),
        label = "latido"
    )
    // Centelleo suave.
    val chispa by transicion.animateFloat(
        initialValue = 0f, targetValue = (2f * PI.toFloat()),
        animationSpec = infiniteRepeatable(tween(2600, easing = LinearEasing)),
        label = "chispa"
    )

    val particulas = remember { crearParticulas(78, 14.2f) }
    val activo = fase == Fase.RESPONDIENDO || fase == Fase.PROCESANDO
    val pulso = if (activo) latido else 0f
    val escala = 1f + pulso * 0.09f

    Canvas(modifier = modificador.fillMaxSize()) {
        val cx = size.width / 2f
        val cy = size.height / 2f
        val unidad = size.minDimension / 40f          // el widget usaba 40 px
        val haloR = 22f * unidad
        val base = if (activo) Cian else Cian.copy(alpha = 0.72f)

        // Halo radial.
        drawCircle(
            brush = Brush.radialGradient(
                colors = listOf(base.copy(alpha = 0.26f + pulso * 0.18f), Color.Transparent),
                center = Offset(cx, cy),
                radius = haloR
            ),
            radius = haloR,
            center = Offset(cx, cy)
        )

        // Órbita (anillo fino) — gira más rápido cuando responde.
        val velOrbita = if (fase == Fase.RESPONDIENDO) 1f else if (fase == Fase.PROCESANDO) 0.7f else 0.25f
        drawCircle(
            color = base.copy(alpha = 0.35f),
            radius = 17f * unidad,
            center = Offset(cx, cy),
            style = Stroke(width = 0.7f * unidad)
        )
        // Un tramo brillante de la órbita.
        val a = giro * (1f + velOrbita)
        drawArc(
            color = base.copy(alpha = 0.85f),
            startAngle = (a * 180f / PI.toFloat()) % 360f,
            sweepAngle = 60f,
            useCenter = false,
            topLeft = Offset(cx - 17f * unidad, cy - 17f * unidad),
            size = androidx.compose.ui.geometry.Size(34f * unidad, 34f * unidad),
            style = Stroke(width = 1.1f * unidad)
        )

        // Partículas.
        val sn = sin(giro)
        for (p in particulas) {
            // Rotamos sobre el eje Y.
            val xr = p.x * cos(giro.toDouble()).toFloat() + p.z * sin(giro.toDouble()).toFloat()
            val zr = -p.x * sin(giro.toDouble()).toFloat() + p.z * cos(giro.toDouble()).toFloat()
            // Perspectiva simple.
            val prof = 0.6f + 0.4f * ((zr / 14.2f) + 1f) / 2f
            val px = cx + xr * escala * unidad
            val py = cy + p.y * escala * unidad
            val centelleo = 0.55f + 0.45f * sin(chispa + p.f)
            val col = base.copy(alpha = (0.35f + 0.55f * centelleo) * prof)
            drawCircle(color = col, radius = p.r * unidad * (0.8f + 0.5f * prof), center = Offset(px, py))
        }

        // Núcleo.
        drawCircle(
            brush = Brush.radialGradient(
                colors = listOf(Color.White.copy(alpha = 0.85f), base.copy(alpha = 0.25f), Color.Transparent),
                center = Offset(cx, cy),
                radius = 5.5f * unidad
            ),
            radius = 5.5f * unidad,
            center = Offset(cx, cy)
        )
    }
}

// ---------------------------------------------------------------------------
// ONDA (medidor de barras)
// ---------------------------------------------------------------------------

/**
 * Onda de 26 barras centradas. `fase` decide la intensidad y el ritmo.
 */
@Composable
fun OndaJarvis(fase: Fase, modificador: Modifier = Modifier) {
    val transicion = rememberInfiniteTransition(label = "onda")
    val t by transicion.animateFloat(
        initialValue = 0f, targetValue = 1000f,
        animationSpec = infiniteRepeatable(tween(20000, easing = LinearEasing)),
        label = "t"
    )
    val n = 26
    val objetivo = remember { FloatArray(n) { 0f } }
    val actual = remember { FloatArray(n) { 0f } }
    val color = if (fase == Fase.RESPONDIENDO) Cian else CianSuave

    Canvas(modifier = modificador.fillMaxSize()) {
        val hablando = fase == Fase.RESPONDIENDO
        val pensando = fase == Fase.PROCESANDO
        val amp = when (fase) {
            Fase.RESPONDIENDO -> 1f
            Fase.PROCESANDO -> 0.55f
            Fase.ESCUCHANDO -> 0.35f
            Fase.INACTIVO -> 0.18f
        }
        val paso = (t / 60f).toInt()
        val anchoBarra = size.width / (n * 1.9f)
        val hueco = size.width / n
        val altoMax = size.height * 0.85f
        val altoMin = size.height * 0.08f

        for (i in 0 until n) {
            if (paso % 2 == 0 && i == paso % n) {
                val silaba = 0.35f + 0.65f * Math.abs(sin(t * 0.22f + i)).toFloat()
                objetivo[i] = (if (hablando) silaba else 0.35f + 0.65f * Random.nextFloat()) * amp
            }
            actual[i] += (objetivo[i] - actual[i]) * 0.18f
            val h = altoMin + (altoMax - altoMin) * actual[i]
            val x = hueco * i + (hueco - anchoBarra) / 2f
            val y = size.height / 2f - h / 2f
            drawRoundRect(
                color = color.copy(alpha = if (pensando) 0.95f else 0.75f),
                topLeft = Offset(x, y),
                size = androidx.compose.ui.geometry.Size(anchoBarra, h),
                cornerRadius = androidx.compose.ui.geometry.CornerRadius(anchoBarra / 2f, anchoBarra / 2f)
            )
        }
    }
}
