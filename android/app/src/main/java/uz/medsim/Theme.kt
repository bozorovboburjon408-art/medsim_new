package uz.medsim

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

val Ok = Color(0xFF16A34A)
val Warn = Color(0xFFD97706)

// Asosiy brend ranglari (yashil-moviy, tibbiy, tinch)
val Brand = Color(0xFF0F766E)
val BrandDark = Color(0xFF115E59)
val BrandLight = Color(0xFF2DD4BF)
val Danger = Color(0xFFDC2626)
val DangerDark = Color(0xFF991B1B)

private val LightColors = lightColorScheme(
    primary = Brand,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFD3F4EE),
    onPrimaryContainer = Color(0xFF053B35),
    secondary = Color(0xFF475569),
    secondaryContainer = Color(0xFFE2E8F0),
    tertiary = Color(0xFFD97706),
    tertiaryContainer = Color(0xFFFEF0C7),
    background = Color(0xFFF2F8F7),
    onBackground = Color(0xFF0B1F1E),
    surface = Color.White,
    onSurface = Color(0xFF0F172A),
    surfaceVariant = Color(0xFFE4EEEC),
    onSurfaceVariant = Color(0xFF4B5C5A),
    outline = Color(0xFFB7C9C6),
    error = Danger,
    errorContainer = Color(0xFFFEE2E2),
    onErrorContainer = Color(0xFF7F1D1D),
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFF2DD4BF),
    onPrimary = Color(0xFF042F2B),
    primaryContainer = Color(0xFF134E48),
    onPrimaryContainer = Color(0xFFCFF7F0),
    secondary = Color(0xFF94A3B8),
    secondaryContainer = Color(0xFF334155),
    tertiary = Color(0xFFFBBF24),
    tertiaryContainer = Color(0xFF5B3A06),
    background = Color(0xFF0B1514),
    onBackground = Color(0xFFE6F2F0),
    surface = Color(0xFF14201F),
    onSurface = Color(0xFFE6F2F0),
    surfaceVariant = Color(0xFF22322F),
    onSurfaceVariant = Color(0xFFA7BBB8),
    outline = Color(0xFF3F5552),
    error = Color(0xFFF87171),
    errorContainer = Color(0xFF4C1D1D),
    onErrorContainer = Color(0xFFFECACA),
)

@Composable
fun MedSimTheme(content: @Composable () -> Unit) = MaterialTheme(
    colorScheme = if (isSystemInDarkTheme()) DarkColors else LightColors,
    shapes = Shapes(
        extraSmall = RoundedCornerShape(8.dp),
        small = RoundedCornerShape(14.dp),
        medium = RoundedCornerShape(20.dp),
        large = RoundedCornerShape(28.dp),
        extraLarge = RoundedCornerShape(36.dp),
    ),
    content = content,
)

/** Butun ilova foni: tepada yengil yashil nur, pastga qarab tekis. */
@Composable
fun appBackgroundBrush(): Brush {
    val cs = MaterialTheme.colorScheme
    return Brush.verticalGradient(listOf(cs.primaryContainer.copy(alpha = 0.55f), cs.background, cs.background))
}
