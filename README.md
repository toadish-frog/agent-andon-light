# Agent Andon Light

A physical desktop status light for Claude Code / CLI coding agents — so you can walk away while an agent works and still know its state at a glance, instead of staring at a terminal.

```txt
green            → agent working
yellow           → waiting on you (permission or input)
red              → idle / stopped / session ended
flashing green   → compacting (internal maintenance, still alive)
slow pulsing red → stale / disconnected (device hasn't heard from the host in 30 min)
```

This doc covers "I already have the hardware, how do I get it running." Building the hardware from scratch starts at [`device/docs/USER-GUIDE.md`](device/docs/USER-GUIDE.md) (soldering, wiring, glossary). For the design rationale, see [`device/docs/Implementation-Summary.md`](device/docs/Implementation-Summary.md).

## What you need

- A Waveshare RP2040-Zero, hand-soldered directly onto the custom PCB (`device/hardware/`).
- A data-capable USB-C cable.
- Arduino IDE (one-time, to flash the firmware).
- Python 3 + `pipx` (one-time, to install the host CLI).

## Quick start

**1. Flash the firmware.** Open `device/firmware/andon_light_firmware_strip/andon_light_firmware_strip.ino` in Arduino IDE, select board "Waveshare RP2040-Zero," and upload. Full steps (board-package setup, first-flash BOOTSEL quirk) are in [`device/firmware/README.md`](device/firmware/README.md).

**2. Install the host CLI.** Published on PyPI — no repo clone needed for this step:

```txt
pipx install andon-light
```

Confirm it can see the board:

```txt
andon-light doctor
```

Developing this repo instead? Install from source in editable mode — full details in [`host/README.md`](host/README.md).

**3. Wire up the Claude Code hooks.** Merge the `hooks` object from [`hooks/settings.snippet.json`](hooks/settings.snippet.json) into `~/.claude/settings.json` (every session on this machine) or a project's `.claude/settings.json` (that project only). Rationale for each hook mapping is in [`hooks/README.md`](hooks/README.md).

**4. Restart Claude Code** (or start a new session) — hook config changes don't apply to a session already running.

From here the light tracks your session automatically — no manual commands needed day to day.

## Manual control

Useful for testing, or to set the light by hand:

```txt
andon-light set working       # solid green
andon-light set waiting       # solid yellow
andon-light set idle          # solid red
andon-light set compacting    # chase-fill (compacting)
andon-light heartbeat         # keepalive, no color change
andon-light doctor            # detect the device and report its port
```

## Troubleshooting

For the full diagnostic playbook, see [`device/docs/TROUBLESHOOTING.md`](device/docs/TROUBLESHOOTING.md). Quick version:

- **"No Andon Light device found"** — check the USB cable is data-capable (not charge-only), then run `andon-light doctor`. Override with `--port /dev/ttyACM0` or the `ANDON_LIGHT_PORT` env var if auto-detection finds the wrong thing.
- **"Device or resource busy"** — another process (commonly Arduino IDE's Serial Monitor) has the port open; only one process can hold it at a time. Close it — `andon-light` also retries briefly on its own before giving up.
- **Permission denied opening the port** — your user needs to be in the `dialout` group. Check with `id`, not `groups $USER` (they can disagree — see `device/docs/TROUBLESHOOTING.md` Step 2). If `dialout` is missing from `id`, run `newgrp dialout` to unblock the current shell immediately, then **reboot** for a permanent fix — a desktop log-out alone doesn't reliably rebuild every process's group credentials (confirmed 2026-07-08). One-off alternative: `sudo chmod 666 /dev/ttyACM0` (resets on replug).
- **Light stuck on the wrong color** — confirm your `~/.claude/settings.json` hooks don't have `"async": true` (reintroduces an ordering race — see `hooks/README.md` "Why not async"), and restart Claude Code so the current config is actually loaded. Also check the permission issue above: hook commands end in `|| true`, so a permission failure "succeeds" silently in Claude Code's hook log while the light never changes. If the light stays green after Ctrl+C, confirm `SessionEnd` is present in your hook config (added 2026-07-08 — `Stop` alone doesn't fire on interrupts).
- **Light drops to slow pulsing red mid-session** — the watchdog hasn't heard anything in 30 minutes. If this happens sooner, check that `PreToolUse` is present and firing in your hook config.
- **Nothing lights up at all** — flash didn't take, or the pin assignment is wrong. Check `device/firmware/README.md` for pin assignments against your actual wiring.
- **Light is off after a replug/power-cycle** — expected; current firmware boots straight to idle rather than off. Firmware is stored permanently in flash and survives power cycles, so a replug never needs a reflash — only a source change does.

## Project layout

```txt
device/      the only hardware line — firmware/ (Arduino sketch), hardware/ (KiCad + manufacturing files), docs/ (BOM, Implementation-Summary, USER-GUIDE, TROUBLESHOOTING)
archive/     retired Phase 1 MVP hardware — see below
host/        Python CLI (`andon-light`) — talks to the firmware over USB serial
hooks/       Claude Code hook config that drives the CLI automatically
```

**Note (2026-07-14):** this project used to carry two parallel hardware tracks (`led-bulb/` and `led-strip/`, each with its own firmware/docs). That's retired — the addressable LED strip is the only ongoing hardware line, now living at `device/` (renamed from `led-strip/` since "strip" stopped being a meaningful qualifier with nothing left to disambiguate from). The original 3-discrete-bulb breadboard MVP (used to validate firmware/host/hooks before the strip's custom PCB existed) is preserved as history at [`archive/led-bulb-mvp/`](archive/led-bulb-mvp/), not maintained as a second deliverable — see `device/docs/Implementation-Summary.md` §5 "Phase 1."

## Status

5 units fully assembled — custom PCB Rev A + 3D-printed enclosure, both back from JLC as of 2026-07-30 — individually flashed and tested. `G`/`Y`/`R`/`C`, the sectioned pixel layout, and the watchdog `StalePulse` fallback are all confirmed on the fabricated hardware; enclosure fit was correct first-try on every unit. Packaging & distribution (one-click installers) hasn't started. See [`device/docs/Implementation-Summary.md`](device/docs/Implementation-Summary.md) for the full phase-by-phase status.
