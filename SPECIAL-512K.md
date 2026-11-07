# Phoenix800XL 512K MegaCart special build

This separate cartridge was requested for Mean Hamster OS users needing a
512 KiB image. It does not replace the normal 256 KiB release or change its URL.

Load **Phoenix800XL-512K.car**. It contains a 524,288-byte ROM plus the 16-byte
CAR header (524,304 bytes total), using **MegaCart 512 KB / CAR type 31**.
The cartridge still requires only a stock 64 KiB Atari XL/XE.

The first 256 KiB are identical to the published cartridge whose SHA-256 is
`902bbd1b8110c43eac3cef7ddf032f11d159e899051f0e2ee63133ee7e22ddf0`.
The additional 16 banks contain $FF padding. The CAR mapper number and checksum
are updated for the larger image. Gameplay, sound, controls, seven large birds,
five mothership escorts, scrolling background and T1X artwork are unchanged.
The middle planet remains removed.

Build this variant:

```sh
LLVM_MOS=/path/to/llvm-mos python3 tools/build.py --cart-size 512
```

Without the option, the build still produces the identical 256 KiB cartridge.
The build writes separate filenames so it does not overwrite that cartridge.

Run the existing emulator integration checks against the 512K variant:

```sh
ALTIRRA_BRIDGE_PACKAGE=/path/to/AltirraBridge-nightly-linux-x86_64 \
PHOENIX_XL_CART="$PWD/Phoenix800XL-512K.car" python3 tests/xl_integration.py
```

The special build is tested in AltirraBridge as a stock 64 KiB NTSC 800XL.
Cold boot, joystick movement, shield, all five waves, warm reset and cold reset
passed. The wave checks retained 16/16/7/7/5 enemies with zero late VBI,
audio underruns, missing audio frames or layout faults. The default 256K build
reproduces the published cartridge byte-for-byte; the 512K image passes the
header, length, checksum and unchanged-game-bank comparisons.
Actual loading through HamsterOS on physical hardware has not been tested.
This is a capacity-format variant, not a change to HamsterOS or its firmware.
The general README and prior evidence describe the normal 256 KiB build;
the special build's packaging and emulator results are in `evidence/xl/512k`.

Mapper reference:
https://raw.githubusercontent.com/atari800/atari800/master/DOC/cart.txt
