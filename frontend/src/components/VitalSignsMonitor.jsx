import React, { useEffect, useRef } from 'react';
import { Heart, Activity, Thermometer, Droplet, Baby, Wind, ShieldCheck } from 'lucide-react';

/**
 * VitalSignsMonitor — Real-vaqtli klinik monitor paneli.
 * Bemorning fiziologik ko'rsatkichlari va jonli EKG kardiogramma chizig'ini aks ettiradi.
 */

const VITAL_PROFILES = {
  bobo: {
    hr: 88,
    hrStatus: 'Taxikardiya',
    bpSys: 180,
    bpDia: 100,
    bpStatus: 'Gipertenziya III',
    bpAlert: true,
    temp: 36.6,
    tempStatus: 'Me\'yorda',
    spo2: 94,
    spo2Status: 'Suboptimal',
    rr: 22,
    rrLabel: 'Nafas (RR)',
    rhythm: 'Sinus ritmi, ekstrasistoliya',
    code: 'MK-701-GER'
  },
  homilador: {
    hr: 82,
    hrStatus: 'Ritmik',
    bpSys: 110,
    bpDia: 70,
    bpStatus: 'Me\'yorda',
    bpAlert: false,
    temp: 37.5,
    tempStatus: 'Subfebril',
    tempAlert: true,
    spo2: 98,
    spo2Status: 'Optimal',
    rr: 145,
    rrLabel: 'Homila YU (FHR)',
    rhythm: 'Homila KTG barqaror',
    code: 'MK-320-OBG'
  },
  bola: {
    hr: 115,
    hrStatus: 'Taxikardiya',
    bpSys: 95,
    bpDia: 60,
    bpStatus: 'Yoshiga mos',
    bpAlert: false,
    temp: 39.5,
    tempStatus: 'Gipertermiya',
    tempAlert: true,
    spo2: 97,
    spo2Status: 'Optimal',
    rr: 28,
    rrLabel: 'Nafas (RR)',
    rhythm: 'Sinus taxikardiyasi',
    code: 'MK-051-PED'
  },
  chaqaloq: {
    hr: 138,
    hrStatus: 'Normokardiya',
    bpSys: 70,
    bpDia: 45,
    bpStatus: 'Neonatal norma',
    bpAlert: false,
    temp: 36.8,
    tempStatus: 'Termostabil',
    tempAlert: false,
    spo2: 92,
    spo2Status: 'Gipoksiya xavfi',
    spo2Alert: true,
    rr: 48,
    rrLabel: 'Nafas (RR)',
    rhythm: 'Asfiksiya nazorati',
    code: 'MK-001-NEO'
  }
};

