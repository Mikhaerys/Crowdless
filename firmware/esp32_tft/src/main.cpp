#include <Arduino.h>
#include <HTTPClient.h>
#include <SPI.h>
#include <TFT_eSPI.h>
#include <WiFi.h>
#include <XPT2046_Touchscreen.h>
#include <cstring>
#include <lvgl.h>

#include "app_bridge.h"
#include "screens.h"
#include "ui.h"

// UART wiring between central ESP32 and ESP32-CAM.
static const int CAM_RX_PIN = 16;
static const int CAM_TX_PIN = 17;

// Keep Serial for operator console and Serial2 for ESP32-CAM link.
#define CONSOLE_SERIAL Serial
#define CAM_SERIAL Serial2

#ifndef WIFI_SSID
#define WIFI_SSID "TP-LINK_DDAE"
#endif

#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD "24890717"
#endif

#ifndef BACKEND_BASE_URL
#define BACKEND_BASE_URL "http://192.168.0.124:8000/api/v1"
#endif

static const char *CMD_CAPTURE_QR = "CAPTURE_QR";
static const char *CMD_CAPTURE_DOC = "CAPTURE_DOC";
static const char *CMD_PING = "PING";

static const unsigned long LINE_TIMEOUT_MS = 5000;
static const unsigned long QR_SCAN_TIMEOUT_MS = 15000;
static const unsigned long DOC_CAPTURE_TIMEOUT_MS = 20000;
static const uint16_t BACKEND_CONNECT_TIMEOUT_MS = 5000;
static const uint16_t BACKEND_RESPONSE_TIMEOUT_MS = 20000;

static const uint16_t TFT_HOR_RES = 320;
static const uint16_t TFT_VER_RES = 240;
static const size_t LVGL_DRAW_BUF_LINES = 20;

static const int TOUCH_IRQ_PIN = 36;
static const int TOUCH_MOSI_PIN = 32;
static const int TOUCH_MISO_PIN = 39;
static const int TOUCH_CLK_PIN = 25;
static const int TOUCH_CS_PIN = 33;

static const int TOUCH_RAW_X_MIN = 200;
static const int TOUCH_RAW_X_MAX = 3700;
static const int TOUCH_RAW_Y_MIN = 240;
static const int TOUCH_RAW_Y_MAX = 3800;

static TFT_eSPI tft = TFT_eSPI();
// Keep touch on a dedicated SPI controller to avoid colliding with TFT_eSPI VSPI state.
static SPIClass touchSpi = SPIClass(HSPI);
static XPT2046_Touchscreen touch(TOUCH_CS_PIN, TOUCH_IRQ_PIN);
static lv_display_t *gDisplay = nullptr;
static unsigned long gLastLvTickMs = 0;
static bool gUiReady = false;
static uint8_t gLvglDrawBuf[TFT_HOR_RES * LVGL_DRAW_BUF_LINES * sizeof(lv_color16_t)];

static char gBookingTicketType[16] = "ADULTOS";

void printHelp();
bool connectWifi();
void flushCamInput();
void sendCamCommand(const char *command);
bool readLineFromCam(String &line, unsigned long timeoutMs);
bool readExactBytesFromCam(size_t length, String &output, unsigned long timeoutMs);
bool discardExactBytesFromCam(size_t length, unsigned long timeoutMs);
String escapeJsonString(const String &value);
bool verifyQrWithBackend(const String &qrPayload);
bool captureQrFlow();
bool captureDocumentFlow();
void handleConsoleCommand(const String &command);
void initDisplayAndUi();
void pumpUi();
void updateBookingHints();

void tftFlushCallback(lv_display_t *display, const lv_area_t *area, uint8_t *pxMap);
void touchReadCallback(lv_indev_t *indev, lv_indev_data_t *data);

bool parseQrBeginHeader(const String &header, size_t &payloadLength, bool &isValid);
bool parseImgBeginHeader(const String &header, size_t &imageLength, String &typeLabel,
                         int &width, int &height, int &format);

void setup()
{
    CONSOLE_SERIAL.begin(115200);
    CAM_SERIAL.begin(115200, SERIAL_8N1, CAM_RX_PIN, CAM_TX_PIN);
    delay(250);

    initDisplayAndUi();

    CONSOLE_SERIAL.println();
    CONSOLE_SERIAL.println("Crowdless central ESP32 ready");
    printHelp();

    connectWifi();

    flushCamInput();
    sendCamCommand(CMD_PING);
}

