# Firmware — Agent Andon Light

Arduino sketch for the Waveshare RP2040-Zero, implementing the v2 wire protocol from `.prompt/docs/Implementation-Summary.md` (`G`/`Y`/`R`/`C`/`H`).

## Setup (once — see `.prompt/docs/USER-GUIDE.md` Phase 1 checklist)

1. Arduino IDE 2.x, with the `arduino-pico` board package installed. No LED library needed — the 3 status bulbs are plain `digitalWrite`/`analogWrite` GPIO, not an addressable protocol.
2. Open `andon_light_firmware/andon_light_firmware.ino` — Arduino IDE will load `led_controller.h/.cpp` and `watchdog.h` alongside it as tabs.

## Wiring

The status light is a custom PCBA with 3 discrete LED bulbs (Red/Yellow/Green) and a 4-pin connector: `GND`, `Red`, `Yellow`, `Green`.

- PCBA `GND` ← board `GND`
- PCBA `Green` ← `GPIO1`
- PCBA `Yellow` ← `GPIO2`
- PCBA `Red` ← `GPIO3`

Change the pins in `andon_light_firmware.ino` by editing `kGreenPin`/`kYellowPin`/`kRedPin` if you wire it differently. Note the RP2040-Zero uses plain GPIO numbers (`GPIO0`, `GPIO1`, ...), not the `D0`-style aliases Seeed's boards use — don't copy pin names from XIAO tutorials verbatim.

## Flash & test

1. Select "Waveshare RP2040-Zero" as the board, then flash.
2. Open the Serial Monitor at 115200 baud, line ending "Newline".
3. Type `G`, `Y`, `R` and press enter — confirm the LEDs respond. To test the stale-pulse fallback without waiting the full 30 minutes, temporarily lower `kWatchdogTimeoutMs` (e.g. to `15000`), flash, confirm the slow red pulse kicks in after that shorter wait, then change it back to `1800000` and reflash.

## Confirmed on real hardware (2026-07-07)

- `kGreenPin`/`kYellowPin`/`kRedPin` (`GPIO1`/`GPIO2`/`GPIO3`) — confirmed correct against the actual PCBA wiring via Serial Monitor testing.
- `StalePulse`'s `analogWrite` (PWM) breathing animation on the red pin — confirmed working on GPIO3.

## New in v2: flashing green (`C`)

Added 2026-07-07 alongside the `PostCompact` hook, for "still working, just doing internal context compaction" — visually distinct from solid green (`G`, ordinary working) via a sharp on/off blink (`kFlashPeriodMs = 500` in `led_controller.cpp`), as opposed to `StalePulse`'s slow smooth breathing fade. **Needs re-flashing** to take effect — this is source-level only until the sketch is re-uploaded.

## Power-on default: idle (red), not off

Added 2026-07-08 — the board's `setup()` used to leave all 3 bulbs off until the first serial command arrived. That's fine when Claude Code's `SessionStart` hook fires right after, but a bare USB replug/power-cycle is a hardware event Claude Code never sees, so the light would sit dark indefinitely until some other hook happened to fire. `LedController::begin()` now boots straight to `LightColor::Red` (idle) instead of `Off`, matching the same "not working yet" default reasoning as the `SessionStart` hook. **Needs re-flashing** to take effect. Note: replugging the USB cable does **not** erase or require re-flashing the firmware itself (it's stored permanently in flash memory) — this fix is only about what color it happens to boot into, not whether the program is still there.

## Watchdog timeout: 30 minutes, not 15 seconds

Originally 15s, raised to `kWatchdogTimeoutMs = 1800000` (30 min) after real-world testing with Claude Code hooks showed false stale-pulse trips: the hooks only fire at a few discrete moments (prompt submitted, tool used, waiting, stopped), so any gap longer than 15s between them — e.g. a long stretch of the model just thinking with no tool calls — incorrectly looked "disconnected." 30 minutes comfortably covers that while still eventually recovering if a session is genuinely abandoned mid-turn. See `../hooks/README.md` for the corresponding `PreToolUse` hook addition that keeps the watchdog kicked during tool-heavy stretches.
