# Host CLI — andon-light

Python driver for the Agent Andon Light. Talks to the firmware in `../firmware/` over USB CDC serial.

## Install

```
cd host
pip install -e .
```

## Usage

```
andon-light doctor                             # detect the device
andon-light set working                        # green
andon-light set waiting                        # yellow
andon-light set idle                           # red
andon-light heartbeat                           # keepalive, no color change
andon-light --port /dev/ttyACM0 set working     # override auto-detection
```

## Notes

- Auto-detection (`device_discovery.py`) currently filters by USB vendor ID `0x2E8A` (Raspberry Pi Foundation, used by arduino-pico's default TinyUSB descriptor). This is unverified against real hardware — check with `andon-light doctor` once the board is flashed and plugged in, and adjust `DEFAULT_VID` if it's wrong.
- Override with `--port` or the `ANDON_LIGHT_PORT` env var if auto-detection picks the wrong port or finds nothing.
