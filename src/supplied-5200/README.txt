PHOENIX — EXACT ATARI 5200 SPRITES FROM THE SUPPLIED GIFS

ARTWORK CREDIT
Hand-drawn Atari 5200 artwork by T1X.

The right-hand artwork is used. The left-hand 7800 examples are retained only
inside the original GIFs and full comparison frames for reference.

23 large-bird animation frames and four various-sprite animation frames were
decoded. The various GIF has multiple LEFT/RIGHT pairs: it must not be split
down its overall midpoint. Its 5200 small sprites are x=32..63, while the 5200
ship, shield and explosion are x=160..223. All crop bounds are in the manifest.

PRIMARY FILES
Phoenix5200-Large-Bird-Sprites.png: four columns of 96x32 capture-size cells;
read left to right, then down. All 23 original 5200 animation frames are retained. The last cell is padding.

Phoenix5200-Various-Sprites.png: four animation frames left to right. The first
seven rows are 32x32 small-pose cells. These occupy the left 128 pixels. The
ship row begins at y=224 (64x32 cells); shield at y=256 (64x64); explosion at
y=320 (64x64). The source order, including the position of the ship, is kept.

frames-5200/: every selected sprite frame as an individual lossless RGB PNG.
full-comparison-frames/: all 27 original composite frames, retaining both systems.
sources/: byte-identical original GIFs with short names.
sprite-manifest.json: source hashes, crop rectangles, palettes, frame timing,
native dimensions, atlas positions and pixel-exact verification results.

NO ARTWORK WAS REDRAWN, SMOOTHED, RECOLORED OR STRETCHED.
Black backgrounds, all colored pixels and each sprite's placement within its
original cell are retained. The primary PNGs keep the GIF's original dimensions.

PACKED DATA
Every 5200 crop lies exactly on a repeated 4x2 source-pixel grid and uses at
most four colors including black. packed-5200/ contains a lossless two-bit
encoding of that grid, both row order and 4x8 tile order. Palettes are per-frame
RGB lists in sprite-manifest.json; black is index zero. These are extracted
asset bytes, not a rebuilt game cartridge or inferred GTIA color-register map.

Large-bird data is 24x16 grid samples; small-pose data is 8x16; ship data is
16x16; shield/explosion data is 16x32. To reproduce the supplied GIF dimensions,
repeat every grid sample four times horizontally and twice vertically. This
step exactly recovers the source pixels; it is not an interpolating resize.

Both binary layouts were decoded and checked against every original RGB pixel.
All extracted frames and atlas placements passed with zero differing pixels.

REPRODUCE
Requires Python 3 and Pillow:
python3 extract_sprites.py --large-gif sources/big-bird-32.gif --various-gif sources/various3.gif --out rebuilt

The displayed GIF delays are retained as metadata (large-bird: 100 ms/frame;
various: 200 ms/frame). Game animation cadence is a separate implementation choice.
