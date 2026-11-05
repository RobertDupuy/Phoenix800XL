# Phoenix v0.13 for Atari 5200

Phoenix for an NTSC Atari 5200 with 16 KiB RAM. The 256 KiB cartridge uses CAR
type 73 and includes the repeating five-wave game: two small-bird waves, two
large-bird waves and the mothership, followed by harder cycles.

[Current cartridge](Phoenix5200.car) ·
[Complete source and test fixtures](Phoenix5200-Source-and-Tests.zip) ·
[Emulator preview with sound](Phoenix5200-Preview.mp4)

## Corrected in v0.13

- PHOENIX uses 69 copies of a flying gameplay bird pose with a visible head,
  body and wing. The gaps between N, I and X contain no stray marks.
- All labels are rebuilt from native HUD glyphs. The complete copyright line,
  INSERT 1 COIN, player/coin instructions and 200-point entry display correctly.
- Presentation pages use one font each throughout the visible frame. This
  removes the late font changes that damaged the first two scanlines of text
  and sprites. Startup also retains its own palette throughout the frame.
- Bullets now hit mothership escorts. A foreground bird absorbs a matching
  shot before the armor behind it. Hits explode and score normally; replacement
  escorts wait until the hit effects and awards finish.

![Title screen](title.png)
![Score table](scores.png)

## Controls and game

Joystick left/right moves the ship. The lower fire button starts a game and
shoots; release and press again for each shot. The upper button activates the
shield. The test keyboard mapping uses Left/Right, Left Ctrl for fire, and
Left Shift for shield.

The game retains arcade-derived movement, vertical large-bird motion, center-hit
score numbers, square/asterisk wipe transitions, wave palettes and increasing
round difficulty. There are sixteen small birds, six large birds, and two
replenishing mothership escorts. The mothership has destructible armor, a moving
barrier, a pilot hit gate and a victory sequence. Opening/victory music and sound
effects use POKEY arrangements of recovered arcade data. Large-bird waves have
bird tones over a black background, without an added continuous melody.

## Verification

Reports for the current cartridge are in `evidence/current`.

- Four actual Altirra screenshots across repeated title/score page transitions
  matched all 245,760 displayed pixels, with no missing pixels, stray pixels or
  inconsistent colors. This checks emulator output, not only generated fonts.
- Targeted CPU fixtures cover both escort slots, misses, hit effects, scoring,
  foreground/armor priority and replenishment after awards.
- 411 campaign checks passed across all 16 round values, including armor,
  barriers and progression.
- A controller-driven cold-boot run shot four observed escorts well above the
  ship/shield collision area, destroyed the mothership and entered round two.
  It reads RAM for targeting and observations but never writes game RAM, skips
  waves, loads states or grants invulnerability.

Bird waves render at about 30 updates per second. The mothership remains around
15–20; input and audio run every NTSC video interrupt, with elapsed-frame
simulation catch-up. Atari colors and sound approximate arcade hardware.
Validation used AltirraSDL, not a physical 5200.

## Build

Install LLVM-MOS SDK v23.4.0 (clang 24.0.0git, commit
`a40207a371b60ff787ece46817d9c0f62eada719`) and Python 3.

```sh
export LLVM_MOS=/absolute/path/to/llvm-mos
python tools/build.py
```

The output is `build/Phoenix-First-Flight.car`. The eight 32 KiB banks keep the
fixed lower 16 KiB and vectors identical. `Phoenix5200.car` is the current
release copy; its checksum is in `SHA256SUMS.txt`.

## Tests

CPU tests require `py65`; image checks also require `numpy` and `Pillow`.

```sh
python tests/escort_collision_v013.py
mkdir -p evidence/v011
python tests/campaign_acceptance.py
```

For emulator checks, use AltirraSDL commit
`6ec52575a851e160df070733bd43f955572db5dc` with the included frontend pipe patch.
The patch changes test transport only. Set `ALTIRRA_BRIDGE_SDK` to its Python
SDK directory and `ATARI5200_BIOS` to an original BIOS whose SHA-256 is
`06b250f18983d058c0f156ce7ee88ae48b6eaf11e6f10f21dccf6ac7ffb6a6af`.

```sh
export SDL_VIDEODRIVER=dummy
export SDL_AUDIODRIVER=dummy
python tests/presentation_v013.py --out tests/new-presentation \
  --exe /absolute/path/to/AltirraSDL --record
python tests/play_campaign.py --out tests/new-playthrough \
  --exe /absolute/path/to/AltirraSDL --frames 20000 --goal-wave 6 --record
```

The complete source ZIP contains optional C reference files and large MAME trace
fixtures for the other regression scripts. Original BIOS, full arcade ROMs,
emulator binaries, local configuration and authentication logs are not bundled.
The preview contains native emulator audio raised 6 dB, with no added soundtrack.
Original ownership and source notices are preserved in `src/arcade-assets` and
`reference/notices`.
