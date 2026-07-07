#include "led_controller.h"
#include "watchdog.h"

namespace {
constexpr uint8_t kGreenPin = 1;   // GPIO1 — to the LED PCBA's "Green" pin; confirm against your wiring
constexpr uint8_t kYellowPin = 2;  // GPIO2 — to the LED PCBA's "Yellow" pin; confirm against your wiring
constexpr uint8_t kRedPin = 3;     // GPIO3 — to the LED PCBA's "Red" pin; confirm against your wiring
constexpr uint32_t kWatchdogTimeoutMs = 1800000;  // 30 min — long enough to cover pure-thinking
                                                   // stretches with no hook events; see USER-GUIDE.md
constexpr unsigned long kSerialBaud = 115200;
}  // namespace

LedController leds(kGreenPin, kYellowPin, kRedPin);
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
