# Host CLI — andon-light

Python driver for the Agent Andon Light. Talks to the firmware (`../device/firmware/`) over USB CDC serial via a simple text wire protocol.

## Install

Published on PyPI — for real use (e.g. so Claude Code hooks can call `andon-light`), install it globally on `PATH` via `pipx` (`sudo apt install -y pipx` if you don't have it):

```txt
pipx install andon-light
```

No repo clone needed for this path.

If you're actively developing this repo instead, install from source in editable mode — it symlinks back to the source, so edits show up immediately without reinstalling:

```txt
cd host
pipx install --editable .
```

For local development/testing in an isolated venv (not on `PATH` outside it):

```txt
cd host
python3 -m venv .venv
.venv/bin/pip install -e .
```

## Usage

```txt
andon-light doctor                             # detect the device
andon-light set working                        # solid green
andon-light set waiting                        # solid yellow
andon-light set idle                           # solid red
andon-light set compacting                      # flashing green
andon-light heartbeat                           # keepalive, no color change
andon-light --port /dev/ttyACM0 set working     # override auto-detection
andon-light install-hooks                       # merge Claude Code hooks into settings.json
andon-light install-hooks --yes --scope global  # same, non-interactive (used by the Windows installer)
```

`install-hooks` prints the exact `hooks` block before touching anything, asks for confirmation, lets you pick global (`~/.claude/settings.json`) vs project (`./.claude/settings.json`) scope, and warns before overwriting any hook event you've already customized. It never edits silently — see `../hooks/README.md`.

## Notes

- Auto-detection (`device_discovery.py`) filters by USB vendor ID `0x2E8A` (Raspberry Pi Foundation, used by arduino-pico's default TinyUSB descriptor) — confirmed correct (2026-07-07) against the real Waveshare RP2040-Zero via `udevadm info`; `andon-light doctor` finds it on the first try.
- Override with `--port` or the `ANDON_LIGHT_PORT` env var if auto-detection picks the wrong port or finds nothing.
- "Device or resource busy" means another process (e.g. Arduino IDE's Serial Monitor) still has the port open — only one process can hold it at a time. As of 2026-07-07, `andon-light` retries automatically for ~450ms before giving up, and any serial failure prints a clean one-line message with exit code 1 instead of a raw Python traceback.
