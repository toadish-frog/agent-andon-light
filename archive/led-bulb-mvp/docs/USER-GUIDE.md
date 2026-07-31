# User Guide: Agent Andon Light (3-Bulb MVP)

Companion doc for building the hardware — terminology, setup, wiring, pitfalls. Covers the **3-discrete-bulb variant**; for the addressable LED strip variant, see [`../../../device/docs/USER-GUIDE.md`](../../../device/docs/USER-GUIDE.md). Parts list: [`BOM.md`](BOM.md).

## Contents

- [Glossary](#glossary)
- [Setup Checklist](#setup-checklist)
- [Soldering the Pins](#soldering-the-pins)
- [Wiring the LED PCBA](#wiring-the-led-pcba)
- [Pitfalls to Avoid](#pitfalls-to-avoid)
- [Wire Protocol Reference](#wire-protocol-reference)

## Glossary

| Term | Meaning |
| --- | --- |
| MCU (microcontroller) | The chip on your dev board that runs the firmware. On the RP2040-Zero, that's the RP2040. |
| Firmware | The program running *on* the MCU, not on your laptop. Written in C++ (Arduino framework). |
| Dev board | A ready-made PCB with the MCU plus USB and power regulation already wired up. The RP2040-Zero is one. |
| Discrete LED | A plain single-color LED, on/off (or dimmed) via a normal GPIO pin — no special protocol or library. This project uses 3 (Red/Yellow/Green) on a custom PCBA. |
| Serial / USB CDC | The dev board shows up as a plain serial port over USB, so Python can read/write it directly, no custom driver on Linux/macOS. |
| Watchdog | A firmware safety timer that resets to a known-safe state if it hasn't heard from the host in too long. |
| KiCad | Free, open-source PCB design software. |
| PCBA | "PCB Assembly": a bare PCB with all components soldered on. |

## Setup Checklist

1. **Install the Arduino IDE** (2.x).
2. **Add the RP2040 board package:**
   - Arduino IDE → Preferences → "Additional Board Manager URLs" → add the `arduino-pico` URL.
   - Boards Manager → install "Raspberry Pi Pico/RP2040."
   - Select **"Waveshare RP2040-Zero"** as the board when flashing.
   - No LED library needed — the 3 bulbs are driven with plain `digitalWrite`/`analogWrite`.
3. **Wire the PCBA** (full walkthrough below):
   - PCBA `GND` → board `GND`
   - PCBA `Red`/`Yellow`/`Green` → 3 board GPIO pins of your choice (firmware default: `GPIO1`/`GPIO2`/`GPIO3`)
4. **Flash a test sketch** that cycles red → yellow → green every 2 seconds — confirms the hardware is good before anything else.
5. **Verify via Serial Monitor:** send `G`, `Y`, `R` as single characters, confirm each LED responds — this exercises the firmware's command parser before Python is involved.

## Soldering the Pins

The Waveshare RP2040-Zero ships bare — the edge holes are **castellated pads** (plated half-holes), not header pins.

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

Solder at least **5V**, **GND**, and one **GPIO** pin (firmware default: `GP0`). Read the label printed on your board next to each pad — don't guess positions from a diagram.

| Method | Trade-off |
| --- | --- |
| Solder a male header strip (recommended) | Board plugs into a breadboard like any other module — reusable |
| Solder wires directly into the pads | No header stock needed, but hard-wires the board to those specific wires |

**Caution:** let each joint cool a few seconds before touching it, and solder 5V and GND on separate pins — never bridge two adjacent pads with one solder blob.

## Wiring the LED PCBA

Simpler than an addressable strip — 4 wires total, no resistor or capacitor to add (already on the PCBA), no shared power rail beyond a common ground.

```txt
 [RP2040-Zero]                    [LED PCBA, 4-pin connector]
   GND o---------------------------o GND
   GP1 o---------------------------o Green
   GP2 o---------------------------o Yellow
   GP3 o---------------------------o Red

   USB-C port -----> cable -----> your computer
```

1. Seat the MCU on a breadboard, if you have one.
2. Connect `GND` first — every other wire's signal is measured relative to this.
3. Connect the 3 signal wires, one MCU GPIO each to `Red`/`Yellow`/`Green`. Any 3 free GPIO pins work — make sure they match `kGreenPin`/`kYellowPin`/`kRedPin` in `andon_light_firmware.ino` (or edit the sketch to match your wiring).
4. Plug in USB-C last, once all 4 wires are connected — powering a half-wired setup risks a short.

## Pitfalls to Avoid

| Pitfall | What to know |
| --- | --- |
| Wrong connector pinout | Read the PCBA's silkscreen labels directly — don't assume pin order from this doc or a photo. Double-check `GND` isn't landed on a signal pin. |
| Charge-only USB-C cable | Board won't enumerate as a serial port. Try a different cable first. |
| Skipping the Serial Monitor check | Isolates firmware bugs from host-CLI bugs — matters most the first time debugging both halves of a system you haven't built before. |
| Windows CDC driver not detected | If the board doesn't show up in Device Manager as a COM port, the `arduino-pico` package usually installs the right driver automatically; if not, search by exact board name + "Windows driver." |
| Hooks not resetting the watchdog | Claude Code hooks fire only at discrete moments, not continuously — a long thinking-only stretch with no tool calls can leave the watchdog unfed. `PreToolUse` resets it on every tool call — see [`../firmware/README.md`](../firmware/README.md) and [`../../../hooks/README.md`](../../../hooks/README.md). |

Heartbeat/watchdog isn't optional polish — it's what makes this device trustworthy to walk away from.

## Wire Protocol Reference

| Command | Effect | Meaning |
| --- | --- | --- |
| `G\n` | Solid green | Agent working |
| `Y\n` | Solid yellow | Waiting for human input / permission |
| `R\n` | Solid red | Idle / stopped / session start |
| `C\n` | Flashing green | Compacting (internal maintenance, still alive) |
| `H\n` | No color change | Heartbeat, resets the watchdog |

Watchdog timeout: **30 minutes**.

Hook mapping (rationale: [`../../../hooks/README.md`](../../../hooks/README.md)):

| Hook event | Color |
| --- | --- |
| `SessionStart` | idle |
| `UserPromptSubmit` / `PreToolUse` | working |
| `Notification` / `PermissionRequest` | waiting |
| `PreCompact` | compacting |
| `Stop` | idle |
