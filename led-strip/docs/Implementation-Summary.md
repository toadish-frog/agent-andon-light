# Implementation Summary: Agent Andon Light — LED Strip variant

Companion to `../../led-bulb/docs/Implementation-Summary.md`. This doc covers only what's specific to the **addressable LED strip variant** — architecture, protocol, and roadmap status that differ from the bulb variant. Shared decisions (MCU choice, host language, hook mapping, wire protocol shape) are inherited unchanged from the bulb variant's doc; see that file for the full reasoning.

---

## 1. What's different from the bulb variant

| Part | Bulb variant | Strip variant |
| --- | --- | --- |
| LED board | Custom PCBA, 3 discrete bulbs (Red/Yellow/Green), 4-pin connector (`GND`+3 signal) | Custom PCBA, WS2812-style addressable strip, 10 LEDs, 3-pin connector (`S`/`V`/`G`) |
| Firmware LED driver | Plain `digitalWrite`/`analogWrite`, no library | **Adafruit_NeoPixel** library — required, WS2812 timing can't be bit-banged reliably with plain GPIO calls. Single new dependency, scoped to `led-strip/firmware/` only. |
| MCU pins used | 3 GPIO (one per bulb) + shared GND | 1 GPIO (data/signal) + 5V + GND |
| Power source | 3.3V or 5V, current draw is trivial (discrete on/off LEDs) | Must be 5V/`VBUS`, not 3V3 — 10 addressable LEDs draw meaningfully more current. Firmware caps brightness (`kBrightness = 130/255`) to keep draw and eye comfort reasonable. |
| Pixel addressing | Each state drives its own dedicated GPIO — inherently "one lamp per state" | Each state drives its own dedicated 3-pixel *section* of the strip (pixels 2-4/5-7/8-10 for G/Y/R), plus an always-on dim-white status pixel (1) — see "Addressable pixel layout" below. |

Everything else — MCU (Waveshare RP2040-Zero), host language (Python/`pyserial`), wire protocol shape (`G`/`Y`/`R`/`C`/`H` single-character commands), watchdog timeout (30 min), and Claude Code hook mapping — is **identical** to the bulb variant and does not need to be re-decided or re-implemented. The host CLI and hooks config work against either firmware unmodified, since both speak the same protocol.

## 2. Architecture

```txt
┌─────────────────────────┐
│  Claude Code / CLI agent│
│  (hooks fire on events) │
└───────────┬─────────────┘
            │ shell exec
            ▼
┌───────────────────────────┐
│  andon-light CLI (Python) │  ← ../../host/ (shared, unmodified)
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
│  10x addressable LEDs,    │
│  all driven to same color │
└───────────────────────────┘
```

### Addressable pixel layout

An early version of this firmware used `strip.fill()` to set all 10 pixels to the same color per state — visually plausible, but not actually andon-light behavior, which communicates state by *which* lamp is lit, not by turning every lamp the same color. Each state now owns a dedicated sub-range of the strip instead:

| Pixels (1-indexed) | Role | Color |
| --- | --- | --- |
| 1 | Status — always on, regardless of state | Dim white |
| 2-4 | Green section | `G` state → solid green |
| 5-7 | Yellow section | `Y` state → solid yellow |
| 8-10 | Red section | `R` state → solid red; watchdog stale → breathing red (`StalePulse`) |
| 2-10 (all 9 non-status pixels) | `C` (`CompactFlash`) | Chase-fill sequence, not confined to one section — see below |

For `G`/`Y`/`R`/`StalePulse`, only the active section's pixels are lit at any given time; every other section is off. The status pixel (1) is the exception — it stays dim white through every state, including `Off`, as a constant "board is powered and firmware is running" indicator independent of the state color.

`StalePulse`'s breathing cosine curve is unchanged from the original all-pixels version — just scoped to the red section (`renderSection()` in `led_controller.cpp`) instead of the whole strip. `CompactFlash` was redesigned (2026-07-11) from a flat square-wave blink of the green section into a chase-fill sequence spanning all 9 non-status pixels: a single lit pixel sweeps down from pixel 10 to pixel 2 and locks on, the next sweep goes down to pixel 3 (pixel 2 stays lit) and locks pixel 3, and so on — pixels accumulate lit from pixel 2 upward, one per pass, until all 9 are lit, then it resets to empty and repeats. This is deliberately a different rendering path from the other four states (it doesn't use `renderSection()`, since it needs to light two disjoint pixel ranges — the locked-on prefix and the single sweeping pixel — at once); see the `kCompactPixelCount`/`kCompactStepMs`/`kCompactTotalSteps` constants in `led_controller.cpp`.

