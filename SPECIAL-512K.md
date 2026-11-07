# Phoenix800XL 512K J(atari)Cart special build

Load **Phoenix800XL-512K.car**. This replaces the failed MegaCart special build
with **J(atari)Cart 512K / CAR type 110**, the same mapper as the supplied working
Flicky cartridge. The normal 256K MegaCart release remains unchanged.

The ROM is 524,288 bytes; the CAR file is 524,304 bytes including its header.
It runs on a stock 64 KiB Atari XL/XE. Gameplay, sound, controls, seven large
birds, five mothership escorts, T1X artwork and the latest scrolling background
are retained. The middle planet remains removed.

This is a real banking conversion. J(atari)Cart maps an 8 KiB window at
$A000–$BFFF, selected by the address of a write to $D500–$D53F. Startup now
copies common code and artwork into RAM at $4000–$9FFF. Mothership code and data
fit together in one ROM bank by reusing native artwork in RAM; its masks use
otherwise unused RAM at $D800. Large bird artwork uses 30 complete poses per
bank, selected by pose. Blank mothership tiles share an identical blank shape.
Runtime banks include reset stubs. No artwork pixels were resampled or changed.

Build:

```sh
LLVM_MOS=/path/to/llvm-mos python3 tools/build.py --cart-size 512
python3 tests/jcart_packaging.py
```

The default build still produces the byte-identical normal 256K cartridge.
The special build uses a separate filename.

Validation in stock 64 KiB NTSC AltirraBridge:

- A joystick-only player completed all five waves, defeated the mothership and
  reached wave 6. It used no game RAM writes, and exercised deaths and restarts.
- Cold boot, joystick movement, shield, warm reset and cold reset passed.
- Full-flock wave fixtures retained 16/16/7/7/5 enemies. Render rates were
  29.961, 29.961, 21.872, 22.471 and 18.676 frames/s. No late VBI, audio
  underruns, missing audio frames or layout faults occurred in those samples.
- Both large waves matched the normal cartridge's decoded graphics across
  640 frames. Mothership graphics matched across 280 damage/scroll fixtures.
- The scrolling background passed 544 pixel comparisons, all 256 entrance
  offsets and 320 timing checks, with no pixel errors or blank bands.
- Packaging checks validate all 120 large-bird poses, 128 mothership tile
  halves, cartridge checksum, resident RAM copies and runtime reset stubs.

The measured large-bird rendering CPU cost increased 0.53%; mothership cost
increased 0.07% in the matched graphics fixtures. No enemy counts were reduced.
Reports and emulator screenshots are in `evidence/xl/512k`. Older evidence
elsewhere retains the normal cartridge's original hashes and provenance.
Physical loading through HamsterOS still needs the user's hardware test.

Emulator checks:

```sh
ALTIRRA_BRIDGE_PACKAGE=/path/to/AltirraBridge-nightly-linux-x86_64 \
PHOENIX_XL_CART="$PWD/Phoenix800XL-512K.car" python3 tests/xl_integration.py
ALTIRRA_BRIDGE_PACKAGE=/path/to/AltirraBridge-nightly-linux-x86_64 \
PHOENIX_XL_CART="$PWD/Phoenix800XL-512K.car" python3 tests/xl_playthrough.py
```

Mapper references:
https://github.com/jhusak/jataricart
https://raw.githubusercontent.com/atari800/atari800/master/DOC/cart.txt
