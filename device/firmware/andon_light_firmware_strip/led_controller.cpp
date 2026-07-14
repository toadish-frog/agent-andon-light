#include "led_controller.h"

#include <math.h>

namespace {
constexpr uint32_t kPulsePeriodMs = 1200;   // StalePulse: slow breathing fade

// CompactFlash: a chase-fill sequence, not a blink. Each pass sweeps a single lit pixel
// down from silkscreen pixel 10 to pixel 2 (a "chase"), then locks that pass's bottom
// pixel on before starting the next pass — so pixels accumulate from pixel 2 upward, one
// per pass, until all 9 non-status pixels are lit, then the whole thing resets and
// repeats. kCompactPixelCount is all non-status pixels (array indices
// kGreenStart..kRedStart+kRedCount-1, i.e. 1-9, which are silkscreen pixels 2-10); pass k
// (array-index terms) sweeps (kCompactPixelCount - k) transient pixels then locks index k,
// so total steps across all kCompactPixelCount passes is the triangular number
// kCompactPixelCount + (kCompactPixelCount-1) + ... + 1.
constexpr uint32_t kCompactStepMs = 120;
constexpr uint16_t kCompactPixelCount = 9;
constexpr uint16_t kCompactTotalSteps = kCompactPixelCount * (kCompactPixelCount + 1) / 2;

// Base brightness cap (0-255), applied to every solid/animated color.
// WS2812 pixels are uncomfortably bright at 255/255 close up, and capping
// also keeps worst-case current draw well within what USB bus power can
// supply across 10 pixels. Raise if the strip is diffused/behind a cover.
constexpr uint8_t kBrightness = 130;

// Pixel layout (0-indexed; silkscreen/BOM label these 1-10). An andon light communicates
// state by which lamp is lit, not by turning every lamp the same color at once — so each
// color gets its own dedicated sub-range of the strip instead of using strip.fill() across
// all 10 pixels. See led-strip/docs/Implementation-Summary.md "Addressable pixel layout".
constexpr uint16_t kStatusPixel = 0;   // pixel 1 — dim white, "board is powered and running"
constexpr uint16_t kGreenStart = 1;    // pixels 2-4
constexpr uint16_t kGreenCount = 3;
constexpr uint16_t kYellowStart = 4;   // pixels 5-7
constexpr uint16_t kYellowCount = 3;
constexpr uint16_t kRedStart = 7;      // pixels 8-10
constexpr uint16_t kRedCount = 3;

// Deliberately low per-channel value (pre-scaled again by kBrightness at show() time) —
// a status indicator, not a fourth state color, so it should read as clearly dimmer than
// any active G/Y/R section next to it.
constexpr uint8_t kDimWhiteLevel = 25;
}  // namespace

LedController::LedController(uint8_t dataPin, uint16_t numPixels)
    : strip_(numPixels, dataPin, NEO_GRB + NEO_KHZ800) {}

void LedController::begin() {
  strip_.begin();
  strip_.setBrightness(kBrightness);
  strip_.clear();
  strip_.show();  // all off until the first color, avoids a garbage-data flash on boot
  // Boot to Off (dim-white status pixel only, all sections dark) rather than a solid
  // section color — this is the strip variant's own "board is alive" signal, playing the
  // same role the bulb variant's boot-to-red does, just encoded as the always-on status
  // pixel instead of a section color. See led-strip/docs/Implementation-Summary.md
  // "Addressable pixel layout" / "Boot behavior differs intentionally" for why.
  setColor(LightColor::Off);
}

void LedController::setColor(LightColor color) {
  bool alreadyAnimating = (color == LightColor::StalePulse || color == LightColor::CompactFlash) &&
                           color == current_;
  if (alreadyAnimating) {
    return;  // already animating this state — don't reset the animation phase every loop
  }
  current_ = color;

  switch (color) {
    case LightColor::Green:  renderSection(kGreenStart, kGreenCount, 0, 255, 0);     break;
    case LightColor::Yellow: renderSection(kYellowStart, kYellowCount, 255, 255, 0); break;
    case LightColor::Red:    renderSection(kRedStart, kRedCount, 255, 0, 0);         break;
    case LightColor::StalePulse:
    case LightColor::CompactFlash:
      pulsePhaseStartMs_ = millis();
      break;
    case LightColor::Off:
    default: renderSection(0, 0, 0, 0, 0); break;  // no section lit; status pixel still shown
  }
}

void LedController::update() {
  if (current_ == LightColor::StalePulse) {
    uint32_t elapsed = (millis() - pulsePhaseStartMs_) % kPulsePeriodMs;
    float phase = elapsed / static_cast<float>(kPulsePeriodMs);
    float brightness = 0.5f * (1.0f - cosf(phase * 2.0f * PI));  // 0..1 breathing curve
    renderSection(kRedStart, kRedCount, static_cast<uint8_t>(255 * brightness), 0, 0);
  } else if (current_ == LightColor::CompactFlash) {
    uint32_t step = ((millis() - pulsePhaseStartMs_) / kCompactStepMs) % kCompactTotalSteps;

    // Find which pass `step` falls in and the offset within it. Pass k (1-indexed) has
    // (kCompactPixelCount - k) transient steps followed by 1 lock step, so pass sizes count
    // down from kCompactPixelCount to 1 as k goes from 1 to kCompactPixelCount.
    uint16_t offset = step;
    uint16_t pass = 1;
    uint16_t passSize = kCompactPixelCount;
    while (offset >= passSize) {
      offset -= passSize;
      pass++;
      passSize = kCompactPixelCount - pass + 1;
    }
    uint16_t numTransient = kCompactPixelCount - pass;
    bool transientPhase = offset < numTransient;
    uint16_t filledCount = transientPhase ? (pass - 1) : pass;  // pixels 1..filledCount locked on
    // Sweep direction is top-down: the topmost unfilled pixel goes first each pass.
    uint16_t activeIndex = transientPhase ? (kRedStart + kRedCount - 1 - offset) : 0;

    for (uint16_t i = kGreenStart; i <= kRedStart + kRedCount - 1; i++) {
      bool lit = (i <= filledCount) || (transientPhase && i == activeIndex);
      strip_.setPixelColor(i, lit ? strip_.Color(0, 255, 0) : 0);
    }
    strip_.setPixelColor(kStatusPixel, strip_.Color(kDimWhiteLevel, kDimWhiteLevel, kDimWhiteLevel));
    strip_.show();
  }
}

void LedController::renderSection(uint16_t sectionStart, uint16_t sectionCount, uint8_t r, uint8_t g,
                                   uint8_t b) {
  for (uint16_t i = 0; i < strip_.numPixels(); i++) {
    if (i == kStatusPixel) continue;  // set once, below — never part of a color section
    bool inSection = i >= sectionStart && i < sectionStart + sectionCount;
    strip_.setPixelColor(i, inSection ? strip_.Color(r, g, b) : 0);
  }
  strip_.setPixelColor(kStatusPixel, strip_.Color(kDimWhiteLevel, kDimWhiteLevel, kDimWhiteLevel));
  strip_.show();
}
