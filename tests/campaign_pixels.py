"""Independent pixel compositor for scrolling/damaged mothership backgrounds."""
from cpu_model import *
import numpy as np,random,hashlib
from PIL import Image
G=np.array([list(open(R/'build/boss-glyphs.bin','rb').read()[i*8:i*8+8])for i in range(128)],dtype=np.uint8)
G=np.array([[[int(v)>>(6-2*x)&3 for x in range(4)]for v in tile]for tile in G])
ST=json.load(open(R/'src/arcade-assets/stars-irregular.json'))['cells']
def decode(m):
 a=np.zeros((200,160),np.uint8);b=m[0x9a]
 for row in range(25):
  font=[0x1800,0x2000,0x3000][min(row//8,2)]+b*1024
  for col in range(32):
   c=m[0x2800+b*1024+row*32+col]
   for y in range(8):
    v=m[font+(c&127)*8+y]
    for x in range(4):
     p=v>>(6-2*x)&3;a[row*8+y,(col+4)*4+x]=4 if p==3 and c&128 else p
 return a
rng=random.Random(511);t=Model();t.init();m=t.m.b;cases=0;worst=0
for scroll in list(range(113,-1,-7))+list(range(255,158,-3)):
 m[0x83]=5;t.call('wave_reset');m[0x80]=1;m[S['boss_status']]=1 if scroll<=113 else 2;m[S['boss_scroll']]=scroll
 for _ in range(6):m[0x8d]=1;t.call('mothership_tick')
 m[S['boss_scroll']]=scroll
 # Persistent holes, partly ablated layers, and arbitrary barrier rotation.
 for i in range(234):
  v=m[S['boss_body']+i]
  if 76<=v<=79 or v==94:
   if rng.random()<.3:m[S['boss_body']+i]=rng.choice([0,76,77,78,79]);m[0x1200+i]=1
  elif 96<=v<=111:m[S['boss_body']+i]=rng.randrange(96,112);m[0x1200+i]=1
 m[S['boss_dirty_rows']:S['boss_dirty_rows']+10]=bytes([1]*10)
 t.call('mothership_background');worst=max(worst,t.call('mothership_background'))
 expected=np.zeros((200,160),np.uint8)
 for r,c in ST:expected[r*8+3,c*4]=4
 top=48-scroll
 if scroll>113:top+=256
 y0=(top//8-(top%8==0))*8-32
 y1=y0+80
 if y1>0 and y0<200:expected[max(0,y0):min(200,y1),32:136]=0
 for r in range(9):
  for c in range(26):
   tile=G[m[S['boss_body']+r*26+c]]
   for y in range(8):
    yy=top+r*8+y-32
    if 0<=yy<200:expected[yy,32+c*4:36+c*4]=tile[y]
 got=decode(m)
 if not np.array_equal(got,expected):
  print('mismatch',scroll,np.count_nonzero(got!=expected),np.argwhere(got!=expected)[:20]);raise SystemExit(1)
 assert not m[0x32d],(scroll,m[0x32d]);cases+=1
report=dict(car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),mothership_pixel_cases=cases,pixel_errors=0,maximum_sampled_background_cpu_cycles=worst,scope=__doc__)
(R/'evidence/v011/mothership-pixels.json').write_text(json.dumps(report,indent=2));print(report)