export default function VitalSignsMonitor({ activeMannequin }) {
  const canvasRef = useRef(null);
  const data = activeMannequin ? (VITAL_PROFILES[activeMannequin.slug] || VITAL_PROFILES.bobo) : null;

  // Jonli EKG kardiogrammasi canvas animatsiyasi
  useEffect(() => {
    if (!data) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationFrameId;
    let x = 0;
    const height = canvas.height;
    const width = canvas.width;
    const points = [];

    // Fon to'ri chizish
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;
    for (let i = 0; i < width; i += 20) {
      ctx.beginPath();
      ctx.moveTo(i, 0);
      ctx.lineTo(i, height);
      ctx.stroke();
    }
    for (let j = 0; j < height; j += 15) {
      ctx.beginPath();
      ctx.moveTo(0, j);
      ctx.lineTo(width, j);
      ctx.stroke();
    }

    const render = () => {
      // EKG to'lqin formulasini generatsiya qilish (P-Q-R-S-T to'lqini)
      const phase = (x % 100);
      let y = height / 2;

      if (phase >= 15 && phase < 22) {
        // P to'lqin
        y -= Math.sin(((phase - 15) / 7) * Math.PI) * 6;
      } else if (phase >= 25 && phase < 28) {
        // Q tishcha
        y += 4;
      } else if (phase >= 28 && phase < 34) {
        // R cho'qqisi
        y -= 26;
      } else if (phase >= 34 && phase < 38) {
        // S tishcha
        y += 8;
      } else if (phase >= 48 && phase < 60) {
        // T to'lqin
        y -= Math.sin(((phase - 48) / 12) * Math.PI) * 9;
      }

      points.push({ x, y });

      // Chizish
      ctx.fillStyle = 'rgba(15, 23, 42, 0.08)';
      ctx.fillRect(0, 0, width, height);

      // EKG yashil chiziq
      ctx.strokeStyle = '#10b981';
      ctx.lineWidth = 2;
      ctx.shadowColor = '#10b981';
      ctx.shadowBlur = 4;
      ctx.beginPath();

      const startIndex = Math.max(0, points.length - 80);
      for (let i = startIndex; i < points.length; i++) {
        if (i === startIndex) {
          ctx.moveTo(points[i].x % width, points[i].y);
        } else {
          ctx.lineTo(points[i].x % width, points[i].y);
        }
      }
      ctx.stroke();
      ctx.shadowBlur = 0;

      x += 2;
      if (points.length > 200) points.shift();

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [data]);

  if (!activeMannequin) {
    return (
      <div className="bg-slate-900 text-slate-400 px-6 py-3 border-b border-slate-800 flex items-center justify-between text-xs font-mono">
        <div className="flex items-center gap-2">
          <Activity size={16} className="text-slate-500 animate-pulse" />
          <span>KLINIK TELEMETRIYA KANALI KUTILMOQDA (BEMORNI TANLANG)</span>
        </div>
        <div className="flex items-center gap-4 text-slate-500">
          <span>SAMPLING: 500 Hz</span>
          <span>FILTR: 0.05-40 Hz</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-slate-950 text-white px-5 py-2.5 border-b border-slate-800 shadow-inner select-none">
      <div className="flex items-center justify-between gap-4">
        
        {/* Kardiomonitor EKG Ekran */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="relative rounded-lg overflow-hidden border border-slate-800 bg-slate-900 shadow-inner">
            <canvas ref={canvasRef} width={180} height={46} className="block" />
            <div className="absolute top-1 left-2 text-[9px] font-mono text-emerald-400 font-bold tracking-wider flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping"></span>
              LEAD II
            </div>
          </div>
          <div>
            <div className="flex items-center gap-1.5 text-xs text-slate-400 font-medium">
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                {data.code}
              </span>
              <span className="text-slate-200 font-semibold">{activeMannequin.name}</span>
            </div>
            <div className="text-[10px] text-slate-400 font-mono flex items-center gap-1 mt-0.5">
              <ShieldCheck size={11} className="text-blue-400" />
              <span>{data.rhythm}</span>
            </div>
          </div>
        </div>

        {/* 4 ta Asosiy Vital Ko'rsatkichlar */}
        <div className="grid grid-cols-4 gap-2.5 flex-1 max-w-2xl">
          
          {/* 1. PULS (HR) */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-lg px-3 py-1.5 flex items-center justify-between">
            <div>
              <div className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1">
                <Heart size={11} className="text-emerald-400 fill-emerald-400 animate-pulse" />
                <span>PULS (HR)</span>
              </div>
              <div className="text-xl font-mono font-extrabold text-emerald-300 leading-none mt-1">
                {data.hr}
                <span className="text-[10px] font-normal text-slate-400 ml-1">bpm</span>
              </div>
            </div>
            <span className="text-[9px] font-semibold text-emerald-500/80 bg-emerald-950/60 px-1.5 py-0.5 rounded border border-emerald-900/50">
              {data.hrStatus}
            </span>
          </div>

          {/* 2. ARTERIAL BOSIM (NIBP) */}
          <div className={`rounded-lg px-3 py-1.5 flex items-center justify-between border ${
            data.bpAlert 
              ? 'bg-amber-950/40 border-amber-800/80' 
              : 'bg-slate-900/90 border-slate-800'
          }`}>
            <div>
              <div className="text-[10px] font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1">
                <Activity size={11} className="text-amber-400" />
                <span>BOSIM (NIBP)</span>
              </div>
              <div className="text-xl font-mono font-extrabold text-amber-300 leading-none mt-1">
                {data.bpSys}/{data.bpDia}
                <span className="text-[9px] font-normal text-slate-400 ml-1">mmHg</span>
              </div>
            </div>
            <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded border ${
              data.bpAlert
                ? 'bg-amber-900/50 text-amber-300 border-amber-700 animate-pulse'
                : 'bg-slate-800 text-slate-400 border-slate-700'
            }`}>
              {data.bpStatus}
            </span>
          </div>

          {/* 3. TANA HARORATI (TEMP) */}
          <div className={`rounded-lg px-3 py-1.5 flex items-center justify-between border ${
            data.tempAlert 
              ? 'bg-rose-950/40 border-rose-800/80' 
              : 'bg-slate-900/90 border-slate-800'
          }`}>
            <div>
              <div className="text-[10px] font-bold text-rose-400 uppercase tracking-wider flex items-center gap-1">
                <Thermometer size={11} className="text-rose-400" />
                <span>HARORAT</span>
              </div>
              <div className="text-xl font-mono font-extrabold text-rose-300 leading-none mt-1">
                {data.temp}°
                <span className="text-[10px] font-normal text-slate-400 ml-0.5">C</span>
              </div>
            </div>
            <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded border ${
              data.tempAlert
                ? 'bg-rose-900/50 text-rose-300 border-rose-700 animate-pulse'
                : 'bg-slate-800 text-slate-400 border-slate-700'
            }`}>
              {data.tempStatus}
            </span>
          </div>

          {/* 4. SPO2 YOKI HOMILA YURAK URISHI */}
          <div className="bg-slate-900/90 border border-slate-800 rounded-lg px-3 py-1.5 flex items-center justify-between">
            <div>
              <div className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-1">
                {activeMannequin.slug === 'homilador' ? (
                  <Baby size={11} className="text-cyan-400" />
                ) : (
                  <Wind size={11} className="text-cyan-400" />
                )}
                <span>{data.rrLabel}</span>
              </div>
              <div className="text-xl font-mono font-extrabold text-cyan-300 leading-none mt-1">
                {data.rr}
                <span className="text-[9px] font-normal text-slate-400 ml-1">
                  {activeMannequin.slug === 'homilador' ? 'bpm' : '/min'}
                </span>
              </div>
            </div>
            <div className="text-right">
              <div className="text-[9px] text-slate-400 font-mono">SpO₂ {data.spo2}%</div>
              <span className="text-[8px] font-semibold text-cyan-400">
                {data.spo2Status}
              </span>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
