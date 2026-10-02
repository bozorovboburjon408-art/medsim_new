import React, { useState, useRef } from 'react';
import { Mic, Loader2, MicOff, Send } from 'lucide-react';
import { useSpeechRecording } from '../hooks/useSpeechRecording';

/**
 * VoiceRecorder — Ovozli va Matnli muloqot konsoli
 */
export default function VoiceRecorder({ activeMannequin, isProcessing, onAudioReady, onTextSubmit }) {
  const { isRecording, startRecording, stopRecording, audioBlob, transcript, error } = useSpeechRecording();
  const [inputText, setInputText] = useState('');

  const prevBlobRef = useRef(null);
  if (audioBlob && audioBlob !== prevBlobRef.current) {
    prevBlobRef.current = audioBlob;
    Promise.resolve().then(() => onAudioReady({ audioBlob, transcript }));
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

  const handleTextSubmit = (e) => {
    e.preventDefault();
    if (!inputText.trim() || disabled) return;
    onTextSubmit(inputText.trim());
    setInputText('');
  };

  const isBaby = activeMannequin?.slug === 'chaqaloq';

  return (
    <div className="flex flex-col p-4 bg-gradient-to-t from-slate-50 to-white border-t border-slate-200 select-none space-y-3">
      
      {/* Mikrofon va Jonli Ovozli PTT */}
      <div className="flex items-center justify-center gap-4">
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
            title={!activeMannequin ? "Avval bemorni tanlang" : "Gapirish uchun bosib ushlab turing"}
            className={`
              relative flex items-center justify-center w-16 h-16 rounded-full shadow-md
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
              <Loader2 size={30} className="animate-spin" />
            ) : isRecording ? (
              <Mic size={30} className="animate-pulse" />
            ) : disabled ? (
              <MicOff size={26} />
            ) : (
              <Mic size={30} />
            )}
          </button>
        </div>

        <div className="text-left">
          <div className="text-xs font-bold text-slate-800">
            {isRecording ? '🔴 Tinglamoqda... Gapiring!' : isProcessing ? '⚡ DeepSeek AI javob tayyorlamoqda...' : 'Gapirish uchun bosib turing'}
          </div>
          <div className="text-[11px] text-slate-500 mt-0.5 max-w-xs truncate">
            {transcript ? `"${transcript}"` : (isBaby ? 'Chaqaloq tovushli javob qaytaradi' : 'Savolingiz avtomatik aniqlanadi va eshittiriladi')}
          </div>
        </div>
      </div>

      {/* Matnli tezkor savol kiritish (Qo'lda yozish ham mumkin) */}
      <form onSubmit={handleTextSubmit} className="flex items-center gap-2">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder={disabled ? "Avval bemorni tanlang..." : "Yoki savolingizni shu yerga yozib yuboring..."}
          disabled={disabled}
          className="flex-1 bg-white border border-slate-300 text-slate-800 text-xs rounded-xl px-3.5 py-2.5 outline-none
                     focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-100 disabled:cursor-not-allowed"
        />
        <button
          type="submit"
          disabled={disabled || !inputText.trim()}
          className="bg-blue-600 hover:bg-blue-700 text-white p-2.5 rounded-xl transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer shadow-xs"
        >
          <Send size={15} />
        </button>
      </form>

      {error && (
        <div className="text-red-500 text-[11px] font-semibold text-center">{error}</div>
      )}
    </div>
  );
}
