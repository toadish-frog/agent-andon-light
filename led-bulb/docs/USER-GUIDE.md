# User Guide & Reminders: Agent Andon Light

A companion doc for the "I've never built hardware before" part of this project — terminology, setup steps, and pitfalls to remember. Covers the **3-discrete-bulb variant** — for the addressable LED strip variant, see `../../led-strip/docs/USER-GUIDE.md`. See `Implementation-Summary.md` for the architecture/roadmap, and `BOM.md` for parts.

## Glossary (hardware terms used across this project)

- **MCU (microcontroller)** — the small computer chip on your dev board. The Waveshare RP2040-Zero has one (the RP2040 chip itself). It runs the firmware you write.
- **Firmware** — the program that runs *on* the MCU, as opposed to on your laptop. Written in C++ here, using the Arduino framework.
- **Dev board** — a small ready-made PCB with the MCU plus USB, power regulation, etc. already wired up, so you don't need to design that part yourself. The RP2040-Zero is a dev board.
- **Discrete LED** — a plain single-color LED bulb, as opposed to an addressable RGB LED — you turn it on/off (or dim it) with a normal GPIO pin, no special protocol or library needed. This project uses 3 of them (Red/Yellow/Green) on a custom PCBA instead of an addressable strip.
- **Serial / USB CDC** — a way for the dev board to show up on your computer as a plain "serial port" (like an old-school COM port) over USB, so your Python code can just open it and write/read text, no custom USB driver needed on Linux/macOS.
- **Watchdog** — a safety timer in the firmware that resets to a known-safe state if it doesn't hear from the host software for too long, so the device fails safely instead of freezing on stale data.
- **KiCad** — free, open-source software for designing PCBs (used in Phase 2, not needed for Phase 1's breadboard).
- **PCBA** — "PCB Assembly": a bare PCB with all the components soldered onto it. A PCB fab/assembly service can do this for you from your KiCad files, or you can hand-solder it yourself. You already have one for the 3 status LEDs.

## Phase 1 Setup Checklist (Breadboard MVP)

1. Install the Arduino IDE (2.x).
2. In Arduino IDE → Preferences → "Additional Board Manager URLs", add the `arduino-pico` board package URL, then install "Raspberry Pi Pico/RP2040" boards via the Boards Manager — select "Waveshare RP2040-Zero" as the board when flashing. No LED library needed — the 3 bulbs are driven with plain `digitalWrite`/`analogWrite`.
3. Wire the PCBA (see "Soldering Pins First" and "Wiring the LED PCBA" below for the full walkthrough if this is your first time): PCBA `GND` → board `GND`, PCBA `Red`/`Yellow`/`Green` → 3 board GPIO pins of your choice (note them in the sketch — the firmware defaults to `GPIO1`/`GPIO2`/`GPIO3`, placeholders to confirm against your actual wiring).
4. Flash a simple test sketch that cycles red → yellow → green every 2 seconds. If this works, your hardware is good and everything else is software from here.
5. Open the Arduino Serial Monitor, send `G`, `Y`, `R` as single characters, and confirm the LED responds — this is your firmware's command parser working before Python ever gets involved.

## Soldering Pins First

The Waveshare RP2040-Zero ships **bare** — the holes along its edges are **castellated pads** (plated half-holes), not header pins. Nothing plugs into a breadboard until something is soldered into them. This step comes before any breadboard wiring.

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

Solder at least: **5V**, **GND**, and one **GPIO** pin (the firmware defaults to `GP0`). Read the actual label printed on your board next to each pad — don't guess positions from any diagram, including this one.

Two ways to do it:

- **Solder a male header strip into the pads (recommended).** Once cooled, the board plugs straight into a breadboard like any other module — reusable for future revisions.
- **Solder wires directly into the pads.** Works with no header stock on hand, but that board is now hard-wired to those specific wires — less flexible if you re-wire later.

**Caution:** let the board cool a few seconds after each joint before touching it, and solder 5V and GND on separate pins — never bridge two adjacent pads with one solder blob.

## Wiring the LED PCBA

Much simpler than an addressable strip — 4 wires total, no resistor or capacitor to add (they're already on the PCBA), no shared power rail needed since each LED just needs its own GPIO plus a common ground.

**Reading your boards:** both the RP2040-Zero and the LED PCBA have their pin/pad names printed directly on the silkscreen (tiny white text — `GND`, `GP1`, `Red`, `Green`, etc). Read the actual text on your physical boards rather than matching positions from a photo/tutorial — exact pin placement isn't something to guess at, and the firmware's default pin numbers (`GPIO1`/`GPIO2`/`GPIO3`) are placeholders until you confirm them.

```txt
 [RP2040-Zero]                    [LED PCBA, 4-pin connector]
   GND o---------------------------o GND
   GP1 o---------------------------o Green
   GP2 o---------------------------o Yellow
   GP3 o---------------------------o Red

   USB-C port -----> cable -----> your computer
```

1. **Seat/steady the MCU** on a breadboard if you have one handy — not required electrically, just makes it easier to hold still while wiring.
2. **Connect `GND` first.** One wire from the MCU's `GND` pin to the PCBA's `GND` pin — every other wire's signal is measured relative to this, so get it in before anything else.
3. **Connect the 3 signal wires**, one MCU GPIO pin each to the PCBA's `Red`/`Yellow`/`Green` pins. Any 3 free GPIO pins work — just make sure the pin numbers you wired match `kGreenPin`/`kYellowPin`/`kRedPin` in `andon_light_firmware.ino` (or edit the sketch to match your wiring, whichever's easier).
4. **Plug in USB-C last**, once all 4 wires are connected — powering a half-wired setup risks a short.

## Reminders / Pitfalls

- **Confirm the connector pinout before plugging in.** Don't assume pin order from this doc or a photo — read the PCBA's silkscreen labels directly, and double check `GND` isn't accidentally landed on a signal pin (or vice versa) before powering on.
- **Data-capable cable, always.** Many USB-C cables are charge-only. If the board doesn't enumerate as a serial port on your computer, try a different cable before debugging code.
- **Don't skip the Serial Monitor step** (Phase 1, step 6) even though it feels redundant with building the Python CLI next — it isolates firmware bugs from host-software bugs, which matters a lot the first time you're debugging both halves of a system you've never built before.
- **Windows CDC driver:** if the board doesn't show up in Device Manager as a COM port, the `arduino-pico` package usually installs the right driver automatically; if not, that's the first thing to search for by exact board name + "Windows driver".
- **Heartbeat/watchdog isn't optional polish** — it's what makes this device trustworthy to walk away from. Don't defer it past Phase 4 in practice even if the roadmap lists it later; a status light that can silently go stale is worse than no status light.
- **Claude Code hooks only fire at discrete moments, not continuously.** Real-world testing (2026-07-07) showed the light falsely dropping to the stale-pulse mid-turn, because nothing resets the watchdog during a long stretch of the model just thinking with no tool calls in between hook events. Fixed by adding a `PreToolUse` hook (kicks the watchdog on every tool call) and raising the watchdog timeout from 15s to 30 minutes — see `../firmware/README.md` and `../../hooks/README.md`.

## Quick Reference: Wire Protocol (v1)

```text
G\n   solid green    → agent working
Y\n   solid yellow   → waiting for human input / permission
R\n   solid red      → idle / stopped / quota reached / default at session start
C\n   flashing green → compacting (internal maintenance, still alive)
H\n   heartbeat      → no color change, resets the watchdog timer
```

Watchdog timeout: **30 minutes** (raised from an initial 15s once real Claude Code sessions showed long thinking-only stretches falsely triggering the stale state).

Hook mapping (fine-tuned 2026-07-07 from real usage — see `../../hooks/README.md`): `SessionStart`→idle, `UserPromptSubmit`/`PreToolUse`→working, `Notification`/`PermissionRequest`→waiting, `PostCompact`→compacting, `Stop`→idle.
