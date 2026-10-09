# MedSim: loyiha holati (to'liq topshiriq hujjati)

## 1. Loyiha nima
Patronaj hamshiralik talabalari uchun **AI bemor simulyatori**. Talaba (hamshira) planshetdagi Android ilovada o'zbekcha gapiradi, AI bemor o'zbekcha javob beradi va ovozi har maniken ichidagi Bluetooth karnaydan chiqadi.

Bemorlar (`backend/app/patients.py`, ssenariylar `backend/app/scenarios/*.txt`):
| id | Kim | Izoh |
|---|---|---|
| `buvi` | Salomat buvi, 75, qandli diabet | faqat o'zi gapiradi |
| `homilador` | Nilufar, 32 haftalik homilador | |
| `bola` | **Jasmina**, 5 yoshli QIZALOQ, gijja | ssenariy: foydalanuvchi bergan "5 yoshli qiz bola" hujjati (ism: Jasmina Rahimova) |
| `bobo` | Hikmatilla ota, 78, skrining | quloqlari og'ir |
| `chaqaloq` | AI yo'q | yig'laydi/kuladi (mp3), ESP32-C6 maniken datchigi yoki planshet akselerometri bilan tinchlanadi |

Oila (`patients.py` FAMILY_COMMON): hamma bemor bitta oila. Hikmatilla ota (78) va Salomat buvi (75) er-xotin; o'g'li Asilbek (35) Rossiyada (Moskvada) ishlaydi; uning rafiqasi Nilufar (33, 32 haftalik homilador) ularning kelini; qizi Jasmina (5) ularning nevarasi. Har bemorning promptida shu oila va o'z munosabatlari bor.

