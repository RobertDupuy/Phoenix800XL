# Continuous dark-blue background on Atari 800XL

Waves 1 and 2, including subsequent cycles, scroll downward at the existing
arcade-derived rate. The complete 256-line field now wraps during entrances
as well as gameplay. The previous entrance clipping left a large empty area;
that clipping is removed. Two empty star rows in the still-image layout are
filled, so every eight-line strip of the background contains scenery.

The left comet uses the original arcade set-B object 2, preserving its compact
head and broken diagonal tail. The middle planet has been removed; only the
underlying stars remain in that slot. `xl-space-objects.json` defines the comet
mapping from `arcade-bg-colors.json`; the native 8x16 logical pixels display at
16x16. The right-hand object remains byte-for-byte identical to the approved
arcade set-B object 4. Everything uses the same existing dark-blue pen. Both
objects retain their previous positions, scroll behavior and foreground priority.

## Rendering

Eight pre-shifted artwork phases occupy $E300-$EAFF. Thirty-two sparse map
placement lists occupy $EB00-$FEFF. Startup copies these 7 KiB from otherwise
unused MegaCart bank-zero space into RAM under the OS. The cartridge remains
256 KiB, MegaCart CAR type 30, and requires only stock 64 KiB RAM.

Glyphs 64-81 are reserved for three background slots on small waves; the
removed middle object's slot now contains only stars.
Birds retain their 62 resident templates and use the remaining dynamic slots.
A buffer's old background positions are erased only when its whole-cell scroll
position changes. Ready-made placements and a short glyph copy replace the
per-object allocation and coordinate work that initially reduced performance.
No extra work is added to the video interrupt.

The transition scratch byte `large_old_mode` now uses $E00D. Its previous
address, $3854, overlapped small-wave glyph 84's ownership record and could
leave a stale cached sprite at the wave-1-to-wave-2 transition. The scrolling
pixel test now verifies cached template contents as well as visible pixels.

## Measurements and validation

| Wave | Full flock | Render frames/s |
| --- | ---: | ---: |
| 1 | 16 | 29.961 |
| 2 | 16 | 29.961 |
| 3 | 7 | 21.872 |
| 4 | 7 | 22.571 |
| 5 | 5 | 18.876 |

The five-wave table above is retained from the prior scenery revision; current
wave-1/2 movie-capture runs independently confirm 29.961 FPS, zero late VBI,
audio underruns and drawing faults. The artwork comparison verifies identical
runtime code, placement tables and both remaining objects; only the removed
planet's bitmap slot and the cartridge checksum changed. See `art-change.json`.

The prior five 600-frame samples recorded zero late VBI, audio underruns, missing
sound writes and glyph-allocation faults. Large/boss rendering algorithms are
unchanged; their averages vary with poses.

- 544 moving-flock/death scenes across all scroll offsets: zero pixel errors.
- All 256 entrance countdown values: exact background pixels, with no empty
  eight-line band anywhere in the viewport.
- Prior identical-renderer check: 64 crowded scenes covering all four shields, eight fine phases and both
  buffers: zero pixel errors or glyph-allocation faults.
- Prior identical-renderer check: 1,168 artwork/edge/overlap/death scenes: zero pixel errors.
- 48 actual ANTIC raster samples: 2,064,384 pixels checked for missing/extra
  dark-blue scenery; zero errors. The bottom shield region is covered by the
  independent CPU compositor rather than this raster color check.
- 320 current cadence/stage checks pass. Cold boot and live controls were
  exercised during current capture. Warm/cold resets passed on the prior
  identical-runtime build.

The silent 20-second movie records the real cartridge in emulation. Explicit
stage-placement and invulnerability fixtures keep both full flocks on screen.
Test platform: stock 64 KiB NTSC 800XL in AltirraBridge with its built-in XL OS,
normal CPU, no VBXE or Rapidus. Physical hardware and PAL were not tested.

This is an 800XL playtest build; the published GitHub release is unchanged.
T1X's hand-drawn gameplay artwork and credits are retained.

Arcade background reference:
https://www.computerarcheology.com/Arcade/Phoenix/Code.html
