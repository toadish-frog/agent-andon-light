# Troubleshooting: Agent Andon Light

A step-by-step diagnostic playbook — the exact terminal commands used to debug every real issue hit while building this project, so you can self-diagnose without needing help. Run these in order; each one narrows down where the problem actually is before you go guessing.

Copy-paste each command block into a terminal. Read the **What it tells you** line before running, so you know what to look for in the output.

## Step 0: what are you actually seeing?

Jump to the matching section:

- Light is completely dark / unresponsive → [Step 1](#step-1-is-the-board-running-firmware-at-all)
- Light is on but the wrong color, or stuck → [Step 4](#step-4-is-the-hook-config-correct)
- `andon-light` command fails or errors → [Step 2](#step-2-is-the-device-reachable-by-the-host-cli)
- Something worked once but broke after unplugging/replugging → [Step 1](#step-1-is-the-board-running-firmware-at-all)

## Step 1: is the board running firmware at all?

```txt
lsusb | grep -i "2e8a"
```

**What it tells you:** every USB device the computer currently sees from this board's vendor ID.

- `2e8a:0003 Raspberry Pi RP2 Boot` → the board is sitting in **bootloader mode**, not running any firmware. No LEDs will respond, no serial port will exist. This happens if you (or a previous flash attempt) held the BOOT button while plugging in, and the flash never completed. Fix: open Arduino IDE and click Upload — it'll detect the board in this state and finish the flash. See "Launching Arduino IDE" below if it's not open.
- A line with `Waveshare` or `RP2040 Zero` in the description → firmware **is** running normally. Move to Step 2.
- Nothing at all → the board isn't connected, or the cable isn't data-capable. Check the USB-C cable (try a different one — many are charge-only) and that it's fully seated.

You can also check for the bootloader's mass-storage drive directly:

```txt
find /media /run/media /mnt -maxdepth 3 -iname "*RPI*" 2>/dev/null
```

If this prints a path (e.g. `/run/media/sean/RPI-RP2`), that confirms bootloader mode — same fix as above.

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

**Important: check with `id`, not `groups $USER`.** These can disagree, and only one of them reflects reality for a running process:

```txt
id
```

`id` (no arguments) shows the group list actually baked into *this shell's* live credentials — this is what the kernel checks when `andon-light` tries to open the port. `groups $USER` instead re-queries the account database fresh, every time, regardless of what any running process actually has. A user can be correctly listed in `dialout` by `groups $USER` while every currently-running shell (including a brand new one) still lacks it in `id` — group membership is fixed into a process's credentials wherever its session chain started, and a normal desktop **"log out"** does not reliably rebuild that in every environment. This was confirmed the hard way (2026-07-08): even a full logout via the desktop menu, followed by opening a brand-new terminal, still showed no `dialout` in `id` for the new shell.

If `id` is missing `dialout`:

- **Immediate unblock, current shell only:**
  ```txt
  newgrp dialout
  ```
  This starts a new shell with `dialout` applied, without needing to log out. Any *already-running* `claude` session (started before you ran this) still won't have it — start a new `claude` session from within this same `newgrp`'d shell to pick it up.
- **Permanent fix, guaranteed to work everywhere (including whatever process hosts a `claude` session in an IDE/editor):**
  ```txt
  sudo reboot
  ```
  A full reboot is the only thing that reliably rebuilds *every* process's credentials from scratch. A desktop "log out" was not sufficient in testing — some session/manager state can persist across it. After rebooting, no `newgrp` or `chmod` is needed again, ever — this is a one-time fix.
- **One-off, if you can't reboot right now:**
  ```txt
  sudo chmod 666 /dev/ttyACM0
  ```
  (Resets on every replug — a stopgap, not a fix.)

**Gotcha: `|| true` hides this failure.** Every hook command ends in `|| true` (see `../../hooks/README.md`) so a disconnected device doesn't spam errors during normal use. This means Claude Code's own hook log (e.g. `PostCompact [andon-light set compacting || true] completed successfully`) will say "completed successfully" **even when the underlying `andon-light` call failed with exactly this permission error** — the hook process itself still exits 0. Don't trust that log line as proof the light actually changed; if you suspect this, run the `andon-light` command directly (without `|| true`) and check its real exit code.

## Step 3: is something else holding the port open?

```txt
andon-light set idle
```

**What it tells you:**

- Succeeds silently, exit code 0 → the CLI → firmware link works. If the physical LED still didn't change, the firmware itself may need reflashing (go to Step 1) or the pin wiring may not match the sketch (see `../firmware/README.md`).
- `andon-light: serial error: ... Device or resource busy` → another program has the port open — almost always Arduino IDE's Serial Monitor. Close it (there's a disconnect/plug icon in the Serial Monitor panel), then retry.

Check the exit code explicitly if the message scrolled past:

```txt
andon-light set idle; echo "exit code: $?"
```

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
- **Did you restart Claude Code after editing this file?** Hook config is only read when a Claude Code session starts — an already-running session will not pick up a config change. This is the single most common "why didn't it do anything" cause.

## Step 5: manually simulate what a hook would do

Useful to isolate "is it the light/CLI, or is it Claude Code's hooks" — run the exact commands a hook would run, by hand:

```txt
andon-light set working    # should go solid green
andon-light set waiting    # should go solid yellow
andon-light set idle       # should go solid red
andon-light set compacting # should go flashing green
```

If all four work correctly by hand but the light doesn't react during an actual Claude Code session, the problem is in the hook config (Step 4) or Claude Code not having picked it up yet (restart it) — not in the hardware or CLI.

## Launching Arduino IDE from a terminal

The Arduino IDE AppImage may fail to launch normally with a FUSE-related error (`dlopen(): error loading libfuse.so.2` or `Cannot mount AppImage`). If double-clicking it doesn't work, run this from a terminal instead — it bypasses the FUSE mount entirely:

```txt
cd ~/Downloads
./arduino-ide_2.3.10_Linux_64bit.AppImage --appimage-extract-and-run
```

(Adjust the filename if you've downloaded a different version.) It'll take a few seconds to extract and open; the window should appear on screen once it's ready. It restores your previously open sketch/tabs automatically.

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
