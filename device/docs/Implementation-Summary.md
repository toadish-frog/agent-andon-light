# Implementation Summary: Agent Andon Light

*Generated from `.prompt/arch/ARCH-prompt.md`. This is the living reference for the project's tech stack, architecture, structure, and roadmap. Update it as decisions change — treat it as project memory, not a one-time snapshot.*

This is now the **sole** Implementation Summary for the project. Through 2026-07-14 the project carried two parallel hardware tracks — `led-bulb/` (3 discrete LED bulbs) and `led-strip/` (10-LED addressable WS2812 strip) — each with its own doc set. That's retired: **the addressable strip is the only ongoing hardware line**, now living at `device/` (renamed from `led-strip/`, since "strip" no longer needs to disambiguate from anything). The bulb PCBA is preserved as history at [`../archive/led-bulb-mvp/`](../archive/led-bulb-mvp/) — see "Phase 1 — Breadboard MVP" below — not kept as a second deliverable.

---

## 1. Recommended Technology Stack

### Hardware

| Part | Recommendation | Why |
| --- | --- | --- |
| MCU board | **Waveshare RP2040-Zero** | Native USB (no separate USB-UART chip), thumbnail-sized (23.5×18mm) with castellated pads (hand-solderable onto a custom PCB), USB-C, ~¥30. Fully supported by Arduino IDE via the `arduino-pico` board package. Has its own onboard WS2812 RGB LED (GPIO16), so firmware/toolchain can be smoke-tested before wiring anything external. |
| Status LEDs (final) | **Custom PCBA, WS2812-style addressable strip, 10 LEDs**, wired to the MCU via a 3-pin connector (`S`/`V`/`G`) | The project's only status-light hardware. Individually addressable per pixel over one data wire (`Adafruit_NeoPixel`), letting each agent state own a dedicated 3-pixel section instead of one shared color across fixed bulbs — see "Addressable pixel layout" below. |
| Status LEDs (Phase 1 interim, archived) | Custom PCBA, 3x discrete LED bulbs (Red/Yellow/Green), 4-pin connector (`GND`+3 signal) | Validated firmware/host-CLI/hooks end-to-end before the strip's custom PCB existed — see "Phase 1 — Breadboard MVP" below and [`archive/led-bulb-mvp/`](../archive/led-bulb-mvp/). Each bulb was a plain on/off GPIO output (`digitalWrite`/`analogWrite`, no addressable protocol) — simpler to drive, at the cost of the strip's per-pixel flexibility. Retired once the strip PCB was designed and sent to fab. |
| Cable / connector | 3-conductor wire or JST-style connector matching the strip PCBA's header, plus a data-capable USB-C to USB-A cable to the host | 3 wires (`S`/`V`/`G`) from MCU to the strip PCBA; USB-C carries power + serial to the host computer. |
| Enclosure | 3D-printed diffuser + base | Passes light through 9 individually visible segments, not 3 discrete bulb positions — see Phase 6 below. |

No part on this list is export-restricted or unusual — it's a commodity microcontroller and commodity LEDs, the same components used in countless hobbyist keyboards and lamps.

### Firmware

- **Language:** C++ (Arduino framework).
- **Library:** **Adafruit_NeoPixel** — required for the WS2812 strip; timing can't be bit-banged reliably with plain GPIO calls. (The archived bulb MVP needed no LED library — plain `digitalWrite`/`analogWrite` sufficed for 3 discrete on/off bulbs.)
- **Toolchain:** Arduino IDE (or Arduino CLI) with the `arduino-pico` board package.
- **Interface:** USB CDC serial — enumerates as a plain serial port on every OS, no custom driver needed on any of them (confirmed on Windows 2026-07-31: zero extra driver steps, no `arduino-pico` INF required).
- **Power:** must be 5V/`VBUS`, not 3.3V — 10 addressable LEDs draw meaningfully more current than the bulb MVP's 3 discrete LEDs did. Firmware caps brightness (`kBrightness = 130/255`) to keep draw and eye comfort reasonable.

### Host Driver Software

