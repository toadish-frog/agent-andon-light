#include "led_controller.h"
#include "watchdog.h"

namespace {
constexpr uint8_t kLedDataPin = 0;  // GPIO0 — WS2812 data-in, through the series resistor per BOM
constexpr uint16_t kLedCount = 5;
constexpr uint32_t kWatchdogTimeoutMs = 15000;
constexpr unsigned long kSerialBaud = 115200;
}  // namespace

LedController leds(kLedDataPin, kLedCount);
Watchdog watchdog(kWatchdogTimeoutMs);

void setup() {
  Serial.begin(kSerialBaud);
  leds.begin();
  watchdog.kick();
}

void loop() {
  while (Serial.available()) {
    switch (Serial.read()) {
      case 'G': leds.setColor(LightColor::Green);  watchdog.kick(); break;
      case 'Y': leds.setColor(LightColor::Yellow); watchdog.kick(); break;
      case 'R': leds.setColor(LightColor::Red);    watchdog.kick(); break;
      case 'H': watchdog.kick(); break;
      default: break;  // ignores '\n', '\r', and anything unrecognized
    }
  }

  if (watchdog.isStale()) {
    leds.setColor(LightColor::StalePulse);
  }
  leds.update();
}
