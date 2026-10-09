Men "MedSim" loyihasi ustida ishlayapman: patronaj hamshiralik talabalari uchun AI bemor simulyatori (Android planshet ilova + Render'dagi FastAPI backend). Talaba o'zbekcha gapiradi, AI bemor o'zbekcha javob beradi, ovoz Bluetooth karnaydan chiqadi. Men o'zbekcha yozaman, sen ham o'zbekcha javob ber. Hech qachon mendan API kalitlarini yuborishni so'rama (ular faqat Render Environment'da turadi).

Hozirgi holat (qisqacha):
- Backend: FastAPI, Render. Matn: Gemini 2.5 (Vertex AI, $300 kredit). Ovoz: ElevenLabs (asosiy, V3 modeli Jasmina uchun, ovoz ID O72h9AUwisM6Zj4He72B), zaxira Edge TTS. Ovozdan matn: hozir Android'ning o'z tanishi; Gemini va ElevenLabs Scribe o'zbekchada zaif chiqdi.
- Bemorlar: Salomat buvi, Nilufar (homilador), Jasmina (5 yoshli qizaloq), Hikmatilla ota (bobo), chaqaloq (AI yo'q, ESP32 datchik).
- Asosiy ochiq muammolar: 1) ovozdan matn sifati (o'zbekcha), 2) javob kechikishi (birinchi tovush ~6 s, nishon 3 s), 3) bemor xulq-atvori (takrorlash, to'qima shikoyat), 4) Android ilovani yangilash, 5) baholash (keyinga qoldirilgan).
- Kodim GitHub'da: bozorovboburjon408-art/medsim_new, branch claude/confident-volta-sfk9ep. To'liq hujjatlar shu repoda: HANDOFF.md (loyiha holati) va PROMPTS.md (AI ko'rsatmalari).

Sen kodni ko'ra olmaysan va o'zgartira olmaysan, shuning uchun menga aniq, nusxalab qo'yiladigan javoblar ber (qaysi faylda nimani o'zgartirish). Men senga fayl matnini yoki xato xabarini tashlayman. Quyida HANDOFF.md matni:

[BU YERGA HANDOFF.md NI TO'LIQ QO'YING]
