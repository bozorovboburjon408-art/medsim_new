package uz.medsim

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothClass
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioAttributes
import android.media.AudioDeviceInfo
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.ParcelFileDescriptor
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
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withTimeoutOrNull
import kotlin.coroutines.resume

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

    /** Telefon ovoz tizimidagi hozirgi Bluetooth chiqishlar (A2DP, LE Audio va h.k.). */
    fun bluetoothDevices(ctx: Context): List<AudioDeviceInfo> {
        val am = ctx.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        // SCO (telefon qo'ng'irog'i kanali) ataylab kiritilmagan: bir kalonka A2DP va SCO sifatida ikki marta ko'rinadi, SCO ga ovoz yuborsak jim bo'lib qoladi
        val types = mutableSetOf(AudioDeviceInfo.TYPE_BLUETOOTH_A2DP, AudioDeviceInfo.TYPE_HEARING_AID)
        if (android.os.Build.VERSION.SDK_INT >= 31) {
            types.add(AudioDeviceInfo.TYPE_BLE_HEADSET); types.add(AudioDeviceInfo.TYPE_BLE_SPEAKER)
        }
        return am.getDevices(AudioManager.GET_DEVICES_OUTPUTS).filter { it.type in types }
    }

    /** Saqlangan manzil bo'yicha hozirgi ovoz qurilmasi (ulangan bo'lsa), aks holda null: ovoz telefon dinamigidan chiqadi. */
    fun resolve(ctx: Context, address: String?): Int? {
        if (address.isNullOrBlank()) return null
        return bluetoothDevices(ctx).firstOrNull { it.address.equals(address, true) }?.id
    }

    data class Spk(val address: String, val name: String, val connected: Boolean)

    /** Tanlangan kalonkaga qisqa sinov signali (880 Hz). Kalonka ovoz tizimida faol bo'lmasa false. */
    fun testTone(ctx: Context, address: String): Boolean {
        val id = resolve(ctx, address) ?: return false
        val p = PcmPlayer(RATE, id, bluetoothDevices(ctx))
        val beep = RATE * 700 / 1000
        val gap = RATE * 350 / 1000
        val n = beep * 2 + gap
        val b = ByteArray(n * 2)
        for (k in 0 until 2) for (i in 0 until beep) {
            val env = minOf(1.0, minOf(i, beep - i) / (RATE * 0.05))
            val v = (Math.sin(2.0 * Math.PI * 880.0 * i / RATE) * 14000.0 * env).toInt()
            val idx = (k * (beep + gap) + i) * 2
            b[idx] = (v and 0xFF).toByte(); b[idx + 1] = (v shr 8).toByte()
        }
        p.write(b); p.finish {}
        return true
    }

    /** Tizimning "ovoz chiqishi" paneli (faol Bluetooth kalonkani almashtirish). Eski Android'da Bluetooth sozlamalari. */
    fun openOutputSwitcher(ctx: Context) {
        try {
            if (android.os.Build.VERSION.SDK_INT >= 34) {
                android.media.MediaRouter2.getInstance(ctx).showSystemOutputSwitcher()
                return
            }
        } catch (_: Exception) {}
        try {
            ctx.startActivity(android.content.Intent(android.provider.Settings.ACTION_BLUETOOTH_SETTINGS).addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK))
        } catch (_: Exception) {}
    }

    /** 0 = qurilmada Bluetooth yo'q, 1 = o'chiq, 2 = yoqilgan, 3 = ruxsat berilmagan. */
    @SuppressLint("MissingPermission")
    fun btState(ctx: Context): Int {
        if (ctx.checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) return 3
        val ad = (ctx.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager)?.adapter ?: return 0
        return if (ad.isEnabled) 2 else 1
    }

    /** Hozir ulangan Bluetooth ovoz qurilmalari manzillari (A2DP profili bo'yicha, bir nechta bo'lishi mumkin). */
    @SuppressLint("MissingPermission")
    private suspend fun a2dpConnected(ctx: Context, adapter: BluetoothAdapter): Set<String> = withTimeoutOrNull(1500) {
        suspendCancellableCoroutine<Set<String>> { cont ->
            val l = object : BluetoothProfile.ServiceListener {
                override fun onServiceConnected(profile: Int, proxy: BluetoothProfile) {
                    val set = try { proxy.connectedDevices.map { it.address }.toSet() } catch (_: Exception) { emptySet() }
                    try { adapter.closeProfileProxy(profile, proxy) } catch (_: Exception) {}
                    if (cont.isActive) cont.resume(set)
                }
                override fun onServiceDisconnected(profile: Int) {}
            }
            val ok = try { adapter.getProfileProxy(ctx, l, BluetoothProfile.A2DP) } catch (_: Exception) { false }
            if (!ok && cont.isActive) cont.resume(emptySet())
        }
    } ?: emptySet()

    /** Telefonga juftlangan (paired) HAMMA audio qurilmalar + hozir ulangan/faol qurilmalar. Ulanganlar tepada. */
    @SuppressLint("MissingPermission")
    suspend fun speakers(ctx: Context): List<Spk> {
        val out = linkedMapOf<String, Spk>()
        val active = bluetoothDevices(ctx)
        val activeAddr = active.map { it.address.uppercase() }.toSet()
        val granted = ctx.checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) == PackageManager.PERMISSION_GRANTED
        val adapter = (ctx.getSystemService(Context.BLUETOOTH_SERVICE) as? BluetoothManager)?.adapter
        if (granted && adapter != null) {
            val connected = a2dpConnected(ctx, adapter).map { it.uppercase() }.toSet() + activeAddr
            try {
                for (d in adapter.bondedDevices) {
                    val major = d.bluetoothClass?.majorDeviceClass
                    if (major != null && major != BluetoothClass.Device.Major.AUDIO_VIDEO) continue  // telefon, soat va h.k. emas
                    val nm = (if (android.os.Build.VERSION.SDK_INT >= 30) d.alias else null) ?: d.name ?: d.address
                    out[d.address.uppercase()] = Spk(d.address, nm, d.address.uppercase() in connected)
                }
            } catch (_: SecurityException) {}
        }
        for (d in active) {  // ro'yxatda yo'q, lekin faol qurilma
            val k = d.address.uppercase()
            if (k !in out) out[k] = Spk(d.address, d.productName?.toString() ?: d.address, true)
        }
        return out.values.sortedWith(compareByDescending<Spk> { it.connected }.thenBy { it.name.lowercase() })
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

    /** Ovoz kuchaytirish koeffitsiyenti (1 = o'zgarishsiz). Sozlamalardan o'rnatiladi. */
    @Volatile var gain = 2.0f

    /** Raqamli kuchaytirish: 60% dan yuqori cho'qqilar yumshoq cheklanadi (tanh), shuning uchun baqirmaydi va buzilmaydi. */
    private fun amplify(b: ByteArray): ByteArray {
        val g = gain
        if (g <= 1.001f) return b
        val out = ByteArray(b.size)
        var i = 0
        while (i + 1 < b.size) {
            val v = ((b[i].toInt() and 0xFF) or (b[i + 1].toInt() shl 8)).toShort().toInt()
            val x = v * g / 32768.0
            val ax = Math.abs(x)
            val y = if (ax < 0.6) x else Math.signum(x) * (0.6 + 0.4 * Math.tanh((ax - 0.6) / 0.4))
            val o = (y * 32767.0).toInt().coerceIn(-32768, 32767)
            out[i] = (o and 0xFF).toByte(); out[i + 1] = (o shr 8).toByte()
            i += 2
        }
        return out
    }

    fun writePcm(ctx: Context, bytes: ByteArray, rate: Int) {
        val p = pcm ?: PcmPlayer(RATE, dev, bluetoothDevices(ctx)).also { pcm = it }
        p.write(amplify(if (rate == RATE) bytes else resample(bytes, rate, RATE)))
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
        deviceId?.let { id ->
            val d = btDevices.firstOrNull { it.id == id }
            // faol A2DP kalonka yagona bo'lsa, tizim ovozni o'zi shu yerga yo'naltiradi; setPreferredDevice trekni 'o'ldirib' qayta yaratadi
            val onlyA2dp = d != null && d.type == AudioDeviceInfo.TYPE_BLUETOOTH_A2DP && btDevices.count { it.type == AudioDeviceInfo.TYPE_BLUETOOTH_A2DP } == 1
            if (d != null && !onlyA2dp) t.setPreferredDevice(d)
        }
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
            writeAll(quiet(1100))  // 1.1 s kuchsiz shovqin: ovoz yo'li va kalonka uyg'onadi
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


/**
 * Planshetning ICHKI mikrofonidan yozadi va ovoz tanish moduliga (Android 13+: EXTRA_AUDIO_SOURCE) oqim sifatida beradi.
 * Shunda Bluetooth kalonka faqat ovoz chiqarish uchun ishlaydi: tanish moduli kalonkaning mikrofoniga (garnitura rejimi) o'tmaydi.
 */
class OwnMic(ctx: Context, private val onLevel: (Float) -> Unit) {
    private val pipe = ParcelFileDescriptor.createPipe()
    val readFd: ParcelFileDescriptor get() = pipe[0]
    @Volatile private var running = true
    private val main = Handler(Looper.getMainLooper())

    init {
        val rate = 16000
        val min = AudioRecord.getMinBufferSize(rate, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        val r = AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION, rate, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, maxOf(min, rate * 2))
        val am = ctx.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        am.getDevices(AudioManager.GET_DEVICES_INPUTS).firstOrNull { it.type == AudioDeviceInfo.TYPE_BUILTIN_MIC }?.let { r.setPreferredDevice(it) }
        Thread { loop(r) }.start()
    }

    private fun loop(r: AudioRecord) {
        val out = ParcelFileDescriptor.AutoCloseOutputStream(pipe[1])
        val buf = ByteArray(3200)  // 0.1 s
        try {
            r.startRecording()
            while (running) {
                val n = r.read(buf, 0, buf.size)
                if (n <= 0) break
                out.write(buf, 0, n)
                var sum = 0.0
                var i = 0
                while (i + 1 < n) { val v = (buf[i].toInt() and 0xFF) or (buf[i + 1].toInt() shl 8); sum += v.toDouble() * v; i += 2 }
                val rms = Math.sqrt(sum / (n / 2))
                main.post { onLevel((rms / 2500.0).toFloat().coerceIn(0f, 1f)) }
            }
        } catch (_: Exception) {
        } finally {
            try { r.stop() } catch (_: Exception) {}
            r.release()
            try { out.close() } catch (_: Exception) {}
        }
    }

    fun stop() {
        running = false
        try { pipe[0].close() } catch (_: Exception) {}
    }
}
