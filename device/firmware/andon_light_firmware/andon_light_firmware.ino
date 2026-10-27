#include "brightness_store.h"
#include "led_controller.h"
#include "watchdog.h"

namespace {
constexpr uint8_t kDataPin = 1;    // GPIO1 — to the LED strip PCBA's "S" (signal) pin; confirm against your wiring
constexpr uint16_t kNumPixels = 10;  // WS2812-style strip PCBA, 10 addressable LEDs
constexpr uint32_t kWatchdogTimeoutMs = 1800000;  // 30 min — same value as the led-bulb variant;
                                                   // see ../../../led-bulb/firmware/README.md
constexpr unsigned long kSerialBaud = 115200;
constexpr uint8_t kMaxBrightnessDigits = 3;  // "100"

// `B<n>\n` is the only multi-byte command, so it gets a tiny state machine instead of the
// one-byte switch below. Anything malformed (no digits, a non-digit, too many digits) is
// dropped silently, matching how unrecognized single bytes are already ignored.
bool readingBrightness = false;
uint16_t brightnessValue = 0;
uint8_t brightnessDigits = 0;
}  // namespace

LedController leds(kDataPin, kNumPixels);
Watchdog watchdog(kWatchdogTimeoutMs);
BrightnessStore brightnessStore(LedController::kDefaultBrightnessPercent,
                                LedController::kMinBrightnessPercent,
                                LedController::kMaxBrightnessPercent);

void applyBrightness(uint16_t percent) {
  uint8_t clamped = constrain(percent, LedController::kMinBrightnessPercent,
                              LedController::kMaxBrightnessPercent);
  leds.setBrightnessPercent(clamped);
  brightnessStore.save(clamped);
}

// Returns true if the byte was consumed by an in-progress `B<n>` command. Brightness is a
// display setting, not agent activity, so it deliberately doesn't kick the watchdog.
bool handleBrightnessByte(int c) {
  if (!readingBrightness) return false;
  if (c >= '0' && c <= '9' && brightnessDigits < kMaxBrightnessDigits) {
    brightnessValue = brightnessValue * 10 + (c - '0');
    brightnessDigits++;
    return true;
  }
  readingBrightness = false;
  if (c == '\n' || c == '\r') {
    if (brightnessDigits > 0) applyBrightness(brightnessValue);
    return true;
  }
  return false;  // malformed — drop it and let the byte be handled as a normal command
}

void setup() {
  Serial.begin(kSerialBaud);
  brightnessStore.begin();
  leds.begin(brightnessStore.load());
  watchdog.kick();
}

void loop() {
  while (Serial.available()) {
    int c = Serial.read();
    if (handleBrightnessByte(c)) continue;
    switch (c) {
      case 'G': leds.setColor(LightColor::Green);        watchdog.kick(); break;
      case 'Y': leds.setColor(LightColor::Yellow);       watchdog.kick(); break;
      case 'R': leds.setColor(LightColor::Red);          watchdog.kick(); break;
      case 'C': leds.setColor(LightColor::CompactFlash); watchdog.kick(); break;
      case 'H': watchdog.kick(); break;
      case 'B':
        readingBrightness = true;
        brightnessValue = 0;
        brightnessDigits = 0;
        break;
      default: break;  // ignores '\n', '\r', and anything unrecognized
    }
  }

  if (watchdog.isStale()) {
    leds.setColor(LightColor::StalePulse);
  }
  leds.update();
}
