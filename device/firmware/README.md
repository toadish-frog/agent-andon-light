# Firmware — Agent Andon Light

Arduino sketch for the Waveshare RP2040-Zero, implementing the wire protocol (`G`/`Y`/`R`/`C`/`H`) documented in `../docs/Implementation-Summary.md`.

Addressable WS2812-style strip PCBA, 10 LEDs, 3-pin `S`/`V`/`G` connector. An earlier, now-archived interim MVP used 3 discrete bulbs instead — see `../archive/led-bulb-mvp/firmware/` for that history, preserved but not maintained.

## Dependency: Adafruit_NeoPixel

An addressable WS2812-style strip needs sub-microsecond bit timing that the Arduino core can't produce with ordinary `digitalWrite`/`analogWrite` GPIO calls (which is all the archived bulb MVP needed, with no library at all). This sketch uses the **Adafruit_NeoPixel** library (Arduino Library Manager → search "Adafruit NeoPixel" → Install) — the standard, widely-used driver for this exact chip family, with native RP2040/PIO support via `arduino-pico`.

## Setup (once)

1. Arduino IDE 2.x, with the `arduino-pico` board package installed.
2. Install the **Adafruit NeoPixel** library via Library Manager (Tools → Manage Libraries...).
3. Open `andon_light_firmware_strip/andon_light_firmware_strip.ino` — Arduino IDE will load `led_controller.h/.cpp` and `watchdog.h` alongside it as tabs.

## Wiring

The status light is a custom PCBA with a 10-LED addressable strip and a 3-pin connector: `S` (signal/data), `V` (voltage/power), `G` (ground).

- PCBA `G` ← board `GND`
- PCBA `V` ← board `5V`/`VBUS` (**not** `3V3` — see Power note below)
- PCBA `S` ← `GPIO1`

Change the pin in `andon_light_firmware_strip.ino` by editing `kDataPin` if you wire it differently. `GPIO1` is confirmed correct against the real breadboard-wired PCBA (see "Status" below) — still worth double-checking against your own board's silkscreen labels if you rewire it.

### Power note

Pull `V` from the RP2040-Zero's `5V`/`VBUS` pin, not `3V3` — WS2812-style LEDs are rated for ~5V and 10 of them can draw meaningfully more current than the 3 discrete bulbs did. The data line itself runs at 3.3V logic from the RP2040, which most WS2812 clones tolerate fine at short (<~30cm) wire lengths; if you see flicker or wrong colors, the usual fix is a level shifter (e.g. 74HCT125) on the data line, or shortening the wire run. Firmware caps brightness at `kBrightness = 130/255` in `led_controller.cpp` (see the comment there) to keep both current draw and eye comfort reasonable — raise it if the strip is diffused behind a cover.

### Breadboard wiring (as built, confirmed working 2026-07-11)

The RP2040-Zero's pin spacing doesn't straddle the breadboard's center gap, so it sits beside the breadboard rather than seated in it, connected entirely by individual female-to-male Dupont jumpers:

