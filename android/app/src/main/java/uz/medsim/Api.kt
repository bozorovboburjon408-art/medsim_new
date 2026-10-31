package uz.medsim

import android.util.Base64
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import android.util.Log
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

data class Turn(val role: String, val content: String) // "user" = hamshira, "assistant" = bemor
data class Reply(val text: String, val mp3: ByteArray, val llmMs: Int = 0, val ttsMs: Int = 0)

data class EvalStage(val name: String, val score: Int, val max: Int, val done: List<String>, val missed: List<String>)
data class EvalResult(
    val total: Int, val stages: List<EvalStage>, val strengths: List<String>, val advice: List<String>, val summary: String,
)

data class Seg(
    val text: String, val mp3: ByteArray, val ms: Int,
    val llmMs: Int = 0, val ttsMs: Int = 0, val model: String = "", val tries: String = "",
    val fmt: String = "mp3", val tts: String = "", val pcmRate: Int = 0, val usage: String = "",
)

data class BabyStatus(
    val online: Boolean,
    val state: String,
    val stateUz: String,
    val isCrying: Boolean,
    val isSoothed: Boolean,
    val isLaughing: Boolean,
    val soothingProgress: Int,
    val happyProgress: Int,
    val holdingStatus: String,
    val holdingText: String,
    val shakeStatus: String,
    val shakeText: String,
    val motion: Float,
    val pitch: Float,
    val roll: Float,
    val sensorOk: Boolean
)

object Api {
    // Bo'sh turgan ulanishni qayta ishlatmaymiz: planshet Wi-Fi'si uni jimgina uzadi va birinchi so'rov 45 s osilib qoladi
    private val http = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .connectionPool(okhttp3.ConnectionPool(0, 1, TimeUnit.MINUTES))
        .readTimeout(25, TimeUnit.SECONDS).build()

    private fun normalize(u: String): String {
        val t = u.trim().trimEnd('/')
        return if (t.startsWith("http://") || t.startsWith("https://")) t else "http://$t"
    }

    suspend fun chat(baseUrl: String, patientId: String, history: List<Turn>): Reply =
        withContext(Dispatchers.IO) {
            val body = JSONObject()
                .put("patient_id", patientId)
                .put("history", JSONArray(history.map {
                    JSONObject().put("role", it.role).put("content", it.content)
                }))
            val req = Request.Builder()
                .url(normalize(baseUrl) + "/chat")
                .post(body.toString().toRequestBody("application/json".toMediaType()))
                .build()
            http.newCall(req).execute().use { r ->
                val raw = r.body!!.string()
                check(r.isSuccessful) { "Server xatosi ${r.code}: " + (runCatching { JSONObject(raw).getString("detail") }.getOrDefault(raw)).take(300) }
                val j = JSONObject(raw)
                Reply(j.getString("text"), Base64.decode(j.getString("audio_b64"), Base64.DEFAULT),
                    j.optInt("llm_ms"), j.optInt("tts_ms"))
            }
        }

    /** Oqim: har bir gap tayyor bo'lishi bilan onSeg (asosiy oqimda) chaqiriladi. */
    suspend fun chatStream(baseUrl: String, patientId: String, history: List<Turn>, model: String, tts: String, onSeg: (Seg) -> Unit) =
        withContext(Dispatchers.IO) {
            val body = JSONObject()
                .put("patient_id", patientId)
                .put("history", JSONArray(history.map {
                    JSONObject().put("role", it.role).put("content", it.content)
                }))
            if (model.isNotBlank()) body.put("model", model)
            if (tts.isNotBlank()) body.put("tts", tts)
            val req = Request.Builder()
                .url(normalize(baseUrl) + "/chat_stream")
                .post(body.toString().toRequestBody("application/json".toMediaType()))
                .build()
            Log.d("API", "chat_stream so'rovi yuborilmoqda: ${normalize(baseUrl)} patient=$patientId tts=$tts")
            http.newCall(req).execute().use { r ->
                Log.d("API", "chat_stream javob kodi=${r.code}")
                if (!r.isSuccessful) {
                    val raw = r.body!!.string()
                    error("Server xatosi ${r.code}: " + (runCatching { JSONObject(raw).getString("detail") }.getOrDefault(raw)).take(300))
                }
                val src = r.body!!.source()
                while (true) {
                    val line = src.readUtf8Line() ?: break
                    if (line.isBlank()) continue
                    Log.d("API", "qator keldi (${line.length} belgi)")
                    val j = JSONObject(line)
                    if (j.has("error")) error(j.getString("error"))
                    val isPcm = j.has("pcm_b64")
                    val seg = Seg(j.optString("text"), Base64.decode(j.getString(if (isPcm) "pcm_b64" else "audio_b64"), Base64.DEFAULT), j.optInt("ms"),
                        j.optInt("llm_ms"), j.optInt("tts_ms"), j.optString("model"), j.optString("tries"),
                        j.optString("fmt", "mp3"), j.optString("tts"), if (isPcm) j.optInt("rate", 24000) else 0, j.optString("usage"))
                    withContext(Dispatchers.Main) { onSeg(seg) }
                }
            }
        }

