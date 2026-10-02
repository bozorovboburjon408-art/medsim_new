/*
 * ==============================================================================
 * MEDSIM — Universal ESP32 Audio Speaker & Mannequin Firmware
 * ==============================================================================
 * YANGI 100% ISHONCHLI ARXITEKTURA:
 * 1. Hech qanday SWYH yoki tashqi streaming ilovalari KERAK EMAS!
 * 2. mDNS yoqilgan: Brauzer yoki Planshetdan to'g'ridan-to'g'ri http://medsim-speaker.local orqali ulanadi (IP qidirish shart emas!).
 * 3. To'g'ridan-to'g'ri HTTP Push (POST /play) orqali toza audio qabul qiladi va dinamikda ijro etadi.
 * 4. MPU-6050 Harakat sensori integratsiyasi (Chaqaloqni ovuntirish uchun).
 * 5. ESP32 ning ichki DAC (GPIO 25/26) orqali toza tovush chiqaradi (tashqi murakkab kutubxonalarsiz, 100% xatosiz kompilyatsiya bo'ladi!).
 * 
 * Pinout (Ulanishlar):
 * - PAM8403 / Dinamik Audio Kirishi -> GPIO 25 (DAC1) yoki GPIO 26 (DAC2)
 * - MPU-6050 SDA -> GPIO 21 (I2C Data)
 * - MPU-6050 SCL -> GPIO 22 (I2C Clock)
 * - MPU-6050 VCC -> 3.3V yoki 5V
 * - MPU-6050 GND -> GND
 * - Ichki LED -> GPIO 2
 * ==============================================================================
 */

#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <Wire.h>
#include <driver/dac.h>
#include <math.h>

// 1. WI-FI SOZLAMALARI
const char* ssid     = "A56";
const char* password = "21082007";

// mDNS Domen nomi (Masalan: http://medsim-speaker.local)
const char* mdns_host = "medsim-speaker";

WebServer server(80);

#define MPU_ADDR 0x68
#define LED_PIN 2

// Ovoz va Maniken holati
volatile int masterVolume = 85;       // 0 - 100 %
volatile bool isCrying = false;
volatile bool isSoothed = false;
volatile int soothingProgress = 0;    // 0 - 100 %
float currentMotion = 0.0;
unsigned long soothingStartTime = 0;
unsigned long lastMotionCheck = 0;

// ==============================================================================
// 1. MPU-6050 SENSOR DRAYVERI (I2C: SDA=21, SCL=22)
// ==============================================================================
bool mpuAvailable = false;

void initMPU6050() {
    Wire.begin(21, 22);
    Wire.setClock(400000);
    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x6B); // PWR_MGMT_1
    Wire.write(0);    // Uyqudan uyg'otish
    if (Wire.endTransmission() == 0) {
        mpuAvailable = true;
        Serial.println("✅ MPU-6050 sensori ulandi (I2C: 21, 22)");
    } else {
        mpuAvailable = false;
        Serial.println("ℹ️ MPU-6050 ulanmagan (Faqat audio kalonka rejimida ishlaydi)");
    }
}

void readMPU6050(int16_t &ax, int16_t &ay, int16_t &az, int16_t &gx, int16_t &gy, int16_t &gz) {
    if (!mpuAvailable) return;
    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x3B);
    Wire.endTransmission(false);
    Wire.requestFrom((uint8_t)MPU_ADDR, (size_t)14, true);

    if (Wire.available() >= 14) {
        ax = (Wire.read() << 8) | Wire.read();
        ay = (Wire.read() << 8) | Wire.read();
        az = (Wire.read() << 8) | Wire.read();
        int16_t temp = (Wire.read() << 8) | Wire.read();
        gx = (Wire.read() << 8) | Wire.read();
        gy = (Wire.read() << 8) | Wire.read();
        gz = (Wire.read() << 8) | Wire.read();
    }
}

// ==============================================================================
// 2. AUDIO DAC CHIQISH VA TON GENERATORI (GPIO 25 & 26)
// ==============================================================================
void silenceDAC() {
    dacWrite(25, 128); // Sukunat darajasi
    dacWrite(26, 128);
}

