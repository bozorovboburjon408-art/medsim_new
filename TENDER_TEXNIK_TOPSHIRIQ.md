# 📑 TEXNIK TOPSHIRIQ VA LOYIHA TAVSIFI
**Loyiha kodi / Shifri:** `MEDSIM-AIOT-2026`  
**Loyiha to'liq nomi:** *"Tibbiyot xodimlarining amaliy, diagnostik va muloqot ko'nikmalarini baholovchi ko'p agentli kiber-fizik simulyatsiya platformasi va apparat-dasturiy majmuasini ishlab chiqish"*

---

## 1. LOYIHANING UMUMIY KONSEPSIYASI VA MAQSADI
Ushbu loyiha patronaj hamshiralari va tibbiyot xodimlarining klinik-muloqot kompetensiyalarini baholash va oshirishga qaratilgan **Kiber-Fizik Simulyatsiya Majmuasi (Cyber-Physical Simulation Complex)** hisoblanadi. 

Tizim oddiy dasturiy ta'minot emas, balki **apparat qismi (Embedded IoT SoC), neyrotarmoqli nutqni tanish va sintezlash (NLU/STT/TTS), Deterministik AI Guardrails xavfsizlik arxitekturasi hamda reaktiv planshet boshqaruv tizimining** uzviy va yuqori darajadagi gibrid integratsiyasidan iborat.

---

## 2. APPARAT VA EMBEDDED IOT QATLAMIGA QO'YILADIGAN QAT'IY TALABLAR (HARDWARE)

Ijrochi har bir antropomorfik maniken (4 ta mustaqil biologik yosh guruhi) ichiga integratsiya qilinadigan apparat mikrotizimlarini ishlab chiqishi shart:

1. **Hisoblash yadrosi va SoC arxitekturasi:**
   - Har bir maniken mustaqil 32-bitli ikki yadroli **Xtensa® Dual-Core LX6 (kamida 240 MHz)** mikroprotsessorli IoT moduli (ESP32 SoC) bilan jihozlanishi shart.
   - Apparat darajasida **FreeRTOS** real-vaqt operatsion tizimi boshqaruvida ko'p oqimli (multi-threading) audio buferlash va tarmoq stekini boshqarish.

2. **Raqamli Audio Trakti va Dinamik drayver:**
   - Ovoz uzatishda shovqinsiz raqamli **I2S (Inter-IC Sound)** protokoli qo'llanilishi shart (oddiy analog PWM yoki Bluetooth qat'iyan man etiladi).
   - Raqamli signalni tovushga aylantirish uchun apparatli **DMA (Direct Memory Access)** buferi bilan ishlovchi tashqi DAC (Digital-to-Analog Converter) drayveri integratsiya qilinishi lozim.
   - Ovoz chastotasi: 16 kHz, 16-bit Mono PCM uzatish.

3. **Deterministik Wi-Fi Routing va Manzillash:**
   - Har bir maniken lokal IEEE 802.11 b/g/n tarmog'ida individual statik IP (yoki qat'iy DHCP reservation) bilan ajratilishi shart.
   - Audio paketlarni sub-sekundlik (jitter < 50ms) kechikish bilan qabul qiluvchi o'rnatilgan HTTP/UDP audio-streaming server ta'minlanishi zarur.
   - Avtomatik **Hardware Watchdog** va aloqa uzilganda o'z-o'zini tiklash (Auto-Reconnection) mexanizmi bo'lishi shart.

---

## 3. SUN'IY INTELLEKT, NLU VA GUARDRAILS QATLAMIGA TALABLAR

Tizimda erkin chat-botlardan foydalanish taqiqlanadi. AI qat'iy tibbiy ssenariylar va rolli cheklovlar doirasida ishlashi shart:

1. **O'zbek Tili Akustik STT (Speech-to-Text) Modeli:**
   - Hamshiraning og'zaki nutqini real vaqt rejimida o'zbek tilidagi tibbiy va xalqona so'zlashuv kontekstida matnga aylantirish (aniqlik darajasi WER < 12%).
   - Fonetik shovqinlarni filtrlash va nol-kechikishli audio oqimini qabul qilish.

2. **Deterministik Chekli Avtomat (DFA) va Skriptli Moslashuv:**
   - Baza darajasida belgilangan klinik ssenariylar bo'yicha Regex-shablonlar va ko'p bosqichli kalit so'zlar klasteri (Priority-based keyword matching) orqali avtomatik javob tanlash mexanizmi.

3. **Multi-Layered AI Guardrails (Xavfsizlik va Cheklov Qatlami):**
   - **4 qatlamli dinamik prompt inyeksiyasi:** Baza qoidalari -> Maniken klinik shaxsiyati -> Ssenariy konteksti -> Klinik tavsiyalar.
   - **Gallyutsinatsiya va fosh bo'lishni bloklash:** AI hech qachon o'zining model, robot yoki dastur ekanligini oshkor qilmasligi, mavzudan tashqari (siyosiy, umumiy, noadekvat) savollarga avtomatik ravishda qahramonning xarakteriga mos rad javobini qaytarishi (`Strict Content Policy`).
   - **Klinik noaniqlik cheklovi:** Bemor (maniken) shifokor nomidan gapirmaydi, tashxis qo'ymaydi — faqat sub'yektiv simptomlar haqida axborot beradi.

