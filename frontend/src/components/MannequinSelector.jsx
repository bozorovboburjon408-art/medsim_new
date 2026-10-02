import React, { useState, useEffect } from 'react';
import { Wifi, WifiOff, Users, Radio, Stethoscope, ChevronRight, AlertCircle, Heart } from 'lucide-react';

/**
 * MannequinSelector — Bemorlar (Manikenlar) Triaj va Tanlov Paneli
 * Har bir manikenning klinik triaj holati, apparat IP manzili va fiziologik xarakteristikasini ko'rsatadi.
 */

const MANNEQUINS = [
  {
    slug: 'bobo',
    name: 'Qariya Bobo',
    age: '70 yosh (Geriatriya)',
    emoji: '👴',
    code: 'MK-701-GER',
    triage: 'Sariq (Nazorat)',
    triageColor: 'bg-amber-100 text-amber-800 border-amber-300',
    description: 'Surunkali arterial gipertenziya III, stenokardiya',
    ip: '192.168.1.10',
    audioMode: 'TTS • Oqsoqol ovozi (0.7 pitch)',
    accent: {
      border: 'border-amber-400',
      activeBg: 'bg-gradient-to-r from-amber-50/90 to-white',
      ring: 'ring-amber-200',
      badge: 'bg-amber-500 text-white',
      bar: 'bg-amber-500'
    }
  },
  {
    slug: 'homilador',
    name: 'Gulnora opa (Homilador)',
    age: '32 hafta • 28 yosh (Akusherlik)',
    emoji: '🤰',
    code: 'MK-320-OBG',
    triage: 'Qizil (Shoshilinch)',
    triageColor: 'bg-rose-100 text-rose-800 border-rose-300 animate-pulse',
    description: 'Surunkali piyelonefrit xuruji, anemiya (Hb 80 g/l)',
    ip: '192.168.1.11',
    audioMode: 'TTS • Ayol ovozi (1.1 pitch)',
    accent: {
      border: 'border-rose-400',
      activeBg: 'bg-gradient-to-r from-rose-50/90 to-white',
      ring: 'ring-rose-200',
      badge: 'bg-rose-500 text-white',
      bar: 'bg-rose-500'
    }
  },
  {
    slug: 'bola',
    name: '5 yoshli Bola',
    age: '5 yosh (Pediatriya)',
    emoji: '👦',
    code: 'MK-051-PED',
    triage: 'Sariq (Gipertermiya)',
    triageColor: 'bg-blue-100 text-blue-800 border-blue-300',
    description: 'Tana harorati 39.5°C, inyeksiya fobiyasi',
    ip: '192.168.1.12',
    audioMode: 'TTS • Bola ovozi (1.4 pitch)',
    accent: {
      border: 'border-blue-400',
      activeBg: 'bg-gradient-to-r from-blue-50/90 to-white',
      ring: 'ring-blue-200',
      badge: 'bg-blue-500 text-white',
      bar: 'bg-blue-500'
    }
  },
  {
    slug: 'chaqaloq',
    name: 'Chaqaloq',
    age: '0-1 yosh (Neonatologiya)',
    emoji: '👶',
    code: 'MK-001-NEO',
    triage: 'Moviy (Asfiksiya)',
    triageColor: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    description: 'Asfiksiya belgilari, gipoksiya, tovushli reaksiyalar',
    ip: '192.168.1.13',
    audioMode: 'Direct MP3 DMA (TTS yo\'q)',
    accent: {
      border: 'border-emerald-400',
      activeBg: 'bg-gradient-to-r from-emerald-50/90 to-white',
      ring: 'ring-emerald-200',
      badge: 'bg-emerald-500 text-white',
      bar: 'bg-emerald-500'
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
    <div className="flex flex-col h-full bg-slate-900 border-r border-slate-800 select-none">
      {/* Sarlavha */}
      <div className="p-4 border-b border-slate-800 bg-slate-950/60">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users size={16} className="text-blue-400" />
            <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
              Bemorlar Ro'yxati
            </h2>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
            4 Maniken
          </span>
        </div>
        <p className="text-[11px] text-slate-400 mt-1">
          Muloqot va tekshiruv uchun bemor profilini tanlang
        </p>
      </div>

      {/* Manikenlar kartochkalari */}
      <div className="flex-1 p-3.5 space-y-3 overflow-y-auto">
        {MANNEQUINS.map(m => {
          const isActive = activeMannequin?.slug === m.slug;
          const isOnline = healthStatus[m.slug] ?? true;

          return (
            <button
              key={m.slug}
              onClick={() => onSelect(m)}
              className={`
                w-full text-left rounded-xl p-3.5 transition-all duration-200 border relative overflow-hidden group
                ${isActive
                  ? `${m.accent.border} ${m.accent.activeBg} ring-2 ${m.accent.ring} shadow-lg shadow-black/20 text-slate-900`
                  : 'border-slate-800 bg-slate-800/60 hover:bg-slate-800 hover:border-slate-700 text-slate-200'
                }
              `}
            >
              {/* Faol vertikal indikator chiziq */}
              {isActive && (
                <div className={`absolute top-0 left-0 bottom-0 w-1.5 ${m.accent.bar}`} />
              )}

              {/* Yuqori qator: Kod va Triaj */}
              <div className="flex items-center justify-between mb-1.5">
                <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${
                  isActive ? 'bg-slate-900/10 text-slate-700' : 'bg-slate-900 text-slate-400 border border-slate-800'
                }`}>
                  {m.code}
                </span>

                <span className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded-full border ${m.triageColor}`}>
                  {m.triage}
                </span>
              </div>

              {/* Markaz: Ism va Avatar */}
              <div className="flex items-start gap-3 my-1">
                <div className={`text-3xl p-1.5 rounded-xl shrink-0 ${
                  isActive ? 'bg-white shadow-sm' : 'bg-slate-900/80 border border-slate-700/50'
                }`}>
                  {m.emoji}
                </div>

                <div className="min-w-0 flex-1">
                  <div className={`font-bold text-sm leading-tight flex items-center gap-1.5 ${
                    isActive ? 'text-slate-900' : 'text-white'
                  }`}>
                    <span className="truncate">{m.name}</span>
                    {isActive && (
                      <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shrink-0"></span>
                    )}
                  </div>
                  <div className={`text-[11px] mt-0.5 font-medium ${
                    isActive ? 'text-slate-600' : 'text-slate-400'
                  }`}>
                    {m.age}
                  </div>
                  <div className={`text-[11px] leading-snug mt-1 line-clamp-2 ${
                    isActive ? 'text-slate-700 font-medium' : 'text-slate-400'
                  }`}>
                    {m.description}
                  </div>
                </div>
              </div>

              {/* Pastki qator: Hardware Telemetriya & Audio rejimi */}
              <div className={`mt-2.5 pt-2 border-t flex items-center justify-between text-[10px] font-mono ${
                isActive ? 'border-slate-300/80 text-slate-600' : 'border-slate-700/60 text-slate-400'
              }`}>
                <div className="flex items-center gap-1">
                  <Radio size={12} className={isActive ? 'text-blue-600' : 'text-slate-500'} />
                  <span>{m.ip}</span>
                </div>

                <div className="flex items-center gap-1">
                  <span className={`w-1.5 h-1.5 rounded-full ${isOnline ? 'bg-emerald-500' : 'bg-rose-500'}`}></span>
                  <span className="truncate max-w-[120px]">{m.audioMode}</span>
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Pastki holat */}
      <div className="p-3.5 border-t border-slate-800 bg-slate-950 text-center">
        <div className="flex items-center justify-center gap-2 text-[11px] font-mono text-slate-400">
          <Stethoscope size={13} className="text-blue-400" />
          <span>Wi-Fi Audio Mesh: <strong className="text-emerald-400 font-bold">FAOL</strong></span>
        </div>
      </div>
    </div>
  );
}
