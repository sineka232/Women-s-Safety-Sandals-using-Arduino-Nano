// Nano + SIM800L + SoftwareSerial SMS example
#include <SoftwareSerial.h>

SoftwareSerial sim800(7, 8); // RX, TX to SIM800L (change pins)
SoftwareSerial gpsSerial(9, 10); // if you have GPS on SoftwareSerial

const int sosPin = 2;
const int ledPin = 13;
unsigned long lastDebounce = 0;
const unsigned long debounceDelay = 300;

String readGPS() {
  // simple loop to get GPRMC and parse lat/lon - simplified
  unsigned long start = millis();
  String line;
  while (millis() - start < 3000) {
    if (gpsSerial.available()) {
      char c = gpsSerial.read();
      line += c;
      if (c == '\n') {
        if (line.indexOf("GPRMC") >= 0) {
          // crude: return whole line; parse on server or here
          return line;
        }
        line = "";
      }
    }
  }
  return "";
}

void sendSMS(const char* number, const String &message) {
  sim800.println("AT+CMGF=1"); // text mode
  delay(500);
  sim800.print("AT+CMGS=\"");
  sim800.print(number);
  sim800.println("\"");
  delay(500);
  sim800.print(message);
  delay(500);
  sim800.write(26); // Ctrl+Z
  delay(5000);
}

void setup() {
  pinMode(sosPin, INPUT_PULLUP); // button pulls to ground
  pinMode(ledPin, OUTPUT);
  Serial.begin(9600);
  sim800.begin(9600);
  gpsSerial.begin(9600);
  delay(1000);
  Serial.println("Ready");
}

void loop() {
  if (digitalRead(sosPin) == LOW) {
    if (millis() - lastDebounce > debounceDelay) {
      lastDebounce = millis();
      digitalWrite(ledPin, HIGH);
      String gps = readGPS(); // may be empty
      String message = "SOS! ";
      if (gps.length() > 0) {
        message += "GPS:";
        message += gps;
      } else {
        message += "No GPS fix";
      }
      // Send SMS to registered number and police
      sendSMS("+91YYYYYYYYYY", message);
      delay(2000);
      sendSMS("+91ZZZZZZZZZZ", message);
      // feedback
      for (int i=0;i<6;i++){
        digitalWrite(ledPin, !digitalRead(ledPin));
        delay(150);
      }
      digitalWrite(ledPin, LOW);
    }
  }
  delay(50);
}
