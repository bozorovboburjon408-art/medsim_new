@echo off
chcp 65001 >nul
title MedSim — Hamshiralar Tibbiy Simulyatsiya Tizimi

echo ===============================================================================
echo          🏥 MEDSIM — HAMSHIRALAR TIBBIY SIMULYATSIYA TIZIMI
echo ===============================================================================
echo.
echo 1. Backend server ishga tushirilmoqda (FastAPI + DeepSeek AI + TTS)...
start /b cmd /c "cd /d "%~dp0backend" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"

echo 2. Frontend planshet interfeysi ishga tushirilmoqda (React 19)...
start /b cmd /c "cd /d "%~dp0frontend" && npm run dev -- --host 0.0.0.0 --port 3000"

echo.
echo 3. Tizim tayyorlanmoqda, iltimos 3 soniya kuting...
timeout /t 3 /nobreak >nul

echo.
echo ✅ Tizim to'liq ishga tushdi!
echo 🌐 Brauzer ochilmoqda: http://localhost:3000
echo.
echo 👵 Salomat buvi (75 yosh) | 🤰 Gulnora opa | 👦 Jasurbek | 👶 Chaqaloq
echo 🔊 Barcha 4 ta ESP32 kalonkalari lokal Wi-Fi tarmog'ida to'g'ridan-to'g'ri ishlaydi!
echo ===============================================================================

start http://localhost:3000

echo.
echo Dasturni to'xtatish uchun ushbu oynani yoping.
pause >nul
