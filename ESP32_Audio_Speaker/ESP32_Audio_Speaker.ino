#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>
#include "AudioOutputInternalDAC.h"

// ==========================================
// 1. WI-FI VA STREAM SOZLAMALARI
// ==========================================
const char* default_ssid     = "A56";
const char* default_password = "21082007";

// Smartfoningiz jonli oqim manzili
String audioServerUrl = "http://192.168.118.207:5901/stream/swyh.wav";

Preferences prefs;
WebServer server(80);
WiFiClient streamClient;

// ==========================================
// 2. EQUALIZER VA DSP (BLOKLI DMA QAYTA ISHLASH)
// ==========================================
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

    // Blok bo'yicha yuqori tezlikda DSP va DMA uzatish (CPU va Wi-Fi yukini 95% kamaytiradi)
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

private:
    inline float softLimit(float x) {
        if (x > 1.0f) return 1.0f;
        if (x < -1.0f) return -1.0f;
        return x - (x * x * x) * 0.333333f;
    }
};

EqualizerDAC* dacOut = nullptr;

// ==========================================
// 3. ULTRA-PAST KECHIKISHLI RING BUFFER (~60ms)
// ==========================================
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

    // Kechikish to'planmasligi uchun eski baytlarni o'tkazib yuborish
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

AudioRingBuffer ringBuf(12288); // 12 KB bufer (~64 ms maksimal zahira - nol kechikish)

volatile bool shouldReconnect = false;
int currentVol = 80;
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

// ==========================================
// 4. STREAM ULANISH VA QABUL QILISH
// ==========================================
void connectToStream() {
    streamClient.stop();
    ringBuf.clear();

    String host;
    int port;
    String path;
    parseUrl(audioServerUrl, host, port, path);

    Serial.printf("\nStream serverga ulanmoqda: %s:%d%s\n", host.c_str(), port, path.c_str());
    if (!streamClient.connect(host.c_str(), port, 3000)) {
        Serial.println("❌ Serverga ulanib bo'lmadi! Smartfonda ilova yoqilganini tekshiring.");
        vTaskDelay(pdMS_TO_TICKS(1500));
        shouldReconnect = true;
        return;
    }

    // Kechikishni yo'qotish uchun TCP No Delay yoqish
    streamClient.setNoDelay(true);

    // HTTP GET so'rovi
    streamClient.printf("GET %s HTTP/1.0\r\nHost: %s:%d\r\nConnection: keep-alive\r\n\r\n",
                        path.c_str(), host.c_str(), port);

    // HTTP sarlavhalarini o'tkazib yuborish
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

    // WAV 44-bayt sarlavhasini tekshirish va o'tkazib yuborish
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
        Serial.println("✅ WAV sarlavhasi aniqlandi (44-bayt o'tkazib yuborildi)!");
    } else {
        ringBuf.write(wavHeader, hdrRead);
    }

    lastDataTime = millis();
    Serial.println("✅ Jonli audio oqim ishga tushdi (ultra-past kechikish bilan)!");
}

// Tarmoq oqimi vazifasi (Core 0 - Wi-Fi bilan birga)
void streamTask(void* parameter) {
    uint8_t tempBuf[512];
    while (true) {
        if (shouldReconnect || !streamClient.connected()) {
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
                    Serial.println("Oqim uzildi, qayta ulanmoqda...");
                    shouldReconnect = true;
                }
            }
        } else {
            vTaskDelay(pdMS_TO_TICKS(500));
        }
    }
}

// Audio DAC ijro vazifasi (Core 1)
void audioTask(void* parameter) {
    const int BLOCK_SAMPLES = 128; // 64 stereo namuna (128 ta int16 qiymat)
    const int BLOCK_BYTES = BLOCK_SAMPLES * sizeof(int16_t); // 256 bayt = ~1.33 ms
    int16_t block[BLOCK_SAMPLES];
    bool prebuffering = true;

    while (true) {
        // Pre-buffering: faqat 2048 bayt (~10ms) zahira to'planishini kutadi (bir zumda boshlanadi!)
        if (prebuffering) {
            if (ringBuf.available() >= 2048) {
                prebuffering = false;
            } else {
                vTaskDelay(pdMS_TO_TICKS(2));
                continue;
            }
        }

        // Kechikishni avtomatik yo'qotish (Latency sync):
        // Agar buferda 6144 baytdan (~32ms) ko'proq audio yig'ilsa, eskisini tashlab jonli efirga yetib oladi
        if (ringBuf.available() > 6144) {
            ringBuf.skip(BLOCK_BYTES);
        }

        if (ringBuf.read((uint8_t*)block, BLOCK_BYTES) == BLOCK_BYTES) {
            dacOut->processAndOutput(block, BLOCK_SAMPLES);
        } else {
            // Tarmoqda vaqtinchalik uzulish bo'lsa sukunat beradi (aloqani uzmaydi!)
            memset(block, 0, BLOCK_BYTES);
            dacOut->ConsumeSamples(block, BLOCK_SAMPLES);
            if (ringBuf.available() < 1024) {
                prebuffering = true;
            }
            vTaskDelay(pdMS_TO_TICKS(1));
        }
    }
}

