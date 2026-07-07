# Firmware — Agent Andon Light

Arduino sketch for the Waveshare RP2040-Zero, implementing the v1 wire protocol from `.prompt/docs/Implementation-Summary.md` (`G`/`Y`/`R`/`H`).

## Setup (once — see `.prompt/docs/USER-GUIDE.md` Phase 1 checklist)

1. Arduino IDE 2.x, with the `arduino-pico` board package installed. No LED library needed — the 3 status bulbs are plain `digitalWrite`/`analogWrite` GPIO, not an addressable protocol.
2. Open `andon_light_firmware/andon_light_firmware.ino` — Arduino IDE will load `led_controller.h/.cpp` and `watchdog.h` alongside it as tabs.

## Wiring

The status light is a custom PCBA with 3 discrete LED bulbs (Red/Yellow/Green) and a 4-pin connector: `GND`, `Red`, `Yellow`, `Green`.

- PCBA `GND` ← board `GND`
- PCBA `Green` ← `GPIO1`
- PCBA `Yellow` ← `GPIO2`
- PCBA `Red` ← `GPIO3`

Change the pins in `andon_light_firmware.ino` by editing `kGreenPin`/`kYellowPin`/`kRedPin` if you wire it differently. Note the RP2040-Zero uses plain GPIO numbers (`GPIO0`, `GPIO1`, ...), not the `D0`-style aliases Seeed's boards use — don't copy pin names from XIAO tutorials verbatim.

## Flash & test

1. Select "Waveshare RP2040-Zero" as the board, then flash.
2. Open the Serial Monitor at 115200 baud, line ending "Newline".
3. Type `G`, `Y`, `R` and press enter — confirm the LEDs respond. Then stop sending anything for ~15s and confirm it drops into a slow red pulse (the stale/disconnected state) rather than freezing on the last color.

## Known unknowns (this hasn't touched real hardware yet)

- `kGreenPin`/`kYellowPin`/`kRedPin` (`GPIO1`/`GPIO2`/`GPIO3`) are starting guesses, not verified pins — confirm against the PCBA's actual connector pinout (read the silkscreen labels, don't assume) and update the sketch to match your wiring.
- The `StalePulse` breathing animation uses `analogWrite` (PWM) on the red pin — confirm `arduino-pico` supports PWM on whichever GPIO you pick for red (most RP2040 GPIOs do; check if you land on a pin that doesn't).
