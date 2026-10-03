# MedSim — agent uchun yo'riqnoma (Antigravity / Gemini CLI / Claude Code / boshqa agentlar)

Avval `HANDOFF.md` ni to'liq o'qing: loyiha holati, arxitektura, qaror va muammolar shu yerda.

## Qoidalar
- Foydalanuvchi bilan **o'zbek tilida** gaplashing.
- **API kalitlarini** hech qachon chatga/gitga yozmang va foydalanuvchidan so'ramang. Kalit faqat Render → Environment da (`GEMINI_API_KEY`).
- Branch: `claude/confident-volta-sfk9ep` (Render shu branchdan avtomatik deploy qiladi). Boshqa branchga push qilmang.
- Python o'zgartirsangiz: toza venv da `pip install -r backend/requirements.txt` bilan tekshiring (httpx versiyasi to'qnashuvi bir marta deployni buzgan).
- `backend/app/live.py` ichidagi LAB_HTML (JS) ni o'zgartirsangiz, jsdom yoki brauzerda ishga tushirib tekshiring (qo'shtirnoq xatosi sahifani buzgan).
- Bemor javoblari: sof o'zbek, 1–2 qisqa gap. Production ovozi faqat Edge TTS; Gemini faqat matn (LLM) uchun.
- Android APK ni GitHub Actions (`.github/workflows/android.yml`) quradi; artifact nomi `1-tayyor-demo`.
