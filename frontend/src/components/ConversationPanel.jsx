import React, { useRef, useEffect } from 'react';
import { MessageSquare, User, Clock } from 'lucide-react';

/**
 * ConversationPanel — Sodda, oq va toza muloqot chat paneli
 */

const THEMES = {
  bobo: {
    bubbleBg: 'bg-amber-50 border-amber-200 text-slate-800',
    avatarBg: 'bg-amber-100 border-amber-200 text-amber-900',
    tag: 'bg-amber-100 text-amber-800'
  },
  homilador: {
    bubbleBg: 'bg-pink-50 border-pink-200 text-slate-800',
    avatarBg: 'bg-pink-100 border-pink-200 text-pink-900',
    tag: 'bg-pink-100 text-pink-800'
  },
  bola: {
    bubbleBg: 'bg-blue-50 border-blue-200 text-slate-800',
    avatarBg: 'bg-blue-100 border-blue-200 text-blue-900',
    tag: 'bg-blue-100 text-blue-800'
  },
  chaqaloq: {
    bubbleBg: 'bg-emerald-50 border-emerald-200 text-slate-800',
    avatarBg: 'bg-emerald-100 border-emerald-200 text-emerald-900',
    tag: 'bg-emerald-100 text-emerald-800'
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
      <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-white select-none">
        <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 mb-4 shadow-xs">
          <MessageSquare size={30} className="text-slate-400" />
        </div>
        <h3 className="text-base font-bold text-slate-800">Muloqot boshlanmadi</h3>
        <p className="text-xs text-slate-500 max-w-sm mt-1">
          Bemor bilan gaplashish uchun chap paneldan biror bemorni tanlang.
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-white">
      {/* Sarlavha */}
      <div className="px-5 py-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between select-none">
        <div className="flex items-center gap-2.5">
          <span className="text-2xl">{activeMannequin.emoji}</span>
          <div>
            <span className="font-bold text-slate-900 text-sm">{activeMannequin.name}</span>
            <span className="text-xs text-slate-500 ml-2 font-medium">({activeMannequin.age})</span>
          </div>
        </div>

        <div className="text-xs text-slate-400 font-medium">
          {conversation.filter(m => m.speaker !== 'system').length} ta xabar
        </div>
      </div>

      {/* Muloqot oynasi */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4" ref={scrollRef}>
        {conversation.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-slate-400 select-none py-16">
            <div className="w-14 h-14 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 mb-3">
              <MessageSquare size={26} />
            </div>
            <p className="text-sm font-semibold text-slate-600">Muloqot hali boshlanmadi</p>
            <p className="text-xs text-slate-400 mt-1 text-center">
              Mikrofon tugmasini bosib ushlab turing va bemorga savol bering.
            </p>
          </div>
        ) : (
          conversation.map((msg, idx) => {
            if (msg.speaker === 'system') {
              return (
                <div key={idx} className="flex justify-center my-2">
                  <div className="bg-slate-100 text-slate-600 border border-slate-200 text-xs px-4 py-1.5 rounded-full font-medium shadow-xs">
                    {msg.text}
                  </div>
                </div>
              );
            }

            const isNurse = msg.speaker === 'nurse';

            return (
              <div key={idx} className={`flex items-start gap-3 ${isNurse ? 'justify-end' : 'justify-start'}`}>
                {/* Bemor avatari */}
                {!isNurse && (
                  <div className={`w-9 h-9 rounded-full flex items-center justify-center text-lg border shrink-0 shadow-xs ${theme.avatarBg}`}>
                    {activeMannequin.emoji}
                  </div>
                )}

                <div className={`max-w-[80%] rounded-2xl p-4 shadow-xs ${
                  isNurse
                    ? 'bg-blue-600 text-white rounded-tr-xs'
                    : `${theme.bubbleBg} rounded-tl-xs border`
                }`}>
                  {/* Speaker nomi va vaqt */}
                  <div className="flex items-center justify-between gap-4 mb-1 text-[11px]">
                    <span className={`font-bold ${isNurse ? 'text-blue-100' : 'text-slate-700'}`}>
                      {isNurse ? 'Hamshira' : activeMannequin.name}
                    </span>

                    <span className={isNurse ? 'text-blue-200' : 'text-slate-400'}>
                      {new Date(msg.timestamp).toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>

                  {/* Xabar matni */}
                  <p className="text-sm leading-relaxed">
                    {msg.text}
                  </p>
                </div>

                {/* Hamshira avatari */}
                {isNurse && (
                  <div className="w-9 h-9 rounded-full bg-blue-600 text-white flex items-center justify-center shrink-0 shadow-xs">
                    <User size={18} />
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
