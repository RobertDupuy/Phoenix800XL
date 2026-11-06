"""Executable-ROM sound checks: pitch, capacitors, triggers and VBI publication."""
from cpu_model import *
import hashlib,math
D=json.loads((R/'src/arcade-assets/audio-circuit.json').read_text());t=Model();t.init();m=t.m.b;cycles=[];notes=0
# Retain all three tune sequences and both note envelopes exactly.
for tune_id in (1,2,3):
 m[0x3e00:0x3e50]=bytes(80);m[S['g_sound_a']]=15;m[S['g_sound_b']]=(tune_id<<6)|15
 phase=12817;pos=e0=e1=f0=f1=0;data=D['music_ntsc'][(tune_id-1)*192:tune_id*192]
 for tick in range(1400):
  phase+=1000
  if phase>=12817:
   phase-=12817
   if pos<96:
    a,b=data[pos*2:pos*2+2];pos+=1;notes+=1
    if a:f0=a;e0=31
    if b:f1=b;e1=64
  e0=max(0,e0-1);e1=max(0,e1-1);cycles.append(t.call('audio_tick'))
  assert (m[S['tune_pos']],m[S['env0']],m[S['env1']],m[S['fr0']],m[S['fr1']])==(pos,e0,e1,f0,f1)
  assert m[0x3e61]==D['volume0'][e0] and m[0x3e63]==D['volume1'][e1]
 assert pos==96 and not(e0 or e1)
# Compare actual frequency to the unquantized recovered circuit period.
fast_errors=[];old_errors=[];pitch_cases=0
for idx in range(48):
 for nib in range(15):
  m[S['mod_level']]=idx//16;m[S['c22_level']]=(idx%16)*16;m[S['g_sound_a']]=nib
  t.call('audio_pitch_a');div=t.c.a;period=(D['vco_a_ntsc_lo'][idx]+256*D['vco_a_ntsc_hi'][idx])*(16-nib)/256
  desired=1789772.5/(56*period)
  actual=1789772.5/(2*(div+4)) if div>=64 else 1789772.5/(56*(div+1))
  if div>=64:
   fast_errors.append(abs(actual/desired-1)*100)
   previous=((int(period+0.5)-1)&255);old_errors.append(abs((1789772.5/(56*(previous+1)))/desired-1)*100)
   assert abs(actual/desired-1)<.0061
  else:assert abs(actual/desired-1)<.06
  pitch_cases+=1
# Entire B lookup is monotonic with its capacitor and saturates, never wraps.
for nib in range(16):
 previous=-1
 for idx in range(64):
  m[S['c7_level']]=idx*4;m[S['g_sound_b']]=nib;t.call('audio_pitch_b')
  assert t.c.a>=previous,(idx,nib);previous=t.c.a;pitch_cases+=1
# Noise is held by latch state, not a short chirp that expires during death.
for address in ['noise_shot_level','noise_death_level']:m[S[address]]=0
m[S['g_sound_a']]=79;m[S['g_sound_b']]=15;levels=[]
for _ in range(64):t.call('audio_tick');levels.append(m[S['noise_shot_level']])
assert levels==sorted(levels) and levels[-1]==63
assert m[0x3e67]&15==8
m[S['g_sound_a']]=15
for _ in range(12):t.call('audio_tick')
assert m[S['noise_shot_level']]==0 and m[0x3e67]==0
m[S['g_sound_a']]=143
for _ in range(64):t.call('audio_tick');assert m[0x3e66]==159 and m[0x3e67]&15
m[S['g_sound_a']]=15;t.call('audio_tick');assert m[0x3e67]&15
for _ in range(120):t.call('audio_tick')
assert m[S['noise_death_level']]==0 and m[0x3e67]==0
# Shield is triggered by the actual gameplay path and uses original $3B28.
t.init();m[0x3e00:0x3e50]=bytes(80);m[S['shield_count']]=0;m[S['shield_edge']]=1;t.call('shield_update')
assert m[S['audio_shield_count']]==64
m[S['state']]=0
for i in range(64):
 t.call('audio_controls');assert m[S['g_sound_b']]==((63-i)&6)*2
# The score path restores the original bonus-life pulse sequence.
m[S['score_digits']:S['score_digits']+6]=bytes([0,0,3,0,0,0]);m[S['bonus_stage']]=0;t.c.a=1;t.call('score_add')
assert m[S['audio_bonus_count']]==255
m[S['state']]=0
for i in range(255):
 t.call('audio_controls');assert m[S['g_sound_b']]==(((255-i)&8)|7)
# Original mothership arrival gate/control bytes.
for age in range(512):
 m[S['state']]=1;m[S['large_mode']]=3;m[S['boss_status']]=1;m[S['arcade_clock']]=age&255;m[S['arcade_clock']+1]=age>>8
 t.call('audio_controls');assert m[S['g_sound_b']]==(10 if age&96 else 28+(age&2))
# Music, noise and clock selection travel through one coherent ring entry.
for slot in range(8):
 m[S['audio_head']]=(slot+1)&7;m[S['audio_tail']]=slot
 regs=bytes([42,167,128,166,200,164,159,136]);m[0x3e80+slot*8:0x3e88+slot*8]=regs;m[0x3ec0+slot]=32
 pub=t.call('music_update');assert bytes(m[0xe800:0xe808])==regs and m[0xe808]==32
 assert m[S['audio_tail']]==(slot+1)&7
# Audio refill depths cover the rendering interval without growing bird-wave latency.
for scene,depth in [(0,3),(1,3),(2,3),(3,6)]:
 m[S['large_mode']]=scene;m[S['audio_head']]=m[S['audio_tail']]=0;m[S['music_pending']]=0
 t.call('audio_prepare');assert (m[S['audio_head']]-m[S['audio_tail']])&7==depth
assert max(cycles)<3000
report=dict(car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),tune_ticks=4200,note_steps=notes,pitch_cases=pitch_cases,high_clock_pitch_cases=len(fast_errors),high_clock_worst_error_pct=max(fast_errors),old_same_pitches_worst_error_pct=max(old_errors),arrival_control_cases=512,shield_trigger_and_ticks=64,bonus_life_trigger_and_ticks=255,audio_tick_max_cpu_cycles=max(cycles),vbi_publish_cpu_cycles=pub,limits='Circuit/control and pitch tests; spectral comparisons and actual POKEY recordings are in audio_study_v021.py. POKEY retains square-wave timbre and two music voices.')
(R/'evidence/v021/audio-cpu.json').write_text(json.dumps(report,indent=2));print(report)
