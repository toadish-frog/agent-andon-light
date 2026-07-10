# Bill of Materials: Agent Andon Light (LED Strip variant)

Companion to `../../led-bulb/docs/BOM.md` — same MCU, different LED board. See that doc for the general parts-buying notes; this doc only calls out what differs for the strip variant.

Every part below is a standard, unrestricted commodity electronic component (microcontroller dev board + addressable LEDs + passives). Nothing here is export-controlled, encryption-related, or radio-emitting beyond the board's native USB.

## Phase 1 — Breadboard MVP

| # | Part | Qty | Approx. Cost | Notes |
| --- | --- | --- | --- | --- |
| 1 | Waveshare RP2040-Zero | 1 | ¥30 | The MCU dev board |
| 2 | Custom PCBA, WS2812-style addressable strip (10 LEDs) | 1 | — (already in hand) | — |
| 3 | Half-size breadboard | 1 | ¥10 | — |
| 4 | Jumper wire set (M-M, M-F) | 1 set | ¥10 | — |
| 5 | 3-pin connector/wire matching the PCBA's header (`S`/`V`/`G`) | 1 | ¥5 | Match the PCBA's actual header type (JST or plain pin header) |
| 6 | USB-C to USB-A cable (data-capable) | 1 | ¥15 | Confirm it's rated for data transfer, not charge-only — many cheap cables are power-only and won't enumerate as a serial device |
| 7 | (Optional, only if data-line glitches are observed) 74HCT125 level shifter | 1 | ¥2 | Not needed by default — see `../firmware/README.md` Power note. Buy only if troubleshooting shows a real need. |

**Phase 1 total: ~¥60 (~$8), plus whatever the PCBA itself cost.** No soldering strictly required beyond the MCU's header pins — everything else plugs together.

> **Difference from the bulb variant:** this variant's LED PCBA (item #2) is an addressable WS2812-style strip with 10 LEDs on a 3-pin connector (`S`/`V`/`G`), not 3 discrete bulbs on a 4-pin connector. It draws meaningfully more current than the bulb PCBA (10 LEDs vs. 3), so `V` must come from the MCU's 5V/`VBUS` pin, not 3V3 — see `../firmware/README.md` for the full power reasoning.

## Phase 2 — Custom PCB

Same fab path as the bulb variant (`../../led-bulb/docs/BOM.md` Phase 2) if you later consolidate MCU + LED strip onto one board — not detailed separately here since it depends on the final KiCad layout, which hasn't been designed yet for either variant.

## Notes

- The LED strip PCBA (item #2) is already in hand — not something to source for Phase 1.
- Buy a spare strip PCBA if redesigning in Phase 2 — cheap insurance, same reasoning as spare bulbs in the bulb variant's BOM.
