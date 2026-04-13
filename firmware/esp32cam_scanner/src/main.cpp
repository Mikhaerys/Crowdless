#include <Arduino.h>
#include "esp_camera.h"
#include <ESP32QRCodeReader.h>

// Optional LED flash on many ESP32-CAM boards.
static const int FLASH_LED_PIN = 4;

// Command channel with central ESP32.
// Change to Serial1/Serial2 if your wiring uses another UART.
#define CTRL_SERIAL Serial

// Serial protocol commands received from central ESP32.
static const char *CMD_CAPTURE_QR = "CAPTURE_QR";
static const char *CMD_CAPTURE_DOC = "CAPTURE_DOC";
static const char *CMD_PING = "PING";

// Chunk size for streaming image bytes over serial.
static const size_t SERIAL_CHUNK_SIZE = 512;

ESP32QRCodeReader qrReader(CAMERA_MODEL_AI_THINKER);
bool qrSetupOk = false;
bool qrWorkerRunning = false;

bool initQrReader();
bool startQrWorker();
void stopQrWorker();
bool captureQrAndSend();
bool captureDocumentAndSend();
bool captureAndSend(const char *typeLabel, framesize_t frameSize, int jpegQuality,
                    bool flashOn);
void sendQrPayload(const QRCodeData &qrCodeData);
void sendLog(const char *level, const char *detail);
void handleCommand(const String &command);
void sendStatus(const char *status, const char *detail = nullptr);
void setFlash(bool on);

void setup()
{
    pinMode(FLASH_LED_PIN, OUTPUT);
    setFlash(false);

    CTRL_SERIAL.begin(115200);
    delay(250);

    if (!initQrReader())
    {
        sendStatus("ERROR", "QR_READER_SETUP_FAILED");
        return;
    }

    sendStatus("READY", "ESP32CAM_SCANNER");
}

void loop()
{
    if (CTRL_SERIAL.available())
    {
        String command = CTRL_SERIAL.readStringUntil('\n');
        command.trim();

        if (command.length() > 0)
        {
            handleCommand(command);
        }
    }
}

bool initQrReader()
{
    if (!psramFound())
    {
        sendStatus("ERROR", "PSRAM_REQUIRED");
        return false;
    }

    QRCodeReaderSetupErr setupErr = qrReader.setup();
    if (setupErr != SETUP_OK)
    {
        return false;
    }

    qrSetupOk = true;
    return startQrWorker();
}

bool startQrWorker()
{
    if (!qrSetupOk)
    {
        return false;
    }

    if (!qrWorkerRunning)
    {
        qrReader.beginOnCore(1);
        qrWorkerRunning = true;
    }

    return true;
}

void stopQrWorker()
{
    if (qrWorkerRunning)
    {
        qrReader.end();
        qrWorkerRunning = false;
        delay(30);
    }
}

bool captureQrAndSend()
{
    if (!startQrWorker())
    {
        sendStatus("ERROR", "QR_READER_NOT_READY");
        return false;
    }

    const unsigned long maxWaitMs = 10000;
    const unsigned long startMs = millis();
    unsigned int invalidDetections = 0;

    // Turn on flash while scanning QR to improve decode success in low light.
    setFlash(true);
    delay(80);

    while (millis() - startMs < maxWaitMs)
    {
        // Reinitialize qrCodeData on each loop iteration to avoid stale data.
        QRCodeData qrCodeData = {};
        if (qrReader.receiveQrCode(&qrCodeData, 250))
        {
            if (qrCodeData.valid)
            {
                setFlash(false);
                sendQrPayload(qrCodeData);
                return true;
            }

            invalidDetections++;
            sendLog("WARN", "QR_INVALID_RETRY");
        }
    }

    setFlash(false);
    if (invalidDetections > 0)
    {
        sendStatus("ERROR", "QR_INVALID_TIMEOUT");
    }
    else
    {
        sendStatus("ERROR", "QR_TIMEOUT");
    }

    return false;
}

bool captureDocumentAndSend()
{
    // Keep document capture in camera's current stable mode set by QR reader.
    return captureAndSend("DOC", FRAMESIZE_QVGA, 0, true);
}

bool captureAndSend(const char *typeLabel, framesize_t frameSize, int jpegQuality,
                    bool flashOn)
{
    stopQrWorker();

    (void)frameSize;
    (void)jpegQuality;

    sensor_t *sensor = esp_camera_sensor_get();
    if (sensor == nullptr)
    {
        sendStatus("ERROR", "SENSOR_NOT_FOUND");
        startQrWorker();
        return false;
    }

    if (flashOn)
    {
        setFlash(true);
        delay(120);
    }

    camera_fb_t *fb = esp_camera_fb_get();

    if (flashOn)
    {
        setFlash(false);
    }

    if (fb == nullptr)
    {
        sendStatus("ERROR", "CAPTURE_FAILED");
        startQrWorker();
        return false;
    }

    CTRL_SERIAL.printf("IMG_BEGIN,%s,%u,%u,%u,%u\n", typeLabel,
                       static_cast<unsigned>(fb->len),
                       static_cast<unsigned>(fb->width),
                       static_cast<unsigned>(fb->height),
                       static_cast<unsigned>(fb->format));

    size_t offset = 0;
    while (offset < fb->len)
    {
        size_t remaining = fb->len - offset;
        size_t toSend = remaining > SERIAL_CHUNK_SIZE ? SERIAL_CHUNK_SIZE : remaining;
        CTRL_SERIAL.write(fb->buf + offset, toSend);
        offset += toSend;
    }

    CTRL_SERIAL.println("IMG_END");
    esp_camera_fb_return(fb);
    startQrWorker();

    sendStatus("OK", typeLabel);
    return true;
}

void sendQrPayload(const QRCodeData &qrCodeData)
{
    if (!qrCodeData.valid)
    {
        sendStatus("ERROR", "QR_INVALID");
        return;
    }

    CTRL_SERIAL.printf("QR_BEGIN,%u,%u\n", static_cast<unsigned>(qrCodeData.payloadLen),
                       qrCodeData.valid ? 1u : 0u);
    CTRL_SERIAL.write(qrCodeData.payload, qrCodeData.payloadLen);
    CTRL_SERIAL.println();
    CTRL_SERIAL.println("QR_END");
    sendStatus("OK", "QR");
}

void sendLog(const char *level, const char *detail)
{
    CTRL_SERIAL.printf("LOG,%s,%s\n", level, detail);
}

void handleCommand(const String &command)
{
    if (command.equalsIgnoreCase(CMD_CAPTURE_QR))
    {
        captureQrAndSend();
        return;
    }

    if (command.equalsIgnoreCase(CMD_CAPTURE_DOC))
    {
        captureDocumentAndSend();
        return;
    }

    if (command.equalsIgnoreCase(CMD_PING))
    {
        sendStatus("PONG", "ESP32CAM_SCANNER");
        return;
    }

    sendStatus("ERROR", "UNKNOWN_COMMAND");
}

void sendStatus(const char *status, const char *detail)
{
    if (detail == nullptr)
    {
        CTRL_SERIAL.printf("STATUS,%s\n", status);
    }
    else
    {
        CTRL_SERIAL.printf("STATUS,%s,%s\n", status, detail);
    }
}

void setFlash(bool on)
{
    digitalWrite(FLASH_LED_PIN, on ? HIGH : LOW);
}