// Chaqaloq yig'isi sintezi
void playBabyCryCycle() {
    float vol = (masterVolume / 100.0f);
    for (int t = 0; t < 650; t++) {
        if (!isCrying) break;
        float freq = 520.0f + 320.0f * sinf(3.14159f * (t / 650.0f));
        float tremolo = 0.75f + 0.25f * sinf(2.0f * 3.14159f * 12.0f * (t / 1000.0f));
        float sample = 128.0f + (sinf(2.0f * 3.14159f * freq * (t / 1000.0f)) * 95.0f * vol * tremolo);
        uint8_t dacVal = (uint8_t)constrain((int)sample, 0, 255);
        dacWrite(25, dacVal);
        dacWrite(26, dacVal);
        delayMicroseconds(125);
    }
    silenceDAC();
    for (int p = 0; p < 120; p++) {
        if (!isCrying) break;
        delay(1);
    }
}

// Test ohangi (Do - Mi - Sol)
void playTestChime() {
    int notes[] = {523, 659, 784, 1046}; // Do, Mi, Sol, Do
    float vol = (masterVolume / 100.0f) * 0.8f;

    for (int n = 0; n < 4; n++) {
        int freq = notes[n];
        for (int t = 0; t < 150; t++) {
            float sample = 128.0f + (sinf(2.0f * 3.14159f * freq * (t / 1000.0f)) * 80.0f * vol);
            uint8_t dacVal = (uint8_t)constrain((int)sample, 0, 255);
            dacWrite(25, dacVal);
            dacWrite(26, dacVal);
            delayMicroseconds(125);
        }
        silenceDAC();
        delay(30);
    }
    silenceDAC();
}

// ==============================================================================
// 3. TO'G'RIDAN-TO'G'RI HTTP AUDIO QABUL QILISH (POST /play)
// ==============================================================================
void handlePlayAudio() {
    if (server.hasArg("plain") == false) {
        server.send(400, "text/plain", "Audio ma'lumot topilmadi");
        return;
    }

    String audioData = server.arg("plain");
    const uint8_t* bytes = (const uint8_t*)audioData.c_str();
    size_t len = audioData.length();

    digitalWrite(LED_PIN, HIGH);
    Serial.printf("🔊 Audio qabul qilindi: %d bayt. Ijro etilmoqda...\n", len);

    // 8-bit yoki 16-bit WAV/PCM namunalarini to'g'ridan-to'g'ri DAC ga uzatish
    size_t startOffset = 0;
    if (len > 44 && bytes[0] == 'R' && bytes[1] == 'I' && bytes[2] == 'F' && bytes[3] == 'F') {
        startOffset = 44; // WAV sarlavhasini o'tkazib yuborish
    }

    float vol = (masterVolume / 100.0f);
    for (size_t i = startOffset; i < len; i++) {
        uint8_t sample = bytes[i];
        // Ovoz balandligini qo'llash
        int centered = (int)sample - 128;
        uint8_t scaled = (uint8_t)constrain(128 + (int)(centered * vol), 0, 255);
        dacWrite(25, scaled);
        dacWrite(26, scaled);
        delayMicroseconds(62); // ~16kHz namuna tezligi
    }

    silenceDAC();
    digitalWrite(LED_PIN, LOW);
    server.send(200, "text/plain", "OK: Ijro etildi");
}

// ==============================================================================
// 4. MPU-6050 HARAKAT VA OVUNTIRISHNI TEKSHIRISH
// ==============================================================================
void updateMotionSensor() {
    if (!mpuAvailable) return;

    int16_t ax, ay, az, gx, gy, gz;
    readMPU6050(ax, ay, az, gx, gy, gz);

    float gX = abs(gx) / 131.0f;
    float gY = abs(gy) / 131.0f;
    float gZ = abs(gz) / 131.0f;
    currentMotion = (gX + gY + gZ);

    if (isCrying) {
        if (currentMotion >= 20.0f && currentMotion <= 180.0f) {
            if (soothingStartTime == 0) soothingStartTime = millis();
            unsigned long elapsed = millis() - soothingStartTime;
            soothingProgress = min(100, (int)((elapsed / 3500.0f) * 100));

            if (soothingProgress >= 100) {
                isCrying = false;
                isSoothed = true;
                soothingStartTime = 0;
                silenceDAC();
                playTestChime();
            }
        } else {
            if (soothingStartTime != 0) {
                soothingStartTime = 0;
                soothingProgress = max(0, soothingProgress - 20);
            }
        }
    }
}

