#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include "AudioOutputInternalDAC.h"

// ==============================================================================
// 1. WI-FI VA STREAM SOZLAMALARI
// ==============================================================================
const char* default_ssid     = "A56";
const char* default_password = "21082007";

// Smartfon jonli oqim manzili (Boshlang'ich qiymat)
String audioServerUrl = "";

Preferences prefs;
WebServer server(80);
WiFiClient streamClient;

// ==============================================================================
// 2. EQUALIZER VA DSP (BLOKLI DMA QAYTA ISHLASH)
// ==============================================================================
class EqualizerDAC : public AudioOutputInternalDAC {
public:
    float volume = 0.8f;      // 0.0 - 1.0
    float bassGain = 1.0f;    // -10 dB .. +10 dB
    float trebleGain = 1.0f;  // -10 dB .. +10 dB

    float lpL = 0.0f, lpR = 0.0f;
    float hpL = 0.0f, hpR = 0.0f;
    float prevInL = 0.0f, prevInR = 0.0f;

    void setParams(int volPercent, int bassDb, int trebleDb) {
        volume = constrain(volPercent, 0, 100) / 100.0f;
        bassGain = powf(10.0f, constrain(bassDb, -10, 10) / 20.0f);
        trebleGain = powf(10.0f, constrain(trebleDb, -10, 10) / 20.0f);
    }

    // Blok bo'yicha yuqori tezlikda DSP va DMA uzatish
    void processAndOutput(int16_t* samples, int sampleCount) {
        for (int i = 0; i < sampleCount; i += 2) {
            float inL = (float)samples[i];
            float inR = (float)samples[i + 1];

            // Bass filtri (~250Hz @ 48kHz)
            lpL += 0.032f * (inL - lpL);
            lpR += 0.032f * (inR - lpR);

            // Treble filtri (~3kHz @ 48kHz)
            hpL = 0.72f * (hpL + inL - prevInL);
            hpR = 0.72f * (hpR + inR - prevInR);
            prevInL = inL;
            prevInR = inR;

            float midL = inL - lpL - hpL;
            float midR = inR - lpR - hpR;

            float outL = (lpL * bassGain + midL + hpL * trebleGain) * volume;
            float outR = (lpR * bassGain + midR + hpR * trebleGain) * volume;

            outL = softLimit(outL / 32768.0f) * 32767.0f;
            outR = softLimit(outR / 32768.0f) * 32767.0f;

            samples[i]     = (int16_t)constrain((int)outL, -32768, 32767);
            samples[i + 1] = (int16_t)constrain((int)outR, -32768, 32767);
        }

        ConsumeSamples(samples, sampleCount);
    }

    void playBeep(int freq = 440, int durationMs = 250) {
        int totalSamples = (48000 * durationMs) / 1000;
        int16_t buf[128];
        for (int s = 0; s < totalSamples; s += 64) {
            for (int i = 0; i < 128; i += 2) {
                float t = (float)(s + i / 2) / 48000.0f;
                int16_t sample = (int16_t)(sinf(2.0f * 3.14159f * freq * t) * 16000.0f * volume);
                buf[i] = sample;
                buf[i + 1] = sample;
            }
            ConsumeSamples(buf, 128);
            vTaskDelay(pdMS_TO_TICKS(1));
        }
    }

private:
    inline float softLimit(float x) {
        if (x > 1.0f) return 1.0f;
        if (x < -1.0f) return -1.0f;
        return x - (x * x * x) * 0.333333f;
    }
};

EqualizerDAC* dacOut = nullptr;

// ==============================================================================
// 3. ULTRA-PAST KECHIKISHLI RING BUFFER (~60ms)
// ==============================================================================
class AudioRingBuffer {
private:
    uint8_t* buffer;
    size_t capacity;
    volatile size_t head;
    volatile size_t tail;
    portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;

public:
    AudioRingBuffer(size_t size) : capacity(size), head(0), tail(0) {
        buffer = (uint8_t*)malloc(size);
    }

    size_t available() {
        portENTER_CRITICAL(&mux);
        size_t h = head;
        size_t t = tail;
        portEXIT_CRITICAL(&mux);
        if (h >= t) return h - t;
        return capacity - (t - h);
    }

    size_t space() {
        return capacity - 1 - available();
    }

