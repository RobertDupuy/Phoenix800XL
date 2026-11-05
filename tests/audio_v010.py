from cpu_model import *
import hashlib
D=json.loads((R/'src/arcade-assets/audio-circuit.json').read_text());t=Model();t.init();m=t.m.b;notes=0;cycles=[]
for tune_id in (1,2,3):
 m[0x3e00:0x3e50]=bytes(80);m[S['g_sound_a']]=15;m[S['g_sound_b']]=(tune_id<<6)|15
 phase=12817;pos=0;e0=e1=f0=f1=0
 data=D['music_ntsc'][(tune_id-1)*192:tune_id*192]
 for tick in range(1400):
  phase+=1000
  if phase>=12817:
   phase-=12817
   if pos<96:
    a,b=data[pos*2:pos*2+2];pos+=1;notes+=1
    if a:f0=a;e0=31
    if b:f1=b;e1=64
  e0=max(0,e0-1);e1=max(0,e1-1)
  cycles.append(t.call('audio_tick'))
  assert (m[S['tune_pos']],m[S['env0']],m[S['env1']],m[S['fr0']],m[S['fr1']])==(pos,e0,e1,f0,f1),(tune_id,tick)
  assert m[0x3e61]==D['volume0'][e0] and m[0x3e63]==D['volume1'][e1]
 assert pos==96 and e0==e1==0
# Every oscillator table entry matches the previous bounded fixed-point math.
checks=0
for which,size in [('a',48),('b',64)]:
 for idx in range(size):
  for nib in range(16):
   m[S['g_sound_'+which]]=nib
   if which=='a':m[S['mod_level']]=idx//16;m[S['c22_level']]=(idx%16)*16
   else:m[S['c7_level']]=idx*4
   t.call('audio_pitch_'+which)
   want=(((D['vco_'+which+'_ntsc_lo'][idx]+256*D['vco_'+which+'_ntsc_hi'][idx])*(16-nib)+128)//256-1)&255
   assert t.c.a==want,(which,idx,nib,t.c.a,want);checks+=1
# All live bird heights produce continuous audible control output after music.
m[0x80]=1;m[0x33c]=1;m[S['bird_elapsed']]=4;m[S['music_pending']]=0
for height in range(32):
 m[S['bird_height']]=height
 for _ in range(100):
  t.call('music_compute')
  assert m[0x3e67]&15,'silent bird oscillator'
# Actual NMI publication is bounded and advances the ring exactly once.
m[S['audio_head']]=2;m[S['audio_tail']]=0
pub=t.call('music_update');assert m[S['audio_tail']]==1
assert bytes(m[0xe800:0xe808])==bytes(m[0x3e80:0x3e88])
report=dict(car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),tunes=3,note_steps=notes,tune_ticks=4200,oscillator_pitch_cases=checks,bird_cadence_ticks=3200,audio_tick_max_cpu_cycles=max(cycles),vbi_publish_cpu_cycles=pub,limits='POKEY arrangement and circuit approximation; MAME tune 1 is itself an uncertain alarm reconstruction. Gameplay uses tune 3 at game start, tune 2 after the mothership victory, and discrete effects; campaign_acceptance.py checks the live victory trigger.')
(R/'evidence/v011/audio.json').write_text(json.dumps(report,indent=2));print(report)
