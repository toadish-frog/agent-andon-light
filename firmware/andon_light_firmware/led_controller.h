#pragma once

#include <Adafruit_NeoPixel.h>

enum class LightColor { Off, Green, Yellow, Red, StalePulse };

class LedController {
 public:
  LedController(uint8_t dataPin, uint16_t ledCount);

  void begin();
  void setColor(LightColor color);
  void update();  // call every loop() iteration; drives the StalePulse animation

 private:
  Adafruit_NeoPixel strip_;
  LightColor current_ = LightColor::Off;
  uint32_t pulsePhaseStartMs_ = 0;

  void showSolid(uint8_t r, uint8_t g, uint8_t b);
  void showPulse();
};