    size_t write(const uint8_t* data, size_t len) {
        size_t written = 0;
        while (written < len) {
            portENTER_CRITICAL(&mux);
            size_t nextHead = (head + 1) % capacity;
            if (nextHead == tail) {
                portEXIT_CRITICAL(&mux);
                break;
            }
            buffer[head] = data[written++];
            head = nextHead;
            portEXIT_CRITICAL(&mux);
        }
        return written;
    }

    size_t read(uint8_t* data, size_t len) {
        size_t bytesRead = 0;
        while (bytesRead < len) {
            portENTER_CRITICAL(&mux);
            if (head == tail) {
                portEXIT_CRITICAL(&mux);
                break;
            }
            data[bytesRead++] = buffer[tail];
            tail = (tail + 1) % capacity;
            portEXIT_CRITICAL(&mux);
        }
        return bytesRead;
    }

    void skip(size_t len) {
        portENTER_CRITICAL(&mux);
        size_t avail = (head >= tail) ? (head - tail) : (capacity - (tail - head));
        if (len > avail) len = avail;
        tail = (tail + len) % capacity;
        portEXIT_CRITICAL(&mux);
    }

    void clear() {
        portENTER_CRITICAL(&mux);
        head = 0;
        tail = 0;
        portEXIT_CRITICAL(&mux);
    }
};

AudioRingBuffer ringBuf(12288); // 12 KB bufer

volatile bool shouldReconnect = false;
int currentVol = 85;
int currentBass = 0;
int currentTreble = 0;
unsigned long lastDataTime = 0;

void silenceDac() {
    dacWrite(25, 128); // GPIO 25 sukunat
    dacWrite(26, 128); // GPIO 26 sukunat
}

// URL tahlil qilish
void parseUrl(const String& url, String& host, int& port, String& path) {
    String u = url;
    if (u.startsWith("http://")) {
        u = u.substring(7);
    }
    int slashIdx = u.indexOf('/');
    String hostPort;
    if (slashIdx >= 0) {
        hostPort = u.substring(0, slashIdx);
        path = u.substring(slashIdx);
    } else {
        hostPort = u;
        path = "/";
    }

    int colonIdx = hostPort.indexOf(':');
    if (colonIdx >= 0) {
        host = hostPort.substring(0, colonIdx);
        port = hostPort.substring(colonIdx + 1).toInt();
    } else {
        host = hostPort;
        port = 80;
    }
}

// ==============================================================================
// 4. STREAM ULANISH VA QABUL QILISH
// ==============================================================================
void connectToStream() {
    streamClient.stop();
    ringBuf.clear();

    if (audioServerUrl.length() < 7) {
        vTaskDelay(pdMS_TO_TICKS(1000));
        return;
    }

    String host;
    int port;
    String path;
    parseUrl(audioServerUrl, host, port, path);

    Serial.printf("\nStream serverga ulanmoqda: %s:%d%s\n", host.c_str(), port, path.c_str());
    if (!streamClient.connect(host.c_str(), port, 2500)) {
        Serial.println("❌ Ulanib bo'lmadi! Brauzerdan yoki ilovadan manzilni tekshiring.");
        vTaskDelay(pdMS_TO_TICKS(2000));
        shouldReconnect = true;
        return;
    }

    streamClient.setNoDelay(true);
    streamClient.printf("GET %s HTTP/1.0\r\nHost: %s:%d\r\nConnection: keep-alive\r\n\r\n",
                        path.c_str(), host.c_str(), port);

    unsigned long start = millis();
    bool inHeader = true;
    String line = "";
    while (streamClient.connected() && millis() - start < 3000 && inHeader) {
        if (streamClient.available()) {
            char c = streamClient.read();
            if (c == '\n') {
                if (line.length() <= 1) {
                    inHeader = false;
                    break;
                }
                line = "";
            } else if (c != '\r') {
                line += c;
            }
        } else {
            vTaskDelay(pdMS_TO_TICKS(1));
        }
    }

    if (inHeader) {
        Serial.println("❌ HTTP javob olinmadi!");
        streamClient.stop();
        shouldReconnect = true;
        return;
    }

    // WAV sarlavhasi
    uint8_t wavHeader[44];
    size_t hdrRead = 0;
    start = millis();
    while (streamClient.connected() && millis() - start < 1500 && hdrRead < 44) {
        if (streamClient.available()) {
            wavHeader[hdrRead++] = streamClient.read();
        } else {
            vTaskDelay(pdMS_TO_TICKS(1));
        }
    }

    if (hdrRead >= 4 && wavHeader[0] == 'R' && wavHeader[1] == 'I' && wavHeader[2] == 'F' && wavHeader[3] == 'F') {
        Serial.println("✅ WAV sarlavhasi aniqlandi!");
    } else {
        ringBuf.write(wavHeader, hdrRead);
    }

    lastDataTime = millis();
    Serial.println("✅ Jonli audio oqim ishga tushdi!");
}

