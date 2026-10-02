import React, { useRef, useEffect } from 'react';
import { MessageSquare, Stethoscope, User, Clock, ShieldCheck, Volume2, Sparkles } from 'lucide-react';

/**
 * ConversationPanel — Klinik Muloqot va Transkript Jurnali
 * Hamshira va bemor dialogini real vaqt rejimida tibbiy transkript ko'rinishida chiqaradi.
 */

const THEMES = {
  bobo: {
    bubbleBg: 'bg-amber-50 border-amber-200 text-amber-950',
    tag: 'bg-amber-100 text-amber-800 border-amber-300',
    avatarBg: 'bg-amber-100 border-amber-300 text-amber-900',
  },
  homilador: {
    bubbleBg: 'bg-rose-50 border-rose-200 text-rose-950',
    tag: 'bg-rose-100 text-rose-800 border-rose-300',
    avatarBg: 'bg-rose-100 border-rose-300 text-rose-900',
  },
  bola: {
    bubbleBg: 'bg-blue-50 border-blue-200 text-blue-950',
    tag: 'bg-blue-100 text-blue-800 border-blue-300',
    avatarBg: 'bg-blue-100 border-blue-300 text-blue-900',
  },
  chaqaloq: {
    bubbleBg: 'bg-emerald-50 border-emerald-200 text-emerald-950',
    tag: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    avatarBg: 'bg-emerald-100 border-emerald-300 text-emerald-900',
  }
};

export default function ConversationPanel({ conversation, activeMannequin }) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [conversation]);

  const theme = activeMannequin ? (THEMES[activeMannequin.slug] || THEMES.bobo) : THEMES.bobo;

  if (!activeMannequin) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-slate-900/40 select-none">
        <div className="w-16 h-16 rounded-2xl bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-400 mb-4 shadow-lg">
          <Stethoscope size={32} className="text-blue-400" />
        </div>
        <h3 className="text-base font-bold text-slate-200 font-mono">KLINIK TELEMETRIYA VA AUDIOMULOQOT</h3>
        <p className="text-xs text-slate-400 max-w-sm mt-1">
          Muloqotni boshlash uchun chap paneldan kerakli bemorni tanlang va mikrofon tugmasini bosing.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-slate-900/30">
      {/* Muloqot Sarlavhasi */}
      <div className="px-5 py-2.5 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-slate-800 flex items-center justify-center text-lg border border-slate-700">
            {activeMannequin.emoji}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-white text-xs">{activeMannequin.name}</span>
              <span className="text-[10px] font-mono text-slate-400">({activeMannequin.age})</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 text-[11px] font-mono text-slate-400">
          <div className="flex items-center gap-1">
            <Volume2 size={13} className="text-emerald-400" />
            <span>ESP32 Wi-Fi Audio</span>
          </div>
          <span className="text-slate-600">•</span>
          <span>{conversation.filter(m => m.speaker !== 'system').length} ta replika</span>
        </div>
      </div>

      {/* Xabarlar lentasi */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4" ref={scrollRef}>
        {conversation.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-400 select-none py-12">
            <div className="w-12 h-12 rounded-xl bg-slate-800/80 flex items-center justify-center text-slate-500 mb-3 border border-slate-700">
              <MessageSquare size={22} />
            </div>
            <p className="text-sm font-semibold text-slate-300">Suhbat jurnali bo'sh</p>
            <p className="text-xs text-slate-500 mt-1 max-w-xs text-center">
              Hamshira savol berganda uning ovozi STT orqali matnga o'girilib, bu yerda aks etadi.
            </p>
          </div>
        ) : (
          conversation.map((msg, idx) => {
            if (msg.speaker === 'system') {
              return (
                <div key={idx} className="flex justify-center my-2">
                  <div className="bg-slate-800/90 text-slate-300 border border-slate-700 text-xs px-4 py-1.5 rounded-full font-mono flex items-center gap-2 shadow-sm">
                    <ShieldCheck size={13} className="text-blue-400" />
                    <span>{msg.text}</span>
                  </div>
                </div>
              );
            }

            const isNurse = msg.speaker === 'nurse';

            return (
              <div key={idx} className={`flex items-start gap-2.5 ${isNurse ? 'justify-end' : 'justify-start'}`}>
                {/* Bemor avatari */}
                {!isNurse && (
                  <div className={`w-8 h-8 rounded-xl flex items-center justify-center text-base border shrink-0 shadow-sm ${theme.avatarBg}`}>
                    {activeMannequin.emoji}
                  </div>
                )}

                <div className={`max-w-[78%] rounded-2xl p-4 shadow-md transition-all ${
                  isNurse
                    ? 'bg-blue-600 text-white rounded-tr-sm border border-blue-500'
                    : `${theme.bubbleBg} rounded-tl-sm border shadow-sm`
                }`}>
                  {/* Meta qator */}
                  <div className="flex items-center justify-between gap-4 mb-1.5 pb-1 border-b border-black/5">
                    <div className="flex items-center gap-1.5">
                      <span className={`text-[10px] font-mono font-bold uppercase tracking-wider ${
                        isNurse ? 'text-blue-200' : 'text-slate-600'
                      }`}>
                        {isNurse ? '👩‍⚕️ Hamshira (Patronaj)' : `${activeMannequin.name}`}
                      </span>

                      {!isNurse && msg.emotion && (
                        <span className={`text-[9px] font-bold uppercase px-1.5 py-0.2 rounded border ${theme.tag}`}>
                          {msg.emotion}
                        </span>
                      )}
                    </div>

                    <div className={`text-[10px] font-mono ${isNurse ? 'text-blue-200' : 'text-slate-400'}`}>
                      {new Date(msg.timestamp).toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </div>
                  </div>

                  {/* Asosiy matn */}
                  <p className="text-[13px] leading-relaxed font-normal">
                    {msg.text}
                  </p>
                </div>

                {/* Hamshira avatari */}
                {isNurse && (
                  <div className="w-8 h-8 rounded-xl bg-blue-600 text-white flex items-center justify-center text-sm font-bold shrink-0 border border-blue-400 shadow-md">
                    <User size={16} />
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
