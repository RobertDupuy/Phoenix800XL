"""Execute real death/respawn code in the 6502 ROM; fixtures, not live gameplay.

Arcade reference: $0BA0 resets the large-bird scroll after a death; $32B0
rebuilds BirdsLeft records from the tail of $3F80/$3FC0, as starting eggs.
"""
from cpu_model import Model, R, S
import hashlib
import json
import sys
import numpy as np

sys.path.insert(0, str(R/'tools'))
from prepare_native import tables

original = tables()['bird_data_alt_page']
art = json.loads((R/'build/flight-art.json').read_text())

def decode(m):
    out = np.zeros((200, 160), dtype=np.uint8)
    b = m[S['back_buffer']]
    for row in range(25):
        font = [0x1800, 0x2000, 0x3000][min(row//8, 2)] + b*1024
        for col in range(32):
            code = m[0x2800+b*1024+row*32+col]
            for y in range(8):
                byte = m[font+(code&127)*8+y]
                for x in range(4):
                    v = byte >> (6-2*x) & 3
                    out[row*8+y, (col+4)*4+x] = 4 if v == 3 and code&128 else v
    return out

def expected_eggs(m):
    out = np.zeros((200, 160), dtype=np.uint8)
    frames = art['second_palette_frames' if m[S['large_mode']] == 2 else 'frames']
    for i in range(8):
        if not m[S['enemy_on']+i]:
            continue
        xx = m[S['large_x']+i]
        xx = 28 + (xx-256 if xx >= 232 else xx)//2
        yy = m[S['large_y']+i]
        for y, row in enumerate(frames[m[S['large_pose']+i]]):
            for x, v in enumerate(row):
                dy = (yy+y)&255
                if v and 32 <= dy < 232 and 28 <= xx+x < 132:
                    out[dy-32, xx+x] = v
    return out

t = Model()
t.init()
m = t.m.b
cases = pixels = live_checks = 0
for round_number in range(16):
    for stage in (3, 4):
        for survivors in range(S['large_population']+1):
            wave = round_number*5 + stage
            m[S['wave']] = wave
            t.call('wave_reset')
            m[S['state']] = 1
            m[S['lives']] = 3
            m[S['aliens_left']] = survivors
            m[S['bird_scroll']] = (176+round_number*3)&255
            m[S['bird_records']:S['bird_records']+64] = bytes([15, 73, 224, 2, 64, 100, 16, 120])*8
            m[S['large_y']:S['large_y']+8] = bytes([208])*8
            m[S['large_left']:S['large_left']+8] = bytes([90])*8
            m[S['large_right']:S['large_right']+8] = bytes([120])*8
            score = bytes(m[S['score_digits']:S['score_digits']+6])
            t.call('damage_player')
            assert m[S['state']] == 3
            for _ in range(96):
                t.call('game_tick_regular')
            assert m[S['state']] == 4 and m[S['lives']] == 2
            for _ in range(129):
                t.call('game_tick_regular')
                assert m[S['state']] == 4
            # Poison both old screen maps: neither may survive the next render.
            m[0x2800:0x3000] = bytes([127])*2048
            m[S['large_buffer']:S['large_buffer']+2] = bytes([1, 1])
            m[S['shot_on']] = m[S['second_on']] = 1
            m[S['bomb_on']:S['bomb_on']+5] = bytes([1])*5
            t.call('game_tick_regular')
            assert m[S['state']] == 1 and m[S['lives']] == 2
            assert m[S['wave']] == wave and m[S['aliens_left']] == survivors
            assert bytes(m[S['score_digits']:S['score_digits']+6]) == score
            assert m[S['invuln']] == 0
            assert m[S['bird_scroll']] == m[S['bird_frame']] == 0
            offset = (stage-3)*64 + (8-survivors)*8
            expected = bytes((8-survivors)*8) + bytes(original[offset:offset+survivors*8])
            assert bytes(m[S['bird_records']:S['bird_records']+64]) == expected
            assert list(m[S['enemy_on']:S['enemy_on']+8]) == [0]*(8-survivors)+[1]*survivors
            assert not any(m[S['large_left']:S['large_left']+16])
            assert not any(m[S['large_buffer']:S['large_buffer']+2])
            assert m[S['shot_on']] == m[S['second_on']] == 0
            assert not any(m[S['bomb_on']:S['bomb_on']+5])
            if round_number == 0:
                expected_image = expected_eggs(m)
                for _ in range(3):
                    m[S['front_buffer']] ^= 1
                    t.call('render_scene')
                    assert np.array_equal(decode(m), expected_image), (stage, survivors, 'stale pixels')
                    assert not m[S['layout_faults']]
                    pixels += 1
            if survivors:
                for _ in range(4):
                    t.call('game_tick_regular')
                    assert m[S['state']] == 1 and m[S['lives']] == 2, (wave, survivors, 'immediate death')
                    live_checks += 1
            cases += 1

report = dict(car_sha256=hashlib.sha256((R/'build/Phoenix800XL.car').read_bytes()).hexdigest(),
              method=__doc__, death_and_respawn_cases=cases, rounds=16, large_bird_waves=2,
              survivor_counts=list(range(S['large_population']+1)), exact_original_record_matches=cases,
              rendered_buffer_checks=pixels, pixel_errors=0,
              immediate_collision_checks=live_checks, added_invulnerability=False,
              score_and_wave_preserved=True, payload_bytes=262144)
out = R/'evidence/v019'
out.mkdir(parents=True, exist_ok=True)
(out/'respawn.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
