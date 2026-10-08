/*
 * ==============================================================================
 * MEDSIM — Aqlli Chaqaloq Manikeni (ESP32-C6 + MPU-6050)
 * ==============================================================================
 * Ushbu dastur ESP32-C6 va MPU-6050 sensori yordamida chaqaloqning:
 * 1. Qo'lda to'g'ri/noto'g'ri ko'tarilishini (Pitch va Roll burchaklari)
 * 2. Chayqatish intensivligini (Shaken Baby sindromi yoki mayin ovutish)
 * 3. 4 ta asosiy holatini (CRYING, SOOTHING, CALM, LAUGHING)
 * aniqlaydi, Serial Monitor orqali real vaqtda to'liq ma'lumot chiqaradi hamda
 * Wi-Fi tarmog'i orqali REST API va Web Dashboard taqdim etadi.
 *
 * Platforma: ESP32-C6 (ESP-IDF / Arduino Core for ESP32)
 *
 * Ulanish Pinlari (Pinout):
 * - MPU-6050 VCC -> ESP32-C6 3.3V
 * - MPU-6050 GND -> ESP32-C6 GND
 * - MPU-6050 SDA -> ESP32-C6 GPIO 6
 * - MPU-6050 SCL -> ESP32-C6 GPIO 7
 * - Status LED   -> ESP32-C6 GPIO 8
 * ==============================================================================
 */

#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <Wire.h>
#include <math.h>

// 1. WI-FI VA TARMOQ SOZLAMALARI
const char* ssid = "A56";              // O'zingizning Wi-Fi nomingiz
const char* password = "21082007";     // Wi-Fi paroli
const char* mdns_host = "medsim-baby"; // http://medsim-baby.local

WebServer server(80);

// ESP32-C6 PIN SOZLAMALARI
#define I2C_SDA_PIN 6   // ESP32-C6 standart SDA
#define I2C_SCL_PIN 7   // ESP32-C6 standart SCL
#define LED_PIN     8   // ESP32-C6 Status LED
#define MPU_ADDR    0x68

// Chaqaloq holatlari
enum BabyState {
  STATE_CALM,      // Tinch / Xotirjam
  STATE_CRYING,    // Yig'lamoqda
  STATE_SOOTHING,  // Ovunmoqda (tinchlanish jarayonida)
  STATE_LAUGHING   // Kulmoqda / Qiyqirmoqda
};

BabyState currentState = STATE_CALM;
BabyState previousState = STATE_CALM;

// Holat parametrlari
volatile int soothingProgress = 0; // 0 - 100% (Ovunish darajasi)
volatile int happyProgress = 0;    // 0 - 100% (Xursandchilik/kulish darajasi)
float currentMotion = 0.0;
float pitch = 0.0;
float roll = 0.0;
float accelMagnitude = 1.0;

// Diagnostika matnlari
String holdingStatus = "LYING"; // "CORRECT", "UPSIDE_DOWN", "TILTED", "LYING"
String holdingText = "Yotqizilgan";
String shakeStatus = "NONE";   // "NONE", "GENTLE", "VIOLENT"
String shakeText = "Harakatsiz";

unsigned long lastUpdate = 0;
unsigned long lastSerialPrint = 0;
unsigned long gentleHoldStartTime = 0;
unsigned long violentShakeTime = 0;

// Sensor xom ma'lumotlari
int16_t raw_ax = 0, raw_ay = 0, raw_az = 0;
int16_t raw_gx = 0, raw_gy = 0, raw_gz = 0;
bool mpuAvailable = false;

// Holat nomini matn ko'rinishida olish
String getStateName(BabyState st) {
  switch (st) {
    case STATE_CRYING:   return "YIG'LAMOQDA 😭";
    case STATE_SOOTHING: return "OVUNMOQDA 🍼";
    case STATE_CALM:     return "TINCH 😌";
    case STATE_LAUGHING: return "KULMOQDA 😄";
    default:             return "NOMA'LUM";
  }
}

// ==============================================================================
// 1. MPU-6050 INITIALIZATSIYA VA O'QISH
// ==============================================================================
void initMPU6050() {
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  Wire.setClock(400000); // 400 kHz Fast Mode

  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x6B); // PWR_MGMT_1
  Wire.write(0);    // Uyqudan uyg'otish
  if (Wire.endTransmission() == 0) {
    mpuAvailable = true;
    Serial.printf("✅ MPU-6050 sensori muvaffaqiyatli ulandi (I2C: SDA=%d, SCL=%d)\n", I2C_SDA_PIN, I2C_SCL_PIN);
  } else {
    mpuAvailable = false;
    Serial.println("❌ MPU-6050 topilmadi! Simlarni tekshiring.");
  }
}

