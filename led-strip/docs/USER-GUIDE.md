# User Guide & Reminders: Agent Andon Light (LED Strip variant)

Companion to `../../led-bulb/docs/USER-GUIDE.md` — read that one first for the general glossary (MCU, firmware, dev board, Serial/USB CDC, watchdog, KiCad, PCBA) and soldering-pins-first walkthrough, all of which apply unchanged here. This doc only covers what's different for the **addressable LED strip variant**.

## Glossary additions (strip-specific terms)

- **Addressable LED / WS2812** — unlike a discrete LED (plain on/off via one GPIO), an addressable LED is controlled over a single data wire using a precise timed protocol, and many can be daisy-chained on that one wire. This project drives 10 of them, all set to the same color at once (no per-pixel effects), so from across the room it looks and behaves just like the bulb variant.
- **NeoPixel** — Adafruit's name for WS2812-family addressable LEDs, and the name of the Arduino library (`Adafruit_NeoPixel`) used to drive them — see `../firmware/README.md`.
- **Data line / signal timing** — WS2812 LEDs read color data as a sequence of precisely-timed pulses (roughly 800kHz). This is too fast and too precise for plain `digitalWrite` loops to produce reliably, which is why this variant needs the NeoPixel library where the bulb variant didn't need any library at all.

## Phase 1 Setup Checklist (Breadboard MVP)

1. Install the Arduino IDE (2.x) — same as the bulb variant.
2. In Arduino IDE → Preferences → "Additional Board Manager URLs", add the `arduino-pico` board package URL, then install "Raspberry Pi Pico/RP2040" boards via the Boards Manager — select "Waveshare RP2040-Zero" as the board when flashing.
3. **Install the Adafruit NeoPixel library** (Tools → Manage Libraries... → search "Adafruit NeoPixel" → Install). Only needed for this variant, not the bulb one.
4. Wire the PCBA (see "Wiring the LED Strip PCBA" below): PCBA `G` → board `GND`, PCBA `V` → board `5V`/`VBUS` (not `3V3`), PCBA `S` → one board GPIO pin (note it in the sketch — the firmware defaults to `GPIO1`, a placeholder to confirm against your actual wiring).
5. Flash the sketch, open the Serial Monitor, send `G`, `Y`, `R` as single characters — confirm all 10 LEDs light up together in the same solid color.

## Wiring the LED Strip PCBA

Simpler in wire count than the bulb variant (3 wires instead of 4) but more sensitive to power/signal quality since it's driving 10 addressable LEDs instead of 3 discrete ones.

**Reading your boards:** both the RP2040-Zero and the strip PCBA have pin/pad names printed on the silkscreen. Read the actual text on your physical boards — the firmware's default pin number (`GPIO1`) is a placeholder until you confirm it.

```txt
 [RP2040-Zero]                    [LED Strip PCBA, 3-pin connector]
   GND o---------------------------o G  (ground)
   5V  o---------------------------o V  (power — NOT 3V3, see below)
   GP1 o---------------------------o S  (signal/data)

   USB-C port -----> cable -----> your computer
```

1. **Seat/steady the MCU** on a breadboard if you have one handy.
2. **Connect `G` (ground) first.** One wire from the MCU's `GND` pin to the PCBA's `G` pin.
3. **Connect `V` to the MCU's `5V`/`VBUS` pin, not `3V3`.** 10 addressable LEDs can draw noticeably more current than 3V3 is meant to supply on most dev boards — see the Power section in `../firmware/README.md` for the full reasoning.
4. **Connect `S` to one free GPIO pin** — make sure the pin you wire matches `kDataPin` in `andon_light_firmware_strip.ino` (or edit the sketch to match your wiring).
5. **Plug in USB-C last**, once all 3 wires are connected — powering a half-wired setup risks a short.

## Reminders / Pitfalls (strip-specific, in addition to the bulb variant's list)

- **`V` must be 5V, not 3V3.** This is the one wiring mistake specific to this variant that the bulb variant's docs don't warn about, since discrete bulbs don't care about the difference the way 10 addressable LEDs' current draw does.
- **Flicker or wrong colors on first power-up** usually means a data-line signal integrity issue (3.3V logic driving a 5V-rated strip), not a firmware bug — see `../firmware/README.md`'s level-shifter fallback before assuming the code is wrong.
- **All the bulb variant's general reminders still apply**: data-capable USB cable, don't skip the Serial Monitor test before building on the Python CLI, watchdog/heartbeat isn't optional polish, and Claude Code hooks only fire at discrete moments (handled the same way here via the same 30-minute watchdog + `PreToolUse` hook — no changes needed for this variant).

## Quick Reference: Wire Protocol

Identical to the bulb variant — see `../../led-bulb/docs/USER-GUIDE.md` "Quick Reference: Wire Protocol" and "Hook mapping." The only difference is that each command now drives all 10 pixels to the same state instead of 1-3 discrete GPIOs; the host CLI, hook config, and protocol bytes are byte-for-byte identical.
