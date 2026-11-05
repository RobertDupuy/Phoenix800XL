"""Compile clean presentation pages from native gameplay sprites and HUD glyphs.

A page keeps one character set for its entire visible area. Display interrupts
change only palettes; no visible character row depends on a font-bank deadline.
"""
from pathlib import Path
import json

R = Path(__file__).resolve().parents[1]
A = R / 'src/arcade-assets'
B = R / 'build'
WIDTH, HEIGHT = 160, 192
SMALL = [0, 14, 44, 90]
LARGE = [0, 172, 44, 134]
BOSS = [0, 26, 44, 90]
BASE = [14, 44, 90, 168]
START_ROWS = [0, 4, 8, 12, 16, 19, 21]


def pack_fonts(pages, palettes):
    fonts, maps, font_tables, counts = [], bytearray(), [], []
    for page, palette in zip(pages, palettes):
        # Palette changes run across these two intentionally empty scanlines.
        for band in range(1, len(START_ROWS)):
            if palette[band] != palette[band-1]:
                y = START_ROWS[band] * 8
                assert not any(page[y-1]) and not any(page[y]), ('palette boundary', y)
        tiles, page_map = [bytes(8)], bytearray()
        for row in range(24):
            band = max(i for i, start in enumerate(START_ROWS) if start <= row)
            colors = palette[band]
            for col in range(40):
                block = [line[col*4:col*4+4] for line in page[row*8:row*8+8]]
                has3 = any(colors[2] in line for line in block)
                has4 = any(colors[3] in line for line in block)
                assert not (has3 and has4), (row, col, 'mixed ANTIC alternate color')
                flag = 128 if has4 else 0
                lookup = {0: 0, colors[0]: 1, colors[1]: 2, (colors[3] if flag else colors[2]): 3}
                tile = bytes(sum(lookup[v] << (6-x*2) for x, v in enumerate(line)) for line in block)
                if tile not in tiles:
                    tiles.append(tile)
                page_map.append(tiles.index(tile) | flag)
        counts.append(len(tiles))
        assert len(tiles) <= 128, ('page needs too many glyphs', len(counts)-1, len(tiles))
        font = b''.join(tiles) + bytes((128-len(tiles))*8)
        fonts.append(font)
        font_tables.extend([0x10 + (len(fonts)-1)*4] * len(START_ROWS))
        if maps:
            maps.extend(bytes(64))
        maps.extend(page_map)
    all_palettes = palettes[0] + palettes[1]
    maps[960:1016] = bytes(p[k] for k in range(4) for p in all_palettes)
    raw, packed, i = b''.join(fonts), bytearray(), 0
    while i < len(raw):
        n = 1
        while i+n < len(raw) and raw[i+n] == raw[i] and n < 128:
            n += 1
        if n >= 3:
            packed.extend([127+n, raw[i]])
            i += n
        else:
            start = i
            i += n
            while i < len(raw) and i-start < 128:
                n = 1
                while i+n < len(raw) and raw[i+n] == raw[i] and n < 128:
                    n += 1
                if n >= 3 or i+n-start > 128:
                    break
                i += n
            packed.append(i-start-1)
            packed.extend(raw[start:i])
    (B/'intro-fonts.bin').write_bytes(raw)
    (B/'intro-fonts-packed.bin').write_bytes(packed)
    (B/'intro-maps.bin').write_bytes(maps)
    (B/'intro-font-table.bin').write_bytes(bytes(font_tables))
    return dict(unique_rom_fonts=len(fonts), glyphs_per_page=counts, font_bytes=len(raw),
                packed_font_bytes=len(packed), map_bytes=len(maps))


