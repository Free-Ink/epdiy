# FreeInk fork notes (branch `esp32s31`)

This branch is [EPDiy](https://github.com/vroland/epdiy) 2.1.3 with the
ESP32-S31 / ESP-IDF 6.1 port that the Metalio E-Ink4-Plus vendor made in
[CloudZao/Metalio-E-INK4-Plus](https://github.com/CloudZao/Metalio-E-INK4-Plus)
(commit `690a023c66862af103a3187464373ee7c5efcd14`,
`main/boards/metalio-e-ink4-plus/display/`). The vendor credits Shenzhen Xinzhi
Future Technology Co., Ltd. Their repository is MIT, but the EPDiy code in it
stays LGPL-3.0, as does this fork (`LICENSE`).

## Changes against upstream 2.1.3

- Render core, LCD driver, high-level API and board core from the vendor port.
- `src/output_common/riscv_ve.c`: C versions of the Xtensa vector routines in
  `diff.S` / `lut.S`, from the vendor port without its self-test.
- `src/output_lcd/lcd_driver.c`: the S31 LCD low-level calls take LCD group 0,
  as the ESP-IDF 6.1 snapshot in pioarduino's Arduino 4.0 expects.
- `src/output_common/lut.c`: an S31 pixel-pair lookup, used when EPDiy is
  initialized with `EPD_LUT_64K`. The 1K lookup needs about 37 us per
  1216-pixel row on the S31, more than the 34 us each of the two line producers
  has, so the LCD stream underran. The 64K table is expanded from the 1K table
  each phase and keeps its bit order.
- `src/render.c`: line queues of 104 rows per producer instead of the vendor's
  128, which frees about 14.6 KB of internal RAM. The 192-row prefill needs 96.
- `src/displays.c`: only the `E0470A14_AF` panel, so the built-in waveform
  tables are not linked.
- `src/waveforms/my_*`: the vendor's E0470A14-AF waveforms. `my_gray8_*.h` are
  Apache-2.0 (`src/waveforms/LICENSE.gray8`).
- `src/font.c`: `uncompress` renamed to `epd_uncompress` to avoid the zlib
  symbol.
- `library.json`: the upstream board files and the I2S output are left out of
  the build.

## Compliance

This is not legal advice. Whoever distributes a firmware image that links this
library (it is statically linked) should, as LGPL-3.0 section 4 asks: state that
the image uses EPDiy under the LGPL-3.0, ship or point to the LGPL-3.0 and
GPL-3.0 texts, and point to the exact source commit, so a recipient can rebuild
the image with a modified copy of this library.
