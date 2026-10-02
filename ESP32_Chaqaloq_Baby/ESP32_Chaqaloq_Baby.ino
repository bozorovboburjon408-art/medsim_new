/*
 * ==============================================================================
 * MEDSIM — Chaqaloq Simulyatori Firmware (ESP32 + MPU-6050 + Audio DAC)
 * ==============================================================================
 * Vazifasi:
 * 1. Planshetdan yoki Web paneldan buyruq kelganda chaqaloq yig'laydi (/trigger_cry)
 * 2. MPU-6050 sensori orqali hamshira chaqaloqni qo'liga olib mayin tebratayotganini (rocking) aniqlaydi
 * 3. 3-4 soniya tebratilgach, yig'i to'xtaydi va tinch nafas / ovunish ovozi chiqadi
 * 4. DAC GPIO 25/26 orqali to'g'ridan-to'g'ri dinamikka ovoz beradi (hech qanday qo'shimcha kutubxonasiz!)
 * 
 * Pinout (Ulanish):
 * - MPU-6050 VCC -> 3.3V yoki 5V
 * - MPU-6050 GND -> GND
 * - MPU-6050 SDA -> GPIO 21
 * - MPU-6050 SCL -> GPIO 22
 * - PAM8403 / Dinamik Kirishi -> GPIO 25 (DAC1) yoki GPIO 26 (DAC2)
 * - LED Indikator -> GPIO 2 (Ichki ko'k chiroq)
 * ==============================================================================
 */

#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <math.h>

// Wi-Fi sozlamalari
const char* ssid     = "A56";
const char* password = "21082007";

WebServer server(80);

// MPU-6050 I2C Manzili
#define MPU_ADDR 0x68

// LED indikator
#define LED_PIN 2

// Chaqaloq holati
volatile bool isCrying = false;
volatile bool isSoothed = false;
volatile int soothingProgress = 0; // 0 - 100%
float currentMotion = 0.0;
unsigned long soothingStartTime = 0;
unsigned long lastMotionCheckTime = 0;
unsigned long cryStartTime = 0;

// Ovoz sozlamasi
int masterVolume = 85; // 0 - 100 %

// ==============================================================================
// 1. MPU-6050 DRAYVERI (Tashqi kutubxonalarsiz, to'g'ridan-to'g'ri I2C orqali)
// ==============================================================================
bool initMPU6050() {
    Wire.begin(21, 22); // SDA=21, SCL=22
    Wire.setClock(400000); // 400kHz tezkor I2C

    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x6B); // PWR_MGMT_1 registri
    Wire.write(0);    // MPU-6050 ni uyqudan uyg'otish
    byte err = Wire.endTransmission();

    if (err == 0) {
        Serial.println("✅ MPU-6050 sensori muvaffaqiyatli ulandi (I2C: SDA=21, SCL=22)");
        return true;
    } else {
        Serial.println("⚠️ MPU-6050 topilmadi! Simlarni tekshiring (SDA=21, SCL=22).");
        return false;
    }
}

void readMPU6050(int16_t &ax, int16_t &ay, int16_t &az, int16_t &gx, int16_t &gy, int16_t &gz) {
    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x3B); // Boshlang'ich registr
    Wire.endTransmission(false);
    Wire.requestFrom((uint8_t)MPU_ADDR, (size_t)14, true);

    if (Wire.available() >= 14) {
        ax = (Wire.read() << 8) | Wire.read();
        ay = (Wire.read() << 8) | Wire.read();
        az = (Wire.read() << 8) | Wire.read();
        int16_t temp = (Wire.read() << 8) | Wire.read(); // Harorat
        gx = (Wire.read() << 8) | Wire.read();
        gy = (Wire.read() << 8) | Wire.read();
        gz = (Wire.read() << 8) | Wire.read();
    }
}

// ==============================================================================
// 2. CHAQALOQ OVOZI SINTEZI (ESP32 DAC: GPIO 25)
// ==============================================================================
void silenceDAC() {
    dacWrite(25, 128); // 0V o'rtadagi jimlik darajasi
    dacWrite(26, 128);
}

