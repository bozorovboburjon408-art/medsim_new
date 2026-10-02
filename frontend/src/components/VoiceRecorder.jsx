import React, { useState, useRef, useEffect } from 'react';
import { Mic, Loader2, MicOff, Send, Sparkles } from 'lucide-react';
import { useSpeechRecording } from '../hooks/useSpeechRecording';

/**
 * VoiceRecorder — Ovozli va Matnli muloqot konsoli
 */
export default function VoiceRecorder({ activeMannequin, isProcessing, onAudioReady, onTextSubmit }) {
  const { isRecording, startRecording, stopRecording, audioBlob, transcript, getTranscript, error } = useSpeechRecording();
  const [inputText, setInputText] = useState('');
  const [liveText, setLiveText] = useState('');

  // Transkript jonli yangilanib borishi
  useEffect(() => {
    if (transcript) {
      setLiveText(transcript);
    }
  }, [transcript]);

  // Audio va Transkript tayyor bo'lganda yuborish
  const prevBlobRef = useRef(null);
  useEffect(() => {
    if (audioBlob && audioBlob !== prevBlobRef.current) {
      prevBlobRef.current = audioBlob;
      const finalTranscript = getTranscript() || transcript || liveText;
      onAudioReady({ audioBlob, transcript: finalTranscript });
      setLiveText('');
    }
  }, [audioBlob, transcript, liveText, getTranscript, onAudioReady]);

  const disabled = !activeMannequin || isProcessing;

  const handleMicClick = () => {
    if (disabled) return;
    if (isRecording) {
      const capturedText = (liveText || transcript || getTranscript() || '').trim();
      stopRecording();
      if (capturedText) {
        onTextSubmit(capturedText);
        setLiveText('');
      }
    } else {
      setLiveText('');
      startRecording();
    }
  };

  const handleTextSubmit = (e) => {
    e.preventDefault();
    if (!inputText.trim() || disabled) return;
    onTextSubmit(inputText.trim());
    setInputText('');
  };

  const handleChipClick = (question) => {
    if (disabled) return;
    onTextSubmit(question);
  };

  // Har bir bemor uchun tezkor professional tibbiy savollar
  const getQuickQuestions = () => {
    if (!activeMannequin) return [];
    switch (activeMannequin.slug) {
      case 'homilador':
        return [
          "Ahvolingiz qanday, qayeringiz og'riyapti?",
          "Qon bosimi va haroratingizni o'lchaymiz",
          "Siydik rangida o'zgarish bormi?",
          "Bolangiz qimirlayaptimi?",
          "Shifoxonaga yotishingiz zarur"
        ];
      case 'bobo':
        return [
          "Assalomu alaykum Salomat buvi, ahvolingiz qanday?",
          "Qon bosimi va qand miqdorini o'lchaymiz",
          "Chanqash va og'iz qurishi bormi?",
          "Tovondagi yara qachondan bitmayapti?",
          "Parhezga va metformin dorisiga rioya qiling",
          "Tovonga spirt/yod surtmang, iliq suvda yuving"
        ];
      case 'bola':
        return [
          "Assalomu alaykum Nilufar opa, Jasurbek qanday?",
          "Tunda qichishish va tish g'ijirlatish bormi?",
          "Kindik atrofida og'riq bormi?",
          "Barcha oila a'zolari bir vaqtda dori ichishi shart",
          "Tirnoqlarini kalta oling, kiyimlarni qaynoq dazmollang"
        ];
      default:
        return ["Ahvolingiz qanday?"];
    }
  };

  const quickQuestions = getQuickQuestions();
  const isBaby = activeMannequin?.slug === 'chaqaloq';

  return (
    <div className="flex flex-col p-3.5 bg-gradient-to-t from-slate-50 to-white border-t border-slate-200 select-none space-y-2.5">
      
      {/* Tezkor tavsiya etilgan savollar chiplari */}
      {quickQuestions.length > 0 && !isBaby && (
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar text-[11px]">
          <span className="text-slate-400 flex items-center gap-0.5 shrink-0 font-medium">
            <Sparkles size={12} className="text-amber-500" /> Savollar:
          </span>
          {quickQuestions.map((q, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleChipClick(q)}
              disabled={disabled}
              className="bg-slate-100 hover:bg-blue-50 hover:text-blue-700 hover:border-blue-300 text-slate-700 px-2.5 py-1 rounded-lg border border-slate-200 text-xs transition-colors shrink-0 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {q}
            </button>
          ))}
        </div>
      )}

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
            type="button"
            onClick={handleMicClick}
            disabled={disabled}
            title={!activeMannequin ? "Avval bemorni tanlang" : isRecording ? "To'xtatish va yuborish uchun bosing" : "Ovoz yozish uchun bosing"}
            className={`
              relative flex items-center justify-center w-14 h-14 rounded-full shadow-md
              transition-all duration-200 touch-none select-none cursor-pointer
              ${disabled
                ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                : isRecording
                ? 'bg-red-500 text-white scale-110 shadow-red-300 shadow-lg animate-pulse'
                : 'bg-blue-600 text-white hover:bg-blue-700 hover:scale-105 active:scale-95 shadow-blue-200'
              }
            `}
          >
            {isProcessing ? (
              <Loader2 size={26} className="animate-spin" />
            ) : isRecording ? (
              <Mic size={26} className="animate-bounce" />
            ) : disabled ? (
              <MicOff size={22} />
            ) : (
              <Mic size={26} />
            )}
          </button>
        </div>

        <div className="text-left flex-1 min-w-0">
          <div className="text-xs font-bold text-slate-800 flex items-center gap-1.5">
            {isRecording ? (
              <span className="text-red-600 flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-red-500 animate-ping inline-block" />
                Gapiring... (To'xtatish uchun mikrofonni bosing)
              </span>
            ) : isProcessing ? (
              <span className="text-blue-600">⚡ DeepSeek AI javob bermoqda...</span>
            ) : (
              <span>Mikrofon orqali gapirish</span>
            )}
          </div>
          
          <div className="text-[11px] text-slate-500 mt-0.5 truncate">
            {liveText ? (
              <span className="text-emerald-700 font-medium bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                "{liveText}"
              </span>
            ) : (
              isBaby ? 'Chaqaloq tovushli javob qaytaradi' : 'Savolingiz o\'zbek tilida aniqlanadi va sof ovozda eshittiriladi'
            )}
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
          className="flex-1 bg-white border border-slate-300 text-slate-800 text-xs rounded-xl px-3.5 py-2 outline-none
                     focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-slate-100 disabled:cursor-not-allowed shadow-inner"
        />
        <button
          type="submit"
          disabled={disabled || !inputText.trim()}
          className="bg-blue-600 hover:bg-blue-700 text-white p-2 rounded-xl transition-all disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer shadow-xs"
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

