# Bill of Materials: Agent Andon Light (3-Bulb MVP)

Two BOMs: a breadboard build (cheap, proves the concept) and a custom PCB build, once firmware/software worked end-to-end.

Every part is a standard, unrestricted commodity component. Nothing here is export-controlled, encryption-related, or radio-emitting beyond the board's native USB.

## Breadboard Build

| # | Part | Qty | Cost | Notes |
| --- | --- | --- | --- | --- |
| 1 | Waveshare RP2040-Zero | 1 | ¥30 | MCU dev board |
| 2 | Custom PCBA, 3x LED bulbs (Red/Yellow/Green) | 1 | already in hand | — |
| 3 | Half-size breadboard | 1 | ¥10 | — |
| 4 | Jumper wire set (M-M, M-F) | 1 set | ¥10 | — |
| 5 | 4-pin connector matching the PCBA's header (`GND`, `R`, `Y`, `G`) | 1 | ¥5 | Match the PCBA's header type (JST or plain pin header) |
| 6 | USB-C to USB-A cable, data-capable | 1 | ¥15 | Many cheap cables are charge-only and won't enumerate as serial |

**Total: ~¥60 (~$8),** plus whatever the PCBA itself cost. No soldering required beyond the MCU's header pins.

The LED side used a custom PCBA with 3 discrete bulbs (Red/Yellow/Green) on a 4-pin connector, already in hand — not a WS2812 strip, so no data-line resistor, decoupling cap, or level shifter appears anywhere in this BOM; current-limiting resistors live on the PCBA itself.

## Custom PCB Build

Adds to / replaces the breadboard parts once the design is finalized in KiCad.

| # | Part | Qty | Cost | Notes |
| --- | --- | --- | --- | --- |
| 1 | Waveshare RP2040-Zero | 1 | ¥30 | Hand-soldered onto the custom PCB via its castellated edge pads |
| 2 | LED bulbs (Red/Yellow/Green, through-hole or SMD to match footprint) | 3 | ¥3 | Only needed if integrating onto a new board rather than reusing the existing PCBA |
| 3 | 220–330 Ω resistor (one per LED, through-hole or 0805 SMD to match) | 3 | ¥1 | Current-limiting per bulb — simple Ohm's-law sizing, no protocol timing concerns |
| 4 | USB-C connector (only if not using the RP2040-Zero's onboard port) | 1 | ¥2 | Only needed if the enclosure routes the cable differently |
| 5 | Custom PCB (2-layer), CAD sent to a fab | 5–10 (min order) | ¥15–35 total | Spares are nearly free at this batch size |
| 6 | 3D-printed or laser-cut enclosure/diffuser | 1 set | ¥10–35 | Can ride along with the PCB order or be sourced separately |

**Total: ~¥50–90,** including PCB fab minimums and enclosure, spread across however many units ordered. If reusing the existing 3-bulb PCBA rather than redesigning the LED board, items #2–3 aren't needed.

## Notes

- If you want an assembly service to place and solder the SMD parts for you, the listed parts need to be in that assembler's own stock — check before finalizing the KiCad BOM. Hand-soldering has no such constraint.
- Buy a spare LED bulb or two of each color if redesigning the LED board — cheap insurance against a dead LED or a reversed-polarity mistake during hand-soldering.
