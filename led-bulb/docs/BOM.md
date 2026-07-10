# Bill of Materials: Agent Andon Light

Two BOMs: **Phase 1 (breadboard MVP)** — buy this first, cheap, to prove the whole concept — and **Phase 2 (custom PCB)**, once the software/firmware works end-to-end.

Every part below is a standard, unrestricted commodity electronic component (microcontroller dev board + addressable LEDs + passives). Nothing here is export-controlled, encryption-related, or radio-emitting beyond the board's native USB.

## Phase 1 — Breadboard MVP

| # | Part | Qty | Approx. Cost | Notes |
| --- | --- | --- | --- | --- |
| 1 | Waveshare RP2040-Zero | 1 | ¥30 | The MCU dev board — see `Implementation-Summary.md` §1 for why this board was chosen |
| 2 | Custom PCBA, 3x LED bulbs (Red/Yellow/Green) | 1 | — (already in hand) | — |
| 3 | Half-size breadboard | 1 | ¥10 | — |
| 4 | Jumper wire set (M-M, M-F) | 1 set | ¥10 | — |
| 5 | 4-pin connector/wire matching the PCBA's header (GND, R, Y, G) | 1 | ¥5 | Match the PCBA's actual header type (JST or plain pin header) |
| 6 | USB-C to USB-A cable (data-capable) | 1 | ¥15 | Confirm it's rated for data transfer, not charge-only — many cheap cables are power-only and won't enumerate as a serial device |

**Phase 1 total: ~¥60 (~$8), plus whatever the PCBA itself cost.** No soldering strictly required beyond the MCU's header pins — everything else plugs together.

> **Note (2026-07-07):** the LED side of Phase 1 changed from a WS2812B addressable strip to a custom PCBA with 3 discrete LED bulbs (Red/Yellow/Green) on a 4-pin connector (`GND`+3 signal) — already in hand, so it's no longer a line item to source. This also drops the WS2812-specific parts (data-line resistor, decoupling cap, level shifter) from both phases below, since discrete on/off LEDs don't need them — any current-limiting resistors live on the PCBA itself.

## Phase 2 — Custom PCB

Adds to / replaces Phase 1 parts once the design is finalized in KiCad.

| # | Part | Qty | Approx. Cost | Notes |
| --- | --- | --- | --- | --- |
| 1 | Waveshare RP2040-Zero | 1 | ¥30 | Same module, now hand-soldered onto the custom PCB via its castellated edge pads |
| 2 | LED bulbs (Red/Yellow/Green, 5mm through-hole or SMD to match final footprint) | 3 | ¥3 | Same 3 discrete colors as the Phase 1 PCBA, sourced individually if integrating them onto a new board rather than reusing the existing PCBA |
| 3 | 220–330 Ω resistor x3 (one per LED, through-hole or 0805 SMD to match) | 3 | ¥1 | Current-limiting per bulb — simple Ohm's-law sizing for a plain on/off LED, no protocol timing concerns like WS2812 had |
| 4 | USB-C connector (if not relying on the RP2040-Zero's onboard port) | 1 | ¥2 | Only needed if the enclosure design routes the cable differently than the board's own port |
| 5 | Custom PCB (2-layer), CAD sent to a fab | 5–10 (min order) | ¥15–35 total | Order 5–10 minimum — spares are nearly free at this size |
| 6 | 3D-printed or laser-cut enclosure/diffuser | 1 set | ¥10–35 | Can ride along with the PCB order (many fabs offer this as an add-on) or be sourced separately |

**Phase 2 total: ~¥50–90** including PCB fab minimums and enclosure (spread across however many units you order — 5–10 boards for the price of one is normal for small-batch PCB fab, so keep the spares). If Phase 2 just reuses the existing 3-bulb PCBA from Phase 1 rather than redesigning the LED board, items #2–3 aren't needed at all — only relevant if consolidating everything (MCU + LEDs) onto one new board.

## Notes

- If you want an assembly service to place and solder the SMD parts for you rather than hand-soldering, the parts you list in the BOM need to be in that assembler's own stock — check before finalizing the KiCad BOM. Hand-soldering has no such constraint.
- Buy a spare LED bulb or two of each color if redesigning the LED board in Phase 2 — cheap insurance against a dead LED or a reversed-polarity mistake during hand-soldering.
