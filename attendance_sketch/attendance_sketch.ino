#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_Fingerprint.h>

/* ---------------- Pins ---------------- */
#define OLED_SDA 14
#define OLED_SCL 15
#define FP_RX 13
#define FP_TX 12   // connect AFTER boot

/* ---------------- WiFi & Server ---------------- */
const char* WIFI_SSID = "Arup";
const char* WIFI_PASS = "@r()pWFp@$$1";
const char* SERVER_BASE = "http://192.168.0.101:8000";

/* ---------------- Objects ---------------- */
HardwareSerial fp(2);
Adafruit_Fingerprint finger(&fp);
Adafruit_SSD1306 display(128, 64, &Wire, -1);

/* ---------------- State ---------------- */
String currentMode = "";
unsigned long lastModePoll = 0;

/* ---------------- Helpers ---------------- */
void oled(const String& l1, const String& l2="") {
  display.clearDisplay();
  display.setCursor(0,0);
  display.println(l1);
  if (l2.length()) display.println(l2);
  display.display();
}

String httpGET(const String& url) {
  HTTPClient http;
  http.begin(url);
  http.GET();
  String body = http.getString();
  http.end();
  return body;
}

void httpPOST(const String& url, const String& payload) {
  HTTPClient http;
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  http.POST(payload);
  http.end();
}

String extractMode(const String& json) {
  if (json.indexOf("register") >= 0) return "register";
  if (json.indexOf("attendance") >= 0) return "attendance";
  return "";
}

/* ---------------- Finger helpers ---------------- */
bool waitFingerDown(unsigned long timeoutMs=12000) {
  unsigned long t0 = millis();
  while (millis() - t0 < timeoutMs) {
    if (finger.getImage() == FINGERPRINT_OK) return true;
    delay(50);
  }
  return false;
}

bool waitFingerUp(unsigned long timeoutMs=6000) {
  unsigned long t0 = millis();
  while (millis() - t0 < timeoutMs) {
    if (finger.getImage() == FINGERPRINT_NOFINGER) return true;
    delay(50);
  }
  return false;
}

/* ---------------- Setup ---------------- */
void setup() {
  Serial.begin(115200);
  delay(800);

  Wire.begin(OLED_SDA, OLED_SCL);
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  display.setTextSize(1);
  display.setTextColor(WHITE);

  oled("WiFi...");
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) delay(300);
  oled("WiFi OK");

  fp.begin(57600, SERIAL_8N1, FP_RX, FP_TX);
  finger.begin(57600);
  if (!finger.verifyPassword()) {
    oled("FP ERROR");
    while(1);
  }

  // Initial mode sync
  String body = httpGET(String(SERVER_BASE) + "/mode");
  currentMode = extractMode(body);
  if (currentMode == "") currentMode = "attendance"; // safe default
  if (currentMode == "register")
    oled("REGISTER MODE", "Scan finger");
  else
    oled("ATTENDANCE MODE", "Scan finger");
}

/* ---------------- Loop ---------------- */
void loop() {
  // Poll mode every 1s
  if (millis() - lastModePoll > 1000) {
    lastModePoll = millis();
    String body = httpGET(String(SERVER_BASE) + "/mode");
    Serial.println("MODE RAW: " + body);

    String m = extractMode(body);
    if (m.length() && m != currentMode) {
      currentMode = m;
      if (currentMode == "register")
        oled("REGISTER MODE", "Scan finger");
      else
        oled("ATTENDANCE MODE", "Scan finger");
    }
  }

  /* ---------- REGISTER MODE ---------- */
  if (currentMode == "register") {
    oled("REGISTER MODE", "1st scan...");
    if (!waitFingerDown()) return;
    if (finger.image2Tz(1) != FINGERPRINT_OK) return;

    oled("1st scan OK", "Remove finger");
    if (!waitFingerUp()) return;

    oled("REGISTER MODE", "2nd scan...");
    if (!waitFingerDown()) return;
    if (finger.image2Tz(2) != FINGERPRINT_OK) return;

    oled("2nd scan OK");

    if (finger.createModel() != FINGERPRINT_OK) {
      oled("Enroll failed");
      delay(2000);
      return;
    }

    finger.getTemplateCount();
    int newID = finger.templateCount + 1;
    if (finger.storeModel(newID) != FINGERPRINT_OK) {
      oled("Store failed");
      delay(2000);
      return;
    }

    oled("Sending ID...", String(newID));
    httpPOST(String(SERVER_BASE) + "/register-fingerprint",
             "{\"fingerprint_id\":" + String(newID) + "}");

    delay(3000);
    oled("REGISTER MODE", "Next teacher");
    return;
  }

  /* ---------- ATTENDANCE MODE ---------- */
  if (currentMode == "attendance") {
    oled("ATTENDANCE MODE", "Scan finger");
    if (!waitFingerDown()) return;
    if (finger.image2Tz() != FINGERPRINT_OK) return;

    if (finger.fingerFastSearch() != FINGERPRINT_OK) {
      oled("Not recognized");
      delay(2000);
      return;
    }

    int fid = finger.fingerID;
    httpPOST(String(SERVER_BASE) + "/attendance",
             "{\"fingerprint_id\":" + String(fid) + "}");
    oled("Sent", "ID " + String(fid));
    delay(3000);
    return;
  }
}
