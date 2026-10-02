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

object Api {
    private val http = OkHttpClient.Builder()
        .readTimeout(60, TimeUnit.SECONDS).build()

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
}
