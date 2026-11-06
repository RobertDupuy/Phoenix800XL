"""CPU regression for the real mothership shot path; explicit synthetic fixtures."""
from cpu_model import Model, S, R
import hashlib
import json


def fixture(positions=((80, 144), (144, 144))):
    t = Model()
    t.init()
    m = t.m.b
    m[S['wave']] = 5
    t.call('wave_reset')
    m[S['state']] = 1
    m[S['boss_status']] = 2
    m[S['boss_entrance_shown']] = 0
    m[S['boss_scroll']] = 248
    m[S['boss_body']:S['boss_body']+234] = bytes(234)
    m[S['enemy_on']:S['enemy_on']+16] = bytes([1]*len(positions) + [0]*(16-len(positions)))
    m[S['aliens_left']] = len(positions)
    m[S['invuln']] = 0
    for i, (x, y) in enumerate(positions):
        m[S['raw_enemy_x']+i] = x
        m[S['raw_enemy_y']+i] = y
        m[S['enemy_kind']+i] = 1
        m[S['enemy_shape']+i] = 32
    t.call('prepare_shot_bounds')
    t.call('refresh_alien_screen')
    t.call('latch_aliens')
    return t, m


def shoot(t, m, x, y):
    m[S['shot_on']] = 1
    m[S['raw_shot_x']] = x
    m[S['raw_shot_y']] = y+8
    t.call('player_shots')


checks = []
for slot, x in enumerate([80, 144]):
    t, m = fixture()
    shoot(t, m, x, 144)
    assert m[S['enemy_on']+slot] == 0
    assert m[S['display_enemy_on']+slot] == 0
    assert m[S['enemy_on']+1-slot] == 1
    assert m[S['aliens_left']] == 1 and m[S['shot_on']] == 0
    assert m[S['burst_count']] == 12 and m[S['audio_hit_pending']] == 1
    for _ in range(12):
        t.call('burst_tick')
        t.call('score_service')
    assert int(''.join(str(v) for v in m[S['score_digits']:S['score_digits']+6])) == 20
    checks.append('shot kills escort slot '+str(slot)+' and awards 20 once')

t, m = fixture()
shoot(t, m, 64, 144)
assert list(m[S['enemy_on']:S['enemy_on']+2]) == [1, 1] and m[S['shot_on']] == 1
checks.append('misses remain misses')

for state in [1, 3, 4]:
    t, m = fixture()
    m[S['boss_status']] = state
    shoot(t, m, 80, 144)
    assert m[S['aliens_left']] == 2 and m[S['shot_on']] == 1
checks.append('hidden escorts cannot be hit during entry or victory')

t, m = fixture(((80, 88), (144, 88)))
armor = S['boss_body']+4*26+9
m[armor] = 79
shoot(t, m, 80, 88)
assert m[S['enemy_on']] == 0 and m[armor] == 79
checks.append('foreground escort absorbs shot before armor behind it')

t, m = fixture(((80, 88), (144, 88)))
armor = S['boss_body']+4*26+12
m[armor] = 79
shoot(t, m, 104, 88)
t.call('boss_play')
assert m[armor] == 78 and m[S['shot_on']] == 0 and m[S['aliens_left']] == 2
checks.append('unobstructed shot damages armor exactly once')

t, m = fixture()
shoot(t, m, 80, 144)
shoot(t, m, 144, 144)
assert m[S['aliens_left']] == 0
t.call('boss_play')
t.call('score_service')
assert m[S['aliens_left']] == 0 and m[S['burst_count']] > 0
ticks = 0
while not m[S['aliens_left']] and ticks < 100:
    t.call('boss_play')
    t.call('score_service')
    ticks += 1
assert m[S['aliens_left']] == S['escort_population'] and ticks >= 20
assert int(''.join(str(v) for v in m[S['score_digits']:S['score_digits']+6])) == 40
assert m[S['wave']] == 5 and m[S['boss_status']] == 2
checks.append('both hit animations and awards finish before five escorts replenish')

t, m = fixture(tuple((16+i*32,144) for i in range(5)))
shoot(t,m,144,144)
assert m[S['enemy_on']+4] == 0 and m[S['aliens_left']] == 4
assert list(m[S['enemy_on']:S['enemy_on']+4]) == [1]*4
checks.append('the added fifth escort is hittable and leaves the other four alive')

report = dict(car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),
              method=__doc__, checks=checks, replenishment_wait_ticks=ticks)
out = R/'evidence/v013'
out.mkdir(parents=True, exist_ok=True)
(out/'escort-collision.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