**Boot behavior differs intentionally from the bulb variant.** The bulb variant boots straight to solid red (see `../../led-bulb/firmware/andon_light_firmware/led_controller.cpp`) so a bare power-on/replug isn't indistinguishable from "board not running" during the gap before the first real hook fires. The strip variant boots to `Off` instead — dim-white status pixel only, all three color sections dark — because the status pixel already serves that same "alive" signal on its own, without needing to guess a placeholder state color. Functionally this closes the same gap the bulb variant's boot-to-red closes; it's just encoded as a dedicated indicator pixel instead of borrowing one of the three state colors.

## 3. Directory structure

```txt
led-strip/
├── firmware/
│   ├── README.md                        # wiring, flashing, NeoPixel dependency note, power caveats
│   └── andon_light_firmware_strip/
│       ├── andon_light_firmware_strip.ino
│       ├── led_controller.h/.cpp        # NeoPixel-backed driver, same LightColor enum as bulb variant
│       └── watchdog.h                   # byte-identical copy of the bulb variant's watchdog (hardware-agnostic)
└── docs/
    ├── BOM.md
    ├── Implementation-Summary.md         # this file
    └── USER-GUIDE.md
```

`watchdog.h` is duplicated rather than shared because Arduino sketches must be self-contained folders (the IDE only loads `.ino`-adjacent files as tabs) — it's hardware-agnostic logic, so the two copies are expected to stay identical; if the timeout value or watchdog behavior ever needs to change, update both.

## 4. Roadmap status

