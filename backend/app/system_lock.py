"""
Tizim Xavfsizlik va Litsenziya Boshqaruvi Moduli (System Lock & License Guard)
===========================================================================
Ushbu modul to'lov amalga oshirilmagunicha butun tizimni (veb-sahifalar, API va WebSockets)
to'liq va chetlab o'tib bo'lmaydigan qilib qulflash uchun xizmat qiladi.

Qulflashni o'chirish / yoqish:
- SYSTEM_LOCKED = True   -> Tizim to'liq bloklangan ("Avval dasturni pulini to'lang!!!")
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
SYSTEM_LOCKED = True  # True = Qulflangan, False = Ochiq
MASTER_UNLOCK_KEY = "21082007Bb"  # Dasturchi maxfiy master kaliti
LOCK_MESSAGE = "Avval dasturni pulini to'lang!!!"

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
# Katta, qat'iy "Avval dasturni pulini to'lang!!!" ogohlantirishi bilan
# ==============================================================================
LOCK_SCREEN_HTML = """<!DOCTYPE html>
<html lang="uz">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>KIRISH CHEKLANGAN — Avval dasturni pulini to'lang!!!</title>
    <link rel="icon" href="/static/logo.png">
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@500;700;800&display=swap');
        
        * {
            -webkit-touch-callout: none;
            -webkit-user-select: none;
            user-select: none;
            box-sizing: border-box;
            cursor: default;
        }

        body {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: #05070e;
            color: #f8fafc;
            min-height: 100vh;
            margin: 0;
            padding: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            background-image: 
                radial-gradient(circle at 50% 25%, rgba(239, 68, 68, 0.25) 0%, transparent 60%),
                radial-gradient(circle at 80% 80%, rgba(220, 38, 38, 0.12) 0%, transparent 45%),
                radial-gradient(circle at 20% 80%, rgba(239, 68, 68, 0.12) 0%, transparent 45%);
        }

        .mono {
            font-family: 'JetBrains Mono', monospace;
        }

        /* Pulse Animations */
        @keyframes lockPulse {
            0%, 100% {
                transform: scale(1);
                box-shadow: 0 0 45px rgba(239, 68, 68, 0.5), inset 0 0 25px rgba(239, 68, 68, 0.3);
            }
            50% {
                transform: scale(1.06);
                box-shadow: 0 0 75px rgba(239, 68, 68, 0.85), inset 0 0 35px rgba(239, 68, 68, 0.5);
            }
        }

        @keyframes ringWave {
            0% { transform: scale(0.9); opacity: 0.9; }
            100% { transform: scale(1.5); opacity: 0; }
        }

        @keyframes glowText {
            0%, 100% {
                text-shadow: 0 0 15px rgba(239, 68, 68, 0.8), 0 0 30px rgba(239, 68, 68, 0.5);
            }
            50% {
                text-shadow: 0 0 30px rgba(239, 68, 68, 1), 0 0 50px rgba(239, 68, 68, 0.8), 0 0 70px rgba(255, 0, 0, 0.6);
            }
        }

        .glow-title {
            animation: glowText 2s infinite ease-in-out;
        }

        .lock-icon-container {
            position: relative;
            width: 104px;
            height: 104px;
            border-radius: 50%;
            background: linear-gradient(135deg, #271015 0%, #0f0a12 100%);
            border: 3px solid #ef4444;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: lockPulse 2.5s infinite ease-in-out;
            pointer-events: none;
        }

        .lock-ring {
            position: absolute;
            inset: -10px;
            border-radius: 50%;
            border: 2px solid rgba(239, 68, 68, 0.6);
            animation: ringWave 2.5s infinite cubic-bezier(0.2, 0.8, 0.2, 1);
            pointer-events: none;
        }

        /* Glassmorphism Card */
        .glass-card {
            background: rgba(15, 18, 30, 0.92);
            backdrop-filter: blur(25px);
            -webkit-backdrop-filter: blur(25px);
            border: 2px solid rgba(239, 68, 68, 0.45);
            box-shadow: 0 30px 60px -15px rgba(0, 0, 0, 0.95), 0 0 50px -10px rgba(239, 68, 68, 0.35);
        }

        .glass-inset {
            background: rgba(8, 10, 18, 0.85);
            border: 1px solid rgba(239, 68, 68, 0.25);
        }

        /* Scanline effect */
        .scanlines {
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background: linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.3) 50%);
            background-size: 100% 4px;
            z-index: 1;
            pointer-events: none;
            opacity: 0.4;
        }
    </style>
