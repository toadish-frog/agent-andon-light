# Firmware — Agent Andon Light

Arduino sketch for the Waveshare RP2040-Zero, implementing the v1 wire protocol from `.prompt/docs/Implementation-Summary.md` (`G`/`Y`/`R`/`H`).

## Setup (once — see `.prompt/docs/USER-GUIDE.md` Phase 1 checklist)

1. Arduino IDE 2.x, with the `arduino-pico` board package and the Adafruit NeoPixel library installed.
2. Open `andon_light_firmware/andon_light_firmware.ino` — Arduino IDE will load `led_controller.h/.cpp` and `watchdog.h` alongside it as tabs.

## Wiring

- WS2812 data pin ← `GPIO0` (through the 300–500 Ω resistor from the BOM)
- WS2812 5V/GND ← board 5V/GND (add the 1000 µF cap across these if you have one)

Change the pin in `andon_light_firmware.ino` by editing `kLedDataPin` if you wire it differently. Note the RP2040-Zero uses plain GPIO numbers (`GPIO0`, `GPIO1`, ...), not the `D0`-style aliases Seeed's boards use — don't copy pin names from XIAO tutorials verbatim.

**Free smoke test before wiring anything:** the RP2040-Zero has its own onboard WS2812 RGB LED on `GPIO16`. You can flash a quick one-off sketch pointed at pin 16 to confirm the board, toolchain, and NeoPixel library all work *before* you've wired a single external LED — a good first checkpoint given no hardware here has been tested yet.

## Flash & test

1. Select "Waveshare RP2040-Zero" as the board, then flash.
2. Open the Serial Monitor at 115200 baud, line ending "Newline".
3. Type `G`, `Y`, `R` and press enter — confirm the LEDs respond. Then stop sending anything for ~15s and confirm it drops into a slow red pulse (the stale/disconnected state) rather than freezing on the last color.

## Known unknowns (this hasn't touched real hardware yet)

- `kLedDataPin = 0` (GPIO0) is a starting guess, not a verified pin — swap it if you wire the LED elsewhere. Avoid GPIO16 for the external strip since that's wired to the onboard LED.
- `NEO_GRB + NEO_KHZ800` is the standard WS2812B config; if colors come out swapped (e.g. green shows as red), the specific LEDs you received may use a different color order — check the datasheet/listing.
