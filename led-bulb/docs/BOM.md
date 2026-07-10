# Bill of Materials: Agent Andon Light

Two BOMs: **Phase 1 (breadboard MVP)** — buy this first, cheap, to prove the whole concept — and **Phase 2 (custom PCB)**, once the software/firmware works end-to-end.

Every part below is a standard, unrestricted commodity electronic component (microcontroller dev board + addressable LEDs + passives). Nothing here is export-controlled, encryption-related, or radio-emitting beyond the board's native USB — safe to source domestically and safe to hand any vendor as a parts list.

Sourcing base is **mainland China**, buying directly from **拼多多 (Pinduoduo)** and **SZLCSC (szlcsc.com / 立创商城)** — no international marketplace (Temu/AliExpress) in the loop anymore.

## SZLCSC vs. Pinduoduo — Sourcing Comparison

| Dimension | SZLCSC (szlcsc.com / 立创商城) | Pinduoduo (拼多多) |
| --- | --- | --- |
| What it's for | Authentic, traceable electronic **components** — ICs, passives, connectors, reels/cut-tape/loose piece | Generic consumer-facing **modules, dev boards, tools, cables** |
| Part authenticity | High — official distributor, real datasheets, lot/batch traceability | Variable — open marketplace of small sellers; clones/mislabeled parts are a real risk on branded modules (e.g. dev boards) |
| Min order qty | Usually 1 pc for most catalog parts (some reel-only parts have a MOQ) | Usually 1 pc; frequent group-buy (拼团) pricing for small multi-unit discounts |
| Pricing | Fair wholesale-ish pricing for genuine parts; small premium on tiny single-piece orders | Usually the cheapest option for generic modules/hobbyist kits — built for aggressive pricing |
| Domestic shipping | Fast (1–3 days, ships from Shenzhen), often free over a small order threshold | Fast (1–5 days), but courier/speed varies seller to seller |
| Invoicing | Proper VAT invoice (发票) available — useful for a documented, production-grade BOM | Consumer receipt only, generally no formal invoice |
| Selection gap | Does **not** carry breadboards, jumper wire kits, or generic USB cables — components only | Does **not** reliably carry precision/branded parts with guaranteed authenticity |
| Best fit here | **Phase 2** — fab-bound SMD components, especially if using JLCPCB's assembly service (parts must be in their stock, which pulls from LCSC/SZLCSC) | **Phase 1** — generic breadboard parts, dev board, tools; cheapest and fastest for one-off hobbyist buys |

**Net call:** Pinduoduo for Phase 1 (nothing here needs traceability, and PDD is cheaper/faster for generic modules), SZLCSC for Phase 2's SMD components feeding into JLCPCB, PDD as fallback for the one item (the RP2040-Zero dev board) that SZLCSC may not stock as a finished module.

## Phase 1 — Breadboard MVP

Sourced via **Pinduoduo (拼多多)**, per your call on cost and delivery time for this phase.

| # | Part | Qty | Approx. Cost (CNY) | Sourced Via | Chinese Search Keywords |
| --- | --- | --- | --- | --- | --- |
| 1 | Waveshare RP2040-Zero | 1 | ¥30 | Pinduoduo | "RP2040-Zero 开发板" or "Waveshare RP2040 Zero" |
| 2 | Custom PCBA, 3x LED bulbs (Red/Yellow/Green) | 1 | — (already in hand) | n/a | — |
| 3 | Half-size breadboard | 1 | ¥10 | Pinduoduo | "面包板 400孔 无焊" |
| 4 | Jumper wire set (M-M, M-F) | 1 set | ¥10 | Pinduoduo | "杜邦线 公对公 公对母" |
| 5 | 4-pin connector/wire matching the PCBA's header (GND, R, Y, G) | 1 | ¥5 | Pinduoduo | "杜邦线 4Pin 单头" or match the PCBA's actual header type (JST/排针) |
| 6 | USB-C to USB-A cable (data-capable) | 1 | ¥15 | Pinduoduo | "USB-C 数据线" (confirm listing says 数据线/传输, not just 充电线/charge-only) |

**Phase 1 total: ~¥60 (~$8), plus whatever the PCBA itself cost.** No soldering strictly required beyond the MCU's header pins — everything else plugs together.