| Phase | Status |
| --- | --- |
| Firmware written | **Done** — `led_controller.h/.cpp`, `andon_light_firmware_strip.ino`, `watchdog.h` all written against the same protocol as the validated bulb variant; pixel rendering refined to addressable per-state sections (see "Addressable pixel layout" above) rather than all-pixels-one-color. |
| Flashed to real hardware | **Confirmed (2026-07-11).** `kDataPin = GPIO1` flashed and verified correct — `G`/`Y`/`R` confirmed lighting the right 3-pixel section, and the redesigned `C` chase-fill sequence confirmed working on the physical strip. **Not yet exercised:** the watchdog `StalePulse` (breathing red) animation, and the boot-to-`Off` dim-white status pixel wasn't specifically checked. |
| Host CLI / hooks integration | **N/A — no work needed.** Protocol is identical to the already-validated bulb variant, so `../../host/` and `../../hooks/` apply unmodified. Testing so far was via `G`/`Y`/`R` sent directly (Serial Monitor or equivalent) — running the same checks through the actual `andon-light` CLI, and eventually wiring up `../../hooks/`, is still worth doing before relying on this day-to-day. |
| Power/current draw validated on real hardware | **Partially confirmed.** The resistor + capacitor addition (`BOM.md` items #8-9) is wired and running with no flicker, brownout, or reset symptoms observed. Exact current draw hasn't been measured with a multimeter, so `kBrightness = 130/255` is still a reasoned value, not a measured one — fine for continued use, worth revisiting only if symptoms show up later. |
| Custom PCB design (Phase 5) | **Active (chosen 2026-07-11).** This variant was chosen over the bulb variant to go first for a custom PCB, now that firmware/host/hooks/power are all confirmed stable on real hardware. See §6 "Development Roadmap" below. |

## 5. Open questions

- **~~`kDataPin` placement~~ — resolved (2026-07-11):** `GPIO1` confirmed correct against the real PCBA; `G`/`Y`/`R` all lit the correct section.
- **~~Data-line signal integrity at 3.3V logic~~ — resolved (2026-07-11):** no flicker or wrong colors observed with the resistor added to the data line; a level shifter (`BOM.md` item #7) remains available if this regresses (e.g. after lengthening the wire run), but wasn't needed.
- **~~Section boundaries~~ — resolved (2026-07-11):** the 1 status + 3 green + 3 yellow + 3 red layout confirmed correct against the physical 10-pixel strip via `G`/`Y`/`R` testing.
- **Final brightness value** — `130/255` is a reasoned starting point (current draw + eye comfort), not explicitly evaluated for "is this the right brightness" yet. Adjust after living with it a while, especially if it ends up behind a diffuser (would allow raising it back up for better contrast).
- **Dim-white status pixel level** — `kDimWhiteLevel = 25` (pre-`kBrightness`-scaling) is a reasoned guess at "visibly on but clearly dimmer than an active G/Y/R section." It would have been visible during the `G`/`Y`/`R` testing but hasn't been explicitly confirmed as the right dimness — adjust if it reads as too dim to notice or bright enough to be mistaken for a fourth state color.
- **~~`C` (CompactFlash) chase-fill~~ — resolved (2026-07-11):** flashed and confirmed working on the physical strip.
- **`StalePulse` animation** — written against the same logic as the validated bulb variant, but not yet triggered and observed on the physical strip. Needs either a real 30-minute idle wait or temporarily lowering `kWatchdogTimeoutMs` per `../firmware/README.md` "Flash & test."

## 6. Development Roadmap

This section was missing from earlier drafts of this doc — it was written as a narrow "what's different from the bulb variant" companion (see the intro), so Phases 0-4 were only ever tracked as the ad-hoc §4 status table above, not as a full phase breakdown. Phases 0-4's methodology, Kanban shape, and timeline assumptions are inherited unchanged from `../../led-bulb/docs/Implementation-Summary.md` §4 — this section picks up from Phase 5, the first phase where the two variants genuinely diverge.

**Phase 5 — Custom PCB is the active phase for this variant (decided 2026-07-11).** The bulb variant's own Phase 5 is on hold — see `../../led-bulb/docs/Implementation-Summary.md` §4.1 and §5 — in favor of this one going first, now that firmware, host CLI, hooks, and power are all confirmed stable on real hardware (§4 above).

### Phase 5 — Custom PCB (LED Strip variant)

*Est. 1–2 weeks (design + fab/ship) · 10–15 hrs effort — same estimate class as the bulb variant's Phase 5*

- Learn just enough KiCad to place the RP2040-Zero and route the confirmed-working breadboard circuit (`../firmware/README.md` "Breadboard wiring") as fixed traces/pads instead of jumpers:
  - 1 GPIO data pin → in-series 330–470 Ω resistor (`BOM.md` item #8) → the strip connector's `S` pad.
  - `5V`/`VBUS` and `GND` → the strip connector's `V`/`G` pads.
  - 100–1000 µF capacitor (`BOM.md` item #9) across `V`/`G`, close to the strip connector — mind footprint polarity marking.
  - A 3-pin connector footprint matching the strip PCBA's existing JST pigtail (or a direct-solder pad if consolidating onto one board instead of keeping the strip as a separate PCBA).
- No level shifter footprint needed by default (resolved open question, §5 above) — consider an optional unpopulated footprint for one, in case a longer strip run or a different WS2812 clone batch needs it later.
- Route a 2-layer board; run DRC; export Gerbers.
- Send CAD to a PCB fab service; order 5–10 boards (see `BOM.md` for the parts list).
- Hand-solder (or use the fab's assembly service, if available).
- **Deliverable:** first real strip-variant PCBA — RP2040-Zero + resistor + capacitor consolidated onto one board, replacing the current breadboard setup.
- **Blocked by:** ~~Phase 4 firmware/protocol being stable~~ — resolved 2026-07-11; `G`/`Y`/`R`/`C` all confirmed on real hardware, `StalePulse` reasoned-but-unconfirmed is not considered blocking.
- **Open design questions carried into this phase:** exact connector footprint/orientation to match the strip PCBA's pigtail, and whether to keep the resistor/capacitor as through-hole parts (matching the breadboard prototype) or move to SMD for a more finished board.

### Phase 6 — Enclosure

Not started — blocked by Phase 5 PCB dimensions being final, same reasoning as the bulb variant's Phase 6 (`../../led-bulb/docs/Implementation-Summary.md` §5). A strip-specific consideration for later: the enclosure/diffuser needs to pass light through 9 individually visible segments rather than 3 discrete bulb positions, which may push toward a continuous frosted channel rather than 3 separate bulb-shaped cutouts.

### Phase 7 — Packaging & Distribution / Phase 8 — Stretch Goals

Not variant-specific — see `../../led-bulb/docs/Implementation-Summary.md` §5 Phase 7-8 for the existing plan (one-click installer, permission-gated hooks merge, stretch goals). That plan only touches `host/`/`hooks/`, not firmware, so it applies unchanged to either variant once either one reaches this point.
