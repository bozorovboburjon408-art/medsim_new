@echo off
chcp 65001 >nul
title MedSim Boshqaruv Markazi

echo ===============================================================================
echo          🏥 MEDSIM — HAMSHIRALAR TIBBIY SIMULYATSIYA TIZIMI
echo ===============================================================================
echo.
echo 1/3. Backend server ishga tushirilmoqda (FastAPI + DeepSeek AI)...
pushd "%~dp0backend"
start "MedSim Backend (Port 8000)" cmd /k "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
popd

echo 2/3. Frontend planshet interfeysi ishga tushirilmoqda (Port 3000)...
pushd "%~dp0frontend"
start "MedSim Frontend (Port 3000)" cmd /k "npm run dev"
popd

echo.
echo 3/3. Tizim yuklanmoqda (6 soniya kuting)...
timeout /t 6 /nobreak >nul

echo.
echo ✅ Tizim to'liq ishga tushdi!
echo 🌐 Brauzer ochilmoqda: http://localhost:3000
echo.

start http://localhost:3000

echo ===============================================================================
echo  Tizim faol ishlamoqda.
echo  Agar brauzerda sahifa ochilmasa, klaviaturadan F5 (Sahifani yangilash) ni bosing.
echo ===============================================================================
pause
