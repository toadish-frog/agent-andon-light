#include "led_controller.h"
#include "watchdog.h"

namespace {
constexpr uint8_t kDataPin = 1;    // GPIO1 — to the LED strip PCBA's "S" (signal) pin; confirm against your wiring
constexpr uint16_t kNumPixels = 10;  // WS2812-style strip PCBA, 10 addressable LEDs
constexpr uint32_t kWatchdogTimeoutMs = 1800000;  // 30 min — same value as the led-bulb variant;
                                                   // see ../../../led-bulb/firmware/README.md
constexpr unsigned long kSerialBaud = 115200;
}  // namespace

LedController leds(kDataPin, kNumPixels);
Watchdog watchdog(kWatchdogTimeoutMs);

void setup() {
  Serial.begin(kSerialBaud);
  leds.begin();
  watchdog.kick();
}

void loop() {
  while (Serial.available()) {
    switch (Serial.read()) {
      case 'G': leds.setColor(LightColor::Green);        watchdog.kick(); break;
      case 'Y': leds.setColor(LightColor::Yellow);       watchdog.kick(); break;
      case 'R': leds.setColor(LightColor::Red);          watchdog.kick(); break;
      case 'C': leds.setColor(LightColor::CompactFlash); watchdog.kick(); break;
      case 'H': watchdog.kick(); break;
      default: break;  // ignores '\n', '\r', and anything unrecognized
    }
  }

  if (watchdog.isStale()) {
    leds.setColor(LightColor::StalePulse);
  }
  leds.update();
}