// ==============================================================================
// 5. WEB SERVER VA BOSHQARUV PANELI
// ==============================================================================
void setupWebServer() {
    // 1. To'g'ridan-to'g'ri audio ijro (Planshetdan HTTP Push)
    server.on("/play", HTTP_POST, handlePlayAudio);

    // 2. Test ovozi
    server.on("/test", HTTP_GET, []() {
        playTestChime();
        server.send(200, "text/plain", "Test signali chalindi");
    });

    // 3. Yig'latish (A-usul)
    server.on("/trigger_cry", HTTP_GET, []() {
        isCrying = true;
        isSoothed = false;
        soothingProgress = 0;
        soothingStartTime = 0;
        server.send(200, "application/json", "{\"status\":\"crying\",\"message\":\"Yiglash boshlandi\"}");
    });

    // 4. Yig'ini to'xtatish
    server.on("/stop_cry", HTTP_GET, []() {
        isCrying = false;
        isSoothed = true;
        soothingProgress = 100;
        silenceDAC();
        server.send(200, "application/json", "{\"status\":\"calm\",\"message\":\"Tinchlandi\"}");
    });

    // 5. Ovoz balandligi
    server.on("/volume", HTTP_GET, []() {
        if (server.hasArg("level")) masterVolume = constrain(server.arg("level").toInt(), 0, 100);
        server.send(200, "text/plain", "Volume: " + String(masterVolume) + "%");
    });

    // 6. JSON Status
    server.on("/status", HTTP_GET, []() {
        String json = "{";
        json += "\"online\":true,";
        json += "\"ip\":\"" + WiFi.localIP().toString() + "\",";
        json += "\"mdns\":\"http://" + String(mdns_host) + ".local\",";
        json += "\"volume\":" + String(masterVolume) + ",";
        json += "\"is_crying\":" + String(isCrying ? "true" : "false") + ",";
        json += "\"is_soothed\":" + String(isSoothed ? "true" : "false") + ",";
        json += "\"soothing_progress\":" + String(soothingProgress) + ",";
        json += "\"motion\":" + String(currentMotion, 1) + ",";
        json += "\"free_heap\":" + String(ESP.getFreeHeap());
        json += "}";
        server.send(200, "application/json", json);
    });

    // 7. Chiroyli Web Panel (Toza oq dizayn)
    server.on("/", HTTP_GET, []() {
        String html = "<!DOCTYPE html><html lang='uz'><head><meta charset='utf-8'>"
                      "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                      "<title>MedSim — Universal AI Kalonka</title>"
                      "<style>"
                      "*{box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;margin:0;padding:0;}"
                      "body{background:#f8fafc;color:#1e293b;padding:20px;display:flex;justify-content:center;align-items:center;min-height:100vh;}"
                      ".card{background:#ffffff;border:1px solid #e2e8f0;border-radius:22px;padding:24px;width:100%;max-width:440px;box-shadow:0 10px 25px rgba(0,0,0,0.05);}"
                      "h2{font-size:20px;color:#0f172a;display:flex;align-items:center;gap:8px;margin-bottom:4px;}"
                      ".sub{font-size:12px;color:#64748b;margin-bottom:16px;}"
                      ".badge{display:inline-block;padding:4px 10px;border-radius:20px;font-size:11px;font-weight:600;margin-bottom:12px;background:#dcfce7;color:#166534;}"
                      ".info-box{background:#f1f5f9;border-radius:12px;padding:12px;font-size:12px;margin-bottom:16px;line-height:1.6;}"
                      ".btn{display:block;width:100%;padding:12px;border:none;border-radius:12px;font-size:14px;font-weight:600;cursor:pointer;margin-top:10px;transition:all 0.15s;text-align:center;}"
                      ".btn-blue{background:#2563eb;color:#fff;}.btn-blue:hover{background:#1d4ed8;}"
                      ".btn-green{background:#10b981;color:#fff;}.btn-green:hover{background:#059669;}"
                      ".btn-red{background:#ef4444;color:#fff;}.btn-red:hover{background:#dc2626;}"
                      ".btn-outline{background:#fff;border:1px solid #cbd5e1;color:#334155;}.btn-outline:hover{background:#f8fafc;}"
                      "</style></head><body><div class='card'>"
                      "<h2>🔊 MedSim Universal Kalonka</h2>"
                      "<p class='sub'>To'g'ridan-to'g'ri HTTP Push va mDNS Tizimi</p>"
                      "<span class='badge'>● Wi-Fi: " + String(ssid) + " (Ulandi)</span>"
                      "<div class='info-box'>"
                      "📍 <b>Kalonka IP:</b> " + WiFi.localIP().toString() + "<br>"
                      "🏷️ <b>Doimiy Nom:</b> <a href='http://" + String(mdns_host) + ".local' style='color:#2563eb;font-weight:bold;'>http://" + String(mdns_host) + ".local</a><br>"
                      "📡 <b>MPU-6050 Sensori:</b> " + (mpuAvailable ? "Faol (Uланган)" : "Ulanmagan") + "<br>"
                      "</div>"
                      "<button class='btn btn-blue' onclick='testSound()'>🔔 1. Test Signalini Chalish</button>"
                      "<button class='btn btn-red' onclick='triggerCry()'>😭 2. Chaqaloqni Yig'latish</button>"
                      "<button class='btn btn-green' onclick='stopCry()'>✨ 3. Tinchlantirish</button>"
                      "<hr style='border:0;border-top:1px solid #f1f5f9;margin:16px 0;'>"
                      "<div style='font-size:12px;color:#64748b;text-align:center;'>Planshet bilan avtomatik sinxronizatsiya qilingan</div>"
                      "</div>"
                      "<script>"
                      "function testSound(){fetch('/test');}"
                      "function triggerCry(){fetch('/trigger_cry');}"
                      "function stopCry(){fetch('/stop_cry');}"
                      "</script></body></html>";
        server.send(200, "text/html", html);
    });

    server.begin();
    Serial.println("🌐 HTTP Web Server ishga tushdi (Port 80)");
}

