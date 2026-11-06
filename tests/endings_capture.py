"""Explicit emulator fixtures for victory and game-over/restart, not a playthrough.
Scene setup writes RAM at a simulation boundary; subsequent input is physical fire.
"""
from play_campaign import Frontend,R
from pathlib import Path
import argparse,json
from PIL import Image
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--exe',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--record',action='store_true');args=p.parse_args()
out=args.out.resolve();e=Frontend(out,args.exe.resolve(),args.record)
S=json.loads((R/'build/symbols.json').read_text());events=[]
def fixture(values):
 e.a.bp_set(S['simulation_update']);e.a.cycles(180000)
 assert int(e.a.regs()['PC'][1:],16)==S['simulation_update']
 e.a.bp_clear_all()
 for key,value in values.items():e.a.memload(S.get(key,key),bytes(value if isinstance(value,list) else [value]))
 # A breakpoint opens the debugger console, which owns keyboard input.
 # Return keyboard focus to the emulated display before controller checks.
 e.ui('run_command Debug.ToggleDebugger');e.ui('wait_frames 1');e.a.pause()
def boss_scene():
 fixture({'wave':4,'cycle_stage':3,'wave_wait':1,'enemy_on':[0]*16,'display_enemy_on':[0]*16,
          'entrance_timer':0,'entrance_handoff':0,'wipe_timer':0,'state':1,'large_mode':0,'boss_status':0})
 for _ in range(100):
  m=e.step(0,4)
  if m[S['boss_status']]==2:return m
 raise AssertionError('boss entry failed')
try:
 for _ in range(100):
  m=e.step(4,4)
  if m[S['state']]==1:break
 e.step(0,8);boss_scene()
 fixture({'boss_status':3,'boss_timer':96,'boss_scroll':248,'boss_award_row':5,
          'enemy_on':[0]*16,'display_enemy_on':[0]*16,'bomb_on':[0]*5,'shot_on':0,'second_on':0,'shield_pose':255})
 for i in range(100):
  m=e.step(0,2)
  events.append({'part':'victory','frame':e.frames,'state':m[S['boss_status']],'timer':m[S['boss_timer']],'scroll':m[S['boss_scroll']]})
  if i%4==0:e.a.screenshot(path=str(out/f'victory-{i:03}.png'))
  if m[S['wave']]==6:break
 assert m[S['wave']]==6
 boss_scene()
 fixture({'state':3,'death_timer':1,'lives':1,'boss_scroll':248,S['boss_body']+110:[0]*16})
 for i in range(300):
  m=e.step(4,2)
  assert m[S['state']]==2
  events.append({'part':'gameover','frame':e.frames,'timer':m[S['gameover_timer']],'state':m[S['state']]})
  if i in [2,10,18,25,90,110]:e.a.screenshot(path=str(out/f'gameover-{i:03}.png'))
  if i>110 and m[S['gameover_timer']]==0:break
 assert m[S['gameover_timer']]==0 and m[S['gameover_armed']]==0,(m[S['gameover_timer']],m[S['gameover_armed']],m[S['fire_now']])
 e.step(0,4)
 blank=False;restarted=False
 for i in range(16):
  m=e.step(4,2 if i==0 else 1)
  path=out/f'restart-{i:02}.png';e.a.screenshot(path=str(path))
  dark=not np.asarray(Image.open(path).convert('RGB')).any()
  blank|=dark
  if m[S['state']]==4 and not m[S['restart_blank']]:
   assert set(m[0x2800:0x2b20])<={0,1} and set(m[0x2c00:0x2f20])<={0,1},'stale mothership glyphs after restart'
  restarted|=m[S['wave']]==1 and m[S['state']]==4 and m[S['restart_blank']]==0
  events.append({'part':'restart','frame':e.frames,'blank':dark,'blank_flag':m[S['restart_blank']],'state':m[S['state']]})
 assert blank and restarted,(blank,restarted)
 assert m[S['layout_faults']]==0
 (out/'report.json').write_text(json.dumps({'car_sha256':e.car_sha256,'method':__doc__,'blank_frame_observed':blank,'restarted_cleanly':restarted,'events':events},indent=2))
 print('PASS: victory, flashing game over, held-fire lockout, visible blank before restart')
finally:
 (out/'events.json').write_text(json.dumps(events,indent=2))
 e.close()
