"""Execute actual small-bird death/respawn instructions in CPU fixtures.

The v0.19 regression fell through from arcade_resume into player_update because
the initializer occupies a different ROM section. Surviving attackers stayed
at the next ship's location. These fixtures place survivors at that location,
run the complete death delay, and check the reset and first live collision ticks.
No emulator display timing or physical hardware is simulated.
"""
from cpu_model import Model, R, S
import hashlib
import json
import sys

sys.path.insert(0, str(R / 'tools'))
from prepare_native import tables
from scene_oracle import scene

original = tables()
positions = original['alien_position_layout_page']
pointers = original['alien_position_pointer_table']


def check_render(t):
    m = t.m.b
    m[S['front_buffer']] ^= 1
    t.call('render_scene')
    base = 0x2800 + m[S['back_buffer']] * 0x400
    font = 0x2000 + m[S['back_buffer']] * 0x400
    actual = bytearray()
    for yy in range(200):
        for cell in range(40):
            ch = m[base + yy // 8 * 32 + cell - 4] if 4 <= cell < 36 else 0
            p = m[font + (ch & 127) * 8 + yy % 8]
            actual.extend(4 if v == 3 and ch & 128 else v
                          for v in (p >> 6, p >> 4 & 3, p >> 2 & 3, p & 3))
    assert actual == scene(m).tobytes(), 'stale or incorrect small-bird pixels'
    assert m[S['layout_faults']] == 0


t = Model()
t.init()
m = t.m.b
cases = pixels = live_checks = 0
for round_number in range(16):
    for stage in (1, 2):
        for survivors in range(17):
            wave = round_number * 5 + stage
            m[S['wave']] = wave
            t.call('wave_reset')
            m[S['state']] = 1
            m[S['lives']] = 3
            m[S['aliens_left']] = survivors
            # A scattered surviving flock, with every attacker near the ship.
            m[S['enemy_on']:S['enemy_on']+16] = bytes(
                int((i * 5) % 16 < survivors) for i in range(16))
            m[S['raw_enemy_x']:S['raw_enemy_x']+16] = bytes([100] * 16)
            m[S['raw_enemy_y']:S['raw_enemy_y']+16] = bytes([208] * 16)
            m[S['pattern_lo']:S['pattern_lo']+16] = bytes([37] * 16)
            m[S['pattern_hi']:S['pattern_hi']+16] = bytes([18] * 16)
            m[S['sched_phase']:S['sched_phase']+20] = bytes([7] * 20)
            m[S['fast_aliens']] = 1
            m[S['score_digits']:S['score_digits']+6] = bytes([0, 1, 2, 3, 4, 0])
            score = bytes(m[S['score_digits']:S['score_digits']+6])
            t.call('player_update')
            t.call('latch_aliens')
            render_case = round_number == 0 and survivors in (0, 1, 4, 16)
            if render_case:
                # Populate both real buffers before death to test old footprints.
                for _ in range(2):
                    check_render(t)
                    pixels += 1
            m[S['shot_on']] = m[S['second_on']] = 1
            m[S['bomb_on']:S['bomb_on']+5] = bytes([1] * 5)
            t.call('damage_player')
            assert m[S['state']] == 3
            for _ in range(96):
                t.call('game_tick_regular')
            assert m[S['state']] == 4 and m[S['lives']] == 2
            for _ in range(129):
                t.call('game_tick_regular')
                assert m[S['state']] == 4
            t.call('game_tick_regular')
            assert m[S['state']] == 1 and m[S['lives']] == 2
            assert m[S['wave']] == wave and m[S['aliens_left']] == survivors
            assert bytes(m[S['score_digits']:S['score_digits']+6]) == score
            assert m[S['level_round']] == (round_number << 4) | (stage * 2 - 1)
            assert m[S['invuln']] == 0
            assert m[S['shot_on']] == m[S['second_on']] == 0
            assert not any(m[S['bomb_on']:S['bomb_on']+5])
            assert not any(m[S['sched_phase']:S['sched_phase']+20])
            assert m[S['fast_aliens']] == 0
            expected_on = bytes([1] * survivors + [0] * (16 - survivors))
            assert bytes(m[S['enemy_on']:S['enemy_on']+16]) == expected_on
            assert bytes(m[S['display_enemy_on']:S['display_enemy_on']+16]) == expected_on
            offset = pointers[(m[S['level_round']] >> 1) & 15]
            expected = positions[offset:offset+32]
            assert bytes(m[S['raw_enemy_x']:S['raw_enemy_x']+16]) == expected[::2]
            assert bytes(m[S['raw_enemy_y']:S['raw_enemy_y']+16]) == expected[1::2]
            for live, display in [('raw_enemy_x', 'display_enemy_x'),
                                  ('raw_enemy_y', 'display_enemy_y'),
                                  ('enemy_shape', 'display_enemy_shape')]:
                assert m[S[live]:S[live]+16] == m[S[display]:S[display]+16]
            assert bytes(m[S['pattern_lo']:S['pattern_lo']+16]) == bytes(16)
            assert bytes(m[S['pattern_hi']:S['pattern_hi']+16]) == bytes([16] * 16)
            assert bytes(m[S['enemy_kind']:S['enemy_kind']+16]) == bytes([1] * 16)
            assert bytes(m[S['enemy_shape']:S['enemy_shape']+16]) == bytes([32] * 16)
            if render_case:
                for _ in range(3):
                    check_render(t)
                    pixels += 1
            t.call('alien_body_collision')
            assert m[S['state']] == 1 and m[S['lives']] == 2, (wave, survivors)
            live_checks += 1
            if survivors:
                for _ in range(8):
                    t.call('game_tick_regular')
                    assert m[S['state']] == 1 and m[S['lives']] == 2, (wave, survivors)
                    live_checks += 1
            cases += 1

report = dict(car_sha256=hashlib.sha256((R/'build/Phoenix800XL.car').read_bytes()).hexdigest(),
              method=__doc__, death_and_respawn_cases=cases, rounds=16,
              small_bird_waves=2, survivor_counts=list(range(17)),
              exact_original_formation_matches=cases, rendered_buffer_checks=pixels,
              pixel_errors=0, immediate_collision_checks=live_checks,
              added_invulnerability=False, score_wave_and_survivors_preserved=True,
              payload_bytes=262144)
out = R / 'evidence/v020'
out.mkdir(parents=True, exist_ok=True)
(out/'small-respawn.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
