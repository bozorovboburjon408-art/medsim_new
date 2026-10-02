import React, { useState, useEffect, useRef } from 'react';
import { Play, Square, Sparkles, Activity, Volume2, VolumeX, HeartHandshake, CheckCircle2, AlertTriangle } from 'lucide-react';
import { triggerBaby, getBabyStatus, sendBabyMotion } from '../services/api';

/**
 * BabySimulator — Chaqaloq simulyatori interfeysi (A-usul)
 * Planshetdan yig'latish va ESP32 (MPU-6050) orqali mayin tebranganda tinchlantirish.
 */
export default function BabySimulator({ onLogMessage }) {
  const [isCrying, setIsCrying] = useState(false);
  const [isSoothed, setIsSoothed] = useState(false);
  const [soothingProgress, setSoothingProgress] = useState(0);
  const [motionValue, setMotionValue] = useState(0);
  const [isRockingManual, setIsRockingManual] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(true);

  const audioCtxRef = useRef(null);
  const oscillatorIntervalRef = useRef(null);
  const rockingTimerRef = useRef(null);

  // Web Audio API orqali brauzerda chaqaloq yig'isini sintezlash (offline / demo uchun)
  const startBrowserCrySound = () => {
    if (!soundEnabled) return;
    try {
      if (!audioCtxRef.current) {
        audioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)();
      }
      const ctx = audioCtxRef.current;
      if (ctx.state === 'suspended') {
        ctx.resume();
      }

      const playCryCycle = () => {
        if (!isCrying) return;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'triangle';

        const now = ctx.currentTime;
        // Wah-wah pitch drop: 650Hz -> 450Hz
        osc.frequency.setValueAtTime(550, now);
        osc.frequency.exponentialRampToValueAtTime(750, now + 0.3);
        osc.frequency.exponentialRampToValueAtTime(420, now + 0.7);

        gain.gain.setValueAtTime(0.01, now);
        gain.gain.linearRampToValueAtTime(0.2, now + 0.15);
        gain.gain.exponentialRampToValueAtTime(0.01, now + 0.7);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(now);
        osc.stop(now + 0.7);
      };

      playCryCycle();
      oscillatorIntervalRef.current = setInterval(playCryCycle, 900);
    } catch (e) {
      console.warn("Web audio xatosi:", e);
    }
  };

  const stopBrowserSound = () => {
    if (oscillatorIntervalRef.current) {
      clearInterval(oscillatorIntervalRef.current);
      oscillatorIntervalRef.current = null;
    }
  };

  // Statusni backenddan har 800ms da so'rab turish
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const data = await getBabyStatus();
        if (data) {
          setIsCrying(data.is_crying);
          setIsSoothed(data.is_soothed);
          setSoothingProgress(data.soothing_progress);
          setMotionValue(data.motion_intensity);
        }
      } catch (e) {}
    }, 800);
    return () => clearInterval(interval);
  }, []);

  // Ovoz effektlarini holatga qarab boshqarish
  useEffect(() => {
    if (isCrying) {
      startBrowserCrySound();
    } else {
      stopBrowserSound();
    }
    return () => stopBrowserSound();
  }, [isCrying, soundEnabled]);

  // Planshet sensorini tinglash (agar planshet qo'lda tebratilsa)
  useEffect(() => {
    const handleDeviceMotion = (event) => {
      if (!isCrying) return;
      const acc = event.accelerationIncludingGravity;
      if (acc) {
        const total = (Math.abs(acc.x || 0) + Math.abs(acc.y || 0) + Math.abs(acc.z || 0));
        // Tebranish harakati aniqlanganda
        if (total > 11.5 && total < 22.0) {
          handleManualRock();
        }
      }
    };

    if (window.DeviceMotionEvent) {
      window.addEventListener('devicemotion', handleDeviceMotion);
    }
    return () => {
      if (window.DeviceMotionEvent) {
        window.removeEventListener('devicemotion', handleDeviceMotion);
      }
    };
  }, [isCrying]);

  // 1. Chaqaloqni yig'latish (A-usul)
  const handleStartCrying = async () => {
    setIsCrying(true);
    setIsSoothed(false);
    setSoothingProgress(0);
    setMotionValue(0);
    await triggerBaby('start_crying');
    if (onLogMessage) {
      onLogMessage({
        speaker: 'mannequin',
        text: "😭 [Chaqaloq baland ovozda yig'lay boshladi! Hamshira uni qo'liga olib tebratishi lozim]"
      });
    }
  };

  // 2. Majburiy to'xtatish
  const handleStopCrying = async () => {
    setIsCrying(false);
    setIsSoothed(true);
    setSoothingProgress(100);
    stopBrowserSound();
    await triggerBaby('stop_crying');
    if (onLogMessage) {
      onLogMessage({
        speaker: 'mannequin',
        text: "✨ [Chaqaloq ovuntirildi va tinchlandi]"
      });
    }
  };

  // 3. Planshetdan tebratishni simulyatsiya qilish (tugma bosib ushlab turganda)
  const handleManualRock = async () => {
    if (!isCrying) return;
    setMotionValue(65.4); // Tebranish intensivligi
    const res = await sendBabyMotion(65.4);
    if (res) {
      setSoothingProgress(res.soothing_progress);
      if (res.is_soothed) {
        setIsCrying(false);
        setIsSoothed(true);
        if (onLogMessage) {
          onLogMessage({
            speaker: 'mannequin',
            text: "🎉 [Hamshira chaqaloqni mayin tebratib ovuntirdi. Vazifa muvaffaqiyatli bajarildi!]"
          });
        }
      }
    }
  };

  const startRockingHold = () => {
    if (!isCrying) return;
    setIsRockingManual(true);
    handleManualRock();
    rockingTimerRef.current = setInterval(handleManualRock, 400);
  };

  const stopRockingHold = () => {
    setIsRockingManual(false);
    if (rockingTimerRef.current) {
      clearInterval(rockingTimerRef.current);
      rockingTimerRef.current = null;
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-50 p-5 overflow-y-auto">
      
      {/* Yuqori sarlavha */}
      <div className="bg-white rounded-2xl p-4 border border-emerald-100 shadow-xs mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-2xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-2xl shadow-inner">
            {isCrying ? '😭' : isSoothed ? '😴' : '👶'}
          </div>
          <div>
            <h3 className="font-bold text-slate-900 text-sm flex items-center gap-1.5">
              <span>Chaqaloq Parvarishi Simulyatori</span>
              <span className="text-[11px] font-semibold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full">
                A-usul: Taktil + MPU-6050
              </span>
            </h3>
            <p className="text-xs text-slate-500">
              Yig'layotgan chaqaloqni qo'lga olib mayin tebratish orqali ovuntirish
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={() => setSoundEnabled(!soundEnabled)}
          className={`p-2 rounded-xl border text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer ${
            soundEnabled ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-slate-100 text-slate-400 border-slate-200'
          }`}
          title="Ovozni yoqish / o'chirish"
        >
          {soundEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
          <span>{soundEnabled ? 'Ovoz: Yoqiq' : "Ovoz: O'chiq"}</span>
        </button>
      </div>

      {/* Asosiy Holat Kartasi */}
      <div className={`rounded-3xl p-6 border text-center transition-all duration-300 shadow-sm mb-4 ${
        isCrying
          ? 'bg-gradient-to-b from-red-50 to-white border-red-200 animate-pulse'
          : isSoothed
          ? 'bg-gradient-to-b from-emerald-50 to-white border-emerald-200'
          : 'bg-white border-slate-200'
      }`}>
        <div className="text-6xl mb-3 inline-block transition-transform duration-300 hover:scale-110">
          {isCrying ? '😭' : isSoothed ? '😴' : '👶'}
        </div>

        <h4 className={`text-lg font-bold mb-1 ${
          isCrying ? 'text-red-700' : isSoothed ? 'text-emerald-700' : 'text-slate-800'
        }`}>
          {isCrying
            ? "Chaqaloq to'xtovsiz yig'lamoqda!"
            : isSoothed
            ? "Chaqaloq ovundi va tinchlandi!"
            : "Chaqaloq tinch holatda (Krovatda)"
          }
        </h4>

        <p className="text-xs text-slate-500 max-w-md mx-auto mb-4">
          {isCrying
            ? "Hamshira chaqaloqni qo'liga olib, bag'riga bosgan holda bir maromda mayin tebrating (MPU-6050 harakatni o'lchamoqda)."
            : isSoothed
            ? "Ajoyib natija! Hamshira chaqaloqni to'g'ri holatda ovuntirdi va uning bezovtaligini bartaraf etdi."
            : "Stsenariyni boshlash uchun pastdagi 'Chaqaloqni yig'latish' tugmasini bosing."
          }
        </p>

        {/* Ovunish Progress Bar */}
        <div className="max-w-md mx-auto bg-slate-100 rounded-full h-4 p-0.5 border border-slate-200 overflow-hidden mb-2">
          <div
            className={`h-full rounded-full transition-all duration-300 ${
              soothingProgress >= 100 ? 'bg-emerald-500' : 'bg-gradient-to-r from-amber-400 to-emerald-500'
            }`}
            style={{ width: `${soothingProgress}%` }}
          />
        </div>

        <div className="flex justify-between max-w-md mx-auto text-xs font-semibold text-slate-500">
          <span>Ovuntirish darajasi:</span>
          <span className={soothingProgress >= 100 ? 'text-emerald-600 font-bold' : 'text-slate-700'}>
            {soothingProgress}%
          </span>
        </div>
      </div>

      {/* Boshqaruv Tugmalari */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        {/* Yig'latish tugmasi (A-usul) */}
        <button
          type="button"
          onClick={handleStartCrying}
          disabled={isCrying}
          className={`p-4 rounded-2xl font-bold text-sm flex items-center justify-center gap-2 shadow-sm transition-all cursor-pointer ${
            isCrying
              ? 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed'
              : 'bg-red-600 hover:bg-red-700 text-white hover:shadow-red-200 hover:shadow-lg active:scale-98'
          }`}
        >
          <Play size={18} className="fill-white" />
          <span>1. Chaqaloqni yig'latish</span>
        </button>

        {/* Tebratish / Ovuntirish (Simulyatsiya yoki MPU-6050) */}
        <button
          type="button"
          onMouseDown={startRockingHold}
          onMouseUp={stopRockingHold}
          onTouchStart={startRockingHold}
          onTouchEnd={stopRockingHold}
          disabled={!isCrying}
          className={`p-4 rounded-2xl font-bold text-sm flex items-center justify-center gap-2 border shadow-sm transition-all select-none ${
            !isCrying
              ? 'bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed'
              : isRockingManual
              ? 'bg-emerald-600 text-white scale-98 shadow-emerald-200 shadow-md border-emerald-600'
              : 'bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border-emerald-300 active:scale-98 cursor-pointer'
          }`}
        >
          <HeartHandshake size={18} />
          <span>{isRockingManual ? 'Tebratilmoqda...' : '2. Bosib turib tebrating (3 soniya)'}</span>
        </button>
      </div>

      {/* MPU-6050 Sensori holati */}
      <div className="bg-white rounded-2xl p-4 border border-slate-200 flex items-center justify-between text-xs">
        <div className="flex items-center gap-2 text-slate-700 font-semibold">
          <Activity size={16} className="text-blue-500 animate-pulse" />
          <span>ESP32 MPU-6050 Harakat Sensori:</span>
        </div>
        <div className="font-mono font-bold bg-slate-100 text-slate-800 px-2.5 py-1 rounded-lg border border-slate-200">
          {motionValue > 0 ? `${motionValue.toFixed(1)} dps` : '0.0 dps (Turg\'un)'}
        </div>
      </div>

      {/* Tibbiy ko'rsatmalar */}
      <div className="mt-4 bg-blue-50/70 border border-blue-100 rounded-2xl p-4 text-xs text-blue-900 space-y-2">
        <h5 className="font-bold flex items-center gap-1.5 text-blue-950">
          <CheckCircle2 size={14} className="text-blue-600" />
          <span>Hamshira uchun baholash mezonlari:</span>
        </h5>
        <ul className="list-disc list-inside space-y-1 text-blue-800/90 leading-relaxed">
          <li>Chaqaloqning bosh va bo'yin qismini qo'l bilan suyab ehtiyotkorlik bilan ko'tarish;</li>
          <li>Bag'riga bosgan holda ritmik va mayin tebratish (qo'pol silkimaslik);</li>
          <li>Chaqaloq tinchlangach, tana harorati, qorin tarangligi va taglik holatini tekshirish.</li>
        </ul>
      </div>

    </div>
  );
}
