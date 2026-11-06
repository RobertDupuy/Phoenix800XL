"""Compile clean presentation pages from native gameplay sprites and HUD glyphs.

A page keeps one character set for its entire visible area. Display interrupts
change only palettes; no visible character row depends on a font-bank deadline.
"""
from pathlib import Path
import json
import supplied_art as supplied

R = Path(__file__).resolve().parents[1]
A = R / 'src/arcade-assets'
B = R / 'build'
WIDTH, HEIGHT = 160, 192
SMALL = [0, 14, 44, 90]
LARGE = [0, 170, 236, 86]
BOSS = [0, 170, 100, 102]
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

    # Letter positions are based on occupied source pixels, not padded cells.
    # One blank native column separates adjacent bird sprites inside letters.
    # Three blank columns separate letters on the main line. P rises above H/O.
    title_placements = []
    logo = [[0]*92 for _ in range(72)]
    def logo_bird(shape, x, y):
        pixels=poses[shape]
        occupied=[(xx,yy) for yy,line in enumerate(pixels) for xx,v in enumerate(line) if v]
        x0=min(p[0] for p in occupied);y0=min(p[1] for p in occupied)
        title_placements.append(dict(shape=shape,x=x,y=y,source_trim=[x0,y0]))
        for xx,yy in occupied:
            dx=x+xx-x0;dy=y+yy-y0
            assert 0<=dx<92 and 0<=dy<72
            assert logo[dy][dx]==0,('title birds overlap',shape,x,y)
            logo[dy][dx]=pixels[yy][xx]
    for y in range(0,72,8):logo_bird(36,0,y)
    for y in (0,16):
        for x in (8,16):logo_bird(36,x,y)
        logo_bird(72,24,y)
    logo_bird(36,24,8)
    for y in range(32,72,8):
        for x in (10,18,24,32,38,52,64,70):logo_bird(72,x,y)
    for x,y in ((14,48),(28,32),(28,64)):logo_bird(72,x,y)
    for y in (32,48,64):logo_bird(36,42,y)
    for x,y,shape in ((55,40,80),(57,48,80),(59,56,84)):logo_bird(shape,x,y)
    for x in (76,88):
        for y in (32,64):logo_bird(72,x,y)
    for x,y,shape in ((76,40,80),(84,40,82),(76,56,86),(84,56,84)):logo_bird(shape,x,y)
    logo_bird(36,80,48)
    stamp(title,logo,34,40,[0,14,90,202],dict(kind='gameplay-bird-title',placements=title_placements))
    # Actual 32-by-16 gameplay frame: no height enlargement.
    stamp(title, large[40], 64, 134, LARGE, dict(kind='large', pose=40))

    centered(scores, 'INSERT 1 COIN', 32)
    centered(scores, '* 1 PLAYER  1 COIN *', 48)
    centered(scores, '* 2 PLAYERS 2 COINS *', 64)
    centered(scores, 'SCORE AVERAGE TABLE', 88)
    text(scores, '20 40 80', 52, 104, 90)
    text(scores, '200', 52, 120, 90)
    text(scores, '50 100 100-800', 52, 136, 14)
    text(scores, '1000-9000', 52, 160, 102)
    stamp(scores, poses[36], 24, 104, SMALL, dict(kind='small', shape=36))
    stamp(scores, poses[204], 24, 112, SMALL, dict(kind='small', shape=204))
    stamp(scores, large[40], 12, 134, LARGE, dict(kind='large', pose=40))
    pilot = supplied.pixels('small-pose-row-06',2).tolist()
    stamp(scores, pilot, 24, 152, BOSS, dict(kind='pilot', source_group='small-pose-row-06', frame=2))
    title_palette = [[14,90,202,168] for _ in START_ROWS]
    for i in (4,5,6): title_palette[i] = [170,236,86,168]
    score_palette = [BASE[:] for _ in START_ROWS]
    score_palette[4] = [170, 236, 86, 14]
    score_palette[5] = [170, 100, 102, 168]
    score_palette[6] = score_palette[5][:]
    info = pack_fonts([title, scores], [title_palette, score_palette])
    info.update(pages=['native-sprite PHOENIX title', 'native-sprite score table'],
                startup_font_ram=[4096, 4096+info['font_bytes']],
                sprite_method='Unscaled gameplay pixels; explicit text from native HUD glyphs',
                title_shape='mixed gameplay poses', title_birds=len(title_placements),
                title_placements=title_placements, title_large_frame=40, title_large_size=[32,16],
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
