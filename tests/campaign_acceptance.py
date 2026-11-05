"""Focused CPU checks against the recovered arcade rules, with explicit fixtures."""
from cpu_model import *
import sys,random,hashlib
sys.path.insert(0,str(R/'tools'))
from prepare_native import tables
T=tables();t=Model();t.init();m=t.m.b;checks=0
# Every phase/round combination selects its own original formations and bomb cap.
for w in range(1,81):
 m[0x83]=w;t.call('wave_reset');stage=(w-1)%5;rn=((w-1)//5)*16
 assert m[S['level_round']]==rn+[1,3,5,7,11][stage]
 assert m[S['bomb_limit']]==min(5,3+rn//16)
 if stage in [0,1,4]:
  p=T['alien_position_pointer_table'][(m[S['level_round']]>>1)&15]
  assert list(m[0x430:0x440])==list(T['alien_position_layout_page'][p:p+32:2])
  assert list(m[0x440:0x450])==list(T['alien_position_layout_page'][p+1:p+32:2])
 else:assert m[S['bird_round']]==rn+(5 if stage==2 else 7) and m[0x374]==6
 checks+=1
# Exact armor and rotating barrier half-tile damage tables, including the core gate.
m[0x83]=5;t.call('wave_reset');m[0x80]=1;m[S['boss_status']]=2;m[S['boss_scroll']]=248
for tile in list(range(76,80))+list(range(96,112)):
 for half in [0,4]:
  for above in [0,94,126]:
   m[S['boss_status']]=2;m[S['boss_body']+116]=tile;m[S['boss_body']+90]=above
   m[0x88]=1;m[0xa6]=104+half;m[0xa7]=88
   t.call('mothership_collision')
   assert m[0x88]==0,(tile,half)
   if tile<80:
    expected=tile-1 if tile>76 else 0
    gate=above==94 and tile==76
    assert m[S['boss_body']+116]==expected
    assert m[S['boss_body']+90]==(79 if gate else above)
    assert m[S['boss_status']]==2
   else:
    open_gate=(tile&3)==1 if half else (tile&12)==4
    expected=tile if open_gate else T['mothership_explosion_pointers'][(tile&15)+(16 if half else 0)]
    assert m[S['boss_body']+116]==expected
    assert m[S['boss_status']]==(3 if open_gate and above&240==112 else 2)
   checks+=1
# Entry, descent stop, and the complete victory -> second-cycle route.
m[0x83]=5;t.call('wave_reset');m[0x80]=1
for i in range(120):t.call('mothership_tick')
assert m[S['boss_status']]==2 and m[S['boss_scroll']]==249
for i in range(6000):m[0x8d]=i&255;t.call('mothership_tick')
assert m[S['boss_scroll']]==159
m[S['boss_status']]=3;m[S['boss_timer']]=96;m[S['boss_scroll']]=248;m[0xc0:0xc6]=bytes(6)
for i in range(159):t.call('campaign_tick')
assert m[0x83]==5 and m[S['boss_status']]==4 and (m[S['g_sound_b']]>>6)==2
assert list(m[0xc0:0xc6])==[0,0,3,2,0,0],list(m[0xc0:0xc6])
t.call('campaign_tick');assert m[0x83]==6 and m[S['level_round']]==17 and m[0x71a]>0
# Every aligned kill height and round, including the original zero-bonus case.
for rn in range(0,256,16):
 for scroll in range(152,256,8):
  m[0x83]=5;t.call('wave_reset');m[0x80]=1;m[S['cycle_round']]=rn
  m[S['boss_status']]=3;m[S['boss_timer']]=33;m[S['boss_scroll']]=scroll
  m[0xc0:0xc6]=bytes(6)
  v=(scroll+96)&255;v=(v>>1)|((v&1)<<7);v+=rn
  if v>=144:v=144
  if (v&15)>=10:v+=6
  expected=(v>>4)*1000+(v&15)*100
  t.call('campaign_tick')
  score=int(''.join(str(q)for q in m[0xc0:0xc6]))
  assert score==expected,(rn,scroll,score,expected)
  t.call('campaign_tick');assert int(''.join(str(q)for q in m[0xc0:0xc6]))==expected
  checks+=1
# Wipes run between stages 2->3, 3->4, 4->5 and finish in the next stage.
for w in [2,3,4]:
 m[0x83]=w;t.call('wave_reset');m[0x80]=1;m[0x400:0x410]=bytes(16);m[0x8e]=1;t.call('wave_update')
 assert m[S['wipe_timer']]==1
 for i in range(55):t.call('campaign_tick')
 assert m[0x83]==w+1 and m[S['wipe_timer']]==0
 checks+=1
report=dict(car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),checks=checks,rounds=16,armor_and_barrier_cases=120,entry_ticks=120,victory_ticks=160,next_wave=6,award=3200,method=__doc__)
(R/'evidence/v011/campaign.json').write_text(json.dumps(report,indent=2));print(report)
