#include "led_controller.h"

#include <math.h>

namespace {
constexpr uint32_t kPulsePeriodMs = 1200;   // StalePulse: slow breathing fade
constexpr uint32_t kFlashPeriodMs = 500;    // CompactFlash: sharp on/off blink

// Base brightness cap (0-255), applied to every solid/animated color.
// WS2812 pixels are uncomfortably bright at 255/255 close up, and capping
// also keeps worst-case current draw well within what USB bus power can
// supply across 10 pixels. Raise if the strip is diffused/behind a cover.
constexpr uint8_t kBrightness = 130;
}  // namespace

LedController::LedController(uint8_t dataPin, uint16_t numPixels)
    : strip_(numPixels, dataPin, NEO_GRB + NEO_KHZ800) {}

void LedController::begin() {
  strip_.begin();
  strip_.setBrightness(kBrightness);
  strip_.show();  // all off until the first color, avoids a garbage-data flash on boot
  // Boot straight to idle (red) rather than Off — a bare power-on/replug is a
  // hardware event Claude Code's SessionStart hook never sees, so without this
  // the light would sit dark until the next real hook fires. Same "not working
  // yet" default reasoning as the SessionStart hook.
  setColor(LightColor::Red);
}

void LedController::setColor(LightColor color) {
  bool alreadyAnimating = (color == LightColor::StalePulse || color == LightColor::CompactFlash) &&
                           color == current_;
  if (alreadyAnimating) {
    return;  // already animating this state — don't reset the animation phase every loop
  }
  current_ = color;

  switch (color) {
    case LightColor::Green:  showSolid(0, 255, 0);   break;
    case LightColor::Yellow: showSolid(255, 255, 0); break;
    case LightColor::Red:    showSolid(255, 0, 0);   break;
    case LightColor::StalePulse:
    case LightColor::CompactFlash:
      pulsePhaseStartMs_ = millis();
      break;
    case LightColor::Off:
    default: showSolid(0, 0, 0); break;
  }
}

void LedController::update() {
  if (current_ == LightColor::StalePulse) {
    uint32_t elapsed = (millis() - pulsePhaseStartMs_) % kPulsePeriodMs;
    float phase = elapsed / static_cast<float>(kPulsePeriodMs);
    float brightness = 0.5f * (1.0f - cosf(phase * 2.0f * PI));  // 0..1 breathing curve
    showSolid(static_cast<uint8_t>(255 * brightness), 0, 0);
  } else if (current_ == LightColor::CompactFlash) {
    uint32_t elapsed = (millis() - pulsePhaseStartMs_) % kFlashPeriodMs;
    bool on = elapsed < (kFlashPeriodMs / 2);  // sharp square-wave blink, not a fade
    showSolid(0, on ? 255 : 0, 0);
  }
}

void LedController::showSolid(uint8_t r, uint8_t g, uint8_t b) {
  strip_.fill(strip_.Color(r, g, b));
  strip_.show();
}