4. **Emotsional va Formantli Ovoz Sintezi (TTS):**
   - Har bir qahramon uchun alohida ovoz parametrlari (tembr, pitch, speed, intonatsiya) generatsiyasi:
     - *Bobo:* Past chastotali, sekin, charchoq va hansirash formantlari bilan.
     - *Homilador ayol:* O'rta balandlikda, xavotirli va emotsional intonatsiya.
     - *Bola:* Yuqori chastotali, ingichka, bolalarcha va qo'rquv intonatsiyasi.
   - *Neonatal (Chaqaloq) moduli:* TTS ishlatilmaydi; vaziyatga qarab (yig'lash, asfiksiya, intoksikatsiya nolasi, kulish) to'g'ridan-to'g'ri MP3/WAV DMA oqimi orqali ishga tushiriladi.

---

## 4. DASTURIY TA'MINOT VA ARXITEKTURA TALABLARI

1. **Frontend (Planshet Boshqaruv Quyi Tizimi):**
   - Texnologiya: **React 19** (Concurrent Rendering, Server Components va optimallashtirilgan state-reaktivlik).
   - UI/UX: Gibrid planshet landshaft (Landscape 1024x768+) interfeysi, teginish maydonlari min 48px.
   - **Web Audio API & MediaRecorder:** Hamshiraning audio oqimini mikrosekundlik aniqlikda buferlash va siqilmagan WAV/WebM holatida uzatish.
   - Manikenlar o'rtasida bir teginishda fokusni dinamik o'zgartirish va real-vaqtli Wi-Fi diagnostikasi.

2. **Backend (Asinxron Dvigatel):**
   - Dasturlash tili: **Python 3.11+ / FastAPI ASGI**.
   - Asinxron non-blocking arxitektura (`asyncio`, `asyncpg`, `httpx` connection pooling).
   - Har bir suhbat sessiyasini, javob berish kechikishini (Response Latency ms), tan olingan emotsiyalarni va xatolar logini tranzaksion yozib borish.

3. **Ma'lumotlar Bazasi (PostgreSQL 16+):**
   - Strukturaviy yaxlitlik: `mannequins`, `scenarios`, `script_qa`, `audio_presets`, `sessions`, `session_logs`.
   - Murakkab ma'lumot turlarini qo'llab-quvvatlash: `JSONB` (dinamik ovoz va harakatlar konfiguratsiyasi), `ARRAY` (kalit so'zlar va mavzu klasterlari), `INET` (apparat tarmoq manzillash).

---

## 5. KLINIK SSENARIYLARNING STANDART MATRITsASI

Tizim quyidagi 4 ta toifadagi to'liq klinik va patronaj ssenariylar bazasiga ega bo'lishi shart:

| # | Manikenni identifikatsiyasi | Biologik Guruhi | Klinik Patologiya & Ssenariy |
|---|---|---|---|
| **1** | **Qariya Bobo** | Geriatriya (65-75 yosh) | Surunkali gipertoniya, stenokardiya xuruji, serebrovaskulyar yetishmovchilik. |
| **2** | **Gulnora opa** | Akusherlik (32 hafta homilador) | 3-homiladorlik, surunkali piyelonefrit qo'zishi, 2-darajali temir tanqisligi anemiyasi (Hb 80 g/l), 4 bosqichli to'liq patronaj protokoli. |
| **3** | **Bola** | Pediatriya (5-6 yosh) | Gipertermiya (39.5°C), febril xuruj xavfi, inyeksiya fobiyasi (psixologik qarshilik). |
| **4** | **Chaqaloq** | Neonatologiya (0-1 yosh) | Chaqaloqlar asfiksiyasi, nafas yo'llari obstruktsiyasi, gipoksiya tovushlari. |

---

## 6. TALABGORGA (IJROCHIGA) QO'YILADIGAN KVALIFIKATSIYA VA MALAKA TALABLARI
*(Boshqa nojo'ya va tajribasiz ishtirokchilarning filtrlanishini ta'minlash uchun)*

1. Talabgor **Embedded C++ (ESP-IDF / Arduino SDK), I2S Audio Streaming, FreeRTOS** sohalarida apparat dasturlash bo'yicha real amaliy tajribaga ega bo'lishi shart.
2. Talabgor **FastAPI, Asinxron Python (asyncio/asyncpg), PostgreSQL JSONB/ARRAY** stekida murakkab NLU arxitekturalarini ishlab chiqqan bo'lishi kerak.
3. O'zbek tili fonetikasi va grammatikasiga moslashtirilgan STT/TTS neyrotarmoq modellarini mikrokontrollerlarga simsiz yo'naltirish (Audio-Routing) bo'yicha tayyor dasturiy yechim namunasini taqdim eta olishi shart.
4. Talabgor tomonidan taklif etilayotgan tizim kiber-xavfsizlik, shifrlangan ma'lumotlar almashinuvi va mahalliy lokal Wi-Fi tarmog'ida tashqi internet uzilgan holatda ham avtonom ishlash arxitekturasini qo'llab-quvvatlashi talab etiladi.
