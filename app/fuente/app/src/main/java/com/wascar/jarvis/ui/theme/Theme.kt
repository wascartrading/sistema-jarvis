package com.wascar.jarvis.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Tema NATIVO de JARVIS — paleta del ESTILO 1 (widget JARVIS-HRZ).
// Fondo #061a2c -> #010a12, acento cian (0,255,255), burbujas azul-verde.
private val Esquema = darkColorScheme(
    primary = Color(0xFF00FFFF),
    onPrimary = Color(0xFF001E22),
    secondary = Color(0xFF7DE8FF),
    onSecondary = Color(0xFF00252B),
    background = Color(0xFF04121F),
    onBackground = Color(0xFFEBF5FF),
    surface = Color(0xFF071C2E),
    onSurface = Color(0xFFEBF5FF),
    surfaceVariant = Color(0xFF0A2236),
    onSurfaceVariant = Color(0xFF9FC2D8),
    outline = Color(0xFF16405C)
)

@Composable
fun JarvisTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = Esquema, content = content)
}
