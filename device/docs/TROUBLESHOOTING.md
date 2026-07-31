# Troubleshooting: Agent Andon Light

A step-by-step diagnostic playbook — the exact terminal commands used to debug every real issue hit while building this project. Run these in order; each one narrows down where the problem actually is before you go guessing.

Copy-paste each command block into a terminal. Read the **What it tells you** line before running, so you know what to look for in the output.

## Step 0: what are you actually seeing?

Jump to the matching section:

- Light is completely dark / unresponsive → [Step 1](#step-1-is-the-board-running-firmware-at-all)
- Colors look wrong/flickery, or the *lit* section itself looks broken/garbled (not just other sections being dark, which is normal) → [Step 3.5](#step-35-flicker-wrong-colors-or-unexpected-partial-lighting)
- Light is on but the wrong color, or stuck → [Step 4](#step-4-is-the-hook-config-correct)
- `andon-light` command fails or errors → [Step 2](#step-2-is-the-device-reachable-by-the-host-cli)
- Something worked once but broke after unplugging/replugging → [Step 1](#step-1-is-the-board-running-firmware-at-all)

## Step 1: is the board running firmware at all?

```txt
lsusb | grep -i "2e8a"
```

**What it tells you:** every USB device the computer currently sees from this board's vendor ID.

- `2e8a:0003 Raspberry Pi RP2 Boot` → the board is in **bootloader mode**, not running firmware. No LEDs will respond, no serial port will exist. This happens if you (or a previous flash attempt) held the BOOT button while plugging in, and the flash never completed. Fix: open Arduino IDE and click Upload — it detects the board in this state and finishes the flash. See "Launching Arduino IDE" below if it's not open.
- A line with `Waveshare` or `RP2040 Zero` in the description → firmware **is** running normally. Move to Step 2.
- Nothing at all → the board isn't connected, or the cable isn't data-capable. Try a different USB-C cable (many are charge-only) and confirm it's fully seated.

You can also check for the bootloader's mass-storage drive directly:

```txt
find /media /run/media /mnt -maxdepth 3 -iname "*RPI*" 2>/dev/null
```

A printed path (e.g. `/run/media/sean/RPI-RP2`) confirms bootloader mode — same fix as above.

## Step 2: is the device reachable by the host CLI?

```txt
andon-light doctor
```

**What it tells you:**

- `Found device on /dev/ttyACM0` (or similar) → CLI can see it, port permissions are fine. Move to Step 3.
- `No device found`, or `andon-light` fails with `[Errno 13] Permission denied` → either the board isn't running firmware (go back to Step 1), or it's a permissions issue — check next:

```txt
ls -la /dev/ttyACM0
```

Look at the group column (should be `dialout`).

**Check with `id`, not `groups $USER`** — they can disagree, and only one reflects reality for a running process:

```txt
id
```

`id` (no arguments) shows the group list baked into *this shell's* live credentials — what the kernel checks when `andon-light` opens the port. `groups $USER` instead re-queries the account database fresh each time, regardless of what any running process actually has. A user can show `dialout` under `groups $USER` while every currently-running shell — including a brand-new one — still lacks it under `id`: group membership is fixed into a process's credentials at wherever its session chain started, and a normal desktop **log out** doesn't reliably rebuild that in every environment. Confirmed the hard way (2026-07-08): a full logout via the desktop menu, followed by a brand-new terminal, still showed no `dialout` in `id` for the new shell.

If `id` is missing `dialout`:

- **Immediate unblock, current shell only:**

  ```txt
  newgrp dialout
  ```

  Starts a new shell with `dialout` applied, no logout needed. Any `claude` session already running (started before this) still won't have it — start a new session from within this same `newgrp`'d shell.
- **Permanent fix, works everywhere (including whatever process hosts a `claude` session in an IDE/editor):**

  ```txt
  sudo reboot
  ```

  A full reboot is the only thing that reliably rebuilds *every* process's credentials from scratch — a desktop log-out was not sufficient in testing, since some session/manager state can persist across it. No `newgrp` or `chmod` needed again after rebooting; it's a one-time fix.
- **One-off, if you can't reboot right now:**

  ```txt
  sudo chmod 666 /dev/ttyACM0
  ```

  Resets on every replug — a stopgap, not a fix.

**Gotcha: `|| true` hides this failure.** Every hook command ends in `|| true` (see `../../hooks/README.md`), so a disconnected device doesn't spam errors during normal use. That means Claude Code's own hook log (e.g. `PreCompact [andon-light set compacting || true] completed successfully`) reports "completed successfully" **even when the underlying `andon-light` call failed with exactly this permission error** — the hook process itself still exits 0. Don't trust that log line as proof the light actually changed; if you suspect this, run the `andon-light` command directly, without `|| true`, and check its real exit code.

## Step 3: is something else holding the port open?

```txt
andon-light set idle
```

**What it tells you:**

- Succeeds silently, exit code 0 → the CLI → firmware link works. If the physical LEDs still didn't change, go to Step 3.5, or the firmware may need reflashing (Step 1).
- `andon-light: serial error: ... Device or resource busy` → another program has the port open, almost always Arduino IDE's Serial Monitor. Close it (there's a disconnect/plug icon in the Serial Monitor panel) and retry.

Check the exit code explicitly if the message scrolled past:

```txt
andon-light set idle; echo "exit code: $?"
```

## Step 3.5: flicker, wrong colors, or unexpected partial lighting

Addressable strips depend on precise data timing and adequate power, not just an on/off signal, so they can show symptoms a simpler discrete-LED board couldn't.

**First, rule out the obvious non-bug: partial lighting is the design, not a fault.** `G`/`Y`/`R` each light only their own 3-pixel section (2-4 / 5-7 / 8-10) plus the always-on dim-white status pixel (1) — see `USER-GUIDE.md` "Pixel layout." Seeing 7 pixels dark while `G` is active is correct behavior. The signal/power problems below look different: pixels *within* the active section itself are wrong (some lit, some not, or garbled color), or the pattern doesn't match any valid section boundary at all.

- **Within the active section, some pixels light correctly and the rest are garbage/dark (the lit section itself looks broken, not just other sections being off)** → classic data-line signal integrity problem. The RP2040 drives `S` at 3.3V logic; most WS2812 clones tolerate this at short wire runs, but a marginal connection, a long wire, or a clone with tighter timing margins can lose sync partway down the chain. Try shortening the `S` wire, checking the connector crimp/solder joint, or adding a 74HCT125 level shifter (see `BOM.md` item #7) between `GPIO1` and `S`.
- **Colors look dim, wrong hue, or the board browns-out/resets when the light comes on** → check `V` is wired to the MCU's `5V`/`VBUS` pin, not `3V3` (a common miswiring since `3V3` is often the more prominent pin on breakout diagrams). 10 addressable LEDs draw meaningfully more current than `3V3` regulators on small dev boards are meant to supply — see `../firmware/README.md` "Power note."
- **Nothing lights up at all — not even the pixel-1 status light — but `andon-light set idle` returns exit code 0** → confirm `kDataPin` in `andon_light_firmware_strip.ino` actually matches the GPIO wired to `S`. A wrong data pin means zero pixels get valid data — check the pin, not the LEDs. (If pixel 1 alone is lit dim white but sections 2-10 stay dark regardless of command, that's not a data-pin problem — see Step 3 first, the command may not be reaching the board at all.)
- **The lit pixels don't line up with pixel 1 / 2-4 / 5-7 / 8-10 at all** (e.g. a `G` command lights pixels 4-6 instead of 2-4) → the strip's physical pixel 1 may not correspond to the firmware's index-0 pixel. Addressable strips have a data-in end and a data-out end; if `S` is wired to the wrong end, or the PCBA numbers its pixels in the opposite direction from the firmware's assumption, every section shifts. Check which end of the strip PCBA is silkscreened as the data input and confirm `S` is wired there.
- **Still stuck?** Confirm the Adafruit_NeoPixel library is actually installed (Arduino IDE → Tools → Manage Libraries... → search "Adafruit NeoPixel") — a missing library shows as a compile error, not a runtime symptom, but it's worth ruling out if you're unsure the last flash actually succeeded.

## Step 4: is the hook config correct?

```txt
cat ~/.claude/settings.json
```

**What to check:**

- Is it valid JSON? Run:

```txt
python3 -c "import json; json.load(open('/home/sean/.claude/settings.json'))" && echo "VALID JSON"
```

If this errors, the file has a syntax mistake (usually a missing comma or brace) — Claude Code will likely ignore the whole `hooks` block until it's fixed.

- Does every hook command end in `|| true`? Without it, a hook failure (e.g. device unplugged) surfaces as noisy error output in Claude Code instead of failing silently.
- Are the hook commands **not** marked `"async": true`? Async was tried and reverted (2026-07-08) — it caused hook commands to complete out of order, leaving the light stuck on a stale color. See `../../hooks/README.md` "Why not async" for the full story.
- **Did you restart Claude Code after editing this file?** Hook config is only read when a Claude Code session starts — a session already running won't pick up a config change. This is the single most common "why didn't it do anything" cause.

## Step 5: manually simulate what a hook would do

Useful to isolate "is it the light/CLI, or is it Claude Code's hooks" — run the exact commands a hook would run, by hand:

```txt
andon-light set working    # pixels 2-4 solid green (rest dark except pixel 1)
andon-light set waiting    # pixels 5-7 solid yellow (rest dark except pixel 1)
andon-light set idle       # pixels 8-10 solid red (rest dark except pixel 1)
andon-light set compacting # chase-fill across pixels 2-10, filling in one pixel per pass until all 9 are lit, then resets
```

If all four work correctly by hand but the light doesn't react during an actual Claude Code session, the problem is in the hook config (Step 4) or Claude Code hasn't picked it up yet (restart it) — not the hardware or CLI.

## Launching Arduino IDE from a terminal

The Arduino IDE AppImage may fail to launch normally with a FUSE-related error (`dlopen(): error loading libfuse.so.2` or `Cannot mount AppImage`). If double-clicking doesn't work, run this from a terminal instead — it bypasses the FUSE mount entirely:

```txt
cd ~/Downloads
./arduino-ide_2.3.10_Linux_64bit.AppImage --appimage-extract-and-run
```

(Adjust the filename for your downloaded version.) It takes a few seconds to extract and open; the window appears once ready, restoring your previously open sketch/tabs automatically.

## Why `host/` doesn't need to know about the LED hardware

`host/andon_light/cli.py` maps each state to a single ASCII character (`COLOR_COMMANDS = {"working": "G", "waiting": "Y", "idle": "R", "compacting": "C"}`) and hands it to `SerialLink.send()`, which writes that byte plus `\n` to whatever serial port `device_discovery.py` found. Nothing in `host/` knows or cares how many LEDs are on the other end, what pins they're wired to, or whether they're addressable — that logic lives entirely in firmware (`led_controller.cpp`), on the far side of the serial link. Device auto-detection (`DEFAULT_VID = 0x2E8A`) matches the **Waveshare RP2040-Zero** itself, independent of the LED board attached to it. This is also why `host/` needed zero changes when this project's Phase 1 MVP hardware (3 discrete bulbs, now archived at `../archive/led-bulb-mvp/`) was retired in favor of the WS2812 strip.

## Reference: what "normal" looks like

For comparison, here's confirmed-working output from this project's actual hardware (a Waveshare RP2040-Zero), so you know what a healthy state looks like:

```txt
$ lsusb | grep 2e8a
Bus 005 Device 010: ID 2e8a:0003 Raspberry Pi RP2 Boot      # ← bootloader mode (bad if unexpected)
# vs., when firmware is running normally, lsusb won't show a distinct "RP2 Boot" line —
# check `udevadm info -a -n /dev/ttyACM0 | grep -iE "manufacturer|product"` instead:
#   ATTRS{manufacturer}=="Waveshare"
#   ATTRS{product}=="RP2040 Zero"

$ andon-light doctor
Found device on /dev/ttyACM0

$ andon-light set working; echo "exit=$?"
exit=0
```
