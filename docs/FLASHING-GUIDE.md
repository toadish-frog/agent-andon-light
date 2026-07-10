# Flashing Guide: Swapping Between Firmware Variants

You have one physical board (Waveshare RP2040-Zero) and two separate firmware sketches — `led-bulb/firmware/andon_light_firmware/` and `led-strip/firmware/andon_light_firmware_strip/`. This doc is for when you want to test the strip firmware while the board is currently running the bulb firmware (or vice versa).

## Short answer: yes, you have to reflash

The RP2040's flash memory holds **one program at a time**. There's no toggle, no dual-boot, no runtime switch — "the bulb firmware" and "the strip firmware" are two completely different compiled programs, and uploading one **overwrites** whatever was there before. Whichever sketch you uploaded most recently is the only one that exists on the board; the other one only exists as source code on your computer until you flash it again.

This is the same mechanism as any firmware update — nothing variant-specific about it. Flashing is also non-volatile: once uploaded, the new firmware persists across power cycles/replugs, exactly like the bulb firmware has been doing. It does **not** auto-revert.

## What does *not* change when you swap

- **`host/` (the `andon-light` CLI) — nothing to touch.** It sends the same single-character commands (`G`/`Y`/`R`/`C`/`H`) over serial no matter which firmware is on the other end.
- **`hooks/` (Claude Code integration) — nothing to touch.** Same reasoning — the hook config just calls `andon-light`, which doesn't know or care which variant is flashed.
- **The board's identity/port** — it'll still enumerate as the same Waveshare RP2040-Zero on the same `/dev/ttyACM0` (or similar) either way, since that's determined by the MCU, not the sketch running on it.

Only the physical LED behavior changes: 3 discrete bulbs light up vs. all 10 strip pixels light up together.

## Before you start: do you have the strip PCBA wired up?

- **Yes, it's wired per `led-strip/docs/USER-GUIDE.md`** (`S`→`GPIO1`, `V`→`5V`, `G`→`GND`) → you'll get full visual confirmation the strip lights up correctly. Go to "Step-by-step" below.
- **No, not wired yet — you just want to confirm the strip firmware compiles and flashes cleanly** → you can still do this safely. `GPIO1` will just be an unconnected output pin with nothing listening; nothing bad happens. You won't see any light, but the Serial Monitor will still confirm the board is running the new firmware and responding to commands (see "Verifying without the strip attached" below).
- **Caution if the bulb PCBA is still physically wired to `GPIO1`/`GPIO2`/`GPIO3` when you flash the strip firmware:** the strip firmware only drives `GPIO1` (as WS2812 data timing, not a simple on/off signal), so the bulb PCBA's Green LED (on `GPIO1`) may flicker oddly or look dim — this is harmless, just confusing. It's not a meaningful test of the strip firmware either way. If you want a clean test, disconnect the bulb PCBA's wires first, or wire the strip PCBA to different, currently-unused GPIO pins and change `kDataPin` in `andon_light_firmware_strip.ino` to match before flashing.

## Step-by-step: flashing the strip firmware for testing

### 1. Launch Arduino IDE

Your AppImage is at `~/Downloads/arduino-ide_2.3.10_Linux_64bit.AppImage`. Try double-clicking it first.

**If that fails** with a FUSE-related error (`dlopen(): error loading libfuse.so.2` or `Cannot mount AppImage, please check your FUSE setup`) — confirmed to happen on this machine even with `libfuse2t64` installed — launch it from a terminal instead with the extract-and-run flag, which bypasses the FUSE mount entirely:

```txt
cd ~/Downloads
./arduino-ide_2.3.10_Linux_64bit.AppImage --appimage-extract-and-run
```

**Verified working (2026-07-11):** this command was run directly and confirmed to bring up a working Arduino IDE window — a plain `./arduino-ide_2.3.10_Linux_64bit.AppImage` with no flag was tried first and failed with exactly the FUSE error above; `--appimage-extract-and-run` is what actually launched it, not a guess.

**What happens when you run it:**

1. It extracts the AppImage's contents to a new temp directory, `/tmp/appimage_extracted_<random-hash>/` (~540MB) — this is a one-time-per-launch extraction, not a permanent install.
2. It then runs the extracted `arduino-ide` binary from that temp directory, which spawns several helper processes alongside the main window: an `arduino-cli daemon` (handles board communication), plus `serial-discovery`, `mdns-discovery`, and a `pluggable_discovery.py` process (all for detecting connected boards).
3. The whole thing takes roughly 8–10 seconds from running the command to the window appearing — it's not instant, don't assume it failed if nothing shows up in the first couple seconds.
4. If Arduino IDE was already open with the bulb sketch, it restores that — you're about to point it at the strip sketch instead (next step).

**To check it's actually running**, from another terminal:

```txt
ps aux | grep -i arduino | grep -v grep
```

You should see the main `arduino-ide` process plus the helper processes listed above, all running from a path under `/tmp/appimage_extracted_.../`.

### 2. Open the strip sketch

File → Open → navigate to and select:

```txt
led-strip/firmware/andon_light_firmware_strip/andon_light_firmware_strip.ino
```

Arduino IDE will load `led_controller.h`, `led_controller.cpp`, and `watchdog.h` alongside it as tabs automatically (same as it did for the bulb sketch).