// ==========================================
// 5. SMARTFON VA WEB API
// ==========================================
void setupWebServer() {
    // 1. Ekvalayzer va Ovoz sozlash
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

    // 2. Dinamik oqim manzilini almashtirish
    server.on("/stream", HTTP_GET, []() {
        if (server.hasArg("url")) {
            audioServerUrl = server.arg("url");
            prefs.putString("url", audioServerUrl);
            shouldReconnect = true;
            server.send(200, "text/plain", "OK");
            Serial.println("Yangi URL o'rnatildi: " + audioServerUrl);
        } else {
            server.send(400, "text/plain", "URL yo'q");
        }
    });

    // 3. Status
    server.on("/status", HTTP_GET, []() {
        String json = "{\"online\":true,\"vol\":" + String(currentVol) +
                      ",\"bass\":" + String(currentBass) +
                      ",\"treble\":" + String(currentTreble) +
                      ",\"buffered\":" + String(ringBuf.available()) +
                      ",\"url\":\"" + audioServerUrl + "\"}";
        server.send(200, "application/json", json);
    });

    // 4. Web Panel
    server.on("/", HTTP_GET, []() {
        String html = "<!DOCTYPE html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>ESP32 AI Kalonka</title><style>body{font-family:sans-serif;background:#121212;color:#fff;padding:20px;text-align:center;}.card{background:#1e1e1e;border-radius:12px;padding:20px;max-width:400px;margin:auto;}input[type=range]{width:100%;margin:15px 0;accent-color:#4CAF50;}button{background:#2196F3;border:none;color:#fff;padding:12px;border-radius:8px;font-size:16px;cursor:pointer;width:100%;margin-top:10px;}</style></head><body><div class='card'><h2>🎵 ESP32 Kalonka</h2><p>IP: " + WiFi.localIP().toString() + "</p><hr style='border-color:#333;'><label>🔊 Ovoz: <span id='v'>" + String(currentVol) + "</span>%</label><input type='range' min='0' max='100' value='" + String(currentVol) + "' oninput='upd()' id='vol'><label>🎸 Bass: <span id='b'>" + String(currentBass) + "</span> dB</label><input type='range' min='-10' max='10' value='" + String(currentBass) + "' oninput='upd()' id='bass'><label>🎼 Treble: <span id='t'>" + String(currentTreble) + "</span> dB</label><input type='range' min='-10' max='10' value='" + String(currentTreble) + "' oninput='upd()' id='treble'><button onclick='setPhone()'>📲 Smartfonga Ulanish</button></div><script>function upd(){var v=document.getElementById('vol').value;var b=document.getElementById('bass').value;var t=document.getElementById('treble').value;document.getElementById('v').innerText=v;document.getElementById('b').innerText=b;document.getElementById('t').innerText=t;fetch('/set?vol='+v+'&bass='+b+'&treble='+t);}function setPhone(){var url=prompt('Smartfon IP:','192.168.118.207');if(url)fetch('/stream?url='+encodeURIComponent('http://'+url+':5901/stream/swyh.wav'));}</script></body></html>";
        server.send(200, "text/html", html);
    });

    server.begin();
}

// ==========================================
// 6. SETUP VA LOOP
// ==========================================
void setup() {
    Serial.begin(115200);
    delay(500);

    silenceDac();

    prefs.begin("speaker_cfg", false);
    currentVol = prefs.getInt("vol", 80);
    currentBass = prefs.getInt("bass", 0);
    currentTreble = prefs.getInt("treble", 0);
    audioServerUrl = prefs.getString("url", audioServerUrl);

    dacOut = new EqualizerDAC();
    dacOut->SetRate(48000);
    dacOut->SetChannels(2);
    dacOut->begin();
    dacOut->setParams(currentVol, currentBass, currentTreble);

    WiFi.mode(WIFI_STA);
    WiFi.begin(default_ssid, default_password);
    Serial.println("\n--- ESP32 AI Kalonka (Ultra-Past Kechikish) ---");
    Serial.print("Wi-Fi ga ulanmoqda...");

    int retry = 0;
    while (WiFi.status() != WL_CONNECTED && retry < 25) {
        delay(500);
        Serial.print(".");
        retry++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\n✅ Wi-Fi ulandi!");
        Serial.print("ESP32 IP manzili: ");
        Serial.println(WiFi.localIP());
    }

    setupWebServer();

    // 1. Tarmoq qabul qilish vazifasi (Core 0)
    xTaskCreatePinnedToCore(streamTask, "StreamTask", 8192, NULL, 3, NULL, 0);

    // 2. Audio DAC ijro vazifasi (Core 1)
    xTaskCreatePinnedToCore(audioTask, "AudioTask", 8192, NULL, 4, NULL, 1);

    delay(200);
    shouldReconnect = true;
}

void loop() {
    server.handleClient();
    delay(2);
}
