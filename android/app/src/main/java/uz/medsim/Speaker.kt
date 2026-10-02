package uz.medsim

import android.content.Context
import android.media.AudioDeviceInfo
import android.media.AudioManager
import android.media.MediaPlayer
import java.io.File

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
        } catch (e: Exception) { false }
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

    fun enqueue(ctx: Context, bytes: ByteArray) {
        val f = File(ctx.cacheDir, "seg_${seq++}.mp3").also { it.writeBytes(bytes) }
        queue.addLast(f)
        if (!playing) playNext(ctx)
    }

    fun endStream() {
        expectMore = false
        if (!playing && queue.isEmpty()) idleCb()
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
