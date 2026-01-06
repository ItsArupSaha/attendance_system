#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_Fingerprint.h>

#define OLED_SDA 14
#define OLED_SCL 15

#define FP_RX 13   // ESP RX <- Sensor TX
#define FP_TX 12   // ESP TX -> Sensor RX (connect AFTER boot)

Adafruit_SSD1306 display(128, 64, &Wire, -1);
HardwareSerial fp(2);
Adafruit_Fingerprint finger(&fp);

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("BOOT");

  // OLED
  Wire.begin(OLED_SDA, OLED_SCL);
  display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(WHITE);
  display.setCursor(0,0);
  display.println("OLED OK");
  display.println("FP starting...");
  display.display();

  // Fingerprint
  fp.begin(57600, SERIAL_8N1, FP_RX, FP_TX);
  finger.begin(57600);

  if (finger.verifyPassword()) {
    Serial.println("FINGERPRINT DETECTED");
    display.println("FP DETECTED");
  } else {
    Serial.println("FP NOT FOUND");
    display.println("FP NOT FOUND");
  }
  display.display();
}

void loop() {
  if (finger.getImage() == FINGERPRINT_OK) {
    Serial.println("IMAGE TAKEN");
    display.clearDisplay();
    display.setCursor(0,0);
    display.println("FP OK");
    display.println("IMAGE TAKEN");
    display.display();
    delay(1000);
  }
}
