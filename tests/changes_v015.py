"""Execute the new rules in the built 6502 ROM. Fixtures are synthetic, not gameplay."""
from cpu_model import Model, S, R
import hashlib
import json

checks = []


def fixture(wave=1):
    t = Model()
    t.init()
    m = t.m.b
    m[S['wave']] = wave
    t.call('wave_reset')
    m[S['state']] = 1
    m[S['invuln']] = 0
    m[S['video_ship_x']] = 100
    t.call('player_update')
    return t, m


def score(m):
    return int(''.join(str(v) for v in m[S['score_digits']:S['score_digits']+6]))


def escort_fixture():
    t, m = fixture(5)
    assert m[S['aliens_left']] == 4
    assert list(m[S['enemy_on']:S['enemy_on']+16]) == [1]*4+[0]*12
    m[S['boss_status']] = 2
    m[S['boss_entrance_shown']] = 0
    m[S['boss_scroll']] = 248
    m[S['boss_body']:S['boss_body']+234] = bytes(234)
    for i, x in enumerate([48, 80, 144, 176]):
        m[S['raw_enemy_x']+i] = x
        m[S['raw_enemy_y']+i] = 144
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


# Initial and replacement populations use all four collision/render slots.
for slot, x in enumerate([48, 80, 144, 176]):
    t, m = escort_fixture()
    shoot(t, m, x, 144)
    assert m[S['enemy_on']+slot] == m[S['display_enemy_on']+slot] == 0
    assert sum(m[S['enemy_on']:S['enemy_on']+4]) == 3
    assert m[S['aliens_left']] == 3 and m[S['shot_on']] == 0
    for _ in range(16):
        t.call('burst_tick')
        t.call('score_service')
    assert score(m) == 20
checks.append('all four escorts are shootable and award 20 exactly once')

t, m = escort_fixture()
for x in [48, 80, 144]:
    shoot(t, m, x, 144)
    for _ in range(16):
        t.call('burst_tick')
        t.call('score_service')
shoot(t, m, 176, 144)
assert m[S['aliens_left']] == 0 and score(m) == 60
wait = 0
while not m[S['aliens_left']] and wait < 100:
    t.call('boss_play')
    t.call('score_service')
    wait += 1
assert m[S['aliens_left']] == 4 and wait >= 20
assert score(m) == 80 and m[S['fast_aliens']] == 0
assert list(m[S['enemy_on']:S['enemy_on']+16]) == [1]*4+[0]*12
checks.append('four escorts replenish after the last hit/award, at normal speed')

for wave, population, expected in [(5,4,0),(5,3,0),(5,2,1),(5,1,1),(1,5,0),(1,4,1),(2,4,1)]:
    t, m = fixture(wave)
    m[S['aliens_left']] = population
    m[S['main_phase']] = m[S['fast_aliens']] = 0
    t.call('arcade_step')
    assert m[S['fast_aliens']] == expected, (wave, population)
checks.append('boss fast movement starts at 2; ordinary small-wave threshold stays 5')

# Every playable ship X, every visible bird X, and every fine-X phase.
t, m = fixture()
cases = 0
for sx in range(12, 193):
    m[S['raw_ship_x']] = sx
    for x in range(208):
        m[S['raw_enemy_x']] = x
        m[S['raw_enemy_y']] = 231
        m[S['axcmp']] = 232
        m[S['aycmp']] = x
        t.c.x = 0
        t.call('safe_small_entry')
        actual = m[S['raw_enemy_x']]
        if -48 <= x-sx < 48:
            assert abs(actual-sx) >= 64 and actual % 8 == x % 8
        else:
            assert actual == x
        assert m[S['raw_enemy_y']] == 231
        cases += 1
for oldx, oldy, x, y, move in [
    (208,208,207,208,True), (255,208,0,208,True),
    (80,232,80,231,True), (80,232,80,184,True),
    (80,232,80,183,False), (80,233,80,232,False),
    (80,221,80,220,False), (80,231,80,230,False),
    (208,140,207,140,False), (208,208,208,208,False),
]:
    sx = min(192,max(12,x))
    m[S['raw_ship_x']] = sx
    m[S['raw_enemy_x']] = x
    m[S['raw_enemy_y']] = y
    m[S['aycmp']] = oldx
    m[S['axcmp']] = oldy
    t.c.x = 0
    t.call('safe_small_entry')
    assert (m[S['raw_enemy_x']] != x) == move, (oldx,oldy,x,y)
