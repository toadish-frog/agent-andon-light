# Implementation Summary: Agent Andon Light

*Generated from `.prompt/arch/ARCH-prompt.md`. This is the living reference for the project's tech stack, architecture, structure, and roadmap. Update it as decisions change — treat it as project memory, not a one-time snapshot.*

---

## 1. Recommended Technology Stack

### Hardware

| Part | Recommendation | Why |
| --- | --- | --- |
| MCU board | **Waveshare RP2040-Zero** | Native USB (no separate USB-UART chip), thumbnail-sized (23.5×18mm) with castellated pads (easy to hand-solder onto a custom PCB later), USB-C, ~¥30. Fully supported by Arduino IDE via the same `arduino-pico` board package as the XIAO — one-time setup, then standard Arduino workflow. Bonus: has its own onboard WS2812 RGB LED (GPIO16), so firmware/toolchain can be smoke-tested before wiring anything external. Switched from the originally-proposed Seeed XIAO RP2040 on 2026-07-05 — functionally equivalent, this one's onboard LED edged it out; only firmware-level difference is pin naming (`GPIO0`-style, not XIAO's `D0`-style aliases). |
| Status LEDs | **Custom PCBA, 3x discrete LED bulbs** (Red/Yellow/Green), wired to the MCU via a 4-pin connector (`GND`, `Red`, `Yellow`, `Green`) | Swapped from an addressable WS2812B strip on 2026-07-07 — user already has this custom PCBA in hand. Each bulb is its own simple on/off GPIO output instead of a single-wire addressable protocol; current-limiting resistors for each bulb live on the PCBA itself, not as separate breadboard parts. Simpler to drive (`digitalWrite`, no timing-sensitive protocol) at the cost of losing full-RGB/animatable color — fine here since the product only ever needs 3 fixed colors. |
| Cable / connector | 4-conductor wire or JST-style connector matching the PCBA's header, plus USB-C to USB-A cable (data-capable) to the host | 4 wires (`GND`+3 signal) from MCU GPIOs to the PCBA; USB-C carries power+serial to the host computer. |
| Enclosure (Phase 2) | 3D-printed or laser-cut diffuser + base | Cheap to iterate on locally or via a print-on-demand service. |

No part on this list is export-restricted or unusual — it's a commodity microcontroller and commodity LEDs, the same components used in countless hobbyist keyboards and lamps.

### Firmware

