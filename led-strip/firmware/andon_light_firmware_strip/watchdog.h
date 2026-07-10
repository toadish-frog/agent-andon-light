#pragma once

#include <Arduino.h>

class Watchdog {
 public:
  explicit Watchdog(uint32_t timeoutMs) : timeoutMs_(timeoutMs) {}

  void kick() { lastKickMs_ = millis(); }
  bool isStale() const { return millis() - lastKickMs_ > timeoutMs_; }

 private:
  uint32_t timeoutMs_;
  uint32_t lastKickMs_ = 0;
};
