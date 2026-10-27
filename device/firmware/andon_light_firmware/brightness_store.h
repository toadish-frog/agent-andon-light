#pragma once

#include <Arduino.h>
#include <EEPROM.h>

// Persists the user-set brightness percent across power cycles. arduino-pico emulates
// EEPROM in the last flash sector, so every commit() is a real flash erase/write — save()
// only commits when the value actually changes, and that only happens on an explicit
// `B<n>` command, never per hook call, so flash wear isn't a concern in practice.
class BrightnessStore {
 public:
  BrightnessStore(uint8_t defaultPercent, uint8_t minPercent, uint8_t maxPercent)
      : defaultPercent_(defaultPercent), minPercent_(minPercent), maxPercent_(maxPercent) {}

  void begin() { EEPROM.begin(kEepromSize); }

  // Erased flash reads back as 0xFF, so the magic byte tells "never saved" apart from a
  // real stored value. Anything missing or out of range falls back to the default.
  uint8_t load() const {
    if (EEPROM.read(kMagicAddr) != kMagic) return defaultPercent_;
    uint8_t percent = EEPROM.read(kPercentAddr);
    if (percent < minPercent_ || percent > maxPercent_) return defaultPercent_;
    return percent;
  }

  void save(uint8_t percent) {
    if (EEPROM.read(kMagicAddr) == kMagic && EEPROM.read(kPercentAddr) == percent) return;
    EEPROM.write(kMagicAddr, kMagic);
    EEPROM.write(kPercentAddr, percent);
    EEPROM.commit();
  }

 private:
  static constexpr size_t kEepromSize = 256;  // arduino-pico minimum emulated size
  static constexpr int kMagicAddr = 0;
  static constexpr int kPercentAddr = 1;
  static constexpr uint8_t kMagic = 0xA5;

  uint8_t defaultPercent_;
  uint8_t minPercent_;
  uint8_t maxPercent_;
};
