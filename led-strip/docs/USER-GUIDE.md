# User Guide & Reminders: Agent Andon Light (LED Strip variant)

Companion to `../../led-bulb/docs/USER-GUIDE.md` — read that one first for the general glossary (MCU, firmware, dev board, Serial/USB CDC, watchdog, KiCad, PCBA) and soldering-pins-first walkthrough, all of which apply unchanged here. This doc only covers what's different for the **addressable LED strip variant**.

## Glossary additions (strip-specific terms)

- **Addressable LED / WS2812** — unlike a discrete LED (plain on/off via one GPIO), an addressable LED is controlled over a single data wire using a precise timed protocol, and many can be daisy-chained on that one wire, each individually settable to its own color. This project uses that per-pixel control to split the 10-pixel strip into dedicated sections — see "Pixel layout" below — rather than setting every pixel to the same color at once.
- **NeoPixel** — Adafruit's name for WS2812-family addressable LEDs, and the name of the Arduino library (`Adafruit_NeoPixel`) used to drive them — see `../firmware/README.md`.
- **Data line / signal timing** — WS2812 LEDs read color data as a sequence of precisely-timed pulses (roughly 800kHz). This is too fast and too precise for plain `digitalWrite` loops to produce reliably, which is why this variant needs the NeoPixel library where the bulb variant didn't need any library at all.

## Phase 1 Setup Checklist (Breadboard MVP)

1. Install the Arduino IDE (2.x) — same as the bulb variant.
2. In Arduino IDE → Preferences → "Additional Board Manager URLs", add the `arduino-pico` board package URL, then install "Raspberry Pi Pico/RP2040" boards via the Boards Manager — select "Waveshare RP2040-Zero" as the board when flashing.
3. **Install the Adafruit NeoPixel library** (Tools → Manage Libraries... → search "Adafruit NeoPixel" → Install). Only needed for this variant, not the bulb one.
4. Wire the PCBA (see "Wiring the LED Strip PCBA" below): PCBA `G` → board `GND`, PCBA `V` → board `5V`/`VBUS` (not `3V3`), PCBA `S` → one board GPIO pin (note it in the sketch — the firmware defaults to `GPIO1`, a placeholder to confirm against your actual wiring).
5. Flash the sketch, open the Serial Monitor. Before sending anything, confirm pixel 1 alone is lit dim white (boot state — see "Pixel layout" below). Then send `G`, `Y`, `R` as single characters — confirm each one lights only its own 3-pixel section (2-4 / 5-7 / 8-10), not the whole strip.

## Pixel layout

The strip is addressable, so each state lights a dedicated sub-range instead of the whole strip:

```txt
pixel:   1           2   3   4     5   6   7      8   9   10
role:    status       green section    yellow section    red section
lit by:  always on    G                Y                  R / stale-pulse
```

- **Pixel 1** is a dim white "board is powered and running" indicator — it's on in every state, including right after boot before any command has been sent.
- **`G`** → pixels 2-4 solid green (pixels 5-10 dark, except pixel 1).
- **`Y`** → pixels 5-7 solid yellow (pixels 2-4 and 8-10 dark, except pixel 1).
- **`R`** → pixels 8-10 solid red (pixels 2-7 dark, except pixel 1).
- **Stale/watchdog timeout** → pixels 8-10 breathe red (same section as `R`, pulsing instead of solid).
- **Compacting** → not confined to the green section like the other states — a single lit pixel chases from pixel 10 down to pixel 2 and locks on, then the next pass sweeps down to pixel 3 (pixel 2 still lit) and locks pixel 3, and so on. Pixels fill in from pixel 2 upward, one per pass, until all 9 non-status pixels are lit, then it resets to empty and repeats — a "still working" progress feel rather than a flat blink.

If you see all 10 pixels the same color at once, that's the old (pre-refinement) firmware behavior — reflash from the current `led-strip/firmware/` source to get the sectioned layout described above.

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

Identical to the bulb variant — see `../../led-bulb/docs/USER-GUIDE.md` "Quick Reference: Wire Protocol" and "Hook mapping." The only difference is that each command now drives its own dedicated 3-pixel section of the strip (see "Pixel layout" above) instead of 1-3 discrete GPIOs; the host CLI, hook config, and protocol bytes are byte-for-byte identical.
