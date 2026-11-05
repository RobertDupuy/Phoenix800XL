# Phoenix v0.12 for Atari 5200

This release implements the repeating five-wave game: two small-bird waves,
two large-bird waves, and the mothership. Destroying the mothership advances to
the next, harder cycle. It uses a 256 KiB cartridge image, CAR type 73, and
targets an NTSC Atari 5200 with 16 KiB RAM.

Move with the joystick, press the lower fire button to shoot, and use the upper
fire button for the shield. Fire starts a game. Shots require new button presses.
The Altirra keyboard mapping used by the test player is Left/Right, Left Ctrl
for fire, and Left Shift for shield.

## New in v0.12

The title spells PHOENIX with 69 intact small-bird sprites from the gameplay
renderer. The score table also uses the current small-bird, large-bird and pilot
artwork at native size and with their gameplay colors. The old converted
illustrations have been removed.

[Download the v0.12 cartridge](Phoenix-v0.12.car) ·
[Complete source and test fixtures](Phoenix-v0.12-Source-and-Tests.zip)

![Title screen](title.png)
![Score table](scores.png)

## Game features

- Mothership entry and descent, persistent destructible armor, rotating barrier,
  pilot hit gate, explosion, score display, victory tune and next-round entry.
- Six large birds and two replenishing mothership escorts, using the population
  reduction authorized for this port. Small waves retain sixteen birds.
- Original round-dependent formations, activation and flight parameters, with
  the complete round nibble passed to the recovered arcade routines. Enemy bomb
  capacity increases from three to four to five over the first three cycles.
- Arcade square/asterisk fill-and-clear wipes before the large-bird waves and
  mothership; the small-wave entrance scroll/fade is retained.
- Distinct small-wave and large-wave palettes derived from the arcade color data;
  a gold mothership, pink rotating barrier and blue starfield. Atari GTIA colors
  approximate the original RGB palette.
- Large-bird vertical motion and center-hit number displays are retained.
- Opening and victory music, bird tones, fire, impact, shield and explosion
  sounds use the POKEY arrangement of the recovered music/circuit data.
  Large-bird waves have a black background and bird tones, rather than an added
  continuous melody.

## Validation and limits

See `evidence/v012` for reports tied to this cartridge SHA-256. The new build
passed a cold boot through both presentation pages, a pixel-for-pixel decode of
both generated pages, and a controller-driven completion of all five waves
into round two. All 77 non-intro binary data files match v0.11. The automated
Altirra player uses physical controller-key events from a cold boot with the
original Atari BIOS. It reads RAM for targeting and observations; it does not
write game RAM, load states, grant invulnerability or skip stages. Separate
CPU/pixel tests explicitly use fixtures and are not presented as playthroughs.

The normal bird waves render at about 30 updates per second. The mothership is
still heavier, roughly 15–20 updates per second in the recorded run. Input and
audio continue on every NTSC video interrupt. Elapsed-frame simulation catches
up across normal boss rendering delays. This is a complete playable wave loop,
not a claim of a locked 30 fps mothership or identical arcade hardware output.
Validation is in AltirraSDL; this release has not been tested on a physical 5200.

## Build

Install LLVM-MOS SDK v23.4.0 (clang 24.0.0git, a40207a371b60ff787ece46817d9c0f62eada719)
and Python 3. The generators use the checked-in source assets.

```sh
export LLVM_MOS=/absolute/path/to/llvm-mos
python tools/build.py
```

The output is `build/Phoenix-First-Flight.car`; the historical internal filename
is retained. All eight 32 KiB banks keep the fixed lower 16 KiB and vectors
identical. The cartridge mapper is the 256 KiB Atari 5200 Super Cart (type 73).

## Tests

CPU and pixel tests require Python packages `py65`, `numpy` and `Pillow`.

```sh
python tests/campaign_acceptance.py
python tests/campaign_cache.py
python tests/flight_acceptance.py
python tests/renderer_native.py
python tests/score_popup_v010.py
python tests/audio_v010.py
python tests/flight_lockstep.py
MAME_TRACE=reference/mame-motion-fixtures/trace.bin python tests/flight_lockstep.py
```

The v010 test filenames are retained regression tests; they read the currently
built cartridge. Some legacy reports are written to `evidence/v011`; create
that directory before running those scripts. The source ZIP includes the
large MAME trace fixtures and C reference files used by the optional lockstep
checks. Extract it to obtain the complete reference tree.

Controller playback uses AltirraSDL commit
`6ec52575a851e160df070733bd43f955572db5dc` with the included frontend pipe-transport
patch. That patch changes UI-test transport only, not the machine emulation.
Set `ALTIRRA_BRIDGE_SDK` to its Python SDK directory and `ATARI5200_BIOS` to your
original BIOS file. Its required SHA-256 is
`06b250f18983d058c0f156ce7ee88ae48b6eaf11e6f10f21dccf6ac7ffb6a6af`.

```sh
export SDL_VIDEODRIVER=dummy
export SDL_AUDIODRIVER=dummy
python tests/play_campaign.py --out tests/new-playthrough \
  --exe /absolute/path/to/AltirraSDL --frames 48000 --goal-wave 11 --record
```

The video is the emulator's native ZMBV/PCM recording. The preview MP4 scales
pixels with nearest-neighbor sampling and raises recorded audio by 6 dB. It
does not add a soundtrack. The recording menu must be available in the emulator
build. Original BIOS, full arcade ROMs and emulator binaries are not bundled.

Original assets and source lineage retain their existing notices in
`src/arcade-assets/ORIGINAL-NOTICES.md` and `reference/notices`.
