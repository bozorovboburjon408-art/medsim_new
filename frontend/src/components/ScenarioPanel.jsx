import React, { useState, useEffect, useMemo } from 'react';
import { Play, Square, Clock, BookOpen, AlertCircle } from 'lucide-react';

/**
 * ScenarioPanel — Sodda, oq va tushunarli Ssenariy va Nazorat Paneli
 */

const MOCK_SCENARIOS = {
  bobo: [
    {
      id: 1,
      title: "Qon bosimi ko'tarilishi",
      desc: "Bemor qon bosimi 180/100 ga ko'tarilib, bosh aylanishi va yurak sanchishi bilan murojaat qilgan.",
      duration: 15,
      actions: [
        "Bemor bilan salomlashish va ahvolini so'rash",
        "Qon bosimini o'lchash",
        "Tinchlantiruvchi suhbat o'tkazish",
        "Dori berish va shifokor chaqirish"
      ]
    }
  ],
  homilador: [
    {
      id: 3,
      title: "Homilador ayol patronaji (Piyelonefrit va Anemiya)",
      desc: "32 haftalik homiladorlik. Surunkali piyelonefrit qo'zishi va 2-darajali anemiya. Shikoyatlar: bel og'rig'i, harorat 37.5°C, to'q siydik, holsizlik.",
      duration: 20,
      actions: [
        "1-BOSQICH: Salomlashish, shikoyatlar va anamnezni surishtirish (bel og'rig'i, to'q siydik, 37.5°C)",
        "2-BOSQICH: Shoshilinch shifokorga xabar berish va statsionarga (patologiya bo'limiga) yo'llanma berish",
        "3-BOSQICH: 'Xavfli belgilar' (harorat 38°C+, qon ketishi, homila harakatsizligi) bo'yicha yo'riqnoma berish",
        "4-BOSQICH: Parhez (tuzsiz, temirga boy), na'matak damlamasi va tizza-tirsak pozitsion terapiyasi",
        "5-BOSQICH: Doppler-UTT va KTG skriningining hayotiy zarurligini tushuntirish"
      ]
    }
  ],
  bola: [
    {
      id: 4,
      title: "Tana haroratining ko'tarilishi",
      desc: "Tana harorati 39.5°C ga ko'tarilgan, bola injiqlik qilyapti va ukoldan qo'rqadi.",
      duration: 15,
      actions: [
        "Bola bilan muloqot o'rnatish va tinchlantirish",
        "Tana haroratini o'lchash",
        "Dori ichirish va onasiga tushuntirish"
      ]
    }
  ],
  chaqaloq: [
    {
      id: 5,
      title: "Nafas olishning qiyinlashishi",
      desc: "Yangi tug'ilgan chaqaloqda asfiksiya belgilari. Teri rangida ko'karish kuzatilmoqda.",
      duration: 10,
      actions: [
        "Nafas yo'llarini tekshirish",
        "Oksigen berish va taktil stimulatsiya",
        "Neonatolog shifokorni chaqirish"
      ]
    }
  ]
};