</head>
<body oncontextmenu="return false;">
    <div class="scanlines"></div>

    <main class="relative z-10 w-full max-w-3xl px-4 py-8 mx-auto">
        <div class="glass-card rounded-3xl p-6 sm:p-12 text-center relative overflow-hidden">
            
            <!-- Top Bold Animated Gradient Bar -->
            <div class="absolute top-0 left-0 right-0 h-2 bg-gradient-to-r from-red-600 via-rose-500 to-red-600"></div>

            <!-- Organization Badge -->
            <div class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-red-950/80 border border-red-500/40 text-red-300 text-xs sm:text-sm font-bold mb-6 uppercase tracking-wider">
                <span class="w-2.5 h-2.5 rounded-full bg-red-500 animate-ping"></span>
                <span>TIZIM TO'LIQ QULFLANGAN</span>
            </div>

            <!-- Glowing Lock Icon -->
            <div class="flex justify-center mb-6">
                <div class="lock-icon-container">
                    <div class="lock-ring"></div>
                    <i class="fa-solid fa-lock text-5xl text-red-500 drop-shadow-[0_0_15px_rgba(239,68,68,0.9)]"></i>
                </div>
            </div>

            <!-- Main Big & Strict Notice -->
            <h1 class="text-3xl sm:text-4xl md:text-5xl font-black text-red-500 tracking-tight leading-tight mb-5 glow-title uppercase">
                Avval dasturni pulini to'lang!!!
            </h1>

            <p class="text-slate-200 text-base sm:text-lg leading-relaxed max-w-xl mx-auto mb-8 font-medium">
                Dasturiy ta'minot, AI klinik bemor moduli va telemetriya monitoring tizimidan foydalanish to'xtatildi. Dasturdan foydalanish uchun dasturchi bilan to'lov hisob-kitobini to'liq bajaring!
            </p>

            <!-- Information Details Inset -->
            <div class="glass-inset rounded-2xl p-5 sm:p-6 text-left mb-6 space-y-3.5">
                <div class="flex items-center justify-between text-xs sm:text-sm py-1.5 border-b border-slate-800">
                    <span class="text-slate-400 flex items-center gap-2">
                        <i class="fa-solid fa-triangle-exclamation text-red-400"></i> Xavfsizlik talabi:
                    </span>
                    <span class="font-extrabold text-red-400 uppercase tracking-wide">To'lov qilinmagan</span>
                </div>
                <div class="flex items-center justify-between text-xs sm:text-sm py-1.5 border-b border-slate-800">
                    <span class="text-slate-400 flex items-center gap-2">
                        <i class="fa-solid fa-ban text-red-400"></i> Tizim holati:
                    </span>
                    <span class="font-bold text-red-300">Bloklangan (403 Forbidden)</span>
                </div>
                <div class="flex items-center justify-between text-xs sm:text-sm py-1.5 border-b border-slate-800">
                    <span class="text-slate-400 flex items-center gap-2">
                        <i class="fa-solid fa-fingerprint text-slate-400"></i> Tizim ID:
                    </span>
                    <span class="mono font-bold text-slate-200">MED-SIM-UZ-7704</span>
                </div>
                <div class="flex items-center justify-between text-xs sm:text-sm py-1.5">
                    <span class="text-slate-400 flex items-center gap-2">
                        <i class="fa-solid fa-user-shield text-emerald-400"></i> Bog'lanish:
                    </span>
                    <span class="font-bold text-emerald-400">Dasturchi / CAIL Lab</span>
                </div>
            </div>

            <!-- Footer -->
            <div class="flex items-center justify-center text-xs text-slate-500 pt-4 border-t border-slate-800/80">
                <div class="flex items-center gap-2 font-medium">
                    <i class="fa-solid fa-shield-halved text-red-500"></i>
                    <span>Mualliflik huquqi va dasturiy ta'minot litsenziyasi bilan himoyalangan &copy; 2026</span>
                </div>
            </div>
        </div>
    </main>

    <script>
        // O'ng tugma va ishlab chiquvchi tugmalari bloklangan
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
                        "code": "PAYMENT_REQUIRED",
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