- **Language:** C++ (Arduino framework) — matches your instinct toward C, and it's the path with the most tutorials, the most stability, and the least setup for RP2040.
- **Library:** none needed for the LEDs — 3 discrete bulbs are driven with plain `digitalWrite`/`analogWrite`, no NeoPixel/FastLED dependency (that was only needed for the addressable WS2812B approach, now dropped).
- **Toolchain:** Arduino IDE (or Arduino CLI once you're comfortable) with the `arduino-pico` board package.
- **Interface:** USB CDC serial — the board enumerates as a plain serial port on every OS, no custom driver needed on Linux/macOS; Windows may auto-install a CDC driver or need the one-time `arduino-pico` INF.

### Host Driver Software

- **Language: Python 3.** This is a deliberate deviation from "maybe C" for the *host* side only (firmware stays C++): the host needs to run identically on Linux/Windows/macOS with minimal setup, and `pyserial` + a `pipx install andon-light` is dramatically less friction than distributing compiled C binaries for three OSes. C remains the right call for firmware, where Arduino's C++ toolchain is the standard anyway.
- **Key library:** `pyserial` for the serial link.
- **Packaging:** a small pip-installable package (`andon-light`) exposing a CLI.
- **Integration point:** Claude Code [Hooks](https://docs.claude.com/) — `SessionStart` → `andon-light set idle` (default state), `UserPromptSubmit`/`PreToolUse` → `andon-light set working`, `Notification`/`PermissionRequest` → `andon-light set waiting`, `PostCompact` → `andon-light set compacting` (flashing green), `Stop` → `andon-light set idle`. This is what makes the light "driven directly by the agent" per your design vision, with zero manual polling. Commands run synchronously (not `async`) — each call is only ~40-50ms, and `async` was found to cause an ordering race (a delayed early-turn command could overwrite a later, correct one — see `hooks/README.md` "Why not async"). Fine-tuned 2026-07-07 after real-session testing — see `hooks/README.md` for the reasoning behind each mapping.
- **Known gap:** no hook fires on a user-initiated Esc/interrupt — confirmed against the official docs, this event isn't currently exposed by Claude Code's hook system (`Stop` only fires when Claude finishes a turn naturally, not on cancellation). The light will hold its last color through an Esc interrupt rather than reflecting it. Not fixable at the hooks-config layer; would need a different integration approach if this becomes a priority.
- **Planned: one-click cross-platform installer (added 2026-07-08).** This was in the original RFP from the start (`.prompt/arch/ARCH-prompt.md` §2: *"As a everyday product user, I want to plug this andon light device to the computer with minimal setup, so that I can quickly use this product without having to spend too much time configuring the environment"*; §3 target platforms: Linux → Windows → macOS, all three checked as required Desktop App targets) but hadn't been scoped until now, after personally hitting the friction firsthand (missing `python3-venv`/`pip`/`pipx`, PEP 668's externally-managed-environment block, `libfuse2` for the Arduino IDE AppImage). Recommended approach: package `andon-light` itself as a **standalone binary per OS via PyInstaller** (bundles the Python interpreter + `pyserial`, so an end user needs zero pre-existing Python/pip/pipx — sidesteps every install-friction issue hit today), wrapped in a minimal first-run installer that (1) places the binary on `PATH`, and (2) interactively offers to merge the Claude Code hooks — see Phase 7 below for the full breakdown, including the explicit-permission requirement for touching `~/.claude/settings.json`.

---

## 2. Proposed Architecture

```txt
┌─────────────────────────┐
│  Claude Code / CLI agent│
│  (hooks fire on events) │
└───────────┬─────────────┘
            │ shell exec
            ▼
┌───────────────────────────┐
│  andon-light CLI (Python) │  ← host/
│  - device discovery       │
│  - serial protocol client │
│  - heartbeat daemon       │
└───────────┬───────────────┘
            │ USB CDC serial (simple text protocol)
            ▼
┌───────────────────────────┐
│  Firmware (C++/Arduino)   │  ← firmware/
│  - parses commands        │
│  - drives 3 discrete LEDs │
│  - watchdog / auto-idle   │
└───────────┬───────────────┘
            │ 3 GPIO pins (+ shared GND)
            ▼
┌───────────────────────────┐
│  Custom PCBA, 3x LED bulbs│
│  Green / Yellow / Red     │
└───────────────────────────┘
```

**Layering rationale:** three clean, independently testable layers — firmware (device logic), host CLI (transport + OS integration), and the hook glue (policy: *which* agent event maps to *which* color). Each layer can be developed and tested standalone before wiring the next one on, which matters a lot for someone learning hardware for the first time: you get a working LED blink before you touch serial, and a working serial round-trip before you touch Claude Code hooks.

**Wire protocol (v2, deliberately simple):**

```txt
G\n   → solid green    (agent working)
Y\n   → solid yellow   (waiting for human input / permission)
R\n   → solid red      (idle / stopped / quota reached)
C\n   → flashing green (compacting — internal maintenance, still "alive")
H\n   → heartbeat (no color change, resets watchdog)
```

`C` (flashing green) was added 2026-07-07 to distinguish "still working, just doing internal context compaction" (`PostCompact` hook) from ordinary solid-green "working," per the fine-grained hook mapping in §1 Integration point below. Visually distinct on purpose: `C` is a sharp on/off blink (500ms period), `StalePulse` (the watchdog fallback, not part of the normal protocol — see §2 Reliability design point) is a slow smooth breathing fade — so a user glancing at the light can tell "busy with maintenance" from "may be disconnected" at a glance.

**Reliability design point:** the whole premise of this device is that the user *walks away and trusts it*. So the firmware runs a watchdog timer — if no heartbeat or command arrives within **30 minutes** of the last one, it falls back to a distinct slow-pulse red ("stale/disconnected"), rather than silently freezing on a stale "green" if the host driver crashes. This single detail is the difference between a toy and something you can actually trust unattended.

Originally set to ~15s, then raised to 30 minutes (2026-07-07) after real Claude Code sessions showed it false-triggering: hooks only fire at a few discrete moments (prompt submitted, tool used, notification, stop), and any gap longer than 15s between them — most commonly a long stretch of the model just thinking with no tool calls — incorrectly looked like a dead connection. A `PreToolUse` hook was also added so any tool-heavy stretch keeps kicking the watchdog continuously; the 30-minute timeout is the remaining safety net for the rarer case of a turn that's pure thinking with zero tool calls.

---

## 3. Proposed Project Directory Structure

```txt
agent-andon-light/
├── .prompt/                    # planning docs (this RFP workflow) — existing
│   ├── arch/                   # architecture prompts + this summary
│   ├── docs/                   # BOM, build guide, glossary (see below)
│   ├── feat/                   # future feature prompts, one per roadmap phase
│   └── fix/                    # bugfix prompts
│
├── firmware/                    # Arduino IDE sketch for the Waveshare RP2040-Zero (per Phase 0 setup)
│   ├── README.md                # wiring, flashing, and Serial Monitor test steps
│   └── andon_light_firmware/
│       ├── andon_light_firmware.ino  # setup/loop, serial command parsing
│       ├── led_controller.h/.cpp     # 3-pin discrete LED driver, color states, stale-pulse animation
│       └── watchdog.h                # heartbeat timeout → stale-state fallback (header-only)
│
├── host/                       # Python driver package
│   ├── README.md                # install + usage
│   ├── pyproject.toml
│   └── andon_light/
│       ├── __init__.py
│       ├── cli.py              # `andon-light set|heartbeat|doctor`
│       ├── serial_link.py       # open/write logic
│       └── device_discovery.py # find the board by VID, or ANDON_LIGHT_PORT/--port override
│
├── hardware/                   # Phase 2: custom PCB (not started)
│   ├── kicad/                  # schematic + layout project
│   └── enclosure/              # 3D-printable diffuser/base STL/STEP files
│
├── hooks/                      # Claude Code integration
│   ├── README.md                # how/when to merge this, and why commands end in `|| true` for now
│   └── settings.snippet.json   # example hooks config to merge into settings.json
│
└── README.md                   # top-level orientation + quick start for users who already have the hardware
```

`firmware/`, `host/`, and `hooks/` now exist as working scaffolds (written ahead of parts arriving, since none of this needed hardware to write or unit-test — see the Phase 0/1/2/3 notes below for what's verified vs. still an assumption). `hardware/` (Phase 5, custom PCB) is still just a placeholder for later.

---

## 4. Project Style & Delivery Timeline

### Methodology: Phase-Gated Kanban

Not Scrum, not pure waterfall — a hybrid that fits a solo builder mixing hardware and software:

- **Phase-gated** because hardware forces real sequential dependencies a sprint board can't paper over — you can't do Phase 5 (custom PCB) before Phase 1–4 prove the firmware/host/hook logic actually works, and you can't do anything in a phase until the parts for it have physically arrived. That's a waterfall trait, and pretending otherwise just creates rework.
- **Kanban, not fixed sprints,** within and across phases — because the two things that block you (a parts shipment, a PCB fab run) don't respect a 2-week sprint boundary. A single-piece-flow board (`Backlog → In Progress → Blocked (shipping/fab) → Done`) reflects reality better than committing to sprint goals you can't control the input to.
- **Agile-style short feedback loops *within* each phase** — each phase is still scoped to end in something you can see or hold (a blinking LED, a working CLI call, a live Claude Code demo), rather than batching all design work before any hands-on testing.

Track progress with the table in §4.2 below — update the Status column as you go. Treat it as a living tracker, not a commitment device.

### Timeline Assumptions

- Solo, part-time hobbyist pace (~5–8 hours/week) — you said "learn as I build," so estimates include a first-timer's learning curve on Arduino and (later) KiCad, not an experienced maker's pace.
- Parts shipping: ~1–5 days (varies by supplier).
- PCB fab + shipping: ~1 week for a standard (non-expedited) small-batch order — noticeably faster than the original international-shipping estimate this replaced.
- **Kickoff: 2026-07-05** (today).

### 4.1 Roadmap Tracking Table

| Phase | Goal | Est. Duration (elapsed) | Est. Effort | Status |
| --- | --- | --- | --- | --- |
| 0 | Research & Order Parts | 3–7 days (shipping is fast) | 3–5 hrs | **Done** — RP2040-Zero + custom LED PCBA in hand, soldered and wired |
| 1 | Breadboard MVP (firmware only) | ~1 week | 5–8 hrs | **Done** — flashed to real hardware 2026-07-07; `G`/`Y`/`R` confirmed correct on the physical bulbs, watchdog stale-pulse confirmed (drops to breathing red after ~15–18s with no heartbeat) |
| 2 | Host CLI MVP | 3–5 days | 4–6 hrs | **Done** — installed in a venv, `andon-light doctor` auto-detected the board (VID `0x2E8A` guess confirmed correct via `udevadm`), `andon-light set working/waiting/idle` confirmed end-to-end against real hardware |
| 3 | Claude Code Hook Integration | 2–3 days | 3–4 hrs | **Done** — merged into `~/.claude/settings.json` (global), `andon-light` on `PATH` via `pipx`. Fine-tuned twice from real-session feedback: expanded to 7 hook events (`SessionStart`, `UserPromptSubmit`, `PreToolUse`, `Notification`, `PermissionRequest`, `PostCompact`, `Stop`), added a 4th LED state (flashing green for compaction), and fixed an `async`-induced ordering race (see §5 Phase 3 and `hooks/README.md`) |
| 4 | Reliability Pass | ~1 week | 5–6 hrs | **Mostly done (2026-07-07)** — watchdog tuned from real usage, CLI error handling hardened (clean messages + busy-retry, no more raw tracebacks), auto-reconnect found to be N/A given the one-shot-CLI architecture actually built. Remaining: live unplug/replug + long-turn stress test, needs the user present |
| 5 | Custom PCB | 1–2 weeks (design + fab/ship) | 10–15 hrs | **On hold (2026-07-11)** — deprioritized in favor of the **led-strip** variant's Phase 5, chosen to go first (see `../../../device/docs/Implementation-Summary.md` §6). This variant itself is fully functional and validated (Phases 0-4 all Done) — it's just not the one getting a custom PCB right now. Plan below remains valid if bulb is revisited later. |
| 6 | Enclosure | ~1 week | 4–6 hrs | Not Started |
| 7 | Packaging & Distribution | 3–5 days | 4–5 hrs | Not Started — scope expanded 2026-07-08 to explicitly include a one-click cross-platform installer + permission-gated hooks merge (was in the original RFP, just not scoped until now) |
| 8 | Stretch Goals | Open-ended | — | Backlog |

**Projected delivery** (elapsed calendar time, phases can overlap slightly where shipping waits allow parallel work):

- **Working breadboard MVP**, hooked into a live Claude Code session (Phases 0–4): ~4 weeks from kickoff → around **2026-08-02**.
- **Finished v1** with custom PCB + enclosure (Phases 0–6): ~6–7 weeks from kickoff → around **2026-08-23**.

Total hands-on effort through Phase 6 is roughly **35–50 hours** — fast parts and PCB fab turnaround cuts several weeks off the original international-shipping estimate, so elapsed time now tracks closer to actual effort than to logistics waits. These dates will still drift; re-baseline them once Phase 0 parts actually land, since that's the first real signal on your actual pace.

---

## 5. Development Roadmap — Detailed Phase Breakdown

### Phase 0 — Research & Order Parts

*Est. 3–7 days elapsed (shipping) · 3–5 hrs effort*

- Install Arduino IDE 2.x; add the `arduino-pico` board-manager URL; install the RP2040 board package (no LED library needed — 3 discrete bulbs are driven with plain `digitalWrite`/`analogWrite`).
- Order the Phase 1 BOM (`BOM.md`).
- **Deliverable:** parts in transit, dev environment ready to go the moment they arrive.
- **Done ahead of schedule while parts ship:** the Phase 1 firmware sketch, Phase 2 host CLI, and Phase 3 hooks config were all written now, since none of them needed hardware to write — see `firmware/`, `host/`, `hooks/`. Still outstanding for Phase 0 itself: installing Arduino IDE and actually placing the parts order.

### Phase 1 — Breadboard MVP (firmware only)

*Est. ~1 week · 5–8 hrs effort*

- Wire the Waveshare RP2040-Zero to the custom PCBA's 4-pin connector (`GND`, `Red`, `Yellow`, `Green`) per `USER-GUIDE.md` — 3 GPIO outputs + shared ground, no breadboard strictly required.
- Flash a test sketch that cycles red → yellow → green.
- Extend it to parse single-character serial commands (`G`/`Y`/`R`) from the Arduino Serial Monitor.
- **Deliverable:** a light that changes color on typed commands — first tangible proof the hardware works.
- **Blocked by:** Phase 0 parts arriving.
- **Status: Done (2026-07-07).** Flashed to the real Waveshare RP2040-Zero via Arduino IDE (AppImage, `--appimage-extract-and-run` since the sandboxed launch environment couldn't mount FUSE directly). First upload required manually forcing BOOTSEL mode (hold BOOT while replugging USB) since the auto-reset trick only works once an `arduino-pico` sketch has run at least once. Serial Monitor confirmed `G`/`Y`/`R` drive the correct bulbs and the watchdog correctly falls back to a slow breathing red after ~15–18s of no heartbeat. The `GPIO1`/`GPIO2`/`GPIO3` pin assignments are now **confirmed correct** against the actual wiring, not just placeholders.

### Phase 2 — Host CLI MVP

*Est. 3–5 days · 4–6 hrs effort*

- Scaffold the `andon-light` Python package (`pyproject.toml`, `andon_light/`).
- Implement `serial_link.py` (open/write over `pyserial`) and a minimal `cli.py` with `andon-light set <color>`.
- **Deliverable:** `andon-light set green` typed in a terminal changes the physical LED — end-to-end terminal → USB → LED.
- **Blocked by:** Phase 1 firmware command parser working.
- **Status: Done (2026-07-07).** Installed into a venv (`python3 -m venv .venv && pip install -e .`) after installing `python3-venv`/`python3-pip`. `andon-light doctor` auto-detected the board on the first try — `DEFAULT_VID = 0x2E8A` was confirmed correct via `udevadm info` against the real Waveshare RP2040-Zero, no fix needed. `andon-light set working/waiting/idle` all confirmed to correctly change the physical LED. One environment gotcha hit along the way: the serial port returned "Device or resource busy" until Arduino IDE's own Serial Monitor was disconnected — only one process can hold a serial port at a time.

### Phase 3 — Claude Code Hook Integration

*Est. 2–3 days · 3–4 hrs effort*

- Write `hooks/settings.snippet.json` mapping `UserPromptSubmit`/`PreToolUse` → working, `Notification` → waiting, `Stop` → idle.
- Merge into a real `settings.json` and run a live Claude Code session against the device.
- **Deliverable:** the actual product, working on a breadboard — the agent drives the light with zero manual intervention.
- **Blocked by:** Phase 2 CLI working standalone.
- **Status: Done (2026-07-07).** `andon-light` installed globally via `pipx install --editable .` (confirmed on `PATH`). The `hooks` object from `hooks/settings.snippet.json` merged into `~/.claude/settings.json` (global scope, user's choice — applies to every Claude Code session on this machine, not just this repo). All 3 hook commands (`andon-light set working/waiting/idle`) smoke-tested manually and confirmed working against the real hardware. `|| true` kept intentionally for now (see `hooks/README.md`) until Phase 4's reliability pass makes a genuinely broken connection worth surfacing loudly. Takes effect on Claude Code restart / new sessions — not the session it was configured from.

### Phase 4 — Reliability Pass

*Est. ~1 week · 5–6 hrs effort*

- ~~Add the firmware watchdog (stale-state fallback if no heartbeat)~~ — done ahead of schedule in Phase 1; timeout tuned from 15s to 30 min on 2026-07-07 after real-world hook testing (see §2 Reliability design point).
- ~~Add host-side auto-reconnect on USB replug~~ — **N/A given the architecture actually built.** This bullet assumed a persistent background daemon (note "kill the daemon" below, from the original design). What got built instead is a fresh one-shot `andon-light` CLI process per hook event — each call does its own device discovery, opens the port, sends, and closes. There's no persistent connection to go stale, so a replug is inherently handled by the next hook's normal invocation. Device auto-detection by VID was already done and confirmed in Phase 2.
- **Done (2026-07-07):** hardened `host/andon_light/` error handling — `cli.py` previously let a busy/missing port raise an unhandled Python traceback; now catches `serial.SerialException` and prints a clean one-line message with exit code 1 (still absorbed by hooks' `|| true`, but no longer noisy for standalone CLI use). `serial_link.py` now retries opening the port up to 3x (150ms apart) specifically on a "busy" error, to ride out the case where two hook-triggered calls land close together. Verified: clean error message on a nonexistent port (no traceback), normal calls still ~40-50ms (retry logic doesn't slow the common case). **Not independently verified:** a live two-process race against a kernel-level `TIOCEXCL` lock (the actual mechanism behind the earlier Arduino-IDE-Serial-Monitor conflict) — pyserial's own `exclusive=True` uses advisory `flock` instead, which doesn't reproduce that lock type, so this is trusted by code inspection rather than a clean repro.
- **Still needs a live session to validate** (can't be done without the user physically present): unplug/replug mid-session, and a real long-running turn stress test — the 30-min watchdog and `PreToolUse` kicks are reasoned to cover this (see §2), but haven't been observed end-to-end yet.
- **Deliverable:** something you can trust to run unattended — the actual bar for "walk away."
- **Blocked by:** Phase 3 end-to-end flow working.

### Phase 5 — Custom PCB

**Status: On hold (2026-07-11)** — see §4.1. The **led-strip** variant was chosen to go first for a custom PCB, since it reached a fully-validated state (firmware, host CLI, hooks, power all confirmed on real hardware) before this variant's own Phase 5 was picked up. This plan remains valid and ready to resume if the bulb variant is revisited later.

*Est. 1–2 weeks (design + fab/ship) · 10–15 hrs effort*

- Learn just enough KiCad to place the RP2040-Zero and route it to the LED PCBA's connector (or integrate the 3 discrete LEDs + resistors directly onto one board, if consolidating).
- Route a 2-layer board; run DRC; export Gerbers.
- Send CAD to a PCB fab service; order 5–10 boards (see `BOM.md` for the parts list).
- Hand-solder (or use the fab's assembly service, if you want them to place and solder the SMD parts for you).
- **Deliverable:** first real PCBA.
- **Blocked by:** Phase 4 firmware/protocol being stable — don't lock in a PCB layout around a protocol that's still changing.

### Phase 6 — Enclosure

*Est. ~1 week · 4–6 hrs effort*

- Design a simple diffuser + base (3D-printable or laser-cut).
- Prototype locally if you have access to a printer, or ride along with the PCB order's add-on services, if the fab offers them.
- **Deliverable:** looks like a product, not a breadboard.
- **Blocked by:** Phase 5 PCB dimensions being final (the enclosure has to fit the actual board).

### Phase 7 — Packaging & Distribution

*Est. 3–5 days · 4–5 hrs effort — scope expanded 2026-07-08, estimate likely needs revisiting once installer tooling is chosen*

- Publish the `andon-light` pip package (still useful for dev/editable installs, per `host/README.md`'s `--editable` vs plain distinction).
- Write install docs; test on Windows and macOS (CDC driver quirks are the most likely surprise here).
- **One-click installer, one per OS (Linux/macOS/Windows) — required by the original RFP, not a stretch goal.** Package `andon-light` as a standalone executable via **PyInstaller** (no separate Python/pip/pipx needed by the end user — directly solves the exact friction hit today: missing `python3-venv`, PEP 668 blocking a plain `pip install`, needing `pipx` installed first). Rough shape:
  - **Linux:** AppImage or a simple tarball + install script that drops the binary in `~/.local/bin`.
  - **Windows:** an installer built with something like Inno Setup wrapping the PyInstaller `.exe`, adding it to `PATH`.
  - **macOS:** a `.pkg` or drag-to-Applications `.app` — flag now, honestly, that **unsigned macOS binaries get blocked by Gatekeeper by default**, so "one-click" on macOS may actually mean "one right-click → Open" unless code-signing/notarization gets set up (a paid Apple Developer account), which is a real scope decision to make explicitly rather than discover late.
- **Hooks merge, bundled into the same installer, with explicit permission — required, not optional.** The installer must never silently edit `~/.claude/settings.json` (or a project's `.claude/settings.json`) — it's a shared config file affecting every Claude Code session, same principle already applied by hand this whole project (see `hooks/README.md`). On first run, the installer should: show the user exactly what `hooks` block it wants to add, ask for explicit confirmation (a real terminal/dialog prompt — "Add Claude Code hooks to ~/.claude/settings.json? [y/N]"), let them pick global vs. project scope (same choice made manually in Phase 3), and only write after an explicit yes. Treat a "no" as a supported outcome, not an error — the CLI should still be fully usable via manual `andon-light set ...` calls without the hooks.
- **Deliverable:** someone else — with zero Python/Arduino/CLI experience — downloads one file, runs it, answers one permission prompt, plugs in a pre-flashed device, and it works. This is the actual bar implied by the original RFP's "minimal setup" user story, not just "there's a pip package now."

### Phase 8 — Stretch Goals

*Open-ended, backlog — not on the critical path to v1*

- Multi-agent/multi-light support, buzzer for alerts, ambient-light brightness sensing, user-configurable color mapping.

---

## 6. Open Questions for You

- ~~XIAO RP2040 vs. Arduino Pro Micro clone~~ — resolved 2026-07-05: switched to the **Waveshare RP2040-Zero** (see §1 MCU board row for why). The Pro Micro (ATmega32U4) remains a valid fallback if RP2040 boards ever become hard to source, but isn't the current plan.
- ~~Heartbeat interval / timeout values~~ — resolved 2026-07-07: tuned from 15s to 30 min after real Claude Code session testing showed false stale-pulse trips (see §2 Reliability design point).
- ~~Hook-to-color mapping~~ — resolved 2026-07-07: expanded past the original 3-color proposal to 7 hook events / 4 LED states (added `PermissionRequest`, `PostCompact`→flashing-green, `SessionStart`→idle-default) — see `hooks/README.md`.
- **Installer tooling choice (added 2026-07-08)** — PyInstaller is recommended in §1/Phase 7 above, but not yet built or tested on any platform. Worth deciding early whether macOS code-signing/notarization (a paid Apple Developer account) is in scope, since it changes both the cost and the "how one-click is 'one-click,' really" answer for that platform specifically.

Next step: turn Phase 1 into a `.prompt/feat/` prompt when you're ready to start building.
