package uz.medsim

import android.Manifest
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.RecognitionListener
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch
import java.io.File

data class PatientInfo(val id: String, val title: String, val isBaby: Boolean = false)

val PATIENTS = listOf(
    PatientInfo("buvi", "Salomat buvi (75 yosh, diabet)"),
    PatientInfo("homilador", "Nilufar (32 haftalik homilador)"),
    PatientInfo("bola", "Jasurbek (5 yosh, gijja)"),
    PatientInfo("chaqaloq", "Chaqaloq", isBaby = true),
)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO, Manifest.permission.BLUETOOTH_CONNECT), 1)
        setContent { MaterialTheme { App() } }
    }
}

@Composable
fun App() {
    val ctx = LocalContext.current
    val prefs = remember { ctx.getSharedPreferences("medsim", Context.MODE_PRIVATE) }
    var server by remember { mutableStateOf(prefs.getString("server", "") ?: "") }
    var current by remember { mutableStateOf<PatientInfo?>(null) }
    // manikenga biriktirilgan kalonka: patient.id -> AudioDeviceInfo.id
    val speakers = remember { mutableStateMapOf<String, Int>() }

    Column(Modifier.fillMaxSize().padding(24.dp)) {
        val p = current
        if (p == null) {
          Column(Modifier.verticalScroll(rememberScrollState())) {
            Text("MedSim — bemorni tanlang", style = MaterialTheme.typography.headlineMedium)
            OutlinedTextField(server, { server = it; prefs.edit().putString("server", it).apply() },
                label = { Text("Server manzili") }, placeholder = { Text("http://192.168.1.5:8000") },
                singleLine = true, modifier = Modifier.fillMaxWidth())
            Spacer(Modifier.height(12.dp))
            PATIENTS.forEach {
                Button({ current = it }, Modifier.fillMaxWidth().padding(vertical = 4.dp)) { Text(it.title) }
            }
          }
        } else {
            TextButton({ Speaker.stop(); current = null }) { Text("← Orqaga") }
            Text(p.title, style = MaterialTheme.typography.headlineSmall)
            SpeakerPicker(speakers[p.id]) { speakers[p.id] = it }
            Spacer(Modifier.height(8.dp))
            if (p.isBaby) BabyScreen(speakers[p.id]) else ChatScreen(p, server, speakers[p.id])
        }
    }
}

@Composable
fun SpeakerPicker(selected: Int?, onPick: (Int) -> Unit) {
    val ctx = LocalContext.current
    var devices by remember { mutableStateOf(Speaker.bluetoothDevices(ctx)) }
    Row(verticalAlignment = Alignment.CenterVertically) {
        Text("Kalonka: ")
        if (devices.isEmpty()) Text("ulangan Bluetooth kalonka yo'q (standart chiqish)")
        devices.forEach { d ->
            FilterChip(selected == d.id, { onPick(d.id) }, { Text(d.productName.toString()) },
                modifier = Modifier.padding(horizontal = 4.dp))
        }
        TextButton({ devices = Speaker.bluetoothDevices(ctx) }) { Text("Yangilash") }
    }
}

@Composable
fun BabyScreen(deviceId: Int?) {
    val ctx = LocalContext.current
    var msg by remember { mutableStateOf("") }
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Button({
            msg = if (Speaker.playAsset(ctx, "baby_cry.mp3", deviceId, loop = true)) "Chaqaloq yig'layapti"
            else "assets/baby_cry.mp3 fayli topilmadi"
        }) { Text("Yig'latish") }
        Button({ Speaker.stop(); msg = "Jim bo'ldi" }) { Text("Ovuntirish (jim)") }
    }
    Text(msg)
}

@Composable
fun ChatScreen(p: PatientInfo, server: String, deviceId: Int?) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    val history = remember(p.id) { mutableStateListOf<Turn>() }
    var status by remember { mutableStateOf("Mikrofon tugmasini bosib gapiring") }
    var busy by remember { mutableStateOf(false) }
    var timing by remember { mutableStateOf("") }

    fun send(text: String) {
        if (server.isBlank()) { status = "Avval bosh sahifada server manzilini kiriting"; return }
        history.add(Turn("user", text)); busy = true; status = "Bemor javob tayyorlayapti…"
        timing = ""
        val t0 = System.currentTimeMillis()
        scope.launch {
            val parts = mutableListOf<String>()
            try {
                Speaker.beginStream(deviceId) { status = "Mikrofon tugmasini bosib gapiring" }
                Api.chatStream(server, p.id, history.toList()) { seg ->
                    if (parts.isEmpty()) {
                        timing = "Birinchi ovozgacha: %.1f s".format((System.currentTimeMillis() - t0) / 1000.0)
                        status = "Bemor gapirmoqda…"
                    }
                    parts.add(seg.text)
                    Speaker.enqueue(ctx, seg.mp3)
                }
                if (parts.isNotEmpty()) history.add(Turn("assistant", parts.joinToString(" ")))
                Speaker.endStream()
            } catch (e: Exception) {
                Speaker.stop()
                status = "Xato: ${e.message}"
            } finally { busy = false }
        }
    }

    fun listen() {
        if (ctx.checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            status = "Mikrofonga ruxsat bering"; return
        }
        val rec = SpeechRecognizer.createSpeechRecognizer(ctx)
        rec.setRecognitionListener(object : RecognitionListener {
            override fun onResults(b: Bundle?) {
                val t = b?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()
                rec.destroy()
                if (t.isNullOrBlank()) status = "Eshitilmadi, qayta urinib ko'ring" else send(t)
            }
            override fun onError(e: Int) { rec.destroy(); status = "Eshitilmadi (xato $e), qayta urinib ko'ring" }
            override fun onReadyForSpeech(p: Bundle?) { status = "Eshityapman…" }
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

    Column(Modifier.fillMaxSize()) {
        LazyColumn(Modifier.weight(1f)) {
            items(history) {
                Text((if (it.role == "user") "Hamshira: " else "Bemor: ") + it.content,
                    Modifier.padding(vertical = 4.dp))
            }
        }
        Text(status)
        if (timing.isNotEmpty()) Text(timing)
        Button(::listen, enabled = !busy, modifier = Modifier.fillMaxWidth().height(64.dp)) { Text("🎤 Gapirish") }
    }
}
