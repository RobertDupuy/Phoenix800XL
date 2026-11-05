"""Check actual Altirra raster captures, including repeated title/score changes.

Cold boot with the original BIOS and physical fire input. No game-memory writes.
The image check covers the final emulator output, not just generated font bytes.
"""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import numpy as np
from PIL import Image
from play_campaign import Frontend

R = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument('--exe', type=Path, required=True)
p.add_argument('--out', type=Path, required=True)
p.add_argument('--record', action='store_true')
args = p.parse_args()
out = args.out.resolve()
e = Frontend(out, args.exe.resolve(), args.record)
symbols = json.loads((R/'build/symbols.json').read_text())
manifest = json.loads((R/'build/intro-art-manifest.json').read_text())
captures = []
last = None
try:
    while len(captures) < 4:
        m = e.step(0, 16)
        page = m[symbols['intro_page']]
        if page != last:
            # Capture after a full settled frame, not on the transition itself.
            e.step(0, 16)
            name = ('title' if page == 0 else 'scores') + ('-repeat' if len(captures) >= 2 else '') + '.png'
            e.a.screenshot(path=str(out/name))
            captures.append(dict(page=page, file=name, frame=e.frames))
            last = page
    for i in range(100):
        m = e.step(4 if i%2 else 0)
    assert m[symbols['state']] == 1 and m[symbols['wave']] == 1
    e.a.screenshot(path=str(out/'gameplay.png'))
finally:
    e.close()

histograms = collections.defaultdict(collections.Counter)
arrays = []
for capture in captures:
    actual = np.asarray(Image.open(out/capture['file']).convert('RGB'))[16:208, 8:328]
    expected = np.repeat(np.asarray(manifest['pages_pixels'][capture['page']], dtype=np.uint8), 2, axis=1)
    mask_errors = int(np.count_nonzero((actual.max(axis=2)>0) != (expected>0)))
    assert mask_errors == 0, (capture['file'], 'missing or stray pixels', mask_errors)
    for code in np.unique(expected):
        colors, counts = np.unique(actual[expected==code], axis=0, return_counts=True)
        for color, count in zip(colors, counts):
            histograms[int(code)][tuple(map(int, color))] += int(count)
    arrays.append((capture, actual, expected))
palette = {code: counter.most_common(1)[0][0] for code, counter in histograms.items()}
assert palette[0] == (0, 0, 0)
assert len(set(palette.values())) == len(palette), 'different GTIA colors collapsed'
for capture, actual, expected in arrays:
    rgb = np.zeros_like(actual)
    for code, color in palette.items():
        rgb[expected==code] = color
    errors = int(np.count_nonzero(np.any(actual != rgb, axis=2)))
    assert errors == 0, (capture['file'], 'inconsistent color pixels', errors)

required = {'INSERT 1 COIN', '* 1 PLAYER  1 COIN *', '* 2 PLAYERS 2 COINS *',
            '20 40 80', '200', 'PHOENIX COPYRIGHT 1980'}
assert required <= {run['text'] for run in manifest['text_runs']}
assert manifest['font_switches_during_visible_page'] == 0
report = dict(car_sha256=e.car_sha256, method=__doc__, captures=captures,
              compared_pixels=len(captures)*320*192, missing_or_stray_pixels=0,
              inconsistent_color_pixels=0, rgb_palette=palette, started_game=True,
              title_pose=manifest['title_shape'], title_birds=manifest['title_birds'])
(out/'report.json').write_text(json.dumps(report, indent=2))
evidence = R/'evidence/v013'
evidence.mkdir(parents=True, exist_ok=True)
(evidence/'presentation-raster.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