// Haqiqiy chaqaloq yig'isini dinamik chastotada sintezlash
void playBabyCryTone(int cycle) {
    // Chaqaloq yig'isi: 450Hz dan 900Hz gacha ko'tarilib-tushuvchi to'lqin
    float vol = (masterVolume / 100.0f);
    
    // Yig'ining har bir nolasi (~700ms)
    for (int t = 0; t < 700; t++) {
        if (!isCrying) break;

        // Chastota modulyatsiyasi (wah-wah effekti)
        float freq = 500.0f + 350.0f * sinf(3.14159f * (t / 700.0f));
        float tremolo = 0.7f + 0.3f * sinf(2.0f * 3.14159f * 12.0f * (t / 1000.0f));
        
        // DAC namunasi (8-bit: 0..255, 128 - markaz)
        float sample = 128.0f + (sinf(2.0f * 3.14159f * freq * (t / 1000.0f)) * 100.0f * vol * tremolo);
        uint8_t dacVal = (uint8_t)constrain((int)sample, 0, 255);

        dacWrite(25, dacVal);
        dacWrite(26, dacVal);
        delayMicroseconds(120);
    }

    // Nola orasidagi kichik nafas olish pauzasi (150ms)
    silenceDAC();
    for (int p = 0; p < 150; p++) {
        if (!isCrying) break;
        delay(1);
    }
}

// Chaqaloq tinchlangandagi nafas / mamnunlik signali
void playBabyCalmTone() {
    float vol = (masterVolume / 100.0f) * 0.6f;
    for (int t = 0; t < 500; t++) {
        float freq = 600.0f - 200.0f * (t / 500.0f); // Pastga tushuvchi mayin ohang
        float sample = 128.0f + (sinf(2.0f * 3.14159f * freq * (t / 1000.0f)) * 70.0f * vol);
        uint8_t dacVal = (uint8_t)constrain((int)sample, 0, 255);
        dacWrite(25, dacVal);
        delayMicroseconds(140);
    }
    silenceDAC();
}

// ==============================================================================
// 3. OVOZ VA TEBRANISHNI BOSHQARISH VAZIFASI (Core 1)
// ==============================================================================
void babyTask(void* parameter) {
    int cycle = 0;
    while (true) {
        if (isCrying) {
            digitalWrite(LED_PIN, HIGH);
            playBabyCryTone(cycle++);
        } else {
            digitalWrite(LED_PIN, LOW);
            silenceDAC();
            vTaskDelay(pdMS_TO_TICKS(50));
        }
    }
}

// ==============================================================================
// 4. MPU-6050 TEBRATISHNI (OVUNTIRISHNI) HISOBLASH ALGORITMI
// ==============================================================================
void updateMotionSensor() {
    int16_t ax, ay, az, gx, gy, gz;
    readMPU6050(ax, ay, az, gx, gy, gz);

    // Giroskop burchak tezligi (gradus/sekund)
    float gX_dps = abs(gx) / 131.0f;
    float gY_dps = abs(gy) / 131.0f;
    float gZ_dps = abs(gz) / 131.0f;
    
    // Umumiy harakat intensivligi
    currentMotion = (gX_dps + gY_dps + gZ_dps);

    if (isCrying) {
        // Hamshira chaqaloqni qo'lga olib mayin tebratayotgan bo'lsa (20..180 dps)
        if (currentMotion >= 20.0f && currentMotion <= 180.0f) {
            if (soothingStartTime == 0) {
                soothingStartTime = millis();
                Serial.println("🤱 Hamshira chaqaloqni ovuntirishni boshladi...");
            }

            unsigned long elapsed = millis() - soothingStartTime;
            soothingProgress = min(100, (int)((elapsed / 3500.0f) * 100)); // 3.5 soniya tebratilsa 100%

            if (soothingProgress >= 100) {
                Serial.println("🎉 Chaqaloq ovundi va tinchlandi!");
                isCrying = false;
                isSoothed = true;
                soothingStartTime = 0;
                playBabyCalmTone();
            }
        } else {
            // Tebranish to'xtatilsa yoki juda qattiq silkitsa (chala qoldirilsa)
            if (soothingStartTime != 0) {
                soothingStartTime = 0;
                soothingProgress = max(0, soothingProgress - 20);
            }
        }
    }
}

