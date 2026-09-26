# MedSim - Hamshiralik Simulyatsiyasi Tizimi

Loyiha hamshiralarni o'qitish va simulyatsiya qilish uchun mo'ljallangan. Tizim maxsus jihozlangan manekenlar (ESP32 orqali boshqariladi) va boshqaruv panelini (veb-ilovalar) o'z ichiga oladi.

## Arxitektura

- **ESP32 Firmware**: Maneken ichidagi audio qabul qiluvchi va sensorlarni boshqaruvchi mikrokontroller.
- **Backend**: Python FastAPI orqali ishlaydigan RESTful API.
- **Frontend**: Node.js / React (yoki boshqa freymvork) asosidagi foydalanuvchi interfeysi.
- **Database**: PostgreSQL 16 ma'lumotlar bazasi.

## Talablar

- Docker va Docker Compose
- Node.js 20+
- Python 3.12+
- PlatformIO (ESP32 dastrurini yozish uchun)

## O'rnatish (Docker orqali)

1. Loyihani yuklab oling.
2. Root papkada `.env` faylini yarating va kerakli muhit o'zgaruvchilarini sozlang:
   ```env
   POSTGRES_USER=medsim
   POSTGRES_PASSWORD=medsim123
   POSTGRES_DB=medsim_db
   ```
3. Docker Compose orqali barcha xizmatlarni ishga tushiring:
   ```bash
   docker-compose up --build
   ```

## ESP32 Dasturini Yozish

1. `esp32/audio_receiver/config.h` faylida Wi-Fi va boshqa sozlamalarni o'zgartiring.
2. PlatformIO yordamida loyihani oching.
3. ESP32 modulini kompyuterga ulang.
4. "Upload" tugmasini bosib dasturni mikrokontrollerga yuklang.

## API Endpoints (ESP32)

- `GET /health` - Qurilma holati va ma'lumotlarini qaytaradi.
- `POST /play` - Audio ma'lumotlarni qabul qilib, o'ynashni boshlaydi.
- `POST /stop` - Audioni to'xtatadi.
- `GET /volume?level=50` - Ovoz balandligini o'zgartiradi (0-100).

## Hissa Qo'shish

Loyiha bo'yicha takliflar yoki xatolar haqida xabar berish uchun Issue yarating yoki Pull Request jo'nating.
