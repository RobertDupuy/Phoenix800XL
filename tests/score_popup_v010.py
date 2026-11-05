from cpu_model import *
import hashlib
T=Model();T.init();m=T.m.b;checks=0;values=set()
for kind in range(1,16):
 for age in range(256):
  m[S['bird_records']]=kind;m[S['bird_records']+4]=age;T.c.x=0;T.call('large_score_value')
  if kind<11:want=5
  elif kind==15:want=10
  else:
   a=((age>>1)&124)+48
   if kind!=14:
    a>>=1
    if kind<12:a>>=1
   if a&15>9:a=(a+6)&255
   if a>0x99:a=(a+0x60)&255
   want=(a>>4)*10+(a&15)
  assert T.c.a==want,(kind,age,T.c.a,want);checks+=1;values.add(want*10)
m[0x83]=3;T.call('wave_reset');m[0x400:0x410]=bytes([11]+[0]*15);m[S['bird_records']]=11;m[S['bird_records']+4]=240;m[S['large_x']]=80;m[S['large_y']]=80;m[S['large_pose']]=40;m[0x88]=1;m[0xa6]=104;m[0xa7]=85;m[0xc0:0xc6]=bytes(6)
T.call('large_collision');assert m[0x400]==0 and m[0x770]==16 and m[0x787]==30 and m[0x88]==0
shown=[]
for step in range(1,17):
 T.call('burst_tick');T.call('score_service')
 if m[0x770] and m[0x77a]:shown.append(step)
assert shown==list(range(2,16)),shown
assert bytes(m[0xc0:0xc6])==bytes([0,0,0,3,0,0])
report=dict(car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),award_formula_cases=checks,popup_fixture_points=300,popup_counter_start=16,digit_visible_effect_steps=shown,effect_rate=61.03515625/2,score_award_count=1,source='Amstar ROM 3844–389C, 3758–37CC: type/timer award, decimal adjustment, split explosion and numeric display; not the former slot-based scores.')
(R/'evidence/v011/score-popup.json').write_text(json.dumps(report,indent=2));print(report)
