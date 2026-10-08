# MedSim — loyiha topshiriq hujjati

## 1. Maqsad
Patronaj hamshiralik talabalari uchun **AI bemor simulyatori**. Talaba (hamshira) o'zbek tilida gapiradi, AI bemor o'zbek tilida javob beradi. Bemor ovozi har bir manekendagi **Bluetooth karnaydan** chiqadi. Mijoz: planshetdagi **native Android (Kotlin) APK**; backend Render'da. ESP32/WiFi modullar endi yo'q.

Bemorlar (`backend/app/patients.py`, ssenariylar `backend/app/scenarios/*.txt`):
- `buvi` — Salomat buvi, 75, qandli diabet (faqat buvi gapiradi)
- `homilador` — Nilufar, 32 haftalik homilador
- `bola` — Jasurbek, 5 yoshli o'g'il bola (o'zi gapiradi; gelmintoz)
- `chaqaloq` — AI yo'q: yig'laydi (assets/baby_cry.mp3), planshetni beshikdek tebratsa (akselerometr) tinchlanadi
- `bobo` — Hikmatilla ota, 78 yosh, yoshga doir skrining (ssenariy qo'shildi; faqat o'zi gapiradi, Edge Sardor ovozi)

## 2. Arxitektura (production)
```
Android: SpeechRecognizer(uz-UZ) -> matn
  -> POST /chat_stream (NDJSON, har gap bo'yicha)
Backend: Gemini (REST streamGenerateContent) gaplarga bo'lib -> Edge TTS (mp3) har gap -> oqim
Android: mp3 navbati MediaPlayer bilan Bluetooth karnayga
```
- Birinchi ovozgacha ~2–2.5 s.
- `/evaluate`: hamshirani baholash (5 mezon × 20 ball) — `evaluator.py`.
- Backend: FastAPI, Docker, Render Starter ($7, uxlamaydi). URL: https://medsim-backend-oyfd.onrender.com . `render.yaml` Blueprint.
- Render **env o'zgaruvchilari kod default'laridan ustun** (GEMINI_MODELS, TTS_PROVIDER...).
- Gemini modellari: `GEMINI_MODELS=gemini-3.5-flash-lite,gemini-3.1-flash-lite` (thinkingLevel=low, sekin/xato modelga circuit-breaker), baholash: `GEMINI_EVAL_MODELS`.
- Ovoz: Gemini TTS asosiy (`gemini-2.5-flash-preview-tts,gemini-3.1-flash-tts-preview`; temperature: 0.0 bilan barqarorlashtirilgan; WAV 24kHz), xatolik yoki limit bo'lsa zaxira Edge TTS (`uz-UZ-MadinaNeural/SardorNeural`) ga avto o'tadi. Azure ixtiyoriy (`TTS_PROVIDER=azure`).

Fayllar: `backend/app/{main,llm,tts,patients,evaluator,config,live}.py`; Android: `android/app/src/main/java/uz/medsim/{Api,Speaker,MainActivity,Theme}.kt`.
Maxfiy sahifalar `?token=` (env `DEBUG_TOKEN`, hozir `sinov7421`): `/voice_lab` (Edge ovoz sozlash), `/live_lab` (Gemini Live tajriba), `/models`, `/health`.

## 3. Hozirgi tajriba: Gemini Live (`backend/app/live.py`)
Maqsad: ovozdan-ovozga modelga (gemini-3.8-live) to'liq o'tish mumkinmi, aniqlash. Hozir faqat **lab** (`/live_lab`), production'ga ulanmagan. WebSocket proxy `/live_ws`: brauzer 16 kHz PCM yuboradi, 24 kHz PCM javob qaytadi; transkriptlar va token hisobi ko'rsatiladi.

Natijalar:
- Birinchi ovoz ~0.5–1.2 s (juda tez), o'zbekcha ovozli javob chiqadi.
- Muammolar: (a) o'zbek tilini tanish sifati past (transkriptsiya tasodifiy tillarga ketadi; `language_codes=["uz-UZ"]` + lug'at qo'shildi, natijasi hali to'liq tekshirilmagan); (b) suhbat davomida **ovoz o'zgarib ketadi** (buvi -> erkak) — kontekst siqish o'chirildi va promptga qoida qo'shildi, tekshirilmagan; (c) bemor o'zini boshqa rol deb o'ylashi (Jasurbek o'zini buvi deb) — prompt boshiga `IDENT` qo'shildi, tekshirilmagan; (d) bola uchun Gemini'da bola ovozi yo'q (hozir Puck); (e) har gapda butun prompt (~4.4K token) qayta hisoblanadi, ~5–6K token/tur.
- **Qaror mezoni:** Live mikrofon bilan o'zbekchani yaxshi tushunsa va ovoz barqaror bo'lsa — Android'ni Live'ga ko'chirish (katta ish: mikrofon oqimi WebSocket orqali, bosib-gapirish tugmasi (echo uchun), baholash uchun transkript). Aks holda — hozirgi tizim (Android STT + Flash-Lite + Edge) da qolish.

## 4. Ochiq vazifalar
1. `/live_lab` ni haqiqiy mikrofon bilan sinash (agent buni qila olmagan; foydalanuvchi sinab natija beradi) va yuqoridagi (a)(b)(c) ni yopish yoki Live'dan voz kechish.
3. Edge ovozlarni `/voice_lab` da sozlash (foydalanuvchi qiymat beradi).
4. UI qayta dizayni (foydalanuvchi generatsiya qilgan mockup/portretlarni beradi).
5. Ssenariy promptlarini qisqartirish (~10K belgi; hamshiraga tavsiyalar qismi bemorga kerak emas) — token tejash.
6. Render env tozalash: eski `TTS_PROVIDER`, `GEMINI_TTS_*`, `VOICELAB_*`.
7. Keyinroq: chaqaloq uchun haqiqiy harakat datchigi.

## 5. Ishga tushirish
Backend: `cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && cp .env.example .env` (kalitni .env ga) `&& uvicorn app.main:app --reload`.
Android: GitHub Actions `android.yml` debug APK quradi (artifact `1-tayyor-demo`) yoki Android Studio'da `android/` ochiladi (minSdk 28, landscape). Ilova sozlamalarida server URL: Render manzili.

## 6. Tajribadan saboqlar
- Gemini TTS qimmat va beqaror edi; past temperature/seed ovozni cho'zib yubordi.
- Edge TTS Render'dan 403 berdi -> `edge-tts>=7.2.8`.
- Bepul Render uxlaydi (30–50 s) -> Starter + ilova `/health` ping.
- Foydalanuvchi AI'ning tezligiga (2–3 s), bir xil premium ovozga va arzonlikka e'tibor beradi; taqdimot (demo) ishonchliligi muhim.
