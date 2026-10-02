import React, { useState, useEffect } from 'react';
import { Activity, Wifi, Clock, Volume2 } from 'lucide-react';

/**
 * StatusBar — Yuqori boshqaruv paneli (Bemor, ESP32 Kalonka IP va Vaqt)
 */
export default function StatusBar({ activeMannequin, sessionId }) {
  const [currentTime, setCurrentTime] = useState(new Date());
  const [espIp, setEspIp] = useState(localStorage.getItem('esp32_ip') || '10.108.2.154');
  const [showIpModal, setShowIpModal] = useState(false);
  const [tempIp, setTempIp] = useState(espIp);
  const [isTestingSpeaker, setIsTestingSpeaker] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  const handleSaveIp = () => {
    localStorage.setItem('esp32_ip', tempIp.trim());
    setEspIp(tempIp.trim());
    setShowIpModal(false);
  };

  const handleTestSpeaker = async () => {
    setIsTestingSpeaker(true);
    try {
      await fetch(`http://${espIp}/test`);
    } catch (e) {
      console.warn("Kalonka test xatosi:", e);
    }
    setTimeout(() => setIsTestingSpeaker(false), 1200);
  };

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

      {/* O'ng taraf: Kalonka IP, Soat va Wi-Fi holati */}
      <div className="flex items-center gap-3">
        
        {/* ESP32 Kalonka sozlamasi */}
        <button
          type="button"
          onClick={() => {
            setTempIp(espIp);
            setShowIpModal(true);
          }}
          className="flex items-center gap-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer shadow-xs"
          title="ESP32 Kalonka manzilini sozlash"
        >
          <Volume2 size={15} />
          <span>Kalonka: {espIp}</span>
        </button>

        <div className="flex items-center gap-1.5 text-slate-600 text-xs font-medium bg-slate-100 px-2.5 py-1.5 rounded-xl border border-slate-200">
          <Clock size={14} className="text-slate-400" />
          <span>{currentTime.toLocaleTimeString('uz-UZ', { hour: '2-digit', minute: '2-digit' })}</span>
        </div>

        <div className="flex items-center gap-1.5 bg-emerald-50 text-emerald-700 border border-emerald-200 px-2.5 py-1.5 rounded-xl text-xs font-bold">
          <Wifi size={14} className="text-emerald-600" />
          <span>Ulangan</span>
        </div>
      </div>

      {/* Kalonka IP Sozlash Modali */}
      {showIpModal && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-5 max-w-sm w-full shadow-2xl border border-slate-200 space-y-4">
            <h3 className="font-bold text-slate-800 text-sm flex items-center gap-2">
              <Volume2 size={18} className="text-blue-600" />
              <span>ESP32 Kalonka Manzili</span>
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              ESP32 Serial Monitorida chiqqan IP manzil yoki nomni kiriting (masalan: 10.108.2.154 yoki medsim-speaker.local):
            </p>
            <input
              type="text"
              value={tempIp}
              onChange={(e) => setTempIp(e.target.value)}
              placeholder="10.108.2.154 yoki medsim-speaker.local"
              className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-mono text-slate-800 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            />
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleTestSpeaker}
                disabled={isTestingSpeaker}
                className="flex-1 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold py-2 rounded-xl transition-colors cursor-pointer"
              >
                {isTestingSpeaker ? 'Chalmoqda...' : '🔔 Test Ovozi'}
              </button>
              <button
                type="button"
                onClick={handleSaveIp}
                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold py-2 rounded-xl transition-colors cursor-pointer"
              >
                Saqlash
              </button>
            </div>
            <button
              type="button"
              onClick={() => setShowIpModal(false)}
              className="w-full text-center text-xs text-slate-400 hover:text-slate-600 cursor-pointer pt-1"
            >
              Yopish
            </button>
          </div>
        </div>
      )}
    </header>
  );
}
