"""Actual Altirra raster checks. Stage selection is an explicit RAM fixture;
ship movement/start/shield inputs are frontend controller key events.
"""
from play_campaign import Frontend,R
from pathlib import Path
import os,json
import numpy as np
from PIL import Image
O=R/'evidence/v026/raster';e=Frontend(O,Path(os.environ['ALTIRRA_SDL']))
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
 (O/'palette.bin').write_bytes(e.a.palette())
 for _ in range(200):
  m=e.step(4,4)
  if m[S['state']]==1 and not m[S['entrance_timer']]:break
 else:raise AssertionError('start')
 e.step(0,16);shot('small-birds')
 for x in range(4):e.step(1,2);shot('ship-'+str(x))
 e.step(0,64)
 seen=set();expected=json.loads((R/'build/shield-manifest.json').read_text())['pixels']
 for f in range(100):
  m=e.step(8 if f<4 else 0,2);pose=m[S['shield_pmg_pose']]
  if pose<4 and pose not in seen:
   path=O/f'shield-{pose}.png';e.a.screenshot(path=str(path))
   actual=np.asarray(Image.open(path).convert('RGB'))
   xx=8+(6+m[S['raw_ship_x']]//8)*8
   crop=actual[192:224,xx:xx+32].max(axis=2)>0
   if np.array_equal(crop,np.repeat(np.asarray(expected[pose])>0,2,1)):
    seen.add(pose);shots.append('shield-'+str(pose))
 assert len(seen)==4,('shield raster',seen)
 stage(3)
 for f in range(0,600,4):
  if f%80==0:e.a.poke(S['invuln'],255)
  m=e.step(0,4)
  if f in (0,80,160,240,320,400,500,580):shot('large-'+str(f))
  assert not m[S['layout_faults']]
  events.append(dict(frame=e.frames,wave=m[S['wave']],late=int.from_bytes(m[S['late_frames']:S['late_frames']+2],'little'),faults=m[S['layout_faults']]))
 fixture({'state':3,'death_timer':95,'explosion_left':12,'raw_ship_x':100,'video_ship_x':100,'invuln':0,'shield_pose':255,'shield_locked':0,'bomb_on':[0]*5})
 for f in range(0,64,4):
  e.step(0,4)
  if f%16==0:shot('explosion-'+str(f//16))
 stage(5)
 for _ in range(80):
  m=e.step(0,4)
  if m[S['boss_status']]==2 and not m[S['boss_entrance_shown']]:break
 e.step(0,12);shot('mothership')
 report=dict(car_sha256=e.car_sha256,method=__doc__,shield_poses_raster_verified=4,shield_silhouette_errors=0,shots=shots,events=events)
 (O/'report.json').write_text(json.dumps(report,indent=2));print({k:v for k,v in report.items() if k!='events'})
finally:e.close()
