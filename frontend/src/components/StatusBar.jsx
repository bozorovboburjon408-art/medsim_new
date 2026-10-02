import React, { useState, useEffect } from 'react';
import { Activity, Wifi, Clock } from 'lucide-react';

/**
 * StatusBar — Sodda, oq va toza yuqori panel
 */
export default function StatusBar({ activeMannequin, sessionId }) {
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between shadow-xs shrink-0 select-none">
      {/* Logo va Tizim Nomi */}
      <div className="flex items-center gap-3">
        <div className="bg-blue-600 text-white p-2 rounded-xl shadow-sm flex items-center justify-center">
          <Activity size={22} />
        </div>
        <div>
          <h1 className="text-lg font-bold text-slate-900 leading-none">MedSim</h1>
          <p className="text-xs text-slate-500 leading-none mt-1">Hamshiralar Simulyatsiya Tizimi</p>
        </div>
      </div>

      {/* Faol bemor va seans holati */}
      <div className="flex items-center gap-3">
        {sessionId && (
          <div className="flex items-center gap-2 bg-emerald-50 text-emerald-700 border border-emerald-200 px-3.5 py-1 rounded-full text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span>Mashg'ulot davom etmoqda</span>
          </div>
        )}

        {activeMannequin && (
          <div className="flex items-center gap-2 bg-slate-100 border border-slate-200 px-3.5 py-1 rounded-xl text-xs text-slate-700">
            <span className="text-slate-500">Bemor:</span>
            <span className="font-bold text-slate-900 flex items-center gap-1.5">
              <span>{activeMannequin.emoji}</span>
              <span>{activeMannequin.name}</span>
            </span>
          </div>
        )}
      </div>

      {/* O'ng taraf: Soat va Wi-Fi holati */}
      <div className="flex items-center gap-5">
        <div className="flex items-center gap-1.5 text-slate-600 text-sm font-medium">
          <Clock size={16} className="text-slate-400" />
          <span>{currentTime.toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
        </div>

        <div className="flex items-center gap-1.5 bg-emerald-50 text-emerald-700 border border-emerald-200 px-2.5 py-1 rounded-lg text-xs font-bold">
          <Wifi size={15} className="text-emerald-600" />
          <span>Ulangan</span>
        </div>
      </div>
    </header>
  );
}