// ==============================================================================
// 5. WEB SERVER ENDPOINTS (Planshet va Brauzer uchun)
// ==============================================================================
void setupWebServer() {
    // 1. Yig'lashni boshlash (Planshetdan A-usul)
    server.on("/trigger_cry", HTTP_GET, []() {
        isCrying = true;
        isSoothed = false;
        soothingProgress = 0;
        soothingStartTime = 0;
        cryStartTime = millis();
        Serial.println("📢 BUYRUQ: Chaqaloq yig'lashni boshladi!");
        server.send(200, "application/json", "{\"status\":\"crying\",\"message\":\"Chaqaloq yiglay boshladi\"}");
    });

    // 2. Yig'lashni to'xtatish
    server.on("/stop_cry", HTTP_GET, []() {
        isCrying = false;
        isSoothed = true;
        soothingProgress = 100;
        Serial.println("🛑 BUYRUQ: Yig'i to'xtatildi.");
        server.send(200, "application/json", "{\"status\":\"calm\",\"message\":\"Yigi toxtatildi\"}");
    });

    // 3. Chaqaloq holati va sensordan jonli ma'lumot olish
    server.on("/status", HTTP_GET, []() {
        String json = "{";
        json += "\"is_crying\":" + String(isCrying ? "true" : "false") + ",";
        json += "\"is_soothed\":" + String(isSoothed ? "true" : "false") + ",";
        json += "\"soothing_progress\":" + String(soothingProgress) + ",";
        json += "\"motion\":" + String(currentMotion, 1) + ",";
        json += "\"ip\":\"" + WiFi.localIP().toString() + "\",";
        json += "\"free_ram\":" + String(ESP.getFreeHeap());
        json += "}";
        server.send(200, "application/json", json);
    });

    // 4. Ovoz balandligini sozlash
    server.on("/volume", HTTP_GET, []() {
        if (server.hasArg("level")) {
            masterVolume = constrain(server.arg("level").toInt(), 0, 100);
        }
        server.send(200, "text/plain", "Volume: " + String(masterVolume) + "%");
    });

    // 5. Chaqaloq Boshqaruv Veb-Paneli
    server.on("/", HTTP_GET, []() {
        String html = "<!DOCTYPE html><html lang='uz'><head><meta charset='utf-8'>"
                      "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                      "<title>MedSim — Chaqaloq Simulyatori</title>"
                      "<style>"
                      "*{box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;margin:0;padding:0;}"
                      "body{background:#f0fdf4;color:#1e293b;padding:20px;display:flex;justify-content:center;align-items:center;min-height:100vh;}"
                      ".card{background:#ffffff;border:1px solid #bbf7d0;border-radius:24px;padding:26px;width:100%;max-width:420px;box-shadow:0 12px 30px rgba(0,0,0,0.06);text-align:center;}"
                      ".emoji{font-size:54px;margin-bottom:8px;display:inline-block;animation:bounce 2s infinite;}"
                      "h2{font-size:20px;color:#166534;margin-bottom:4px;}"
                      ".sub{font-size:12px;color:#64748b;margin-bottom:16px;}"
                      ".status-box{background:#f8fafc;border:2px solid #e2e8f0;border-radius:16px;padding:14px;margin-bottom:18px;transition:all 0.3s;}"
                      ".status-crying{background:#fef2f2;border-color:#fca5a5;color:#991b1b;}"
                      ".status-soothed{background:#f0fdf4;border-color:#86efac;color:#166534;}"
                      ".progress-bar{height:12px;background:#e2e8f0;border-radius:10px;overflow:hidden;margin-top:10px;}"
                      ".progress-fill{height:100%;background:#10b981;width:0%;transition:width 0.3s;}"
                      ".btn{display:block;width:100%;padding:14px;border:none;border-radius:14px;font-size:15px;font-weight:700;cursor:pointer;margin-top:10px;transition:all 0.15s;}"
                      ".btn-cry{background:#ef4444;color:#fff;box-shadow:0 4px 12px rgba(239,68,68,0.3);}"
                      ".btn-cry:hover{background:#dc2626;}"
                      ".btn-calm{background:#10b981;color:#fff;}"
                      ".btn-calm:hover{background:#059669;}"
                      ".motion-badge{display:inline-block;margin-top:12px;font-size:12px;padding:6px 12px;border-radius:20px;background:#f1f5f9;color:#475569;font-weight:600;}"
                      "@keyframes bounce{0%,100%{transform:translateY(0);}50%{transform:translateY(-8px);}}"
                      "</style></head><body><div class='card'>"
                      "<div class='emoji' id='emo'>👶</div>"
                      "<h2>MedSim — Chaqaloq</h2>"
                      "<p class='sub'>Taktil va Harakatli Hamshiralik Simulyatori</p>"
                      "<div class='status-box' id='s_box'>"
                      "<b id='s_title' style='font-size:14px;'>Holat: Tinch (Krovatda)</b><br>"
                      "<span id='s_desc' style='font-size:12px;opacity:0.8;'>Tugmani bosing va chaqaloq yig'laydi</span>"
                      "<div class='progress-bar'><div class='progress-fill' id='p_fill'></div></div>"
                      "<div style='font-size:11px;margin-top:4px;display:flex;justify-content:space-between;color:#64748b;'>"
                      "<span>Ovunish jarayoni:</span><span id='p_txt'>0%</span></div>"
                      "</div>"
                      "<button class='btn btn-cry' onclick='startCry()'>😭 1. Chaqaloqni yig'latish (A-usul)</button>"
                      "<button class='btn btn-calm' onclick='stopCry()'>✨ 2. Majburiy tinchlantirish</button>"
                      "<div class='motion-badge' id='m_badge'>📡 MPU-6050 Harakat: 0.0 dps</div>"
                      "</div>"
                      "<script>"
                      "function startCry(){fetch('/trigger_cry');}"
                      "function stopCry(){fetch('/stop_cry');}"
                      "setInterval(()=>{fetch('/status').then(r=>r.json()).then(d=>{"
                      "var emo=document.getElementById('emo');"
                      "var sBox=document.getElementById('s_box');"
                      "var sTitle=document.getElementById('s_title');"
                      "var sDesc=document.getElementById('s_desc');"
                      "var pFill=document.getElementById('p_fill');"
                      "var pTxt=document.getElementById('p_txt');"
                      "var mBadge=document.getElementById('m_badge');"
                      "pFill.style.width=d.soothing_progress+'%';"
                      "pTxt.innerText=d.soothing_progress+'%';"
                      "mBadge.innerText='📡 MPU-6050 Harakat: '+d.motion+' dps';"
                      "if(d.is_crying){"
                      "emo.innerText='😭';"
                      "sBox.className='status-box status-crying';"
                      "sTitle.innerText='Chaqaloq yiglamoqda!';"
                      "sDesc.innerText=d.soothing_progress>0 ? 'Hamshira tebratyapti...':'Qolga olib mayin tebrating';"
                      "}else if(d.is_soothed){"
                      "emo.innerText='😴';"
                      "sBox.className='status-box status-soothed';"
                      "sTitle.innerText='Chaqaloq ovundi va uxlab qoldi!';"
                      "sDesc.innerText='Vazifa muvaffaqiyatli bajarildi';"
                      "}else{"
                      "emo.innerText='👶';"
                      "sBox.className='status-box';"
                      "sTitle.innerText='Holat: Tinch (Krovatda)';"
                      "sDesc.innerText='Yiglatish uchun tugmani bosing';"
                      "}"
                      "});},500);"
                      "</script></body></html>";
        server.send(200, "text/html", html);
    });

    server.begin();
    Serial.println("🌐 Web Server ishga tushdi!");
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
    Serial.println("  MedSim — Chaqaloq Simulyatori (ESP32)");
    Serial.println("==============================================");

    // MPU-6050 sensori
    initMPU6050();

    // Wi-Fi ulanishi
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
        Serial.print("📍 Chaqaloq IP manzili: http://");
        Serial.println(WiFi.localIP());
    } else {
        Serial.println("\n⚠️ Wi-Fi ulanmadi (Offline rejimda ishlayveradi)");
    }

    setupWebServer();

    // Ovoz sintezi (Core 1 da alohida oqimda ishlaydi)
    xTaskCreatePinnedToCore(babyTask, "BabyTask", 4096, NULL, 2, NULL, 1);
}

void loop() {
    server.handleClient();

    // Har 50ms da MPU-6050 harakatini hisoblash
    if (millis() - lastMotionCheckTime >= 50) {
        lastMotionCheckTime = millis();
        updateMotionSensor();
    }

    delay(2);
}
