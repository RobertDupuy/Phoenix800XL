"""Actual Altirra raster checks. Stage selection is an explicit RAM fixture;
start and wave-1 shield use frontend controller events. Later shield states
are explicit RAM fixtures so debugger focus cannot swallow controller input.
"""
from play_campaign import Frontend,R
from pathlib import Path
import os,json
import numpy as np
from PIL import Image
O=R/'evidence/v028/raster';e=Frontend(O,Path(os.environ['ALTIRRA_SDL']))
S=json.loads((R/'build/symbols.json').read_text());events=[];shots=[]
def fixture(values):
 e.a.bp_set(S['simulation_update']);e.a.cycles(240000)
 assert int(e.a.regs()['PC'][1:],16)==S['simulation_update']
 e.a.bp_clear_all()
 for key,value in values.items():e.a.memload(S.get(key,key),bytes(value if isinstance(value,(list,bytes,bytearray)) else [value]))
 e.ui('run_command Debug.ToggleDebugger');e.ui('wait_frames 1');e.a.pause()
def stage(w):
 fixture({'wave':w-1,'cycle_stage':(w-2)%5,'wave_wait':1,'enemy_on':[0]*16,'display_enemy_on':[0]*16,'aliens_left':0,'entrance_timer':0,'entrance_handoff':0,'wipe_timer':0,'state':1,'large_mode':0,'boss_status':0,'shield_pose':255,'shield_locked':0,'shield_count':0,'bomb_on':[0]*5,'invuln':255,'lives':3})
 for _ in range(100):
  m=e.step(0,2)
  if m[S['wave']]==w:return
 raise AssertionError('stage transition')
def shot(name):
 e.a.screenshot(path=str(O/(name+'.png')));shots.append(name)
try:
 import sys
 sys.path.insert(0,str(R/'tools'))
 import supplied_art as art
 palette=np.frombuffer(e.a.palette(),np.uint8).reshape(256,3)
 seen_by_wave={};pilot_seen=set();late_start=0
 for _ in range(200):
  m=e.step(4,4)
  if m[S['state']]==1 and not m[S['entrance_timer']]:break
 e.step(0,16)
 for wave in (1,3,5):
  if wave!=1:stage(wave)
  for f in range(160):
   m=e.step(0,2)
   if not m[S['entrance_timer']] and not m[S['entrance_shown']] and m[S['boss_status']]!=1 and not m[S['boss_entrance_shown']]:break
  e.step(0,48)
  e.a.poke(S['invuln'],255)
  seen=set()
  if wave!=1:
   for k,v in [('shield_count',254),('shield_locked',1),('shield_pose',0)]:e.a.poke(S[k],v)
  for f in range(110):
   m=e.step(8 if wave==1 and f%16<4 else 0,2);pose=m[S['shield_pmg_pose']]
   assert not m[S['layout_faults']]
   if pose<4 and pose not in seen:
    path=O/f'wave-{wave}-shield-{pose}.png';e.a.screenshot(path=str(path))
    actual=np.asarray(Image.open(path).convert('RGB'))
    xx=8+(6+m[S['raw_ship_x']]//8)*8
    expected=art.pixels('shield',pose).copy();ship=art.pixels('player-ship',0)
    for y,x in zip(*np.where(ship)):
     assert expected[y+8,x]==0
     expected[y+8,x]=4 if ship[y,x]==3 else ship[y,x]
    colors=np.asarray([0,14,44,100,70,198],np.uint8)[expected]
    rgb=np.repeat(palette[colors],2,1)
    crop=actual[192:224,xx:xx+32]
    if np.array_equal(crop,rgb):seen.add(pose);shots.append(path.name)
   if len(seen)==4:break
  seen_by_wave[wave]=sorted(seen)
  assert len(seen)==4,('shield raster',wave,seen,{k:m[S[k]] for k in ['state','shield_pose','shield_locked','shield_count','shield_edge','shield_now','large_mode','entrance_timer','entrance_handoff']})
  if wave==5:
   e.a.poke(S['invuln'],255)
   for f in range(100):
    m=e.step(0,2)
    py=m[S['pilot_old_y']];pf=m[S['pilot_old_frame']]//16
    if py and pf not in pilot_seen:
     path=O/f'pilot-{pf}.png';e.a.screenshot(path=str(path))
     actual=np.asarray(Image.open(path).convert('RGB'))
     expected=art.pixels('small-pose-row-06',pf)
     rgb=np.repeat(palette[np.asarray([0,170,100,102],np.uint8)[expected]],2,1)
     # The structural cockpit lies behind the sprite's transparent margin.
     mask=np.repeat(expected>0,2,1)
     crop=actual[py-16:py,168:184]
     if np.array_equal(crop[mask],rgb[mask]):pilot_seen.add(pf);shots.append(path.name)
   assert len(pilot_seen)==4,('pilot raster',pilot_seen)
 report=dict(car_sha256=e.car_sha256,method=__doc__,shield_poses_by_wave=seen_by_wave,pilot_poses=sorted(pilot_seen),ship_and_shield_color_errors=0,pilot_color_errors=0,shots=shots)
 (O/'report.json').write_text(json.dumps(report,indent=2));print(report)
finally:e.close()
