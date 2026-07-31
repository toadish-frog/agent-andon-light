# Implementation Summary: Agent Andon Light (3-Bulb MVP)

Internal reference for the archived 3-discrete-bulb variant — dev/agent-facing, not tracked on the remote. Frozen history: this variant is retired in favor of the addressable LED strip (see [`../../../device/docs/Implementation-Summary.md`](../../../device/docs/Implementation-Summary.md)), not actively maintained.

---

## 1. Technology Stack

### Hardware

| Part | Choice | Why |
| --- | --- | --- |
| MCU board | Waveshare RP2040-Zero | Native USB, 23.5×18mm castellated pads, USB-C, onboard WS2812 RGB LED for toolchain smoke-testing. Chosen over the Seeed XIAO RP2040 — functionally equivalent, edged out by the onboard LED; only firmware difference is pin naming (`GPIO0`-style, not XIAO's `D0`-style). |
| Status LEDs | Custom PCBA, 3x discrete LED bulbs (Red/Yellow/Green), 4-pin connector (`GND`, `Red`, `Yellow`, `Green`) | Each bulb is a simple on/off GPIO output — no timing-sensitive protocol. Current-limiting resistors live on the PCBA itself. Simpler to drive than an addressable strip, at the cost of losing per-pixel/animatable color — an acceptable trade since the product only ever needs 3 fixed colors. |
| Cable / connector | 4-conductor wire or JST-style connector, plus a data-capable USB-C to USB-A cable to the host | 4 wires (`GND`+3 signal) MCU→PCBA; USB-C carries power+serial to the host. |
| Enclosure | 3D-printed or laser-cut diffuser + base | Never built — this variant was put on hold before reaching enclosure design. |

### Firmware

- **Language:** C++ (Arduino framework).
- **Library:** none — 3 discrete bulbs driven with plain `digitalWrite`/`analogWrite`, no NeoPixel/FastLED dependency.
- **Toolchain:** Arduino IDE (or Arduino CLI) with the `arduino-pico` board package.
- **Interface:** USB CDC serial — enumerates as a plain serial port on every OS.

### Host Driver Software

- **Language:** Python 3 — runs identically on Linux/Windows/macOS with minimal setup.
- **Key library:** `pyserial`.
- **Packaging:** pip-installable package (`andon-light`) exposing a CLI.
- **Integration point:** Claude Code [Hooks](https://docs.claude.com/) — `SessionStart` → idle, `UserPromptSubmit`/`PreToolUse` → working, `Notification`/`PermissionRequest` → waiting, `PreCompact` → compacting, `Stop` → idle. Commands run synchronously, not `async` — see [`../../../hooks/README.md`](../../../hooks/README.md) "Why not async."
- **Known gap:** no hook fires on a user-initiated Esc/interrupt — not exposed by Claude Code's hook system at the time. The light holds its last color through an Esc interrupt.

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
│  andon-light CLI (Python) │  ← host/
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

**Wire protocol:**

| Command | Effect |
| --- | --- |
| `G\n` | Solid green (agent working) |
| `Y\n` | Solid yellow (waiting for human input / permission) |
| `R\n` | Solid red (idle / stopped / quota reached) |
| `C\n` | Flashing green (compacting — internal maintenance, still alive) |
| `H\n` | Heartbeat — no color change, resets watchdog |

`C` (flashing green, `kFlashPeriodMs = 500`) is a sharp on/off blink, visually distinct from `StalePulse`'s slow smooth breathing fade — a user glancing at the light can tell "busy with maintenance" from "may be disconnected" at a glance.

**Reliability:** the firmware runs a watchdog timer — no heartbeat/command within **30 minutes** falls back to a slow-pulse red ("stale/disconnected") rather than silently freezing on a stale color if the host driver crashes. See History for how the timeout was tuned.

---

## 3. Roadmap

| # | Goal | Status |
| --- | --- | --- |
| 0 | Research & order parts | Done |
| 1 | Breadboard MVP (firmware only) | Done |
| 2 | Host CLI MVP | Done |
| 3 | Claude Code hook integration | Done |
| 4 | Reliability pass | Mostly done — live unplug/replug + long-turn stress test never completed |
| 5 | Custom PCB | On hold, then superseded — the strip variant went first and became the sole ongoing hardware line |
| 6 | Enclosure | Not started (blocked on Phase 5) |
| 7 | Packaging & distribution | Not started for this variant — superseded by the strip variant's own Phase 7 |
| 8 | Stretch goals | Backlog, not pursued |

---

## 4. History

| Date | Event |
| --- | --- |
| 2026-07-05 | Kickoff. MCU decision: Waveshare RP2040-Zero over Seeed XIAO RP2040. |
| 2026-07-07 | Breadboard MVP (Phase 1) flashed and confirmed: `G`/`Y`/`R` correct on physical bulbs, watchdog stale-pulse confirmed. Host CLI MVP (Phase 2) done: `andon-light doctor` auto-detected the board (`DEFAULT_VID = 0x2E8A`, confirmed via `udevadm`); `set working/waiting/idle` confirmed end-to-end. Hook integration (Phase 3) done: merged into `~/.claude/settings.json`; hook set expanded to 7 events including `PermissionRequest` and the new `PreCompact`→flashing-green mapping; `async` removed after an ordering-race bug. Reliability pass: hardened error handling (clean messages + exit 1 instead of raw traceback), added retry-on-busy-port logic. Watchdog timeout raised from an initial 15s to 30 minutes after real sessions showed false stale-triggers during long tool-call-free thinking stretches; `PreToolUse` hook added to keep the watchdog fed during tool-heavy stretches. |
| 2026-07-08 | Cross-platform one-click installer + permission-gated hooks merge added to scope (was in the original brief, not previously scheduled). |
| 2026-07-11 | Phase 5 (custom PCB) put on hold — the addressable-strip variant was chosen to go first for a custom PCB, since it reached a fully-validated state before this variant's own Phase 5 was picked up. This variant was later fully superseded: the strip became the project's sole ongoing hardware line, and this MVP was archived. |
