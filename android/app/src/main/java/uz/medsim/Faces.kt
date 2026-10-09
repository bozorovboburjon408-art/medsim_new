package uz.medsim

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.sin

/** Har bir bemorning o'z chizilgan yuzi (emoji o'rniga). */
enum class Look { BUVI, OTA, KELIN, QIZ, BABY }

fun lookOf(id: String) = when (id) {
    "buvi" -> Look.BUVI
    "bobo" -> Look.OTA
    "homilador" -> Look.KELIN
    "bola" -> Look.QIZ
    else -> Look.BABY
}

/**
 * Jonli yuz: ko'z pirpiraydi, [speaking] bo'lsa og'iz ochilib-yopiladi.
 * Fon (gradient doira) tashqarida beriladi, bu faqat yuzning o'zi.
 */
@Composable
fun PatientFace(patientId: String, modifier: Modifier = Modifier, speaking: Boolean = false, sad: Boolean = false) {
    val look = lookOf(patientId)
    val t = rememberInfiniteTransition(label = "face")
    val talk by t.animateFloat(0f, (2 * PI).toFloat(), infiniteRepeatable(tween(560, easing = LinearEasing)), label = "talk")
    val blinkPhase by t.animateFloat(0f, 1f, infiniteRepeatable(tween(3800, easing = LinearEasing)), label = "blink")
    val open = if (speaking) 0.30f + 0.70f * abs(sin(talk)) * (0.55f + 0.45f * abs(sin(talk * 2.3f))) else 0f
    val blink = if (blinkPhase > 0.955f) 0.12f else 1f
    Canvas(modifier) { drawFace(look, open, blink, sad) }
}

private fun shade(c: Color, k: Float) = Color(c.red * k, c.green * k, c.blue * k, c.alpha)