    suspend fun health(baseUrl: String): Boolean = withContext(Dispatchers.IO) {
        runCatching {
            http.newCall(Request.Builder().url(normalize(baseUrl) + "/health").build())
                .execute().use { it.isSuccessful }
        }.getOrDefault(false)
    }

    private fun strList(a: JSONArray?): List<String> = (0 until (a?.length() ?: 0)).map { a!!.getString(it) }

    /** Suhbatni baholash (AI 5-20 soniya o'ylashi mumkin). */
    suspend fun evaluate(baseUrl: String, patientId: String, history: List<Turn>, model: String): EvalResult =
        withContext(Dispatchers.IO) {
            val body = JSONObject()
                .put("patient_id", patientId)
                .put("history", JSONArray(history.map { JSONObject().put("role", it.role).put("content", it.content) }))
            if (model.isNotBlank()) body.put("model", model)
            val req = Request.Builder().url(normalize(baseUrl) + "/evaluate")
                .post(body.toString().toRequestBody("application/json".toMediaType())).build()
            http.newBuilder().readTimeout(90, TimeUnit.SECONDS).build().newCall(req).execute().use { r ->
                val raw = r.body!!.string()
                check(r.isSuccessful) { "Server xatosi ${r.code}: " + (runCatching { JSONObject(raw).getString("detail") }.getOrDefault(raw)).take(300) }
                val j = JSONObject(raw)
                val st = j.getJSONArray("stages")
                EvalResult(
                    j.getInt("total"),
                    (0 until st.length()).map {
                        val s = st.getJSONObject(it)
                        EvalStage(s.getString("name"), s.getInt("score"), s.getInt("max"), strList(s.optJSONArray("done")), strList(s.optJSONArray("missed")))
                    },
                    strList(j.optJSONArray("strengths")), strList(j.optJSONArray("advice")), j.optString("summary"),
                )
            }
        }

    /** ESP32 Chaqaloq manikeni holatini o'qish (/status) */
    suspend fun getBabyStatus(espUrl: String): BabyStatus? = withContext(Dispatchers.IO) {
        runCatching {
            val req = Request.Builder().url(normalize(espUrl) + "/status").build()
            http.newBuilder()
                .connectTimeout(1200, TimeUnit.MILLISECONDS)
                .readTimeout(1500, TimeUnit.MILLISECONDS)
                .build().newCall(req).execute().use { r ->
                if (!r.isSuccessful) return@use null
                val raw = r.body?.string() ?: return@use null
                val j = JSONObject(raw)
                val angles = j.optJSONObject("angles")
                BabyStatus(
                    online = j.optBoolean("online", true),
                    state = j.optString("state", "CALM"),
                    stateUz = j.optString("state_uz", "Tinch"),
                    isCrying = j.optBoolean("is_crying", false),
                    isSoothed = j.optBoolean("is_soothed", true),
                    isLaughing = j.optBoolean("is_laughing", false),
                    soothingProgress = j.optInt("soothing_progress", 0),
                    happyProgress = j.optInt("happy_progress", 0),
                    holdingStatus = j.optString("holding_status", "LYING"),
                    holdingText = j.optString("holding_text", "Yotqizilgan"),
                    shakeStatus = j.optString("shake_status", "NONE"),
                    shakeText = j.optString("shake_text", "Harakatsiz"),
                    motion = j.optDouble("motion", 0.0).toFloat(),
                    pitch = angles?.optDouble("pitch", 0.0)?.toFloat() ?: 0f,
                    roll = angles?.optDouble("roll", 0.0)?.toFloat() ?: 0f,
                    sensorOk = j.optBoolean("sensor_ok", true)
                )
            }
        }.getOrNull()
    }

    suspend fun sendBabyCommand(espUrl: String, endpoint: String): Boolean = withContext(Dispatchers.IO) {
        runCatching {
            val req = Request.Builder().url(normalize(espUrl) + endpoint).build()
            http.newBuilder()
                .connectTimeout(1500, TimeUnit.MILLISECONDS)
                .readTimeout(2, TimeUnit.SECONDS)
                .build().newCall(req).execute().use { it.isSuccessful }
        }.getOrDefault(false)
    }
}

