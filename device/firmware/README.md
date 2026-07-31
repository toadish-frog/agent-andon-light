# Firmware: Agent Andon Light

Arduino sketch for the Waveshare RP2040-Zero — drives a 10-LED addressable WS2812 strip via Adafruit_NeoPixel, speaking the wire protocol below over USB serial.

An earlier iteration used 3 discrete bulbs instead of an addressable strip — see [`../../archive/led-bulb-mvp/firmware/`](../../archive/led-bulb-mvp/firmware/) for that firmware, preserved but not maintained.

## Contents

- [Firmware: Agent Andon Light](#firmware-agent-andon-light)
  - [Contents](#contents)
  - [Dependency: Adafruit\_NeoPixel](#dependency-adafruit_neopixel)
  - [Setup](#setup)
  - [Wiring](#wiring)
    - [Power](#power)
    - [Breadboard Wiring (Prototype Stage)](#breadboard-wiring-prototype-stage)
  - [Pixel Layout](#pixel-layout)
  - [Flash \& Test](#flash--test)
  - [Wire Protocol Reference](#wire-protocol-reference)

## Dependency: Adafruit_NeoPixel

WS2812-style LEDs need sub-microsecond bit timing that plain `digitalWrite`/`analogWrite` can't produce. This sketch uses **Adafruit_NeoPixel** (Arduino Library Manager → search "Adafruit NeoPixel" → Install) — the standard driver for this chip family, with native RP2040/PIO support via `arduino-pico`.

## Setup

1. Arduino IDE 2.x, with the `arduino-pico` board package installed.
2. Install the Adafruit NeoPixel library (Tools → Manage Libraries).
3. Open `andon_light_firmware/andon_light_firmware.ino` — Arduino IDE loads `led_controller.h/.cpp` and `watchdog.h` alongside it as tabs.

## Wiring

The status light is a custom PCBA with a 10-LED addressable strip and a 3-pin connector.

| PCBA pin | Connects to | Note |
| --- | --- | --- |
| `G` | Board `GND` | — |
| `V` | Board `5V`/`VBUS` | **Not** `3V3` — see Power below |
| `S` | `GPIO1` (`kDataPin`) | Edit `kDataPin` in the sketch if wired differently |

### Power

Pull `V` from `5V`/`VBUS`, not `3V3` — WS2812-style LEDs are rated ~5V, and 10 of them draw meaningfully more current than `3V3` is meant to supply. The data line runs at 3.3V logic, which most WS2812 clones tolerate fine at short (<~30cm) wire lengths; flicker or wrong colors usually means a level shifter (e.g. 74HCT125) is needed on the data line, or the wire run is too long. Firmware caps brightness at `kBrightness = 130/255` (`led_controller.cpp`) for current draw and eye comfort — raise it if the strip is diffused behind a cover.

### Breadboard Wiring (Prototype Stage)

The RP2040-Zero's pin spacing doesn't straddle the breadboard's center gap, so it sits beside the breadboard, connected entirely by female-to-male Dupont jumpers:

- **`GND` and `5V`/`VBUS`** each get their own jumper into the breadboard's top power rails (`−` and `+`). Anything downstream taps either rail at whatever hole is convenient.
- **330–470 Ω resistor** (optional, [`BOM.md`](../docs/BOM.md) item #8) sits in series on the data line only: `GPIO1`'s jumper lands in one empty grid column, one resistor leg in that column, the other leg in a second column, and a final jumper runs from that second column to the strip's `S` wire.
- **100–1000 µF electrolytic capacitor** (optional, [`BOM.md`](../docs/BOM.md) item #9, ≥6.3V) bridges the `+`/`−` rails near the strip's `V`/`G` connection. **Polarized** — the leg next to the printed stripe is negative, goes to `−`.
- **No power switch** — toggling power is unplugging the strip's `V` jumper from the `+` rail by hand.
- The strip's JST→Dupont cable plugs in last: `V` → `+` rail, `G` → `−` rail, `S` → the resistor's strip-side column.

The fabricated PCB has the RP2040-Zero soldered directly onto it — this section covers the breadboard/prototype stage only.

## Pixel Layout

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

## Flash & Test

1. Select "Waveshare RP2040-Zero" as the board, then flash.
2. Open the Serial Monitor at 115200 baud, line ending "Newline".
3. Confirm pixel 1 alone is dim white and pixels 2-10 are dark (boot state).
4. Type `G`, `Y`, `R`, pressing enter after each — confirm only that color's 3-pixel section lights, rest stays dark.
5. Type `C` — confirm the chase-fill sweep described above.
6. To test `StalePulse` without waiting 30 minutes: temporarily set `kWatchdogTimeoutMs` to `15000`, flash, confirm the breathing red pulse on pixels 8-10, then set it back to `1800000` and reflash.

## Wire Protocol Reference

| Command | Effect | Meaning |
| --- | --- | --- |
| `G\n` | Pixels 2-4 solid green | Agent working |
| `Y\n` | Pixels 5-7 solid yellow | Waiting for human input / permission |
| `R\n` | Pixels 8-10 solid red | Idle / stopped / quota reached |
| `C\n` | Chase-fill across pixels 2-10 | Compacting — internal maintenance, still alive |
| `H\n` | No color change | Heartbeat, resets the watchdog |

Watchdog timeout: **30 minutes**.
