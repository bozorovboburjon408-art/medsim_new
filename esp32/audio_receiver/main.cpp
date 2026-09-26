#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <driver/i2s.h>
#include <ArduinoJson.h> // Install via Library Manager
#include "config.h"

WebServer server(HTTP_PORT);
int currentVolume = 50;
bool isPlaying = false;
unsigned long lastWatchdogReset = 0;

void setupI2S() {
  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
    .sample_rate = 16000,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = 64,
    .use_apll = false,
    .tx_desc_auto_clear = true,
    .fixed_mclk = 0
  };

  i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_BCK_PIN,
    .ws_io_num = I2S_WS_PIN,
    .data_out_num = I2S_DATA_PIN,
    .data_in_num = I2S_PIN_NO_CHANGE
  };

  i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
  i2s_set_pin(I2S_NUM_0, &pin_config);
  i2s_set_clk(I2S_NUM_0, 16000, I2S_BITS_PER_SAMPLE_16BIT, I2S_CHANNEL_MONO);
}

void handleHealth() {
  StaticJsonDocument<256> doc;
  doc["status"] = "ok";
  doc["mannequin"] = MANNEQUIN_NAME;
  doc["ip"] = WiFi.localIP().toString();
  doc["uptime"] = millis();
  doc["free_memory"] = ESP.getFreeHeap();

  String response;
  serializeJson(doc, response);
  server.send(200, "application/json", response);
}

void handlePlay() {
  if (server.method() != HTTP_POST) {
    server.send(405, "text/plain", "Method Not Allowed");
    return;
  }

  isPlaying = true;
  digitalWrite(LED_PIN, HIGH);

  // In a real application, you would read the POST payload (audio data)
  // chunk by chunk and write it to the I2S driver:
  // size_t bytes_written;
  // i2s_write(I2S_NUM_0, data, length, &bytes_written, portMAX_DELAY);

  server.send(200, "application/json", "{\"status\": \"playing\"}");
  
  // Simulate end of play
  delay(100); 
  digitalWrite(LED_PIN, LOW);
  isPlaying = false;
}

void handleStop() {
  isPlaying = false;
  i2s_zero_dma_buffer(I2S_NUM_0);
  server.send(200, "application/json", "{\"status\": \"stopped\"}");
}

void handleVolume() {
  if (server.hasArg("level")) {
    int level = server.arg("level").toInt();
    if (level >= 0 && level <= 100) {
      currentVolume = level;
      server.send(200, "application/json", "{\"status\": \"success\", \"volume\": " + String(currentVolume) + "}");
    } else {
      server.send(400, "application/json", "{\"status\": \"error\", \"message\": \"Invalid volume\"}");
    }
  } else {
    server.send(400, "application/json", "{\"status\": \"error\", \"message\": \"Missing level param\"}");
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  // Connect to Wi-Fi
  Serial.print("Connecting to WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  if (USE_STATIC_IP) {
    IPAddress ip, gateway, subnet;
    ip.fromString(STATIC_IP);
    gateway.fromString(GATEWAY);
    subnet.fromString(SUBNET);
    WiFi.config(ip, gateway, subnet);
  }

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected.");
  Serial.println(WiFi.localIP());

  setupI2S();

  server.on("/health", HTTP_GET, handleHealth);
  server.on("/play", HTTP_POST, handlePlay);
  server.on("/stop", HTTP_POST, handleStop);
  server.on("/volume", HTTP_GET, handleVolume);

  server.begin();
  Serial.println("HTTP server started");
}

void loop() {
  server.handleClient();
  
  // Basic watchdog timer to reset if stuck
  if (millis() - lastWatchdogReset > 10000) {
    // Reset watchdog logic
    lastWatchdogReset = millis();
  }
}