- **Language: Python 3.** Deliberate deviation from C (firmware stays C++): the host needs to run identically on Linux/Windows/macOS with minimal setup, and `pyserial` + `pipx install andon-light` is far less friction than distributing compiled C binaries for three OSes.
- **Key library:** `pyserial` for the serial link.
- **Packaging:** a small pip-installable package (`andon-light`) exposing a CLI.
- **Integration point:** Claude Code [Hooks](https://docs.claude.com/) — `SessionStart` → `andon-light set idle` (default state), `UserPromptSubmit`/`PreToolUse` → `andon-light set working`, `Notification`/`PermissionRequest` → `andon-light set waiting`, `PreCompact` → `andon-light set compacting` (chase-fill on the strip), `Stop`/`SessionEnd` → `andon-light set idle`. Commands run synchronously, not `async` — each call is only ~40-50ms, and `async` was found to cause an ordering race (see `../../hooks/README.md` "Why not async").
- **Known gap:** no hook fires on a user-initiated Esc/interrupt — not currently exposed by Claude Code's hook system. The light holds its last color through an Esc interrupt.
- **Planned: one-click cross-platform installer** — see Phase 7 below.
- **Unaffected by which firmware is flashed.** `host/andon_light/cli.py` maps each state to a single ASCII byte (`G`/`Y`/`R`/`C`) and writes it to whatever serial port `device_discovery.py` found — it has no idea how many LEDs are on the other end or how they're wired. That logic lives entirely in firmware, on the far side of the serial link. This is why `host/` and `hooks/` needed zero changes when the project moved from the bulb MVP to the strip.

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
│  andon-light CLI (Python) │  ← ../../host/ (unmodified since the bulb MVP)
└───────────┬───────────────┘
            │ USB CDC serial (identical text protocol)
            ▼
┌───────────────────────────┐
│  Firmware (C++/Arduino)   │  ← firmware/andon_light_firmware_strip/
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

**Wire protocol (deliberately simple):**

```txt
G\n   → working states section solid green
Y\n   → waiting states section solid yellow
R\n   → idle states section solid red
C\n   → compacting: chase-fill sequence (internal maintenance, still "alive")
H\n   → heartbeat (no color change, resets watchdog)
```

**Reliability design point:** the premise of this device is that the user *walks away and trusts it*. The firmware runs a watchdog timer — if no heartbeat or command arrives within **30 minutes** of the last one, it falls back to a distinct slow-pulse red on the red section ("stale/disconnected") rather than silently freezing on a stale color if the host driver crashes. Originally 15s, raised to 30 minutes (2026-07-07) after real Claude Code sessions showed it false-triggering during long tool-call-free thinking stretches; a `PreToolUse` hook was added so any tool-heavy stretch keeps kicking the watchdog continuously.

### Addressable pixel layout

Each agent state owns a dedicated sub-range of the strip, rather than setting every pixel to the same color:

| Pixels (1-indexed) | Role | Color |
| --- | --- | --- |
| 1 | Status — always on, regardless of state | Dim white |
| 2-4 | Green section | `G` state → solid green |
| 5-7 | Yellow section | `Y` state → solid yellow |
| 8-10 | Red section | `R` state → solid red; watchdog stale → breathing red (`StalePulse`) |
| 2-10 (all 9 non-status pixels) | `C` (`CompactFlash`) | Chase-fill sequence, not confined to one section |

For `G`/`Y`/`R`/`StalePulse`, only the active section's pixels are lit at any given time; every other section is off. The status pixel (1) is the exception — it stays dim white through every state, including `Off`, as a constant "board is powered and firmware is running" indicator.

`CompactFlash` is a chase-fill sequence spanning all 9 non-status pixels: a single lit pixel sweeps down from pixel 10 to pixel 2 and locks on, the next sweep goes down to pixel 3 (pixel 2 stays lit) and locks pixel 3, and so on — pixels accumulate lit from pixel 2 upward, one per pass, until all 9 are lit, then it resets to empty and repeats. This is a deliberately different rendering path from the other four states (`renderSection()` in `led_controller.cpp` doesn't cover it, since it needs two disjoint lit ranges at once).

**Boot behavior:** the strip boots to `Off` — dim-white status pixel only, all three color sections dark — because the status pixel already serves the "alive" signal on its own, without needing to guess a placeholder state color. (The archived bulb MVP instead booted to solid red, since it had no separate status indicator to lean on — see `archive/led-bulb-mvp/firmware/andon_light_firmware/led_controller.cpp`.)

---

## 3. Project Directory Structure

```txt
agent-andon-light/
├── README.md                   # top-level orientation + quick start
├── docs/                        # (retired 2026-07-14 — was cross-variant FLASHING-GUIDE, no longer needed with one firmware)
├── host/                        # Python driver package (andon-light CLI) — unmodified since the bulb MVP
├── hooks/                       # Claude Code integration (settings.snippet.json + README)
└── device/                      # the only hardware line
    ├── firmware/
    │   ├── README.md
    │   └── andon_light_firmware_strip/
    │       ├── andon_light_firmware_strip.ino
    │       ├── led_controller.h/.cpp
    │       └── watchdog.h
    ├── hardware/                # KiCad schematic/PCB/manufacturing files — Rev A sent to JLC for fab
    │   ├── kicad/
    │   └── manufacturing/
    ├── archive/
    │   └── led-bulb-mvp/         # frozen Phase 0-4 MVP: firmware + docs for the 3-discrete-bulb breadboard PCBA
    └── docs/
        ├── BOM.md
        ├── Implementation-Summary.md   # this file
        ├── USER-GUIDE.md
        └── TROUBLESHOOTING.md
```

---

## 4. Project Style & Delivery Timeline

### Methodology: Phase-Gated Kanban

Not Scrum, not pure waterfall — a hybrid that fits a solo builder mixing hardware and software:

- **Phase-gated** because hardware forces real sequential dependencies a sprint board can't paper over — you can't route a custom PCB before the firmware/host/hook logic actually works, and you can't do anything in a phase until the parts for it have physically arrived.
- **Kanban, not fixed sprints,** within and across phases — a parts shipment or a PCB fab run doesn't respect a 2-week sprint boundary.
- **Agile-style short feedback loops within each phase** — each phase ends in something you can see or hold (a blinking LED, a working CLI call, a live Claude Code demo).

### Timeline Assumptions

- Solo, part-time hobbyist pace (~5–8 hours/week).
- Parts shipping: ~1–5 days. PCB fab + shipping: ~1 week for a standard small-batch order.
- **Kickoff: 2026-07-05.**

### 4.1 Roadmap Tracking Table

| Phase | Goal | Status |
| --- | --- | --- |
| 0 | Research & Order Parts | **Done** |
| 1 | Breadboard MVP (bulb PCBA, archived) | **Done (2026-07-07)** — see `archive/led-bulb-mvp/docs/Implementation-Summary.md` §5 Phase 1 |
| 2 | Host CLI MVP | **Done (2026-07-07)** |
| 3 | Claude Code Hook Integration | **Done (2026-07-07)** |
| 4 | Reliability Pass | **Mostly done (2026-07-07)** — live unplug/replug + long-turn stress test still outstanding |
| 5 | Custom PCB (strip) | **Done (2026-07-30)** — Rev A back from JLC, assembled, reflashed, and electrically verified across all 5 units |
| 6 | Enclosure | **Done (2026-07-30)** — chassis base + lid 3D-printed via JLC, fit confirmed first-try on all 5 units, no rework needed |
| 7 | Packaging & Distribution | **Mostly done (2026-07-31)** — PyPI published, `install-hooks` shipped, Windows installer built and verified on real hardware; Linux is docs-only by design, macOS deferred; GitHub release still outstanding |
| 8 | Stretch Goals | Backlog |

---

## 5. Development Roadmap — Detailed Phase Breakdown

### Phase 0 — Research & Order Parts

*Est. 3–7 days elapsed (shipping) · 3–5 hrs effort*

- Install Arduino IDE 2.x; add the `arduino-pico` board-manager URL; install the RP2040 board package.
- **Status: Done.** RP2040-Zero + (at the time) a 3-discrete-bulb LED PCBA in hand, soldered and wired. The firmware sketch, host CLI, and hooks config were all written ahead of parts arriving, since none of it needed hardware to write.

### Phase 1 — Breadboard MVP

*Est. ~1 week · 5–8 hrs effort*

**Historical note (2026-07-14):** this phase was completed against the 3-discrete-bulb PCBA, not the WS2812 strip — the strip's own breadboard validation happened later (now summarized in Phase 5 below) since the strip skipped straight to a custom PCB once the bulb MVP had already proven out firmware/host/hooks. Full detail (soldering castellated pads, 4-pin wiring, pin confirmation) is preserved at [`../archive/led-bulb-mvp/`](../archive/led-bulb-mvp/), not reproduced here since it's not part of the ongoing deliverable.

- **Status: Done (2026-07-07).** Flashed to a real Waveshare RP2040-Zero via Arduino IDE. `G`/`Y`/`R` confirmed correct on the physical bulbs; watchdog stale-pulse confirmed (dropped to breathing red after ~15–18s with no heartbeat, before the timeout was later raised to 30 min).

### Phase 2 — Host CLI MVP

*Est. 3–5 days · 4–6 hrs effort*

- Scaffold the `andon-light` Python package (`pyproject.toml`, `andon_light/`), implement `serial_link.py` + `cli.py`.
- **Status: Done (2026-07-07).** `andon-light doctor` auto-detected the board (`DEFAULT_VID = 0x2E8A`, confirmed via `udevadm`). `andon-light set working/waiting/idle` confirmed end-to-end against real hardware. Gotcha hit: "Device or resource busy" until Arduino IDE's Serial Monitor was disconnected — only one process can hold a serial port at a time.

### Phase 3 — Claude Code Hook Integration

*Est. 2–3 days · 3–4 hrs effort*

- Write `hooks/settings.snippet.json`; merge into a real `settings.json`; run a live Claude Code session against the device.
- **Status: Done (2026-07-07).** `andon-light` installed globally via `pipx install --editable .`, confirmed on `PATH`. Merged into `~/.claude/settings.json` (global scope). Fine-tuned to 7 hook events (`SessionStart`, `UserPromptSubmit`, `PreToolUse`, `Notification`, `PermissionRequest`, `PreCompact`, `Stop`) plus `SessionEnd` (added 2026-07-08, `Stop` alone doesn't fire on interrupts) after real-session testing exposed gaps and an `async`-induced ordering race — see `../../hooks/README.md`.

### Phase 4 — Reliability Pass

*Est. ~1 week · 5–6 hrs effort*

- ~~Firmware watchdog~~ — done ahead of schedule in Phase 1; timeout tuned from 15s to 30 min (2026-07-07).
- ~~Host-side auto-reconnect~~ — **N/A.** The architecture built is a fresh one-shot `andon-light` CLI process per hook event, not a persistent daemon — there's no connection to go stale, so a replug is inherently handled by the next hook's normal invocation.
- **Done (2026-07-07):** hardened `host/andon_light/` error handling — clean one-line messages + exit code 1 on a busy/missing port instead of a raw traceback; `serial_link.py` retries opening the port up to 3x on a "busy" error.
- **Still outstanding:** a live two-process race against the kernel `TIOCEXCL` lock hasn't been independently reproduced (trusted by code inspection, not a clean repro). Unplug/replug mid-session and a real long-running-turn stress test still need the user physically present.

### Phase 5 — Custom PCB (LED Strip)

**Status: Done (2026-07-30).** This is the project's one and only ongoing hardware line — there is no other Phase 5 to reconcile against.

*Est. 1–2 weeks (design + fab/ship) · 10–15 hrs effort*

- Breadboard-validated the strip circuit first (10-LED WS2812 PCBA, `S`/`V`/`G` wiring, `Adafruit_NeoPixel`, addressable per-state pixel sections — see §2 above) before committing to a PCB layout.
- Schematic and PCB **hand-drawn in KiCad's GUI** — placement, routing, and footprint choices made directly by hand rather than scripted; an earlier scripted `pcbnew` layout attempt was rejected as too large and not matching commercial WS2812-strip form factor, so the board was rebuilt from scratch by hand. RP2040-Zero soldered directly to the board (unused pins soldered for mechanical anchoring only); 10 daisy-chained WS2812B LEDs, one 390Ω 0805 resistor on the data line, one bulk electrolytic cap, and one 100nF decoupling cap per LED.
- ERC/DRC-clean; Gerbers, drill files, BOM, and CPL exported (`hardware/manufacturing/`).
- **Rev A sent to JLC for fabrication** (`hardware/manufacturing/send-to-jlc/`, contract on file) — 5 boards ordered as a small sample run, not an MOQ bulk order, so per-unit cost ran well above what a larger production order would cost (see `BOM.md`).
- **Deliverable:** first real integrated PCBA — RP2040-Zero + resistor + capacitors + 10 LEDs consolidated onto one board.
- **Closed out (2026-07-30):** all 5 boards arrived from JLC, assembled, and reflashed with the current firmware. Every unit individually confirmed working end-to-end: `G`/`Y`/`R`/`C` all correct on the fabricated PCB's own traces/pads (not just the earlier breadboard version), and the watchdog `StalePulse` breathing-red fallback was triggered and confirmed on real hardware for the first time (previously validated by code inspection only).

### Phase 6 — Enclosure

*Est. ~1 week · 4–6 hrs effort*

**Status: Done (2026-07-30).** Chassis base + lid (`device/hardware/models/andon_light_chassis_base.step`, `andon_light_chassis_lid.step`) 3D-printed via JLC alongside the PCB order. Fit was correct first-try on all 5 units — no redesign or reprint needed. Light passes through the 9-segment strip as intended, with no light-leak or diffusion issues reported.

### Phase 7 — Packaging & Distribution

*Est. 3–5 days · 4–5 hrs effort*

**Status: In Progress (2026-07-30).** Scope was refined after the initial write-up below: not every OS needs the same treatment, since the actual audience splits by platform, not just by technical skill.

- **Published `andon-light` to PyPI (2026-07-30, v0.1.0, MIT licensed).** `pipx install andon-light` now works with no repo clone — see `../../host/README.md` and top-level `README.md`. Package is intentionally tiny (~8KB wheel/sdist).
- **`andon-light install-hooks` subcommand shipped** — the single implementation of "merge hooks with explicit permission," used both by manual CLI use and by the Windows installer's finish-page checkbox (see below). Prints the exact `hooks` block, asks for confirmation, lets the user pick global vs. project scope, and warns before overwriting an already-customized hook event. Never edits silently — a "no" is a supported outcome, the CLI stays fully usable via manual `andon-light set ...` calls without it. See `../../hooks/README.md`.
- **Linux: no installer, by design.** Linux users are assumed comfortable with a terminal and willing to read docs — `pipx install andon-light` (or `pipx install --editable .` from source, for development) is the whole story. No AppImage, no `.deb`, no install script — building one would be solving a problem this audience doesn't have.
- **Windows: real one-click installer, built and verified (2026-07-31).** PyInstaller `--onefile` build (`windows/build.ps1`, dependency-analysis-based — not "bundle everything") wrapped in a per-user Inno Setup installer (`windows/andon-light.iss`, no admin/UAC prompt, adds itself to `PATH`, finish-page checkbox runs `install-hooks`). Windows users are assumed non-technical, unlike the Linux audience — hand-holding is the point here. Built and tested on real Windows hardware: device enumerates as a COM port with no extra driver steps, PATH resolves in a new terminal, install-hooks flow and uninstall both confirmed working.
- **macOS: still deferred**, no Apple hardware available to build, sign, or test on.
- **Deliverable (Windows):** someone with zero Python/Arduino/CLI experience downloads one file, runs it, answers one permission prompt, plugs in a pre-flashed device, and it works.

### Phase 8 — Stretch Goals

*Open-ended, backlog*

- Multi-agent/multi-light support, buzzer for alerts, ambient-light brightness sensing, user-configurable color mapping.

---

## 6. Open Questions

- ~~XIAO RP2040 vs. Arduino Pro Micro clone~~ — resolved 2026-07-05: **Waveshare RP2040-Zero**.
- ~~Heartbeat interval / timeout values~~ — resolved 2026-07-07: 30 min.
- ~~Hook-to-color mapping~~ — resolved 2026-07-07 (later extended with `SessionEnd`, 2026-07-08).
- ~~`kDataPin` placement~~ — resolved 2026-07-11: `GPIO1` confirmed correct against the real strip PCBA.
- ~~Data-line signal integrity at 3.3V logic~~ — resolved 2026-07-11: no flicker or wrong colors observed with the series resistor added; a level shifter remains available (unpopulated footprint candidate) if this regresses.
- ~~Section boundaries (1 status + 3 green + 3 yellow + 3 red)~~ — resolved 2026-07-11, confirmed against the physical 10-pixel strip.
- ~~`C` (CompactFlash) chase-fill~~ — resolved 2026-07-11, flashed and confirmed working.
- ~~`StalePulse` animation~~ — resolved 2026-07-30: triggered and confirmed on real fabricated hardware (breathing red on pixels 8-10 after the watchdog timeout), not just validated by code inspection.
- ~~Fabricated PCB electrical verification~~ — resolved 2026-07-30: all 5 Rev A boards back from JLC, assembled, reflashed, and individually confirmed working (`kDataPin`, power, all 10 pixels, all four states plus `StalePulse`).
- ~~Installer tooling choice~~ — resolved: PyInstaller + Inno Setup, built and verified working on real Windows hardware 2026-07-31. macOS code-signing/notarization remains an open question, deferred with the rest of macOS support.
- **Final brightness value** — `130/255` is a reasoned starting point (current draw + eye comfort), confirmed workable behind the actual diffuser now that the enclosure is built (Phase 6), but not formally re-tuned against it.
- **Dim-white status pixel level** — `kDimWhiteLevel = 25` (pre-`kBrightness`-scaling) is a reasoned guess, not explicitly confirmed as the right dimness.
- **Per-unit cost of this fab run** — the 5-board sample order (PCB + assembly + 3D-printed enclosure) was priced well above what a larger MOQ production run would cost; no clean per-unit figure was logged. Worth getting a real quote at a larger quantity before Phase 7 distribution makes per-unit cost a real question.

Next step: cut the `v0.1.0` GitHub release with the Windows installer attached — the last item in Phase 7.
