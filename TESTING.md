# Atari 800XL playtest validation

Current cartridge SHA-256: `4e5f1290f973d2a479f05ee6cc29badf73b707d3423e5365eb2ced9c7baf9008`.

The current correction suppresses the repeating bonus beep during Für Elise.
The 720-tick comparison with and without bonus timers has zero POKEY register
mismatches. The current CPU/audio and live-victory reports are under
`evidence/victory-audio/`; other game effects remain enabled.

Rendering and controller-playthrough measurements below were obtained on the
preceding build, SHA-256
`942711eff8535cb97c96f1f4eaab9488c42356c5aa12de4fea8080d9c1b70a6e`.
The beep correction leaves its rendering and gameplay code unchanged.

Cartridge: **MegaCart 256 KB, CAR type 30**. This build adds the rendering
optimizations and victory-sound correction described in PERFORMANCE.md.

Tested with AltirraBridge nightly on an NTSC 800XL configured with stock
64 KB RAM, the built-in Altirra XL OS, normal CPU and no VBXE, Rapidus or
stereo POKEY. Fast boot was disabled. Original Atari XL OS ROMs and physical
hardware were not tested. PAL timing is outside this build's validation.

## Results

- Cold boot, fire start, left/right/neutral, down shield, warm reset and cold
  reset passed. Input tests use joystick events without game RAM writes.
- The joystick-only player completed all five waves and reached wave 6 in
  6,676 video frames after boot. It lost two lives, defeated the mothership,
  received the award/extra life and entered the next cycle. No stage injection,
  invulnerability, save-state restore or game-memory writes were used in this
  playthrough. RAM reads guide its decisions. The final player checks input every four video
  frames; an earlier eight-frame-response attempt reached wave 5 but lost its
  last life. That attempt is retained separately in the evidence. It is an automated player, not
  a recording of human play.
- That complete playthrough recorded zero late VBI counters and zero layout
  faults. The existing scanline-8 deadline was preserved.
- Five controlled full-flock samples, 600 video frames each: zero late VBI,
  audio queue underruns, missing per-frame audio writes or layout faults.
- Large-bird raster comparison: 80 sampled frames, 4,096,000 playfield pixels,
  zero missing, extra or incorrectly colored pixels. Occupied hardware
  projectile pixels are excluded from playfield comparison. Stage placement
  and invulnerability in this check are explicit test fixtures.
- Pixel equivalence with the prior MegaCart renderer: 640 large-wave scenes
  and 280 mothership scenes, including clipping, overlap and damage, matched.
- Victory audio: the old extra-life regression suppressed all melody notes.
  The fixed build reaches 56 note positions and 12 distinct lead pitches
  through the actual core-hit/award/next-wave routines.
- Live victory recording on both platforms: 780 video frames, 55 sequencer
  positions, next-wave entry and the extra life confirmed. Zero late VBI,
  audio underruns, missing sound updates or layout faults. The 13.02-second
  WAV files contain actual emulator POKEY output.
- Artwork: 356 checks covering 63 source frames, the preserved eight bird-hit
  frames, all shield-pose transitions, ship-pose restoration and cockpit
  descent. No pixel-shape or color-region errors.
- Directional animation: 16 direction/phase cases and eight source-pose checks.
- Campaign: 411 CPU checks across 16 rounds, including 120 armor/barrier cases,
  the 120-tick entrance and 160-tick mothership victory route.
- Respawn: 256 large-flock and 544 small-flock cases; 5,536 immediate-collision
  checks passed with no added invulnerability.
- Audio: 4,200 tune ticks, 1,744 pitch cases, 8,192 large-bird control ticks,
  2,048 formation cases, all eight bank-fallback cases, 200 explosion-envelope
  combinations and 16 mixing cases passed. This verifies the retained POKEY
  synthesis, not a new human listening comparison against arcade hardware.

## Measured scene rates

These are full-flock sample averages, not guaranteed worst-case frame rates.
Player input and sound update each video frame; simulation and rendering are
scheduled separately. Rendering becomes faster as the flock thins.

| Wave | Enemies | Render frames/s | Simulation ticks/s |
| --- | ---: | ---: | ---: |
| 1 | 16 | 29.961 | 61.021 |
| 2 | 16 | 29.961 | 61.021 |
| 3 | 7 | 21.872 | 60.921 |
| 4 | 7 | 22.171 | 61.021 |
| 5 | 5 | 18.976 | 61.321 |

## Reproduce

Build the cartridge first, then run:

```sh
python3 tests/xl_large_oracle.py --baseline reference/xl-megacart-baseline
python3 tests/xl_mothership_oracle.py --baseline reference/xl-megacart-baseline
python3 tests/victory_audio.py
python3 tests/campaign_acceptance.py
python3 tests/artwork_v030.py
python3 tests/return_facing_v030.py
python3 tests/audio_v026.py
python3 tests/ship_mixing_v025.py
python3 tests/respawn_v019.py
python3 tests/small_respawn_v020.py
export ALTIRRA_BRIDGE_PACKAGE=/path/to/AltirraBridge-nightly-linux-x86_64
python3 tests/xl_integration.py
python3 tests/large_raster_v029.py --out evidence/xl/raster --samples 40 --check
python3 tests/xl_playthrough.py --frames 36000
```

Version suffixes on CPU tests identify their original 5200 regressions; the
memory model, banking and hardware addresses now target the XL cartridge.
Exact machine configuration, inputs and results are retained in `evidence`.
The emulator and OS ROMs are external dependencies and are not bundled.

The GitHub repository was created by importing Phoenix5200 before the user
requested a playtest first. No XL source commit or XL cartridge has been
published there. Publication remains on hold until the user approves it.
