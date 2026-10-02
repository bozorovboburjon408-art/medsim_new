"""
Tizim Xavfsizlik va Litsenziya Boshqaruvi Moduli (System Lock & License Guard)
===========================================================================
Ushbu modul obuna muddati tugaganida butun tizimni (veb-sahifalar, API va WebSockets)
to'liq va chetlab o'tib bo'lmaydigan qilib qulflash uchun xizmat qiladi.

Qulflashni o'chirish / yoqish:
- SYSTEM_LOCKED = True   -> Tizim to'liq bloklangan ("Obuna muddati tugadi, dasturchiga murojaat qiling")
- SYSTEM_LOCKED = False  -> Tizim normal, ochiq holatda ishlaydi

Dasturchi maxfiy master kaliti: "21082007Bb"
URL parametri orqali kirish: ?unlock_key=21082007Bb
"""

import os
from typing import Optional
from fastapi import Request, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse

# ==============================================================================
# ASOSIY XAVFSIZLIK SOZLAMALARI
# ==============================================================================
SYSTEM_LOCKED = False  # True = Qulflangan, False = Ochiq
MASTER_UNLOCK_KEY = "21082007Bb"  # Dasturchi maxfiy master kaliti
LOCK_MESSAGE = "Obuna muddati tugadi, dasturchiga murojaat qiling"

# ==============================================================================
# QULF HOLATINI TEKSHIRISH
# ==============================================================================
def is_system_locked(request: Optional[Request] = None) -> bool:
    """Tizim qulflanganligini tekshiradi (Faqat dasturchi maxfiy kodi orqali ochiladi)"""
    if not SYSTEM_LOCKED:
        return False
        
    if request is not None:
        # 1. URL query parametri orqali tekshirish: ?unlock_key=21082007Bb yoki ?key=21082007Bb
        query_key = request.query_params.get("unlock_key") or request.query_params.get("key") or request.query_params.get("dev")
        if query_key == MASTER_UNLOCK_KEY:
            return False
            
        # 2. Cookie orqali tekshirish
        cookie_key = request.cookies.get("med_dev_unlock_token")
        if cookie_key == MASTER_UNLOCK_KEY:
            return False
            
        # 3. Header orqali tekshirish
        header_key = request.headers.get("X-Dev-Unlock-Key")
        if header_key == MASTER_UNLOCK_KEY:
            return False
            
    return True

def is_system_locked_simple() -> bool:
    """WebSockets yoki oddiy kontekstlar uchun tezkor tekshiruv"""
    return SYSTEM_LOCKED

