import React, { useState, useEffect, useMemo } from 'react';
import { Play, Square, Clock, CheckCircle2, Circle, AlertTriangle, FileText, Award, ChevronRight, Stethoscope } from 'lucide-react';

/**
 * ScenarioPanel — Klinik Ssenariy, Protokol va Ko'nikmalarni Baholash Paneli
 */

const CLINICAL_SCENARIOS = {
  bobo: [
    {
      id: 1,
      code: 'SCN-GER-01',
      title: "Arterial Gipertenziya va Stenokardiya",
      desc: "Bemor qon bosimi 180/100 mm sim.ust. ga ko'tarilgan. Bosh aylanishi, yurak sohasidagi sanchiq va holsizlik.",
      duration: 15,
      diagnosis: "Gipertonik kriz, IYX Stenokardiya xuruji",
      actions: [
        "Salomlashish va shikoyatlarni to'liq aniqlash",
        "Qon bosimi (NIBP) va pulsni o'lchash",
        "Tinchlantiruvchi muomala va holatni baholash",
        "Gipotenziv dori vositalari bo'yicha ko'rsatma berish",
        "Shifokorga xabar berish va EKG tavsiya qilish"
      ]
    }
  ],
  homilador: [
    {
      id: 3,
      code: 'SCN-OBG-32',
      title: "32-Hafta Patronaji: Piyelonefrit va Anemiya",
      desc: "32 haftalik 3-homiladorlik. Surunkali piyelonefrit qo'zishi va o'rta og'ir darajali temir tanqisligi anemiyasi (Hb 80 g/l).",
      duration: 20,
      diagnosis: "Homiladorlik III (32 h), Surunkali piyelonefrit qo'zishi, Anemiya II daraja",
      actions: [
        "1-BOSQICH: Salomlashish, shikoyat va anamnezni surishtirish (bel og'rig'i, to'q siydik, 37.5°C)",
        "2-BOSQICH: Shoshilinch shifokorga xabar berish va statsionarga (patologiya) yo'llanma berish",
        "3-BOSQICH: 'Xavfli belgilar' (harorat 38°C+, qon ketishi, homila harakati) bo'yicha yo'riqnoma",
        "4-BOSQICH: Parhez (tuzsiz, temirga boy), na'matak damlamasi va tizza-tirsak pozitsion terapiyasi",
        "5-BOSQICH: Doppler-UTT va KTG skriningining hayotiy zarurligini tushuntirish"
      ]
    }
  ],
  bola: [
    {
      id: 4,
      code: 'SCN-PED-05',
      title: "Febril Gipertermiya va Inyeksiya Fobiyasi",
      desc: "5 yoshli bola, tana harorati 39.5°C. Injiqlik, shifokor va ukoldan qattiq qo'rquv.",
      duration: 15,
      diagnosis: "O'tkir respirator infeksiya, Febril sindrom",
      actions: [
        "Bola bilan ishonchli psixologik kontakt o'rnatish",
        "Haroratni tushirish bo'yicha fizikal sovutish choralarini ko'rish",
        "Og'riqsiz paratsetamol siropini taklif qilish",
        "Ona uchun febril tutqanoq profilaktikasini tushuntirish"
      ]
    }
  ],
  chaqaloq: [
    {
      id: 5,
      code: 'SCN-NEO-01',
      title: "Yangi Tug'ilgan Chaqaloqda Asfiksiya",
      desc: "Asfiksiya belgilari, gipoksiya, nafas olishning susayishi va qaltirash tovushlari.",
      duration: 10,
      diagnosis: "Chaqaloqlar asfiksiyasi, gipoksiya",
      actions: [
        "Yuqori nafas yo'llari o'tkazuvchanligini tekshirish",
        "Oksigenoterapiya va taktil stimulatsiya ko'rsatish",
        "Neonatolog reanimatologni zudlik bilan chaqirish"
      ]
    }
  ]
};

