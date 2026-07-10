#pragma once

#include <Arduino.h>

enum class LightColor { Off, Green, Yellow, Red, StalePulse, CompactFlash };

class LedController {
 public:
  LedController(uint8_t greenPin, uint8_t yellowPin, uint8_t redPin);

  void begin();
  void setColor(LightColor color);
  void update();  // call every loop() iteration; drives the StalePulse animation

 private:
  uint8_t greenPin_;
  uint8_t yellowPin_;
  uint8_t redPin_;
  LightColor current_ = LightColor::Off;
  uint32_t pulsePhaseStartMs_ = 0;

  void showSolid(bool green, bool yellow, bool red);
};
