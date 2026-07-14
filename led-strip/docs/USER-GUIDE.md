# User Guide & Reminders: Agent Andon Light

A companion doc for the "I've never built hardware before" part of this project — terminology, setup steps, and pitfalls to remember. See `Implementation-Summary.md` for the architecture/roadmap, and `BOM.md` for parts.

## Glossary (hardware terms used across this project)

- **MCU (microcontroller)** — the small computer chip on your dev board. The Waveshare RP2040-Zero has one (the RP2040 chip itself). It runs the firmware you write.
- **Firmware** — the program that runs *on* the MCU, as opposed to on your laptop. Written in C++ here, using the Arduino framework.
- **Dev board** — a small ready-made PCB with the MCU plus USB, power regulation, etc. already wired up, so you don't need to design that part yourself. The RP2040-Zero is a dev board.
- **Addressable LED / WS2812** — unlike a plain on/off LED, an addressable LED is controlled over a single data wire using a precise timed protocol, and many can be daisy-chained on that one wire, each individually settable to its own color. This project uses that per-pixel control to split the 10-pixel strip into dedicated sections — see "Pixel layout" below — rather than setting every pixel to the same color at once.
- **NeoPixel** — Adafruit's name for WS2812-family addressable LEDs, and the name of the Arduino library (`Adafruit_NeoPixel`) used to drive them — see `../firmware/README.md`.
- **Data line / signal timing** — WS2812 LEDs read color data as a sequence of precisely-timed pulses (roughly 800kHz). Too fast and too precise for plain `digitalWrite` loops, which is why this project needs the NeoPixel library.
- **Serial / USB CDC** — a way for the dev board to show up on your computer as a plain "serial port" (like an old-school COM port) over USB, so your Python code can just open it and write/read text, no custom USB driver needed on Linux/macOS.
- **Watchdog** — a safety timer in the firmware that resets to a known-safe state if it doesn't hear from the host software for too long, so the device fails safely instead of freezing on stale data.
- **KiCad** — free, open-source software for designing PCBs. This project's schematic/PCB were hand-drawn in KiCad's GUI (see `Implementation-Summary.md` §5 Phase 5) — see `../hardware/`.
- **PCBA** — "PCB Assembly": a bare PCB with all the components soldered onto it. A PCB fab/assembly service can do this for you from your KiCad files, or you can hand-solder it yourself.

## Phase 1 Setup Checklist (Breadboard MVP)

1. Install the Arduino IDE (2.x).
2. In Arduino IDE → Preferences → "Additional Board Manager URLs", add the `arduino-pico` board package URL, then install "Raspberry Pi Pico/RP2040" boards via the Boards Manager — select "Waveshare RP2040-Zero" as the board when flashing.
3. **Install the Adafruit NeoPixel library** (Tools → Manage Libraries... → search "Adafruit NeoPixel" → Install).
4. Wire the PCBA (see "Soldering Pins First" and "Wiring the LED Strip PCBA" below for the full walkthrough if this is your first time): PCBA `G` → board `GND`, PCBA `V` → board `5V`/`VBUS` (not `3V3`), PCBA `S` → one board GPIO pin (note it in the sketch — the firmware defaults to `GPIO1`, a placeholder to confirm against your actual wiring).
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
- **Compacting** → not confined to the green section like the other states — a single lit pixel chases from pixel 10 down to pixel 2 and locks on, then the next pass sweeps down to pixel 3 (pixel 2 still lit) and locks pixel 3, and so on. Pixels fill in from pixel 2 upward, one per pass, until all 9 non-status pixels are lit, then it resets to empty and repeats.

If you see all 10 pixels the same color at once, that's old (pre-refinement) firmware — reflash from the current `led-strip/firmware/` source to get the sectioned layout described above.

## Soldering Pins First

The Waveshare RP2040-Zero ships **bare** — the holes along its edges are **castellated pads** (plated half-holes), not header pins. Nothing plugs into a breadboard until something is soldered into them.

Board edge, cross-section of one pad:

```txt
   top of board
        |
        v
   ______________
  |              |
  |   PCB body   |___
  |  (green)     |   \___ castellated half-hole
  |______________|       (plated copper inside)
        |
        | <- header pin inserted through the hole,
        |    then soldered so solder fills the gap
        v
     ( o )  <- solder joint (shiny blob once cooled)
```

