"""Compare decoded mothership pixels with the baseline MegaCart renderer.

Both CPUs receive identical explicit damage, scroll and animation fixtures.
This tests background composition and foreground overlap,
including both display buffers, scroll changes and allocator epoch wrap.
"""
from pathlib import Path
import argparse, importlib.util, json, hashlib
import numpy as np
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);p.add_argument('--frames',type=int,default=280);args=p.parse_args()
def load(root,name):
 spec=importlib.util.spec_from_file_location(name,root/'tests/cpu_model.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);t=mod.Model();t.init();return mod,t
def picture(mod,t):
 m=t.m.b;b=m[mod.S['back_buffer']];out=bytearray()
 for row in range(25):
  base=[0x1800,0x2000,0x3000][min(row//8,2)]+b*1024
  for y in range(8):
   for col in range(32):
    ch=m[0x2800+b*1024+row*32+col]
    out.extend((m[base+(ch&127)*8+y],ch&128))
 return bytes(out)
mods=[load(args.baseline,'baseline_cpu'),load(R,'cache_cpu')]
cycles=[0,0];checks=0
for mod,t in mods:
 m=t.m.b;m[mod.S['wave']]=5;t.call('wave_reset');m[mod.S['state']]=1;m[mod.S['boss_status']]=2;m[mod.S['boss_entrance_shown']]=0
 # High RAM starts dirty on a real warm entry; validity must be reset by init.
 for k in ('entrance_timer','wave_wait','wipe_timer','music_pending'):m[mod.S[k]]=0
for frame in range(args.frames):
 pics=[]
 for j,(mod,t) in enumerate(mods):
  m=t.m.b;s=mod.S
  m[s['boss_scroll']]=(249-frame//12)&255
  m[s['phase']]=frame&255
  m[s['invuln']]=255
  if frame%9==0:
   i=104+(frame//9)%22
   m[s['boss_body']+i]=[96,97,101,111][(frame//9)%4]
   m[0x1200+i]=1;m[s['boss_dirty_rows']+i//26]=1

  t.call('mothership_tick')
  cycles[j]+=t.call('boss_render')
  pics.append(picture(mod,t))
  m[s['front_buffer']]=m[s['back_buffer']]
 if pics[0]!=pics[1]:
  bad=[i for i,(a,b) in enumerate(zip(*pics)) if a!=b]
  raise AssertionError(dict(frame=frame,differences=len(bad),first=bad[:12],values=[(pics[0][i],pics[1][i])for i in bad[:12]]))
 checks+=1
report=dict(car_sha256=hashlib.sha256((R/'Phoenix800XL.car').read_bytes()).hexdigest(),baseline_sha256=hashlib.sha256((args.baseline/'Phoenix800XL.car').read_bytes()).hexdigest(),method=__doc__,frames=checks,decoded_pixel_errors=0,cpu_cycles=cycles,cpu_reduction_pct=round((1-cycles[1]/cycles[0])*100,2))
out=R/'evidence/xl/cache';out.mkdir(exist_ok=True,parents=True);(out/'oracle.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
