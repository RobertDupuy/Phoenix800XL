# Phoenix for Atari 800XL

An NTSC Atari 800XL port of the current Phoenix5200 release-candidate build.
Runs with stock 64 KB RAM and standard ANTIC, GTIA and POKEY hardware.

**Atari 800XL MegaCart release candidate.**

Load **Phoenix800XL.car** as a **256 KB MegaCart cartridge (CAR type 30)**.
The CAR header selects the mapper automatically in compatible emulators.
The cartridge supplies its own startup code; no Atari 5200 BIOS is used.

| Joystick port 1 control | Action |
| --- | --- |
| Left / right | Move |
| Fire | Start / shoot |
| Down | Activate shield |
| START key | Start a game |

Fire restarts after the existing game-over delay. Reset returns to the title.

The port preserves the five-wave cycle, subsequent difficulty changes, wipes,
mothership entrance and destruction, seven large birds and five escorts.
Hand-drawn sprite artwork is by **T1X**. The original 5200 artwork is retained;
the port changes hardware access and rendering work, not the sprite drawings.
The victory tune now survives an extra-life award; the same correction is supplied
for Phoenix5200. The repeating bonus beep is suppressed during Für Elise;
the extra life and other effects are retained. POKEY note data and synthesis
are unchanged.

The automated joystick player completed the first cycle and reached wave 6.
See [TESTING.md](TESTING.md) for the exact emulator configuration, validation
results and limitations. PAL timing and physical hardware have not been tested.
The measured improvements to large-bird and mothership rendering are documented in [PERFORMANCE.md](PERFORMANCE.md).

## Build

Requires Python 3 and LLVM-MOS SDK. The tested toolchain is LLVM-MOS SDK
v23.4.0, clang 24.0.0git, revision `a40207a371b60ff787ece46817d9c0f62eada719`.

```sh
python3 -m pip install -r requirements.txt
LLVM_MOS=/path/to/llvm-mos python3 tools/build.py
```

Outputs are `Phoenix800XL.car`, `build/Phoenix800XL.car`, and
`build/Phoenix800XL.rom`. The ROM payload is 262,144 bytes; the CAR adds a
16-byte mapper/checksum header. `SHA256SUMS.txt` identifies this playtest build.

## Port layout

Writing a bank number (0–15) to the MegaCart register at `$D500` selects a
16 KB bank at `$8000–$BFFF`. Bank 0 contains startup code and the XL support image.
Bank 1 contains resident code copied into `$4000–$7FFF`. Banks 2–9 contain the
eight original upper windows; the remaining banks are padding.

Startup disables the OS/BASIC ROMs, installs RAM interrupt vectors, and copies
XL support and an expanded bird-drawing routine into `$C000–$CFFF`
(3,072 bytes currently occupied). The NMI dispatcher preserves the original
display-interrupt latency. GTIA and POKEY accesses use the XL register bases;
PIA joystick input replaces the 5200 analog controller reads.

Generated PMG copies share loads for rows that are identical across all poses.
Shield expiry restores the current ship pose once. The descending cockpit
updates only rows that can change, preserving the exact sprite bytes and
leaving the existing VBI deadline unchanged.

This source begins from Phoenix5200 commit
`3011feb189e019b1e6bbd8558b7488a2742d944b` (v0.31). Its asset provenance and
third-party notices remain in [CREDITS.md](CREDITS.md), `src/arcade-assets`,
and `reference/notices`. No new blanket licence is assigned to those materials.