void streamTask(void* parameter) {
    uint8_t tempBuf[512];
    while (true) {
        if (shouldReconnect || (!streamClient.connected() && audioServerUrl.length() > 6)) {
            shouldReconnect = false;
            connectToStream();
        }

        if (streamClient.connected()) {
            int avail = streamClient.available();
            if (avail > 0) {
                int toRead = min(avail, (int)sizeof(tempBuf));
                if (ringBuf.space() >= toRead) {
                    int bytesRead = streamClient.read(tempBuf, toRead);
                    if (bytesRead > 0) {
                        ringBuf.write(tempBuf, bytesRead);
                        lastDataTime = millis();
                    }
                } else {
                    vTaskDelay(pdMS_TO_TICKS(2));
                }
            } else {
                vTaskDelay(pdMS_TO_TICKS(1));
                if (millis() - lastDataTime > 5000 && !streamClient.connected()) {
                    shouldReconnect = true;
                }
            }
        } else {
            vTaskDelay(pdMS_TO_TICKS(500));
        }
    }
}

void audioTask(void* parameter) {
    const int BLOCK_SAMPLES = 128;
    const int BLOCK_BYTES = BLOCK_SAMPLES * sizeof(int16_t);
    int16_t block[BLOCK_SAMPLES];
    bool prebuffering = true;

    while (true) {
        if (prebuffering) {
            if (ringBuf.available() >= 2048) {
                prebuffering = false;
            } else {
                vTaskDelay(pdMS_TO_TICKS(2));
                continue;
            }
        }

        if (ringBuf.available() > 6144) {
            ringBuf.skip(BLOCK_BYTES);
        }

        if (ringBuf.read((uint8_t*)block, BLOCK_BYTES) == BLOCK_BYTES) {
            dacOut->processAndOutput(block, BLOCK_SAMPLES);
        } else {
            memset(block, 0, BLOCK_BYTES);
            dacOut->ConsumeSamples(block, BLOCK_SAMPLES);
            if (ringBuf.available() < 1024) {
                prebuffering = true;
            }
            vTaskDelay(pdMS_TO_TICKS(1));
        }
    }
}