> **Caution on Pinduoduo specifically:** it's an open consumer marketplace, so part numbers/specs are looser than a dedicated components distributor (SZLCSC) or an official brand store. For item #1 in particular, double-check the listing is a genuine RP2040-based Waveshare board (check seller reviews and listing photos of the actual chip markings) before ordering, and confirm cable listings explicitly support data transfer, not just charging.
>
> **Note (2026-07-07):** the LED side of Phase 1 changed from a WS2812B addressable strip to a custom PCBA with 3 discrete LED bulbs (Red/Yellow/Green) on a 4-pin connector (`GND`+3 signal) — already in hand, so it's no longer a line item to source. This also drops the WS2812-specific parts (data-line resistor, decoupling cap, level shifter) from both phases below, since discrete on/off LEDs don't need them — any current-limiting resistors live on the PCBA itself.

## Phase 2 — Custom PCB

Adds to / replaces Phase 1 parts once the design is finalized in KiCad. PCB fab/CAD goes to **JLCPCB**, by its Chinese name/company **嘉立创 (Jiālìchuàng)**, per your call:

| # | Part | Qty | Approx. Cost (CNY) | Sourced Via | Chinese Search Keywords | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Waveshare RP2040-Zero | 1 | ¥30 | Pinduoduo | "RP2040-Zero 开发板" | Same module, now hand-soldered onto the custom PCB via its castellated edge pads; not reliably stocked as a finished module on SZLCSC |
| 2 | LED bulbs (Red/Yellow/Green, 5mm through-hole or SMD to match final footprint) | 3 | ¥3 | SZLCSC | "5mm LED 红色" / "5mm LED 黄色" / "5mm LED 绿色" (or "贴片LED" for SMD) | Same 3 discrete colors as the Phase 1 PCBA, sourced individually if integrating them onto a new board rather than reusing the existing PCBA |
| 3 | 220–330 Ω resistor x3 (one per LED, through-hole or 0805 SMD to match) | 3 | ¥1 | SZLCSC | "330欧 电阻 直插" or "贴片电阻 0805" | Current-limiting per bulb — simple Ohm's-law sizing for a plain on/off LED, no protocol timing concerns like WS2812 had |
| 4 | USB-C connector (if not relying on the RP2040-Zero's onboard port) | 1 | ¥2 | SZLCSC | "Type-C 母座 贴片" | Only needed if the enclosure design routes the cable differently than the board's own port |
| 5 | Custom PCB (2-layer), CAD sent to fab | 5–10 (min order) | ¥15–35 total | **JLCPCB (嘉立创)** | "PCB打样" / upload Gerber directly on jlcpcb.com | Order 5–10 minimum, spares are nearly free at this size |
| 6 | 3D-printed or laser-cut enclosure/diffuser | 1 set | ¥10–35 | JLCPCB add-on service, or Pinduoduo for local 3D print/laser-cut service | "3D打印服务" / "亚克力激光切割" | Can ride along with the PCB order or be sourced separately |

**Phase 2 total: ~¥50–90** including PCB fab minimums and enclosure (spread across however many units you order — 5–10 boards for the price of one is normal for small-batch PCB fab, so keep the spares). If Phase 2 just reuses the existing 3-bulb PCBA from Phase 1 rather than redesigning the LED board, items #2–3 aren't needed at all — only relevant if consolidating everything (MCU + LEDs) onto one new board.

## Sourcing Notes

- **Phase 1 (Pinduoduo):** optimized for cost and delivery speed on the breadboard/wiring parts. Since these are generic modules (not going onto a fabricated board), listing/part-number looseness matters less here than in Phase 2 — just verify item #1 and the cable as noted above. The LED PCBA itself (item #2) is already in hand, not something to source.
- **Phase 2 PCB fab (JLCPCB / 嘉立创):** send the KiCad Gerbers/CAD here for fabrication. If you also want **JLCPCB's SMT assembly service** (they place and solder the SMD parts for you, rather than you hand-soldering), the parts must be sourced through **SZLCSC** — same corporate family as JLCPCB, and their assembly line pulls stock directly from the SZLCSC catalog. Check each part's SZLCSC part number is in JLCPCB's basic/extended parts library before finalizing the KiCad BOM. If you're hand-soldering instead, Pinduoduo works fine and is usually cheaper for small one-off quantities of the non-critical passives.
- Buy a spare LED bulb or two of each color if redesigning the LED board in Phase 2 — cheap insurance against a dead LED or a reversed-polarity mistake during hand-soldering.
