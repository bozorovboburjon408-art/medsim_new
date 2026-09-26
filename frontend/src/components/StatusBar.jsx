import React, { useState, useEffect } from 'react';
import { Activity, Wifi, WifiOff, Clock } from 'lucide-react';

/**
 * Yuqori holat paneli — logo, sessiya info, vaqt, Wi-Fi holati.
 */
export default function StatusBar({ activeMannequin, sessionId }) {
  const [currentTime, setCurrentTime] = useState(new Date());
  const isConnected = true; // Backend ulanganda real holatga o'zgaradi

  // Soatni yangilab turish
  useEffect(() => {
    const interval = setInterval(() => setCurrentTime(new Date()), 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-14 bg-white border-b border-slate-200 px-6 flex items-center justify-between shadow-sm shrink-0">
      {/* Logo */}
      <div className="flex items-center space-x-3">
        <div className="bg-blue-600 text-white p-1.5 rounded-lg shadow-sm">
          <Activity size={22} />
        </div>
        <div>
          <h1 className="text-lg font-bold text-slate-800 leading-none">MedSim</h1>
          <p className="text-[10px] text-slate-400 leading-none mt-0.5">Hamshiralar Simulyatsiya Tizimi</p>
        </div>
      </div>

      {/* O'rta qism — holat ko'rsatkichlari */}
      <div className="flex items-center space-x-4 text-sm">
        {/* Sessiya badge */}
        {sessionId && (
          <div className="flex items-center bg-green-50 text-green-700 px-3 py-1 rounded-full border border-green-200">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse mr-2" />
            <span className="font-medium text-xs">Seans faol</span>
          </div>
        )}

        {/* Faol manikenning */}
        {activeMannequin && (
          <div className="flex items-center space-x-2 text-slate-700">
            <span className="text-sm font-medium text-slate-500">Faol:</span>
            <span className="bg-slate-100 px-2.5 py-1 rounded-lg text-xs font-bold flex items-center gap-1.5">
              <span>{activeMannequin.emoji}</span>
              <span>{activeMannequin.name}</span>
            </span>
          </div>
        )}
      </div>

      {/* O'ng qism — vaqt va Wi-Fi */}
      <div className="flex items-center space-x-4">
        {/* Vaqt */}
        <div className="flex items-center text-slate-500 text-sm">
          <Clock size={14} className="mr-1.5" />
          <span className="font-medium">
            {currentTime.toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>

        {/* Wi-Fi */}
        <div className="flex items-center gap-1.5">
          {isConnected ? (
            <>
              <Wifi size={18} className="text-green-500" />
              <span className="text-[10px] font-bold text-green-600 uppercase">Ulangan</span>
            </>
          ) : (
            <>
              <WifiOff size={18} className="text-red-500" />
              <span className="text-[10px] font-bold text-red-500 uppercase">Uzilgan</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