void loop()
{
    pumpUi();

    if (CONSOLE_SERIAL.available())
    {
        String command = CONSOLE_SERIAL.readStringUntil('\n');
        command.trim();

        if (command.length() > 0)
        {
            handleConsoleCommand(command);
        }
    }

    if (CAM_SERIAL.available())
    {
        String line;
        if (readLineFromCam(line, 20) && line.length() > 0)
        {
            CONSOLE_SERIAL.print("[CAM] ");
            CONSOLE_SERIAL.println(line);
        }
    }
}

void initDisplayAndUi()
{
    lv_init();

    touchSpi.begin(TOUCH_CLK_PIN, TOUCH_MISO_PIN, TOUCH_MOSI_PIN, TOUCH_CS_PIN);
    touch.begin(touchSpi);
    touch.setRotation(1);

    tft.begin();
    tft.setRotation(1);
    tft.setSwapBytes(true);
    tft.fillScreen(TFT_BLACK);

    gDisplay = lv_display_create(TFT_HOR_RES, TFT_VER_RES);
    lv_display_set_flush_cb(gDisplay, tftFlushCallback);
    lv_display_set_buffers(gDisplay, gLvglDrawBuf, nullptr, sizeof(gLvglDrawBuf),
                           LV_DISPLAY_RENDER_MODE_PARTIAL);

    lv_indev_t *touchIndev = lv_indev_create();
    lv_indev_set_type(touchIndev, LV_INDEV_TYPE_POINTER);
    lv_indev_set_read_cb(touchIndev, touchReadCallback);

    ui_init();
    updateBookingHints();

    gLastLvTickMs = millis();
    gUiReady = true;
}

void pumpUi()
{
    if (!gUiReady)
    {
        return;
    }

    const unsigned long now = millis();
    const unsigned long elapsed = now - gLastLvTickMs;
    if (elapsed > 0)
    {
        lv_tick_inc(elapsed);
        gLastLvTickMs = now;
    }

    lv_timer_handler();
    ui_tick();
}

void tftFlushCallback(lv_display_t *display, const lv_area_t *area, uint8_t *pxMap)
{
    const uint32_t w = static_cast<uint32_t>(area->x2 - area->x1 + 1);
    const uint32_t h = static_cast<uint32_t>(area->y2 - area->y1 + 1);

    tft.startWrite();
    tft.setAddrWindow(area->x1, area->y1, w, h);
    tft.pushColors(reinterpret_cast<uint16_t *>(pxMap), w * h, true);
    tft.endWrite();

    lv_display_flush_ready(display);
}

void touchReadCallback(lv_indev_t *indev, lv_indev_data_t *data)
{
    LV_UNUSED(indev);

    static uint16_t lastX = 0;
    static uint16_t lastY = 0;

    // Some XPT2046 breakout boards do not route T_IRQ reliably; polling touched() is safer.
    const bool isTouched = touch.touched();

    if (isTouched)
    {
        const TS_Point p = touch.getPoint();
        // Touch controller orientation is 180 deg relative to display in this wiring.
        const long mappedX = map(p.x, TOUCH_RAW_X_MIN, TOUCH_RAW_X_MAX, TFT_HOR_RES - 1, 0);
        const long mappedY = map(p.y, TOUCH_RAW_Y_MIN, TOUCH_RAW_Y_MAX, TFT_VER_RES - 1, 0);

        lastX = static_cast<uint16_t>(constrain(mappedX, 0L, static_cast<long>(TFT_HOR_RES - 1)));
        lastY = static_cast<uint16_t>(constrain(mappedY, 0L, static_cast<long>(TFT_VER_RES - 1)));
    }

    data->point.x = static_cast<int16_t>(lastX);
    data->point.y = static_cast<int16_t>(lastY);
    data->state = isTouched ? LV_INDEV_STATE_PRESSED : LV_INDEV_STATE_RELEASED;
}

void updateBookingHints()
{
    if (objects.obj10 != nullptr)
    {
        String detail = "Tipo: ";
        detail += gBookingTicketType;
        detail += "\nEscaneo simulado para continuar al pago.";
        lv_label_set_text(objects.obj10, detail.c_str());
    }
}

void printHelp()
{
    CONSOLE_SERIAL.println("Comandos disponibles:");
    CONSOLE_SERIAL.println("  qr          -> ordena CAPTURE_QR al ESP32-CAM");
    CONSOLE_SERIAL.println("  doc         -> ordena CAPTURE_DOC al ESP32-CAM");
    CONSOLE_SERIAL.println("  ping        -> prueba comunicacion con ESP32-CAM");
    CONSOLE_SERIAL.println("  wifi        -> reconecta WiFi");
    CONSOLE_SERIAL.println("  help        -> muestra ayuda");
    CONSOLE_SERIAL.println("Use la pantalla tactil para navegar la UI EEZ.");
}

