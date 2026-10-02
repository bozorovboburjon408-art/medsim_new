package uz.medsim

import android.util.Base64
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
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
    val fmt: String = "mp3", val tts: String = "", val pcmRate: Int = 0,
)

object Api {
    private val http = OkHttpClient.Builder()
        .readTimeout(45, TimeUnit.SECONDS).build()

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
            http.newCall(req).execute().use { r ->
                if (!r.isSuccessful) {
                    val raw = r.body!!.string()
                    error("Server xatosi ${r.code}: " + (runCatching { JSONObject(raw).getString("detail") }.getOrDefault(raw)).take(300))
                }
                val src = r.body!!.source()
                while (true) {
                    val line = src.readUtf8Line() ?: break
                    if (line.isBlank()) continue
                    val j = JSONObject(line)
                    if (j.has("error")) error(j.getString("error"))
                    val isPcm = j.has("pcm_b64")
                    val seg = Seg(j.optString("text"), Base64.decode(j.getString(if (isPcm) "pcm_b64" else "audio_b64"), Base64.DEFAULT), j.optInt("ms"),
                        j.optInt("llm_ms"), j.optInt("tts_ms"), j.optString("model"), j.optString("tries"),
                        j.optString("fmt", "mp3"), j.optString("tts"), if (isPcm) j.optInt("rate", 24000) else 0)
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
}