Solder at least: **5V**, **GND**, and one **GPIO** pin (the firmware defaults to `GPIO1`). Read the actual label printed on your board next to each pad — don't guess positions from any diagram, including this one.

Two ways to do it:

- **Solder a male header strip into the pads (recommended).** Once cooled, the board plugs straight into a breadboard like any other module — reusable for future revisions.
- **Solder wires directly into the pads.** Works with no header stock on hand, but that board is now hard-wired to those specific wires — less flexible if you re-wire later.

**Caution:** let the board cool a few seconds after each joint before touching it, and solder 5V and GND on separate pins — never bridge two adjacent pads with one solder blob.

(For the current custom PCB, the RP2040-Zero is soldered directly onto the board itself — this section is about the earlier breadboard/prototype wiring stage, not the final PCBA.)

## Wiring the LED Strip PCBA

3 wires total: no resistor or capacitor to hand-add on the breadboard version (they're recommended inline on the data/power lines, per `BOM.md` items #8-9), no shared power rail beyond `V`/`G`.

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
3. **Connect `V` to the MCU's `5V`/`VBUS` pin, not `3V3`.** 10 addressable LEDs can draw noticeably more current than `3V3` is meant to supply on most dev boards — see the Power section in `../firmware/README.md` for the full reasoning.
4. **Connect `S` to one free GPIO pin** — make sure the pin you wire matches `kDataPin` in `andon_light_firmware_strip.ino` (or edit the sketch to match your wiring).
5. **Plug in USB-C last**, once all 3 wires are connected — powering a half-wired setup risks a short.

## Reminders / Pitfalls

- **`V` must be 5V, not 3V3.** The most common wiring mistake — 10 addressable LEDs' current draw needs it.
- **Flicker or wrong colors on first power-up** usually means a data-line signal integrity issue (3.3V logic driving a 5V-rated strip), not a firmware bug — see `../firmware/README.md`'s level-shifter fallback before assuming the code is wrong.
- **Confirm the connector pinout before plugging in.** Don't assume pin order from this doc or a photo — read the PCBA's silkscreen labels directly, and double-check `G` isn't accidentally landed on a signal pin (or vice versa) before powering on.
- **Data-capable cable, always.** Many USB-C cables are charge-only. If the board doesn't enumerate as a serial port, try a different cable before debugging code.
- **Don't skip the Serial Monitor step** (Phase 1, step 5) even though it feels redundant with building the Python CLI next — it isolates firmware bugs from host-software bugs.
- **Windows CDC driver:** if the board doesn't show up in Device Manager as a COM port, the `arduino-pico` package usually installs the right driver automatically; if not, search by exact board name + "Windows driver".
- **Heartbeat/watchdog isn't optional polish** — it's what makes this device trustworthy to walk away from.
- **Claude Code hooks only fire at discrete moments, not continuously.** Real-world testing (2026-07-07) showed the light falsely dropping to the stale-pulse mid-turn, because nothing resets the watchdog during a long stretch of the model just thinking with no tool calls in between hook events. Fixed by adding a `PreToolUse` hook (kicks the watchdog on every tool call) and raising the watchdog timeout from 15s to 30 minutes — see `../firmware/README.md` and `../../hooks/README.md`.

## Quick Reference: Wire Protocol

```text
G\n   solid green    → agent working
Y\n   solid yellow   → waiting for human input / permission
R\n   solid red      → idle / stopped / quota reached / default at session start
C\n   flashing green → compacting (internal maintenance, still alive)
H\n   heartbeat      → no color change, resets the watchdog timer
```

Watchdog timeout: **30 minutes** (raised from an initial 15s once real Claude Code sessions showed long thinking-only stretches falsely triggering the stale state).

Hook mapping (fine-tuned 2026-07-07/08 from real usage — see `../../hooks/README.md`): `SessionStart`→idle, `UserPromptSubmit`/`PreToolUse`→working, `Notification`/`PermissionRequest`→waiting, `PostCompact`→compacting, `Stop`/`SessionEnd`→idle.
