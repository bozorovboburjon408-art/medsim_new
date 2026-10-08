# MedSim — qilinadigan ishlar ro'yxati

Avval `HANDOFF.md` va `AGENTS.md` ni o'qing. Foydalanuvchi bilan o'zbekcha gaplashing. API kalitlarini hech qachon so'ramang (faqat Render → Environment). Faqat `claude/confident-volta-sfk9ep` branchiga push qiling, PR ochmang. Baholash (evaluation) hozircha KERAK EMAS.

## 1. Ovozdan matn (STT), eng muhim muammo
- [ ] Foydalanuvchi `/stt_lab?token=...` da Gemini / ElevenLabs Scribe / Chrome (Google) natijalarini solishtiradi. Natijaga qarab tanlang.
- [ ] Ehtimoliy yechim: Android'ning o'z `SpeechRecognizer` (uz-UZ), yoki Google Cloud Speech-to-Text (Chirp, phrase hints; API yoqish + "Cloud Speech Client" roli kerak), yoki o'zbek mutaxassislari (UzbekVoice, Muxlisa).
- [ ] Tanlangan STT ni Android ilovaga ulash.

## 2. Kechikish (latency)
- [ ] Maqsad: birinchi tovush ≈3 s. Oxirgi o'lchov 6.1 s edi (STT 2.8 s + ElevenLabs v3 har gap 2–6 s).
- [ ] Streaming + qisqa birinchi gap deploy qilingan, lekin o'lchanmagan. `/full_lab` da o'lchang.
- [ ] Agar v3 sekin bo'lsa: Madinaxon uchun `eleven_multilingual_v2` bilan solishtiring. Boshqa bemorlar uchun ham v3 kerakmi, foydalanuvchidan so'rang (javobsiz qolgan).

## 3. Bemor xulq-atvorini tekshirish
- [ ] `/self_test` bilan yangi qoidalarni tekshiring: javob uzunligi savolga mos, ssenariyga sodiqlik va unga qaytish, o'ylab topilgan shikoyat yo'q, takror yo'q, tushunmasa "Nima dedingiz? Tushunmadim".
- [ ] Madinaxon: "yig'layman" so'zi o'rniga haqiqiy yig'i tovushi (`[sobbing]`/`[crying]`), talaffuz va tezlik, ovoz tembri (`eleven_tempo`, `eleven_stability`, pitch). Foydalanuvchi 1x tezlikni xohlaydi, lekin yosh bolaga o'xshashi kerak.
- [ ] Ba'zi so'zlar noto'g'ri chiqyapti (masalan "qichiyapti"), ro'yxatini yig'ib to'g'irlang.

## 4. Madinaxon ssenariysi
- [ ] Foydalanuvchi yangi matnni keyin yuklaydi. Shunda `backend/app/scenarios/bola.txt` ni almashtiring va `patients.py` dagi `name_swap` (Jasurbek→Madinaxon) ni olib tashlang.
- [ ] Ovoz qotirilgan: ElevenLabs id `O72h9AUwisM6Zj4He72B`, model V3.

## 5. Android ilova
- [ ] GitHub Actions (`.github/workflows/android.yml`) oxirgi merge'dan keyin muvaffaqiyatli quryaptimi, tekshiring. Artifact: `1-tayyor-demo`.
- [ ] Yangi STT tanlovini qo'shing (1-bo'lim).
- [ ] Chaqaloq (ESP32-C6, yig'i/kulgi, tebratish sensori) bilan bog'liq Antigravity ishiga TEGMANG.
- [ ] APK ni planshetga o'rnatish (foydalanuvchi to'liq sinovdan keyin).

## 6. Keyinga qoldirilgan
- [ ] Baholash (`evaluator.py`) sozlash.
- [ ] UI dizayn yangilash, ssenariylarni qisqartirish.
- [ ] Render env tozalash (keraksiz o'zgaruvchilar).
- [ ] Edge fallback sozlash.
- [ ] `PROMPTS.md` ni yangilash (ba'zi qismlari eskirgan).

## 7. Ish tartibi bo'yicha eslatmalar
- Python o'zgartirsangiz: toza venv'da `pip install -r backend/requirements.txt` bilan tekshiring.
- Lab sahifalari JS'ini jsdom yoki brauzerda ishga tushirib tekshiring.
- Render: https://medsim-backend-oyfd.onrender.com, lab sahifalari `?token=` bilan (DEBUG_TOKEN Render'da).
- Antigravity bir xil branchga push qilsa: `git merge -s ours origin/<branch>`, o'zingizning versiyangizni saqlang.
- Commit oxiriga attribution qatorlarini qo'shing, repo ichida model nomini yozmang.
