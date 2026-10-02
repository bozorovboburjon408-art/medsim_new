# 🎵 ESP32 Smart Wi-Fi Audio Kalonka Tizimi

Smartfon va noutbukdagi jonli audio signallarni (AI agentlar, musiqa, video) Wi-Fi orqali kechikishlarsiz ESP32 kalonkasiga uzatuvchi to'liq tizim.

---

## 📦 To'plam Tarkibi

| Fayl | Tavsif |
|---|---|
| `AISpeakerHub.apk` | Smartfonlar uchun Android ilovasi (Live Stream, Ekvalayzer, Ko'p kalonkali boshqaruv) |
| `ESP32_Audio_Speaker.ino` | ESP32 uchun to'liq Arduino dasturi (Internal DAC, DSP Bass/Treble, Web Server) |
| `QOLLANMA_ISHLATISH_YORIQNOMASI.txt` | Bosqichma-bosqich to'liq o'zbekcha qo'llanma |

---

## ⚡ Tezkor Boshlash

1. **Ulash sxemasi:**
   - ESP32 `GPIO 25` ➡️ PAM8403 `L_IN`
   - ESP32 `GPIO 26` ➡️ PAM8403 `R_IN`
   - ESP32 `GND` ➡️ PAM8403 `GND`
   - ESP32 `5V / VIN` ➡️ PAM8403 `+5V`

2. **ESP32 dasturini yuklash:**
   - Arduino IDE da `ESP8266Audio` kutubxonasini o'rnating.
   - `ESP32_Audio_Speaker.ino` faylida Wi-Fi nom va parolingizni kiriting.
   - ESP32 ga yuklang va Serial Monitorda uning IP manzilini ko'ring.

3. **Smartfonda ishlatish:**
   - `AISpeakerHub.apk` ni smartfonga o'rnating va oching.
   - **`Boshlash`** tugmasini bosing.
   - Kalonkangiz yonidagi **`📡 Ushbu Kalonkani Telefonga Bog'lash`** tugmasini bosing.
   - Ovoz, Bass va Treble slayderlarini o'zingizga moslang!

---
*Barcha savollar va to'liq yo'riqnoma uchun `QOLLANMA_ISHLATISH_YORIQNOMASI.txt` faylini o'qing.*
