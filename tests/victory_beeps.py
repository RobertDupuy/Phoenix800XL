"""The victory bonus must not add any sound to Fur Elise.

Compare real 6502 POKEY output with and without bonus timers throughout the
melody, including after the 255-tick victory hold. Verify ordinary bonus and
gunshot sounds remain available outside that one suppression.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json

p = argparse.ArgumentParser(); p.add_argument('--root', type=Path); args = p.parse_args()
R = (args.root or Path(__file__).resolve().parents[1]).resolve()
spec = importlib.util.spec_from_file_location('tested_cpu', R/'tests/cpu_model.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); S = mod.S

def fresh():
    t = mod.Model(); t.init(); m = t.m.b
    m[0x3e00:0x3e50] = bytes(80)
    m[S['music_pending']] = 0; m[S['state']] = 1
    m[S['large_mode']] = 3; m[S['boss_status']] = 4
    m[S['g_sound_a']] = 15; m[S['g_sound_b']] = 143
    m[S['audio_victory_count']] = 255
    return t

clean, bonus = fresh(), fresh()
bonus_ticks = 0; audible_ticks = 0
for tick in range(720):
    # Exercise the start, the middle, expiration of the hold, and final decay.
    if tick in (0, 130, 250, 400, 550):
        bonus.m.b[S['audio_bonus_count']] = 64
    was_bonus = bool(bonus.m.b[S['audio_bonus_count']])
    for t in (clean, bonus):
        t.call('music_tick')
    a, b = clean.m.b, bonus.m.b
    assert a[0x3e60:0x3e69] == b[0x3e60:0x3e69], ('bonus changed POKEY output', tick)
    assert a[S['tune']] == b[S['tune']] == 2
    assert b[0x3e67] & 15 == 0, ('victory beep', tick)
    if was_bonus:
        bonus_ticks += 1
    audible_ticks += bool(a[0x3e61] & 15 or a[0x3e63] & 15)
assert bonus_ticks == 320 and audible_ticks > 500
assert not bonus.m.b[S['audio_bonus_count']], 'suppressed beep was deferred'

# The extra-life sound elsewhere remains unchanged.
t = fresh(); m = t.m.b; m[S['audio_victory_count']] = 0
m[S['tune']] = 0; m[S['g_sound_b']] = 15; m[S['audio_bonus_count']] = 64
normal_beeps = 0
for _ in range(64):
    t.call('music_tick'); normal_beeps += bool(m[0x3e67] & 15)
assert normal_beeps == 32

# The requested fix does not mute unrelated gunshots during the melody.
t = fresh(); m = t.m.b; m[S['audio_shot_pending']] = 1
shot_ticks = 0
for _ in range(25):
    t.call('music_tick')
    shot_ticks += any(m[0x3e61+c] & 0xf0 == 0x80 and m[0x3e61+c] & 15 for c in (0,2,4,6))
assert shot_ticks > 0
car = R/('Phoenix5200.car' if (R/'Phoenix5200.car').exists() else 'Phoenix800XL.car')
report = dict(method=__doc__, car_sha256=hashlib.sha256(car.read_bytes()).hexdigest(),
              compared_audio_ticks=720, suppressed_bonus_ticks=bonus_ticks,
              audible_melody_ticks=audible_ticks, normal_bonus_beep_ticks=normal_beeps,
              unrelated_gunshot_ticks=shot_ticks, register_mismatches=0)
out = R/'evidence/victory-audio'; out.mkdir(parents=True, exist_ok=True)
(out/'no-victory-beeps.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