checks.append(f'{cases} bottom-entry combinations: clear lane for every ship X; fine phase preserved')
checks.append('near-ship side returns protected; existing visible dives and high entries untouched')

# Exercise the real movement routine, then its real player collision routine.
vectors = t.m[S['alien_direction_vectors']:S['alien_direction_vectors']+256]
cluster = t.m[S['alien_movement_cluster_a']:S['alien_movement_cluster_a']+4096]
pattern = next(i for i,v in enumerate(cluster) if v < 64 and 248 <= vectors[v*2+1] <= 255)
direction = cluster[pattern]
dy = vectors[direction*2+1]-256
dx = vectors[direction*2]
dx = dx-256 if dx>=128 else dx
for sx in range(12,193):
    m[S['video_ship_x']] = sx
    t.call('player_update')
    m[S['enemy_on']:S['enemy_on']+16] = bytes([1]+[0]*15)
    m[S['aliens_left']] = 1
    m[S['raw_enemy_x']] = (sx-dx)&255
    m[S['raw_enemy_y']] = 232
    m[S['pattern_lo']] = pattern&255
    m[S['pattern_hi']] = 16+(pattern>>8)
    t.call('alien_move')
    assert m[S['raw_enemy_y']] == 232+dy
    assert abs(m[S['raw_enemy_x']]-sx)>=64
    assert m[S['collision_cell_x']] == m[S['raw_enemy_x']]&248
    t.call('alien_body_collision')
    assert m[S['state']] == 1 and m[S['enemy_on']] == 1
checks.append('actual 6502 movement publishes relocated collision bounds without a return hit')

t,m=fixture()
m[S['enemy_on']:S['enemy_on']+16] = bytes([1]+[0]*15)
m[S['aliens_left']] = 1
m[S['raw_enemy_x']] = 96
m[S['raw_enemy_y']] = 208
m[S['aycmp']] = 255
m[S['axcmp']] = 208
t.c.x=0
t.call('safe_small_entry')
assert m[S['raw_enemy_x']] == 168
m[S['enemy_shape']] = 32
t.call('prepare_shot_bounds');t.call('refresh_alien_screen');t.call('latch_aliens')
shoot(t,m,168,208)
assert not m[S['enemy_on']] and not m[S['shot_on']]
checks.append('redirected birds remain immediately shootable; no invulnerability was added')

# Ship/shot/shield footprints and both bomb paths follow the 8-pixel lift.
t,m=fixture()
t.call('hardware_init')
for page, asset in [(S['SHIP'],'ship_white'),(S['SHIP_RED'],'ship_red')]:
    assert m[page+216:page+232] == t.m[S[asset]:S[asset]+16]
    assert not any(m[page+232:page+240])
m[S['shot_on']]=0;m[S['fire_edge']]=1
t.call('shot_update')
assert m[S['raw_shot_y']]==200 and m[S['shot_y']]==208
for pose in range(4):
    m[S['shield_pose']]=pose;m[S['shield_pmg_pose']]=255
    t.call('shield_players')
    for side, page in enumerate([S['SHIP'],S['SHIP_RED']]):
        start=S['shield_green']+pose*64+side*32
        assert m[page+208:page+240] == t.m[start:start+32]
m[S['shield_pose']]=255
t.call('shield_players')
assert not any(m[S['SHIP']+208:S['SHIP']+216])
assert m[S['SHIP']+216:S['SHIP']+232] == t.m[S['ship_white']:S['ship_white']+16]
for page in [S['SHIP'],S['SHIP_RED']]:
    assert not any(m[page+232:page+240])
for routine, ys in [('alien_body_collision',[201,202,222,223,230]),('bomb_collision',[211,212,224,225,232]),('bomb_collision_one',[211,212,224,225,232])]:
    for y in ys:
        t,m=fixture()
        m[S['enemy_on']:S['enemy_on']+16]=bytes([1]+[0]*15)
        m[S['raw_enemy_x']]=100;m[S['raw_enemy_y']]=y
        m[S['bomb_on']]=1;m[S['raw_bomb_x']]=104;m[S['raw_bomb_y']]=y
        t.c.x=0
        t.call(routine)
        expected=202<=y<223 if routine=='alien_body_collision' else 212<=y<225
        assert (m[S['state']]==3)==expected,(routine,y,m[S['state']])
checks.append('ship art, shield restore, shot origin and both bomb/body windows moved exactly 8 pixels')

report=dict(car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),method=__doc__,checks=checks,return_cases=cases,replenishment_wait_ticks=wait)
(R/'evidence/v015').mkdir(exist_ok=True)
(R/'evidence/v015/changes.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