// ==============================================================================
// 5. SMARTFON VA BRAUZER WEB BOSHQARUV PANELI (2-VARIANT)
// ==============================================================================
void setupWebServer() {
    // 1. Ekvalayzer va ovoz
    server.on("/set", HTTP_GET, []() {
        if (server.hasArg("vol")) currentVol = server.arg("vol").toInt();
        if (server.hasArg("bass")) currentBass = server.arg("bass").toInt();
        if (server.hasArg("treble")) currentTreble = server.arg("treble").toInt();

        dacOut->setParams(currentVol, currentBass, currentTreble);
        prefs.putInt("vol", currentVol);
        prefs.putInt("bass", currentBass);
        prefs.putInt("treble", currentTreble);

        server.send(200, "text/plain", "OK");
    });

    // 2. Stream URL o'rnatish
    server.on("/stream", HTTP_GET, []() {
        if (server.hasArg("url")) {
            audioServerUrl = server.arg("url");
            prefs.putString("url", audioServerUrl);
            shouldReconnect = true;
            server.send(200, "text/plain", "OK: " + audioServerUrl);
            Serial.println("Yangi URL o'rnatildi: " + audioServerUrl);
        } else {
            server.send(400, "text/plain", "URL yo'q");
        }
    });

    // 3. Test ovozi
    server.on("/test", HTTP_GET, []() {
        dacOut->playBeep(523, 200); // Do
        vTaskDelay(pdMS_TO_TICKS(50));
        dacOut->playBeep(659, 200); // Mi
        vTaskDelay(pdMS_TO_TICKS(50));
        dacOut->playBeep(784, 300); // Sol
        server.send(200, "text/plain", "Test ovozi yangradi");
    });

    // 4. Status JSON
    server.on("/status", HTTP_GET, []() {
        String json = "{\"online\":true,\"ip\":\"" + WiFi.localIP().toString() +
                      "\",\"gateway\":\"" + WiFi.gatewayIP().toString() +
                      "\",\"vol\":" + String(currentVol) +
                      ",\"bass\":" + String(currentBass) +
                      ",\"treble\":" + String(currentTreble) +
                      ",\"stream_connected\":" + String(streamClient.connected() ? "true" : "false") +
                      ",\"url\":\"" + audioServerUrl + "\"}";
        server.send(200, "application/json", json);
    });

    // 5. Brauzer Boshqaruv Paneli (To'liq Oq rangli zamonaviy veb-interfeys)
    server.on("/", HTTP_GET, []() {
        String gateway = WiFi.gatewayIP().toString();
        String html = "<!DOCTYPE html><html lang='uz'><head><meta charset='utf-8'>"
                      "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                      "<title>ESP32 AI Kalonka Paneli</title>"
                      "<style>"
                      "*{box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;margin:0;padding:0;}"
                      "body{background:#f8fafc;color:#1e293b;padding:20px;display:flex;justify-content:center;align-items:center;min-height:100vh;}"
                      ".card{background:#ffffff;border:1px solid #e2e8f0;border-radius:18px;padding:24px;width:100%;max-width:440px;box-shadow:0 10px 25px rgba(0,0,0,0.05);}"
                      "h2{font-size:20px;color:#0f172a;display:flex;align-items:center;gap:8px;margin-bottom:4px;}"
                      ".sub{font-size:12px;color:#64748b;margin-bottom:18px;}"
                      ".badge{display:inline-block;padding:4px 10px;border-radius:20px;font-size:11px;font-weight:600;margin-bottom:12px;}"
                      ".badge-ok{background:#dcfce7;color:#166534;}"
                      ".info-box{background:#f1f5f9;border-radius:12px;padding:12px;font-size:12px;margin-bottom:16px;line-height:1.6;}"
                      ".label-row{display:flex;justify-content:space-between;font-size:13px;font-weight:600;margin-top:14px;margin-bottom:4px;}"
                      "input[type=range]{width:100%;accent-color:#2563eb;cursor:pointer;height:6px;}"
                      "input[type=text]{width:100%;padding:10px 12px;border:1px solid #cbd5e1;border-radius:10px;font-size:13px;outline:none;margin-top:6px;}"
                      "input[type=text]:focus{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,0.1);}"
                      ".btn{display:block;width:100%;padding:12px;border:none;border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;margin-top:12px;transition:all 0.15s;text-align:center;}"
                      ".btn-primary{background:#2563eb;color:#fff;}.btn-primary:hover{background:#1d4ed8;}"
                      ".btn-success{background:#10b981;color:#fff;}.btn-success:hover{background:#059669;}"
                      ".btn-outline{background:#fff;border:1px solid #cbd5e1;color:#334155;}.btn-outline:hover{background:#f8fafc;}"
                      "</style></head><body><div class='card'>"
                      "<h2>🔊 ESP32 AI Kalonka</h2>"
                      "<p class='sub'>Hamshiralar Simulyatsiya Tizimi</p>"
                      "<span class='badge badge-ok'>● Wi-Fi: " + String(default_ssid) + "</span>"
                      "<div class='info-box'>"
                      "📍 <b>Kalonka IP:</b> " + WiFi.localIP().toString() + "<br>"
                      "📱 <b>Smartfon (Gateway) IP:</b> " + gateway + "<br>"
                      "🔗 <b>Joriy URL:</b> <span id='u_txt'>" + (audioServerUrl.length() > 0 ? audioServerUrl : "Ulanmagan") + "</span>"
                      "</div>"
                      "<button class='btn btn-success' onclick='connectHotspot()'>⚡ Smartfonga To'g'ridan-to'g'ri Ulanish</button>"
                      "<button class='btn btn-outline' onclick='testSound()'>🔔 Dinamikni Tekshirish (Test Ovoz)</button>"
                      "<hr style='border:0;border-top:1px solid #f1f5f9;margin:18px 0;'>"
                      "<div class='label-row'><span>🔊 Ovoz balandligi</span><span id='v'>" + String(currentVol) + "%</span></div>"
                      "<input type='range' min='0' max='100' value='" + String(currentVol) + "' oninput='upd()' id='vol'>"
                      "<div class='label-row'><span>🎸 Bass (Past chastota)</span><span id='b'>" + String(currentBass) + " dB</span></div>"
                      "<input type='range' min='-10' max='10' value='" + String(currentBass) + "' oninput='upd()' id='bass'>"
                      "<div class='label-row'><span>🎼 Treble (Yuqori chastota)</span><span id='t'>" + String(currentTreble) + " dB</span></div>"
                      "<input type='range' min='-10' max='10' value='" + String(currentTreble) + "' oninput='upd()' id='treble'>"
                      "<div style='margin-top:16px;'><label style='font-size:12px;font-weight:600;color:#64748b;'>Qo'lda Stream URL kiritish:</label>"
                      "<input type='text' id='custom_url' placeholder='http://" + gateway + ":5901/stream/swyh.wav' value='" + audioServerUrl + "'>"
                      "<button class='btn btn-primary' onclick='setUrl()'>Oqimni Ulash</button></div>"
                      "</div>"
                      "<script>"
                      "function upd(){var v=document.getElementById('vol').value;var b=document.getElementById('bass').value;var t=document.getElementById('treble').value;"
                      "document.getElementById('v').innerText=v+'%';document.getElementById('b').innerText=b+' dB';document.getElementById('t').innerText=t+' dB';"
                      "fetch('/set?vol='+v+'&bass='+b+'&treble='+t);}"
                      "function connectHotspot(){var url='http://" + gateway + ":5901/stream/swyh.wav';document.getElementById('custom_url').value=url;fetch('/stream?url='+encodeURIComponent(url)).then(()=>alert('Ulandi: '+url));}"
                      "function setUrl(){var url=document.getElementById('custom_url').value;if(url)fetch('/stream?url='+encodeURIComponent(url)).then(()=>alert('Yangi URL saqlandi'));}"
                      "function testSound(){fetch('/test').then(()=>alert('Test signali yuborildi'));}"
                      "</script></body></html>";
        server.send(200, "text/html", html);
    });

    server.begin();
}

