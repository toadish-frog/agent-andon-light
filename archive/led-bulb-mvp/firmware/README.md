# Firmware: Agent Andon Light (3-Bulb MVP)

Arduino sketch for the Waveshare RP2040-Zero, implementing the wire protocol below (`G`/`Y`/`R`/`C`/`H`).

This is the **3-discrete-bulb variant** (Red/Yellow/Green LEDs on a 4-pin connector). For the addressable LED strip variant, see [`../../../device/firmware/`](../../../device/firmware/).

## Setup

See [`../docs/USER-GUIDE.md`](../docs/USER-GUIDE.md) Setup Checklist.

1. Arduino IDE 2.x, with the `arduino-pico` board package installed. No LED library needed — the 3 status bulbs are plain `digitalWrite`/`analogWrite` GPIO, not an addressable protocol.
2. Open `andon_light_firmware/andon_light_firmware.ino` — Arduino IDE loads `led_controller.h/.cpp` and `watchdog.h` alongside it as tabs.

## Wiring

The status light is a custom PCBA with 3 discrete LED bulbs (Red/Yellow/Green) and a 4-pin connector.

| PCBA pin | Connects to |
| --- | --- |
| `GND` | Board `GND` |
| `Green` | `GPIO1` |
| `Yellow` | `GPIO2` |
| `Red` | `GPIO3` |

Change the pins in `andon_light_firmware.ino` by editing `kGreenPin`/`kYellowPin`/`kRedPin` if wired differently. The RP2040-Zero uses plain GPIO numbers (`GPIO0`, `GPIO1`, ...), not the `D0`-style aliases Seeed's boards use — don't copy pin names from XIAO tutorials verbatim.

## Flash & Test

1. Select "Waveshare RP2040-Zero" as the board, then flash.
2. Open the Serial Monitor at 115200 baud, line ending "Newline".
3. Type `G`, `Y`, `R` and press enter — confirm the LEDs respond. To test the stale-pulse fallback without waiting 30 minutes, temporarily lower `kWatchdogTimeoutMs` (e.g. to `15000`), flash, confirm the slow red pulse kicks in after that shorter wait, then change it back to `1800000` and reflash.

## Design Notes

- **`C` (flashing green)** signals "still working, just doing internal context compaction" — visually distinct from solid green (`G`, ordinary working) via a sharp on/off blink (`kFlashPeriodMs = 500` in `led_controller.cpp`), as opposed to `StalePulse`'s slow smooth breathing fade.
- **Power-on default is idle (red), not off.** `LedController::begin()` boots straight to `LightColor::Red` instead of `Off` — a bare USB replug/power-cycle is a hardware event Claude Code never sees, so booting to `Off` would leave the light dark indefinitely until some other hook happened to fire. Replugging the USB cable does not erase or require re-flashing the firmware (it's stored permanently in flash) — this only concerns what color it boots into.
- **Watchdog timeout is 30 minutes, not 15 seconds.** Claude Code hooks only fire at a few discrete moments (prompt submitted, tool used, waiting, stopped), so a 15s timeout produced false stale-pulse trips during any gap longer than that between hook events — e.g. a long stretch of the model just thinking with no tool calls. 30 minutes comfortably covers that while still eventually recovering if a session is genuinely abandoned mid-turn. See [`../../../hooks/README.md`](../../../hooks/README.md) for the corresponding `PreToolUse` hook addition that keeps the watchdog kicked during tool-heavy stretches.

## Wire Protocol Reference

| Command | Effect | Meaning |
| --- | --- | --- |
| `G\n` | Solid green | Agent working |
| `Y\n` | Solid yellow | Waiting for human input / permission |
| `R\n` | Solid red | Idle / stopped / quota reached |
| `C\n` | Flashing green | Compacting — internal maintenance, still alive |
| `H\n` | No color change | Heartbeat, resets the watchdog |
