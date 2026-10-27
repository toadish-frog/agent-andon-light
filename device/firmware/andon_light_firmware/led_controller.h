#pragma once

#include <Adafruit_NeoPixel.h>
#include <Arduino.h>

enum class LightColor { Off, Green, Yellow, Red, StalePulse, CompactFlash };

class LedController {
 public:
  LedController(uint8_t dataPin, uint16_t numPixels);

  void begin(uint8_t brightnessPercent);
  void setColor(LightColor color);
  // Percent of the hardware maximum (255), clamped to [kMinBrightnessPercent, 100]. Re-renders
  // the current solid color immediately; animations pick it up on their next update().
  void setBrightnessPercent(uint8_t percent);
  void update();  // call every loop() iteration; drives the StalePulse/CompactFlash animation

  static constexpr uint8_t kMinBrightnessPercent = 5;  // below this the status pixel rounds to off
  static constexpr uint8_t kMaxBrightnessPercent = 100;
  static constexpr uint8_t kDefaultBrightnessPercent = 51;  // 130/255, the original fixed cap

 private:
  Adafruit_NeoPixel strip_;
  LightColor current_ = LightColor::Off;
  uint32_t pulsePhaseStartMs_ = 0;

  // Draws current_ if it's a solid state (Off/Green/Yellow/Red). Animated states are drawn
  // by update() instead, so this is a no-op for them.
  void renderSolid();

  // Lights pixels [sectionStart, sectionStart + sectionCount) to (r,g,b) and every other
  // non-status pixel off, then always re-asserts the dim-white status pixel on top. This is
  // the single render path for every state (solid colors call it directly; StalePulse/
  // CompactFlash call it once per update() with a time-varying color) so the status pixel and
  // "everything outside the active section is off" behavior can't drift between states.
  void renderSection(uint16_t sectionStart, uint16_t sectionCount, uint8_t r, uint8_t g, uint8_t b);
};
