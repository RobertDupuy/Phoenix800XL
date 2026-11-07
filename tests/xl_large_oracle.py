"""Match both large waves against the pre-cache renderer, through scrolling,
pose changes, wing clipping, overlapping birds and foreground effects."""
from pathlib import Path
import argparse,importlib.util,json,hashlib
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);args=p.parse_args()
def load(root,name):
 spec=importlib.util.spec_from_file_location(name,root/'tests/cpu_model.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);t=mod.Model();t.init();return mod,t
def picture(mod,t):
 m=t.m.b;b=m[mod.S['back_buffer']];out=bytearray()
 for row in range(25):
  base=[0x1800,0x2000,0x3000][min(row//8,2)]+b*1024
  for y in range(8):
   for col in range(32):
    ch=m[0x2800+b*1024+row*32+col];out.extend((m[base+(ch&127)*8+y],ch&128))
 return bytes(out)
cycles=[0,0];frames=0
for wave in (3,4):
 mods=[load(args.baseline,'baseline_cpu'),load(R,'cached_cpu')]
 for mod,t in mods:
  m=t.m.b;s=mod.S;m[s['wave']]=wave;t.call('wave_reset');m[s['state']]=1
 for frame in range(320):
  pictures=[]
  for j,(mod,t) in enumerate(mods):
   m=t.m.b;s=mod.S;m[s['invuln']]=255
   for _ in range(3):t.call('large_tick')
   # Dense, clipped poses cover the hot-path merge and drawing paths.
   if 100<=frame<160:
    for bird in range(7):
     m[s['large_x']+bird]=(frame+bird*12)&255;m[s['large_y']+bird]=(frame//3+bird*8+64)&255
     m[s['large_pose']+bird]=(frame//4+bird)%60
     m[s['large_left']+bird]=(frame+bird)%40;m[s['large_right']+bird]=(frame+bird*2)%40
   cycles[j]+=t.call('large_render');pictures.append(picture(mod,t));m[s['front_buffer']]=m[s['back_buffer']]
  if pictures[0]!=pictures[1]:
   bad=[i for i,(a,b) in enumerate(zip(*pictures)) if a!=b]
   raise AssertionError(dict(wave=wave,frame=frame,differences=len(bad),first=bad[:8],allocation=[(t.m.b[mod.S['layout_faults']],list(t.m.b[mod.S['lg_next']:mod.S['lg_next']+3])) for mod,t in mods]))
  frames+=1
report=dict(car_sha256=hashlib.sha256((R/('Phoenix800XL-512K.car' if json.loads((R/'build/symbols.json').read_text()).get('XL_JCART') else 'Phoenix800XL.car')).read_bytes()).hexdigest(),baseline_sha256=hashlib.sha256((args.baseline/'Phoenix800XL.car').read_bytes()).hexdigest(),frames=frames,decoded_pixel_errors=0,cpu_cycles=cycles,cpu_reduction_pct=round((1-cycles[1]/cycles[0])*100,2),method=__doc__)
out=R/'evidence/xl/cache';out.mkdir(parents=True,exist_ok=True);(out/'large-oracle.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
