# Troubleshooting: Agent Andon Light (LED Strip variant)

A step-by-step diagnostic playbook for the **addressable LED strip variant**. Steps 1–5 below are structurally identical to the bulb variant's playbook (`../../led-bulb/docs/TROUBLESHOOTING.md`) because the MCU, host CLI, and Claude Code hook layer are the *exact same code* regardless of which LED PCBA is wired up — see "Why `host/` is unaffected by which variant you have" at the bottom for why. This doc reproduces those shared steps in full (rather than just linking out) so you don't have to flip between two files mid-debug, and adds one strip-specific step (Step 3.5) for problems that can't happen on the bulb variant.

Copy-paste each command block into a terminal. Read the **What it tells you** line before running, so you know what to look for in the output.

## Step 0: what are you actually seeing?

Jump to the matching section:

- Light is completely dark / unresponsive → [Step 1](#step-1-is-the-board-running-firmware-at-all)
- Colors look wrong/flickery, or the *lit* section itself looks broken/garbled (not just other sections being dark, which is normal) → [Step 3.5](#step-35-strip-specific-flicker-wrong-colors-or-unexpected-partial-lighting)
- Light is on but the wrong color, or stuck → [Step 4](#step-4-is-the-hook-config-correct)
- `andon-light` command fails or errors → [Step 2](#step-2-is-the-device-reachable-by-the-host-cli)
- Something worked once but broke after unplugging/replugging → [Step 1](#step-1-is-the-board-running-firmware-at-all)

## Step 1: is the board running firmware at all?

```txt
lsusb | grep -i "2e8a"
```

**What it tells you:** every USB device the computer currently sees from this board's vendor ID. Identical check to the bulb variant — the MCU (Waveshare RP2040-Zero) is the same board either way.

- `2e8a:0003 Raspberry Pi RP2 Boot` → the board is sitting in **bootloader mode**, not running any firmware. No LEDs will respond, no serial port will exist. Fix: open Arduino IDE and click Upload — it'll detect the board in this state and finish the flash. See "Launching Arduino IDE" below if it's not open.
- A line with `Waveshare` or `RP2040 Zero` in the description → firmware **is** running normally. Move to Step 2.
- Nothing at all → the board isn't connected, or the cable isn't data-capable. Check the USB-C cable (try a different one — many are charge-only) and that it's fully seated.

You can also check for the bootloader's mass-storage drive directly:

```txt
find /media /run/media /mnt -maxdepth 3 -iname "*RPI*" 2>/dev/null
```

If this prints a path, that confirms bootloader mode — same fix as above.

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

`id` (no arguments) shows the group list actually baked into *this shell's* live credentials — this is what the kernel checks when `andon-light` tries to open the port. `groups $USER` instead re-queries the account database fresh every time, regardless of what any running process actually has. A normal desktop **"log out"** does not reliably rebuild that in every environment (confirmed on the bulb variant, 2026-07-08 — same underlying OS/user account, so it applies here unchanged).

If `id` is missing `dialout`:

- **Immediate unblock, current shell only:**
  ```txt
  newgrp dialout
  ```
- **Permanent fix, guaranteed to work everywhere:**
  ```txt
  sudo reboot
  ```
- **One-off, if you can't reboot right now:**
  ```txt
  sudo chmod 666 /dev/ttyACM0
  ```
  (Resets on every replug — a stopgap, not a fix.)

**Gotcha: `|| true` hides this failure.** Every hook command ends in `|| true` (see `../../hooks/README.md`) so a disconnected device doesn't spam errors during normal use. Claude Code's own hook log will say "completed successfully" **even when the underlying `andon-light` call failed** — the hook process itself still exits 0. If you suspect this, run the `andon-light` command directly (without `|| true`) and check its real exit code.

## Step 3: is something else holding the port open?

```txt
andon-light set idle
```

**What it tells you:**

- Succeeds silently, exit code 0 → the CLI → firmware link works. If the physical LEDs still didn't change, go to Step 3.5 (strip-specific) or the firmware may need reflashing (Step 1).
- `andon-light: serial error: ... Device or resource busy` → another program has the port open — almost always Arduino IDE's Serial Monitor. Close it, then retry.

Check the exit code explicitly if the message scrolled past:

```txt
andon-light set idle; echo "exit code: $?"
```

## Step 3.5: strip-specific — flicker, wrong colors, or unexpected partial lighting

This step doesn't exist in the bulb variant's playbook — discrete on/off bulbs can't exhibit these symptoms, but an addressable strip can, because it depends on precise data timing and adequate power, not just an on/off signal.

**First, rule out the obvious non-bug: partial lighting is the design, not a fault.** Since the pixel-layout refinement, `G`/`Y`/`R` each light only their own 3-pixel section (2-4 / 5-7 / 8-10) plus the always-on dim-white status pixel (1) — see `../firmware/README.md` "Pixel layout: addressable sections, not one solid color." Seeing 7 pixels dark while `G` is active is correct behavior, not a symptom. The signal/power problems below produce a different, distinguishable pattern: pixels *within* the active section itself are wrong (some lit, some not, or garbled color), or the pattern doesn't match any valid section boundary at all.

- **Within the active section, some pixels light up correctly and the rest are garbage/dark (not just "the other two sections are off," but the lit section itself looks broken)** → classic symptom of a data-line signal integrity problem. The RP2040 drives `S` at 3.3V logic; most WS2812 clones tolerate this at short wire runs, but a marginal connection, a long wire, or a clone with tighter timing margins can lose sync partway down the chain. Try: shortening the `S` wire, checking the connector crimp/solder joint, or adding a 74HCT125 level shifter (see `BOM.md` item #7) between `GPIO1` and `S`.
- **Colors look dim, wrong hue, or the board browns-out/resets when the light comes on** → check `V` is wired to the MCU's `5V`/`VBUS` pin, not `3V3` (a common miswiring since `3V3` is often the more prominent pin on breakout diagrams). 10 addressable LEDs draw meaningfully more current than `3V3` regulators on small dev boards are meant to supply. See `../firmware/README.md` "Power note."
- **Nothing lights up at all — not even the pixel-1 status light — but `andon-light set idle` returns exit code 0** → confirm `kDataPin` in `andon_light_firmware_strip.ino` actually matches the GPIO you wired to `S`. Unlike the bulb variant (where a wrong pin still toggles *some* GPIO, just not the one you're watching), a wrong data pin on the strip means zero pixels get valid data at all — check the pin, not the LEDs. (If pixel 1 alone is lit dim white but sections 2-10 stay dark no matter which command you send, that's not a data-pin problem — see Step 3 first, the command may not be reaching the board at all.)
- **The lit pixels don't line up with pixel 1 / 2-4 / 5-7 / 8-10 at all** (e.g. a `G` command lights pixels 4-6 instead of 2-4) → the strip's physical pixel 1 may not correspond to the firmware's index-0 pixel. Addressable strips have a data-in end and a data-out end; if `S` is wired to the wrong end, or the PCBA numbers its pixels in the opposite direction from the firmware's assumption, every section shifts. Check which end of the strip PCBA is silkscreened as the data input and confirm `S` is wired there.
- **Still stuck?** Confirm the Adafruit_NeoPixel library is actually installed (Arduino IDE → Tools → Manage Libraries... → search "Adafruit NeoPixel") — a missing library shows as a compile error, not a runtime symptom, but it's worth ruling out if you're not sure the last flash actually succeeded.

## Step 4: is the hook config correct?

```txt
cat ~/.claude/settings.json
```

**What to check:**

- Is it valid JSON? Run:

```txt
python3 -c "import json; json.load(open('/home/sean/.claude/settings.json'))" && echo "VALID JSON"
```

- Does every hook command end in `|| true`?
- Are the hook commands **not** marked `"async": true`? See `../../hooks/README.md` "Why not async."
- **Did you restart Claude Code after editing this file?** This is the single most common "why didn't it do anything" cause.

This step is identical regardless of variant — the hook config has no idea which LED PCBA is attached, it just runs `andon-light` commands.

## Step 5: manually simulate what a hook would do

```txt
andon-light set working    # pixels 2-4 solid green (rest dark except pixel 1)
andon-light set waiting    # pixels 5-7 solid yellow (rest dark except pixel 1)
andon-light set idle       # pixels 8-10 solid red (rest dark except pixel 1)
andon-light set compacting # pixels 2-4 flashing green (rest dark except pixel 1)
```

If all four work correctly by hand but the light doesn't react during an actual Claude Code session, the problem is in the hook config (Step 4) or Claude Code not having picked it up yet — not in the hardware or CLI.

## Launching Arduino IDE from a terminal

```txt
cd ~/Downloads
./arduino-ide_2.3.10_Linux_64bit.AppImage --appimage-extract-and-run
```

(Adjust the filename if you've downloaded a different version.) Same launch quirk as the bulb variant — see `../../led-bulb/docs/TROUBLESHOOTING.md` for background if double-clicking the AppImage fails with a FUSE error.

## Why `host/` is unaffected by which variant you have

`host/andon_light/cli.py` maps each state to a single ASCII character (`COLOR_COMMANDS = {"working": "G", "waiting": "Y", "idle": "R", "compacting": "C"}`) and hands it to `SerialLink.send()`, which just writes that byte plus `\n` to whatever serial port `device_discovery.py` found. Nothing in `host/` knows or cares how many LEDs are on the other end, what pins they're wired to, or whether they're addressable — that logic lives entirely in firmware (`led_controller.cpp` on either variant), on the far side of the serial link. Device auto-detection (`DEFAULT_VID = 0x2E8A`) matches the **Waveshare RP2040-Zero**, which is identical hardware on both variants — only the downstream LED PCBA differs. So the same `andon-light` install, the same hooks config, and the same troubleshooting Steps 2–5 above apply unchanged no matter which firmware is flashed.

## Reference: what "normal" looks like

```txt
$ lsusb | grep 2e8a
Bus 005 Device 010: ID 2e8a:0003 Raspberry Pi RP2 Boot      # ← bootloader mode (bad if unexpected)
# when firmware is running normally, check instead:
#   udevadm info -a -n /dev/ttyACM0 | grep -iE "manufacturer|product"
#   ATTRS{manufacturer}=="Waveshare"
#   ATTRS{product}=="RP2040 Zero"

$ andon-light doctor
Found device on /dev/ttyACM0

$ andon-light set working; echo "exit=$?"
exit=0
```

This reference output is identical to the bulb variant's — captured against the same MCU. Not yet captured against the physical strip PCBA specifically (see `../docs/Implementation-Summary.md` roadmap status); update this section once the strip has been flashed and observed on real hardware.
