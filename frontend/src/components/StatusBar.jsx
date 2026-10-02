import React, { useState, useEffect } from 'react';
import { Activity, Wifi, Shield, Cpu, Clock, Layers } from 'lucide-react';

/**
 * StatusBar — Tibbiy Simulyatsiya Ishchi Stansiyasining Yuqori Paneli
 */
export default function StatusBar({ activeMannequin, sessionId }) {
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="h-14 bg-slate-900 border-b border-slate-800 px-6 flex items-center justify-between shadow-md shrink-0 select-none">
      {/* Chap: Logo va Tibbiy Markaz Nomi */}
      <div className="flex items-center gap-3">
        <div className="bg-blue-600 text-white p-2 rounded-xl shadow-lg shadow-blue-500/20 flex items-center justify-center">
          <Activity size={20} className="animate-pulse" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base font-extrabold tracking-tight text-white font-mono">
              MedSim <span className="text-blue-400 font-sans font-normal text-xs uppercase px-1.5 py-0.5 bg-blue-950 border border-blue-800 rounded">AIoT 2.0</span>
            </h1>
            <span className="text-[10px] font-mono text-slate-400 hidden md:inline-block bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
              STATION #04 • CLINICAL SIM
            </span>
          </div>
          <p className="text-[11px] text-slate-400 font-medium leading-none mt-0.5">
            Tibbiy Amaliy Ko'nikmalar va Patronaj Simulyatori
          </p>
        </div>
      </div>

      {/* O'rta: Sessiya va Telemetriya */}
      <div className="flex items-center gap-3">
        {sessionId ? (
          <div className="flex items-center gap-2 bg-emerald-950/70 border border-emerald-800/80 px-3 py-1 rounded-full text-emerald-300 text-xs font-mono">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
            <span className="font-semibold">PATRONAJ SEANSI: #{sessionId.substring(0, 6).toUpperCase()}</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 bg-slate-800/60 border border-slate-700 px-3 py-1 rounded-full text-slate-400 text-xs font-mono">
            <Layers size={12} className="text-slate-400" />
            <span>KUTISH REJIMI (STANDBY)</span>
          </div>
        )}

        {activeMannequin && (
          <div className="hidden lg:flex items-center gap-1.5 text-xs bg-slate-800 border border-slate-700 px-3 py-1 rounded-lg text-slate-200">
            <span className="text-slate-400 font-mono text-[11px]">Bemor:</span>
            <span className="font-bold text-white flex items-center gap-1">
              <span>{activeMannequin.emoji}</span>
              <span>{activeMannequin.name}</span>
            </span>
          </div>
        )}
      </div>

      {/* O'ng: IoT Hardware Holati, Vaqt va Xavfsizlik */}
      <div className="flex items-center gap-4 text-xs font-mono">
        {/* Hardware Status */}
        <div className="hidden sm:flex items-center gap-2 text-slate-300 bg-slate-800/80 border border-slate-700/80 px-2.5 py-1 rounded-lg">
          <Cpu size={14} className="text-blue-400" />
          <span className="text-[11px] text-slate-300">ESP32 SoC: <strong className="text-emerald-400 font-bold">4/4 Online</strong></span>
          <div className="flex items-center gap-1 text-emerald-400 font-bold ml-1 pl-1.5 border-l border-slate-700">
            <Wifi size={13} />
            <span className="text-[10px]">192.168.1.x</span>
          </div>
        </div>

        {/* Vaqt */}
        <div className="flex items-center gap-1.5 text-slate-300 font-mono font-medium">
          <Clock size={14} className="text-slate-400" />
          <span>{currentTime.toLocaleTimeString('uz-UZ')}</span>
        </div>

        {/* Xavfsizlik statusi */}
        <div className="hidden xl:flex items-center gap-1 text-slate-400 bg-slate-800/40 px-2 py-1 rounded border border-slate-800 text-[10px]">
          <Shield size={12} className="text-emerald-400" />
          <span>AI GUARDRAILS ACTIVE</span>
        </div>
      </div>
    </header>
  );
}