bool connectWifi()
{
    if (WiFi.status() == WL_CONNECTED)
    {
        return true;
    }

    CONSOLE_SERIAL.printf("Conectando WiFi SSID: %s\n", WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    const unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < 15000)
    {
        delay(250);
        CONSOLE_SERIAL.print(".");
        pumpUi();
    }

    CONSOLE_SERIAL.println();
    if (WiFi.status() != WL_CONNECTED)
    {
        CONSOLE_SERIAL.println("WiFi no conectado");
        return false;
    }

    CONSOLE_SERIAL.print("WiFi conectado. IP: ");
    CONSOLE_SERIAL.println(WiFi.localIP());
    return true;
}

void flushCamInput()
{
    while (CAM_SERIAL.available())
    {
        CAM_SERIAL.read();
    }
}

void sendCamCommand(const char *command)
{
    CAM_SERIAL.print(command);
    CAM_SERIAL.print('\n');
}

bool readLineFromCam(String &line, unsigned long timeoutMs)
{
    line = "";
    const unsigned long start = millis();

    while (millis() - start < timeoutMs)
    {
        while (CAM_SERIAL.available())
        {
            const char c = static_cast<char>(CAM_SERIAL.read());
            if (c == '\r')
            {
                continue;
            }
            if (c == '\n')
            {
                return true;
            }
            line += c;
        }
        delay(2);
        pumpUi();
    }

    return false;
}

bool readExactBytesFromCam(size_t length, String &output, unsigned long timeoutMs)
{
    output = "";
    output.reserve(length);

    size_t remaining = length;
    const unsigned long start = millis();

    while (remaining > 0 && millis() - start < timeoutMs)
    {
        while (CAM_SERIAL.available() && remaining > 0)
        {
            output += static_cast<char>(CAM_SERIAL.read());
            remaining--;
        }
        if (remaining > 0)
        {
            delay(1);
            pumpUi();
        }
    }

    return remaining == 0;
}

bool discardExactBytesFromCam(size_t length, unsigned long timeoutMs)
{
    uint8_t buffer[128];
    size_t remaining = length;
    const unsigned long start = millis();

    while (remaining > 0 && millis() - start < timeoutMs)
    {
        size_t availableBytes = CAM_SERIAL.available();
        if (availableBytes == 0)
        {
            delay(1);
            pumpUi();
            continue;
        }

        size_t toRead = availableBytes;
        if (toRead > sizeof(buffer))
        {
            toRead = sizeof(buffer);
        }
        if (toRead > remaining)
        {
            toRead = remaining;
        }

        const size_t bytesRead = CAM_SERIAL.readBytes(buffer, toRead);
        if (bytesRead == 0)
        {
            delay(1);
            pumpUi();
            continue;
        }

        remaining -= bytesRead;
    }

    return remaining == 0;
}

String escapeJsonString(const String &value)
{
    String escaped;
    escaped.reserve(value.length() + 8);

    for (size_t i = 0; i < value.length(); ++i)
    {
        const char c = value.charAt(i);
        if (c == '"' || c == '\\')
        {
            escaped += '\\';
        }
        escaped += c;
    }

    return escaped;
}

bool verifyQrWithBackend(const String &qrPayload)
{
    if (!connectWifi())
    {
        return false;
    }

    HTTPClient http;
    const String url = String(BACKEND_BASE_URL) + "/validation/qr";

    http.begin(url);
    http.setConnectTimeout(BACKEND_CONNECT_TIMEOUT_MS);
    http.setTimeout(BACKEND_RESPONSE_TIMEOUT_MS);
    http.addHeader("Content-Type", "application/json");

    const String body = String("{\"qr_payload\":\"") + escapeJsonString(qrPayload) + "\"}";
    const int statusCode = http.POST(body);
    String response;
    if (statusCode > 0)
    {
        response = http.getString();
    }
    else
    {
        response = HTTPClient::errorToString(statusCode);
    }
    http.end();

    CONSOLE_SERIAL.printf("Backend status: %d\n", statusCode);
    CONSOLE_SERIAL.println(response);

    return statusCode >= 200 && statusCode < 300;
}