void readMPU6050() {
  if (!mpuAvailable) return;
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom((uint8_t)MPU_ADDR, (size_t)14, true);

  if (Wire.available() >= 14) {
    raw_ax = (Wire.read() << 8) | Wire.read();
    raw_ay = (Wire.read() << 8) | Wire.read();
    raw_az = (Wire.read() << 8) | Wire.read();
    int16_t temp = (Wire.read() << 8) | Wire.read();
    raw_gx = (Wire.read() << 8) | Wire.read();
    raw_gy = (Wire.read() << 8) | Wire.read();
    raw_gz = (Wire.read() << 8) | Wire.read();
  }
}

// ==============================================================================
// 2. CHAQALOQNING HARAKAT VA XULQ-ATVORINI BAHOLASH
// ==============================================================================
void updateBabyBehavior() {
  if (!mpuAvailable) return;

  readMPU6050();

  // 1. Gravitatsiya va burchaklarni hisoblash
  float ax_g = (float)raw_ax / 16384.0f;
  float ay_g = (float)raw_ay / 16384.0f;
  float az_g = (float)raw_az / 16384.0f;

  accelMagnitude = sqrt(ax_g * ax_g + ay_g * ay_g + az_g * az_g);
  float dynamicAccel = abs(accelMagnitude - 1.0f); // Tinch holatdan chetlanish

  // Pitch (bosh balandligi) va Roll (yonbosh burchagi)
  pitch = atan2(ay_g, sqrt(ax_g * ax_g + az_g * az_g)) * 180.0f / M_PI;
  roll = atan2(-ax_g, az_g) * 180.0f / M_PI;

  // 2. Gyroskop harakat tezligi
  float gx_dps = abs(raw_gx) / 131.0f;
  float gy_dps = abs(raw_gy) / 131.0f;
  float gz_dps = abs(raw_gz) / 131.0f;
  float gyroSpeed = gx_dps + gy_dps + gz_dps;

  // Umumiy harakat koeffitsiyenti
  currentMotion = (gyroSpeed * 0.7f) + (dynamicAccel * 100.0f * 0.3f);

  // 3. Ko'tarish holatini aniqlash (Holding Posture)
  bool isProperlyHeld = false;

  if (pitch < -35.0f || az_g < -0.4f) {
    holdingStatus = "UPSIDE_DOWN";
    holdingText = "XAVFLI: Boshi pastga qaragan (Teskari)!";
  } else if (abs(roll) > 65.0f) {
    holdingStatus = "TILTED";
    holdingText = "Noto'g'ri: Yonga qattiq egilgan!";
  } else if (pitch >= 20.0f && pitch <= 85.0f && abs(roll) <= 45.0f) {
    holdingStatus = "CORRECT";
    holdingText = "To'g'ri ko'tarilgan (Quchoqda)";
    isProperlyHeld = true;
  } else {
    holdingStatus = "LYING";
    holdingText = "Gorizontal yotqizilgan";
  }

  // 4. Chayqatish darajasini aniqlash (Shake Intensity)
  bool isGentleRocking = false;
  bool isViolentShaking = false;

  if (currentMotion > 190.0f || dynamicAccel > 0.85f) {
    shakeStatus = "VIOLENT";
    shakeText = "XAVFLI: Juda qattiq siltanmoqda!";
    isViolentShaking = true;
    violentShakeTime = millis();
  } else if (currentMotion >= 20.0f && currentMotion <= 140.0f && dynamicAccel <= 0.65f) {
    shakeStatus = "GENTLE";
    shakeText = "Mayin va me'yorida tebratish";
    isGentleRocking = true;
  } else if (currentMotion < 15.0f) {
    shakeStatus = "NONE";
    shakeText = "Harakatsiz / Tinch";
  } else {
    shakeStatus = "MODERATE";
    shakeText = "Oddiy harakat";
  }

  // ==========================================================================
  // 5. CHAQALOQNING XULQ-ATVORINI BOSHQARISH MANTIG'I (STATE MACHINE)
  // ==========================================================================

  // XAVFLI HOLAT: Agar chaqaloq qattiq siltansa yoki teskari ushlansa -> DARHOL YIG'LAYDI!
  if (isViolentShaking || holdingStatus == "UPSIDE_DOWN") {
    if (currentState != STATE_CRYING) {
      Serial.println("\n--------------------------------------------------------------------------------");
      Serial.println("⚠️ [OGOHLANTIRISH] Chaqaloq qattiq bezovtalandi va YIG'LAY BOSHLADI 😭!");
      if (isViolentShaking) {
        Serial.printf("   Sabab: Juda qattiq siltash (Shaken baby xavfi)! Harakat = %.1f\n", currentMotion);
      }
      if (holdingStatus == "UPSIDE_DOWN") {
        Serial.printf("   Sabab: Boshi pastga qaragan (Teskari ushlash)! Pitch = %.1f°\n", pitch);
      }
      Serial.println("--------------------------------------------------------------------------------");
    }
    currentState = STATE_CRYING;
    soothingProgress = 0;
    happyProgress = 0;
    gentleHoldStartTime = 0;
  }

  // HOLAT 1: YIG'LAMOQDA (STATE_CRYING)
  if (currentState == STATE_CRYING) {
    happyProgress = 0;

    // Chaqaloqni ovutish qoidalari:
    // Bola TO'G'RI ko'tarilgan va MAYIN chayqatilayotgan bo'lishi shart!
    if (isProperlyHeld && isGentleRocking) {
      if (gentleHoldStartTime == 0) {
        gentleHoldStartTime = millis();
        Serial.println("🍼 [OVUNISH BOSHLANDI] Bola to'g'ri ko'tarildi va mayin chayqatilmoqda...");
      }

      // Ovunish jarayoni asta-sekin oshadi
      soothingProgress = min(100, soothingProgress + 3);

      if (soothingProgress >= 100) {
        currentState = STATE_CALM;
        soothingProgress = 100;
        gentleHoldStartTime = 0;
        Serial.println("\n✨ [TINCHLANDI] Chaqaloq to'liq ovundi va xotirjam bo'ldi (TINCH 😌)!");
      }
    } else {
      // Agar to'g'ri ovutilmasa, progress pasayadi
      gentleHoldStartTime = 0;
      soothingProgress = max(0, soothingProgress - 2);
    }
  }

  // HOLAT 2: TINCH / XOTIRJAM (STATE_CALM)
  else if (currentState == STATE_CALM) {
    soothingProgress = 100;

    // Agar bola to'g'ri ko'tarilgan holda erkalab mayin o'ynatilsa -> KULADI!
    if (isProperlyHeld && isGentleRocking) {
      happyProgress = min(100, happyProgress + 4);
      if (happyProgress >= 80) {
        currentState = STATE_LAUGHING;
        Serial.println("\n😄 [KULISH] Chaqaloq xursand bo'lib kulmoqda (KULMOQDA 😄)!");
      }
    } else {
      happyProgress = max(0, happyProgress - 2);
    }
  }

  // HOLAT 3: KULMOQDA / ERKALANISH (STATE_LAUGHING)
  else if (currentState == STATE_LAUGHING) {
    soothingProgress = 100;

    // Mayin erkalash davom etsa, kulishda davom etadi
    if (isProperlyHeld && isGentleRocking) {
      happyProgress = 100;
    } else {
      // Tebranish to'xtasa, asta-sekin kulish bosiladi va xotirjam bo'ladi
      happyProgress = max(0, happyProgress - 3);
      if (happyProgress <= 20) {
        currentState = STATE_CALM;
        Serial.println("\n😌 [XOTIRJAM] Erkalash to'xtadi, chaqaloq tinch holatga qaytdi.");
      }
    }
  }
}

