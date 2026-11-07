"""Source-asset pixel oracle over recovered poses; synthetic instruction fixtures."""
from cpu_model import *
import random,time,hashlib
manifest=json.loads((R/'build/sprite-manifest.json').read_text());poses=manifest['poses'];byshape={p['shape']:p for p in poses};rng=random.Random(520005)
t=Model();t.init();m=t.m.b;results=[]
cases=[]
for pi,p in enumerate(poses):
 for edge in range(8):
  points=[(8+(i%4)*56,32+(i//4)*48) for i in range(16)]
  if edge==1:points=[(64+i%3,104+i%4) for i in range(16)]
  if edge>=2:points=[((i*24)%256,[0,24,32,216,224,248][edge-2]) for i in range(16)]
  cases.append([(x,y,p['shape'],1) for x,y in points])
for k in range(400):
 points=[(rng.randrange(256),rng.randrange(256)) for i in range(16)]
 if k<100:points=[(96+i%3,96+i%4) for i in range(16)]
 cases.append([(x,y,rng.choice(poses)['shape'],int(k<300 or (i+k)%5!=0)) for i,(x,y) in enumerate(points)])
normal_cases=len(cases)
for x in [12,100,192]:
 for timer in range(96,0,-1):cases.append([(8+(i%4)*56,32+(i//4)*48,poses[(i*3)%len(poses)]["shape"],1) for i in range(16)])
for case,objs in enumerate(cases):
 m[0x80]=1 if case<normal_cases else 3
 if case>=normal_cases:
  ecase=case-normal_cases;m[0x377]=96-ecase%96;m[0x379]=[12,100,192][ecase//96]//8
 m[0x9b]=case&1
 for i,(x,y,shape,on) in enumerate(objs):m[0x400+i]=on;m[0x430+i]=x;m[0x440+i]=y;m[0x4a0+i]=shape
 t.call('latch_aliens')
 cycles=t.call('render_scene')
 from scene_oracle import scene
 exp=scene(m).tobytes()
 base=0x2800+m[0x9a]*0x400;font=0x2000+m[0x9a]*0x400
 actual=bytearray()
 for yy in range(200):
  for cell in range(40):
   ch=m[base+yy//8*32+cell-4] if 4<=cell<36 else 0;p=m[font+(ch&127)*8+yy%8]
   actual.extend(4 if v==3 and ch&128 else v for v in (p>>6,p>>4&3,p>>2&3,p&3))
 if actual!=exp:
  diffs=[(i%160,i//160,a,b) for i,(a,b) in enumerate(zip(actual,exp)) if a!=b]
  raise AssertionError((case,m[0x32d],m[0xda],diffs[:15]))
 assert not m[0x32d],(case,'overflow',m[0xda])
 results.append({'case':case,'cycles':cycles,'glyphs':m[0xda]-64})
 if case%400==0:print(case,cycles,m[0xda],flush=True)
out=R/'evidence/renderer-native';out.mkdir(parents=True,exist_ok=True)
(out/'proof.json').write_text(json.dumps({'car_sha256':hashlib.sha256((R/'build/Phoenix800XL.car').read_bytes()).hexdigest(),'fixture':'synthetic py65; source-asset pixel composite, separate from MAME phase comparison; 16 slots; all 60 poses (55 live poses and five entry fades) at eight grid/edge placements, 400 overlap/disappearance scenes and 288 death-count/position scenes','cases':len(cases),'pixels_per_scene':32000,'pixel_errors':0,'max_cpu_cycles':max(r['cycles'] for r in results),'max_glyphs':max(r['glyphs'] for r in results),'dynamic_allocation_structural_bound':None,'with_ship_explosion_structural_bound':None,'results':results},indent=2))
print('PASS',len(cases),max(r['cycles'] for r in results),max(r['glyphs'] for r in results))
