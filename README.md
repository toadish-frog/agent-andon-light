# Agent Andon Light

A physical desktop status light for Claude Code / CLI coding agents — so you can walk away while an agent works and still know its state at a glance, instead of staring at a terminal.

```
green            → agent working
yellow           → waiting on you (permission or input)
red              → idle / stopped / session ended
flashing green   → compacting (internal maintenance, still alive)
slow pulsing red → stale / disconnected (device hasn't heard from the host in 30 min)
```

This doc is the "I already have the hardware, how do I get it running" guide. If you're building the hardware from scratch, start with [`.prompt/docs/USER-GUIDE.md`](.prompt/docs/USER-GUIDE.md) instead (soldering, wiring, glossary). If you want the why behind the design, see [`.prompt/docs/Implementation-Summary.md`](.prompt/docs/Implementation-Summary.md).

## What you need

- A Waveshare RP2040-Zero, header pins soldered on.
- A custom LED PCBA (3 bulbs: Red/Yellow/Green) wired to the RP2040-Zero via a 4-pin connector (`GND`, `Red`, `Yellow`, `Green`).
- A data-capable USB-C cable.
- Arduino IDE (one-time, to flash the firmware).
- Python 3 + `pipx` (one-time, to install the host CLI).

## Quick start

**1. Flash the firmware.** Open `firmware/andon_light_firmware/andon_light_firmware.ino` in Arduino IDE, select board "Waveshare RP2040-Zero," and upload. Full steps (including the board-package setup and first-flash BOOTSEL quirk) are in [`firmware/README.md`](firmware/README.md).

**2. Install the host CLI.**

```
cd host
pipx install --editable .
```

Confirm it can see the board:

```
andon-light doctor
```

Full details in [`host/README.md`](host/README.md).

**3. Wire up the Claude Code hooks.** Merge the `hooks` object from [`hooks/settings.snippet.json`](hooks/settings.snippet.json) into `~/.claude/settings.json` (applies to every Claude Code session on this machine) or a project's `.claude/settings.json` (that project only). Reasoning behind each hook mapping is in [`hooks/README.md`](hooks/README.md).

**4. Restart Claude Code** (or start a new session) — hook config changes don't apply retroactively to an already-running session.

That's it. From here the light tracks your session automatically — no manual commands needed day to day.

## Manual control

Useful for testing, or if you just want to set the light by hand:

```
andon-light set working       # solid green
andon-light set waiting       # solid yellow
andon-light set idle          # solid red
andon-light set compacting    # flashing green
andon-light heartbeat         # keepalive, no color change
andon-light doctor            # detect the device and report its port
```

## Troubleshooting

- **"No Andon Light device found"** — check the USB cable is data-capable (not charge-only), and run `andon-light doctor`. Override with `--port /dev/ttyACM0` or the `ANDON_LIGHT_PORT` env var if auto-detection finds the wrong thing.
- **"Device or resource busy"** — something else has the serial port open (commonly Arduino IDE's Serial Monitor). Close it — only one process can hold the port at a time. `andon-light` retries briefly on its own before giving up.
- **Permission denied opening the port** — your user needs to be in the `dialout` group (`sudo usermod -aG dialout $USER`, then log out/in), or as a quick one-off: `sudo chmod 666 /dev/ttyACM0` (resets on replug).
- **Light stuck on the wrong color** — shouldn't happen; if it does, confirm your `~/.claude/settings.json` hooks don't have `"async": true` on them (that reintroduces an ordering race — see `hooks/README.md` "Why not async"), and restart Claude Code to be sure the current config is actually loaded.
- **Light drops to slow pulsing red mid-session** — the watchdog hasn't heard anything in 30 minutes. If this happens sooner than that, something's wrong with the hook config (check `PreToolUse` is present and firing).
- **Nothing lights up at all** — flash didn't take, or the wrong pins. Check `firmware/README.md`'s pin assignments against your actual wiring.

## Project layout

```
firmware/    Arduino sketch — reads serial commands, drives the 3 LEDs, runs the watchdog
host/        Python CLI (`andon-light`) — talks to the firmware over USB serial
hooks/       Claude Code hook config that drives the CLI automatically
.prompt/docs/  Deeper docs: BOM/sourcing, architecture, full build guide
```

## Status

Breadboard MVP is fully working end-to-end on real hardware: firmware, host CLI, and Claude Code hooks all validated. See `.prompt/docs/Implementation-Summary.md` §4.1 for the up-to-date phase-by-phase status.