def prepare():
    native = json.loads((B/'sprite-manifest.json').read_text())
    poses = {p['shape']: p['pixels'] for p in native['poses']}
    large = json.loads((B/'flight-art.json').read_text())['frames']
    boss_glyphs = (B/'boss-glyphs.bin').read_bytes()
    hud = (A/'hud-glyphs.bin').read_bytes()
    title = [[0]*WIDTH for _ in range(HEIGHT)]
    scores = [[0]*WIDTH for _ in range(HEIGHT)]
    copies, text_runs = [], []

    def stamp(page, pixels, x, y, palette, source):
        copies.append(dict(page='title' if page is title else 'scores', source=source,
                           x=x, y=y, pixels=pixels, palette=palette))
        for yy, line in enumerate(pixels):
            for xx, value in enumerate(line):
                if value:
                    assert 0 <= x+xx < WIDTH and 0 <= y+yy < HEIGHT, (source, 'clipped')
                    assert page[y+yy][x+xx] == 0, (source, 'overlap', x+xx, y+yy)
                    page[y+yy][x+xx] = palette[value]

    code_map = {**{chr(65+i): 1+i for i in range(26)}, **{str(i): 32+i for i in range(10)},
                ' ': 0, '-': 43, '.': 42, '*': 31, ':': 44}

    def text(page, value, x, y, color=168):
        assert x >= 0 and x+len(value)*6 <= WIDTH and y >= 0 and y+8 <= HEIGHT, value
        text_runs.append(dict(page='title' if page is title else 'scores', text=value, x=x, y=y, color=color))
        for i, char in enumerate(value):
            code = code_map[char]
            for yy in range(8):
                for xx in range(6):
                    byte = hud[code*32+(xx//4)*8+yy]
                    if (byte >> (6-(xx%4)*2)) & 3:
                        assert page[y+yy][x+i*6+xx] == 0, (value, 'text overlap')
                        page[y+yy][x+i*6+xx] = color

    def centered(page, value, y, color=168):
        # Start on a cell boundary so repeated words reuse identical glyphs.
        text(page, value, ((WIDTH-len(value)*6)//8)*4, y, color)

    for page in (title, scores):
        text(page, 'SCORE1', 8, 0)
        text(page, 'HI-SCORE', 56, 0)
        text(page, 'SCORE2', 116, 0)
        for x in (8, 62, 116):
            text(page, '000000', x, 8, 90)
        text(page, 'COIN00', 60, 16)
        centered(page, 'PHOENIX COPYRIGHT 1980', 168)
        centered(page, 'AMSTAR ELECTRONICS CORP.', 176)
        centered(page, 'PHOENIX T.M. U.S.A.', 184)

    # Use a flying gameplay pose with a visible head, body and spread wing.
    letters = {
        'P': ['111', '101', '111', '100', '100'],
        'H': ['101', '101', '111', '101', '101'],
        'O': ['111', '101', '101', '101', '111'],
        'E': ['111', '100', '110', '100', '111'],
        'N': ['1001', '1101', '1011', '1001', '1001'],
        'I': ['1']*5,
        'X': ['101', '101', '010', '101', '101'],
    }
    bird = poses[80]
    left = min(x for line in bird for x, v in enumerate(line) if v)
    cursor = 1
    for char in 'PHOENIX':
        rows = letters[char]
        for row, line in enumerate(rows):
            for col, value in enumerate(line):
                if value == '1':
                    stamp(title, bird, cursor+col*7-left, 64+row*12, SMALL,
                          dict(kind='small', shape=80, letter=char))
        cursor += len(rows[0])*7+3

    # The logo area contains only its bird sprites, including N-I-X gaps.
    stars = json.loads((A/'stars-irregular.json').read_text())['cells']
    for row, col in stars:
        y, x = row*8+3, col*4
        if 32 <= y < 160 and not (56 <= y < 128):
            assert title[y][x] == 0
            title[y][x] = 168

    centered(scores, 'INSERT 1 COIN', 32)
    centered(scores, '* 1 PLAYER  1 COIN *', 48)
    centered(scores, '* 2 PLAYERS 2 COINS *', 64)
    centered(scores, 'SCORE AVERAGE TABLE', 88)
    text(scores, '20 40 80', 52, 104, 90)
    text(scores, '200', 52, 120, 90)
    text(scores, '50 100 100-800', 52, 136, 90)
    text(scores, '1000-9000', 52, 160, 90)
    stamp(scores, poses[36], 24, 104, SMALL, dict(kind='small', shape=36))
    stamp(scores, poses[220], 20, 112, SMALL, dict(kind='small', shape=220))
    stamp(scores, poses[204], 28, 112, SMALL, dict(kind='small', shape=204))
    stamp(scores, large[40], 12, 134, LARGE, dict(kind='large', pose=40))
    pilot = [[0]*8 for _ in range(16)]
    for cx, codes in enumerate([[0x74, 0x7c], [0x75, 0x7d]]):
        for cy, code in enumerate(codes):
            for y, byte in enumerate(boss_glyphs[code*8:code*8+8]):
                for x in range(4):
                    pilot[cy*8+y][cx*4+x] = (byte >> (6-x*2)) & 3
    stamp(scores, pilot, 24, 152, BOSS, dict(kind='pilot', tiles=[0x74, 0x7c, 0x75, 0x7d]))
    title_palette = [BASE[:] for _ in START_ROWS]
    score_palette = [BASE[:] for _ in START_ROWS]
    score_palette[4] = [172, 44, 134, 90]
    score_palette[5] = [26, 44, 90, 168]
    score_palette[6] = score_palette[5][:]
    info = pack_fonts([title, scores], [title_palette, score_palette])
    info.update(pages=['native-sprite PHOENIX title', 'native-sprite score table'],
                startup_font_ram=[4096, 4096+info['font_bytes']],
                sprite_method='Unscaled gameplay pixels; explicit text from native HUD glyphs',
                title_shape=80, title_birds=sum(c['page']=='title' for c in copies),
                band_start_rows=START_ROWS, colors=[title_palette, score_palette],
                font_switches_during_visible_page=0)
    (B/'intro-art-manifest.json').write_text(json.dumps(dict(**info, sprite_copies=copies,
                                                           text_runs=text_runs, pages_pixels=[title, scores])))
    manifest = json.loads((B/'art-manifest.json').read_text())
    manifest.update(info)
    (B/'art-manifest.json').write_text(json.dumps(manifest, indent=2))
    print('Startup:', info['title_birds'], 'native title birds;', info['glyphs_per_page'],
          'glyphs/page;', info['packed_font_bytes'], 'packed bytes')


if __name__ == '__main__':
    prepare()
