# XL rendering results and victory-sound correction

Cartridge SHA-256: `942711eff8535cb97c96f1f4eaab9488c42356c5aa12de4fea8080d9c1b70a6e`.
Baseline: `59a43e6189fa3ac936cb9d4595aa885126c5f3ce0ba9e25fc1041ef40a4712bd`.
Both are NTSC, stock 64 KB 800XL, MegaCart 256 KB (type 30).

## Measured rendering rates

The same integration procedure samples 600 video frames per full-flock wave.
These are scene averages, not guaranteed minimum frame rates.

| Scene | Enemies | Before FPS | After FPS | Gain |
| --- | ---: | ---: | ---: | ---: |
| Wave 3 | 7 | 20.074 | 21.872 | 9.0% |
| Wave 4 | 7 | 20.474 | 22.171 | 8.3% |
| Wave 5 | 5 | 16.978 | 18.976 | 11.8% |

The first two waves remain at 29.961 FPS. All five samples retained the full
flocks and recorded zero late vertical interrupts, audio queue underruns,
missing per-frame sound writes, and glyph-allocation faults. Input and sound
continue at video rate; simulation averages about 61 ticks/s independently.

## What was retained

The XL's additional RAM holds an expanded eight-column bird-drawing routine.
Blank tiles skip directly to the next column, avoiding source/map pointer
updates and loop counters. Occupied tiles keep the original unique-glyph and
pixel-OR overlap rules. The platform image now occupies 3 KB, with 4 KB reserved
at C000-CFFF. No RAM expansion, faster CPU, fewer enemies or new artwork is used.

The mothership addresses map cells directly through the column index, removing
repeated pointer additions/subtractions. Animated cells that match their
original artwork now use the existing atlas instead of the damage path.

Matched CPU fixtures reduced large-wave render cycles by 10.15% (640 scenes)
and mothership render cycles by 5.28% (280 scenes). All decoded pixels matched
the baseline. A separate actual-ANTIC comparison checked 80 sampled frames
and 4,096,000 playfield pixels with zero missing, extra or wrong-color pixels.

## Cache experiment outcome

Persistent background and bird-slot caches were implemented and measured.
Their metadata, invalidation and restoration work outweighed their savings;
the background trial was about 20% slower in the matched CPU fixture, and the
bird-slot trial about 28% slower. Those implementations are not in this build.
The retained changes above are the versions that improved measured gameplay.

## Victory tune

The bonus can cross the extra-life threshold at the mothership victory. The
extra-life beep writes the entire sound-B latch, clearing the one-time melody
selection. The old build reaches zero victory notes in that regression.

The arcade sets a 255-tick score-display sound counter at ROM $255B and
reasserts tune 2 at $3923. The correction preserves that behavior: the melody
selection is maintained while the effect bits continue to carry the beeps.
The same correction is supplied for 5200; synthesis, note data and envelopes
are unchanged. The regression executes the actual core-hit, score, extra-life
and next-wave code. Both platforms reach 56 sequencer positions and all 12
lead pitches, with and without an extra-life award.

Reference: https://www.computerarcheology.com/Arcade/Phoenix/Code.html
Original melody hardware configuration:
https://github.com/mamedev/mame/blob/master/src/mame/phoenix/phoenix.cpp

## Reproduction and scope

See TESTING.md and the tests in tests/xl_*oracle.py, tests/xl_integration.py,
tests/victory_audio.py and tests/victory_live.py. Oracle tests take
`--baseline reference/xl-megacart-baseline`. That directory contains the
previous game ROM, its symbols and CPU model for repeatable comparisons.
Raw baseline timing is retained in evidence/xl/baseline-integration.json.
No physical Atari or PAL validation is claimed. For the later scrolling
background change, see SCROLLING.md.