## 2. Arxitektura
```
Android (Kotlin, Compose): ovozdan matn (hozir Android SpeechRecognizer uz-UZ)
  -> POST /chat_stream (NDJSON, gap-gapma)
Backend (FastAPI, Docker, Render Starter, https://medsim-backend-oyfd.onrender.com):
  Gemini (Vertex AI, $300 kredit) gaplarga bo'lib -> ElevenLabs ovozi (oqim, PCM) har gap parallel
Android: PCM/mp3 bo'laklarini Bluetooth karnayga chaladi (AudioTrack)
```
- Branch: `claude/confident-volta-sfk9ep` (Render shu branchdan avtomatik deploy qiladi). Repo: github.com/bozorovboburjon408-art/medsim_new.
- Matn modeli: Vertex AI orqali Gemini (`gemini-2.5-flash-lite`, `gemini-2.5-flash`), `backend/app/llm.py`, `vertex.py`. Kalit: Render'da `GOOGLE_SA_JSON` (service account `medsim-llm`, rol "Agent Platform User"). Tekshiruv: `/llm_check?token=...`.
- Ovoz: **ElevenLabs asosiy** (`CHAT_TTS=eleven`, `ELEVENLABS_API_KEY`). Xato yoki 8 s kechiksa shu gap Edge TTS'da. Zaxira/variantlar: Gemini ovozi (`tts="gemini"`), Edge (`tts="edge_only"`).
- Ovozlar (`backend/app/eleven.py`): buvi 6Fkh9WgMXOqBcOWxX91f, bobo xDwfBjUEPdIoQekNOXAX, homilador 132QLQIkg1RJGmpicuhR (model `eleven_multilingual_v2`); **Jasmina O72h9AUwisM6Zj4He72B, model `eleven_v3`**, gapirish tezligi 0.85 (ElevenLabs sozlamasi), balandlik koeffitsiyenti 1.0 (`eleven_speed`), ifodalilik 0.5. V3 da `[crying]`/`[sobbing]` belgilari yig'lash tovushini beradi; belgilar ekranda ko'rinmaydi, `eleven.prepare/strip_tags/crying_fix`.
- Eski Android ilova `tts="edge"` yuboradi: server uni standartga (ElevenLabs) tenglashtiradi, shuning uchun APK yangilamasdan ham ElevenLabs ishlaydi.
- Ovozdan matn (STT) variantlari (hammasi o'zbekchada **zaif**, asosiy muammo): Gemini (`/transcribe`), ElevenLabs Scribe (`/transcribe?engine=eleven`), Chrome/Google uz-UZ (brauzerda). Android'ning o'z tanishi eng yaxshisi bo'lishi mumkin: solishtirilmoqda.
- Baholash (`/evaluate`, `evaluator.py`, 5 mezon x 20 ball): **hozircha sozlanmaydi**, keyin qaytiladi.

## 3. Render muhit o'zgaruvchilari (qiymatlar faqat Render'da, hech qachon chatga/gitga yozilmaydi)
`DEBUG_TOKEN` (sinov sahifalari uchun, hozir `sinov7421`), `GOOGLE_SA_JSON`, `ELEVENLABS_API_KEY`. Ixtiyoriy: `CHAT_TTS` (eleven|gemini|edge_only), `VERTEX_MODELS`, `STT_MODELS`. Render env kod standartlaridan ustun.

## 4. Sinov sahifalari (hammasi `?token=<DEBUG_TOKEN>`)
- `/full_lab`: mikrofon -> ovozdan matn -> Gemini javob -> ovoz (to'liq zanjir, vaqtlar ko'rsatiladi; STT/TTS/chizg'ichlar tanlanadi).
- `/voice_lab`: ovozlarni yonma-yon eshitish (Edge/Gemini/ElevenLabs), ElevenLabs kutubxonasidan ovoz qidirish.
- `/stt_lab`: Gemini, Scribe va Chrome tanishini yonma-yon solishtirish.
- `/self_test?patient=all|bola|...`: 10 savollik ssenariyli suhbat (matn) + avtomatik belgilar (takror, uzun, "yig'lay" so'zi, to'qima a'zo).
- `/stt_selftest`: ElevenLabs bilan aytdirilgan gaplarda Gemini va Scribe so'z xatosi.
- `/llm_check`, `/health` (deploy commit), `/models`.

## 5. Android ilova
`android/app/src/main/java/uz/medsim/` (Api.kt, Speaker.kt, MainActivity.kt, Theme.kt). Bemor kartalari, mikrofon tugmasi, server holati, chaqaloq ekrani (ESP32 manikeni `esp32/` papkasi + planshet akselerometri zaxira, kulgi/yig'i ovozlari), sozlamalar. APK'ni GitHub Actions quradi (`.github/workflows/android.yml`), artifact nomi `1-tayyor-demo`. **Android hali yangilanmagan**: ilova eski STT (Android) va server standartiga tayanadi; ElevenLabs PCM oqimini (`pcm_b64`, `rate`, bo'sh matnli bo'laklar) qabul qila oladi.

## 6. Ochiq vazifalar (muhimlik tartibida)
1. **Ovozdan matn sifati**: `/stt_lab` da Gemini/Scribe/Chrome solishtirish natijasi kutilmoqda. Chrome/Google yaxshi bo'lsa, Android'ning o'z tanishi qoladi. Aks holda: Google Cloud Speech-to-Text (Chirp, so'z maslahatlari bilan) yoki o'zbek ixtisoslashgan xizmat (UzbekVoice, Muxlisa).
2. **Kechikish**: oxirgi o'lchov birinchi tovush ~6 s edi (STT 2.8 s + V3 ovoz). Oqimli ovoz va qisqa birinchi gap qo'shildi, natija tekshirilmagan. V3 sekin bo'lsa Jasmina uchun `eleven_multilingual_v2` (yig'lash belgisiz).
3. **Bemor xulq-atvori**: javob uzunligi savolga qarab, ssenariyga sodiqlik, takrorlamaslik, tushunarsizga "Nima dedingiz?", Jasmina shikoyatlari qat'iy. Yaqinda o'zgargan, `/self_test` bilan tekshirish kerak.
4. **Android ilovani yangilash**: ElevenLabs ovozi (ishlaydi), tanlangan STT, bola kartasi (Jasmina, qiz), chaqaloq qismi (allaqachon bor). Keyin APK qurish.
5. (Bajarildi) Qiz bola ssenariysi yangilandi: ism Jasmina, `name_swap` olib tashlandi.
6. Edge ovozlarini sozlash (zaxira), UI qayta dizayn (foydalanuvchi mockup beradi), ssenariylarni qisqartirish (token tejash), baholashni qaytib sozlash.

## 7. Muhim qarorlar va saboqlar
- Gemini TTS (Vertex) qimmat va beqaror edi, uslub ko'rsatmasini ovoz chiqarib o'qib yuboradi, ba'zan 20 s kechikadi (shuning uchun qayta yuborish/Edge zaxirasi). Google Cloud TTS o'zbekchani qo'llamaydi.
- Gemini'da haqiqiy bola ovozi yo'q. ElevenLabs'da Jasmina uchun ovoz topildi (O72h9...). Voyaga yetmagan haqiqiy ovozni klonlash faqat vasiyning yozma roziligi bilan.
- Matn tanish promptiga so'zlar ro'yxati qo'shish xato: model uni gapingiz deb yozib yuboradi.
- Mikrofon: gap boshi kesilmasligi uchun doimiy oqim + 0.7 s oldingi yozuv + 0.35 s dum; to'xtatish ikki marta ishga tushmasligi uchun `stopping` bayrog'i.
- Antigravity (boshqa agent) shu branchga yuborgan ishlar `merge -s ours` bilan bekor qilingan (tarixda saqlanadi); faqat chaqaloq/ESP32/kulgi ishlari qaytarildi. Boshqa agent bilan bir branchda ishlamang.
- Qoidalar: foydalanuvchi bilan o'zbekcha; API kalitlarini hech qachon chatga/gitga yozmang va so'ramang (faqat Render Environment); yangi Python bog'liqliklari toza venv'da tekshirilsin; lab sahifalari JS'ini jsdom/brauzerda tekshiring.

## 8. Qanday davom etiladi
- Kodni o'zgartirish: Claude Code (yangi, qisqa sessiya shu hujjat bilan) yoki GitHub'da qo'lda. Oddiy chat kodni ko'rmaydi va o'zgartirmaydi: undan maslahat/kod parchasi olib, qo'lda qo'yish kerak.
- Barcha AI ko'rsatmalari (promptlar) alohida: `PROMPTS.md`.
