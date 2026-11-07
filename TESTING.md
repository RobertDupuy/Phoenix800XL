# Atari 800XL continuous-background validation

Current cartridge SHA-256:
`902bbd1b8110c43eac3cef7ddf032f11d159e899051f0e2ee63133ee7e22ddf0`.

[SCROLLING.md](SCROLLING.md) describes behavior, memory use, measurements and
limitations. Test configuration: stock 64 KiB NTSC 800XL, built-in Altirra XL
OS, normal CPU, fast boot disabled, no VBXE, Rapidus or stereo POKEY.
Physical hardware, original XL OS ROMs and PAL timing have not been tested.

## Current-build checks

- `tests/xl_scroll.py`: 544 moving scenes, 256 entrance offsets, complete
  wrap, template-cache integrity and 320 cadence/stage checks.
- `tests/xl_scroll_live.py`: actual ANTIC scenery pixels, 30 FPS timing and silent movie;
  stage placement/invulnerability are explicitly documented fixtures.
- `evidence/xl/scroll/art-change.json`: only the removed planet's bitmap slot
  and the CAR checksum changed; runtime code, placement tables and both
  remaining objects are identical.

Current reports are in `evidence/xl/scroll/cpu.json`, `live/report.json` and
`art-change.json`. Each records the cartridge hash. The 64 shield scenes,
1,168 artwork scenes and full five-wave integration report belong to the
previous build with identical runtime code; their original hashes are retained.

## Reproduce

```sh
LLVM_MOS=/path/to/llvm-mos python3 tools/build.py
python3 tests/xl_scroll.py
python3 tests/xl_scenery_shield.py
python3 tests/renderer_native.py
export ALTIRRA_BRIDGE_PACKAGE=/path/to/AltirraBridge-nightly-linux-x86_64
python3 tests/xl_integration.py
python3 tests/xl_scroll_live.py
```

Install requirements.txt first. Movie capture also requires ffmpeg.
The emulator and OS ROMs are external dependencies and are not bundled.

## Earlier evidence

PERFORMANCE.md and other evidence directories document previous rendering,
sound, respawn and campaign checks. Their hashes identify the builds actually
tested. The joystick-only playthrough in `evidence/xl/playthrough` belongs to
the preceding scrolling build; it reached wave 6 in its second game.

This change does not modify POKEY synthesis or the fix suppressing the
repeating bonus beep during Fur Elise. The extra life and other effects remain
enabled. This additional build is supplied for playtesting before another
GitHub release update.
