# Troubleshooting: Agent Andon Light (3-Bulb MVP)

Diagnostic playbook — work through these in order to narrow down where a problem actually is. Copy-paste each command into a terminal; read the table below it before running.

## Start Here

| Symptom | Go to |
| --- | --- |
| Light completely dark / unresponsive | [Step 1](#step-1-is-the-board-running-firmware-at-all) |
| Light on but wrong color, or stuck | [Step 4](#step-4-is-the-hook-config-correct) |
| `andon-light` command fails or errors | [Step 2](#step-2-is-the-device-reachable-by-the-host-cli) |
| Worked once, broke after unplug/replug | [Step 1](#step-1-is-the-board-running-firmware-at-all) |

## Step 1: Is the Board Running Firmware at All?

```txt
lsusb | grep -i "2e8a"
```

| Output | Meaning | Fix |
| --- | --- | --- |
| `2e8a:0003 Raspberry Pi RP2 Boot` | Board is in **bootloader mode**, not running firmware | Open Arduino IDE and click Upload — it detects this state and finishes the flash |
| Line with `Waveshare` or `RP2040 Zero` | Firmware **is** running normally | Move to Step 2 |
| Nothing | Board not connected, or cable isn't data-capable | Try a different USB-C cable, confirm fully seated |

Check for the bootloader's mass-storage drive directly:

```txt
find /media /run/media /mnt -maxdepth 3 -iname "*RPI*" 2>/dev/null
```

A printed path confirms bootloader mode — same fix as above.

## Step 2: Is the Device Reachable by the Host CLI?

```txt
andon-light doctor
```

| Output | Meaning |
| --- | --- |
| `Found device on /dev/ttyACM0` (or similar) | CLI can see it, port permissions fine — move to Step 3 |
| `No device found` | Board isn't running firmware — go back to Step 1 |
| `[Errno 13] Permission denied` | Permissions issue — check below |

```txt
ls -la /dev/ttyACM0
```

Look at the group column — should be `dialout`.

**Check with `id`, not `groups $USER`** — they can disagree, and only `id` reflects what a running process actually has:

```txt
id
```

`id` shows the group list baked into *this shell's* live credentials — what the kernel checks when `andon-light` opens the port. `groups $USER` re-queries the account database fresh each time, regardless of what any running process actually has. A user can show `dialout` under `groups $USER` while every currently-running shell — including a brand-new one — still lacks it under `id`, because group membership is fixed into a process's credentials wherever its session chain started, and a normal desktop log-out doesn't reliably rebuild that in every environment.

If `id` is missing `dialout`:

| Fix | Scope | Command |
| --- | --- | --- |
| Immediate unblock | Current shell only | `newgrp dialout` |
| Permanent fix | Every process, system-wide | `sudo reboot` |
| One-off stopgap | Resets on every replug | `sudo chmod 666 /dev/ttyACM0` |

**Gotcha: `|| true` hides this failure.** Every hook command ends in `|| true` (see [`../../../hooks/README.md`](../../../hooks/README.md)), so Claude Code's hook log can report "completed successfully" even when the underlying `andon-light` call actually failed with this exact permission error — the hook process itself still exits 0. Don't trust that log line; run the command directly (without `|| true`) and check its real exit code if you suspect this.

## Step 3: Is Something Else Holding the Port Open?

```txt
andon-light set idle
```

| Output | Meaning |
| --- | --- |
| Succeeds silently, exit code 0 | CLI → firmware link works. LED didn't change? Reflash (Step 1) or check the pin wiring matches the sketch (see `../firmware/README.md`). |
| `Device or resource busy` | Another program has the port open — almost always Arduino IDE's Serial Monitor. Close it and retry. |

```txt
andon-light set idle; echo "exit code: $?"
```

## Step 4: Is the Hook Config Correct?

```txt
cat ~/.claude/settings.json
```

- [ ] **Valid JSON?** Run: `python3 -c "import json, os; json.load(open(os.path.expanduser('~/.claude/settings.json'))); print('VALID JSON')"`
- [ ] **Does every hook command end in `|| true`?** Without it, a hook failure surfaces as noisy error output instead of failing silently.
- [ ] **Hook commands *not* marked `"async": true`?** Async causes hook commands to complete out of order, leaving the light stuck on a stale color — see [`../../../hooks/README.md`](../../../hooks/README.md) "Why not async."
- [ ] **Restarted Claude Code after editing this file?** Hook config is only read at session start.

## Step 5: Manually Simulate What a Hook Would Do

```txt
andon-light set working    # solid green
andon-light set waiting    # solid yellow
andon-light set idle       # solid red
andon-light set compacting # flashing green
```

If all four work by hand but the light doesn't react during an actual Claude Code session, the problem is the hook config (Step 4) or Claude Code hasn't picked it up yet — not the hardware or CLI.

## Launching Arduino IDE from a Terminal

The Arduino IDE AppImage can fail to launch with a FUSE-related error (`dlopen(): error loading libfuse.so.2` or `Cannot mount AppImage`). Run it from a terminal instead — bypasses the FUSE mount entirely:

```txt
cd ~/Downloads
./arduino-ide_2.3.10_Linux_64bit.AppImage --appimage-extract-and-run
```

(Adjust the filename for your version.) Takes a few seconds to extract; restores your previously open sketch/tabs.

## Reference: What "Normal" Looks Like

```txt
$ lsusb | grep 2e8a
Bus 005 Device 010: ID 2e8a:0003 Raspberry Pi RP2 Boot      # bootloader mode (bad if unexpected)

$ udevadm info -a -n /dev/ttyACM0 | grep -iE "manufacturer|product"
ATTRS{manufacturer}=="Waveshare"
ATTRS{product}=="RP2040 Zero"

$ andon-light doctor
Found device on /dev/ttyACM0

$ andon-light set working; echo "exit=$?"
exit=0
```
