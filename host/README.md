# Host CLI: andon-light

Python driver for the Agent Andon Light. Talks to the firmware ([`../device/firmware/`](../device/firmware/)) over USB CDC serial via a simple text wire protocol.

## Layout

```txt
host/
├── pyproject.toml
├── andon_light/
│   ├── cli.py               # argparse entry point, `andon-light` command
│   ├── device_discovery.py  # finds the board by USB vendor ID
│   ├── serial_link.py       # opens/writes the serial connection, retry-on-busy
│   ├── hooks_install.py     # `andon-light install-hooks` merge/confirm logic
│   └── data/
│       ├── settings.snippet.json   # bundled copy for installed/frozen builds (Claude Code)
│       └── codex.hooks.json        # bundled copy for installed/frozen builds (Codex CLI)
└── tests/
    ├── test_cli.py
    └── test_hooks_install.py
```

## Install (development)

For actually using the CLI (Claude Code hooks, manual `andon-light` calls), install the published package instead — see [`../packaging/linux/README.md`](../packaging/linux/README.md) (Linux) or [`../packaging/windows/README.md`](../packaging/windows/README.md) (Windows). macOS isn't tested or supported yet.

To develop this repo, install in editable mode — symlinks back to source, so edits show up immediately without reinstalling:

```txt
cd host
pipx install --editable .
```

For an isolated venv, not on `PATH` outside it:

```txt
cd host
python3 -m venv .venv
.venv/bin/pip install -e .
```

## Usage

```txt
andon-light doctor                              # detect the device
andon-light set working                         # solid green
andon-light set waiting                         # solid yellow
andon-light set idle                             # solid red
andon-light set compacting                       # flashing green
andon-light heartbeat                            # keepalive, no color change
andon-light brightness 30                        # LED brightness, 5-100% of max, saved on the device
andon-light --port /dev/ttyACM0 set working      # override auto-detection
andon-light install-hooks                        # merge Claude Code hooks into settings.json (default agent)
andon-light install-hooks --agent codex          # merge Codex CLI hooks into hooks.json instead
andon-light install-hooks --yes --scope global   # same, non-interactive (used by the Windows installer)
```

`install-hooks` prints the exact `hooks` block before touching anything, asks for confirmation, lets you pick global vs. project scope, and warns before overwriting any hook event you've already customized. It never edits silently. `--agent` selects which agent's hooks and config file to target:

| `--agent` | Global scope | Project scope | Rationale |
| --- | --- | --- | --- |
| `claude` (default) | `~/.claude/settings.json` | `./.claude/settings.json` | See [`../hooks/claude/README.md`](../hooks/claude/README.md) |
| `codex` | `~/.codex/hooks.json` | `./.codex/hooks.json` | See [`../hooks/codex/README.md`](../hooks/codex/README.md) |

Both agents drive the same firmware over the same wire protocol — this is a host-only integration, no firmware update needed either way.

## Notes

- Auto-detection (`device_discovery.py`) filters by USB vendor ID `0x2E8A` (Raspberry Pi Foundation, used by arduino-pico's default TinyUSB descriptor) — matches the Waveshare RP2040-Zero.
- `brightness` needs firmware with the `B<n>` command ([`../device/firmware/README.md`](../device/firmware/README.md) Wire Protocol Reference). Older firmware silently ignores it — the firmware never replies, so the CLI can't detect this; if nothing changes, reflash.
- Override with `--port` or the `ANDON_LIGHT_PORT` env var if auto-detection picks the wrong port or finds nothing.
- "Device or resource busy" means another process (e.g. Arduino IDE's Serial Monitor) has the port open — only one process can hold it at a time. `andon-light` retries automatically for ~450ms before giving up; a serial failure then prints a one-line message with exit code 1 instead of a raw Python traceback.
