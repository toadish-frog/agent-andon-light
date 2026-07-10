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

## Pixel layout: addressable sections, not one solid color

Unlike a first-pass version of this firmware (which used `strip.fill()` to set all 10 pixels to the same color — visually correct-ish, but not actually andon-light behavior, which communicates state by *which* lamp is lit), each color owns a dedicated sub-range of the strip:

```txt
pixel:   1        2  3  4        5  6  7        8  9  10
role:    status    green section    yellow section    red section
color:   dim white 0,255,0 (G)      255,255,0 (Y)      255,0,0 (R)
```

- **Pixel 1 is always dim white**, regardless of state — it's a "board is powered and firmware is running" indicator, separate from the G/Y/R state color. It stays lit through every state, including `Off`.
- **`G`** lights pixels 2-4 green; pixels 5-10 go dark.
- **`Y`** lights pixels 5-7 yellow; pixels 2-4 and 8-10 go dark.
- **`R`** lights pixels 8-10 red; pixels 2-7 go dark.
- **`StalePulse`** (watchdog timeout) breathes the red section (8-10), same cosine curve as before, just confined to that section instead of the whole strip.
- **`CompactFlash`** blinks the green section (2-4) on/off, same square-wave as before, confined to that section.

See `led_controller.cpp`'s `kGreenStart`/`kYellowStart`/`kRedStart`/`kStatusPixel` constants and `led-strip/docs/Implementation-Summary.md` "Addressable pixel layout" for the full reasoning.

## Flash & test

1. Select "Waveshare RP2040-Zero" as the board, then flash.
2. Open the Serial Monitor at 115200 baud, line ending "Newline".
3. Before sending anything, confirm pixel 1 alone is dim white and pixels 2-10 are dark (boot state). Then type `G`, `Y`, `R` and press enter after each — confirm only that color's 3-pixel section lights up (pixels 2-4 / 5-7 / 8-10 respectively) while the rest of the strip (other than the status pixel) stays dark. To test the stale-pulse fallback without waiting the full 30 minutes, temporarily lower `kWatchdogTimeoutMs` (e.g. to `15000`), flash, confirm the slow red breathing pulse kicks in on pixels 8-10 after that shorter wait, then change it back to `1800000` and reflash.

## Status: not yet flashed/tested on real hardware

Written against the same protocol and `LightColor` semantics as the validated bulb variant, but **`kDataPin` and the whole strip path are unconfirmed** — this needs a real flash-and-observe pass before being trusted, per this project's standing rule of validating hardware/timing assumptions against actual behavior rather than reasoning alone.

## Wire protocol (identical to the bulb variant)

```txt
G\n   → pixels 2-4 solid green, rest dark (except status pixel)   (agent working)
Y\n   → pixels 5-7 solid yellow, rest dark (except status pixel)  (waiting for human input / permission)
R\n   → pixels 8-10 solid red, rest dark (except status pixel)    (idle / stopped / quota reached)
C\n   → pixels 2-4 flashing green, rest dark (except status pixel) (compacting — internal maintenance, still alive)
H\n   → heartbeat (no color change, resets watchdog)
```

Watchdog timeout: 30 minutes, same value and same reasoning as the bulb variant — see `../../led-bulb/firmware/README.md`.
