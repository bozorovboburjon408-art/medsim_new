package uz.medsim

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioDeviceInfo
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioTrack
import android.media.MediaCodec
import android.media.MediaExtractor
import android.media.MediaFormat
import android.media.MediaPlayer
import android.os.Handler
import android.os.Looper
import android.util.Log
import java.io.ByteArrayOutputStream
import java.io.File
import java.util.concurrent.Executors
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

/**
 * Bemor ovozi. Hamma gaplar (ElevenLabs PCM ham, Edge mp3 ham) bitta uzluksiz AudioTrack oqimiga tushadi:
 * - javob so'ralishi bilan oqim ochilib, 0.45 s sukunat yoziladi (telefon ovoz yo'li uyg'onadi, gap boshi kesilmaydi);
 * - mp3 avval PCM ga aylantiriladi, gaplar orasida yo'l yopilmaydi;
 * - oqim tizim tomonidan yopib qo'yilsa (dead object) qayta yaratiladi.
 */
object Speaker {
    private const val RATE = 24000
    private val main = Handler(Looper.getMainLooper())
    private val decodeExec = Executors.newSingleThreadExecutor()

    fun bluetoothDevices(ctx: Context): List<AudioDeviceInfo> {
        val am = ctx.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        return am.getDevices(AudioManager.GET_DEVICES_OUTPUTS)
            .filter { it.type == AudioDeviceInfo.TYPE_BLUETOOTH_A2DP }
    }

    // ---- Oddiy fayllar (chaqaloq yig'isi/kulgisi)
    private var player: MediaPlayer? = null

    fun setVolume(v: Float) { player?.setVolume(v, v) }

