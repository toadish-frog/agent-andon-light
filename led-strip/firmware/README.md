# Firmware — Agent Andon Light (LED Strip variant)

Arduino sketch for the Waveshare RP2040-Zero, implementing the same v2 wire protocol as the bulb variant (`G`/`Y`/`R`/`C`/`H`) — see `../docs/Implementation-Summary.md`.

This is the **addressable LED strip variant** (WS2812-style strip PCBA, 10 LEDs, 3-pin `S`/`V`/`G` connector). For the 3-discrete-bulb variant, see `../../led-bulb/firmware/`.

## Dependency: Adafruit_NeoPixel

Unlike the bulb variant (plain `digitalWrite`/`analogWrite`, no library), an addressable WS2812-style strip needs sub-microsecond bit timing that the Arduino core can't produce with ordinary GPIO calls. This sketch uses the **Adafruit_NeoPixel** library (Arduino Library Manager → search "Adafruit NeoPixel" → Install) — the standard, widely-used driver for this exact chip family, with native RP2040/PIO support via `arduino-pico`. This is a deliberate, single new dependency, scoped only to this sketch folder — it does not touch the bulb variant's firmware, the host CLI, or the hooks config at all.

## Setup (once)

1. Arduino IDE 2.x, with the `arduino-pico` board package installed (same as the bulb variant).
2. Install the **Adafruit NeoPixel** library via Library Manager (Tools → Manage Libraries...).
3. Open `andon_light_firmware_strip/andon_light_firmware_strip.ino` — Arduino IDE will load `led_controller.h/.cpp` and `watchdog.h` alongside it as tabs.

## Wiring

The status light is a custom PCBA with a 10-LED addressable strip and a 3-pin connector: `S` (signal/data), `V` (voltage/power), `G` (ground).

- PCBA `G` ← board `GND`
- PCBA `V` ← board `5V`/`VBUS` (**not** `3V3` — see Power note below)
- PCBA `S` ← `GPIO1`

Change the pin in `andon_light_firmware_strip.ino` by editing `kDataPin` if you wire it differently. **`GPIO1` is a placeholder, unconfirmed against real hardware** — confirm it against your PCBA's actual silkscreen labels before trusting it, same as the bulb variant's pins were before they were validated on real hardware.

### Power note

Pull `V` from the RP2040-Zero's `5V`/`VBUS` pin, not `3V3` — WS2812-style LEDs are rated for ~5V and 10 of them can draw meaningfully more current than the 3 discrete bulbs did. The data line itself runs at 3.3V logic from the RP2040, which most WS2812 clones tolerate fine at short (<~30cm) wire lengths; if you see flicker or wrong colors, the usual fix is a level shifter (e.g. 74HCT125) on the data line, or shortening the wire run. Firmware caps brightness at `kBrightness = 130/255` in `led_controller.cpp` (see the comment there) to keep both current draw and eye comfort reasonable — raise it if the strip is diffused behind a cover.

## Flash & test

1. Select "Waveshare RP2040-Zero" as the board, then flash.
2. Open the Serial Monitor at 115200 baud, line ending "Newline".
3. Type `G`, `Y`, `R` and press enter — confirm all 10 LEDs light up the same solid color together. To test the stale-pulse fallback without waiting the full 30 minutes, temporarily lower `kWatchdogTimeoutMs` (e.g. to `15000`), flash, confirm the slow red breathing pulse kicks in after that shorter wait, then change it back to `1800000` and reflash.

## Status: not yet flashed/tested on real hardware

Written against the same protocol and `LightColor` semantics as the validated bulb variant, but **`kDataPin` and the whole strip path are unconfirmed** — this needs a real flash-and-observe pass before being trusted, per this project's standing rule of validating hardware/timing assumptions against actual behavior rather than reasoning alone.

## Wire protocol (identical to the bulb variant)

```txt
G\n   → all 10 pixels solid green    (agent working)
Y\n   → all 10 pixels solid yellow   (waiting for human input / permission)
R\n   → all 10 pixels solid red      (idle / stopped / quota reached)
C\n   → all 10 pixels flashing green (compacting — internal maintenance, still alive)
H\n   → heartbeat (no color change, resets watchdog)
```

Watchdog timeout: 30 minutes, same value and same reasoning as the bulb variant — see `../../led-bulb/firmware/README.md`.