// Helper: JSON yuborish
void sendJsonResponse(int code, const String& content) {
  server.sendHeader("Access-Control-Allow-Origin", "*");
  server.sendHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  server.sendHeader("Access-Control-Allow-Headers", "*");
  server.send(code, "application/json", content);
}

// ==============================================================================
// 3. WEB SERVER VA REST API
// ==============================================================================
void setupWebServer() {
  // 1. IP orqali holat ma'lumotlarini to'liq uzatish (JSON)
  server.on("/status", HTTP_GET, []() {
    String stateStr = "CALM";
    String stateUz = "Tinch";
    if (currentState == STATE_CRYING) {
      stateStr = "CRYING";
      stateUz = "Yig'lamoqda";
    } else if (currentState == STATE_LAUGHING) {
      stateStr = "LAUGHING";
      stateUz = "Kulmoqda";
    } else if (currentState == STATE_SOOTHING || (currentState == STATE_CRYING && soothingProgress > 0)) {
      stateStr = "SOOTHING";
      stateUz = "Ovunmoqda";
    }

    String json = "{";
    json += "\"online\":true,";
    json += "\"ip\":\"" + WiFi.localIP().toString() + "\",";
    json += "\"chip\":\"ESP32-C6\",";
    json += "\"state\":\"" + stateStr + "\",";
    json += "\"state_uz\":\"" + stateUz + "\",";
    json += "\"is_crying\":" + String(currentState == STATE_CRYING ? "true" : "false") + ",";
    json += "\"is_soothed\":" + String(currentState != STATE_CRYING ? "true" : "false") + ",";
    json += "\"is_laughing\":" + String(currentState == STATE_LAUGHING ? "true" : "false") + ",";
    json += "\"soothing_progress\":" + String(soothingProgress) + ",";
    json += "\"happy_progress\":" + String(happyProgress) + ",";
    json += "\"holding_status\":\"" + holdingStatus + "\",";
    json += "\"holding_text\":\"" + holdingText + "\",";
    json += "\"shake_status\":\"" + shakeStatus + "\",";
    json += "\"shake_text\":\"" + shakeText + "\",";
    json += "\"motion\":" + String(currentMotion, 1) + ",";
    json += "\"angles\":{\"pitch\":" + String(pitch, 1) + ",\"roll\":" + String(roll, 1) + "},";
    json += "\"sensor_ok\":" + String(mpuAvailable ? "true" : "false");
    json += "}";
    sendJsonResponse(200, json);
  });

  // 2. Chaqaloqni qo'lda yig'latish
  server.on("/trigger_cry", HTTP_GET, []() {
    currentState = STATE_CRYING;
    soothingProgress = 0;
    happyProgress = 0;
    Serial.println("🌐 [WEB BUYRUQ] /trigger_cry -> Chaqaloq yig'latildi 😭");
    sendJsonResponse(200, "{\"status\":\"crying\",\"message\":\"Chaqaloq yigladi\"}");
  });

  // 3. Chaqaloqni kuldirish
  server.on("/trigger_laugh", HTTP_GET, []() {
    currentState = STATE_LAUGHING;
    soothingProgress = 100;
    happyProgress = 100;
    Serial.println("🌐 [WEB BUYRUQ] /trigger_laugh -> Chaqaloq kuldirildi 😄");
    sendJsonResponse(200, "{\"status\":\"laughing\",\"message\":\"Chaqaloq kuldi\"}");
  });

  // 4. Tinchlantirish
  server.on("/stop_cry", HTTP_GET, []() {
    currentState = STATE_CALM;
    soothingProgress = 100;
    happyProgress = 0;
    Serial.println("🌐 [WEB BUYRUQ] /stop_cry -> Chaqaloq tinchlantirildi 😌");
    sendJsonResponse(200, "{\"status\":\"calm\",\"message\":\"Chaqaloq tinchlandi\"}");
  });

  // 5. Qayta sozlash
  server.on("/reset", HTTP_GET, []() {
    currentState = STATE_CALM;
    soothingProgress = 0;
    happyProgress = 0;
    Serial.println("🌐 [WEB BUYRUQ] /reset -> Tizim qayta sozlandi 🔄");
    sendJsonResponse(200, "{\"status\":\"reset\",\"message\":\"Qayta sozlandi\"}");
  });

  // 6. Zamonaviy Web Dashboard (Brauzerdan kuzatish)
  server.on("/", HTTP_GET, []() {
    String html = "<!DOCTYPE html><html lang='uz'><head><meta charset='utf-8'>"
      "<meta name='viewport' content='width=device-width,initial-scale=1'>"
      "<title>MedSim — Aqlli Chaqaloq Manikeni (ESP32-C6)</title>"
      "<style>"
      "*{box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;margin:0;padding:0;}"
      "body{background:#f8fafc;color:#0f172a;padding:16px;display:flex;justify-content:center;align-items:center;min-height:100vh;}"
      ".card{background:#fff;border-radius:24px;padding:24px;width:100%;max-width:460px;box-shadow:0 12px 35px rgba(0,0,0,0.07);border:1px solid #e2e8f0;}"
      ".header{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;}"
      ".header h2{font-size:20px;display:flex;align-items:center;gap:8px;}"
      ".badge{padding:4px 10px;border-radius:16px;font-size:11px;font-weight:700;background:#dcfce7;color:#166534;}"
      ".state-banner{text-align:center;padding:18px;border-radius:18px;margin-bottom:16px;transition:0.3s;}"
      ".state-emoji{font-size:48px;display:block;margin-bottom:4px;}"
      ".state-title{font-size:22px;font-weight:800;}"
      ".cry-bg{background:#fee2e2;color:#991b1b;}"
      ".calm-bg{background:#dcfce7;color:#166534;}"
      ".laugh-bg{background:#e0e7ff;color:#3730a3;}"
      ".sooth-bg{background:#fef3c7;color:#92400e;}"
      ".box{background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;padding:12px;margin-bottom:12px;font-size:13px;line-height:1.6;}"
      ".row{display:flex;justify-content:space-between;align-items:center;margin:4px 0;font-weight:600;}"
      ".p-bar{background:#e2e8f0;border-radius:8px;height:10px;overflow:hidden;margin:6px 0 10px;}"
      ".p-fill-blue{background:#3b82f6;height:100%;width:0%;transition:width 0.2s;}"
      ".p-fill-purple{background:#8b5cf6;height:100%;width:0%;transition:width 0.2s;}"
      ".btn-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px;}"
      ".btn{padding:10px;border:none;border-radius:12px;font-size:13px;font-weight:700;cursor:pointer;transition:0.15s;}"
      ".btn-red{background:#ef4444;color:#fff;}"
      ".btn-purple{background:#8b5cf6;color:#fff;}"
      ".btn-green{background:#10b981;color:#fff;}"
      ".btn-slate{background:#64748b;color:#fff;}"
      "</style></head><body><div class='card'>"
      "<div class='header'>"
      "<h2>👶 MedSim (ESP32-C6)</h2>"
      "<span class='badge'>IP: " + WiFi.localIP().toString() + "</span>"
      "</div>"
      "<div id='banner' class='state-banner calm-bg'>"
      "<span id='bEmoji' class='state-emoji'>😴</span>"
      "<div id='bTitle' class='state-title'>Tinch</div>"
      "<div id='bDesc' style='font-size:12px;opacity:0.85;'>Chaqaloq xotirjam</div>"
      "</div>"
      "<div class='box'>"
      "<div class='row'><span>Ko'tarish holati:</span><span id='hStatus' style='color:#2563eb;'>-</span></div>"
      "<div class='row'><span>Chayqatish:</span><span id='sStatus' style='color:#059669;'>-</span></div>"
      "<div class='row'><span>Harakat intensivligi:</span><span id='mVal'>0.0</span></div>"
      "<div class='row'><span>Burchaklar:</span><span id='angVal'>Pitch: 0° | Roll: 0°</span></div>"
      "</div>"
      "<div class='box'>"
      "<div class='row'><span>Ovunish progressi:</span><span id='pSooth'>0%</span></div>"
      "<div class='p-bar'><div id='barSooth' class='p-fill-blue'></div></div>"
      "<div class='row'><span>Quvonch va Kulgi darajasi:</span><span id='pLaugh'>0%</span></div>"
      "<div class='p-bar'><div id='barLaugh' class='p-fill-purple'></div></div>"
      "</div>"
      "<div class='btn-grid'>"
      "<button class='btn btn-red' onclick=\"fetch('/trigger_cry')\">😭 Yig'latish</button>"
      "<button class='btn btn-purple' onclick=\"fetch('/trigger_laugh')\">😄 Kuldurish</button>"
      "<button class='btn btn-green' onclick=\"fetch('/stop_cry')\">✅ Tinchlantirish</button>"
      "<button class='btn btn-slate' onclick=\"fetch('/reset')\">🔄 Qayta boshlash</button>"
      "</div>"
      "</div>"
      "<script>"
      "setInterval(() => {"
      " fetch('/status').then(r => r.json()).then(d => {"
      " document.getElementById('mVal').innerText = d.motion;"
      " document.getElementById('hStatus').innerText = d.holding_text;"
      " document.getElementById('sStatus').innerText = d.shake_text;"
      " document.getElementById('angVal').innerText = 'Pitch: ' + d.angles.pitch + '° | Roll: ' + d.angles.roll + '°';"
      " document.getElementById('pSooth').innerText = d.soothing_progress + '%';"
      " document.getElementById('barSooth').style.width = d.soothing_progress + '%';"
      " document.getElementById('pLaugh').innerText = d.happy_progress + '%';"
      " document.getElementById('barLaugh').style.width = d.happy_progress + '%';"
      " let b = document.getElementById('banner');"
      " let em = document.getElementById('bEmoji');"
      " let tt = document.getElementById('bTitle');"
      " let ds = document.getElementById('bDesc');"
      " b.className = 'state-banner ';"
      " if (d.state === 'CRYING') {"
      " b.className += 'cry-bg'; em.innerText = '😭'; tt.innerText = 'Yig\\'layapti!';"
      " ds.innerText = 'To\\'g\\'ri ko\\'taring va mayin tebrating!';"
      " } else if (d.state === 'LAUGHING') {"
      " b.className += 'laugh-bg'; em.innerText = '😄'; tt.innerText = 'Kulmoqda!';"
      " ds.innerText = 'Chaqaloq xursand va quvonmoqda';"
      " } else if (d.state === 'SOOTHING') {"
      " b.className += 'sooth-bg'; em.innerText = '🥺'; tt.innerText = 'Ovunmoqda...';"
      " ds.innerText = 'Mayin tebratish davom etmoqda';"
      " } else {"
      " b.className += 'calm-bg'; em.innerText = '😴'; tt.innerText = 'Tinch / Xotirjam';"
      " ds.innerText = 'Hammasi me\\'yorida';"
      " }"
      " }).catch(e => console.error(e));"
      "}, 200);"
      "</script></body></html>";
    server.send(200, "text/html", html);
  });

  server.begin();
  Serial.println("🌐 HTTP Web Server ishga tushdi (Port 80)");
}

