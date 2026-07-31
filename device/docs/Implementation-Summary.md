# Implementation Summary: Agent Andon Light

Internal reference for tech stack, architecture, and roadmap — dev/agent-facing, not tracked on the remote for outside readers. Update as decisions change.

The addressable WS2812 strip (`device/`) is the sole ongoing hardware line. An earlier 3-discrete-bulb MVP is archived at [`../archive/led-bulb-mvp/`](../archive/led-bulb-mvp/) — not a second deliverable, see History below for why it exists.

---

## 1. Technology Stack

### Hardware

| Part | Choice | Why |
| --- | --- | --- |
| MCU board | Waveshare RP2040-Zero | Native USB (no separate USB-UART chip), 23.5×18mm with castellated pads (hand-solderable), USB-C. Fully supported by Arduino IDE via `arduino-pico`. Onboard WS2812 RGB LED lets firmware/toolchain be smoke-tested before wiring anything external. |
| Status LEDs | Custom PCBA, WS2812-style addressable strip, 10 LEDs, wired via 3-pin connector (`S`/`V`/`G`) | Individually addressable per pixel over one data wire (`Adafruit_NeoPixel`), so each agent state owns a dedicated 3-pixel section instead of one shared color — see [Addressable Pixel Layout](#addressable-pixel-layout). |
| Cable / connector | 3-conductor wire or JST-style connector, plus a data-capable USB-C to USB-A cable to the host | 3 wires (`S`/`V`/`G`) MCU→strip; USB-C carries power + serial to the host. |
| Enclosure | 3D-printed diffuser + base | Passes light through 9 individually visible segments, not 3 discrete bulb positions. |

Full parts list: [`BOM.md`](BOM.md).

### Firmware

- **Language:** C++ (Arduino framework).
- **Library:** Adafruit_NeoPixel — required for WS2812 timing; can't be bit-banged reliably with plain GPIO calls.
- **Toolchain:** Arduino IDE (or Arduino CLI) with the `arduino-pico` board package.
- **Interface:** USB CDC serial — enumerates as a plain serial port on every OS, no custom driver needed on any of them.
- **Power:** must be 5V/`VBUS`, not 3.3V — 10 addressable LEDs draw meaningfully more current than a 3.3V regulator is meant to supply. Firmware caps brightness (`kBrightness = 130/255`) for draw and eye comfort.

### Host Driver Software

- **Language:** Python 3 — runs identically on Linux/Windows/macOS with minimal setup; `pyserial` + `pipx install andon-light` is far less friction than distributing compiled binaries per OS.
- **Key library:** `pyserial`.
- **Packaging:** pip-installable package (`andon-light`) exposing a CLI, published on PyPI.
- **Integration point:** Claude Code [Hooks](https://docs.claude.com/) — mapping and rationale in [`../../hooks/README.md`](../../hooks/README.md). Commands run synchronously (not `async`) — see History for why.
- **Known gap:** no hook fires on a user-initiated Esc/interrupt — not exposed by Claude Code's hook system. The light holds its last color through an Esc interrupt.
- **Unaffected by which firmware is flashed.** `host/andon_light/cli.py` maps each state to a single ASCII byte (`G`/`Y`/`R`/`C`) and writes it to whatever serial port `device_discovery.py` found — it has no idea how many LEDs are on the other end or how they're wired. That logic lives entirely in firmware. This is why `host/` and `hooks/` needed zero changes when the project moved from the bulb MVP to the strip.

---

## 2. Architecture

```txt
┌─────────────────────────┐
│  Claude Code / CLI agent│
│  (hooks fire on events) │
└───────────┬─────────────┘
            │ shell exec
            ▼
┌───────────────────────────┐
│  andon-light CLI (Python) │  ← ../../host/
└───────────┬───────────────┘
            │ USB CDC serial (identical text protocol)
            ▼
┌───────────────────────────┐
│  Firmware (C++/Arduino)   │  ← firmware/andon_light_firmware/
│  - parses commands        │
│  - drives 10 WS2812 pixels│
│    via Adafruit_NeoPixel  │
│  - watchdog / auto-idle   │
└───────────┬───────────────┘
            │ 1 GPIO data pin (+ 5V, GND)
            ▼
┌───────────────────────────┐
│  Custom PCBA, WS2812 strip│
│  10x addressable LEDs     │
└───────────────────────────┘
```

**Wire protocol:**

| Command | Effect |
| --- | --- |
| `G\n` | Working — green section solid |
| `Y\n` | Waiting — yellow section solid |
| `R\n` | Idle — red section solid |
| `C\n` | Compacting — chase-fill sequence |
| `H\n` | Heartbeat — no color change, resets watchdog |

**Reliability:** the firmware runs a watchdog timer — no heartbeat/command within **30 minutes** falls back to a slow-pulse red on the red section ("stale/disconnected") rather than silently freezing on a stale color if the host driver crashes. See History for how the timeout value was tuned.

### Addressable Pixel Layout

Each agent state owns a dedicated sub-range of the strip, rather than setting every pixel to the same color:

| Pixels (1-indexed) | Role | Color |
| --- | --- | --- |
| 1 | Status — always on | Dim white |
| 2-4 | Green section | `G` → solid green |
| 5-7 | Yellow section | `Y` → solid yellow |
| 8-10 | Red section | `R` → solid red; watchdog stale → breathing red (`StalePulse`) |
| 2-10 (all 9 non-status) | `C` (`CompactFlash`) | Chase-fill, not confined to one section |

For `G`/`Y`/`R`/`StalePulse`, only the active section's pixels are lit; every other section is off. Pixel 1 stays dim white through every state, including `Off`, as a constant "board is powered and firmware is running" indicator.

`CompactFlash` chase-fill spans all 9 non-status pixels: a single lit pixel sweeps from pixel 10 down to pixel 2 and locks, the next sweep locks pixel 3 (2 stays lit), and so on — pixels accumulate lit from pixel 2 upward, one per pass, until all 9 are lit, then it resets and repeats. This is a deliberately different rendering path from the other four states (`renderSection()` in `led_controller.cpp` doesn't cover it, since it needs two disjoint lit ranges at once).

**Boot behavior:** the strip boots to `Off` — dim-white status pixel only — since the status pixel alone already serves the "alive" signal, with no need to guess a placeholder state color.

---

## 3. Project Directory Structure

```txt
agent-andon-light/
├── README.md                   # top-level orientation + quick start
├── host/                        # Python driver package (andon-light CLI)
├── hooks/                       # Claude Code integration (settings.snippet.json + README)
├── packaging/                    # OS-specific distribution — windows/, linux/
└── device/                      # the only hardware line
    ├── firmware/
    │   ├── README.md
    │   └── andon_light_firmware/
    │       ├── andon_light_firmware.ino
    │       ├── led_controller.h/.cpp
    │       └── watchdog.h
    ├── hardware/                # KiCad schematic/PCB/manufacturing files — Rev A sent to JLC for fab
    │   ├── kicad/
    │   └── manufacturing/
    ├── archive/
    │   └── led-bulb-mvp/         # frozen 3-discrete-bulb breadboard MVP: firmware + docs
    └── docs/
        ├── BOM.md
        ├── Implementation-Summary.md   # this file
        ├── USER-GUIDE.md
        └── TROUBLESHOOTING.md
```

---

## 4. Roadmap

| # | Goal | Status |
| --- | --- | --- |
| 0 | Research & order parts | Done |
| 1 | Breadboard MVP (bulb PCBA, archived) | Done |
| 2 | Host CLI MVP | Done |
| 3 | Claude Code hook integration | Done |
| 4 | Reliability pass | Mostly done — live unplug/replug + long-turn stress test still outstanding |
| 5 | Custom PCB (strip) | Done — Rev A back from JLC, assembled, reflashed, electrically verified across all 5 units |
| 6 | Enclosure | Done — chassis base + lid 3D-printed via JLC, fit confirmed first-try on all 5 units |
| 7 | Packaging & distribution | Mostly done — PyPI published, `install-hooks` shipped, Windows installer built and verified on real hardware; Linux is docs-only by design, macOS deferred; GitHub release still outstanding |
| 8 | Stretch goals | Backlog — multi-agent/multi-light support, buzzer for alerts, ambient-light brightness sensing, user-configurable color mapping |

---

## 5. Open Items

- **Final brightness value** — `130/255` is a reasoned starting point (current draw + eye comfort), workable behind the actual diffuser, but not formally re-tuned against it.
- **Dim-white status pixel level** — `kDimWhiteLevel = 25` (pre-`kBrightness`-scaling) is a reasoned guess, not explicitly confirmed as the right dimness.
- **Per-unit cost at production quantity** — the 5-board sample order (PCB + assembly + enclosure) was priced well above what a larger MOQ run would cost; no clean per-unit figure logged.
- **macOS support** — deferred, no Apple hardware available to build, sign, or test on. Code-signing/notarization requirements unresearched.
- **`v0.1.0` GitHub release** — not yet cut. Last remaining item in Phase 7.

---

## 6. History

Chronological log of decisions and resolutions — the detail that used to be scattered across every section above now lives here instead.

| Date | Event |
| --- | --- |
| 2026-07-05 | Kickoff. MCU decision: Waveshare RP2040-Zero over XIAO RP2040 / Arduino Pro Micro clone. |
| 2026-07-07 | Bulb-MVP breadboard (Phase 1) flashed and confirmed: `G`/`Y`/`R` correct on physical bulbs, watchdog stale-pulse confirmed. Host CLI MVP (Phase 2) done: `andon-light doctor` auto-detected the board (`DEFAULT_VID = 0x2E8A`, confirmed via `udevadm`); `set working/waiting/idle` confirmed end-to-end. Claude Code hook integration (Phase 3) done: merged into `~/.claude/settings.json`, hook-to-color mapping fine-tuned same day. Reliability pass: hardened `host/andon_light/` error handling (clean one-line message + exit 1 instead of raw traceback), added retry-on-busy-port logic. Watchdog timeout raised from an initial 15s to 30 minutes after real Claude Code sessions showed false stale-triggers during long tool-call-free thinking stretches; `PreToolUse` hook added to keep the watchdog kicked during tool-heavy stretches. |
| 2026-07-08 | `SessionEnd` hook added — `Stop` alone doesn't fire on a user interrupt (Ctrl+C). `async: true` tried and reverted — caused hook commands to complete out of order, leaving the light on a stale color. |
| 2026-07-11 | Strip's own breadboard validation done (ahead of committing to a PCB layout): `kDataPin` confirmed as `GPIO1`; data-line signal integrity at 3.3V logic confirmed fine with a series resistor (level shifter kept as an available fallback); section boundaries (1 status + 3 green + 3 yellow + 3 red) confirmed against the physical 10-pixel strip; `CompactFlash` chase-fill flashed and confirmed working. Bulb variant's own Phase 5 (custom PCB) put on hold in favor of the strip going first. |
| 2026-07-14 | Project restructured: retired the parallel `led-bulb/`/`led-strip/` hardware tracks. Strip renamed from `led-strip/` to `device/` as the sole ongoing hardware line. Bulb MVP archived at `archive/led-bulb-mvp/`. |
| 2026-07-30 | Rev A PCB (5-board sample run) back from JLC — all 5 assembled, reflashed, and individually confirmed working: `G`/`Y`/`R`/`C` correct on the fabricated PCB's own traces, and `StalePulse` triggered and confirmed on real hardware for the first time (previously validated by code inspection only). Enclosure (chassis base + lid) 3D-printed via JLC alongside the PCB order — fit correct first-try on all 5 units, no reprint or redesign needed. Level-shifter footprint confirmed unnecessary on real hardware, left unpopulated. `andon-light` published to PyPI (v0.1.0, MIT licensed). `install-hooks` CLI subcommand shipped. |
| 2026-07-31 | Windows installer (PyInstaller + Inno Setup) built and verified on real Windows hardware: device enumerates as a COM port with zero extra driver steps, PATH resolves in a new terminal, `install-hooks` finish-page flow and uninstall (including a PATH-cleanup fix) both confirmed working. |
