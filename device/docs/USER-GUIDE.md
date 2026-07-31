# User Guide: Agent Andon Light

Building and running the hardware, start to finish. Parts list: [`BOM.md`](BOM.md).

## Contents

- [User Guide: Agent Andon Light](#user-guide-agent-andon-light)
  - [Contents](#contents)
  - [1. Software Setup](#1-software-setup)
  - [2. Build the Hardware](#2-build-the-hardware)
    - [2a. Fabricated PCB](#2a-fabricated-pcb)
    - [2b. Breadboard Prototype (Optional)](#2b-breadboard-prototype-optional)
  - [3. Flash \& Verify](#3-flash--verify)
  - [Reference](#reference)
    - [Glossary](#glossary)
    - [Pixel Layout](#pixel-layout)
    - [Pitfalls to Avoid](#pitfalls-to-avoid)
    - [OS-Specific Notes](#os-specific-notes)
    - [Wire Protocol Reference](#wire-protocol-reference)

## 1. Software Setup

1. Install the Arduino IDE (2.x).
2. Add the RP2040 board package:
   - Arduino IDE → Preferences → "Additional Board Manager URLs" → add the `arduino-pico` URL.
   - Boards Manager → install "Raspberry Pi Pico/RP2040."
   - Select **"Waveshare RP2040-Zero"** as the board when flashing.
3. Install the NeoPixel library — Tools → Manage Libraries → search "Adafruit NeoPixel" → Install.

## 2. Build the Hardware

Pick the section that matches what you have — do one, not both.

### 2a. Fabricated PCB

Start here if you have the fabricated PCB. The fab's assembly service already placed the LEDs and passives; the RP2040-Zero is the one part you solder on yourself.

The fabricated PCB is a single board — MCU and LED strip together, not two boards joined by wires.

1. Solder the RP2040-Zero's castellated edge pads directly onto the board's matching pads. Solder every pad — the ones carrying signal/power connect the MCU to the board's traces, and any unused ones are purely mechanical.

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
        | <- solder fills the gap between the MCU's
        |    pad and the board's matching pad
        v
     ( o )  <- solder joint
```

**Caution:** let each joint cool a few seconds before touching it, and never bridge two adjacent pads with one solder blob.

That's the whole build — no connector, no cable, no wiring step. The `GPIO1` (`kDataPin`) trace between MCU and LEDs is etched into the PCB itself, fixed by the board layout. Continue to [3. Flash & Verify](#3-flash--verify).

### 2b. Breadboard Prototype (Optional)

Skip this if you have the fabricated PCB — you're already done above. This path validates the firmware against a standalone RP2040-Zero dev board wired by hand to a separate LED strip PCBA — the setup used during development before the custom PCB existed.

1. **Solder header pins onto the RP2040-Zero.** It ships bare — the edge holes are castellated pads, not header pins. Solder at least **5V**, **GND**, and one **GPIO** pin (firmware default `GPIO1`). A male header strip (recommended) lets it plug into a breadboard like any module; soldering wires directly works too but hard-wires it to those specific wires. Let each joint cool before touching it, and never bridge two adjacent pads with one solder blob.

2. **Wire it to the LED strip PCBA:**

   ```txt
    [RP2040-Zero]                    [LED Strip PCBA, 3-pin connector]
      GND o---------------------------o G  (ground)
      5V  o---------------------------o V  (power — NOT 3V3, see below)
      GP1 o---------------------------o S  (signal/data)

      USB-C port -----> cable -----> your computer
   ```

   - Seat the MCU on a breadboard, if you have one.
   - Connect `G` (ground) first.
   - Connect `V` to `5V`/`VBUS`, not `3V3` — 10 addressable LEDs draw more current than `3V3` is meant to supply.
   - Connect `S` to a free GPIO pin, matching `kDataPin` in `andon_light_firmware.ino` (or edit the sketch to match your wiring).
   - Plug in USB-C last, once all 3 wires are connected — powering a half-wired setup risks a short.
   - Optional resistor/capacitor: see [`BOM.md`](BOM.md) items #8–9.

Continue to [3. Flash & Verify](#3-flash--verify).

## 3. Flash & Verify

1. Open `device/firmware/andon_light_firmware/andon_light_firmware.ino` in the Arduino IDE.
2. Select **"Waveshare RP2040-Zero"** as the board, then flash.
3. Open the Serial Monitor (115200 baud, line ending "Newline").
4. Confirm pixel 1 alone lights dim white on boot, and pixels 2-10 are dark.
5. Send `G`, `Y`, `R` — confirm each lights only its own 3-pixel section (2-4 / 5-7 / 8-10), not the whole strip.

You now have a working device. Next: install the host CLI and Claude Code hooks — see the top-level [`README.md`](../../README.md) Quick Start.

## Reference

### Glossary

| Term | Meaning |
| --- | --- |
| MCU (microcontroller) | The chip on your dev board that runs the firmware. On the RP2040-Zero, that's the RP2040. |
| Firmware | The program running *on* the MCU, not on your laptop. Written in C++ (Arduino framework). |
| Dev board | A ready-made PCB with the MCU plus USB and power regulation already wired up. The RP2040-Zero is one. |
| Addressable LED / WS2812 | An LED controlled over a single data wire via a precisely-timed protocol. Many can be daisy-chained on one wire, each set to its own color individually. |
| NeoPixel | Adafruit's name for WS2812-family LEDs, and the Arduino library (`Adafruit_NeoPixel`) that drives them. |
| Data line / signal timing | WS2812 LEDs read color from a sequence of ~800kHz timed pulses — too fast/precise for plain `digitalWrite`, hence the NeoPixel library. |
| Serial / USB CDC | The dev board shows up as a plain serial port over USB, so Python can read/write it directly. No custom driver needed on any OS. |
| Watchdog | A firmware safety timer that resets to a known-safe state if it hasn't heard from the host in too long. |
| KiCad | Free, open-source PCB design software — see [`../hardware/`](../hardware/). |
| PCBA | "PCB Assembly": a bare PCB with all components soldered on. |

### Pixel Layout

| Pixels | Section | Lit by |
| --- | --- | --- |
| 1 | Status | Always on (dim white) |
| 2–4 | Green | `G` |
| 5–7 | Yellow | `Y` |
| 8–10 | Red | `R` / stale-pulse |

| State | Behavior |
| --- | --- |
| `G` (working) | Pixels 2-4 solid green |
| `Y` (waiting) | Pixels 5-7 solid yellow |
| `R` (idle) | Pixels 8-10 solid red |
| Stale (watchdog timeout) | Pixels 8-10 breathe red |
| `C` (compacting) | Chase-fill: pixels light one at a time from pixel 10 down to pixel 2, each pass locking one more pixel starting from pixel 2 upward, until all 9 are lit — then it resets and repeats |

Pixel 1 stays dim white through every state, including right after boot.

If all 10 pixels light the same color at once, that's pre-refinement firmware — reflash from the current `device/firmware/` source.

### Pitfalls to Avoid

| Pitfall | What to know |
| --- | --- |
| `V` wired to `3V3` instead of `5V` | Breadboard build only. The most common wiring mistake — 10 addressable LEDs need the extra current headroom. |
| Flicker or wrong colors on power-up | Usually a data-line signal integrity issue, not a firmware bug. **Fabricated PCB:** check for a cold solder joint on the MCU's pads. **Breadboard:** see the level-shifter fallback in [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) Step 3.5. |
| Wrong connector pinout | Breadboard build only. Read the PCBA's silkscreen labels directly — don't assume pin order from this doc or a photo. |
| Charge-only USB-C cable | Board won't enumerate as a serial port. Try a different cable first. |
| Skipping the Serial Monitor check | It isolates firmware bugs from host-CLI bugs before you add the Python CLI on top. |
| Hooks not resetting the watchdog | Claude Code hooks fire only at discrete moments, not continuously — a long thinking-only stretch with no tool calls can leave the watchdog unfed. `PreToolUse` resets it on every tool call. |

Heartbeat/watchdog isn't optional polish — it's what makes this device trustworthy to walk away from.

### OS-Specific Notes

| OS | CDC driver behavior |
| --- | --- |
| Windows | Enumerates as a COM port with no extra driver install. |
| Linux | Enumerates as `/dev/ttyACM0`; your user needs `dialout` group membership — see [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md). |

### Wire Protocol Reference

| Command | Effect | Meaning |
| --- | --- | --- |
| `G\n` | Solid green | Agent working |
| `Y\n` | Solid yellow | Waiting for human input / permission |
| `R\n` | Solid red | Idle / stopped / session start |
| `C\n` | Flashing green | Compacting (internal maintenance, still alive) |
| `H\n` | No color change | Heartbeat, resets the watchdog |

Watchdog timeout: **30 minutes**.

Hook mapping (rationale: [`../../hooks/README.md`](../../hooks/README.md)):

| Hook event | Color |
| --- | --- |
| `SessionStart` | idle |
| `UserPromptSubmit` / `PreToolUse` | working |
| `Notification` / `PermissionRequest` | waiting |
| `PreCompact` | compacting |
| `Stop` / `SessionEnd` | idle |
