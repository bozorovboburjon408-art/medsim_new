package uz.medsim

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioDeviceInfo
import android.media.AudioFormat
import android.media.AudioTrack
import android.media.AudioManager
import android.media.MediaPlayer
import android.os.Handler
import android.os.Looper
import java.io.File
import java.util.concurrent.LinkedBlockingQueue

/** Ulangan Bluetooth kalonkalarni topadi va ovozni tanlangan kalonkaga yo'naltiradi. */
object Speaker {
    fun bluetoothDevices(ctx: Context): List<AudioDeviceInfo> {
        val am = ctx.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        return am.getDevices(AudioManager.GET_DEVICES_OUTPUTS)
            .filter { it.type == AudioDeviceInfo.TYPE_BLUETOOTH_A2DP }
    }

    private var player: MediaPlayer? = null

    fun setVolume(v: Float) { player?.setVolume(v, v) }

    fun stop() {
        items.clear(); playing = false; draining = false; expectMore = false
        pcm?.abort(); pcm = null; drainP?.abort(); drainP = null
        player?.release(); player = null
    }

    /** deviceId == null bo'lsa tizimning standart chiqishi ishlatiladi. */
    fun playFile(ctx: Context, file: File, deviceId: Int?, loop: Boolean = false, onDone: () -> Unit = {}) {
        stop()
        val p = MediaPlayer()
        p.setDataSource(file.absolutePath)
        playPrepared(ctx, p, deviceId, loop, onDone)
    }

    fun playAsset(ctx: Context, name: String, deviceId: Int?, loop: Boolean): Boolean {
        stop()
        return try {
            val fd = ctx.assets.openFd(name)
            val p = MediaPlayer()
            p.setDataSource(fd.fileDescriptor, fd.startOffset, fd.length)
            playPrepared(ctx, p, deviceId, loop) {}
            true
        } catch (e: Exception) {
            try {
                val tmp = File(ctx.cacheDir, "asset_$name").also { f ->
                    ctx.assets.open(name).use { input ->
                        f.outputStream().use { output -> input.copyTo(output) }
                    }
                }
                val p = MediaPlayer()
                p.setDataSource(tmp.absolutePath)
                playPrepared(ctx, p, deviceId, loop) {}
                true
            } catch (e2: Exception) {
                false
            }
        }
    }

    private fun playPrepared(ctx: Context, p: MediaPlayer, deviceId: Int?, loop: Boolean, onDone: () -> Unit) {
        deviceId?.let { id -> bluetoothDevices(ctx).firstOrNull { it.id == id }?.let { p.setPreferredDevice(it) } }
        p.isLooping = loop
        p.setOnCompletionListener { onDone() }
        p.prepare(); p.start()
        player = p
    }

    // ---- Gap-gap oqim ijrosi: PCM (ElevenLabs) va mp3 (Edge zaxirasi) bo'laklari bitta tartibli navbatda, hech qachon bir vaqtda chalinmaydi ----
    private sealed class Item {
        class Mp3(val file: File) : Item()
        class Pcm(val bytes: ByteArray, val rate: Int) : Item()
    }

    private val items = ArrayDeque<Item>()
    private var playing = false   // mp3 bo'lagi chalinyapti
    private var draining = false  // PCM tugashi kutilyapti (mp3 yoki yakun uchun)
    private var expectMore = false
    private var seq = 0
    private var idleCb: () -> Unit = {}
    private var dev: Int? = null
    private var pcm: PcmPlayer? = null
    private var drainP: PcmPlayer? = null  // tugashi kutilayotgan PCM ijrochi (stop() uni ham to'xtatadi)

    fun beginStream(deviceId: Int?, onIdle: () -> Unit) {
        stop(); expectMore = true; dev = deviceId; idleCb = onIdle
    }

    fun enqueue(ctx: Context, bytes: ByteArray, ext: String = "mp3") {
        val f = File(ctx.cacheDir, "seg_${seq++}.$ext").also { it.writeBytes(bytes) }
        items.addLast(Item.Mp3(f))
        advance(ctx)
    }

    /** Xom PCM bo'lagi: navbat bo'sh va mp3 chalinmayotgan bo'lsa darrov chalinadi, aks holda tartib bilan kutadi. */
    fun writePcm(ctx: Context, bytes: ByteArray, rate: Int) {
        if (playing || draining || items.isNotEmpty()) { items.addLast(Item.Pcm(bytes, rate)); return }
        val p = pcm ?: PcmPlayer(ctx, rate, dev).also { pcm = it }
        p.write(bytes)
    }