export default function ScenarioPanel({ activeMannequin, sessionId, onStartSession, onEndSession, completedActions = [] }) {
  const [selectedScenarioId, setSelectedScenarioId] = useState('');
  const [timer, setTimer] = useState(0);

  const scenarios = useMemo(() => {
    return activeMannequin ? (CLINICAL_SCENARIOS[activeMannequin.slug] || []) : [];
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
      <div className="w-1/4 bg-slate-900 border-l border-slate-800 flex flex-col h-full select-none">
        <div className="p-4 border-b border-slate-800 bg-slate-950/60">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
            Klinik Protokol
          </h2>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center p-6 text-center text-slate-500">
          <FileText size={36} className="mb-2 text-slate-600" />
          <p className="text-xs">Ssenariy va protokolni ko'rish uchun bemorni tanlang.</p>
        </div>
      </div>
    );
  }

  const totalActions = activeScenario?.actions?.length || 1;
  const progressPercent = sessionId ? Math.min(100, Math.round((completedActions.length / totalActions) * 100)) : 0;

  return (
    <div className="w-1/4 bg-slate-900 border-l border-slate-800 flex flex-col h-full select-none text-slate-200">
      
      {/* Ssenariy Tanlash va Tashxis */}
      <div className="p-4 border-b border-slate-800 bg-slate-950/60 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs font-bold text-white font-mono uppercase">
            <FileText size={14} className="text-blue-400" />
            <span>Klinik Ssenariy</span>
          </div>
          {activeScenario && (
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-950 border border-blue-800 text-blue-300">
              {activeScenario.code}
            </span>
          )}
        </div>

        <select
          value={selectedScenarioId}
          onChange={(e) => setSelectedScenarioId(e.target.value)}
          disabled={!!sessionId}
          className="w-full bg-slate-800 border border-slate-700 text-white text-xs rounded-xl p-2.5 font-medium
                     focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none
                     disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {scenarios.map(s => (
            <option key={s.id} value={s.id}>{s.title}</option>
          ))}
          {scenarios.length === 0 && <option value="">Ssenariy mavjud emas</option>}
        </select>

        {activeScenario && (
          <div className="bg-slate-800/80 p-3 rounded-xl border border-slate-700 space-y-1.5">
            <div className="text-[11px] font-bold text-slate-100">{activeScenario.title}</div>
            <div className="text-[10px] text-slate-400 leading-snug">{activeScenario.desc}</div>
            <div className="text-[10px] font-mono text-amber-300/90 pt-1 border-t border-slate-700/60 flex items-center gap-1">
              <Stethoscope size={11} />
              <span>Tashxis: {activeScenario.diagnosis}</span>
            </div>
          </div>
        )}
      </div>

      {/* Protokol Bosqichlari va Checklist */}
      <div className="flex-1 p-4 overflow-y-auto space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold text-slate-300 font-mono uppercase tracking-wider flex items-center gap-1.5">
            <span>Patronaj Cheklisti</span>
          </h3>
          <span className="text-[10px] font-mono font-bold text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-900">
            {progressPercent}% Bajarildi
          </span>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden border border-slate-700">
          <div
            style={{ width: `${progressPercent}%` }}
            className="h-full bg-gradient-to-r from-blue-500 to-emerald-400 transition-all duration-300"
          />
        </div>

        <ul className="space-y-2 pt-1">
          {(activeScenario?.actions || []).map((action, i) => {
            const isDone = completedActions.includes(i) || (sessionId && progressPercent >= ((i + 1) / totalActions) * 100);

            return (
              <li
                key={i}
                className={`p-2.5 rounded-xl border text-[11px] transition-all flex items-start gap-2.5 ${
                  isDone
                    ? 'bg-emerald-950/30 border-emerald-800/60 text-emerald-200'
                    : 'bg-slate-800/40 border-slate-800 text-slate-300 hover:border-slate-700'
                }`}
              >
                {isDone ? (
                  <CheckCircle2 size={15} className="text-emerald-400 mt-0.5 shrink-0" />
                ) : (
                  <Circle size={15} className="text-slate-600 mt-0.5 shrink-0" />
                )}
                <span className="leading-relaxed font-normal">{action}</span>
              </li>
            );
          })}
        </ul>
      </div>

      {/* Sessiya Taymeri va Boshqaruv Tugmalari */}
      <div className="p-4 border-t border-slate-800 bg-slate-950 space-y-3">
        <div className="flex items-center justify-between px-1">
          <span className="text-slate-400 font-mono text-xs flex items-center gap-1.5">
            <Clock size={13} />
            <span>Seans Vaqti:</span>
          </span>
          <div className={`text-xl font-mono font-extrabold tracking-wider ${
            sessionId ? 'text-emerald-400 animate-pulse' : 'text-slate-500'
          }`}>
            {formatTime(timer)}
          </div>
        </div>

        {!sessionId ? (
          <button
            onClick={handleStart}
            disabled={!selectedScenarioId}
            className="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500
                       text-white font-bold text-xs py-3 px-4 rounded-xl flex items-center justify-center gap-2
                       shadow-lg shadow-emerald-900/40 transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            <Play size={16} className="fill-white" />
            <span>SIMULYATSIYANI BOSHLASH</span>
          </button>
        ) : (
          <button
            onClick={onEndSession}
            className="w-full bg-gradient-to-r from-rose-600 to-red-600 hover:from-rose-500 hover:to-red-500
                       text-white font-bold text-xs py-3 px-4 rounded-xl flex items-center justify-center gap-2
                       shadow-lg shadow-rose-900/40 transition-all active:scale-95 cursor-pointer"
          >
            <Square size={16} className="fill-white" />
            <span>SEANSNI YAKUNLASH VA BAHOLASH</span>
          </button>
        )}
      </div>
    </div>
  );
}
