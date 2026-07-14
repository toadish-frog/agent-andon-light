# Agent Andon Light

A physical desktop status light for Claude Code / CLI coding agents — so you can walk away while an agent works and still know its state at a glance, instead of staring at a terminal.

```txt
green            → agent working
yellow           → waiting on you (permission or input)
red              → idle / stopped / session ended
flashing green   → compacting (internal maintenance, still alive)
slow pulsing red → stale / disconnected (device hasn't heard from the host in 30 min)
```

This doc is the "I already have the hardware, how do I get it running" guide. If you're building the hardware from scratch, start with [`led-strip/docs/USER-GUIDE.md`](led-strip/docs/USER-GUIDE.md) (soldering, wiring, glossary). If you want the why behind the design, see [`led-strip/docs/Implementation-Summary.md`](led-strip/docs/Implementation-Summary.md).

## What you need

- A Waveshare RP2040-Zero, hand-soldered directly onto the custom PCB (`led-strip/hardware/`).
- A data-capable USB-C cable.
- Arduino IDE (one-time, to flash the firmware).
- Python 3 + `pipx` (one-time, to install the host CLI).

## Quick start

**1. Flash the firmware.** Open `led-strip/firmware/andon_light_firmware_strip/andon_light_firmware_strip.ino` in Arduino IDE, select board "Waveshare RP2040-Zero," and upload. Full steps (including the board-package setup and first-flash BOOTSEL quirk) are in [`led-strip/firmware/README.md`](led-strip/firmware/README.md).

**2. Install the host CLI.**

```txt
cd host
pipx install --editable .
```

Confirm it can see the board:

```txt
andon-light doctor
```

Full details in [`host/README.md`](host/README.md).

**3. Wire up the Claude Code hooks.** Merge the `hooks` object from [`hooks/settings.snippet.json`](hooks/settings.snippet.json) into `~/.claude/settings.json` (applies to every Claude Code session on this machine) or a project's `.claude/settings.json` (that project only). Reasoning behind each hook mapping is in [`hooks/README.md`](hooks/README.md).

**4. Restart Claude Code** (or start a new session) — hook config changes don't apply retroactively to an already-running session.

That's it. From here the light tracks your session automatically — no manual commands needed day to day.

## Manual control

Useful for testing, or if you just want to set the light by hand:

```txt
andon-light set working       # solid green
andon-light set waiting       # solid yellow
andon-light set idle          # solid red
andon-light set compacting    # chase-fill (compacting)
andon-light heartbeat         # keepalive, no color change
andon-light doctor            # detect the device and report its port
```

## Troubleshooting

For a full step-by-step diagnostic playbook (exact terminal commands, in order), see [`led-strip/docs/TROUBLESHOOTING.md`](led-strip/docs/TROUBLESHOOTING.md). Quick version:

- **"No Andon Light device found"** — check the USB cable is data-capable (not charge-only), and run `andon-light doctor`. Override with `--port /dev/ttyACM0` or the `ANDON_LIGHT_PORT` env var if auto-detection finds the wrong thing.
- **"Device or resource busy"** — something else has the serial port open (commonly Arduino IDE's Serial Monitor). Close it — only one process can hold the port at a time. `andon-light` retries briefly on its own before giving up.
- **Permission denied opening the port** — your user needs to be in the `dialout` group. Check with `id` (not `groups $USER` — they can disagree; see `led-strip/docs/TROUBLESHOOTING.md` Step 2 for why). If `dialout` is missing from `id`, run `newgrp dialout` to unblock the current shell immediately, then **reboot** for a permanent fix — a desktop "log out" is not reliably enough to rebuild every process's group credentials in every environment (confirmed 2026-07-08). One-off alternative: `sudo chmod 666 /dev/ttyACM0` (resets on replug).
- **Light stuck on the wrong color** — confirm your `~/.claude/settings.json` hooks don't have `"async": true` on them (that reintroduces an ordering race — see `hooks/README.md` "Why not async"), and restart Claude Code to be sure the current config is actually loaded. Also check for the permission issue above — hook commands end in `|| true`, so a permission failure silently "succeeds" in Claude Code's hook log while the light never actually changes; if `id` is missing `dialout`, that alone can look exactly like a stuck light. If the light stays on green after killing a session with Ctrl+C, make sure `SessionEnd` is present in your hook config (added 2026-07-08 — `Stop` alone doesn't fire on interrupts).
- **Light drops to slow pulsing red mid-session** — the watchdog hasn't heard anything in 30 minutes. If this happens sooner than that, something's wrong with the hook config (check `PreToolUse` is present and firing).
- **Nothing lights up at all** — flash didn't take, or the wrong pins. Check `led-strip/firmware/README.md` for pin assignments against your actual wiring.
- **Light is off after a replug/power-cycle** — expected pre-boot-to-idle firmware; the current firmware boots straight to idle instead. You never need to reflash just for a replug — firmware is stored permanently in flash memory and survives power cycles; reflashing is only needed when the source code itself changes.

## Project layout

```txt
led-strip/   the only hardware line — firmware/ (Arduino sketch), hardware/ (KiCad + manufacturing files, PCB in fab), docs/ (BOM, Implementation-Summary, USER-GUIDE, TROUBLESHOOTING), archive/ (retired Phase 1 MVP hardware — see below)
host/        Python CLI (`andon-light`) — talks to the firmware over USB serial
hooks/       Claude Code hook config that drives the CLI automatically
```

**Note (2026-07-14):** this project used to carry two parallel hardware tracks side by side (`led-bulb/` and `led-strip/`, each with its own firmware/docs). That's retired — `led-strip` is the only ongoing hardware line. The original 3-discrete-bulb breadboard MVP (used to validate firmware/host/hooks before the strip's custom PCB existed) is preserved as history at [`led-strip/archive/led-bulb-mvp/`](led-strip/archive/led-bulb-mvp/), not maintained as a second deliverable. See [`led-strip/docs/Implementation-Summary.md`](led-strip/docs/Implementation-Summary.md) §5 "Phase 1" for the full story.

## Status

Firmware, host CLI, and Claude Code hooks are all validated end-to-end on real hardware (breadboard-wired strip PCBA) — `G`/`Y`/`R`/`C` and the sectioned pixel layout all confirmed working; the watchdog `StalePulse` animation is written but not yet observed on physical hardware. The custom PCB (Rev A) has been designed, DRC/ERC-clean, and sent to JLC for fabrication — boards are in manufacturing, not yet in hand. See [`led-strip/docs/Implementation-Summary.md`](led-strip/docs/Implementation-Summary.md) for the up-to-date phase-by-phase status.
