# Firmware: Agent Andon Light

Arduino sketch for the Waveshare RP2040-Zero — drives a 10-LED addressable WS2812 strip via Adafruit_NeoPixel, speaking the wire protocol below over USB serial.

An earlier iteration used 3 discrete bulbs instead of an addressable strip — see [`../../archive/led-bulb-mvp/firmware/`](../../archive/led-bulb-mvp/firmware/) for that firmware, preserved but not maintained.

**This doc covers firmware only** (code, dependency, flashing, protocol). For physically building the device — soldering, wiring — see [`../docs/USER-GUIDE.md`](../docs/USER-GUIDE.md), the single source of truth for hardware assembly.

## Contents

- [Dependency: Adafruit_NeoPixel](#dependency-adafruit_neopixel)
- [Setup](#setup)
- [Flash & Test](#flash--test)
- [Reference](#reference)
  - [Power](#power)
  - [Pixel Layout](#pixel-layout)
  - [Wire Protocol Reference](#wire-protocol-reference)

## Dependency: Adafruit_NeoPixel

WS2812-style LEDs need sub-microsecond bit timing that plain `digitalWrite`/`analogWrite` can't produce. This sketch uses **Adafruit_NeoPixel** (Arduino Library Manager → search "Adafruit NeoPixel" → Install) — the standard driver for this chip family, with native RP2040/PIO support via `arduino-pico`.

## Setup

1. Arduino IDE 2.x, with the `arduino-pico` board package installed.
2. Install the Adafruit NeoPixel library (Tools → Manage Libraries).
3. Open `andon_light_firmware/andon_light_firmware.ino` — Arduino IDE loads `led_controller.h/.cpp` and `watchdog.h` alongside it as tabs.

Building the physical board (soldering the MCU on, or wiring a breadboard prototype) happens in [`../docs/USER-GUIDE.md`](../docs/USER-GUIDE.md) §2, before you get to Flash & Test below.

## Flash & Test

1. Select "Waveshare RP2040-Zero" as the board, then flash.
2. Open the Serial Monitor at 115200 baud, line ending "Newline".
3. Confirm pixel 1 alone is dim white and pixels 2-10 are dark (boot state).
4. Type `G`, `Y`, `R`, pressing enter after each — confirm only that color's 3-pixel section lights, rest stays dark.
5. Type `C` — confirm the chase-fill sweep described in [Pixel Layout](#pixel-layout) below.
6. To test `StalePulse` without waiting 30 minutes: temporarily set `kWatchdogTimeoutMs` to `15000`, flash, confirm the breathing red pulse on pixels 8-10, then set it back to `1800000` and reflash.

## Reference

### Power

Brightness is capped at `kBrightness = 130/255` (`led_controller.cpp`) for current draw and eye comfort — raise it if the strip is diffused behind a cover. If you're seeing flicker or wrong colors, that's a hardware issue (solder joint or wiring, depending on your build) — see [`../docs/USER-GUIDE.md`](../docs/USER-GUIDE.md) Pitfalls to Avoid, not a firmware setting.

### Pixel Layout

| Pixel | Role | Color |
| --- | --- | --- |
| 1 | Status, always on | Dim white |
| 2-4 | Green section | `G` → RGB(0,255,0) |
| 5-7 | Yellow section | `Y` → RGB(255,255,0) |
| 8-10 | Red section | `R` → RGB(255,0,0); watchdog stale → breathing red |

- Pixel 1 stays dim white through every state, including `Off` — a "board powered, firmware running" indicator, independent of the `G`/`Y`/`R` state color.
- `G`/`Y`/`R` each light only their own section; every other section (except pixel 1) goes dark.
- `StalePulse` (watchdog timeout) breathes the red section (8-10) with the same cosine curve, confined to that section.
- `CompactFlash` uses all 9 non-status pixels (2-10): a single lit pixel sweeps from pixel 10 down to pixel 2 and locks, the next sweep locks pixel 3 (skipping the now-locked pixel 2), and so on — pixels accumulate lit from pixel 2 upward, one per pass, until all 9 are lit, then it resets and repeats. See `kCompactPixelCount`/`kCompactStepMs` in `led_controller.cpp`.

See `led_controller.cpp`'s `kGreenStart`/`kYellowStart`/`kRedStart`/`kStatusPixel` constants for the implementation.

### Wire Protocol Reference

| Command | Effect | Meaning |
| --- | --- | --- |
| `G\n` | Pixels 2-4 solid green | Agent working |
| `Y\n` | Pixels 5-7 solid yellow | Waiting for human input / permission |
| `R\n` | Pixels 8-10 solid red | Idle / stopped / quota reached |
| `C\n` | Chase-fill across pixels 2-10 | Compacting — internal maintenance, still alive |
| `H\n` | No color change | Heartbeat, resets the watchdog |

Watchdog timeout: **30 minutes**.
