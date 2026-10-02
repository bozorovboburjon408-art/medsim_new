@echo off
chcp 65001 >nul
title MedSim Boshqaruv Markazi

echo ===============================================================================
echo          🏥 MEDSIM — HAMSHIRALAR TIBBIY SIMULYATSIYA TIZIMI
echo ===============================================================================
echo.
echo 1. Backend server ishga tushirilmoqda (FastAPI + DeepSeek AI + Edge TTS)...
pushd "%~dp0backend"
start "MedSim Backend (Port 8000)" cmd /k "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
popd

echo 2. Frontend planshet interfeysi ishga tushirilmoqda (Port 3000)...
pushd "%~dp0frontend"
start "MedSim Frontend (Port 3000)" cmd /k "npm run dev -- --host 0.0.0.0 --port 3000"
popd

echo.
echo 3. Tizim tayyorlanmoqda, 3 soniya kuting...
timeout /t 4 /nobreak >nul

echo.
echo ✅ Dastur muvaffaqiyatli ishga tushdi!
echo 🌐 Brauzer ochilmoqda: http://localhost:3000
echo.

start http://localhost:3000

echo ===============================================================================
echo  Tizim faol ishlamoqda. Dasturni to'xtatish uchun ochilgan qora oynalarni yoping.
echo ===============================================================================
pause