# ==============================================================================
# MUTLAQO CHETLAB O'TIB BO'LMAYDIGAN QULF EKRANI (HTML + CSS + JS)
# Kirish cheklandi — Obuna muddati tugadi
# ==============================================================================
LOCK_SCREEN_HTML = """<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>Xizmat to'xtatilgan — Kirish cheklandi</title>
    <link rel="icon" href="/static/logo.png">
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@500;700&display=swap');
        
        * {
            -webkit-touch-callout: none;
            -webkit-user-select: none;
            user-select: none;
            box-sizing: border-box;
            cursor: default;
        }

        body {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: #060913;
            color: #f8fafc;
            min-height: 100vh;
            margin: 0;
            padding: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            background-image: 
                radial-gradient(circle at 50% 20%, rgba(220, 38, 38, 0.18) 0%, transparent 50%),
                radial-gradient(circle at 80% 80%, rgba(245, 158, 11, 0.08) 0%, transparent 40%),
                radial-gradient(circle at 20% 80%, rgba(220, 38, 38, 0.08) 0%, transparent 40%);
        }

        .mono {
            font-family: 'JetBrains Mono', monospace;
        }

        /* Pulse Animations */
        @keyframes lockPulse {
            0%, 100% {
                transform: scale(1);
                box-shadow: 0 0 35px rgba(239, 68, 68, 0.4), inset 0 0 20px rgba(239, 68, 68, 0.2);
            }
            50% {
                transform: scale(1.05);
                box-shadow: 0 0 60px rgba(239, 68, 68, 0.7), inset 0 0 30px rgba(239, 68, 68, 0.4);
            }
        }

        @keyframes ringWave {
            0% { transform: scale(0.9); opacity: 0.8; }
            100% { transform: scale(1.45); opacity: 0; }
        }

        .lock-icon-container {
            position: relative;
            width: 96px;
            height: 96px;
            border-radius: 50%;
            background: linear-gradient(135deg, #1e1b2e 0%, #0f172a 100%);
            border: 2px solid #ef4444;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: lockPulse 2.8s infinite ease-in-out;
            pointer-events: none;
        }

        .lock-ring {
            position: absolute;
            inset: -8px;
            border-radius: 50%;
            border: 2px solid rgba(239, 68, 68, 0.5);
            animation: ringWave 2.8s infinite cubic-bezier(0.2, 0.8, 0.2, 1);
            pointer-events: none;
        }

        /* Glassmorphism Card */
        .glass-card {
            background: rgba(15, 23, 42, 0.85);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(239, 68, 68, 0.3);
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.9), 0 0 40px -10px rgba(220, 38, 38, 0.25);
        }

        .glass-inset {
            background: rgba(8, 12, 22, 0.75);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }

        /* Scanline effect */
        .scanlines {
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%);
            background-size: 100% 4px;
            z-index: 1;
            pointer-events: none;
            opacity: 0.35;
        }
    </style>
</head>
<body oncontextmenu="return false;">
    <div class="scanlines"></div>

    <main class="relative z-10 w-full max-w-2xl px-4 py-8 mx-auto">
        <div class="glass-card rounded-3xl p-6 sm:p-10 text-center relative overflow-hidden">
            
            <!-- Top Gradient Bar -->
            <div class="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-red-600 via-amber-500 to-red-600"></div>

            <!-- Organization Badge -->
            <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-red-950/70 border border-red-500/30 text-red-400 text-xs sm:text-sm font-semibold mb-6 uppercase tracking-wider">
                <span class="w-2 h-2 rounded-full bg-red-500 animate-ping"></span>
                <span>RO'TFMXMO va UIM Navoiy filiali</span>
            </div>

            <!-- Glowing Lock Icon (No clicks allowed) -->
            <div class="flex justify-center mb-6">
                <div class="lock-icon-container">
                    <div class="lock-ring"></div>
                    <i class="fa-solid fa-lock text-4xl text-red-500 drop-shadow-[0_0_12px_rgba(239,68,68,0.8)]"></i>
                </div>
            </div>

            <!-- Main Notice -->
            <h1 class="text-2xl sm:text-3xl md:text-4xl font-black text-white tracking-tight leading-tight mb-4">
                Obuna muddati tugadi, dasturchiga murojaat qiling
            </h1>

            <p class="text-slate-300 text-sm sm:text-base leading-relaxed max-w-lg mx-auto mb-8 font-normal">
                Ushbu tibbiy simulyator va monitoring tizimidan foydalanish litsenziyasi muddati yakunlangan. Barcha interaktiv klinik modullar, AI bemor va telemetriya vaqtincha to'xtatildi.
            </p>

            <!-- Information Details Inset -->
            <div class="glass-inset rounded-2xl p-4 sm:p-5 text-left mb-6 space-y-3">
                <div class="flex items-center justify-between text-xs sm:text-sm py-1 border-b border-slate-800/80">
                    <span class="text-slate-400 flex items-center gap-2">
                        <i class="fa-solid fa-shield-halved text-red-400"></i> Xavfsizlik holati:
                    </span>
                    <span class="font-bold text-red-400 uppercase tracking-wide">Kirish cheklandi</span>
                </div>
                <div class="flex items-center justify-between text-xs sm:text-sm py-1 border-b border-slate-800/80">
                    <span class="text-slate-400 flex items-center gap-2">
                        <i class="fa-solid fa-fingerprint text-slate-400"></i> Tizim ID:
                    </span>
                    <span class="mono font-semibold text-slate-200">MED-SIM-UZ-7704</span>
                </div>
                <div class="flex items-center justify-between text-xs sm:text-sm py-1">
                    <span class="text-slate-400 flex items-center gap-2">
                        <i class="fa-solid fa-headset text-emerald-400"></i> Qayta faollashtirish:
                    </span>
                    <span class="font-semibold text-emerald-400">Dasturchi / CAIL Lab</span>
                </div>
            </div>

            <!-- Footer (Clean & Protected) -->
            <div class="flex items-center justify-center text-xs text-slate-500 pt-4 border-t border-slate-800/60">
                <div class="flex items-center gap-2">
                    <i class="fa-solid fa-microchip text-slate-600"></i>
                    <span>NDKTU CAIL Laboratoriyasi &copy; 2026</span>
                </div>
            </div>
        </div>
    </main>

    <script>
        // Mutlaq himoya: O'ng tugma va barcha ishlab chiquvchi tugmalari bloklangan
        document.addEventListener('contextmenu', e => e.preventDefault());
        document.addEventListener('keydown', e => {
            if (
                e.key === 'F12' ||
                (e.ctrlKey && e.shiftKey && (e.key === 'I' || e.key === 'i' || e.key === 'J' || e.key === 'j' || e.key === 'C' || e.key === 'c')) ||
                (e.ctrlKey && (e.key === 'u' || e.key === 'U' || e.key === 's' || e.key === 'S'))
            ) {
                e.preventDefault();
                return false;
            }
        });
    </script>
</body>
</html>
"""

def get_lock_html() -> str:
    """Qulf ekrani HTML matnini qaytaradi"""
    return LOCK_SCREEN_HTML

def apply_system_lock_middleware(app):
    """
    FastAPI ilovasiga avtomatik qulf middleware o'rnatadi.
    Barcha HTTP so'rovlarni (HTML, JSON, API) to'xtatadi.
    """
    @app.middleware("http")
    async def _system_lock_guard_middleware(request: Request, call_next):
        if is_system_locked(request):
            # API endpointlar uchun 403 JSON qaytarish
            if request.url.path.startswith("/api/"):
                return JSONResponse(
                    status_code=403,
                    content={
                        "status": "error",
                        "code": "SUBSCRIPTION_EXPIRED",
                        "message": LOCK_MESSAGE,
                        "locked": True
                    }
                )
            # Static logo yoki favicon
            if request.url.path == "/static/logo.png" or request.url.path == "/favicon.ico":
                return await call_next(request)
                
            # Barcha sahifalar uchun qulf ekrani
            return HTMLResponse(content=get_lock_html(), status_code=403)
            
        return await call_next(request)