    fun endStream() {
        expectMore = false
        checkIdle()
    }

    private fun advance(ctx: Context) {
        if (playing || draining) return
        while (true) {
            val item = items.firstOrNull() ?: break
            when (item) {
                is Item.Pcm -> {
                    items.removeFirst()
                    val p = pcm ?: PcmPlayer(ctx, item.rate, dev).also { np -> pcm = np }
                    p.write(item.bytes)
                }
                is Item.Mp3 -> {
                    val p = pcm
                    if (p != null) {  // avval PCM to'liq chalinib bo'lsin
                        draining = true; pcm = null; drainP = p
                        p.finish { draining = false; drainP = null; advance(ctx) }
                        return
                    }
                    items.removeFirst()
                    playSeg(ctx, item.file)
                    return
                }
            }
        }
        checkIdle()
    }

    private fun checkIdle() {
        if (expectMore || playing || draining || items.isNotEmpty()) return
        val p = pcm
        if (p != null) {
            pcm = null; draining = true; drainP = p
            p.finish { draining = false; drainP = null; checkIdle() }
        } else idleCb()
    }

    private fun playSeg(ctx: Context, f: File) {
        playing = true
        val p = MediaPlayer()
        try {
            p.setDataSource(f.absolutePath)
            dev?.let { id -> bluetoothDevices(ctx).firstOrNull { it.id == id }?.let { p.setPreferredDevice(it) } }
            p.setOnCompletionListener { it.release(); f.delete(); playing = false; advance(ctx) }
            p.setOnErrorListener { mp, _, _ -> mp.release(); f.delete(); playing = false; advance(ctx); true }
            p.prepare(); p.start()
            player = p
        } catch (e: Exception) {
            p.release(); playing = false; advance(ctx)
        }
    }
}

/** 16-bit mono PCM ni AudioTrack (MODE_STREAM) orqali tanlangan kalonkaga uzluksiz chaladi. */
class PcmPlayer(ctx: Context, private val rate: Int, deviceId: Int?) {
    private val track: AudioTrack
    private val q = LinkedBlockingQueue<ByteArray>()
    private val end = ByteArray(0)
    @Volatile private var aborted = false
    @Volatile private var onFinished: (() -> Unit)? = null
    private val main = Handler(Looper.getMainLooper())

    init {
        val min = AudioTrack.getMinBufferSize(rate, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_16BIT)
        track = AudioTrack.Builder()
            .setAudioAttributes(
                AudioAttributes.Builder()
                    .setUsage(AudioAttributes.USAGE_MEDIA)
                    .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build(),
            )
            .setAudioFormat(
                AudioFormat.Builder()
                    .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                    .setSampleRate(rate)
                    .setChannelMask(AudioFormat.CHANNEL_OUT_MONO).build(),
            )
            .setBufferSizeInBytes(maxOf(min, rate * 2 * 2)) // ~2 soniya bufer
            .setTransferMode(AudioTrack.MODE_STREAM)
            .build()
        deviceId?.let { id -> Speaker.bluetoothDevices(ctx).firstOrNull { it.id == id }?.let { track.setPreferredDevice(it) } }
        Thread { run() }.start()
    }

    fun write(b: ByteArray) { q.put(b) }

    fun finish(cb: () -> Unit) { onFinished = cb; q.put(end) }

    fun abort() {
        aborted = true
        try { track.pause(); track.flush() } catch (_: Exception) {}
        q.put(end)
    }

    private fun run() {
        var written = 0L
        var started = false
        val prebuffer = rate / 2 // ~0.25 s: boshida uzilib qolmasligi uchun
        try {
            while (true) {
                val b = q.take()
                if (aborted || b === end) break
                track.write(b, 0, b.size) // bufer to'lsa kutadi
                written += b.size
                if (!started && written >= prebuffer) { track.play(); started = true }
            }
            if (!aborted) {
                if (!started) track.play()
                val frames = written / 2
                var guard = 0
                while (!aborted && track.playbackHeadPosition < frames && guard < 1200) { Thread.sleep(50); guard++ }
                Thread.sleep(120)
            }
        } catch (_: Exception) {
        } finally {
            try { track.stop() } catch (_: Exception) {}
            track.release()
            if (!aborted) main.post { onFinished?.invoke() }
        }
    }
}
