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
| Flashed to real hardware | **Partially confirmed (2026-07-11).** `kDataPin = GPIO1` flashed and verified correct — `G`/`Y`/`R` all confirmed lighting the right 3-pixel section on the physical strip. **Not yet exercised:** `C` (CompactFlash blink) and the watchdog `StalePulse` (breathing red) animations, and the boot-to-`Off` dim-white status pixel wasn't specifically checked. |
| Host CLI / hooks integration | **N/A — no work needed.** Protocol is identical to the already-validated bulb variant, so `../../host/` and `../../hooks/` apply unmodified. Testing so far was via `G`/`Y`/`R` sent directly (Serial Monitor or equivalent) — running the same checks through the actual `andon-light` CLI, and eventually wiring up `../../hooks/`, is still worth doing before relying on this day-to-day. |
| Power/current draw validated on real hardware | **Partially confirmed.** The resistor + capacitor addition (`BOM.md` items #8-9) is wired and running with no flicker, brownout, or reset symptoms observed. Exact current draw hasn't been measured with a multimeter, so `kBrightness = 130/255` is still a reasoned value, not a measured one — fine for continued use, worth revisiting only if symptoms show up later. |

## 5. Open questions

- **~~`kDataPin` placement~~ — resolved (2026-07-11):** `GPIO1` confirmed correct against the real PCBA; `G`/`Y`/`R` all lit the correct section.
- **~~Data-line signal integrity at 3.3V logic~~ — resolved (2026-07-11):** no flicker or wrong colors observed with the resistor added to the data line; a level shifter (`BOM.md` item #7) remains available if this regresses (e.g. after lengthening the wire run), but wasn't needed.
- **~~Section boundaries~~ — resolved (2026-07-11):** the 1 status + 3 green + 3 yellow + 3 red layout confirmed correct against the physical 10-pixel strip via `G`/`Y`/`R` testing.
- **Final brightness value** — `130/255` is a reasoned starting point (current draw + eye comfort), not explicitly evaluated for "is this the right brightness" yet. Adjust after living with it a while, especially if it ends up behind a diffuser (would allow raising it back up for better contrast).
- **Dim-white status pixel level** — `kDimWhiteLevel = 25` (pre-`kBrightness`-scaling) is a reasoned guess at "visibly on but clearly dimmer than an active G/Y/R section." It would have been visible during the `G`/`Y`/`R` testing but hasn't been explicitly confirmed as the right dimness — adjust if it reads as too dim to notice or bright enough to be mistaken for a fourth state color.
- **`C` (CompactFlash) and `StalePulse` animations** — written against the same logic as the validated bulb variant, but not yet triggered and observed on the physical strip. `C` can be tested directly (`andon-light set compacting`); `StalePulse` needs either a real 30-minute idle wait or temporarily lowering `kWatchdogTimeoutMs` per `../firmware/README.md` "Flash & test."
