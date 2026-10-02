import React, { useEffect, useState } from 'react';
import { Mic, Volume2, Radio } from 'lucide-react';

/**
 * AudioWaveformVisualizer — Akustik Oqim va Spektr Analizatori
 * Hamshira mikrofonga gapirganda va maniken javob berganda jonli ekvalayzer to'lqinlarini render qiladi.
 */
export default function AudioWaveformVisualizer({ isRecording, isProcessing, isSpeaking }) {
  const [bars, setBars] = useState(Array.from({ length: 24 }, () => 15));

  useEffect(() => {
    let interval;
    if (isRecording || isSpeaking) {
      interval = setInterval(() => {
        setBars(
          Array.from({ length: 24 }, (_, i) => {
            const center = Math.abs(i - 12);
            const factor = Math.max(0.2, 1 - center / 14);
            const randomHeight = Math.floor(Math.random() * 65 + 15) * factor;
            return Math.min(80, Math.max(10, randomHeight));
          })
        );
      }, 70);
    } else {
      setBars(Array.from({ length: 24 }, () => 8));
    }
    return () => clearInterval(interval);
  }, [isRecording, isSpeaking]);

  return (
    <div className="flex items-center justify-between px-4 py-2 bg-slate-900/90 rounded-xl border border-slate-800 shadow-inner select-none">
      {/* Status indikatori */}
      <div className="flex items-center gap-2">
        {isRecording ? (
          <div className="flex items-center gap-1.5 text-rose-400 font-mono text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping"></span>
            <Mic size={14} className="animate-pulse" />
            <span>AKUSTIK KANAL: Yozilmoqda...</span>
          </div>
        ) : isProcessing ? (
          <div className="flex items-center gap-1.5 text-cyan-400 font-mono text-xs font-semibold">
            <Radio size={14} className="animate-spin text-cyan-400" />
            <span>KLINIK NLU TAHLIL VA GUARDRAILS...</span>
          </div>
        ) : isSpeaking ? (
          <div className="flex items-center gap-1.5 text-emerald-400 font-mono text-xs font-semibold">
            <Volume2 size={14} className="animate-bounce" />
            <span>ESP32 I2S OVOZ TRAKTI AKTIV</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 text-slate-400 font-mono text-xs">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-600"></span>
            <span>PCM 16kHz / 16-bit Mono (Kutish rejimida)</span>
          </div>
        )}
      </div>

      {/* Ekvalayzer to'lqinlari */}
      <div className="flex items-center gap-1 h-8 px-2">
        {bars.map((height, idx) => (
          <div
            key={idx}
            style={{ height: `${height}%` }}
            className={`w-1 rounded-full transition-all duration-75 ${
              isRecording
                ? 'bg-gradient-to-t from-rose-500 to-rose-300'
                : isSpeaking
                ? 'bg-gradient-to-t from-emerald-500 to-emerald-300'
                : isProcessing
                ? 'bg-gradient-to-t from-cyan-500 to-cyan-300 animate-pulse'
                : 'bg-slate-700/60'
            }`}
          />
        ))}
      </div>
    </div>
  );
}
