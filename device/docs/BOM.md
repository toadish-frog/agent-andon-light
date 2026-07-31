# Bill of Materials: Agent Andon Light

Every part is a standard, unrestricted commodity component (MCU dev board + addressable LEDs + passives). Nothing here is export-controlled, encryption-related, or radio-emitting beyond the board's native USB.

## Fabricated PCB (current build)

| Designator | Part | Qty | Footprint |
| --- | --- | --- | --- |
| WS-RP2040-Zero1 | Waveshare RP2040-Zero | 1 | hand-soldered directly to board |
| D1–D10 | WS2812B-2020 addressable RGB LED | 10 | WS2812B-2020 |
| C1 | 470 µF electrolytic capacitor | 1 | CP_Elec 6.3×5.4 |
| C2–C11 | 100 nF ceramic capacitor (one per LED) | 10 | 0402 |
| R1 | 330 Ω resistor, series on data line | 1 | 0805 |

No level-shifter footprint populated — unnecessary at 3.3V logic for this LED batch. Full sourcing detail (LCSC part numbers, manufacturer, datasheet links) is in [`andon_light_strip-RevA-BOM.csv`](../hardware/manufacturing/pcba/send-to-jlc/andon_light_strip-RevA-BOM.csv) and its CPL file — generated straight from KiCad, authoritative over this table if they ever disagree.

**Enclosure:** 3D-printed chassis, base + lid. STEP files: [`chassis_base`](../hardware/models/andon_light_chassis_base.step), [`chassis_lid`](../hardware/models/andon_light_chassis_lid.step).

## Breadboard / hand-wired build

For prototyping without the fabricated PCB:

| # | Part | Qty | Notes |
| --- | --- | --- | --- |
| 1 | Waveshare RP2040-Zero | 1 | — |
| 2 | Custom PCBA, WS2812-style addressable strip (10 LEDs) | 1 | — |
| 3 | Half-size breadboard | 1 | — |
| 4 | Jumper wire set (M-M, M-F) | 1 set | — |
| 5 | 3-pin connector matching the PCBA's header (`S`/`V`/`G`) | 1 | Match the PCBA's header type (JST or pin header) |
| 6 | USB-C to USB-A cable, data-capable | 1 | Many cheap cables are charge-only and won't enumerate as serial |
| 7 | 74HCT125 level shifter (optional) | 1 | Only if data-line glitches appear — see [`../firmware/README.md`](../firmware/README.md) |
| 8 | 330–470 Ω resistor (optional, recommended) | 1 | Series on data line (`GPIO1` → strip `S`), close to strip end |
| 9 | Electrolytic capacitor, 100–1000 µF ≥6.3V (optional, recommended) | 1 | Across `V`/`G`, close to strip end. Polarized. |

No soldering required beyond the MCU's header pins — everything else plugs together.

## Notes

- Assembly-service SMD placement requires the listed parts to be in that assembler's own stock — check before finalizing the KiCad BOM. Hand-soldering has no such constraint.
- Buy a spare strip PCBA if redesigning — cheap insurance against a dead LED or reversed-polarity mistake.
- An earlier iteration used a different LED board — 3 discrete bulbs (Red/Yellow/Green) on a 4-pin connector. Preserved for reference at [`../../archive/led-bulb-mvp/docs/BOM.md`](../../archive/led-bulb-mvp/docs/BOM.md); not part of the current build.
