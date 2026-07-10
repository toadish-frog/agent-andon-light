#pragma once

#include <Adafruit_NeoPixel.h>
#include <Arduino.h>

enum class LightColor { Off, Green, Yellow, Red, StalePulse, CompactFlash };

class LedController {
 public:
  LedController(uint8_t dataPin, uint16_t numPixels);

  void begin();
  void setColor(LightColor color);
  void update();  // call every loop() iteration; drives the StalePulse/CompactFlash animation

 private:
  Adafruit_NeoPixel strip_;
  LightColor current_ = LightColor::Off;
  uint32_t pulsePhaseStartMs_ = 0;

  // Lights pixels [sectionStart, sectionStart + sectionCount) to (r,g,b) and every other
  // non-status pixel off, then always re-asserts the dim-white status pixel on top. This is
  // the single render path for every state (solid colors call it directly; StalePulse/
  // CompactFlash call it once per update() with a time-varying color) so the status pixel and
  // "everything outside the active section is off" behavior can't drift between states.
  void renderSection(uint16_t sectionStart, uint16_t sectionCount, uint8_t r, uint8_t g, uint8_t b);
};
