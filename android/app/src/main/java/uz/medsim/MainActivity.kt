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
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.DialogProperties
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.math.sqrt

data class PatientInfo(
    val id: String, val name: String, val subtitle: String, val emoji: String, val isBaby: Boolean = false,
)

val PATIENTS = listOf(
    PatientInfo("buvi", "Salomat buvi", "75 yosh · 2-tip qandli diabet", "👵"),
    PatientInfo("homilador", "Nilufar opa", "33 yosh · 32 haftalik homiladorlik", "🤰"),
    PatientInfo("bola", "Madinaxon", "5 yosh · qizaloq", "👧"),
    PatientInfo("bobo", "Hikmatilla ota", "78 yosh · yoshga doir skrining", "👴"),
    PatientInfo("chaqaloq", "Chaqaloq", "Yig'laydi, tebratilsa tinchiydi", "👶", isBaby = true),
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO, Manifest.permission.BLUETOOTH_CONNECT), 1)
        setContent { MedSimTheme { Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) { App() } } }
    }
}

@Composable
fun App() {
    val ctx = LocalContext.current
    val prefs = remember { ctx.getSharedPreferences("medsim", Context.MODE_PRIVATE) }
    var server by remember { mutableStateOf(prefs.getString("server", "") ?: "") }
    var model by remember { mutableStateOf(prefs.getString("model", "") ?: "") }
    var tts by remember { mutableStateOf(prefs.getString("tts", "") ?: "") }
    var espBabyUrl by remember { mutableStateOf(prefs.getString("esp_baby_url", "http://medsim-baby.local") ?: "http://medsim-baby.local") }
    var showSettings by remember { mutableStateOf(server.isBlank()) }
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

// ───────────────────────── Bosh sahifa ─────────────────────────

@Composable
fun HomeScreen(speakers: Map<String, Int>, serverState: Int, onPick: (PatientInfo) -> Unit, onSettings: () -> Unit) {
    val ctx = LocalContext.current
    Column(Modifier.fillMaxSize().padding(horizontal = 28.dp, vertical = 20.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("MedSim", fontSize = 32.sp, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                Text("Bemorni tanlang", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                when (serverState) {
                    1 -> Text("● Server tayyor", style = MaterialTheme.typography.labelLarge, color = Ok)
                    2 -> Text("● Server uyg'onmoqda… (1 daqiqagacha kuting)", style = MaterialTheme.typography.labelLarge, color = Warn)
                    3 -> Text("● Server bilan aloqa yo'q (qayta urinilmoqda)", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.error)
                }
            }
            FilledTonalButton(onSettings) { Text("⚙  Sozlamalar") }
        }
        Spacer(Modifier.height(16.dp))
        LazyVerticalGrid(
            GridCells.Adaptive(300.dp),
            horizontalArrangement = Arrangement.spacedBy(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
            contentPadding = PaddingValues(bottom = 16.dp),
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
    Card(
        Modifier.fillMaxWidth().clip(MaterialTheme.shapes.large).clickable(onClick = onClick),
        shape = MaterialTheme.shapes.large,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(2.dp),
    ) {
        Row(Modifier.padding(20.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(
                Modifier.size(72.dp).clip(CircleShape).background(MaterialTheme.colorScheme.primaryContainer),
                contentAlignment = Alignment.Center,
            ) { Text(p.emoji, fontSize = 38.sp) }
            Spacer(Modifier.width(16.dp))
            Column {
                Text(p.name, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Text(p.subtitle, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                if (speakerName != null) {
                    Spacer(Modifier.height(6.dp))
                    Text("🔊 $speakerName", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
                }
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
        title = { Text("Sozlamalar") },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState())) {
                OutlinedTextField(
                    text, { text = it }, label = { Text("Server manzili (Render)") },
                    placeholder = { Text("https://....onrender.com") }, singleLine = true, modifier = Modifier.fillMaxWidth(),
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
                    placeholder = { Text("http://192.168.1.50 yoki http://medsim-baby.local") }, singleLine = true, modifier = Modifier.fillMaxWidth(),
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
                        "gemini-2.0-flash" to "2.0 Flash",
                        "gemini-2.0-flash-lite" to "2.0 Flash-Lite",
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

// ───────────────────────── Umumiy qismlar ─────────────────────────

@Composable
fun ScreenHeader(p: PatientInfo, onBack: () -> Unit, picker: @Composable () -> Unit) {
    Column {
        Row(verticalAlignment = Alignment.CenterVertically) {
            OutlinedButton(onBack) { Text("←  Orqaga") }
            Spacer(Modifier.width(16.dp))
            Text(p.emoji, fontSize = 30.sp)
            Spacer(Modifier.width(8.dp))
            Column {
                Text(p.name, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Text(p.subtitle, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        Spacer(Modifier.height(8.dp))
        picker()
    }
}

@Composable
fun SpeakerPicker(selected: Int?, onPick: (Int) -> Unit) {
    val ctx = LocalContext.current
    var devices by remember { mutableStateOf(Speaker.bluetoothDevices(ctx)) }
    Row(Modifier.horizontalScroll(rememberScrollState()), verticalAlignment = Alignment.CenterVertically) {
        Text("🔊 Kalonka:", style = MaterialTheme.typography.labelLarge)
        Spacer(Modifier.width(8.dp))
        if (devices.isEmpty()) Text("Bluetooth kalonka ulanmagan (telefon dinamigi)", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        devices.forEach { d ->
            FilterChip(selected == d.id, { onPick(d.id) }, { Text(d.productName.toString()) }, modifier = Modifier.padding(end = 8.dp))
        }
        TextButton({ devices = Speaker.bluetoothDevices(ctx) }) { Text("↻ Yangilash") }
    }
}

enum class Phase(val label: String) {
    IDLE("Gapirish uchun bosing"), LISTENING("Eshityapman…"), THINKING("Bemor o'ylayapti…"), SPEAKING("Bemor gapirmoqda…")
}

@Composable
fun MicButton(phase: Phase, onClick: () -> Unit) {
    val pulse by rememberInfiniteTransition(label = "pulse").animateFloat(
        1f, 1.14f, infiniteRepeatable(tween(650), RepeatMode.Reverse), label = "p",
    )
    val scale = if (phase == Phase.LISTENING) pulse else 1f
    val color = when (phase) {
        Phase.LISTENING -> MaterialTheme.colorScheme.error
        Phase.THINKING -> MaterialTheme.colorScheme.secondary
        else -> MaterialTheme.colorScheme.primary
    }
    Button(
        onClick, enabled = phase != Phase.THINKING && phase != Phase.LISTENING,
        shape = CircleShape, contentPadding = PaddingValues(0.dp),
        colors = ButtonDefaults.buttonColors(containerColor = color, disabledContainerColor = color),
        modifier = Modifier.size(104.dp).graphicsLayer { scaleX = scale; scaleY = scale },
    ) {
        if (phase == Phase.THINKING) CircularProgressIndicator(Modifier.size(36.dp), color = Color.White, strokeWidth = 4.dp)
        else Text("🎤", fontSize = 42.sp)
    }
}

@Composable
fun Bubble(t: Turn, patient: PatientInfo) {
    val nurse = t.role == "user"
    Row(Modifier.fillMaxWidth(), horizontalArrangement = if (nurse) Arrangement.End else Arrangement.Start) {
        Column(horizontalAlignment = if (nurse) Alignment.End else Alignment.Start) {
            Text(
                if (nurse) "Siz (hamshira)" else "${patient.emoji} ${patient.name}",
                style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
            )
            Surface(
                shape = RoundedCornerShape(
                    topStart = 20.dp, topEnd = 20.dp, bottomStart = if (nurse) 20.dp else 4.dp, bottomEnd = if (nurse) 4.dp else 20.dp,
                ),
                color = if (nurse) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surface,
                shadowElevation = if (nurse) 0.dp else 1.dp,
                modifier = Modifier.widthIn(max = 520.dp),
            ) {
                Text(
                    t.content, Modifier.padding(horizontal = 16.dp, vertical = 12.dp), fontSize = 17.sp,
                    color = if (nurse) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurface,
                )
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
    val listState = rememberLazyListState()
    LaunchedEffect(history.size) { if (history.isNotEmpty()) listState.animateScrollToItem(history.size - 1) }

    fun send(text: String) {
        if (server.isBlank()) { error = "Avval Sozlamalarda server manzilini kiriting"; phase = Phase.IDLE; return }
        history.add(Turn("user", text)); phase = Phase.THINKING; error = ""; firstAudio = ""
        val t0 = System.currentTimeMillis()
        scope.launch {
            val parts = mutableListOf<String>()
            var attempt = 0
            while (true) {
                try {
                    Speaker.beginStream(deviceId) { phase = Phase.IDLE }
                    Api.chatStream(server, p.id, history.toList(), model, tts) { seg ->
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
                    if (parts.isNotEmpty()) history.add(Turn("assistant", parts.joinToString(" ")))
                    Speaker.endStream()
                    break
                } catch (e: Exception) {
                    Speaker.stop()
                    if (parts.isEmpty() && attempt == 0) {  // hech narsa kelmagan: bir marta o'zi qayta uriniladi
                        attempt++; phase = Phase.THINKING; error = ""
                        continue
                    }
                    phase = Phase.IDLE
                    val msg = e.message.orEmpty()
                    error = if (msg.contains("timeout", true) || msg.contains("timed out", true))
                        "Server javob bermadi (vaqt tugadi). Mikrofonni bosib qayta urinib ko'ring"
                    else "Xato: $msg"
                    break
                }
            }
        }
    }

    fun listen() {
        if (ctx.checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            error = "Mikrofonga ruxsat bering (Sozlamalar → Ilovalar → MedSim)"; return
        }
        Speaker.stop(); error = ""; phase = Phase.LISTENING
        val rec = SpeechRecognizer.createSpeechRecognizer(ctx)
        rec.setRecognitionListener(object : RecognitionListener {
            override fun onResults(b: Bundle?) {
                val t = b?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()
                rec.destroy()
                if (t.isNullOrBlank()) { phase = Phase.IDLE; error = "Eshitilmadi, qayta urinib ko'ring" } else send(t)
            }
            override fun onError(e: Int) { rec.destroy(); phase = Phase.IDLE; error = "Eshitilmadi (xato $e), qayta urinib ko'ring" }
            override fun onReadyForSpeech(p: Bundle?) {}
            override fun onBeginningOfSpeech() {}
            override fun onRmsChanged(v: Float) {}
            override fun onBufferReceived(b: ByteArray?) {}
            override fun onEndOfSpeech() {}
            override fun onPartialResults(b: Bundle?) {}
            override fun onEvent(t: Int, b: Bundle?) {}
        })
        rec.startListening(Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "uz-UZ")
        })
    }

    evalResult?.let { EvaluationDialog(it) { evalResult = null } }
    Column(Modifier.fillMaxSize().padding(horizontal = 24.dp, vertical = 14.dp)) {
        ScreenHeader(p, onBack, picker)
        Spacer(Modifier.height(10.dp))
        Row(Modifier.weight(1f).fillMaxWidth()) {
            Surface(
                Modifier.weight(1f).fillMaxHeight(), shape = MaterialTheme.shapes.large,
                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
            ) {
                if (history.isEmpty()) {
                    Box(Modifier.fillMaxSize().padding(32.dp), contentAlignment = Alignment.Center) {
                        Text(
                            "Mikrofon tugmasini bosing va bemorga salom bering.\nMasalan: «Assalomu alaykum, ahvollaringiz qanday?»",
                            textAlign = TextAlign.Center, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 17.sp,
                        )
                    }
                } else {
                    LazyColumn(
                        state = listState, contentPadding = PaddingValues(16.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                    ) { items(history) { Bubble(it, p) } }
                }
            }
            Spacer(Modifier.width(20.dp))
            Column(
                Modifier.width(210.dp).fillMaxHeight(),
                horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center,
            ) {
                Text(
                    phase.label, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold,
                    textAlign = TextAlign.Center,
                    color = if (phase == Phase.LISTENING) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurface,
                )
                Spacer(Modifier.height(14.dp))
                MicButton(phase) { listen() }
                Spacer(Modifier.height(12.dp))
                if (firstAudio.isNotEmpty()) Text(firstAudio, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                if (error.isNotEmpty()) {
                    Surface(shape = MaterialTheme.shapes.small, color = MaterialTheme.colorScheme.errorContainer) {
                        Text(error, Modifier.padding(10.dp), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
                    }
                }
                Spacer(Modifier.height(8.dp))
                val canEval = history.any { it.role == "user" } && phase == Phase.IDLE && !evaluating
                OutlinedButton({
                    evaluating = true; error = ""
                    scope.launch {
                        try { evalResult = Api.evaluate(server, p.id, history.toList(), model) }
                        catch (e: Exception) { error = "Baholash xatosi: ${e.message}" }
                        finally { evaluating = false }
                    }
                }, enabled = canEval) {
                    if (evaluating) { CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp); Spacer(Modifier.width(8.dp)); Text("Baholanmoqda…") }
                    else Text("📋 Baholash")
                }
                TextButton({ Speaker.stop(); history.clear(); phase = Phase.IDLE; error = ""; firstAudio = "" }) { Text("Yangi suhbat") }
            }
        }
    }
}

// ───────────────────────── Baholash natijasi ─────────────────────────

@Composable
fun EvaluationDialog(r: EvalResult, onDismiss: () -> Unit) {
    val color = when { r.total >= 80 -> Ok; r.total >= 60 -> Warn; else -> MaterialTheme.colorScheme.error }
    AlertDialog(
        onDismissRequest = onDismiss,
        modifier = Modifier.fillMaxWidth(0.88f),
        properties = DialogProperties(usePlatformDefaultWidth = false),
        title = { Text("Baholash natijasi") },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState())) {
                Row(verticalAlignment = Alignment.Bottom) {
                    Text("${r.total}", fontSize = 48.sp, fontWeight = FontWeight.Bold, color = color)
                    Text(" / 100", fontSize = 20.sp, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.padding(bottom = 8.dp))
                }
                if (r.summary.isNotBlank()) Text(r.summary, style = MaterialTheme.typography.bodyLarge)
                r.stages.forEach { st ->
                    Spacer(Modifier.height(14.dp))
                    Row {
                        Text(st.name, Modifier.weight(1f), fontWeight = FontWeight.SemiBold)
                        Text("${st.score}/${st.max}", fontWeight = FontWeight.Bold)
                    }
                    Spacer(Modifier.height(4.dp))
                    LinearProgressIndicator(
                        progress = st.score.toFloat() / st.max, color = if (st.score * 100 / st.max >= 60) Ok else Warn,
                        trackColor = MaterialTheme.colorScheme.surfaceVariant, modifier = Modifier.fillMaxWidth().height(8.dp).clip(CircleShape),
                    )
                    st.done.forEach { Text("✓ $it", color = Ok, style = MaterialTheme.typography.bodyMedium) }
                    st.missed.forEach { Text("✗ $it", color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodyMedium) }
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

    Column(Modifier.fillMaxSize().padding(horizontal = 24.dp, vertical = 14.dp)) {
        ScreenHeader(p, onBack, picker)
        Spacer(Modifier.height(10.dp))
        Row(Modifier.weight(1f).fillMaxWidth()) {
            Surface(
                Modifier.weight(1f).fillMaxHeight(), shape = MaterialTheme.shapes.large,
                color = when {
                    crying -> MaterialTheme.colorScheme.errorContainer
                    laughing -> MaterialTheme.colorScheme.tertiaryContainer
                    else -> MaterialTheme.colorScheme.primaryContainer
                },
            ) {
                Column(Modifier.fillMaxSize().padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
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
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            if (isEspConnected) "● ESP32 Maniken: Ulangan (${espStatus?.holdingText ?: ""})"
                            else "○ ESP32 Maniken: Ulanmagan (Planshet datchigi rejimida)",
                            style = MaterialTheme.typography.labelMedium,
                            color = if (isEspConnected) Ok else MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }

                    if (isEspConnected && espStatus != null) {
                        Spacer(Modifier.height(14.dp))
                        Card(
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier.fillMaxWidth(0.9f)
                        ) {
                            Column(Modifier.padding(12.dp)) {
                                val isHazard = espStatus!!.shakeStatus == "VIOLENT" || espStatus!!.holdingStatus == "UPSIDE_DOWN"
                                if (isHazard) {
                                    Surface(
                                        color = MaterialTheme.colorScheme.errorContainer,
                                        shape = RoundedCornerShape(8.dp),
                                        modifier = Modifier.fillMaxWidth().padding(bottom = 8.dp)
                                    ) {
                                        Text(
                                            "⚠️ ${if (espStatus!!.holdingStatus == "UPSIDE_DOWN") espStatus!!.holdingText else espStatus!!.shakeText}",
                                            color = MaterialTheme.colorScheme.onErrorContainer,
                                            style = MaterialTheme.typography.bodySmall,
                                            fontWeight = FontWeight.Bold,
                                            modifier = Modifier.padding(8.dp)
                                        )
                                    }
                                }

                                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                    Text("Ovunish progressi:", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.SemiBold)
                                    Text("${espStatus!!.soothingProgress}%", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.primary)
                                }
                                LinearProgressIndicator(
                                    progress = espStatus!!.soothingProgress / 100f,
                                    modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp).height(8.dp).clip(CircleShape),
                                    color = MaterialTheme.colorScheme.primary
                                )

                                if (espStatus!!.happyProgress > 0 || espStatus!!.isLaughing) {
                                    Spacer(Modifier.height(4.dp))
                                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                        Text("Kulgi va quvonch:", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.SemiBold)
                                        Text("${espStatus!!.happyProgress}%", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.tertiary)
                                    }
                                    LinearProgressIndicator(
                                        progress = espStatus!!.happyProgress / 100f,
                                        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp).height(8.dp).clip(CircleShape),
                                        color = MaterialTheme.colorScheme.tertiary
                                    )
                                }

                                Spacer(Modifier.height(6.dp))
                                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                    Text("Chayqatish: ${espStatus!!.shakeText}", style = MaterialTheme.typography.labelSmall)
                                    Text("Pitch: ${espStatus!!.pitch.toInt()}° | Roll: ${espStatus!!.roll.toInt()}°", style = MaterialTheme.typography.labelSmall)
                                }
                            }
                        }
                    }
                }
            }
            Spacer(Modifier.width(20.dp))
            Column(Modifier.width(280.dp).fillMaxHeight(), verticalArrangement = Arrangement.Center) {
                Button(
                    {
                        startCry()
                        if (isEspConnected) scope.launch { Api.sendBabyCommand(espBabyUrl, "/trigger_cry") }
                    },
                    Modifier.fillMaxWidth().height(48.dp)
                ) { Text("😭 Yig'latish", fontSize = 15.sp) }

                Spacer(Modifier.height(8.dp))
                FilledTonalButton(
                    {
                        startLaugh()
                        if (isEspConnected) scope.launch { Api.sendBabyCommand(espBabyUrl, "/trigger_laugh") }
                    },
                    Modifier.fillMaxWidth().height(48.dp)
                ) { Text("😄 Kuldurish", fontSize = 15.sp) }

                Spacer(Modifier.height(8.dp))
                OutlinedButton(
                    {
                        stopAllSounds()
                        if (isEspConnected) scope.launch { Api.sendBabyCommand(espBabyUrl, "/stop_cry") }
                        msg = "Chaqaloq tinchitildi"
                    },
                    Modifier.fillMaxWidth().height(48.dp),
                ) { Text("✅ Tinchlantirish (jim)", fontSize = 15.sp) }

                Spacer(Modifier.height(8.dp))
                FilledTonalButton(
                    {
                        stopAllSounds()
                        if (isEspConnected) scope.launch { Api.sendBabyCommand(espBabyUrl, "/reset") }
                        msg = "Tizim qayta sozlandi"
                    },
                    Modifier.fillMaxWidth().height(48.dp),
                ) { Text("🔄 Qayta sozlash", fontSize = 15.sp) }

                Spacer(Modifier.height(14.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Switch(auto, { auto = it })
                    Spacer(Modifier.width(10.dp))
                    Text("Avtomatik muloqot\n(datchik orqali)", style = MaterialTheme.typography.bodyMedium)
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
                        Text("ESP32 ulanmagan va planshetda datchik yo'q", style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        }
    }
}
