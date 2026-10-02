# MedSim

Patronaj hamshiralari uchun AI bemor simulyatori. Hamshira planshetda (Android APK) bemor bilan o'zbek tilida gaplashadi; bemor javobi manikenga qo'yilgan Bluetooth kalonkada eshitiladi.

- `backend/` — FastAPI: stsenariy (`app/scenarios/`), AI (Gemini yoki Claude), TTS (Edge/Azure). `cp .env.example .env`, so'ng `uvicorn app.main:app`.
- `android/` — Kotlin (Compose) ilova: bemor tanlash, mikrofon (uz-UZ STT), kalonka tanlash, chaqaloq yig'lashi (`app/src/main/assets/baby_cry.mp3` qo'yilishi kerak).

Bemorlar: buvi, homilador ayol, 5 yoshli bola, chaqaloq (faqat yig'laydi). Bobo keyin qo'shiladi.
