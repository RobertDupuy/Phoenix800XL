from cpu_model import *
import numpy as np,hashlib
import scene_oracle as so
F=json.loads((R/'build/flight-art.json').read_text())['frames'];F2=json.loads((R/'build/flight-art.json').read_text())['second_palette_frames'];so.background=lambda timer=0:np.zeros((200,160),dtype=np.uint8)
def decode(m):
 a=np.zeros((200,160),dtype=np.uint8);b=m[0x9a]
 for row in range(25):
  font=[0x1800,0x2000,0x3000][min(row//8,2)]+b*1024
  for col in range(32):
   c=m[0x2800+b*1024+row*32+col]
   for y in range(8):
    v=m[font+(c&127)*8+y]
    for x in range(4):
     p=v>>(6-2*x)&3;a[row*8+y,(col+4)*4+x]=4 if p==3 and c&128 else p
 return a
def background(m):
 a=np.zeros((200,160),dtype=np.uint8)
 if m[0x80] not in [1,3] or m[0x80]==3 and m[0x377]<33:return a
 for i in range(8):
  if not m[0x400+i]:continue
  xx=m[S['large_x']+i];xx=xx-256 if xx>=232 else xx;xx=28+xx//2;yy=m[S['large_y']+i]
  l=m[S['large_left']+i];r=m[S['large_right']+i]
  tr=lambda v:0 if not v else 1 if v<16 else 2 if v<32 else 3
  for y,row in enumerate((F2 if m[0x33c]==2 else F)[m[S['large_pose']+i]]):
   for x,v in enumerate(row):
    dy=(yy+y)&255
    if tr(l)*4<=x<32-tr(r)*4 and 32<=dy<232 and 28<=xx+x<132:
     if v:a[dy-32,xx+x]=v
 return a
t=Model();t.init();m=t.m.b;cases=0;worst=0
for pose in range(60):
 for phase in range(8):
  m[0x83]=3+(pose&1);t.call('wave_reset');m[0x80]=1;m[0x37c]=255;m[0x88]=m[0x710]=0;m[0x480:0x485]=bytes(5);m[0x4d0:0x4e0]=bytes(16)
  for i in range(8):
   m[S['large_x']+i]=(-16+i*32)&255;m[S['large_y']+i]=(i*16+24+phase)&255;m[S['large_pose']+i]=(pose+i)%60
  m[0x9b]^=1;cycles=t.call('render_scene');worst=max(worst,cycles)
  assert np.array_equal(decode(m),background(m)),(pose,phase,np.argwhere(decode(m)!=background(m))[:8])
  assert m[0x32d]==0;cases+=1
# Death, shield, both numeric popup slots and overlapping moving effects.
for scenario in range(40):
 m[0x83]=3;t.call('wave_reset');m[0x80]=1;m[0x37c]=255;m[0x88]=m[0x710]=0;m[0x480:0x485]=bytes(5);m[0x4d0:0x4e0]=bytes(16)
 for i in range(8):m[S['large_x']+i]=8+i*16;m[S['large_y']+i]=56+i*16;m[S['large_pose']+i]=40+i%4
 if scenario<24:m[0x80]=3;m[0x377]=95-scenario*2;m[0x379]=12
 elif scenario<28:m[0x37c]=scenario-24;m[0xa5]=100
 else:
  m[0x770:0x772]=bytes([16,16]);m[0x778:0x77a]=bytes([14-(scenario-28)%14]*2);m[0x77a:0x77c]=b'\1\1';m[0x774:0x776]=bytes([16,24]);m[0x776:0x778]=bytes([8,16]);m[0x787:0x789]=bytes([10,80])
 m[0x9b]^=1;t.call('render_scene');want=so.scene(m,base=background(m));got=decode(m)
 assert np.array_equal(got,want),(scenario,np.count_nonzero(got!=want),np.argwhere(got!=want)[:8]);assert m[0x32d]==0,(scenario,m[0x32d]);cases+=1
 # The next use of this buffer must erase every displaced footprint.
 m[0x80]=1;m[0x37c]=255;m[0x770:0x772]=bytes(2);m[0x9b]^=1;t.call('render_scene');m[0x9b]^=1;t.call('render_scene')
 assert np.array_equal(decode(m),background(m)),('clear',scenario)
# Every occupied fitted pixel is accepted as a shot collision.
shots=0
for pose,frame in enumerate(F):
 for y,row in enumerate(frame):
  for x,v in enumerate(row[:28]):
   if not v:continue
   m[0x83]=3;t.call('wave_reset');m[0x400:0x410]=bytes([pose//4+1]+[0]*15);m[S['large_x']]=40;m[S['large_y']]=80;m[S['large_pose']]=pose
   m[S['bird_records']]=pose//4+1;m[S['bird_records']+4]=64;m[0x88]=1;m[0xa6]=40+x*2;m[0xa7]=80+y
   t.call('large_collision');assert m[0x88]==0,(pose,x,y);assert t.m.bank==0;shots+=1
report=dict(car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),pixel_fixtures=cases,pixel_errors=0,occupied_pixel_collision_cases=shots,synthetic_first_frame_render_max_cpu_cycles=worst,scope='All sixty original draw states, all eight vertical pixel offsets, side clipping, three fonts, death, shield, numeric popups, erasure and pixel hits. CPU-only; elapsed DMA timing is measured separately.')
(R/'evidence/v011/pixels.json').write_text(json.dumps(report,indent=2));print(report)
