#ifndef CONFIG_H
#define CONFIG_H

// WiFi Configuration
#define WIFI_SSID "A56"
#define WIFI_PASSWORD "21082007"

// Network Configuration (Optional Static IP)
#define USE_STATIC_IP false
#define STATIC_IP "192.168.1.10"
#define GATEWAY "192.168.1.1"
#define SUBNET "255.255.255.0"

// Mannequin Settings
#define MANNEQUIN_NAME "bobo"

// HTTP Server
#define HTTP_PORT 80

// I2S Configuration
#define I2S_BCK_PIN 26
#define I2S_WS_PIN 25
#define I2S_DATA_PIN 22

// Audio Buffer
#define MAX_AUDIO_BUFFER_SIZE 4096

// Hardware Pins
#define LED_PIN 2

#endif // CONFIG_H
