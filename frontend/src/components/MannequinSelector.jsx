import React, { useState, useEffect } from 'react';
import { Wifi, Users } from 'lucide-react';

/**
 * MannequinSelector — Sodda, oq va tushunarli Bemorlar Paneli
 */

const MANNEQUINS = [
  {
    slug: 'bobo',
    name: 'Salomat buvi (Qariya)',
    age: '75 yosh',
    emoji: '👵',
    description: '2-tip qandli diabet, qand 11.8 mmol/l, tovon yarasi, chanqash va uyushish',
    color: {
      border: 'border-amber-400',
      activeBg: 'bg-amber-50',
      text: 'text-amber-900',
      glow: 'ring-amber-200',
      badge: 'bg-amber-100 text-amber-800'
    }
  },
  {
    slug: 'homilador',
    name: 'Gulnora opa (Homilador)',
    age: '32 hafta (28 yosh)',
    emoji: '🤰',
    description: 'Piyelonefrit qo\'zishi, 2-darajali anemiya, bel og\'rig\'i, 37.5°C harorat',
    color: {
      border: 'border-pink-400',
      activeBg: 'bg-pink-50',
      text: 'text-pink-900',
      glow: 'ring-pink-200',
      badge: 'bg-pink-100 text-pink-800'
    }
  },
  {
    slug: 'bola',
    name: 'Jasurbek va onasi (Bola)',
    age: '5 yosh',
    emoji: '👦',
    description: 'Aralash gel\'mintoz (enterobioz), tunda qichishish, kindik og\'rig\'i, anemiya',
    color: {
      border: 'border-blue-400',
      activeBg: 'bg-blue-50',
      text: 'text-blue-900',
      glow: 'ring-blue-200',
      badge: 'bg-blue-100 text-blue-800'
    }
  },
  {
    slug: 'chaqaloq',
    name: 'Chaqaloq',
    age: '0-1 yosh',
    emoji: '👶',
    description: 'Gapirmaydi, yig\'lash va kulish tovushlarini chiqaradi',
    color: {
      border: 'border-emerald-400',
      activeBg: 'bg-emerald-50',
      text: 'text-emerald-900',
      glow: 'ring-emerald-200',
      badge: 'bg-emerald-100 text-emerald-800'
    }
  }
];

export default function MannequinSelector({ activeMannequin, onSelect }) {
  const [healthStatus, setHealthStatus] = useState({});

  useEffect(() => {
    const status = {};
    MANNEQUINS.forEach(m => { status[m.slug] = true; });
    setHealthStatus(status);
  }, []);

  return (
    <div className="flex flex-col h-full bg-slate-50 border-r border-slate-200 select-none">
      {/* Sarlavha */}
      <div className="p-4 border-b border-slate-200 bg-white">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-800 flex items-center gap-2">
            <Users size={18} className="text-blue-600" />
            <span>Bemorlar</span>
          </h2>
          <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
            4 ta maniken
          </span>
        </div>
        <p className="text-xs text-slate-500 mt-1">
          Gaplashmoqchi bo'lgan bemorni tanlang
        </p>
      </div>

      {/* Bemorlar ro'yxati */}
      <div className="flex-1 p-3.5 space-y-3 overflow-y-auto">
        {MANNEQUINS.map(m => {
          const isActive = activeMannequin?.slug === m.slug;

          return (
            <button
              key={m.slug}
              onClick={() => onSelect(m)}
              className={`
                w-full text-left rounded-xl p-4 transition-all duration-200 border-2 cursor-pointer
                ${isActive
                  ? `${m.color.border} ${m.color.activeBg} ring-3 ${m.color.glow} shadow-sm`
                  : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-xs'
                }
              `}
            >
              <div className="flex items-start gap-3.5">
                {/* Emoji Avatar */}
                <div className={`text-3xl p-2 rounded-xl shrink-0 ${
                  isActive ? 'bg-white shadow-xs' : 'bg-slate-50'
                }`}>
                  {m.emoji}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-1 mb-0.5">
                    <span className={`font-bold text-sm ${
                      isActive ? m.color.text : 'text-slate-900'
                    }`}>
                      {m.name}
                    </span>

                    {isActive ? (
                      <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${m.color.badge}`}>
                        Tanlangan
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-[10px] font-bold text-emerald-600 uppercase bg-emerald-50 px-2 py-0.5 rounded-full">
                        <Wifi size={11} /> Online
                      </span>
                    )}
                  </div>

                  <div className="text-xs text-slate-500 font-medium">{m.age}</div>
                  <div className="text-xs text-slate-600 mt-1 leading-snug line-clamp-2">
                    {m.description}
                  </div>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Pastki eslatma */}
      <div className="p-3.5 border-t border-slate-200 bg-white text-center">
        <div className="text-xs text-slate-500">
          {activeMannequin
            ? `Hozir faol: ${activeMannequin.emoji} ${activeMannequin.name}`
            : 'Bemor tanlanmagan'}
        </div>
      </div>
    </div>
  );
}