bool parseQrBeginHeader(const String &header, size_t &payloadLength, bool &isValid)
{
    if (!header.startsWith("QR_BEGIN,"))
    {
        return false;
    }

    const int firstComma = header.indexOf(',');
    const int secondComma = header.indexOf(',', firstComma + 1);
    if (firstComma < 0 || secondComma < 0)
    {
        return false;
    }

    payloadLength = static_cast<size_t>(header.substring(firstComma + 1, secondComma).toInt());
    isValid = header.substring(secondComma + 1).toInt() == 1;
    return true;
}

bool parseImgBeginHeader(const String &header, size_t &imageLength, String &typeLabel,
                         int &width, int &height, int &format)
{
    if (!header.startsWith("IMG_BEGIN,"))
    {
        return false;
    }

    const int c1 = header.indexOf(',');
    const int c2 = header.indexOf(',', c1 + 1);
    const int c3 = header.indexOf(',', c2 + 1);
    const int c4 = header.indexOf(',', c3 + 1);
    const int c5 = header.indexOf(',', c4 + 1);

    if (c1 < 0 || c2 < 0 || c3 < 0 || c4 < 0 || c5 < 0)
    {
        return false;
    }

    typeLabel = header.substring(c1 + 1, c2);
    imageLength = static_cast<size_t>(header.substring(c2 + 1, c3).toInt());
    width = header.substring(c3 + 1, c4).toInt();
    height = header.substring(c4 + 1, c5).toInt();
    format = header.substring(c5 + 1).toInt();
    return true;
}

bool captureQrFlow()
{
    CONSOLE_SERIAL.println("Solicitando captura QR al ESP32-CAM...");
    flushCamInput();
    sendCamCommand(CMD_CAPTURE_QR);

    const unsigned long start = millis();
    String header;
    bool headerFound = false;

    while (millis() - start < QR_SCAN_TIMEOUT_MS)
    {
        String line;
        if (!readLineFromCam(line, 250))
        {
            continue;
        }

        if (line.length() == 0)
        {
            continue;
        }

        if (line.startsWith("STATUS,ERROR"))
        {
            CONSOLE_SERIAL.print("Error CAM: ");
            CONSOLE_SERIAL.println(line);
            return false;
        }

        if (line.startsWith("QR_BEGIN,"))
        {
            header = line;
            headerFound = true;
            break;
        }

        CONSOLE_SERIAL.print("[CAM] ");
        CONSOLE_SERIAL.println(line);
    }

    if (!headerFound)
    {
        CONSOLE_SERIAL.println("No se recibio QR_BEGIN");
        return false;
    }

    size_t payloadLength = 0;
    bool isValid = false;
    if (!parseQrBeginHeader(header, payloadLength, isValid))
    {
        CONSOLE_SERIAL.println("Cabecera QR invalida");
        return false;
    }

    String qrPayload;
    if (!readExactBytesFromCam(payloadLength, qrPayload, LINE_TIMEOUT_MS))
    {
        CONSOLE_SERIAL.println("Timeout recibiendo payload QR");
        return false;
    }

    bool qrEndFound = false;
    const unsigned long endStart = millis();
    while (millis() - endStart < LINE_TIMEOUT_MS)
    {
        String marker;
        if (!readLineFromCam(marker, 250))
        {
            continue;
        }
        if (marker.length() == 0)
        {
            continue;
        }
        if (marker == "QR_END")
        {
            qrEndFound = true;
            break;
        }
        if (marker.startsWith("STATUS,"))
        {
            CONSOLE_SERIAL.print("[CAM] ");
            CONSOLE_SERIAL.println(marker);
        }
    }

    if (!qrEndFound)
    {
        CONSOLE_SERIAL.println("No se recibio QR_END");
        return false;
    }

    if (!isValid)
    {
        CONSOLE_SERIAL.println("El ESP32-CAM detecto QR invalido");
        return false;
    }

    CONSOLE_SERIAL.print("QR payload: ");
    CONSOLE_SERIAL.println(qrPayload);

    const bool backendOk = verifyQrWithBackend(qrPayload);
    if (backendOk)
    {
        CONSOLE_SERIAL.println("Entrada validada en backend");
    }
    else
    {
        CONSOLE_SERIAL.println("El backend rechazo la validacion");
    }

    return backendOk;
}