// ==============================================================================
// 6. SETUP VA LOOP
// ==============================================================================
void setup() {
    Serial.begin(115200);
    delay(500);

    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, LOW);
    silenceDAC();

    Serial.println("\n==============================================");
    Serial.println("  MedSim — Universal ESP32 Audio Kalonka");
    Serial.println("==============================================");

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
        Serial.print("📍 IP Manzil: ");
        Serial.println(WiFi.localIP());

        // mDNS ni ishga tushirish (medsim-speaker.local)
        if (MDNS.begin(mdns_host)) {
            Serial.printf("🏷️ mDNS ishga tushdi: http://%s.local\n", mdns_host);
        }
    } else {
        Serial.println("\n⚠️ Wi-Fi ga ulanib bo'lmadi (Offline rejim)");
    }

    setupWebServer();

    // Boshlang'ich qisqa xush kelibsiz signali
    playTestChime();
}

void loop() {
    server.handleClient();

    // Agar chaqaloq yig'layotgan bo'lsa ovoz chiqarish
    if (isCrying) {
        digitalWrite(LED_PIN, HIGH);
        playBabyCryCycle();
    } else {
        digitalWrite(LED_PIN, LOW);
    }

    // Har 50ms da MPU-6050 ni o'qish
    if (millis() - lastMotionCheck >= 50) {
        lastMotionCheck = millis();
        updateMotionSensor();
    }

    delay(2);
}