- **`GND`** and **`5V`/`VBUS`** each get their own Dupont jumper straight from the RP2040 into the breadboard's top two power rails (`−` and `+` respectively). These rails run the full length of the board, so anything downstream can tap either rail at whichever hole is most convenient — no need to route wires back to the RP2040's exact pin location.
- **330–470 Ω resistor** (BOM item #8) sits in series on the data line only, entirely separate from the power rails: `GPIO1`'s Dupont jumper lands in one empty main-grid column, one resistor leg goes in that same column, the other resistor leg goes in a second, different empty column, and a final Dupont jumper runs from that second column out to the strip's `S` wire. The gap between the two columns is what forces current through the resistor.
- **100–1000 µF electrolytic capacitor** (BOM item #9, rated ≥6.3V) bridges straight across the `+`/`−` rails, positioned near wherever the strip's own `V`/`G` wires plug in. **Mind polarity** — the leg next to the printed stripe is negative, goes to the `−` rail.
- **No switch.** The only switch-like part on hand was a small 4-pin momentary tactile pushbutton (the clicky kind with hook-style legs) — unsuitable here since it only connects while physically held down, it doesn't latch on/off. Rather than force it into a role it's not built for, power control is just unplugging the strip's `V` Dupont from the `+` rail by hand when the light needs to be off. This is a deliberate choice, not a placeholder for a switch that's still needed.
- The strip's own JST→Dupont cable ends plug in last: `V` → `+` rail, `G` → `−` rail, `S` → the resistor's strip-side column (not the `GPIO1`-side one).

This wiring — RP2040 off-board via individual jumpers, resistor/capacitor added, no switch — is what's currently running and has been confirmed stable on real hardware; it replaced an earlier setup where the strip's Dupont-to-JST connection was just taped to a table and prone to working loose under physical movement.

## Pixel layout: addressable sections, not one solid color

Unlike a first-pass version of this firmware (which used `strip.fill()` to set all 10 pixels to the same color — visually correct-ish, but not actually andon-light behavior, which communicates state by *which* lamp is lit), `G`/`Y`/`R` each own a dedicated 3-pixel sub-range of the strip. `CompactFlash` is the one exception — it animates across all 9 non-status pixels rather than staying inside one section (see below):

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
- **`CompactFlash`** uses all 9 non-status pixels (2-10), not the green section — a chase-fill sequence: a single lit pixel sweeps from pixel 10 down to pixel 2, then locks pixel 2 on; the next sweep goes from 10 down to pixel 3 (skipping the now-locked pixel 2), locks pixel 3, and so on, so pixels accumulate lit from pixel 2 upward, one per pass, until all 9 are lit — then it resets to empty and repeats. See `led_controller.cpp`'s `kCompactPixelCount`/`kCompactStepMs` constants.

See `led_controller.cpp`'s `kGreenStart`/`kYellowStart`/`kRedStart`/`kStatusPixel` constants and `device/docs/Implementation-Summary.md` "Addressable pixel layout" for the full reasoning.

## Flash & test

1. Select "Waveshare RP2040-Zero" as the board, then flash.
2. Open the Serial Monitor at 115200 baud, line ending "Newline".
3. Before sending anything, confirm pixel 1 alone is dim white and pixels 2-10 are dark (boot state). Then type `G`, `Y`, `R` and press enter after each — confirm only that color's 3-pixel section lights up (pixels 2-4 / 5-7 / 8-10 respectively) while the rest of the strip (other than the status pixel) stays dark. Type `C` — confirm a single lit pixel chases from pixel 10 down to pixel 2 and locks on, then repeats sweeping down to pixel 3 with pixel 2 still lit, and so on, until all 9 are lit and it resets. To test the stale-pulse fallback without waiting the full 30 minutes, temporarily lower `kWatchdogTimeoutMs` (e.g. to `15000`), flash, confirm the slow red breathing pulse kicks in on pixels 8-10 after that shorter wait, then change it back to `1800000` and reflash.

## Status: flashed and confirmed working (2026-07-11)

`kDataPin = GPIO1` is correct against the real PCBA — `G`/`Y`/`R` all confirmed lighting the correct 3-pixel section on the physical strip, running through the breadboard wiring described above (resistor + capacitor, no level shifter needed). **Not yet exercised:** `C` (CompactFlash) and the watchdog `StalePulse` animation, and the exact brightness/dim-white values (`kBrightness`, `kDimWhiteLevel`) haven't been explicitly evaluated as "right," just observed as functional — see `../docs/Implementation-Summary.md` §5 "Open questions" for what's still outstanding.

## Wire protocol

```txt
G\n   → pixels 2-4 solid green, rest dark (except status pixel)   (agent working)
Y\n   → pixels 5-7 solid yellow, rest dark (except status pixel)  (waiting for human input / permission)
R\n   → pixels 8-10 solid red, rest dark (except status pixel)    (idle / stopped / quota reached)
C\n   → chase-fill across pixels 2-10, one pixel locked on per pass until all 9 are lit, then resets (compacting — internal maintenance, still alive)
H\n   → heartbeat (no color change, resets watchdog)
```

Watchdog timeout: 30 minutes — see `../docs/Implementation-Summary.md` §2 "Reliability design point" for the reasoning (raised from an initial 15s after real Claude Code sessions showed long tool-call-free thinking stretches false-triggering the stale state).