// ==============================================================================
// 6. SETUP VA LOOP
// ==============================================================================
void setup() {
    Serial.begin(115200);
    delay(500);

    silenceDac();

    prefs.begin("speaker_cfg", false);
    currentVol = prefs.getInt("vol", 85);
    currentBass = prefs.getInt("bass", 0);
    currentTreble = prefs.getInt("treble", 0);
    audioServerUrl = prefs.getString("url", "");

    dacOut = new EqualizerDAC();
    dacOut->SetRate(48000);
    dacOut->SetChannels(2);
    dacOut->begin();
    dacOut->setParams(currentVol, currentBass, currentTreble);

    WiFi.mode(WIFI_STA);
    WiFi.begin(default_ssid, default_password);
    Serial.println("\n==============================================");
    Serial.println("  ESP32 AI Kalonka (2-Variant: Web Boshqaruv)");
    Serial.println("==============================================");
    Serial.print("Wi-Fi ga ulanmoqda...");

    int retry = 0;
    while (WiFi.status() != WL_CONNECTED && retry < 25) {
        delay(500);
        Serial.print(".");
        retry++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n✅ Wi-Fi ulandi!");
        Serial.print("🌐 ESP32 Web Panel manzili: http://");
        Serial.println(WiFi.localIP());
        Serial.print("📱 Smartfon Hotspot IP: ");
        Serial.println(WiFi.gatewayIP());

        // Agar URL kiritilmagan bo'lsa, avtomatik Hotspot IP ga sozlash
        if (audioServerUrl.length() == 0) {
            audioServerUrl = "http://" + WiFi.gatewayIP().toString() + ":5901/stream/swyh.wav";
            Serial.println("Auto-stream manzili: " + audioServerUrl);
        }
    }

    setupWebServer();

    // 1. Tarmoq oqimi (Core 0)
    xTaskCreatePinnedToCore(streamTask, "StreamTask", 8192, NULL, 3, NULL, 0);

    // 2. Audio DAC ijro (Core 1)
    xTaskCreatePinnedToCore(audioTask, "AudioTask", 8192, NULL, 4, NULL, 1);

    delay(200);
    shouldReconnect = true;
}

void loop() {
    server.handleClient();
    delay(2);
}
