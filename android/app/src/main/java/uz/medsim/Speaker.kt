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
        queue.clear(); playing = false; expectMore = false
        pcm?.abort(); pcm = null
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

    // ---- Gap-gap oqim ijrosi: kelgan mp3 bo'laklari ketma-ket chalinadi ----
    private val queue = ArrayDeque<File>()
    private var playing = false
    private var expectMore = false
    private var seq = 0
    private var idleCb: () -> Unit = {}
    private var dev: Int? = null

    fun beginStream(deviceId: Int?, onIdle: () -> Unit) {
        stop(); expectMore = true; dev = deviceId; idleCb = onIdle
    }

    fun enqueue(ctx: Context, bytes: ByteArray, ext: String = "mp3") {
        val f = File(ctx.cacheDir, "seg_${seq++}.$ext").also { it.writeBytes(bytes) }
        queue.addLast(f)
        if (!playing) playNext(ctx)
    }

    fun endStream() {
        expectMore = false
        val p = pcm
        if (p != null) {
            p.finish { pcm = null; if (!playing && queue.isEmpty()) idleCb() }
        } else if (!playing && queue.isEmpty()) idleCb()
    }

    // ---- Xom PCM oqimi (Gemini): kelgan bo'laklar darrov chalinadi ----
    private var pcm: PcmPlayer? = null

    fun writePcm(ctx: Context, bytes: ByteArray, rate: Int) {
        val p = pcm ?: PcmPlayer(ctx, rate, dev).also { pcm = it }
        p.write(bytes)
    }

    private fun playNext(ctx: Context) {
        val f = queue.removeFirstOrNull()
        if (f == null) {
            playing = false
            if (!expectMore) idleCb()
            return
        }
        playing = true
        val p = MediaPlayer()
        try {
            p.setDataSource(f.absolutePath)
            dev?.let { id -> bluetoothDevices(ctx).firstOrNull { it.id == id }?.let { p.setPreferredDevice(it) } }
            p.setOnCompletionListener { it.release(); f.delete(); playNext(ctx) }
            p.setOnErrorListener { mp, _, _ -> mp.release(); f.delete(); playNext(ctx); true }
            p.prepare(); p.start()
            player = p
        } catch (e: Exception) {
            p.release(); playNext(ctx)
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
