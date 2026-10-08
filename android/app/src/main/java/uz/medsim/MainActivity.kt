package uz.medsim

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.DialogProperties
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.math.sqrt

data class PatientInfo(
    val id: String, val name: String, val subtitle: String, val emoji: String, val isBaby: Boolean = false,
    val tag: String = "", val c1: Color = Brand, val c2: Color = BrandLight,
)

val PATIENTS = listOf(
    PatientInfo("buvi", "Salomat buvi", "75 yosh · 2-tip qandli diabet", "👵", tag = "Qandli diabet", c1 = Color(0xFFF59E0B), c2 = Color(0xFFEA580C)),
    PatientInfo("homilador", "Nilufar opa", "33 yosh · 32 haftalik homiladorlik", "🤰", tag = "Homiladorlik", c1 = Color(0xFFF472B6), c2 = Color(0xFFBE185D)),
    PatientInfo("bola", "Madinaxon", "5 yosh · qizaloq, gijja kasalligi", "👧", tag = "Bolalar", c1 = Color(0xFF38BDF8), c2 = Color(0xFF4F46E5)),
    PatientInfo("bobo", "Hikmatilla ota", "78 yosh · yoshga doir skrining", "👴", tag = "Skrining", c1 = Color(0xFF2DD4BF), c2 = Color(0xFF0F766E)),
    PatientInfo("chaqaloq", "Chaqaloq", "Yig'laydi, tebratilsa tinchiydi", "👶", isBaby = true, tag = "Maniken", c1 = Color(0xFFA78BFA), c2 = Color(0xFF7C3AED)),
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO, Manifest.permission.BLUETOOTH_CONNECT), 1)
        setContent {
            MedSimTheme {
                Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    Box(Modifier.fillMaxSize().background(appBackgroundBrush())) { App() }
                }
            }
        }
    }
}

private const val DEFAULT_SERVER = "https://medsim-backend-oyfd.onrender.com"
private const val DEFAULT_ESP_BABY_URL = "http://10.186.157.233"

@Composable
fun App() {
    val ctx = LocalContext.current
    val prefs = remember { ctx.getSharedPreferences("medsim", Context.MODE_PRIVATE) }
    val savedServer = prefs.getString("server", null)
    var server by remember { mutableStateOf(if (savedServer.isNullOrBlank()) DEFAULT_SERVER else savedServer) }
    var model by remember { mutableStateOf(prefs.getString("model", "") ?: "") }
    var tts by remember { mutableStateOf("eleven") }  // ovoz qotirilgan: ElevenLabs (xato bo'lsa server o'zi Edge'ga o'tadi)

    val savedBaby = prefs.getString("esp_baby_url", null)
    val initialBaby = if (savedBaby.isNullOrBlank() || savedBaby == "http://medsim-baby.local") DEFAULT_ESP_BABY_URL else savedBaby
    var espBabyUrl by remember { mutableStateOf(initialBaby) }
    var showSettings by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        val ed = prefs.edit()
        var changed = false
        if (savedServer.isNullOrBlank()) { ed.putString("server", DEFAULT_SERVER); changed = true }
        if (savedBaby.isNullOrBlank() || savedBaby == "http://medsim-baby.local") { ed.putString("esp_baby_url", DEFAULT_ESP_BABY_URL); changed = true }
        if (changed) ed.apply()
    }
    var current by remember { mutableStateOf<PatientInfo?>(null) }
    // manikenga biriktirilgan kalonka: patient.id -> AudioDeviceInfo.id
    val speakers = remember { mutableStateMapOf<String, Int>() }

    // Server holati: 0 noma'lum, 1 tayyor, 2 uyg'onmoqda, 3 aloqa yo'q. Ilova ochiq turganda server uxlamaydi.
    var serverState by remember { mutableStateOf(0) }
    LaunchedEffect(server) {
        if (server.isBlank()) { serverState = 0; return@LaunchedEffect }
        while (true) {
            serverState = 2
            val ok = Api.health(server)
            serverState = if (ok) 1 else 3
            delay(if (ok) 8 * 60 * 1000L else 20 * 1000L)
        }
    }

    val p = current
    if (p == null) {
        HomeScreen(speakers, serverState, onPick = { current = it }, onSettings = { showSettings = true })
    } else {
        val picker: @Composable () -> Unit = { SpeakerPicker(speakers[p.id]) { speakers[p.id] = it } }
        val back = { Speaker.stop(); current = null }
        if (p.isBaby) BabyScreen(p, espBabyUrl, speakers[p.id], back, picker)
        else ChatScreen(p, server, model, tts, speakers[p.id], back, picker)
    }
    if (showSettings) SettingsDialog(server, model, tts, espBabyUrl, onDismiss = { showSettings = false }) { srv, mdl, tt, esp ->
        server = srv.trim(); model = mdl; tts = tt; espBabyUrl = esp.trim()
        prefs.edit().putString("server", server).putString("model", model).putString("tts", tts)
            .putString("esp_baby_url", espBabyUrl).apply(); showSettings = false
    }
}

// ───────────────────────── Kichik umumiy qismlar ─────────────────────────

@Composable
fun Avatar(p: PatientInfo, size: Dp) {
    Box(
        Modifier.size(size).clip(CircleShape).background(Brush.linearGradient(listOf(p.c1, p.c2))),
        contentAlignment = Alignment.Center,
    ) { Text(p.emoji, fontSize = (size.value * 0.5f).sp) }
}

@Composable
fun RoundButton(label: String, onClick: () -> Unit, size: Dp = 42.dp) {
    Box(
        Modifier.size(size).clip(CircleShape).background(MaterialTheme.colorScheme.surfaceVariant).clickable(onClick = onClick),
        contentAlignment = Alignment.Center,
    ) { Text(label, fontSize = 20.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface) }
}

