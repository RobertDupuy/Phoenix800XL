"""Game-over input gating and original-arcade mothership destruction checks."""
from cpu_model import Model,R,S
import json,hashlib,numpy as np

t=Model();t.init();m=t.m.b
m[S['lives']]=1;m[S['state']]=3;m[S['death_timer']]=1
t.call('death_tick')
assert m[S['state']]==2 and m[S['gameover_timer']]==183
flashes=set()
for tick in range(183):
 m[S['fire_now']]=1;m[S['fire_edge']]=1
 t.call('game_tick_regular');t.call('render_banner')
 assert m[S['state']]==2
 flashes.add(bool(any(m[0x0ae8+m[S['back_buffer']]*1024:0x0b58+m[S['back_buffer']]*1024])))
assert flashes=={False,True}
for _ in range(20):t.call('game_tick_regular')
assert m[S['state']]==2 and not m[S['gameover_armed']]
m[S['fire_now']]=0;t.call('game_tick_regular')
m[0x2800:0x3000]=bytes([127])*2048
m[S['fire_now']]=1;m[S['fire_edge']]=1;t.call('game_tick_regular')
assert m[S['state']]==4 and m[S['restart_blank']]==1
assert m[0xd400]==m[0xc01d]==0 and m[0xd40e]==64
assert not any(m[0x2800:0x3000]),'old mothership map survived restart'

art=json.loads((R/'build/victory-manifest.json').read_text())
raw=(R/'reference/mame-victory/trace.bin').read_bytes();size=3076;comparisons=0
for i,frame in enumerate(art['foreground_codes']):
 ram=raw[i*size+4:(i+1)*size]
 assert ram[0x3a5]==95-i
 for cx in range(16):
  for cy in range(16):
   assert ram[0x282-cx*32+cy]==frame[cx*16+cy]
   comparisons+=1
 core=art['core_codes'][i]
 if core is not None:
  for cx in range(4):
   for cy in range(4):
    assert ram[0x9c6-cx*32+cy]==core[cx*4+cy]
    comparisons+=1

def decode(m):
 a=np.zeros((200,160),np.uint8);b=m[S['back_buffer']]
 for row in range(25):
  font=[0x1800,0x2000,0x3000][min(row//8,2)]+b*1024
  for col in range(32):
   code=m[0x2800+b*1024+row*32+col]
   for y in range(8):
    byte=m[font+(code&127)*8+y]
    for x in range(4):
     v=byte>>(6-2*x)&3
     a[row*8+y,(col+4)*4+x]=4 if v==3 and code&128 else v
 return a

t=Model();t.init();m=t.m.b;m[S['wave']]=5;t.call('wave_reset');m[S['state']]=1
cases=0;worst=0
for scroll in (248,200,152):
 for frame,cells in enumerate(art['frames']):
  m[S['front_buffer']]^=1;m[S['boss_status']]=3;m[S['boss_timer']]=95-frame;m[S['boss_scroll']]=scroll
  t.call('mothership_background');expected=decode(m)
  worst=max(worst,t.call('mothership_picture'))
  for cell,tid in cells:
   cx,cy=divmod(cell,16);row=(((8-scroll)&255)//8-4+cy)&31
   if row>=25:continue
   tile=art['tiles'][tid]
   for y in range(8):
    for x in range(4):
     v=tile[y]>>(6-2*x)&3;mask=tile[8+y]>>(6-2*x)&3
     yy=row*8+y;xx=(13+cx)*4+x
     if not mask:expected[yy,xx]=v
  assert np.array_equal(decode(m),expected),(scroll,frame,np.argwhere(decode(m)!=expected)[:5])
  assert not m[S['layout_faults']] and t.m.bank==0
  cases+=1

# Arcade end sequence is 96 destruction ticks followed by 64 award ticks.
m[S['boss_status']]=3;m[S['boss_timer']]=96;m[S['boss_scroll']]=248
m[S['boss_award_row']]=5;m[S['phase']]=0
for _ in range(96):t.call('mothership_tick')
assert m[S['boss_status']]==4 and m[S['boss_timer']]==64
for _ in range(63):t.call('mothership_tick')
assert m[S['boss_scroll']]==216 and m[S['boss_award_row']]==5
t.call('mothership_tick');assert m[S['campaign_advance']]==1
report=dict(car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),
 gameover_delay_ticks=183,gameover_seconds=183/61.03515625,flashing_verified=True,
 held_fire_blocked=True,release_then_press_required=True,restart_display_disabled=True,
 original_MAME_tile_comparisons=comparisons,mothership_pixel_scenes=cases,
 pixel_errors=0,layout_faults=0,maximum_blast_cpu_cycles=worst,
 explosion_ticks=96,award_ticks=64,award_scroll_pixels=32,bonus_position_fixed=True)
(R/'evidence/v018/endings.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