private fun DrawScope.drawFace(look: Look, open: Float, blink: Float, sad: Boolean) {
    val u = size.minDimension / 100f
    fun o(x: Float, y: Float) = Offset(x * u, y * u)
    fun sz(w: Float, h: Float) = Size(w * u, h * u)
    fun stroke(w: Float) = Stroke(w * u, cap = StrokeCap.Round)

    val elder = look == Look.BUVI || look == Look.OTA
    val skin = when (look) {
        Look.BUVI -> Color(0xFFEFC29A); Look.OTA -> Color(0xFFE2AE80); Look.KELIN -> Color(0xFFF4CBA4)
        Look.QIZ -> Color(0xFFF9D4B2); Look.BABY -> Color(0xFFFBD8BE)
    }
    val skinDark = shade(skin, 0.86f)
    val ink = Color(0xFF2A2230)
    val brown = Color(0xFF4B2E1F)

    // ── kiyim va bo'yin
    val cloth = when (look) {
        Look.BUVI -> Color(0xFF6D28D9); Look.OTA -> Color(0xFF1E3A5F); Look.KELIN -> Color(0xFFFFF4E6)
        Look.QIZ -> Color(0xFFF472B6); Look.BABY -> Color(0xFFFFFFFF)
    }
    drawRoundRect(skinDark, o(43f, 60f), sz(14f, 22f), CornerRadius(5f * u))
    drawOval(cloth, o(6f, 76f), sz(88f, 64f))
    if (look == Look.OTA) {  // yoqa
        drawArc(Color(0xFFF1F5F9), 20f, 140f, true, o(38f, 70f), sz(24f, 16f))
    }
    if (look == Look.BUVI) {  // yoqadagi zeb
        drawCircle(Color(0xFFFDE68A), 2.2f * u, o(50f, 82f))
    }

    // ── orqa soch / ro'mol
    when (look) {
        Look.BUVI -> drawOval(Color(0xFFDC2626), o(18f, 12f), sz(64f, 68f))
        Look.KELIN -> drawOval(Color(0xFF7DA7E8), o(18f, 12f), sz(64f, 70f))
        Look.QIZ -> {
            drawOval(brown, o(21f, 14f), sz(58f, 56f))
            drawOval(brown, o(7f, 40f), sz(17f, 32f))
            drawOval(brown, o(76f, 40f), sz(17f, 32f))
            drawCircle(Color(0xFFEC4899), 4.4f * u, o(17f, 40f))
            drawCircle(Color(0xFFEC4899), 4.4f * u, o(83f, 40f))
        }
        else -> {}
    }

    // ── quloqlar va bosh
    val bigHead = look == Look.BABY
    drawOval(skin, o(22.5f, 43f), sz(8f, 12f))
    drawOval(skin, o(69.5f, 43f), sz(8f, 12f))
    if (look == Look.OTA) {  // chakkadagi oqargan sochlar
        drawOval(Color(0xFFD1D5DB), o(24f, 34f), sz(7f, 16f))
        drawOval(Color(0xFFD1D5DB), o(69f, 34f), sz(7f, 16f))
    }
    if (bigHead) drawOval(skin, o(24f, 21f), sz(52f, 56f)) else drawOval(skin, o(27f, 24f), sz(46f, 50f))

    // ── bosh kiyimi / soch (old tomon)
    when (look) {
        Look.BUVI, Look.KELIN -> {
            val sc = if (look == Look.BUVI) Color(0xFFDC2626) else Color(0xFF7DA7E8)
            drawArc(sc, 180f, 180f, true, o(24.5f, 17f), sz(51f, 36f))
            drawArc(shade(sc, 0.78f), 188f, 164f, false, o(24.5f, 17f), sz(51f, 36f), style = stroke(1.6f))
            if (look == Look.BUVI) {
                val dots = listOf(34f to 27f, 50f to 22f, 66f to 27f, 27f to 44f, 73f to 44f, 24f to 58f, 76f to 58f)
                dots.forEach { (x, y) -> drawCircle(Color(0xFFFDE68A), 1.5f * u, o(x, y)) }
            } else {
                drawCircle(Color(0xFFDBEAFE), 1.5f * u, o(36f, 27f)); drawCircle(Color(0xFFDBEAFE), 1.5f * u, o(50f, 23f))
                drawCircle(Color(0xFFDBEAFE), 1.5f * u, o(64f, 27f))
            }
        }
        Look.OTA -> {  // do'ppi
            val cap = Color(0xFF111827)
            drawArc(cap, 180f, 180f, true, o(26f, 11f), sz(48f, 38f))
            drawRoundRect(cap, o(26f, 28f), sz(48f, 9f), CornerRadius(3f * u))
            listOf(34f, 42f, 50f, 58f, 66f).forEach { x ->
                val p = Path().apply {
                    moveTo(x * u, 30.2f * u); lineTo((x + 2.4f) * u, 32.5f * u); lineTo(x * u, 34.8f * u); lineTo((x - 2.4f) * u, 32.5f * u); close()
                }
                drawPath(p, Color(0xFFF8FAFC))
            }
            val big = Path().apply {
                moveTo(50f * u, 14f * u); lineTo(56f * u, 21f * u); lineTo(50f * u, 27f * u); lineTo(44f * u, 21f * u); close()
            }
            drawPath(big, Color(0xFFF8FAFC), style = stroke(1.1f))
        }
        Look.QIZ -> drawArc(brown, 180f, 180f, true, o(26f, 18f), sz(48f, 30f))
        Look.BABY -> {
            drawArc(Color(0xFF7C4A2D), 200f, 140f, false, o(44f, 14f), sz(12f, 12f), style = stroke(2f))
            drawCircle(Color(0xFF7C4A2D), 1.6f * u, o(56f, 20.5f))
        }
    }

    // ── ko'z qoshlari va ko'zlar
    val browColor = when (look) {
        Look.BUVI, Look.OTA -> Color(0xFFD1D5DB); else -> brown
    }
    val ey = if (bigHead) 51f else 49f
    listOf(40f, 60f).forEach { x ->
        drawArc(browColor, 205f, 130f, false, o(x - 4.5f, ey - 9f), sz(9f, 7f), style = stroke(if (elder) 1.8f else 1.5f))
        val w = if (elder) 4.6f else 5.8f
        val h = (if (elder) 5.6f else 7.4f) * blink
        if (blink < 0.5f) {
            drawLine(ink, o(x - 3f, ey), o(x + 3f, ey), 1.4f * u, StrokeCap.Round)
        } else {
            drawOval(ink, o(x - w / 2f, ey - h / 2f), sz(w, h))
            drawCircle(Color.White, 1.1f * u, o(x + 0.9f, ey - h * 0.22f))
        }
    }
    if (look == Look.BUVI) {  // ko'zoynak
        listOf(40f, 60f).forEach { x -> drawCircle(Color(0xFF475569), 7.6f * u, o(x, ey), style = stroke(1.2f)) }
        drawLine(Color(0xFF475569), o(47.6f, ey - 1f), o(52.4f, ey - 1f), 1.2f * u, StrokeCap.Round)
        drawLine(Color(0xFF475569), o(32.4f, ey - 1f), o(27.5f, ey - 3f), 1.2f * u, StrokeCap.Round)
        drawLine(Color(0xFF475569), o(67.6f, ey - 1f), o(72.5f, ey - 3f), 1.2f * u, StrokeCap.Round)
    }

    // ── yonoq, burun
    val cheek = Color(0xFFF87171).copy(alpha = if (look == Look.BABY || look == Look.QIZ) 0.38f else 0.24f)
    drawCircle(cheek, 5.4f * u, o(33.5f, ey + 9f))
    drawCircle(cheek, 5.4f * u, o(66.5f, ey + 9f))
    drawArc(skinDark, 20f, 140f, false, o(46.8f, ey + 3f), sz(6.4f, 5f), style = stroke(1.2f))
    if (elder) {  // ajinlar
        drawArc(skinDark.copy(alpha = 0.7f), 100f, 70f, false, o(33f, ey + 4f), sz(9f, 13f), style = stroke(1f))
        drawArc(skinDark.copy(alpha = 0.7f), 10f, 70f, false, o(58f, ey + 4f), sz(9f, 13f), style = stroke(1f))
    }

    // ── soqol va mo'ylov (ota)
    var my = 0f
    if (look == Look.OTA) {
        val white = Color(0xFFF3F4F6)
        drawArc(white, 0f, 180f, true, o(32f, 56f), sz(36f, 28f))
        drawOval(white, o(37.5f, ey + 5f), sz(12.5f, 5.6f))
        drawOval(white, o(50f, ey + 5f), sz(12.5f, 5.6f))
        my = 4f
    }

    // ── og'iz
    val mouthColor = Color(0xFFB4505A)
    val mouthY = ey + 9f + my
    if (open > 0.05f) {
        val h = 2.4f + 8.5f * open
        drawOval(Color(0xFF6B1F2A), o(44.2f, mouthY), sz(11.6f, h))
        drawOval(Color(0xFFE57373), o(46.2f, mouthY + h * 0.52f), sz(7.6f, h * 0.42f))
    } else if (sad) {
        drawArc(mouthColor, 205f, 130f, false, o(42f, mouthY + 3f), sz(16f, 9f), style = stroke(1.9f))
    } else {
        drawArc(mouthColor, 25f, 130f, false, o(42f, mouthY - 3f), sz(16f, 9f), style = stroke(1.9f))
    }
    if (sad) {  // ko'z yoshi
        drawOval(Color(0xFF93C5FD), o(36.5f, ey + 4f), sz(2.6f, 5f))
        drawOval(Color(0xFF93C5FD), o(63f, ey + 4f), sz(2.6f, 5f))
    }
}
