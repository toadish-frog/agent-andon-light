#include "led_controller.h"

#include <math.h>

namespace {
constexpr uint32_t kPulsePeriodMs = 1200;
}  // namespace

LedController::LedController(uint8_t greenPin, uint8_t yellowPin, uint8_t redPin)
    : greenPin_(greenPin), yellowPin_(yellowPin), redPin_(redPin) {}

void LedController::begin() {
  pinMode(greenPin_, OUTPUT);
  pinMode(yellowPin_, OUTPUT);
  pinMode(redPin_, OUTPUT);
  showSolid(false, false, false);
}

void LedController::setColor(LightColor color) {
  if (color == LightColor::StalePulse && current_ == LightColor::StalePulse) {
    return;  // already pulsing — don't reset the animation phase every loop
  }
  current_ = color;

  switch (color) {
    case LightColor::Green:  showSolid(true, false, false); break;
    case LightColor::Yellow: showSolid(false, true, false); break;
    case LightColor::Red:    showSolid(false, false, true); break;
    case LightColor::StalePulse:
      digitalWrite(greenPin_, LOW);
      digitalWrite(yellowPin_, LOW);
      pulsePhaseStartMs_ = millis();
      break;
    case LightColor::Off:
    default: showSolid(false, false, false); break;
  }
}

void LedController::update() {
  if (current_ == LightColor::StalePulse) {
    uint32_t elapsed = (millis() - pulsePhaseStartMs_) % kPulsePeriodMs;
    float phase = elapsed / static_cast<float>(kPulsePeriodMs);
    float brightness = 0.5f * (1.0f - cosf(phase * 2.0f * PI));  // 0..1 breathing curve
    analogWrite(redPin_, static_cast<int>(255 * brightness));
  }
}

void LedController::showSolid(bool green, bool yellow, bool red) {
  digitalWrite(greenPin_, green ? HIGH : LOW);
  digitalWrite(yellowPin_, yellow ? HIGH : LOW);
  digitalWrite(redPin_, red ? HIGH : LOW);
}