bool captureDocumentFlow()
{
    CONSOLE_SERIAL.println("Solicitando captura de documento al ESP32-CAM...");
    flushCamInput();
    sendCamCommand(CMD_CAPTURE_DOC);

    const unsigned long start = millis();
    String header;
    bool headerFound = false;

    while (millis() - start < DOC_CAPTURE_TIMEOUT_MS)
    {
        String line;
        if (!readLineFromCam(line, 250))
        {
            continue;
        }

        if (line.length() == 0)
        {
            continue;
        }

        if (line.startsWith("STATUS,ERROR"))
        {
            CONSOLE_SERIAL.print("Error CAM: ");
            CONSOLE_SERIAL.println(line);
            return false;
        }

        if (line.startsWith("IMG_BEGIN,"))
        {
            header = line;
            headerFound = true;
            break;
        }

        CONSOLE_SERIAL.print("[CAM] ");
        CONSOLE_SERIAL.println(line);
    }

    if (!headerFound)
    {
        CONSOLE_SERIAL.println("No se recibio IMG_BEGIN");
        return false;
    }

    size_t imageLength = 0;
    String typeLabel;
    int width = 0;
    int height = 0;
    int format = 0;
    if (!parseImgBeginHeader(header, imageLength, typeLabel, width, height, format))
    {
        CONSOLE_SERIAL.println("Cabecera IMG invalida");
        return false;
    }

    CONSOLE_SERIAL.printf("Imagen %s: %u bytes, %dx%d, fmt=%d\n", typeLabel.c_str(),
                          static_cast<unsigned>(imageLength), width, height, format);

    if (!discardExactBytesFromCam(imageLength, DOC_CAPTURE_TIMEOUT_MS))
    {
        CONSOLE_SERIAL.println("Timeout recibiendo bytes de imagen");
        return false;
    }

    bool imgEndFound = false;
    const unsigned long endStart = millis();
    while (millis() - endStart < LINE_TIMEOUT_MS)
    {
        String line;
        if (!readLineFromCam(line, 250))
        {
            continue;
        }
        if (line.length() == 0)
        {
            continue;
        }
        if (line == "IMG_END")
        {
            imgEndFound = true;
            break;
        }
        CONSOLE_SERIAL.print("[CAM] ");
        CONSOLE_SERIAL.println(line);
    }

    if (!imgEndFound)
    {
        CONSOLE_SERIAL.println("No se recibio IMG_END");
        return false;
    }

    CONSOLE_SERIAL.println("Captura de documento completada");
    return true;
}

extern "C" bool app_capture_qr_and_validate()
{
    return captureQrFlow();
}

extern "C" bool app_capture_document_for_entry()
{
    CONSOLE_SERIAL.println("Validacion de identidad en backend pendiente; usando captura local.");
    return captureDocumentFlow();
}

extern "C" bool app_capture_document_for_booking()
{
    CONSOLE_SERIAL.println("Registro de compra con validacion de documento simulada.");
    return captureDocumentFlow();
}

extern "C" bool app_verify_payment_simulated()
{
    CONSOLE_SERIAL.println("Pago verificado de forma simulada (integracion pendiente).");
    delay(250);
    pumpUi();
    return true;
}

extern "C" void app_set_booking_ticket_type(const char *ticketType)
{
    if (ticketType == nullptr || ticketType[0] == '\0')
    {
        return;
    }

    strncpy(gBookingTicketType, ticketType, sizeof(gBookingTicketType) - 1);
    gBookingTicketType[sizeof(gBookingTicketType) - 1] = '\0';
    updateBookingHints();
}

void handleConsoleCommand(const String &command)
{
    if (command.equalsIgnoreCase("qr") || command.equalsIgnoreCase("capture_qr"))
    {
        captureQrFlow();
        return;
    }

    if (command.equalsIgnoreCase("doc") || command.equalsIgnoreCase("capture_doc"))
    {
        captureDocumentFlow();
        return;
    }

    if (command.equalsIgnoreCase("ping"))
    {
        flushCamInput();
        sendCamCommand(CMD_PING);
        String response;
        if (readLineFromCam(response, LINE_TIMEOUT_MS))
        {
            CONSOLE_SERIAL.print("Respuesta CAM: ");
            CONSOLE_SERIAL.println(response);
        }
        else
        {
            CONSOLE_SERIAL.println("Sin respuesta del ESP32-CAM");
        }
        return;
    }

    if (command.equalsIgnoreCase("wifi"))
    {
        connectWifi();
        return;
    }

    if (command.equalsIgnoreCase("help"))
    {
        printHelp();
        return;
    }

    CONSOLE_SERIAL.print("Comando no reconocido: ");
    CONSOLE_SERIAL.println(command);
    printHelp();
}