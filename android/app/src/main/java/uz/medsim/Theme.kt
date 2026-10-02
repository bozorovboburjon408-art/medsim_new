package uz.medsim

import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

val Ok = Color(0xFF15803D)
val Warn = Color(0xFFB45309)

private val Colors = lightColorScheme(
    primary = Color(0xFF0F766E),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFCCFBF1),
    onPrimaryContainer = Color(0xFF042F2E),
    secondary = Color(0xFF475569),
    background = Color(0xFFF3F7F6),
    onBackground = Color(0xFF0F172A),
    surface = Color.White,
    onSurface = Color(0xFF0F172A),
    surfaceVariant = Color(0xFFE4ECEA),
    onSurfaceVariant = Color(0xFF475569),
    error = Color(0xFFB91C1C),
    errorContainer = Color(0xFFFEE2E2),
)

@Composable
fun MedSimTheme(content: @Composable () -> Unit) = MaterialTheme(
    colorScheme = Colors,
    shapes = Shapes(
        small = RoundedCornerShape(12.dp),
        medium = RoundedCornerShape(20.dp),
        large = RoundedCornerShape(28.dp),
    ),
    content = content,
)
