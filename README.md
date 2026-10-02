# 🏥 MedSim — Hamshiralar Tibbiy Simulyatsiya Tizimi

Hamshiralik kasbiy ko'nikmalarini baholash va o'rgatish uchun mo'ljallangan interaktiv tibbiy simulyatsiya va apparat-dasturiy majmuasi.

---

## 🌟 Asosiy Imkoniyatlar

1. **AI Bemorlar (Klinik Case va Dialoglar):**
   * 👵 **Salomat buvi (75 yosh):** 2-tip qandli diabet, diabetik tovon yarasi, arterial gipertenziya parvarishi.
   * 🤰 **Gulnora opa (28 yosh):** 32 haftalik homiladorlik patronaji, surunkali piyelonefrit va 2-darajali anemiya.
   * 👦 **Jasurbek (5 yosh) va onasi Nilufar opa:** Gel'mintoz (enterobioz va askaridoz) shikoyatlari va gigiyenik tavsiyalar.
   * 👶 **Chaqaloq:** Yig'lash va taktil ovuntirish simulyatori.

2. **Ovozli Sintez (Neural TTS):**
   * Microsoft Edge Neural TTS orqali tabiiy va sof o'zbek tili ovozi (`uz-UZ-MadinaNeural` va `uz-UZ-SardorNeural`).

3. **ESP32 Audio & Taktil Maniken:**
   * mDNS qo'llab-quvvatlash: `http://medsim-speaker.local` (IP qidirish shart emas).
   * To'g'ridan-to'g'ri HTTP Push (`POST /play`) audio uzatish.
   * MPU-6050 (GY-521) sensori orqali chaqaloqni mayin tebratib ovuntirishni avtomatik aniqlash.

---

## 📂 Loyiha Tuzilishi

* **`frontend/`** — React 19 + Tailwind CSS planshet interfeysi.
* **`backend/`** — FastAPI + DeepSeek AI + Edge TTS + SQLAlchemy backend.
* **`ESP32_Audio_Speaker/`** — Universal ESP32 Audio Kalonka firmware (`ESP32_Audio_Speaker.ino`).
* **`ESP32_Chaqaloq_Baby/`** — Chaqaloq manikeni firmware (`ESP32_Chaqaloq_Baby.ino`).
* **`QOLLANMA_ISHLATISH_YORIQNOMASI.txt`** — Foydalanish bo'yicha to'liq qo'llanma.

---

## 🚀 Ishga Tushirish

### Frontend & Backend:
* Backend: `http://localhost:8000` (yoki Render live)
* Frontend: `http://localhost:3000` (yoki Render live)

### ESP32 Ulanishi:
* `GPIO 25/26` ➡️ PAM8403 Ovoz kirishi
* `GPIO 21/22` ➡️ MPU-6050 I2C (SDA/SCL)
* Brauzerdan kirish: `http://medsim-speaker.local`
