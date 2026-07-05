#include "led_controller.h"

#include <Arduino.h>
#include <math.h>

namespace {
constexpr uint32_t kPulsePeriodMs = 1200;
constexpr uint8_t kBrightness = 80;  // out of 255; keep it desk-friendly, not blinding
}  // namespace

LedController::LedController(uint8_t dataPin, uint16_t ledCount)
    : strip_(ledCount, dataPin, NEO_GRB + NEO_KHZ800) {}

void LedController::begin() {
  strip_.begin();
  strip_.setBrightness(kBrightness);
  showSolid(0, 0, 0);
}

void LedController::setColor(LightColor color) {
  if (color == LightColor::StalePulse && current_ == LightColor::StalePulse) {
    return;  // already pulsing — don't reset the animation phase every loop
  }
  current_ = color;

  switch (color) {
    case LightColor::Green:  showSolid(0, 255, 0); break;
    case LightColor::Yellow: showSolid(255, 200, 0); break;
    case LightColor::Red:    showSolid(255, 0, 0); break;
    case LightColor::StalePulse: pulsePhaseStartMs_ = millis(); break;
    case LightColor::Off:
    default:                 showSolid(0, 0, 0); break;
  }
}

void LedController::update() {
  if (current_ == LightColor::StalePulse) {
    showPulse();
  }
}

void LedController::showSolid(uint8_t r, uint8_t g, uint8_t b) {
  for (uint16_t i = 0; i < strip_.numPixels(); ++i) {
    strip_.setPixelColor(i, strip_.Color(r, g, b));
  }
  strip_.show();
}

void LedController::showPulse() {
  uint32_t elapsed = (millis() - pulsePhaseStartMs_) % kPulsePeriodMs;
  float phase = elapsed / static_cast<float>(kPulsePeriodMs);
  float brightness = 0.5f * (1.0f - cosf(phase * 2.0f * PI));  // 0..1 breathing curve
  showSolid(static_cast<uint8_t>(255 * brightness), 0, 0);
}
