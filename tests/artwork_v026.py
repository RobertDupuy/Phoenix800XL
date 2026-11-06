"""Independent source-frame roundtrips and three-plane player tests."""
import sys,json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from cpu_model import Model,R,S
sys.path.insert(0,str(R/'tools'))
import supplied_art as art
B=R/'build';cases=0;used=set()
N=json.loads((B/'sprite-manifest.json').read_text());F=json.loads((B/'flight-art.json').read_text())
def crop(a):
 a=np.asarray(a);x,y,r,b=art.bbox(a);return a[y:b,x:r]
def same(a,b):
 global cases
 assert np.array_equal(crop(a),crop(b));cases+=1
# Compare every encoded pose with its original supplied frame, excluding only
# transparent positioning margins. Injured birds intentionally lose a wing.
for p in N['poses']:
 if not p['kind']:continue
 src=p['source'];same(p['pixels'],art.pixels(src['group'],src['frame']));used.add((src['group'],src['frame']))
for i,p in enumerate(F['frames']):
 kind=i//4+1;frame=F['source_frames'][i];src=art.pixels('large-bird',frame)
 if kind in (12,13,14):
  yy,xx=np.where((src==2)|(src==3));left,right=int(xx.min()),int(xx.max())+1
  if kind in (13,14):src[:,:left]=0
  if kind in (12,14):src[:,right:]=0
 same(p,src);used.add(('large-bird',frame))
# Decode the actual banked ROM bytes rather than only generator manifests.
rom=(B/'Phoenix-First-Flight.rom').read_bytes()
for bank in (2,5):
 for i,p in enumerate(F['frames']):
  packed=rom[bank*32768+16384+i*256:bank*32768+16384+(i+1)*256]
  decoded=[[packed[x//4*32+8+y]>>(6-(x%4)*2)&3 for x in range(32)] for y in range(16)]
  assert decoded==p;cases+=1
for f in range(4):
 same(json.loads((B/'shield-manifest.json').read_text())['pixels'][f],art.pixels('shield',f));used.add(('shield',f))
 # Death layout uses the source yellow explosion without resampling.
 out=np.zeros((112,64),np.uint8)
 for cell,tid in N['explosions'][f*8]:
  x,y=divmod(cell,16)
  for yy,v in enumerate(N['tiles'][tid]):
   for xx in range(4):out[y*8+yy,x*4+xx]=v>>(6-xx*2)&3
 same(out,art.pixels('explosion',f));used.add(('explosion',f))
 # Small-bird death animation has three distinct source color regions.
 out=np.zeros((16,12),np.uint8)
 for j,tid in enumerate(N['bursts'][6-f*2]):
  for y,v in enumerate(N['tiles'][tid]):
   for x in range(4):out[(j%2)*8+y,(j//2)*4+x]=v>>(6-x*2)&3
 same(out,art.pixels('small-pose-row-06',f));used.add(('small-pose-row-06',f))
# Exercise all ship poses in the actual 6502, including stationary frames.
t=Model();t.init();m=t.m.b
for frame in range(4):
 m[S['video_ship_x']]=96+frame*2;m[S['ship_pose']]=255;t.call('animate_ship')
 pose=((m[S['video_ship_x']]+4)>>1)&3
 out=np.zeros((16,16),np.uint8)
 for col,addr in [(1,0x1400),(2,0x1600),(3,0x1500)]:
  for y,v in enumerate(m[addr+216:addr+232]):
   for x in range(8):
    if v&(128>>x):
     assert out[y,x+4]==0;out[y,x+4]=col
 same(out,art.pixels('player-ship',pose));used.add(('player-ship',pose))
 before=bytes(m[0x1400:0x1700]);t.call('animate_ship');assert before==bytes(m[0x1400:0x1700])
# The extra bomb now shares the ordinary software projectile renderer.
for wave in (1,3,5):
 m[S['wave']]=wave;t.call('wave_reset');m[S['state']]=1;m[S['enemy_on']:S['enemy_on']+16]=bytes(16)
 m[S['bomb_on']:S['bomb_on']+5]=bytes([0,0,0,1,0]);m[S['bomb_x']+3]=124;m[S['bomb_y']+3]=220
 m[S['shield_pose']]=255;t.call('latch_aliens');t.call('render_scene')
 b=m[S['back_buffer']];assert m[0x724+b]==19 and m[0x726+b]==22
 assert not m[S['layout_faults']];cases+=1
assert len(used)==63,(len(used),sorted(used))
assert len(rom)==262144
report=dict(car_sha256=hashlib.sha256((B/'Phoenix-First-Flight.car').read_bytes()).hexdigest(),source_frames_used=len(used),checks=cases,pixel_shape_or_color_region_errors=0,normal_frames='exact source pixels; positioning changes only transparent margins',injured_states='supplied full-spread frame with the appropriate wing removed',car_payload_bytes=len(rom))
O=R/'evidence/v026';O.mkdir(exist_ok=True,parents=True);(O/'artwork.json').write_text(json.dumps(report,indent=2));print(report)
