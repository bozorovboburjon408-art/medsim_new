import React, { useRef, useEffect } from 'react';
import { MessageCircle } from 'lucide-react';

/**
 * Suhbat paneli — Hamshira va manikenning muloqot tarixini ko'rsatadi.
 * Chat ko'rinishi: hamshira o'ngda (ko'k), manikenning javoblari chapda (qahramon rangida).
 */

// Qahramon ranglari
const MANNEQUIN_COLORS = {
  bobo: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-900', emotion: 'text-amber-600' },
  homilador: { bg: 'bg-pink-50', border: 'border-pink-200', text: 'text-pink-900', emotion: 'text-pink-600' },
  bola: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-900', emotion: 'text-blue-600' },
  chaqaloq: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-900', emotion: 'text-emerald-600' },
};

export default function ConversationPanel({ conversation, activeMannequin }) {
  const scrollRef = useRef(null);

  // Yangi xabar kelganda pastga scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [conversation]);

  // Manikenning rangi
  const mColors = activeMannequin ? (MANNEQUIN_COLORS[activeMannequin.slug] || MANNEQUIN_COLORS.bobo) : MANNEQUIN_COLORS.bobo;

  // Manikenni tanlash kerak
  if (!activeMannequin) {
    return (
      <div className="flex-1 flex items-center justify-center bg-white p-8 text-center">
        <div>
          <div className="text-7xl mb-6 opacity-30">🩺</div>
          <p className="text-xl font-semibold text-slate-400 mb-2">Muloqotni boshlash uchun</p>
          <p className="text-lg text-slate-400">chapdan bemorni tanlang</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Suhbat sarlavhasi */}
      <div className={`px-6 py-3 ${mColors.bg} border-b ${mColors.border} flex items-center gap-3`}>
        <span className="text-2xl">{activeMannequin.emoji}</span>
        <div>
          <span className={`font-bold ${mColors.text}`}>{activeMannequin.name}</span>
          <span className="text-xs text-slate-500 ml-2">({activeMannequin.age})</span>
        </div>
        <div className="ml-auto flex items-center gap-1 text-xs text-slate-400">
          <MessageCircle size={14} />
          <span>{conversation.filter(m => m.speaker !== 'system').length} xabar</span>
        </div>
      </div>

      {/* Xabarlar ro'yxati */}
      <div className="flex-1 overflow-y-auto p-6" ref={scrollRef}>
        {conversation.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-400">
            <MessageCircle size={48} className="mb-4 opacity-30" />
            <p className="text-lg">Muloqot hali boshlanmadi</p>
            <p className="text-sm mt-1">Mikrofon tugmasini bosib bemorga savol bering</p>
          </div>
        ) : (
          <div className="space-y-4">
            {conversation.map((msg, idx) => {
              // Tizim xabari
              if (msg.speaker === 'system') {
                return (
                  <div key={idx} className="flex justify-center">
                    <div className="bg-slate-100 text-slate-500 text-sm px-4 py-2 rounded-full max-w-[80%] text-center">
                      {msg.text}
                    </div>
                  </div>
                );
              }

              const isNurse = msg.speaker === 'nurse';

              return (
                <div key={idx} className={`flex ${isNurse ? 'justify-end' : 'justify-start'}`}>
                  {/* Manikenning emoji avatari */}
                  {!isNurse && (
                    <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-lg mr-2 mt-1 shrink-0">
                      {activeMannequin.emoji}
                    </div>
                  )}

                  <div className={`max-w-[70%] rounded-2xl p-4 shadow-sm ${
                    isNurse
                      ? 'bg-blue-600 text-white rounded-br-sm'
                      : `${mColors.bg} border ${mColors.border} ${mColors.text} rounded-bl-sm`
                  }`}>
                    {/* Emotion badge */}
                    {!isNurse && msg.emotion && (
                      <div className={`text-[10px] font-bold uppercase mb-1.5 tracking-wider ${mColors.emotion}`}>
                        {msg.emotion}
                      </div>
                    )}

                    <p className="text-[15px] leading-relaxed">{msg.text}</p>

                    <div className={`text-[10px] mt-2 text-right ${isNurse ? 'text-blue-200' : 'text-slate-400'}`}>
                      {new Date(msg.timestamp).toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>

                  {/* Hamshira avatari */}
                  {isNurse && (
                    <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-lg ml-2 mt-1 shrink-0">
                      👩‍⚕️
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
