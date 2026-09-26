import React, { useState, useEffect, useMemo } from 'react';
import { Play, Square, Clock, ChevronRight, BookOpen, AlertCircle } from 'lucide-react';

/**
 * Ssenariy boshqaruv paneli.
 * Har bir manikenning o'ziga xos ssenariylari bor.
 * Sessiyani boshlash/to'xtatish va taymer shu yerda.
 */

const MOCK_SCENARIOS = {
  bobo: [
    {
      id: 1,
      title: "Qon bosimi ko'tarilishi",
      desc: "Bemor qon bosimi 180/100 ga ko'tarilib, bosh aylanishi va yurak sanchishi bilan murojaat qilgan.",
      duration: 15,
      actions: ["Bemor bilan salomlashish", "Qon bosimini o'lchash", "Tinchlantiruvchi suhbat", "Dori berish"]
    },
    {
      id: 2,
      title: "Nafas qisishi",
      desc: "Surunkali yurak yetishmovchiligi fonida nafas qisishi. Bemor o'tirgan holatda nafas olishga majbur.",
      duration: 10,
      actions: ["Ahvolini so'rash", "Nafas chastotasini o'lchash", "Shifokor chaqirish"]
    }
  ],
  homilador: [
    {
      id: 3,
      title: "Erta tug'ruq xavfi",
      desc: "Homiladorlikning 32-haftasi, qornning pastki qismida kuchli sanchish og'riqlari.",
      duration: 20,
      actions: ["Anamnez yig'ish", "Puls o'lchash", "Qorin tekshiruvi", "Shifokor chaqirish"]
    },
    {
      id: 6,
      title: "Toxikoz",
      desc: "Ertalabki ko'ngil aynish va qusish. Bemor suvdan ham ko'ngli aynayapti.",
      duration: 12,
      actions: ["Simptomlarni aniqlash", "Suyuqlik berish", "Tinchlantirish"]
    }
  ],
  bola: [
    {
      id: 4,
      title: "Tana haroratining ko'tarilishi",
      desc: "Tana harorati 39.5°C ga ko'tarilgan, bola injiqlik qilyapti va ovqat yemayapti.",
      duration: 15,
      actions: ["Haroratni o'lchash", "Bolani tinchlantirish", "Dori ichirish", "Oilaga tushuntirish"]
    }
  ],
  chaqaloq: [
    {
      id: 5,
      title: "Nafas olishning qiyinlashishi",
      desc: "Yangi tug'ilgan chaqaloqda asfiksiya belgilari. Teri rangida ko'karish kuzatilmoqda.",
      duration: 10,
      actions: ["Nafas yo'llarini tekshirish", "Oksigen berish", "Neonatolog chaqirish"]
    }
  ]
};

export default function ScenarioPanel({ activeMannequin, sessionId, onStartSession, onEndSession }) {
  const [selectedScenarioId, setSelectedScenarioId] = useState('');
  const [timer, setTimer] = useState(0);

  // Manikenning ssenariylari
  const scenarios = useMemo(() => {
    return activeMannequin ? (MOCK_SCENARIOS[activeMannequin.slug] || []) : [];
  }, [activeMannequin?.slug]);

  // Manikenni almashtirganda birinchi ssenariyni tanlash
  useEffect(() => {
    if (scenarios.length > 0) {
      setSelectedScenarioId(scenarios[0].id.toString());
    } else {
      setSelectedScenarioId('');
    }
  }, [activeMannequin?.slug]); // eslint-disable-line

  // Sessiya taymeri
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

  // Manikenni tanlash kerak
  if (!activeMannequin) {
    return (
      <div className="w-1/4 bg-white border-l border-slate-200 flex flex-col h-full">
        <div className="p-5 border-b border-slate-100">
          <h2 className="text-lg font-bold text-slate-800">Ssenariy va Nazorat</h2>
        </div>
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center text-slate-400">
            <BookOpen size={40} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm">Ssenariylarni ko'rish uchun</p>
            <p className="text-sm">bemorni tanlang</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-1/4 bg-white border-l border-slate-200 flex flex-col h-full">
      {/* Ssenariy tanlash */}
      <div className="p-5 border-b border-slate-100">
        <h2 className="text-lg font-bold text-slate-800 mb-3">Ssenariy tanlash</h2>
        <select
          value={selectedScenarioId}
          onChange={(e) => setSelectedScenarioId(e.target.value)}
          disabled={!!sessionId}
          className="w-full bg-slate-50 border border-slate-300 text-slate-800 text-sm rounded-lg
                     focus:ring-2 focus:ring-blue-500 focus:border-blue-500 block p-3
                     disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {scenarios.map(s => (
            <option key={s.id} value={s.id}>{s.title}</option>
          ))}
          {scenarios.length === 0 && <option value="">Ssenariy yo'q</option>}
        </select>

        {/* Ssenariy tavsifi */}
        {activeScenario && (
          <div className="mt-3 bg-blue-50 p-4 rounded-xl border border-blue-100">
            <h3 className="font-semibold text-blue-900 text-sm mb-1.5">{activeScenario.title}</h3>
            <p className="text-xs text-blue-800/80 leading-relaxed mb-2">{activeScenario.desc}</p>
            <div className="flex items-center text-[11px] font-bold text-blue-600 uppercase tracking-wide">
              <Clock size={12} className="mr-1" />
              Taxminiy vaqt: {activeScenario.duration} daqiqa
            </div>
          </div>
        )}
      </div>

      {/* Kutilayotgan amallar */}
      <div className="flex-1 p-5 overflow-y-auto">
        <h3 className="font-bold text-slate-700 text-sm mb-3 flex items-center gap-2">
          <AlertCircle size={14} className="text-blue-500" />
          Kutilayotgan amallar
        </h3>
        <ul className="space-y-2.5">
          {(activeScenario?.actions || [
            "Bemor bilan muloqot o'rnatish",
            "Simptomlarni so'rash",
            "Birlamchi ko'rik o'tkazish",
            "Yordam ko'rsatish"
          ]).map((action, i) => (
            <li key={i} className="flex items-start text-sm text-slate-600">
              <div className="w-5 h-5 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-[10px] font-bold mr-2 mt-0.5 shrink-0">
                {i + 1}
              </div>
              <span className="leading-snug">{action}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Sessiya boshqaruvi */}
      <div className="p-5 border-t border-slate-100 bg-gradient-to-b from-white to-slate-50">
        {/* Taymer */}
        <div className="flex justify-between items-center mb-4">
          <span className="text-slate-600 font-medium text-sm">Seans vaqti:</span>
          <div className={`text-2xl font-mono font-bold ${sessionId ? 'text-green-600' : 'text-slate-300'}`}>
            {formatTime(timer)}
          </div>
        </div>

        {/* Boshlash / Yakunlash tugmasi */}
        {!sessionId ? (
          <button
            onClick={handleStart}
            disabled={!selectedScenarioId}
            className="w-full bg-green-600 hover:bg-green-700 text-white font-bold py-3.5 px-6
                       rounded-xl flex items-center justify-center transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed
                       active:scale-[0.98] shadow-sm"
          >
            <Play size={18} className="mr-2" />
            Seansni boshlash
          </button>
        ) : (
          <button
            onClick={onEndSession}
            className="w-full bg-red-600 hover:bg-red-700 text-white font-bold py-3.5 px-6
                       rounded-xl flex items-center justify-center transition-colors
                       active:scale-[0.98] shadow-sm"
          >
            <Square size={18} className="mr-2" />
            Seansni yakunlash
          </button>
        )}
      </div>
    </div>
  );
}