// ==============================================================================
// 4. SETUP VA LOOP
// ==============================================================================
void setup() {
  Serial.begin(115200);
  delay(500);

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  Serial.println("\n=======================================================");
  Serial.println("  MEDSIM — Aqlli Chaqaloq Manikeni (ESP32-C6)          ");
  Serial.println("  MPU-6050 Harakat va Holatlarni Kuzatish Tizimi        ");
  Serial.println("=======================================================");

  initMPU6050();

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.print("Wi-Fi ga ulanmoqda...");

  int retry = 0;
  while (WiFi.status() != WL_CONNECTED && retry < 25) {
    delay(500);
    Serial.print(".");
    retry++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✅ Wi-Fi ulandi!");
    Serial.print("📡 IP Manzil: ");
    Serial.println(WiFi.localIP());

    if (MDNS.begin(mdns_host)) {
      Serial.printf("🔗 mDNS: http://%s.local\n", mdns_host);
    }
  } else {
    Serial.println("\n⚠️ Wi-Fi ga ulanib bo'lmadi (Offline rejim)");
  }

  setupWebServer();
  Serial.println("🚀 Tizim to'liq ishga tushdi! Telemetriya ma'lumotlari boshlandi:\n");
}

void loop() {
  server.handleClient();

  // Har 50 ms da datchik ma'lumotlarini tahlil qilish (20 Hz)
  if (millis() - lastUpdate >= 50) {
    lastUpdate = millis();
    updateBabyBehavior();
  }

  // Har 500 ms da Serial Monitorga to'liq holat telemetriyasini chiqarish
  if (millis() - lastSerialPrint >= 500) {
    lastSerialPrint = millis();
    Serial.printf("[HOLAT: %-16s] | Ko'tarish: %-11s | Chayqatish: %-8s | Harakat: %5.1f | Pitch: %+5.1f° | Roll: %+5.1f° | Ovunish: %3d%% | Kulgi: %3d%%\n",
                  getStateName(currentState).c_str(),
                  holdingStatus.c_str(),
                  shakeStatus.c_str(),
                  currentMotion,
                  pitch,
                  roll,
                  soothingProgress,
                  happyProgress);
  }

  // Holatga mos LED ko'rsatkichlari (Vizual indikatsiya)
  if (currentState == STATE_CRYING) {
    // Yig'layotganda tez miltillaydi (ogohlantirish)
    digitalWrite(LED_PIN, (millis() / 200) % 2);
  } else if (currentState == STATE_LAUGHING) {
    // Kulayotganda quvnoq ikkitalik miltillash
    int cycle = (millis() % 600);
    digitalWrite(LED_PIN, (cycle < 100 || (cycle > 200 && cycle < 300)) ? HIGH : LOW);
  } else if (currentState == STATE_CALM) {
    // Tinch holatda doimiy yonib turadi
    digitalWrite(LED_PIN, HIGH);
  } else {
    digitalWrite(LED_PIN, LOW);
  }

  delay(2);
}
