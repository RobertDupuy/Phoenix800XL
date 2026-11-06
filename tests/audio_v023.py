"""Executable-ROM sound regressions: arcade dispatcher, coexistence and transitions."""
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

# Arcade $3AD0 compares the counter BEFORE incrementing. Check every cadence
# against its recovered control sequence, including the initial pulse.
t.init();m=t.m.b;m[0x3e00:0x3e50]=bytes(80)
m[S['state']]=1;m[S['large_mode']]=1;m[S['aliens_left']]=6
cadence=(R/'build/bird_sound_cadence.bin').read_bytes();pulse_cases=0
for height,limit in enumerate(cadence):
 m[S['bird_height']]=height;m[S['audio_bird_stage']]=m[S['audio_bird_count']]=0
 count=stage=0;pulses=0
 for tick in range(256):
  expected=((stage&1)<<2)|32
  old=count;count=(count+1)&255
  if old==0:stage=(stage+1)&255;expected|=16;pulses+=1
  elif limit<count:count=0
  t.call('audio_controls')
  assert m[S['g_sound_b']]==expected,(height,tick,expected,m[S['g_sound_b']])
  assert m[S['audio_bird_count']]==count and m[S['audio_bird_stage']]==stage
  pulse_cases+=1
 assert pulses>=2
# Formation shape bytes $20..$27 must remain quiet at ANY screen height.
m[S['large_mode']]=0;m[S['g_sound_b']]=15
m[S['enemy_on']:S['enemy_on']+16]=bytes([1]*16)
formation_cases=0
for shape in range(32,40):
 m[S['enemy_shape']:S['enemy_shape']+16]=bytes([shape]*16)
 for y in range(256):
  m[S['raw_enemy_y']:S['raw_enemy_y']+16]=bytes([y]*16)
  t.call('audio_controls');assert m[S['g_sound_a']]==15;formation_cases+=1
for count in range(17):
 m[S['enemy_shape']:S['enemy_shape']+16]=bytes([40]*count+[32]*(16-count))
 t.call('audio_controls');assert m[S['g_sound_a']]==(0x25+min(count,8) if count else 15)
# A cleared wave, wipe, entrance or empty flock cannot sustain its bird sound.
for mode in (0,1,2,3):
 m[S['large_mode']]=mode;m[S['boss_status']]=2
 for gate in ('wave_wait','wipe_timer','entrance_timer'):
  m[S[gate]]=50;t.call('audio_controls')
  assert m[S['g_sound_a']]&15==15 and m[S['g_sound_b']]&15==15
  m[S[gate]]=0
for mode in (1,2):
 m[S['large_mode']]=mode;m[S['aliens_left']]=0;t.call('audio_controls')
 assert m[S['g_sound_b']]&15==15
# Arrival advances from its actual countdown while the small-bird clock is frozen.
m[S['large_mode']]=3;m[S['boss_status']]=1;m[S['arcade_clock']]=m[S['arcade_clock']+1]=0
arrival=[];arrival_hz=[]
for remaining in range(120,0,-1):
 m[S['boss_timer']]=remaining;t.call('audio_controls');arrival.append(m[S['g_sound_b']]);t.call('audio_tick')
 assert m[0x3e67]&15<=3
 arrival_hz.append(1789772.5/(56*(m[0x3e66]+1)))
assert len(set(arrival))>=3 and max(arrival_hz)<1800
m[S['boss_status']]=3;t.call('audio_controls');assert m[S['g_sound_b']]&15==15
# Gun/death noise shares an idle voice instead of cutting off the bird oscillator.
m[0x3e00:0x3e50]=bytes(80);m[S['boss_status']]=0
for noise in (64,128):
 for tick in range(64):
  m[S['g_sound_a']]=15|noise;m[S['g_sound_b']]=32
  t.call('audio_tick')
  assert m[0x3e67]&0xf0==0xa0 and m[0x3e67]&15,'bird pulse was preempted by noise'
  t.call('audio_pitch_b');assert m[0x3e66]==t.c.a
  assert m[0x3e63]&0xf0==0x80,'noise not mixed into idle music voice'
# Every queued register set is coherent, including the independent fast clock.
for slot in range(8):
 m[S['audio_head']]=(slot+1)&7;m[S['audio_tail']]=slot
 regs=bytes([42,167,128,166,200,164,159,136]);m[0x3e80+slot*8:0x3e88+slot*8]=regs;m[0x3ec0+slot]=32
 pub=t.call('music_update');assert bytes(m[0xe800:0xe808])==regs and m[0xe808]==32
 assert m[S['audio_tail']]==(slot+1)&7
# The fallback is fixed-bank NMI code: a stalled/banked foreground cannot
# hold a note forever, and it does not use foreground zero-page scratch.
for bank in range(8):
 t.m.high=bank&4;t.m.low=bank&3
 m[S['audio_head']]=m[S['audio_tail']]=0
 m[S['audio_last_controls']:S['audio_last_controls']+4]=bytes([0xaf,0xa8,0xa4,0x8f])
 scratch=bytes(m[0x70:0x80])
 for _ in range(15):t.call('music_update')
 assert all(m[x]&15==0 for x in (0xe801,0xe803,0xe805,0xe807))
 assert bytes(m[0x70:0x80])==scratch
 t.m.high=t.m.low=0
# Transition buffering covers the reset work without adding normal-wave latency.
for mode,wait,wipe,depth in [(0,0,0,3),(1,0,0,3),(2,0,0,3),(3,0,0,6),(1,30,0,6),(2,0,40,6)]:
 m[S['large_mode']]=mode;m[S['wave_wait']]=wait;m[S['wipe_timer']]=wipe
 m[S['audio_head']]=m[S['audio_tail']]=0;m[S['music_pending']]=0
 t.call('audio_prepare');assert (m[S['audio_head']]-m[S['audio_tail']])&7==depth
report=dict(car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),tune_ticks=4200,pitch_cases=pitch_cases,large_bird_reference_control_ticks=pulse_cases,formation_cases=formation_cases,arrival_seconds=120/61,arrival_max_hz=max(arrival_hz),arrival_peak_volume=3,noise_does_not_cut_bird_tone=True,underrun_fades_in_frames=15,underrun_banks_tested=8,normal_queue_frames=3,transition_and_boss_queue_frames=6)
(R/'evidence/v023/audio-cpu.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