    fun stop() {
        gen.incrementAndGet(); pending.set(0); expectMore = false
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

    // ---- Suhbat oqimi
    private val gen = AtomicInteger(0)       // har stop()/beginStream() da oshadi: eski dekodlash natijasi tashlab yuboriladi
    private val pending = AtomicInteger(0)   // hali PCM ga aylantirilmagan mp3 bo'laklar
    private var expectMore = false
    private var idleCb: () -> Unit = {}
    private var dev: Int? = null
    private var pcm: PcmPlayer? = null
    private var seq = 0

    /** Javob so'ralishi bilan chaqiriladi: ovoz yo'li oldindan uyg'otiladi. */
    fun beginStream(ctx: Context, deviceId: Int?, onIdle: () -> Unit) {
        stop(); expectMore = true; dev = deviceId; idleCb = onIdle
        pcm = PcmPlayer(RATE, deviceId, bluetoothDevices(ctx))
        Log.d("SPK", "beginStream: oqim ochildi, yo'l uyg'otilmoqda")
    }

    fun writePcm(ctx: Context, bytes: ByteArray, rate: Int) {
        val p = pcm ?: PcmPlayer(RATE, dev, bluetoothDevices(ctx)).also { pcm = it }
        p.write(if (rate == RATE) bytes else resample(bytes, rate, RATE))
    }

    /** Edge mp3 bo'lagi: PCM ga aylantirilib (orqa oqimda, tartib saqlanadi) umumiy oqimga yoziladi. */
    fun enqueue(ctx: Context, bytes: ByteArray, ext: String = "mp3") {
        val g = gen.get()
        pending.incrementAndGet()
        val f = File(ctx.cacheDir, "seg_${seq++}.$ext").also { it.writeBytes(bytes) }
        decodeExec.execute {
            val r = runCatching { Mp3.decode(f) }.getOrNull()
            f.delete()
            main.post {
                pending.decrementAndGet()
                if (gen.get() == g) {
                    if (r != null) writePcm(ctx, r.first, r.second) else Log.d("SPK", "mp3 dekodlanmadi")
                    tryFinish()
                }
            }
        }
    }

    fun endStream() {
        expectMore = false
        tryFinish()
    }

    private fun tryFinish() {
        if (expectMore || pending.get() > 0) return
        val p = pcm
        pcm = null
        if (p != null) p.finish { idleCb() } else idleCb()
    }

    private fun resample(src: ByteArray, from: Int, to: Int): ByteArray {
        val n = src.size / 2
        if (n < 2) return src
        val outN = (n.toLong() * to / from).toInt()
        val out = ByteArray(outN * 2)
        for (i in 0 until outN) {
            val pos = i.toDouble() * from / to
            val i0 = pos.toInt().coerceAtMost(n - 1)
            val i1 = (i0 + 1).coerceAtMost(n - 1)
            val fr = pos - i0
            val a = (src[i0 * 2].toInt() and 0xFF) or (src[i0 * 2 + 1].toInt() shl 8)
            val b = (src[i1 * 2].toInt() and 0xFF) or (src[i1 * 2 + 1].toInt() shl 8)
            val v = (a + (b - a) * fr).toInt().coerceIn(-32768, 32767)
            out[i * 2] = (v and 0xFF).toByte(); out[i * 2 + 1] = (v shr 8).toByte()
        }
        return out
    }
}

/** mp3 -> 16-bit mono PCM (MediaCodec). */
object Mp3 {
    fun decode(file: File): Pair<ByteArray, Int>? {
        val ex = MediaExtractor()
        try {
            ex.setDataSource(file.absolutePath)
            var idx = -1
            for (i in 0 until ex.trackCount) {
                if (ex.getTrackFormat(i).getString(MediaFormat.KEY_MIME)?.startsWith("audio/") == true) { idx = i; break }
            }
            if (idx < 0) return null
            ex.selectTrack(idx)
            val fmt = ex.getTrackFormat(idx)
            val codec = MediaCodec.createDecoderByType(fmt.getString(MediaFormat.KEY_MIME)!!)
            codec.configure(fmt, null, null, 0)
            codec.start()
            var rate = fmt.getInteger(MediaFormat.KEY_SAMPLE_RATE)
            var ch = fmt.getInteger(MediaFormat.KEY_CHANNEL_COUNT)
            val out = ByteArrayOutputStream()
            val info = MediaCodec.BufferInfo()
            var inEos = false
            var outEos = false
            var guard = 0
            while (!outEos && guard++ < 20000) {
                if (!inEos) {
                    val i = codec.dequeueInputBuffer(10000)
                    if (i >= 0) {
                        val buf = codec.getInputBuffer(i)!!
                        val n = ex.readSampleData(buf, 0)
                        if (n < 0) { codec.queueInputBuffer(i, 0, 0, 0, MediaCodec.BUFFER_FLAG_END_OF_STREAM); inEos = true }
                        else { codec.queueInputBuffer(i, 0, n, ex.sampleTime, 0); ex.advance() }
                    }
                }
                val o = codec.dequeueOutputBuffer(info, 10000)
                if (o >= 0) {
                    val b = codec.getOutputBuffer(o)!!
                    val chunk = ByteArray(info.size)
                    b.position(info.offset); b.get(chunk)
                    out.write(chunk)
                    codec.releaseOutputBuffer(o, false)
                    if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) outEos = true
                } else if (o == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED) {
                    val nf = codec.outputFormat
                    rate = nf.getInteger(MediaFormat.KEY_SAMPLE_RATE)
                    ch = nf.getInteger(MediaFormat.KEY_CHANNEL_COUNT)
                }
            }
            codec.stop(); codec.release()
            var pcm = out.toByteArray()
            if (ch == 2) {  // stereo -> mono
                val m = ByteArray(pcm.size / 2)
                for (i in 0 until pcm.size / 4) {
                    val l = (pcm[i * 4].toInt() and 0xFF) or (pcm[i * 4 + 1].toInt() shl 8)
                    val r = (pcm[i * 4 + 2].toInt() and 0xFF) or (pcm[i * 4 + 3].toInt() shl 8)
                    val v = (l + r) / 2
                    m[i * 2] = (v and 0xFF).toByte(); m[i * 2 + 1] = (v shr 8).toByte()
                }
                pcm = m
            }
            return pcm to rate
        } finally {
            ex.release()
        }
    }
}

/** 16-bit mono PCM ni AudioTrack (MODE_STREAM) orqali uzluksiz chaladi. Boshida sukunat yoziladi (yo'l uyg'onishi uchun). */
class PcmPlayer(private val rate: Int, private val deviceId: Int?, private val btDevices: List<AudioDeviceInfo>) {
    private var track: AudioTrack = build()
    private val q = LinkedBlockingQueue<ByteArray>()
    private val end = ByteArray(0)
    @Volatile private var aborted = false
    @Volatile private var onFinished: (() -> Unit)? = null
    private val main = Handler(Looper.getMainLooper())

    init { Thread { run() }.start() }

