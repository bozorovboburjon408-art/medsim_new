import React, { useRef } from 'react';
import { Mic, Loader2, MicOff, Radio, Volume2, ShieldAlert } from 'lucide-react';
import { useSpeechRecording } from '../hooks/useSpeechRecording';
import AudioWaveformVisualizer from './AudioWaveformVisualizer';

/**
 * VoiceRecorder — Klinik Ovoz Yozish va PTT (Push-To-Talk) Boshqaruv Konsoli
 */
export default function VoiceRecorder({ activeMannequin, isProcessing, onAudioReady }) {
  const { isRecording, startRecording, stopRecording, audioBlob, error } = useSpeechRecording();

  const prevBlobRef = useRef(null);
  if (audioBlob && audioBlob !== prevBlobRef.current) {
    prevBlobRef.current = audioBlob;
    Promise.resolve().then(() => onAudioReady(audioBlob));
  }

  const disabled = !activeMannequin || isProcessing;

  const handlePointerDown = (e) => {
    if (disabled) return;
    e.preventDefault();
    startRecording();
  };

  const handlePointerUp = (e) => {
    if (disabled || !isRecording) return;
    e.preventDefault();
    stopRecording();
  };

  const isBaby = activeMannequin?.slug === 'chaqaloq';

  return (
    <div className="p-4 bg-slate-950 border-t border-slate-800 space-y-3 select-none">
      {/* Jonli Audio Spektr va To'lqin Visualizatori */}
      <AudioWaveformVisualizer
        isRecording={isRecording}
        isProcessing={isProcessing}
        isSpeaking={false}
      />

      {/* Asosiy PTT Tugmasi va Ma'lumot Qatori */}
      <div className="flex items-center justify-between gap-4">
        {/* Chap: Telemetriya va Format */}
        <div className="hidden sm:block text-[11px] font-mono text-slate-400 space-y-0.5">
          <div className="flex items-center gap-1.5 text-slate-300">
            <Radio size={12} className="text-blue-400" />
            <span>Kanal: <strong>WebRTC Audio</strong></span>
          </div>
          <div>Protokol: <strong>PCM 16-bit Mono</strong></div>
        </div>

        {/* O'rta: Katta PTT (Push-To-Talk) Ovoz Tugmasi */}
        <div className="flex items-center gap-4">
          <div className="relative">
            {/* Animatsion pulsatsiya doiralari */}
            {isRecording && (
              <>
                <div className="absolute inset-0 bg-rose-500 rounded-full animate-ping opacity-30 scale-[1.5]" />
                <div className="absolute inset-0 bg-rose-400 rounded-full animate-pulse opacity-20 scale-[1.8]" />
              </>
            )}

            <button
              onPointerDown={handlePointerDown}
              onPointerUp={handlePointerUp}
              onPointerLeave={handlePointerUp}
              onContextMenu={(e) => e.preventDefault()}
              disabled={disabled}
              className={`
                relative flex items-center justify-center w-16 h-16 rounded-2xl shadow-xl
                transition-all duration-200 touch-none select-none border
                ${disabled
                  ? 'bg-slate-900 border-slate-800 text-slate-600 cursor-not-allowed'
                  : isRecording
                  ? 'bg-gradient-to-tr from-rose-600 to-rose-500 border-rose-400 text-white scale-105 shadow-rose-900/50'
                  : isProcessing
                  ? 'bg-gradient-to-tr from-cyan-600 to-blue-600 border-cyan-400 text-white'
                  : 'bg-gradient-to-tr from-blue-600 to-indigo-600 border-blue-400 text-white hover:scale-105 active:scale-95 shadow-blue-900/40 cursor-pointer'
                }
              `}
            >
              {isProcessing ? (
                <Loader2 size={28} className="animate-spin" />
              ) : isRecording ? (
                <Mic size={28} className="animate-pulse" />
              ) : disabled ? (
                <MicOff size={26} />
              ) : (
                <Mic size={28} />
              )}
            </button>
          </div>

          <div>
            <div className="text-xs font-bold text-white flex items-center gap-1.5">
              <span>{isRecording ? '🔴 Yozilmoqda (Mikrofon faol)' : isProcessing ? '⚡ AI Tahlil qilinmoqda...' : 'PTT (Gapirish uchun bosing)'}</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              {disabled
                ? 'Avval chap paneldan bemorni tanlang'
                : isBaby
                ? '🍼 Chaqaloqqa gapiring (Ovozli trigger ishga tushadi)'
                : 'Tugmani bosib ushlab turing va savol bering'}
            </div>
          </div>
        </div>

        {/* O'ng: Aloqa holati */}
        <div className="hidden md:flex flex-col items-end text-[11px] font-mono text-slate-400">
          <div className="flex items-center gap-1.5 text-emerald-400 font-bold">
            <Volume2 size={13} />
            <span>Wi-Fi Routing: TAYYOR</span>
          </div>
          <span className="text-[10px] text-slate-500">Kechikish: &lt; 28ms</span>
        </div>
      </div>

      {error && (
        <div className="bg-rose-950/80 border border-rose-800 text-rose-300 text-xs px-3 py-1.5 rounded-lg flex items-center gap-2 font-mono">
          <ShieldAlert size={14} className="text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
