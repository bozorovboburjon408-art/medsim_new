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
data class Reply(val text: String, val mp3: ByteArray)

object Api {
    private val http = OkHttpClient.Builder()
        .readTimeout(60, TimeUnit.SECONDS).build()

    suspend fun chat(baseUrl: String, patientId: String, history: List<Turn>): Reply =
        withContext(Dispatchers.IO) {
            val body = JSONObject()
                .put("patient_id", patientId)
                .put("history", JSONArray(history.map {
                    JSONObject().put("role", it.role).put("content", it.content)
                }))
            val req = Request.Builder()
                .url(baseUrl.trimEnd('/') + "/chat")
                .post(body.toString().toRequestBody("application/json".toMediaType()))
                .build()
            http.newCall(req).execute().use { r ->
                check(r.isSuccessful) { "Server xatosi: ${r.code}" }
                val j = JSONObject(r.body!!.string())
                Reply(j.getString("text"), Base64.decode(j.getString("audio_b64"), Base64.DEFAULT))
            }
        }
}