export default function ScenarioPanel({ activeMannequin, sessionId, onStartSession, onEndSession }) {
  const [selectedScenarioId, setSelectedScenarioId] = useState('');
  const [timer, setTimer] = useState(0);

  const scenarios = useMemo(() => {
    return activeMannequin ? (MOCK_SCENARIOS[activeMannequin.slug] || []) : [];
  }, [activeMannequin?.slug]);

  useEffect(() => {
    if (scenarios.length > 0) {
      setSelectedScenarioId(scenarios[0].id.toString());
    } else {
      setSelectedScenarioId('');
    }
  }, [activeMannequin?.slug]);

  useEffect(() => {
    let interval;
    if (sessionId) {
      interval = setInterval(() => setTimer(prev => prev + 1), 1000);
    } else {
      setTimer(0);
    }
    return () => clearInterval(interval);
  }, [sessionId]);

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  const activeScenario = scenarios.find(s => s.id.toString() === selectedScenarioId);

  const handleStart = () => {
    if (!activeScenario) return;
    onStartSession({
      mannequinSlug: activeMannequin.slug,
      scenarioId: activeScenario.id,
      scenarioTitle: activeScenario.title
    });
  };

  if (!activeMannequin) {
    return (
      <div className="w-1/4 bg-white border-l border-slate-200 flex flex-col h-full select-none">
        <div className="p-4 border-b border-slate-100">
          <h2 className="text-base font-bold text-slate-800">Ssenariy va Nazorat</h2>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-slate-400">
          <BookOpen size={36} className="mb-2 opacity-40 text-slate-400" />
          <p className="text-xs">Ssenariylarni ko'rish uchun bemorni tanlang</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-1/4 bg-white border-l border-slate-200 flex flex-col h-full select-none">
      
      {/* Ssenariy tanlash */}
      <div className="p-4 border-b border-slate-100 space-y-3">
        <h2 className="text-sm font-bold text-slate-800">Ssenariy tanlash</h2>
        
        <select
          value={selectedScenarioId}
          onChange={(e) => setSelectedScenarioId(e.target.value)}
          disabled={!!sessionId}
          className="w-full bg-slate-50 border border-slate-300 text-slate-800 text-xs rounded-lg p-2.5 font-medium
                     focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none
                     disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {scenarios.map(s => (
            <option key={s.id} value={s.id}>{s.title}</option>
          ))}
          {scenarios.length === 0 && <option value="">Ssenariy yo'q</option>}
        </select>

        {activeScenario && (
          <div className="bg-blue-50 p-3.5 rounded-xl border border-blue-100 space-y-1.5">
            <h3 className="font-bold text-blue-900 text-xs">{activeScenario.title}</h3>
            <p className="text-xs text-blue-800/80 leading-relaxed">{activeScenario.desc}</p>
            <div className="flex items-center text-[11px] font-bold text-blue-600 uppercase tracking-wide pt-1">
              <Clock size={12} className="mr-1" />
              Taxminiy vaqt: {activeScenario.duration} daqiqa
            </div>
          </div>
        )}
      </div>

      {/* Kutilayotgan amallar */}
      <div className="flex-1 p-4 overflow-y-auto space-y-2.5">
        <h3 className="font-bold text-slate-700 text-xs flex items-center gap-1.5">
          <AlertCircle size={14} className="text-blue-500" />
          <span>Kutilayotgan amallar</span>
        </h3>

        <ul className="space-y-2">
          {(activeScenario?.actions || []).map((action, i) => (
            <li key={i} className="flex items-start text-xs text-slate-600">
              <div className="w-5 h-5 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-[10px] font-bold mr-2 mt-0.5 shrink-0">
                {i + 1}
              </div>
              <span className="leading-snug">{action}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Sessiya boshqaruvi va Taymer */}
      <div className="p-4 border-t border-slate-100 bg-slate-50 space-y-3">
        <div className="flex justify-between items-center px-1">
          <span className="text-slate-600 font-medium text-xs">Seans vaqti:</span>
          <div className={`text-2xl font-mono font-bold ${sessionId ? 'text-green-600 animate-pulse' : 'text-slate-300'}`}>
            {formatTime(timer)}
          </div>
        </div>

        {!sessionId ? (
          <button
            onClick={handleStart}
            disabled={!selectedScenarioId}
            className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-4
                       rounded-xl flex items-center justify-center gap-2 text-xs transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed active:scale-98 shadow-xs cursor-pointer"
          >
            <Play size={16} className="fill-white" />
            <span>Seansni boshlash</span>
          </button>
        ) : (
          <button
            onClick={onEndSession}
            className="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-3 px-4
                       rounded-xl flex items-center justify-center gap-2 text-xs transition-colors
                       active:scale-98 shadow-xs cursor-pointer"
          >
            <Square size={16} className="fill-white" />
            <span>Seansni yakunlash</span>
          </button>
        )}
      </div>
    </div>
  );
}
