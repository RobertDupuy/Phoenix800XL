"""Exercise actual 6502 output: concurrent blast and shot, allocation and fade."""
from cpu_model import *
import hashlib

t=Model();t.init();m=t.m.b;cases=0;max_cycles=0
for kind in (16,64):
 for shot in (0,4,16,32,63):
  for death in (0,8,32,128,255):
   for gate in (15,79,143,207):
    m[0x3e00:0x3e50]=bytes(80)
    m[S['boss_status']]=0;m[S['g_sound_a']]=gate;m[S['g_sound_b']]=15
    m[S['noise_shot_level']]=shot;m[S['noise_death_level']]=death
    m[S['noise_death_kind']]=kind
    cycles=t.call('audio_tick');max_cycles=max(max_cycles,cycles)
    sv=round(8*m[S['noise_shot_level']]/63)
    dv=round(8*(m[S['noise_death_level']]>>2)/63)
    voices=[(m[0x3e60+c],m[0x3e61+c]&15) for c in range(0,8,2) if m[0x3e61+c]&15]
    if kind==16 and sv and dv:
     assert len(voices)==2,(kind,shot,death,gate,voices)
     assert (159,dv) in voices,('lost low explosion tail',voices)
     other=voices.copy();other.remove((159,dv))
     assert other[0][1]==sv,('lost overlapping shot',voices)
     hz=1789772.5/28/(other[0][0]+1)
     expected=588+6325*(m[S['noise_shot_level']]+(m[S['noise_death_level']]>>2))/126
     assert abs(hz/expected-1)<.06,(hz,expected)
    else:
     assert len(voices)==bool(sv or dv),(kind,shot,death,gate,voices)
    cases+=1

# An extra shot can borrow only silence. Preserve every busy music/bird voice.
allocation_cases=0
for busy in range(16):
 m[0x3e60:0x3e68]=bytes([51,0,64,0,91,0,103,0])
 for ch in range(4):m[0x3e61+ch*2]=0xa7 if busy&(1<<ch) else 0
 before=bytes(m[0x3e60:0x3e68]);m[0x3e68]=32
 m[S['noise_extra_freq']]=21;m[S['noise_extra_control']]=0x85
 t.call('audio_extra_mix')
 after=bytes(m[0x3e60:0x3e68]);changed=[]
 for ch in range(4):
  if busy&(1<<ch):assert before[ch*2:ch*2+2]==after[ch*2:ch*2+2]
  elif after[ch*2+1]&15:changed.append(ch);assert after[ch*2:ch*2+2]==bytes([21,0x85])
 assert len(changed)==(busy!=15)
 assert m[0x3e68]==(0 if changed==[2] else 32)
 allocation_cases+=1

# Start at the game's real damage entry with an already active gunshot.
t=Model();t.init();m=t.m.b;m[0x3e00:0x3e50]=bytes(80)
m[S['state']]=1;m[S['invuln']]=0;m[S['boss_status']]=0;m[S['g_sound_b']]=15
m[S['audio_shot_count']]=18;m[S['noise_shot_level']]=50
t.call('damage_player');overlap_ticks=0;blast_ticks=0;records=[]
for tick in range(120):
 cycles=t.call('music_tick');max_cycles=max(max_cycles,cycles)
 voices=[(m[0x3e60+c],m[0x3e61+c]&15) for c in range(0,8,2) if m[0x3e61+c]&15]
 blast_ticks+=bool(m[S['g_sound_a']]&128)
 sv=round(8*m[S['noise_shot_level']]/63);dv=round(8*(m[S['noise_death_level']]>>2)/63)
 if sv and dv:
  assert (159,dv) in voices
  assert len(voices)>=2
  overlap_ticks+=1
 if tick<16:assert m[S['audio_shot_count']]==18
 records.append(dict(tick=tick,control=m[S['g_sound_a']],voices=voices))
assert blast_ticks==16 and overlap_ticks>=15
assert not any(m[0x3e61+c]&15 for c in range(0,8,2)), 'effect failed to end'
report=dict(car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),
 envelope_combinations=cases,voice_allocation_cases=allocation_cases,gate_ticks=blast_ticks,
 real_damage_overlap_ticks=overlap_ticks,maximum_audio_cycles=max_cycles,records=records)
(R/'evidence/v025').mkdir(parents=True,exist_ok=True)
(R/'evidence/v025/ship-mixing.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2))
