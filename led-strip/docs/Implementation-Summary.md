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
| 2-4 | Green section | `G` state → solid green; `C` (CompactFlash) → blinking green |
| 5-7 | Yellow section | `Y` state → solid yellow |
| 8-10 | Red section | `R` state → solid red; watchdog stale → breathing red (`StalePulse`) |

Only the active section's pixels are lit at any given time; every other section is off. The status pixel (1) is the exception — it stays dim white through every state, including `Off`, as a constant "board is powered and firmware is running" indicator independent of the G/Y/R state color. The animation math itself (breathing cosine curve for `StalePulse`, square-wave blink for `CompactFlash`) is unchanged from the original all-pixels version — it's now just scoped to a 3-pixel section (`renderSection()` in `led_controller.cpp`) instead of the whole strip.

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
| Flashed to real hardware | **Not started.** `kDataPin = GPIO1` is a placeholder, unconfirmed against the actual strip PCBA's wiring — same status the bulb variant's pins were in before their first real flash. Needs Arduino IDE + Adafruit_NeoPixel library install, then a flash-and-observe pass per `../firmware/README.md` "Flash & test." |
| Host CLI / hooks integration | **N/A — no work needed.** Protocol is identical to the already-validated bulb variant, so `../../host/` and `../../hooks/` apply unmodified. |
| Power/current draw validated on real hardware | **Not started.** Brightness cap (`kBrightness = 130/255`) and the 5V/VBUS wiring guidance are reasoned from WS2812 datasheet current specs, not yet measured on the physical PCBA — validate before leaving the strip running unattended for long periods, consistent with this project's standing rule of confirming hardware/timing assumptions against real behavior rather than reasoning alone. |

## 5. Open questions

- **`kDataPin` placement** — `GPIO1` is a guess by analogy to the bulb variant's `kGreenPin`; confirm against the strip PCBA's actual `S` pad silkscreen before wiring.
- **Data-line signal integrity at 3.3V logic** — most WS2812 clones tolerate 3.3V data at short wire runs, but this is unverified for this specific PCBA. If flicker/wrong colors show up during first flash-and-test, add a 74HCT125 level shifter (see `BOM.md` item #7) rather than assuming the firmware logic is wrong.
- **Final brightness value** — `130/255` is a reasoned starting point (current draw + eye comfort), not measured. Adjust after seeing the physical strip lit, especially if it ends up behind a diffuser (would allow raising it back up for better contrast).
- **Dim-white status pixel level** — `kDimWhiteLevel = 25` (pre-`kBrightness`-scaling) is a reasoned guess at "visibly on but clearly dimmer than an active G/Y/R section," not measured against the physical strip. Adjust after first flash-and-observe if it reads as too dim to notice or bright enough to be mistaken for a fourth state color.
- **Section boundaries assume exactly 10 pixels.** `kGreenStart`/`kYellowStart`/`kRedStart` in `led_controller.cpp` are hardcoded to the 1 status + 3 + 3 + 3 = 10 layout in the acceptance criteria; if the physical strip PCBA turns out to have a different pixel count, these constants (not just `kNumPixels` in the `.ino`) need updating together.
