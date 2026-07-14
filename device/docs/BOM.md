# Bill of Materials: Agent Andon Light

Every part below is a standard, unrestricted commodity electronic component (microcontroller dev board + addressable LEDs + passives). Nothing here is export-controlled, encryption-related, or radio-emitting beyond the board's native USB.

## Phase 1 — Breadboard MVP

| # | Part | Qty | Approx. Cost | Notes |
| --- | --- | --- | --- | --- |
| 1 | Waveshare RP2040-Zero | 1 | ¥30 | The MCU dev board — see `Implementation-Summary.md` §1 for why this board was chosen |
| 2 | Custom PCBA, WS2812-style addressable strip (10 LEDs) | 1 | — (already in hand) | — |
| 3 | Half-size breadboard | 1 | ¥10 | — |
| 4 | Jumper wire set (M-M, M-F) | 1 set | ¥10 | — |
| 5 | 3-pin connector/wire matching the PCBA's header (`S`/`V`/`G`) | 1 | ¥5 | Match the PCBA's actual header type (JST or plain pin header) |
| 6 | USB-C to USB-A cable (data-capable) | 1 | ¥15 | Confirm it's rated for data transfer, not charge-only — many cheap cables are power-only and won't enumerate as a serial device |
| 7 | (Optional, only if data-line glitches are observed) 74HCT125 level shifter | 1 | ¥2 | Not needed by default — see `../firmware/README.md` Power note. Buy only if troubleshooting shows a real need. |
| 8 | (Optional, recommended) 330–470 Ω resistor | 1 | <¥1 | In series on the data line (`GPIO1` → strip `S`), close to the strip end — damps ringing/overshoot on the signal edge. Standard WS2812 wiring practice; cheap enough to include by default. |
| 9 | (Optional, recommended) Electrolytic capacitor, 100–1000 µF, rated ≥6.3V | 1 | ¥1 | Across `V`/`G`, close to the strip end — buffers the current spikes from 10 LEDs switching at once. **Polarized** — mind the +/− legs when wiring. Standard WS2812 wiring practice; cheap enough to include by default. |

**Phase 1 total: ~¥60 (~$8), plus whatever the PCBA itself cost.** No soldering strictly required beyond the MCU's header pins — everything else plugs together.

## Phase 2 — Custom PCB (manufacturing, 2026-07-14)

RP2040-Zero + 390Ω 0805 series resistor + bulk electrolytic cap + one 100nF decoupling cap per LED + 10x WS2812B LEDs, all consolidated onto a single hand-routed KiCad board. The RP2040-Zero is hand-soldered directly to the board (unused castellated pins soldered for mechanical anchoring only) rather than connected via a separate connector.

The authoritative parts list for the fabricated board is `../hardware/manufacturing/send-to-jlc/andon_light_strip-RevA-BOM.csv` (JLC assembly BOM) and its accompanying CPL (component placement) file, not a hand-maintained table here — those are generated directly from the KiCad project and are what was actually sent to the fab, so they won't drift out of sync the way a duplicated table here could.

- Custom PCB (2-layer), Rev A: sent to JLC (`../hardware/manufacturing/send-to-jlc/`, contract on file) — boards not yet in hand.
- No level shifter footprint populated by default (item #7 above resolved as unnecessary on real hardware) — see `Implementation-Summary.md` §6 Open Questions if this needs revisiting for a longer run or a different WS2812 clone batch.

## Notes

- If you want an assembly service to place and solder the SMD parts for you rather than hand-soldering, the parts you list in the BOM need to be in that assembler's own stock — check before finalizing the KiCad BOM. Hand-soldering has no such constraint.
- Buy a spare strip PCBA if redesigning — cheap insurance against a dead LED or a reversed-polarity mistake during hand-soldering.
- **Earlier interim hardware (archived, not part of the current BOM):** Phase 1 of this project originally validated firmware/host/hooks against a different LED board — a custom PCBA with 3 discrete LED bulbs (Red/Yellow/Green) on a 4-pin connector, ¥3-ish per bulb + a 220–330 Ω current-limiting resistor per bulb. That hardware and its own BOM are preserved at `../archive/led-bulb-mvp/docs/BOM.md` for historical reference — it's not part of the ongoing deliverable and nothing here depends on it.
