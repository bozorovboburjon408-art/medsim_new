import React, { useState, useEffect } from 'react';
import { Wifi, WifiOff } from 'lucide-react';

/**
 * Manikenlar ro'yxati — ESP32 health check orqali online/offline tekshiriladi.
 * Hozircha statik, backend ulanganda dinamik bo'ladi.
 */
const MANNEQUINS = [
  {
    slug: 'bobo',
    name: 'Bobo',
    age: '65-75 yosh',
    emoji: '👴',
    description: 'Tajribali, o\'jar, og\'riqdan shikoyat qiladi',
    color: {
      border: 'border-amber-400',
      bg: 'bg-amber-50',
      activeBg: 'bg-amber-100',
      text: 'text-amber-900',
      glow: 'ring-amber-200',
      badge: 'bg-amber-100 text-amber-700'
    }
  },
  {
    slug: 'homilador',
    name: 'Gulnora opa (Homilador)',
    age: '32 hafta (28 yosh)',
    emoji: '🤰',
    description: 'Piyelonefrit xuruji, anemiya, bel og\'rig\'i, holsizlik',
    color: {
      border: 'border-pink-400',
      bg: 'bg-pink-50',
      activeBg: 'bg-pink-100',
      text: 'text-pink-900',
      glow: 'ring-pink-200',
      badge: 'bg-pink-100 text-pink-700'
    }
  },
  {
    slug: 'bola',
    name: 'Bola',
    age: '5-6 yosh',
    emoji: '👦',
    description: 'Qo\'rqoq, yig\'loqi, sodda gapiradi',
    color: {
      border: 'border-blue-400',
      bg: 'bg-blue-50',
      activeBg: 'bg-blue-100',
      text: 'text-blue-900',
      glow: 'ring-blue-200',
      badge: 'bg-blue-100 text-blue-700'
    }
  },
  {
    slug: 'chaqaloq',
    name: 'Chaqaloq',
    age: '0-1 yosh',
    emoji: '👶',
    description: 'Gapirmaydi, faqat ovoz chiqaradi',
    color: {
      border: 'border-emerald-400',
      bg: 'bg-emerald-50',
      activeBg: 'bg-emerald-100',
      text: 'text-emerald-900',
      glow: 'ring-emerald-200',
      badge: 'bg-emerald-100 text-emerald-700'
    }
  }
];

export default function MannequinSelector({ activeMannequin, onSelect }) {
  const [healthStatus, setHealthStatus] = useState({});

  // ESP32 health check (backend orqali)
  useEffect(() => {
    // Hozircha barchasini "online" deb belgilaymiz
    // Backend ulanganda: GET /api/mannequins dan real holat olinadi
    const status = {};
    MANNEQUINS.forEach(m => { status[m.slug] = true; });
    setHealthStatus(status);
  }, []);

  return (
    <div className="flex flex-col h-full bg-slate-50 border-r border-slate-200">
      {/* Sarlavha */}
      <div className="p-4 pb-3 border-b border-slate-200">
        <h2 className="text-lg font-bold text-slate-800">Bemorlar</h2>
        <p className="text-xs text-slate-500 mt-0.5">Gaplashmoqchi bo'lgan bemorni tanlang</p>
      </div>

      {/* Manikenlar gridi */}
      <div className="flex-1 p-4 overflow-y-auto">
        <div className="grid grid-cols-1 gap-3">
          {MANNEQUINS.map(m => {
            const isActive = activeMannequin?.slug === m.slug;
            const isOnline = healthStatus[m.slug] ?? false;

            return (
              <button
                key={m.slug}
                onClick={() => onSelect(m)}
                className={`
                  relative flex items-center p-4 rounded-xl border-2 transition-all duration-200 text-left
                  ${isActive
                    ? `${m.color.border} ${m.color.activeBg} ring-4 ${m.color.glow} shadow-md`
                    : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm'
                  }
                `}
              >
                {/* Emoji */}
                <div className={`text-4xl mr-4 ${isActive ? '' : 'grayscale-0'}`}>
                  {m.emoji}
                </div>

                {/* Ma'lumotlar */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className={`font-bold text-base ${isActive ? m.color.text : 'text-slate-800'}`}>
                      {m.name}
                    </span>
                    {isActive && (
                      <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${m.color.badge}`}>
                        Faol
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-slate-500 mb-1">{m.age}</div>
                  <div className="text-xs text-slate-400 truncate">{m.description}</div>
                </div>

                {/* Online/Offline */}
                <div className="flex flex-col items-center ml-2">
                  {isOnline ? (
                    <Wifi size={16} className="text-green-500" />
                  ) : (
                    <WifiOff size={16} className="text-red-400" />
                  )}
                  <span className={`text-[9px] mt-1 font-bold uppercase ${isOnline ? 'text-green-600' : 'text-red-400'}`}>
                    {isOnline ? 'Online' : 'Offline'}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Pastki ma'lumot */}
      <div className="p-4 border-t border-slate-200 bg-white">
        <div className="text-[11px] text-slate-400 text-center">
          {activeMannequin
            ? `${activeMannequin.emoji} ${activeMannequin.name} tanlangan`
            : 'Bemor tanlanmagan'
          }
        </div>
      </div>
    </div>
  );
}