### 3. Install the Adafruit_NeoPixel library (one-time)

The strip firmware needs this library; the bulb firmware never did, so skip this if you've already installed it before.

Tools → Manage Libraries... → search "Adafruit NeoPixel" → Install.

If this step is skipped, the next step (Verify/Compile) will fail with a `Adafruit_NeoPixel.h: No such file or directory` error — that's the tell if you hit it.

### 4. Confirm board and port selection

- Tools → Board → should already show "Waveshare RP2040-Zero" (this doesn't change between sketches — it's the same physical board).
- Tools → Port → should already show the board's port (e.g. `/dev/ttyACM0`). If unsure which port, run `andon-light doctor` in a terminal first — but close Arduino IDE's Serial Monitor (if open) before running it, since only one process can hold the port at a time.

### 5. Upload

Click the Upload button (→ arrow icon), or Sketch → Upload.

**You do not need to force BOOTSEL mode for this.** That manual hold-BOOT-while-replugging trick was only needed the very first time any `arduino-pico` sketch was ever flashed to this board. Since the bulb firmware (also an `arduino-pico` sketch) is already running, its auto-reset-to-bootloader mechanism works normally — Arduino IDE will reset the board into bootloader mode itself, flash, and restart it automatically. Just click Upload and wait for "Done uploading" in the log.

### 6. Verify

**With the strip PCBA wired up:** open the Serial Monitor (Tools → Serial Monitor, or the icon top-right), set baud to 115200 and line ending to "Newline," and type `G`, `Y`, `R`, `C`, pressing enter after each. Confirm all 10 strip pixels respond together, matching the color/animation described in `led-strip/firmware/README.md`.

**Without the strip PCBA wired up (verifying the flash itself, not the light):** same Serial Monitor steps — you won't see any physical light, but if the board doesn't hang, crash, or fail to accept the upload, that confirms the firmware compiled and is running correctly. You can also confirm it's alive via:

```txt
andon-light doctor
andon-light set working; echo "exit=$?"
```

An `exit=0` here means the CLI successfully sent the command over serial and the firmware accepted it — the strip-specific code (`led_controller.cpp`) ran without crashing, even though you can't see the LEDs.

## Swapping back to the bulb firmware afterward

Same procedure, in reverse — this is not optional if you want the board back to daily-driver status, since the strip firmware will keep running indefinitely otherwise (flash doesn't expire or auto-revert):

1. Arduino IDE: File → Open → `led-bulb/firmware/andon_light_firmware/andon_light_firmware.ino`
2. No new library needed (the bulb firmware has no dependencies).
3. Board/port selection unchanged.
4. Click Upload. No BOOTSEL needed, same reasoning as above.
5. Verify: Serial Monitor `G`/`Y`/`R`/`C`, or `andon-light set working` — should drive the 3 discrete bulbs again, back to normal.

## Cleaning up after you're done

`--appimage-extract-and-run` extracts a fresh copy to `/tmp/appimage_extracted_<hash>/` **every time you run it** — it does not reuse a previous extraction. Closing the Arduino IDE window normally (window close button, or Quit from the menu) lets the AppImage runtime clean that temp directory up on its own; you shouldn't normally need to do this by hand.

**If you force-killed Arduino IDE instead of closing it normally** (or it crashed), the temp directory can be left behind and won't clean itself up. Check for leftovers:

```txt
ls -la /tmp/ | grep appimage_extracted
du -sh /tmp/appimage_extracted_* 2>/dev/null
```

Each one is ~540MB, so a few of these accumulating across sessions is worth noticing. To remove a stale one **after confirming Arduino IDE is actually closed** (don't delete out from under a running process):

```txt
ps aux | grep -i arduino | grep -v grep   # should print nothing
rm -rf /tmp/appimage_extracted_<hash>      # use the exact path from the ls above
```

**If Arduino IDE seems stuck or won't reopen cleanly**, kill any lingering processes first, then relaunch:

```txt
pkill -f arduino-ide
pkill -f arduino-cli
```

Then re-run the launch command from Step 1. This is also the right move if a previous Upload got interrupted mid-flash and the board seems unresponsive afterward — kill and relaunch Arduino IDE before assuming the board itself is broken.

## Gotchas

- **Arduino IDE doesn't show you "what's currently flashed."** There's no indicator in the IDE that says which sketch is actually running on the board right now — it only shows which sketch is open in the editor. If you lose track of which firmware is live, the only way to check is by testing behavior (send a command, see what lights up) or re-flashing whichever one you want to be sure of.
- **Close the Serial Monitor before running `andon-light` commands, and vice versa.** Only one process can hold the serial port open at a time — this is the same "Device or resource busy" issue documented in both variants' `TROUBLESHOOTING.md`.
- **Claude Code hooks will keep firing during this whole process**, sending whatever commands correspond to your current Claude Code session state, since hooks don't know or care that you're mid-flash. This is harmless — `andon-light`'s busy-retry and `|| true` absorb any transient conflicts — but don't be surprised if the light changes on its own while you're testing.
- **This doc lives at `docs/` (repo root), not inside either variant's `docs/`,** because it's about the relationship *between* the two variants (which one is physically on the board right now), not about either one specifically.