    private fun build(): AudioTrack {
        val min = AudioTrack.getMinBufferSize(rate, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_16BIT)
        val t = AudioTrack.Builder()
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
        deviceId?.let { id -> btDevices.firstOrNull { it.id == id }?.let { t.setPreferredDevice(it) } }
        return t
    }

    fun write(b: ByteArray) { q.put(b) }

    fun finish(cb: () -> Unit) { onFinished = cb; q.put(end) }

    fun abort() {
        aborted = true
        try { track.pause(); track.flush() } catch (_: Exception) {}
        q.put(end)
    }

    private var framesOnTrack = 0L
    private val rnd = java.util.Random()

    /** Eshitilmaydigan darajada (~-62 dB) kuchsiz shovqin: Bluetooth kalonka mutlaqo jim signalni ko'rib o'zini yopib qo'ymasin. */
    private fun quiet(ms: Int): ByteArray {
        val n = rate * ms / 1000
        val b = ByteArray(n * 2)
        for (i in 0 until n) {
            val v = rnd.nextInt(49) - 24
            b[i * 2] = (v and 0xFF).toByte(); b[i * 2 + 1] = (v shr 8).toByte()
        }
        return b
    }

    /** Hammasini yozadi; tizim oqimni yopib qo'ysa (xato kodi) qayta yaratib davom etadi. */
    private fun writeAll(b: ByteArray) {
        var off = 0
        var fails = 0
        while (off < b.size && !aborted) {
            val n = track.write(b, off, b.size - off)
            if (n < 0) {
                Log.d("SPK", "AudioTrack.write xato $n: oqim qayta yaratiladi")
                if (++fails > 3) return
                try { track.release() } catch (_: Exception) {}
                track = build(); track.play(); framesOnTrack = 0
                continue
            }
            off += n
            framesOnTrack += n / 2
        }
    }

    private fun run() {
        try {
            track.play()
            writeAll(quiet(700))  // 0.7 s kuchsiz shovqin: ovoz yo'li va kalonka uyg'onadi
            Log.d("SPK", "PCM oqimi ishga tushdi (yo'l uyg'otildi)")
            var total = 0L
            while (true) {
                val b = q.poll(60, TimeUnit.MILLISECONDS)
                if (b == null) {
                    // pauza: oqim ochiq turishi uchun yengil sukunat yoziladi (Bluetooth kalonka uxlab qolmaydi, keyingi gap boshi kesilmaydi)
                    if (!aborted) {
                        val ahead = framesOnTrack - track.playbackHeadPosition
                        if (ahead < rate / 8) writeAll(quiet(100))
                    }
                    continue
                }
                if (aborted || b === end) break
                writeAll(b)
                total += b.size
            }
            if (!aborted) {
                var guard = 0
                while (!aborted && track.playbackHeadPosition < framesOnTrack && guard < 1500) { Thread.sleep(40); guard++ }
                Thread.sleep(150)
                Log.d("SPK", "PCM tugadi, yozilgan=${total}B underrun=${if (android.os.Build.VERSION.SDK_INT >= 24) track.underrunCount else -1}")
            }
        } catch (_: Exception) {
        } finally {
            try { track.stop() } catch (_: Exception) {}
            track.release()
            if (!aborted) main.post { onFinished?.invoke() }
        }
    }
}


/**
 * Ovoz tanish moduli boshlanganda/tugaganda "qung" tovushi chiqaradi. Eshitish paytida tizim ovozlarini vaqtincha o'chirib turamiz
 * (faqat o'zimiz o'chirganlarni qaytaramiz); bemor gapirishidan oldin qaytariladi.
 */
object Beep {
    private val streams = intArrayOf(AudioManager.STREAM_MUSIC, AudioManager.STREAM_NOTIFICATION, AudioManager.STREAM_SYSTEM)
    private val ours = mutableSetOf<Int>()

    fun mute(ctx: Context) {
        val am = ctx.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        for (st in streams) {
            if (st in ours) continue
            try {
                if (!am.isStreamMute(st)) { am.adjustStreamVolume(st, AudioManager.ADJUST_MUTE, 0); ours.add(st) }
            } catch (_: Exception) {}
        }
    }

    fun unmute(ctx: Context) {
        if (ours.isEmpty()) return
        val am = ctx.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        for (st in ours) {
            try { am.adjustStreamVolume(st, AudioManager.ADJUST_UNMUTE, 0) } catch (_: Exception) {}
        }
        ours.clear()
    }
}
