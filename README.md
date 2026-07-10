# Agent Andon Light

A physical desktop status light for Claude Code / CLI coding agents — so you can walk away while an agent works and still know its state at a glance, instead of staring at a terminal.

```txt
green            → agent working
yellow           → waiting on you (permission or input)
red              → idle / stopped / session ended
flashing green   → compacting (internal maintenance, still alive)
slow pulsing red → stale / disconnected (device hasn't heard from the host in 30 min)
```

This doc is the "I already have the hardware, how do I get it running" guide. If you're building the hardware from scratch, start with the USER-GUIDE for your variant below (soldering, wiring, glossary). If you want the why behind the design, see the Implementation-Summary for your variant.

## Which hardware variant do you have?

Two independent, fully-separated firmware/docs tracks live side by side — same wire protocol, same host CLI, same Claude Code hooks either way. Pick the one matching your physical LED board:

| Variant | LED board | Directory |
| --- | --- | --- |
| **led-bulb** | Custom PCBA, 3 discrete bulbs (Red/Yellow/Green), 4-pin connector (`GND`+3 signal) | [`led-bulb/`](led-bulb/) |
| **led-strip** | Custom PCBA, addressable WS2812-style strip (10 LEDs), 3-pin connector (`S`/`V`/`G`) | [`led-strip/`](led-strip/) |

Each variant directory has its own `firmware/` (Arduino sketch) and `docs/` (BOM, Implementation-Summary, USER-GUIDE). `host/` and `hooks/` below are shared — they don't change based on which variant you have.

## What you need

- A Waveshare RP2040-Zero, header pins soldered on.
- The LED PCBA for your variant (see table above) wired to the RP2040-Zero.
- A data-capable USB-C cable.
- Arduino IDE (one-time, to flash the firmware).
- Python 3 + `pipx` (one-time, to install the host CLI).

## Quick start

**1. Flash the firmware.** Open your variant's sketch in Arduino IDE (`led-bulb/firmware/andon_light_firmware/andon_light_firmware.ino` or `led-strip/firmware/andon_light_firmware_strip/andon_light_firmware_strip.ino`), select board "Waveshare RP2040-Zero," and upload. Full steps (including the board-package setup and first-flash BOOTSEL quirk) are in that variant's `firmware/README.md`.

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
andon-light set compacting    # flashing green
andon-light heartbeat         # keepalive, no color change
andon-light doctor            # detect the device and report its port
```

## Troubleshooting

For a full step-by-step diagnostic playbook (exact terminal commands, in order), see [`led-bulb/docs/TROUBLESHOOTING.md`](led-bulb/docs/TROUBLESHOOTING.md) or [`led-strip/docs/TROUBLESHOOTING.md`](led-strip/docs/TROUBLESHOOTING.md) for your variant — the CLI/hooks/permission steps are identical in both (see the strip doc's "Why `host/` is unaffected by which variant you have"), the strip one just adds an extra step for addressable-strip-only symptoms (flicker, partial lighting, power). Quick version:

- **"No Andon Light device found"** — check the USB cable is data-capable (not charge-only), and run `andon-light doctor`. Override with `--port /dev/ttyACM0` or the `ANDON_LIGHT_PORT` env var if auto-detection finds the wrong thing.
- **"Device or resource busy"** — something else has the serial port open (commonly Arduino IDE's Serial Monitor). Close it — only one process can hold the port at a time. `andon-light` retries briefly on its own before giving up.
- **Permission denied opening the port** — your user needs to be in the `dialout` group. Check with `id` (not `groups $USER` — they can disagree; see `led-bulb/docs/TROUBLESHOOTING.md` Step 2 for why). If `dialout` is missing from `id`, run `newgrp dialout` to unblock the current shell immediately, then **reboot** for a permanent fix — a desktop "log out" is not reliably enough to rebuild every process's group credentials in every environment (confirmed 2026-07-08). One-off alternative: `sudo chmod 666 /dev/ttyACM0` (resets on replug).
- **Light stuck on the wrong color** — confirm your `~/.claude/settings.json` hooks don't have `"async": true` on them (that reintroduces an ordering race — see `hooks/README.md` "Why not async"), and restart Claude Code to be sure the current config is actually loaded. Also check for the permission issue above — hook commands end in `|| true`, so a permission failure silently "succeeds" in Claude Code's hook log while the light never actually changes; if `id` is missing `dialout`, that alone can look exactly like a stuck light. If the light stays on green after killing a session with Ctrl+C, make sure `SessionEnd` is present in your hook config (added 2026-07-08 — `Stop` alone doesn't fire on interrupts).
- **Light drops to slow pulsing red mid-session** — the watchdog hasn't heard anything in 30 minutes. If this happens sooner than that, something's wrong with the hook config (check `PreToolUse` is present and firing).
- **Nothing lights up at all** — flash didn't take, or the wrong pins. Check your variant's `firmware/README.md` for pin assignments against your actual wiring.
- **Light is off after a replug/power-cycle** — expected on firmware from before 2026-07-08 (it booted to "off" until the first hook fired); fixed by having it boot straight to idle/red instead — reflash if you're still on older firmware. Either way, you never need to reflash just for a replug — firmware is stored permanently in flash memory and survives power cycles; reflashing is only needed when the source code itself changes.

## Project layout

```txt
led-bulb/    3-discrete-bulb variant — firmware/ (Arduino sketch) + docs/ (BOM, Implementation-Summary, USER-GUIDE, TROUBLESHOOTING)
led-strip/   addressable LED strip variant — same firmware/ + docs/ shape (BOM, Implementation-Summary, USER-GUIDE, TROUBLESHOOTING)
host/        Python CLI (`andon-light`) — talks to either variant's firmware over USB serial, unmodified
hooks/       Claude Code hook config that drives the CLI automatically, unmodified regardless of variant
docs/        Cross-variant docs — how to swap which firmware is flashed on the one physical board you have
```

Only one firmware variant can be flashed to the board at a time — see [`docs/FLASHING-GUIDE.md`](docs/FLASHING-GUIDE.md) if you want to switch between the bulb and strip firmware (e.g. to test one while normally running the other).

## Status

Breadboard MVP is fully working end-to-end on real hardware for the **led-bulb** variant: firmware, host CLI, and Claude Code hooks all validated. See `led-bulb/docs/Implementation-Summary.md` §4.1 for the up-to-date phase-by-phase status. The **led-strip** variant is new firmware written against the same protocol but not yet flashed/tested on physical hardware — see `led-strip/docs/Implementation-Summary.md` for its status.