@Composable
fun StatusPill(serverState: Int) {
    val (text, color) = when (serverState) {
        1 -> "Server tayyor" to Ok
        2 -> "Server uyg'onmoqda…" to Warn
        3 -> "Aloqa yo'q" to MaterialTheme.colorScheme.error
        else -> return
    }
    Row(
        Modifier.clip(CircleShape).background(color.copy(alpha = 0.12f)).padding(horizontal = 12.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(Modifier.size(8.dp).clip(CircleShape).background(color))
        Spacer(Modifier.width(7.dp))
        Text(text, style = MaterialTheme.typography.labelLarge, color = color, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
fun SpeakingBars(color: Color) {
    val t = rememberInfiniteTransition(label = "bars")
    Row(Modifier.height(22.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(3.dp)) {
        listOf(420, 560, 360, 500, 440).forEach { d ->
            val h by t.animateFloat(0.25f, 1f, infiniteRepeatable(tween(d), RepeatMode.Reverse), label = "b$d")
            Box(Modifier.width(4.dp).height((22f * h).dp).clip(CircleShape).background(color))
        }
    }
}

// ───────────────────────── Bosh sahifa ─────────────────────────

@Composable
fun HomeScreen(speakers: Map<String, Int>, serverState: Int, onPick: (PatientInfo) -> Unit, onSettings: () -> Unit) {
    val ctx = LocalContext.current
    Column(Modifier.fillMaxSize().padding(horizontal = 20.dp).padding(top = 18.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                Modifier.size(46.dp).clip(RoundedCornerShape(15.dp)).background(Brush.linearGradient(listOf(Brand, BrandLight))),
                contentAlignment = Alignment.Center,
            ) { Text("M", color = Color.White, fontSize = 26.sp, fontWeight = FontWeight.ExtraBold) }
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text("MedSim", fontSize = 26.sp, fontWeight = FontWeight.ExtraBold, color = MaterialTheme.colorScheme.onBackground)
                Text("Patronaj hamshiralik simulyatori", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            RoundButton("⚙", onSettings, 44.dp)
        }
        Spacer(Modifier.height(14.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("Bemorni tanlang", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
            StatusPill(serverState)
        }
        Spacer(Modifier.height(14.dp))
        LazyVerticalGrid(
            GridCells.Adaptive(310.dp),
            horizontalArrangement = Arrangement.spacedBy(14.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
            contentPadding = PaddingValues(bottom = 24.dp),
        ) {
            items(PATIENTS) { p ->
                val dev = speakers[p.id]?.let { id -> Speaker.bluetoothDevices(ctx).firstOrNull { it.id == id }?.productName?.toString() }
                PatientCard(p, dev) { onPick(p) }
            }
        }
    }
}

@Composable
fun PatientCard(p: PatientInfo, speakerName: String?, onClick: () -> Unit) {
    Surface(
        Modifier.fillMaxWidth().shadow(4.dp, MaterialTheme.shapes.large, clip = false).clip(MaterialTheme.shapes.large).clickable(onClick = onClick),
        shape = MaterialTheme.shapes.large,
        color = MaterialTheme.colorScheme.surface,
    ) {
        Column {
            Box(Modifier.fillMaxWidth().height(6.dp).background(Brush.horizontalGradient(listOf(p.c1, p.c2))))
            Row(Modifier.padding(horizontal = 18.dp, vertical = 16.dp), verticalAlignment = Alignment.CenterVertically) {
                Avatar(p, 66.dp)
                Spacer(Modifier.width(16.dp))
                Column(Modifier.weight(1f)) {
                    Text(p.name, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text(p.subtitle, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Spacer(Modifier.height(8.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        if (p.tag.isNotEmpty()) Text(
                            p.tag, style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.SemiBold, color = p.c2,
                            modifier = Modifier.clip(CircleShape).background(p.c1.copy(alpha = 0.16f)).padding(horizontal = 10.dp, vertical = 4.dp),
                        )
                        if (speakerName != null) {
                            Spacer(Modifier.width(8.dp))
                            Text("🔊 $speakerName", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary, maxLines = 1, overflow = TextOverflow.Ellipsis)
                        }
                    }
                }
                Text("›", fontSize = 30.sp, color = MaterialTheme.colorScheme.outline)
            }
        }
    }
}

@Composable
fun SettingsDialog(server: String, model: String, tts: String, espBabyUrl: String, onDismiss: () -> Unit, onSave: (String, String, String, String) -> Unit) {
    var text by remember { mutableStateOf(server) }
    var mdl by remember { mutableStateOf(model) }
    var tt by remember { mutableStateOf(tts) }
    var esp by remember { mutableStateOf(espBabyUrl) }
    var result by remember { mutableStateOf("") }
    val scope = rememberCoroutineScope()
    AlertDialog(
        onDismissRequest = onDismiss,
        shape = MaterialTheme.shapes.large,
        title = { Text("Sozlamalar", fontWeight = FontWeight.Bold) },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState())) {
                OutlinedTextField(
                    text, { text = it }, label = { Text("Server manzili (Render)") },
                    placeholder = { Text("https://....onrender.com") }, singleLine = true, modifier = Modifier.fillMaxWidth(),
                    shape = MaterialTheme.shapes.small,
                )
                Spacer(Modifier.height(8.dp))
                OutlinedButton({
                    scope.launch {
                        result = "Tekshirilyapti… (server uxlayotgan bo'lsa 1 daqiqagacha)"
                        result = if (Api.health(text)) "✓ Server javob berdi" else "✗ Ulanib bo'lmadi. Manzilni tekshiring yoki qayta urinib ko'ring"
                    }
                }) { Text("Serverni tekshirish") }
                if (result.isNotEmpty()) {
                    Spacer(Modifier.height(6.dp))
                    Text(result, color = if (result.startsWith("✓")) Ok else MaterialTheme.colorScheme.onSurfaceVariant)
                }

                Spacer(Modifier.height(14.dp))
                OutlinedTextField(
                    esp, { esp = it }, label = { Text("Chaqaloq manikeni IP (ESP32)") },
                    placeholder = { Text("http://10.186.157.233") }, singleLine = true, modifier = Modifier.fillMaxWidth(),
                    shape = MaterialTheme.shapes.small,
                )
                Spacer(Modifier.height(8.dp))
                var espResult by remember { mutableStateOf("") }
                OutlinedButton({
                    scope.launch {
                        espResult = "Tekshirilyapti…"
                        val st = Api.getBabyStatus(esp)
                        espResult = if (st != null) "✓ Maniken ulandi: ${st.stateUz} (${st.holdingText})"
                                    else "✗ Maniken topilmadi. IP manzil va Wi-Fi ni tekshiring"
                    }
                }) { Text("Manikenni tekshirish") }
                if (espResult.isNotEmpty()) {
                    Spacer(Modifier.height(6.dp))
                    Text(espResult, color = if (espResult.startsWith("✓")) Ok else MaterialTheme.colorScheme.onSurfaceVariant)
                }

                Spacer(Modifier.height(14.dp))
                Text("AI modeli (sinov uchun)", style = MaterialTheme.typography.labelLarge)
                Row(Modifier.horizontalScroll(rememberScrollState())) {
                    listOf(
                        "" to "Avto",
                        "gemini-2.5-flash-lite" to "2.5 Flash-Lite",
                        "gemini-2.5-pro" to "2.5 Pro",
                        "gemini-2.5-flash" to "2.5 Flash",
                    ).forEach { (id, label) ->
                        FilterChip(mdl == id, { mdl = id }, { Text(label) }, modifier = Modifier.padding(end = 8.dp))
                    }
                }
            }
        },
        confirmButton = { Button({ onSave(text, mdl, tt, esp) }) { Text("Saqlash") } },
        dismissButton = { TextButton(onDismiss) { Text("Bekor qilish") } },
    )
}

// ───────────────────────── Ekran sarlavhasi ─────────────────────────

@Composable
fun ScreenHeader(p: PatientInfo, onBack: () -> Unit, picker: @Composable () -> Unit, trailing: @Composable RowScope.() -> Unit = {}) {
    var showSpeakers by remember { mutableStateOf(false) }
    Surface(
        color = MaterialTheme.colorScheme.surface, shadowElevation = 6.dp,
        shape = RoundedCornerShape(bottomStart = 28.dp, bottomEnd = 28.dp),
    ) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
            RoundButton("‹", onBack)
            Spacer(Modifier.width(10.dp))
            Avatar(p, 46.dp)
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(p.name, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(p.subtitle, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            Spacer(Modifier.width(8.dp))
            Box(
                Modifier.clip(CircleShape).background(MaterialTheme.colorScheme.primaryContainer)
                    .clickable { showSpeakers = true }.padding(horizontal = 12.dp, vertical = 8.dp),
            ) { Text("🔊", fontSize = 16.sp) }
            Spacer(Modifier.width(8.dp))
            trailing()
        }
    }
    if (showSpeakers) AlertDialog(
        onDismissRequest = { showSpeakers = false },
        shape = MaterialTheme.shapes.large,
        title = { Text("Kalonka tanlash", fontWeight = FontWeight.Bold) },
        text = { picker() },
        confirmButton = { TextButton({ showSpeakers = false }) { Text("Tayyor") } },
    )
}

@Composable
fun SpeakerPicker(selected: Int?, onPick: (Int) -> Unit) {
    val ctx = LocalContext.current
    var devices by remember { mutableStateOf(Speaker.bluetoothDevices(ctx)) }
    Column {
        Text(
            "Bemor ovozi shu kalonkadan chiqadi (har bemorga alohida).",
            style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.height(10.dp))
        if (devices.isEmpty()) Text(
            "Bluetooth kalonka ulanmagan. Ovoz telefon dinamigidan chiqadi.",
            style = MaterialTheme.typography.bodyMedium,
        )
        devices.forEach { d ->
            FilterChip(
                selected == d.id, { onPick(d.id) }, { Text(d.productName.toString()) },
                modifier = Modifier.fillMaxWidth().padding(bottom = 6.dp),
            )
        }
        TextButton({ devices = Speaker.bluetoothDevices(ctx) }) { Text("↻ Ro'yxatni yangilash") }
    }
}

// ───────────────────────── Bosib turib gapirish tugmasi ─────────────────────────

enum class Phase(val label: String) {
    IDLE("Bosib turing va gapiring"), LISTENING("Eshityapman… gapirib bo'lgach qo'yib yuboring"),
    THINKING("Bemor o'ylayapti…"), SPEAKING("Bemor gapirmoqda…")
}

@Composable
fun MicIcon(color: Color, modifier: Modifier = Modifier) {
    Canvas(modifier) {
        val w = size.width
        val h = size.height
        val sw = w * 0.075f
        drawRoundRect(color, Offset(w * 0.36f, h * 0.04f), Size(w * 0.28f, h * 0.52f), CornerRadius(w * 0.14f))
        drawArc(color, 0f, 180f, false, Offset(w * 0.21f, h * 0.27f), Size(w * 0.58f, h * 0.5f), style = Stroke(sw, cap = StrokeCap.Round))
        drawLine(color, Offset(w * 0.5f, h * 0.77f), Offset(w * 0.5f, h * 0.94f), sw, StrokeCap.Round)
        drawLine(color, Offset(w * 0.34f, h * 0.94f), Offset(w * 0.66f, h * 0.94f), sw, StrokeCap.Round)
    }
}

/** Bosib turilganda yoziladi, qo'yib yuborilganda xabar jo'natiladi. [level] 0..1: ovoz balandligiga qarab halqa kattalashadi. */
@Composable
fun HoldToTalkButton(phase: Phase, level: Float, onPress: () -> Unit, onRelease: () -> Unit) {
    val listening = phase == Phase.LISTENING
    val busy = phase == Phase.THINKING
    val pulse by rememberInfiniteTransition(label = "pulse").animateFloat(
        1f, 1.07f, infiniteRepeatable(tween(700), RepeatMode.Reverse), label = "p",
    )
    val lv by animateFloatAsState(level, tween(110), label = "lv")
    val grad = when {
        listening -> Brush.linearGradient(listOf(Color(0xFFEF4444), DangerDark))
        busy -> Brush.linearGradient(listOf(Color(0xFF94A3B8), Color(0xFF64748B)))
        else -> Brush.linearGradient(listOf(BrandLight, Brand))
    }
    val ringColor = if (listening) Danger else Brand
    val busyState by rememberUpdatedState(busy)
    val onPressState by rememberUpdatedState(onPress)
    val onReleaseState by rememberUpdatedState(onRelease)
    val scale = if (listening) 1f + 0.10f * lv else 1f
    Box(Modifier.size(156.dp), contentAlignment = Alignment.Center) {
        if (listening) {
            Box(Modifier.size((110f + 44f * lv).dp).clip(CircleShape).background(ringColor.copy(alpha = 0.16f)))
            Box(Modifier.size((110f + 18f * lv).dp * pulse).clip(CircleShape).background(ringColor.copy(alpha = 0.18f)))
        } else if (!busy) {
            Box(Modifier.size(124.dp * pulse).clip(CircleShape).background(ringColor.copy(alpha = 0.08f)))
        }
        Box(
            Modifier.size(104.dp)
                .graphicsLayer { scaleX = scale; scaleY = scale }
                .shadow(10.dp, CircleShape)
                .clip(CircleShape).background(grad)
                .pointerInput(Unit) {
                    awaitEachGesture {
                        awaitFirstDown(requireUnconsumed = false)
                        val active = !busyState
                        if (active) onPressState()
                        // barmoq tugmadan siljib chiqib ketsa ham bosilgan hisoblanadi; faqat butunlay ko'tarilganda tugaydi
                        do {
                            val event = awaitPointerEvent()
                        } while (event.changes.any { it.pressed })
                        if (active) onReleaseState()
                    }
                },
            contentAlignment = Alignment.Center,
        ) {
            if (busy) CircularProgressIndicator(Modifier.size(38.dp), color = Color.White, strokeWidth = 4.dp)
            else MicIcon(Color.White, Modifier.size(46.dp))
        }
    }
}

// ───────────────────────── Xabar pufakchalari ─────────────────────────

@Composable
fun Bubble(t: Turn, patient: PatientInfo) {
    val nurse = t.role == "user"
    Row(
        Modifier.fillMaxWidth(), verticalAlignment = Alignment.Bottom,
        horizontalArrangement = if (nurse) Arrangement.End else Arrangement.Start,
    ) {
        if (!nurse) { Avatar(patient, 32.dp); Spacer(Modifier.width(8.dp)) }
        Column(horizontalAlignment = if (nurse) Alignment.End else Alignment.Start, modifier = Modifier.weight(1f, fill = false)) {
            Text(
                if (nurse) "Siz (hamshira)" else patient.name,
                style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(horizontal = 6.dp, vertical = 3.dp),
            )
            val shape = RoundedCornerShape(
                topStart = 22.dp, topEnd = 22.dp, bottomStart = if (nurse) 22.dp else 6.dp, bottomEnd = if (nurse) 6.dp else 22.dp,
            )
            if (nurse) Box(Modifier.widthIn(max = 520.dp).clip(shape).background(Brush.linearGradient(listOf(Brand, BrandDark)))) {
                Text(t.content, Modifier.padding(horizontal = 16.dp, vertical = 12.dp), fontSize = 17.sp, color = Color.White)
            } else Surface(shape = shape, color = MaterialTheme.colorScheme.surface, shadowElevation = 2.dp, modifier = Modifier.widthIn(max = 520.dp)) {
                Text(t.content, Modifier.padding(horizontal = 16.dp, vertical = 12.dp), fontSize = 17.sp, color = MaterialTheme.colorScheme.onSurface)
            }
        }
    }
}

// ───────────────────────── Suhbat ─────────────────────────

@Composable
fun ChatScreen(p: PatientInfo, server: String, model: String, tts: String, deviceId: Int?, onBack: () -> Unit, picker: @Composable () -> Unit) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val history = remember(p.id) { mutableStateListOf<Turn>() }
    var phase by remember { mutableStateOf(Phase.IDLE) }
    var error by remember { mutableStateOf("") }
    var firstAudio by remember { mutableStateOf("") }
    var evaluating by remember { mutableStateOf(false) }
    var evalResult by remember { mutableStateOf<EvalResult?>(null) }
    var partial by remember { mutableStateOf("") }
    var level by remember { mutableStateOf(0f) }
    var showMenu by remember { mutableStateOf(false) }
    var showInfo by remember { mutableStateOf(false) }
    val listState = rememberLazyListState()
    LaunchedEffect(history.size) { if (history.isNotEmpty()) listState.animateScrollToItem(history.size - 1) }

    // Bosib turib gapirish holati
    val recRef = remember { arrayOfNulls<SpeechRecognizer>(1) }
    val buffer = remember { mutableListOf<String>() }
    val held = remember { booleanArrayOf(false) }
    val errStreak = remember { intArrayOf(0) }
    val pressedAt = remember { longArrayOf(0L) }
    val pendingUp = remember { arrayOfNulls<kotlinx.coroutines.Job>(1) }
    val gen = remember { intArrayOf(0) }  // har yangi savolda oshadi: eski javobning qolgan ovozi chalinmasin

    fun send(text: String) {
        if (server.isBlank()) { error = "Avval Sozlamalarda server manzilini kiriting"; phase = Phase.IDLE; return }
        history.add(Turn("user", text)); phase = Phase.THINKING; error = ""; firstAudio = ""
        val t0 = System.currentTimeMillis()
        val my = ++gen[0]
        scope.launch {
            val parts = mutableListOf<String>()
            var attempt = 0
            while (true) {
                try {
                    Speaker.beginStream(deviceId) { phase = Phase.IDLE }
                    Api.chatStream(server, p.id, history.toList(), model, tts) { seg ->
                        if (gen[0] != my) return@chatStream
                        if (parts.isEmpty() && seg.text.isNotEmpty()) {
                            firstAudio = "Birinchi ovozgacha: %.1f s\nAI %.1f s · ovoz %.1f s (%s)\n%s%s\n%s".format(
                                (System.currentTimeMillis() - t0) / 1000.0, seg.llmMs / 1000.0, seg.ttsMs / 1000.0, seg.tts,
                                seg.model, if (seg.tries.isNotEmpty()) "\n⚠ ${seg.tries}" else "", seg.usage,
                            )
                            phase = Phase.SPEAKING
                        }
                        if (seg.text.isNotEmpty()) parts.add(seg.text)
                        if (seg.pcmRate > 0) Speaker.writePcm(ctx, seg.mp3, seg.pcmRate)
                        else Speaker.enqueue(ctx, seg.mp3, seg.fmt)
                    }
                    if (gen[0] != my) break  // bemor gapi bo'linib, hamshira yangi savol berdi
                    if (parts.isNotEmpty()) history.add(Turn("assistant", parts.joinToString(" ")))
                    Speaker.endStream()
                    break
                } catch (e: Exception) {
                    if (gen[0] != my) break
                    Speaker.stop()
                    if (parts.isEmpty() && attempt == 0) {  // hech narsa kelmagan: bir marta o'zi qayta uriniladi
                        attempt++; phase = Phase.THINKING; error = ""
                        continue
                    }
                    phase = Phase.IDLE
                    val msg = e.message.orEmpty()
                    error = if (msg.contains("timeout", true) || msg.contains("timed out", true))
                        "Server javob bermadi (vaqt tugadi). Tugmani bosib qayta urinib ko'ring"
                    else "Xato: $msg"
                    break
                }
            }
        }
    }

    fun finish() {
        recRef[0]?.destroy(); recRef[0] = null
        val text = buffer.joinToString(" ").trim()
        buffer.clear(); partial = ""; level = 0f
        if (text.isBlank()) { phase = Phase.IDLE; error = "Eshitilmadi. Tugmani bosib turib, aniqroq gapiring" } else send(text)
    }

    fun startRec() {
        val rec = SpeechRecognizer.createSpeechRecognizer(ctx)
        recRef[0] = rec
        rec.setRecognitionListener(object : RecognitionListener {
            override fun onResults(b: Bundle?) {
                val t = b?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()
                rec.destroy(); if (recRef[0] === rec) recRef[0] = null
                if (!t.isNullOrBlank()) { buffer.add(t); errStreak[0] = 0 }
                partial = buffer.joinToString(" ")
                // tugma hali bosilgan bo'lsa, tanish to'xtab qolgan: yana davom etamiz (gap boshi yo'qolmaydi)
                if (held[0]) scope.launch { delay(120); if (held[0]) startRec() } else finish()
            }
            override fun onError(e: Int) {
                rec.destroy(); if (recRef[0] === rec) recRef[0] = null
                val soft = e == SpeechRecognizer.ERROR_NO_MATCH || e == SpeechRecognizer.ERROR_SPEECH_TIMEOUT
                if (held[0]) {
                    if (!soft) errStreak[0]++
                    if (errStreak[0] >= 4) {
                        held[0] = false; buffer.clear(); partial = ""; level = 0f
                        phase = Phase.IDLE; error = "Mikrofon ishlamadi (xato $e). Qayta urinib ko'ring"
                    } else scope.launch { delay(250); if (held[0]) startRec() }
                } else finish()
            }
            override fun onReadyForSpeech(p: Bundle?) {}
            override fun onBeginningOfSpeech() {}
            override fun onRmsChanged(v: Float) { level = ((v + 2f) / 12f).coerceIn(0f, 1f) }
            override fun onBufferReceived(b: ByteArray?) {}
            override fun onEndOfSpeech() {}
            override fun onPartialResults(b: Bundle?) {
                val t = b?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()
                if (!t.isNullOrBlank()) partial = (buffer + t).joinToString(" ")
            }
            override fun onEvent(t: Int, b: Bundle?) {}
        })
        rec.startListening(Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "uz-UZ")
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 10000L)
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 10000L)
        })
    }

    fun pressDown() {
        val pu = pendingUp[0]
        if (pu != null && pu.isActive) { pu.cancel(); pendingUp[0] = null; return }  // barmoq 0.35 s ichida qaytdi: bir xil bosish davom etadi
        if (ctx.checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            error = "Mikrofonga ruxsat bering (Sozlamalar → Ilovalar → MedSim)"; return
        }
        gen[0]++; Speaker.stop(); error = ""; buffer.clear(); partial = ""; errStreak[0] = 0
        held[0] = true; pressedAt[0] = System.currentTimeMillis(); phase = Phase.LISTENING
        startRec()
    }

    fun releaseNow() {
        if (!held[0]) return
        held[0] = false
        if (System.currentTimeMillis() - pressedAt[0] < 400 && buffer.isEmpty()) {  // tasodifan tegib ketdi
            recRef[0]?.destroy(); recRef[0] = null
            partial = ""; level = 0f; phase = Phase.IDLE; error = "Tugmani bosib turing va gapiring"
            return
        }
        val r = recRef[0]
        if (r != null) {
            r.stopListening()
            scope.launch { delay(3500); if (!held[0] && phase == Phase.LISTENING && recRef[0] != null) finish() }  // natija kelmasa
        } else finish()
    }

    fun pressUp() {
        if (!held[0]) return
        pendingUp[0]?.cancel()
        pendingUp[0] = scope.launch { delay(350); releaseNow() }  // qisqa uzilishlar (barmoq titrashi) e'tiborsiz qoldiriladi
    }

    DisposableEffect(p.id) { onDispose { pendingUp[0]?.cancel(); held[0] = false; recRef[0]?.destroy(); recRef[0] = null } }

    evalResult?.let { EvaluationDialog(it) { evalResult = null } }
    if (showInfo) AlertDialog(
        onDismissRequest = { showInfo = false }, shape = MaterialTheme.shapes.large,
        title = { Text("Texnik ma'lumot", fontWeight = FontWeight.Bold) },
        text = { Text(firstAudio.ifEmpty { "Hali javob olinmagan." }, style = MaterialTheme.typography.bodyMedium) },
        confirmButton = { TextButton({ showInfo = false }) { Text("Yopish") } },
    )

    Column(Modifier.fillMaxSize()) {
        val canEval = history.any { it.role == "user" } && phase == Phase.IDLE && !evaluating
        ScreenHeader(p, onBack, picker) {
            FilledTonalButton(
                {
                    evaluating = true; error = ""
                    scope.launch {
                        try { evalResult = Api.evaluate(server, p.id, history.toList(), model) }
                        catch (e: Exception) { error = "Baholash xatosi: ${e.message}" }
                        finally { evaluating = false }
                    }
                },
                enabled = canEval, contentPadding = PaddingValues(horizontal = 14.dp, vertical = 8.dp),
            ) {
                if (evaluating) CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp)
                else Text("📋 Baholash", fontWeight = FontWeight.SemiBold)
            }
            Spacer(Modifier.width(8.dp))
            Box {
                RoundButton("⋮", { showMenu = true })
                DropdownMenu(showMenu, { showMenu = false }) {
                    DropdownMenuItem(
                        text = { Text("Yangi suhbat") },
                        onClick = { showMenu = false; Speaker.stop(); history.clear(); phase = Phase.IDLE; error = ""; firstAudio = "" },
                    )
                    DropdownMenuItem(text = { Text("Texnik ma'lumot") }, onClick = { showMenu = false; showInfo = true })
                }
            }
        }

        val chatArea: @Composable (Modifier) -> Unit = { mod ->
            Box(mod, contentAlignment = Alignment.TopCenter) {
                Box(Modifier.widthIn(max = 820.dp).fillMaxSize()) {
                    if (history.isEmpty()) {
                        Column(
                            Modifier.fillMaxSize().padding(24.dp),
                            horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center,
                        ) {
                            Avatar(p, 84.dp)
                            Spacer(Modifier.height(14.dp))
                            Text("${p.name} bilan suhbat", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center)
                            Spacer(Modifier.height(8.dp))
                            Text(
                                "Mikrofon tugmasini bosib turing, gapiring va qo'yib yuboring.\nMasalan: «Assalomu alaykum, ahvollaringiz qanday?»",
                                textAlign = TextAlign.Center, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 16.sp,
                            )
                        }
                    } else {
                        LazyColumn(
                            state = listState, contentPadding = PaddingValues(horizontal = 16.dp, vertical = 18.dp),
                            verticalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxSize(),
                        ) { items(history) { Bubble(it, p) } }
                    }
                }
            }
        }

        // side = true: yotiq (past) ekranda panel o'ng tomonda, aks holda pastda
        val dock: @Composable (Boolean) -> Unit = { side ->
            Surface(
                if (side) Modifier.width(260.dp).fillMaxHeight() else Modifier.fillMaxWidth(),
                color = MaterialTheme.colorScheme.surface, shadowElevation = 14.dp,
                shape = if (side) RoundedCornerShape(topStart = 30.dp, bottomStart = 30.dp) else RoundedCornerShape(topStart = 30.dp, topEnd = 30.dp),
            ) {
                Column(
                    (if (side) Modifier.fillMaxSize() else Modifier.fillMaxWidth()).padding(start = 18.dp, end = 18.dp, top = 12.dp, bottom = 10.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center,
                ) {
                    // Doimiy balandlikdagi joy: matn/xato paydo bo'lganda tugma siljib ketmasin
                    Box(Modifier.fillMaxWidth().height(if (side) 78.dp else 62.dp), contentAlignment = Alignment.Center) {
                        if (error.isNotEmpty()) {
                            Surface(shape = MaterialTheme.shapes.small, color = MaterialTheme.colorScheme.errorContainer) {
                                Text(error, Modifier.padding(horizontal = 12.dp, vertical = 6.dp), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onErrorContainer, maxLines = 3, overflow = TextOverflow.Ellipsis)
                            }
                        } else if (phase == Phase.LISTENING && partial.isNotBlank()) {
                            Surface(shape = MaterialTheme.shapes.medium, color = MaterialTheme.colorScheme.surfaceVariant) {
                                Text(partial, Modifier.padding(horizontal = 12.dp, vertical = 6.dp), fontSize = 15.sp, maxLines = if (side) 3 else 2, overflow = TextOverflow.Ellipsis)
                            }
                        }
                    }
                    HoldToTalkButton(phase, level, onPress = { pressDown() }, onRelease = { pressUp() })
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        if (phase == Phase.SPEAKING) { SpeakingBars(MaterialTheme.colorScheme.primary); Spacer(Modifier.width(10.dp)) }
                        Text(
                            phase.label, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold, textAlign = TextAlign.Center,
                            color = if (phase == Phase.LISTENING) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        }

        BoxWithConstraints(Modifier.weight(1f).fillMaxWidth()) {
            if (maxHeight < 480.dp) Row(Modifier.fillMaxSize()) {
                chatArea(Modifier.weight(1f).fillMaxHeight())
                dock(true)
            } else Column(Modifier.fillMaxSize()) {
                chatArea(Modifier.weight(1f).fillMaxWidth())
                dock(false)
            }
        }
    }
}

// ───────────────────────── Baholash natijasi ─────────────────────────

@Composable
fun ScoreRing(total: Int, color: Color) {
    val track = MaterialTheme.colorScheme.surfaceVariant
    Box(Modifier.size(104.dp), contentAlignment = Alignment.Center) {
        Canvas(Modifier.fillMaxSize()) {
            val s = Stroke(width = 12.dp.toPx(), cap = StrokeCap.Round)
            val inset = 6.dp.toPx()
            val sz = Size(size.width - inset * 2, size.height - inset * 2)
            drawArc(track, -90f, 360f, false, Offset(inset, inset), sz, style = s)
            drawArc(color, -90f, 360f * (total.coerceIn(0, 100) / 100f), false, Offset(inset, inset), sz, style = s)
        }
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text("$total", fontSize = 34.sp, fontWeight = FontWeight.ExtraBold, color = color)
            Text("/ 100", fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
fun EvaluationDialog(r: EvalResult, onDismiss: () -> Unit) {
    val color = when { r.total >= 80 -> Ok; r.total >= 60 -> Warn; else -> MaterialTheme.colorScheme.error }
    AlertDialog(
        onDismissRequest = onDismiss,
        modifier = Modifier.fillMaxWidth(0.92f).widthIn(max = 720.dp),
        shape = MaterialTheme.shapes.large,
        properties = DialogProperties(usePlatformDefaultWidth = false),
        title = { Text("Baholash natijasi", fontWeight = FontWeight.Bold) },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState())) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    ScoreRing(r.total, color)
                    Spacer(Modifier.width(16.dp))
                    if (r.summary.isNotBlank()) Text(r.summary, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
                }
                r.stages.forEach { st ->
                    Spacer(Modifier.height(10.dp))
                    Surface(shape = MaterialTheme.shapes.medium, color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f)) {
                        Column(Modifier.fillMaxWidth().padding(14.dp)) {
                            Row {
                                Text(st.name, Modifier.weight(1f), fontWeight = FontWeight.SemiBold)
                                Text("${st.score}/${st.max}", fontWeight = FontWeight.Bold)
                            }
                            Spacer(Modifier.height(6.dp))
                            LinearProgressIndicator(
                                progress = st.score.toFloat() / st.max, color = if (st.score * 100 / st.max >= 60) Ok else Warn,
                                trackColor = MaterialTheme.colorScheme.surface, modifier = Modifier.fillMaxWidth().height(8.dp).clip(CircleShape),
                            )
                            Spacer(Modifier.height(4.dp))
                            st.done.forEach { Text("✓ $it", color = Ok, style = MaterialTheme.typography.bodyMedium) }
                            st.missed.forEach { Text("✗ $it", color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodyMedium) }
                        }
                    }
                }
                if (r.strengths.isNotEmpty()) {
                    Spacer(Modifier.height(16.dp)); Text("Kuchli tomonlar", fontWeight = FontWeight.Bold)
                    r.strengths.forEach { Text("• $it") }
                }
                if (r.advice.isNotEmpty()) {
                    Spacer(Modifier.height(12.dp)); Text("Yaxshilash uchun", fontWeight = FontWeight.Bold)
                    r.advice.forEach { Text("• $it") }
                }
            }
        },
        confirmButton = { Button(onDismiss) { Text("Yopish") } },
    )
}

// ───────────────────────── Chaqaloq ─────────────────────────

// Tebranish sozlamalari (m/s², chiziqli tezlanish RMS). Real manikenda sinab sozlanadi.
private const val ROCK_MIN = 0.5f
private const val SHAKE_MAX = 6.0f
private const val CALM_AFTER_MS = 4000L
private const val RESUME_AFTER_MS = 10000L
private const val SHAKE_AFTER_MS = 1000L

@Composable
fun BabyScreen(p: PatientInfo, espBabyUrl: String, deviceId: Int?, onBack: () -> Unit, picker: @Composable () -> Unit) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var msg by remember { mutableStateOf("Chaqaloq manikeni tekshirilmoqda…") }
    var auto by remember { mutableStateOf(true) }
    var crying by remember { mutableStateOf(false) }
    var laughing by remember { mutableStateOf(false) }
    var espStatus by remember { mutableStateOf<BabyStatus?>(null) }
    var isEspConnected by remember { mutableStateOf(false) }

    // Planshet ichki akselerometri (zaxira datchik)
    var rms by remember { mutableStateOf(0f) }
    var hasSensor by remember { mutableStateOf(true) }
    val level = remember { floatArrayOf(0f) }

    fun startCry() {
        if (laughing) {
            Speaker.stop()
            laughing = false
        }
        if (!crying) {
            crying = true
            Speaker.playAsset(ctx, "baby_cry.mp3", deviceId, loop = true)
        }
    }

    fun startLaugh() {
        if (crying) {
            Speaker.stop()
            crying = false
        }
        if (!laughing) {
            laughing = true
            Speaker.playAsset(ctx, "baby_laugh.m4a", deviceId, loop = true)
        }
    }

    fun stopAllSounds() {
        if (crying || laughing) {
            Speaker.stop()
            crying = false
            laughing = false
        }
    }

    // 1. ESP32 Maniken bilan real-vaqtda aloqa (Polling har 250ms)
    LaunchedEffect(espBabyUrl) {
        while (true) {
            val st = Api.getBabyStatus(espBabyUrl)
            if (st != null) {
                isEspConnected = true
                espStatus = st
                msg = when (st.state) {
                    "CRYING" -> "Chaqaloq yig'layapti! (${st.holdingText})"
                    "SOOTHING" -> "Ovunmoqda… (${st.soothingProgress}%)"
                    "LAUGHING" -> "Quvonib kulmoqda! 😄"
                    else -> "Chaqaloq tinch / xotirjam 😴"
                }
                if (auto) {
                    if (st.isCrying) {
                        startCry()
                    } else if (st.isLaughing || st.state == "LAUGHING") {
                        startLaugh()
                    } else if (crying || laughing) {
                        stopAllSounds()
                    }
                }
            } else {
                isEspConnected = false
            }
            delay(250)
        }
    }

    // 2. Agar ESP32 ulanmagan bo'lsa, planshetning o'zini tebratish datchigi ishlaydi (Fallback)
    DisposableEffect(Unit) {
        val sm = ctx.getSystemService(Context.SENSOR_SERVICE) as SensorManager
        val sensor = sm.getDefaultSensor(Sensor.TYPE_LINEAR_ACCELERATION)
        val l = object : SensorEventListener {
            override fun onSensorChanged(e: SensorEvent) {
                val a2 = e.values[0] * e.values[0] + e.values[1] * e.values[1] + e.values[2] * e.values[2]
                level[0] = level[0] * 0.98f + a2 * 0.02f
            }
            override fun onAccuracyChanged(s: Sensor?, a: Int) {}
        }
        if (sensor == null) hasSensor = false
        else sm.registerListener(l, sensor, SensorManager.SENSOR_DELAY_GAME)
        onDispose { sm.unregisterListener(l); stopAllSounds() }
    }

    LaunchedEffect(isEspConnected) {
        if (isEspConnected) return@LaunchedEffect
        var rockMs = 0L; var stillMs = 0L; var shakeMs = 0L
        val step = 200L
        while (true) {
            delay(step)
            val r = sqrt(level[0]); rms = r
            if (!auto || isEspConnected) continue
            val shaking = r > SHAKE_MAX
            val rocking = r in ROCK_MIN..SHAKE_MAX
            shakeMs = if (shaking) shakeMs + step else 0
            rockMs = if (rocking) rockMs + step else 0
            stillMs = if (r < ROCK_MIN) stillMs + step else 0
            when {
                shakeMs >= SHAKE_AFTER_MS -> {
                    startCry()
                    msg = "Qattiq silkitish! Chaqaloq yig'layapti"
                }
                crying && rockMs >= CALM_AFTER_MS -> {
                    stopAllSounds()
                    msg = "Chaqaloq tinchidi"
                }
                !crying && stillMs >= RESUME_AFTER_MS -> {
                    startCry()
                    msg = "Chaqaloq yana yig'layapti"
                }
            }
        }
    }

    val shake by rememberInfiniteTransition(label = "shake").animateFloat(
        -5f, 5f, infiniteRepeatable(tween(260), RepeatMode.Reverse), label = "s",
    )

    // Chaqaloq holati kartasi
    val statusContent: @Composable (Modifier) -> Unit = { mod ->
        Surface(
            mod, shape = MaterialTheme.shapes.large,
            color = when {
                crying -> MaterialTheme.colorScheme.errorContainer
                laughing -> MaterialTheme.colorScheme.tertiaryContainer
                else -> MaterialTheme.colorScheme.primaryContainer
            },
        ) {
            Column(Modifier.fillMaxWidth().padding(20.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                val emoji = when {
                    crying -> "😭"
                    espStatus?.isLaughing == true -> "😄"
                    espStatus?.state == "SOOTHING" -> "🥺"
                    else -> "👶"
                }
                Text(emoji, fontSize = 84.sp, modifier = Modifier.graphicsLayer { rotationZ = if (crying) shake else 0f })
                Spacer(Modifier.height(10.dp))
                Text(msg, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold, textAlign = TextAlign.Center)

                Spacer(Modifier.height(12.dp))
                Row(
                    Modifier.clip(CircleShape).background(MaterialTheme.colorScheme.surface.copy(alpha = 0.7f)).padding(horizontal = 12.dp, vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Box(Modifier.size(8.dp).clip(CircleShape).background(if (isEspConnected) Ok else MaterialTheme.colorScheme.outline))
                    Spacer(Modifier.width(7.dp))
                    Text(
                        if (isEspConnected) "Maniken ulangan (${espStatus?.holdingText ?: ""})"
                        else "Maniken ulanmagan · planshet datchigi",
                        style = MaterialTheme.typography.labelMedium,
                        color = if (isEspConnected) Ok else MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }

                if (isEspConnected && espStatus != null) {
                    Spacer(Modifier.height(14.dp))
                    Surface(
                        color = MaterialTheme.colorScheme.surface, shape = MaterialTheme.shapes.medium,
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Column(Modifier.padding(14.dp)) {
                            val isHazard = espStatus!!.shakeStatus == "VIOLENT" || espStatus!!.holdingStatus == "UPSIDE_DOWN"
                            if (isHazard) {
                                Surface(
                                    color = MaterialTheme.colorScheme.errorContainer,
                                    shape = RoundedCornerShape(10.dp),
                                    modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp),
                                ) {
                                    Text(
                                        "⚠️ ${if (espStatus!!.holdingStatus == "UPSIDE_DOWN") espStatus!!.holdingText else espStatus!!.shakeText}",
                                        color = MaterialTheme.colorScheme.onErrorContainer,
                                        style = MaterialTheme.typography.bodyMedium,
                                        fontWeight = FontWeight.Bold,
                                        modifier = Modifier.padding(10.dp),
                                    )
                                }
                            }

                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text("Ovunish progressi", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
                                Text("${espStatus!!.soothingProgress}%", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.primary)
                            }
                            LinearProgressIndicator(
                                progress = espStatus!!.soothingProgress / 100f,
                                modifier = Modifier.fillMaxWidth().padding(vertical = 5.dp).height(10.dp).clip(CircleShape),
                                color = MaterialTheme.colorScheme.primary,
                                trackColor = MaterialTheme.colorScheme.surfaceVariant,
                            )

                            if (espStatus!!.happyProgress > 0 || espStatus!!.isLaughing) {
                                Spacer(Modifier.height(6.dp))
                                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                    Text("Kulgi va quvonch", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
                                    Text("${espStatus!!.happyProgress}%", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.tertiary)
                                }
                                LinearProgressIndicator(
                                    progress = espStatus!!.happyProgress / 100f,
                                    modifier = Modifier.fillMaxWidth().padding(vertical = 5.dp).height(10.dp).clip(CircleShape),
                                    color = MaterialTheme.colorScheme.tertiary,
                                    trackColor = MaterialTheme.colorScheme.surfaceVariant,
                                )
                            }

                            Spacer(Modifier.height(6.dp))
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text("Chayqatish: ${espStatus!!.shakeText}", style = MaterialTheme.typography.labelMedium)
                                Text("Pitch ${espStatus!!.pitch.toInt()}° · Roll ${espStatus!!.roll.toInt()}°", style = MaterialTheme.typography.labelMedium)
                            }
                        }
                    }
                }
            }
        }
    }

    // Boshqaruv tugmalari
    val controlsContent: @Composable ColumnScope.() -> Unit = {
        val bh = Modifier.fillMaxWidth().height(54.dp)
        val shape = RoundedCornerShape(18.dp)
        Button(
            {
                startCry()
                if (isEspConnected) scope.launch { Api.sendBabyCommand(espBabyUrl, "/trigger_cry") }
            },
            bh, shape = shape,
        ) { Text("😭  Yig'latish", fontSize = 16.sp, fontWeight = FontWeight.SemiBold) }

        Spacer(Modifier.height(10.dp))
        FilledTonalButton(
            {
                startLaugh()
                if (isEspConnected) scope.launch { Api.sendBabyCommand(espBabyUrl, "/trigger_laugh") }
            },
            bh, shape = shape,
        ) { Text("😄  Kuldirish", fontSize = 16.sp, fontWeight = FontWeight.SemiBold) }

        Spacer(Modifier.height(10.dp))
        OutlinedButton(
            {
                stopAllSounds()
                if (isEspConnected) scope.launch { Api.sendBabyCommand(espBabyUrl, "/stop_cry") }
                msg = "Chaqaloq tinchitildi"
            },
            bh, shape = shape,
        ) { Text("✅  Tinchlantirish (jim)", fontSize = 16.sp, fontWeight = FontWeight.SemiBold) }

        Spacer(Modifier.height(10.dp))
        FilledTonalButton(
            {
                stopAllSounds()
                if (isEspConnected) scope.launch { Api.sendBabyCommand(espBabyUrl, "/reset") }
                msg = "Tizim qayta sozlandi"
            },
            bh, shape = shape,
        ) { Text("🔄  Qayta sozlash", fontSize = 16.sp, fontWeight = FontWeight.SemiBold) }

        Spacer(Modifier.height(16.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Switch(auto, { auto = it })
            Spacer(Modifier.width(10.dp))
            Text("Avtomatik muloqot (datchik orqali)", style = MaterialTheme.typography.bodyMedium)
        }

        if (!isEspConnected) {
            Spacer(Modifier.height(12.dp))
            if (hasSensor) {
                val zoneColor = when {
                    rms > SHAKE_MAX -> MaterialTheme.colorScheme.error
                    rms >= ROCK_MIN -> Ok
                    else -> MaterialTheme.colorScheme.secondary
                }
                val zoneText = when {
                    rms > SHAKE_MAX -> "Qattiq silkitish ✗"
                    rms >= ROCK_MIN -> "Yumshoq tebratish ✓"
                    else -> "Qimirlamayapti"
                }
                LinearProgressIndicator(
                    progress = (rms / SHAKE_MAX).coerceIn(0f, 1f),
                    color = zoneColor, trackColor = MaterialTheme.colorScheme.surfaceVariant,
                    modifier = Modifier.fillMaxWidth().height(10.dp).clip(CircleShape),
                )
                Spacer(Modifier.height(4.dp))
                Text("%s · %.2f".format(zoneText, rms), style = MaterialTheme.typography.labelMedium, color = zoneColor)
            } else {
                Text("ESP32 ulanmagan va qurilmada datchik yo'q", style = MaterialTheme.typography.bodySmall)
            }
        }
    }

    Column(Modifier.fillMaxSize()) {
        ScreenHeader(p, onBack, picker)
        BoxWithConstraints(Modifier.weight(1f).fillMaxWidth().padding(horizontal = 16.dp, vertical = 14.dp)) {
            if (maxWidth < 700.dp) {
                Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState())) {
                    statusContent(Modifier.fillMaxWidth())
                    Spacer(Modifier.height(16.dp))
                    controlsContent()
                }
            } else {
                Row(Modifier.fillMaxSize()) {
                    Box(Modifier.weight(1f).fillMaxHeight().verticalScroll(rememberScrollState())) { statusContent(Modifier.fillMaxWidth()) }
                    Spacer(Modifier.width(20.dp))
                    Column(Modifier.width(300.dp).fillMaxHeight().verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.Center) {
                        controlsContent()
                    }
                }
            }
        }
    }
}
