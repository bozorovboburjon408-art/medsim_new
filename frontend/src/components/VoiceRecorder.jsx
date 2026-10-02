import React, { useRef } from 'react';
import { Mic, Loader2, MicOff } from 'lucide-react';
import { useSpeechRecording } from '../hooks/useSpeechRecording';

/**
 * VoiceRecorder — Sodda, oq va qulay mikrofon paneli
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
    <div className="flex flex-col items-center justify-center p-5 bg-gradient-to-t from-slate-50 to-white border-t border-slate-200 select-none">
      {/* Mikrofon tugmasi */}
      <div className="relative">
        {/* Pulsatsiya animatsiyasi */}
        {isRecording && (
          <>
            <div className="absolute inset-0 bg-red-400 rounded-full animate-ping opacity-30 scale-[1.4]" />
            <div className="absolute inset-0 bg-red-300 rounded-full animate-pulse opacity-20 scale-[1.6]" />
          </>
        )}

        <button
          onPointerDown={handlePointerDown}
          onPointerUp={handlePointerUp}
          onPointerLeave={handlePointerUp}
          onContextMenu={(e) => e.preventDefault()}
          disabled={disabled}
          title={!activeMannequin ? "Avval manikenni tanlang" : "Gapirish uchun bosib ushlab turing"}
          className={`
            relative flex items-center justify-center w-20 h-20 rounded-full shadow-md
            transition-all duration-200 touch-none select-none cursor-pointer
            ${disabled
              ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
              : isRecording
              ? 'bg-red-500 text-white scale-110 shadow-red-200 shadow-xl'
              : 'bg-blue-600 text-white hover:bg-blue-700 hover:scale-105 active:scale-95 shadow-blue-200'
            }
          `}
        >
          {isProcessing ? (
            <Loader2 size={36} className="animate-spin" />
          ) : isRecording ? (
            <Mic size={36} className="animate-pulse" />
          ) : disabled ? (
            <MicOff size={32} />
          ) : (
            <Mic size={36} />
          )}
        </button>
      </div>

      {/* Holat matni */}
      <div className="mt-3 text-center h-8 flex items-center justify-center">
        {error && (
          <span className="text-red-500 text-xs font-semibold">{error}</span>
        )}
        {!error && isProcessing && (
          <div className="flex items-center gap-2 text-blue-600 font-semibold text-xs">
            <Loader2 size={15} className="animate-spin" />
            <span>Bemor javobini kutish...</span>
          </div>
        )}
        {!error && !isProcessing && isRecording && (
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 bg-red-500 rounded-full animate-pulse" />
            <span className="text-red-600 font-bold text-xs">Yozilmoqda... Gapiring!</span>
          </div>
        )}
        {!error && !isProcessing && !isRecording && activeMannequin && (
          <span className="text-slate-500 text-xs font-medium">
            {isBaby
              ? '🍼 Chaqaloq — gapirish uchun tugmani bosing'
              : '🎤 Gapirish uchun tugmani bosib ushlab turing'}
          </span>
        )}
        {!activeMannequin && (
          <span className="text-slate-400 text-xs">⬅️ Avval chap paneldan bemorni tanlang</span>
        )}
      </div>
    </div>
  );
}
