# User Guide: Agent Andon Light

Building the hardware — terminology, setup, wiring, and pitfalls to know before you start. Parts list: [`BOM.md`](BOM.md).

## Contents

- [Glossary](#glossary)
- [Setup Checklist](#setup-checklist)
- [Pixel Layout](#pixel-layout)
- [Soldering the Pins](#soldering-the-pins)
- [Wiring the LED Strip](#wiring-the-led-strip)
- [Pitfalls to Avoid](#pitfalls-to-avoid)
- [OS-Specific Notes](#os-specific-notes)
- [Wire Protocol Reference](#wire-protocol-reference)

## Glossary

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

## Setup Checklist

1. **Install the Arduino IDE** (2.x).
2. **Add the RP2040 board package:**
   - Arduino IDE → Preferences → "Additional Board Manager URLs" → add the `arduino-pico` URL.
   - Boards Manager → install "Raspberry Pi Pico/RP2040."
   - Select **"Waveshare RP2040-Zero"** as the board when flashing.
3. **Install the NeoPixel library** — Tools → Manage Libraries → search "Adafruit NeoPixel" → Install.
4. **Wire the PCBA** (full walkthrough in [Wiring the LED Strip](#wiring-the-led-strip)):
   - PCBA `G` → board `GND`
   - PCBA `V` → board `5V`/`VBUS` (not `3V3`)
   - PCBA `S` → one GPIO pin (firmware default: `GPIO1`)
5. **Flash and verify:**
   - Flash the sketch, open the Serial Monitor.
   - Pixel 1 alone should light dim white on boot.
   - Send `G`, `Y`, `R` — each should light only its own 3-pixel section (2-4 / 5-7 / 8-10), not the whole strip.

## Pixel Layout

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

## Soldering the Pins

The Waveshare RP2040-Zero ships bare — the edge holes are **castellated pads** (plated half-holes), not header pins. Nothing plugs into a breadboard until something is soldered into them.

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
     ( o )  <- solder joint
```

Solder at least **5V**, **GND**, and one **GPIO** pin (firmware default: `GPIO1`). Read the label printed on your board next to each pad — don't guess positions from a diagram.

| Method | Trade-off |
| --- | --- |
| Solder a male header strip (recommended) | Board plugs into a breadboard like any other module — reusable |
| Solder wires directly into the pads | No header stock needed, but hard-wires the board to those specific wires |

**Caution:** let each joint cool a few seconds before touching it, and solder 5V and GND on separate pins — never bridge two adjacent pads with one solder blob.

The fabricated PCB has the RP2040-Zero soldered directly onto it — this section covers the breadboard/prototype stage only.

## Wiring the LED Strip

```txt
 [RP2040-Zero]                    [LED Strip PCBA, 3-pin connector]
   GND o---------------------------o G  (ground)
   5V  o---------------------------o V  (power — NOT 3V3, see below)
   GP1 o---------------------------o S  (signal/data)

   USB-C port -----> cable -----> your computer
```

3 wires total on the breadboard version. Optional resistor/capacitor: see [`BOM.md`](BOM.md) items #8–9.

1. Seat the MCU on a breadboard, if you have one.
2. Connect `G` (ground) first.
3. Connect `V` to `5V`/`VBUS`, not `3V3` — 10 addressable LEDs draw more current than `3V3` is meant to supply. See the Power section in [`../firmware/README.md`](../firmware/README.md).
4. Connect `S` to a free GPIO pin, matching `kDataPin` in `andon_light_firmware.ino` (or edit the sketch to match your wiring).
5. Plug in USB-C last, once all 3 wires are connected — powering a half-wired setup risks a short.

## Pitfalls to Avoid

| Pitfall | What to know |
| --- | --- |
| `V` wired to `3V3` instead of `5V` | The most common wiring mistake — 10 addressable LEDs need the extra current headroom. |
| Flicker or wrong colors on power-up | Usually a data-line signal integrity issue (3.3V logic driving a 5V-rated strip), not a firmware bug. See the level-shifter fallback in [`../firmware/README.md`](../firmware/README.md). |
| Wrong connector pinout | Read the PCBA's silkscreen labels directly — don't assume pin order from this doc or a photo. |
| Charge-only USB-C cable | Board won't enumerate as a serial port. Try a different cable first. |
| Skipping the Serial Monitor check | It isolates firmware bugs from host-CLI bugs before you add the Python CLI on top. |
| Hooks not resetting the watchdog | Claude Code hooks fire only at discrete moments, not continuously — a long thinking-only stretch with no tool calls can leave the watchdog unfed. `PreToolUse` resets it on every tool call. |

Heartbeat/watchdog isn't optional polish — it's what makes this device trustworthy to walk away from.

## OS-Specific Notes

| OS | CDC driver behavior |
| --- | --- |
| Windows | Enumerates as a COM port with no extra driver install. |
| Linux | Enumerates as `/dev/ttyACM0`; your user needs `dialout` group membership — see [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md). |

## Wire Protocol Reference

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
