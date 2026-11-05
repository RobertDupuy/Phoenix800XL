"""Stateful background-cache regression with alternating buffers and foreground."""
from cpu_model import *
import numpy as np, random, hashlib
from campaign_pixels import decode, G, ST

def expected(m):
 a=np.zeros((200,160),np.uint8)
 for r,c in ST:a[r*8+3,c*4]=4
 top=(48-m[S['boss_scroll']])&255
 y0=(top//8-(top%8==0))*8-32;y1=y0+80
 if y1>0 and y0<200:a[max(0,y0):min(200,y1),32:136]=0
 for r in range(9):
  for c in range(26):
   y=top+r*8-32
   if y<200 and y+8>0:
    a[max(y,0):min(y+8,200),32+c*4:36+c*4]=G[m[S['boss_body']+r*26+c]][max(-y,0):min(8,200-y)]
 return a

t=Model();t.init();m=t.m.b;rng=random.Random(912)
m[0x83]=5;t.call('wave_reset');m[0x80]=1;m[S['boss_status']]=2;m[S['boss_scroll']]=249
m[0x400:0x410]=bytes(16);m[0x4d0:0x4e0]=bytes(16)
worst=0
for frame in range(600):
 for j in range(2):
  m[0x8d]=(frame*2+j)&255;t.call('mothership_tick')
 if frame%7==0:
  candidates=[i for i in range(234)if m[S['boss_body']+i] in [76,77,78,79,94]]
  if candidates:
   i=rng.choice(candidates);m[S['boss_body']+i]=rng.choice([0,76,77,78,79]);m[0x1200+i]=1
   m[S['boss_dirty_rows']:S['boss_dirty_rows']+10]=bytes([1]*10)
 m[0x9b]^=1;m[0x37c]=frame%4 if frame%11==0 else 255;m[0xa5]=100
 m[0x4d0:0x4d2]=b'\1\1';m[0x410:0x412]=bytes([48,104]);m[0x420:0x422]=bytes([48+(frame%17)*8,72+(frame%15)*8]);m[0x4c0:0x4c2]=bytes([32+(frame%12)*2,32+((frame+3)%12)*2])
 t.call('render_scene')
 # Erasure on the same buffer must recover every background pixel, even after
 # foreground glyph eviction, shield cells, phase changes and epoch rollover.
 cycles=t.call('mothership_background');worst=max(worst,cycles)
 assert np.array_equal(decode(m),expected(m)),('cache',frame,np.argwhere(decode(m)!=expected(m))[:8])
 assert m[0x32d]==0,(frame,m[0x32d])
report=dict(car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),stateful_frames=600,pixel_errors=0,layout_faults=0,maximum_warm_background_cpu_cycles=worst,method=__doc__)
(R/'evidence/v011/mothership-cache.json').write_text(json.dumps(report,indent=2));print(report)
