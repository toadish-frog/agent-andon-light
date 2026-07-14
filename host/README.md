# Host CLI — andon-light

Python driver for the Agent Andon Light. Talks to the firmware (`../led-strip/firmware/`) over USB CDC serial via a simple text wire protocol.

## Install

For local development/testing (isolated venv, not on `PATH` outside it):

```txt
cd host
python3 -m venv .venv
.venv/bin/pip install -e .
```

For real use — e.g. so Claude Code hooks can call `andon-light` — install it globally on `PATH` via `pipx` (`sudo apt install -y pipx` if you don't have it):

``` txt
cd host
pipx install --editable .
```

`--editable` is right if you're actively developing this repo (symlinks back to the source, so edits show up immediately without reinstalling). If you're setting this up for someone else who just wants a working device — not editing the code — drop `--editable`:

``` txt
cd host
pipx install .
```

A plain install copies the package into pipx's own store, so it keeps working even if the source folder is later moved or deleted — `--editable` would silently break in that case, since it only points back at the original path.

## Usage

``` txt
andon-light doctor                             # detect the device
andon-light set working                        # solid green
andon-light set waiting                        # solid yellow
andon-light set idle                           # solid red
andon-light set compacting                      # flashing green
andon-light heartbeat                           # keepalive, no color change
andon-light --port /dev/ttyACM0 set working     # override auto-detection
```

## Notes

- Auto-detection (`device_discovery.py`) filters by USB vendor ID `0x2E8A` (Raspberry Pi Foundation, used by arduino-pico's default TinyUSB descriptor) — **confirmed correct** (2026-07-07) against the real Waveshare RP2040-Zero via `udevadm info`, and `andon-light doctor` finds it on the first try.
- Override with `--port` or the `ANDON_LIGHT_PORT` env var if auto-detection picks the wrong port or finds nothing.
- If you see "Device or resource busy," something else (e.g. Arduino IDE's Serial Monitor) still has the port open — only one process can hold it at a time. As of 2026-07-07, `andon-light` retries automatically for ~450ms before giving up, and any serial failure now prints a clean one-line message with exit code 1 instead of a raw Python traceback.
