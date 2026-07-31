# Troubleshooting: Agent Andon Light

Diagnostic playbook — work through these in order to narrow down where a problem actually is. Copy-paste each command into a terminal; read the table below it before running, so you know what to look for.

## Start Here

| Symptom | Go to |
| --- | --- |
| Light completely dark / unresponsive | [Step 1](#step-1-is-the-board-running-firmware) |
| Colors wrong/flickery, or the lit section itself looks broken | [Step 3.5](#step-35-flicker-wrong-colors-or-unexpected-partial-lighting) |
| Light on but wrong color, or stuck | [Step 4](#step-4-is-the-hook-config-correct) |
| `andon-light` command fails or errors | [Step 2](#step-2-is-the-device-reachable-by-the-host-cli) |
| Worked once, broke after unplug/replug | [Step 1](#step-1-is-the-board-running-firmware) |

## Step 1: Is the Board Running Firmware?

```txt
lsusb | grep -i "2e8a"
```

| Output | Meaning | Fix |
| --- | --- | --- |
| `2e8a:0003 Raspberry Pi RP2 Boot` | Board is in **bootloader mode**, not running firmware — no LEDs will respond, no serial port exists | Open Arduino IDE and click Upload — it detects this state and finishes the flash |
| Line with `Waveshare` or `RP2040 Zero` | Firmware **is** running normally | Move to Step 2 |
| Nothing | Board not connected, or cable isn't data-capable | Try a different USB-C cable, confirm it's fully seated |

You can also check for the bootloader's mass-storage drive directly:

```txt
find /media /run/media /mnt -maxdepth 3 -iname "*RPI*" 2>/dev/null
```

A printed path (e.g. `/run/media/sean/RPI-RP2`) confirms bootloader mode — same fix as above.

## Step 2: Is the Device Reachable by the Host CLI?

```txt
andon-light doctor
```

| Output | Meaning |
| --- | --- |
| `Found device on /dev/ttyACM0` (or similar) | CLI can see it, port permissions are fine — move to Step 3 |
| `No device found` | Board isn't running firmware — go back to Step 1 |
| `[Errno 13] Permission denied` | Port-permissions issue — see [Linux-Specific: Permission Denied](#permission-denied-opening-the-port) below |

## Step 3: Is Something Else Holding the Port Open?

```txt
andon-light set idle
```

| Output | Meaning |
| --- | --- |
| Succeeds silently, exit code 0 | CLI → firmware link works. LEDs didn't change? Go to Step 3.5, or reflash (Step 1). |
| `andon-light: serial error: ... Device or resource busy` | Another program has the port open — almost always Arduino IDE's Serial Monitor. Close it and retry. |

Check the exit code explicitly if the message scrolled past:

```txt
andon-light set idle; echo "exit code: $?"
```

## Step 3.5: Flicker, Wrong Colors, or Unexpected Partial Lighting

Addressable strips depend on precise data timing and adequate power, not just an on/off signal.

**Rule out the obvious non-bug first:** partial lighting is the design, not a fault. `G`/`Y`/`R` each light only their own 3-pixel section (2-4 / 5-7 / 8-10) plus the always-on status pixel (1) — see [`USER-GUIDE.md`](USER-GUIDE.md) Pixel Layout. Seeing 7 pixels dark while `G` is active is correct. The problems below look different: pixels *within* the active section are wrong, or the pattern doesn't match any valid section at all.

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Some pixels in the active section are garbled/dark, others correct | Data-line signal integrity — the RP2040 drives `S` at 3.3V logic; a marginal connection or long wire can lose sync partway down the chain | Shorten the `S` wire, check the connector crimp/solder joint, or add a 74HCT125 level shifter (see [`BOM.md`](BOM.md) item #7) |
| Dim colors, wrong hue, or the board browns-out/resets when the light comes on | `V` wired to `3V3` instead of the MCU's `5V`/`VBUS` pin | Rewire to `5V` — 10 addressable LEDs draw more current than `3V3` is meant to supply, see [`../firmware/README.md`](../firmware/README.md) Power note |
| Nothing lights at all — not even pixel 1 — but `andon-light set idle` returns exit code 0 | `kDataPin` in `andon_light_firmware.ino` doesn't match the GPIO wired to `S` | Check the pin, not the LEDs. (If pixel 1 lights but sections 2-10 stay dark regardless of command, that's Step 3, not this — the command may not be reaching the board at all.) |
| Lit pixels don't line up with the expected sections (e.g. `G` lights pixels 4-6 instead of 2-4) | `S` wired to the wrong end of the strip, or the PCBA numbers pixels in the opposite direction from the firmware's assumption | Check which end of the strip PCBA is silkscreened as the data input, confirm `S` is wired there |

Still stuck? Confirm the Adafruit_NeoPixel library is actually installed (Arduino IDE → Tools → Manage Libraries → search "Adafruit NeoPixel") — a missing library shows as a compile error, not a runtime symptom, but worth ruling out.

## Step 4: Is the Hook Config Correct?

```txt
cat ~/.claude/settings.json
```

- [ ] **Valid JSON?** Run:

  ```txt
  python3 -c "import json, os; json.load(open(os.path.expanduser('~/.claude/settings.json'))); print('VALID JSON')"
  ```

  If this errors, the file has a syntax mistake (usually a missing comma or brace) — Claude Code will likely ignore the whole `hooks` block until it's fixed.
- [ ] **Does every hook command end in `|| true`?** Without it, a hook failure (e.g. device unplugged, or the permission error above) surfaces as noisy error output in Claude Code instead of failing silently. This also means Claude Code's own hook log can say "completed successfully" even when the underlying `andon-light` call actually failed — don't trust that log line as proof the light changed; run the command directly (without `|| true`) and check its real exit code if you suspect this.
- [ ] **Are hook commands *not* marked `"async": true`?** Async causes hook commands to complete out of order, leaving the light stuck on a stale color — see [`../../hooks/README.md`](../../hooks/README.md) "Why not async."
- [ ] **Did you restart Claude Code after editing this file?** Hook config is only read when a session starts — a session already running won't pick up a config change. This is the single most common "why didn't it do anything" cause.

## Step 5: Manually Simulate What a Hook Would Do

Useful to isolate "is it the light/CLI, or is it Claude Code's hooks" — run the exact commands a hook would run, by hand:

```txt
andon-light set working    # pixels 2-4 solid green (rest dark except pixel 1)
andon-light set waiting    # pixels 5-7 solid yellow (rest dark except pixel 1)
andon-light set idle       # pixels 8-10 solid red (rest dark except pixel 1)
andon-light set compacting # chase-fill across pixels 2-10
```

If all four work correctly by hand but the light doesn't react during an actual Claude Code session, the problem is in the hook config (Step 4) or Claude Code hasn't picked it up yet (restart it) — not the hardware or CLI.

## Linux-Specific

### Permission Denied Opening the Port

```txt
ls -la /dev/ttyACM0
```

Look at the group column — should be `dialout`.

**Check with `id`, not `groups $USER`** — they can disagree, and only `id` reflects what a running process actually has:

```txt
id
```

`id` (no arguments) shows the group list baked into *this shell's* live credentials — what the kernel checks when `andon-light` opens the port. `groups $USER` re-queries the account database fresh each time, regardless of what any running process actually has. A user can show `dialout` under `groups $USER` while every currently-running shell — including a brand-new one — still lacks it under `id`, because group membership is fixed into a process's credentials at wherever its session chain started, and a normal desktop log-out doesn't reliably rebuild that in every environment.

If `id` is missing `dialout`:

| Fix | Scope | Command |
| --- | --- | --- |
| Immediate unblock | Current shell only | `newgrp dialout` |
| Permanent fix | Every process, system-wide (only reliable option — a desktop log-out alone isn't guaranteed to rebuild every process's credentials) | `sudo reboot` |
| One-off stopgap | Resets on every replug | `sudo chmod 666 /dev/ttyACM0` |

### Launching Arduino IDE from a Terminal

The Arduino IDE AppImage can fail to launch with a FUSE-related error (`dlopen(): error loading libfuse.so.2` or `Cannot mount AppImage`). If double-clicking doesn't work, run it from a terminal instead — bypasses the FUSE mount entirely:

```txt
cd ~/Downloads
./arduino-ide_2.3.10_Linux_64bit.AppImage --appimage-extract-and-run
```

(Adjust the filename for your downloaded version.) Takes a few seconds to extract and open; restores your previously open sketch/tabs automatically.

### Reference: What "Normal" Looks Like

```txt
$ lsusb | grep 2e8a
Bus 005 Device 010: ID 2e8a:0003 Raspberry Pi RP2 Boot      # bootloader mode (bad if unexpected)

# When firmware is running normally, lsusb won't show a distinct "RP2 Boot" line —
# check udevadm instead:
$ udevadm info -a -n /dev/ttyACM0 | grep -iE "manufacturer|product"
ATTRS{manufacturer}=="Waveshare"
ATTRS{product}=="RP2040 Zero"

$ andon-light doctor
Found device on /dev/ttyACM0

$ andon-light set working; echo "exit=$?"
exit=0
```

## Windows-Specific

### SmartScreen Warning

Neither `andon-light.exe` nor `andon-light-setup.exe` is code-signed, so Windows shows "Windows protected your PC" the first time either one runs, and some antivirus engines may flag the build outright — a PyInstaller `--onefile` binary's self-extract-to-temp-dir behavior at runtime resembles a malware dropper. Neither means the build is broken.

**Fix:** click "More info," then "Run anyway."

### `andon-light` Not Found After Installing

Open a **new** terminal — PATH changes made by the installer don't apply to a terminal that was already open.

### Uninstall Left a Stale PATH Entry

If the installed version predates the current installer's PATH-cleanup logic, its uninstaller won't remove the `PATH` entry it added. Check manually: System Properties → Environment Variables → `Path` (User) → remove any leftover `AndonLight` entry.

## Why `host/` Doesn't Need to Know About the LED Hardware

`host/andon_light/cli.py` maps each state to a single ASCII character (`COLOR_COMMANDS = {"working": "G", "waiting": "Y", "idle": "R", "compacting": "C"}`) and hands it to `SerialLink.send()`, which writes that byte plus `\n` to whatever serial port `device_discovery.py` found. Nothing in `host/` knows or cares how many LEDs are on the other end, what pins they're wired to, or whether they're addressable — that logic lives entirely in firmware (`led_controller.cpp`), on the far side of the serial link. Device auto-detection (`DEFAULT_VID = 0x2E8A`) matches the Waveshare RP2040-Zero itself, independent of the LED board attached to it.
