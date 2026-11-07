"""Execute the real core-hit -> score -> extra-life -> next-wave audio path.

Arcade ROM $255B sets $436B to $FF; $3923 reasserts tune 2 while that
counter runs. The regression specifically crosses the 3,000-point extra-life
threshold, whose beeps previously cleared the port's one-time tune selection.
"""
from pathlib import Path
import argparse,importlib.util,json,hashlib
p=argparse.ArgumentParser();p.add_argument('--root',type=Path);p.add_argument('--expect-bug',action='store_true');args=p.parse_args()
R=(args.root or Path(__file__).resolve().parents[1]).resolve()
spec=importlib.util.spec_from_file_location('tested_cpu',R/'tests/cpu_model.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);S=mod.S
results=[]
for extra_life in (False,True):
 t=mod.Model();t.init();m=t.m.b;m[S['wave']]=5;t.call('wave_reset');m[S['state']]=1
 m[0x3e00:0x3e50]=bytes(80);m[S['music_pending']]=0;m[S['g_sound_a']]=m[S['g_sound_b']]=15
 m[S['boss_status']]=2;m[S['boss_scroll']]=248;m[S['boss_entrance_shown']]=0
 m[S['boss_body']+90]=112;m[S['boss_body']+116]=101
 m[S['score_digits']:S['score_digits']+6]=bytes(6);m[S['bonus_stage']]=0 if extra_life else 2
 m[S['shot_on']]=1;m[S['raw_shot_x']]=104;m[S['raw_shot_y']]=88
 t.call('mothership_collision');assert m[S['boss_status']]==3
 started=None;trace=[];notes=[];lastpos=0
 for tick in range(800):
  m[S['invuln']]=255;t.call('campaign_tick');t.call('music_tick')
  if started is None and m[S['boss_status']]==4:started=tick
  if started is not None:
   trace.append([tick,m[S['tune']],m[S['tune_pos']],m[S['g_sound_b']],m[S['audio_bonus_count']]])
   pos=m[S['tune_pos']]
   if pos!=lastpos:
    notes.append([pos,m[S['fr0']],m[S['fr1']]]);lastpos=pos
 assert started is not None and m[S['wave']]==6
 uninterrupted=all(row[1]==2 for row in trace[:255])
 if args.expect_bug:
  if extra_life:assert not uninterrupted
 else:
  assert uninterrupted,trace[:4]
  assert m[S['tune_pos']]>=48 and len({n[1]for n in notes})>=12,(m[S['tune_pos']],notes)
  data=json.loads((R/'src/arcade-assets/audio-circuit.json').read_text())['music_ntsc'][192:384]
  f0=f1=0
  for pos,a,b in notes:
   na,nb=data[(pos-1)*2:pos*2]
   if na:f0=na
   if nb:f1=nb
   assert (a,b)==(f0,f1),(pos,a,b,f0,f1)
 results.append(dict(extra_life=extra_life,lives=m[S['lives']],next_wave=m[S['wave']],victory_start_tick=started,uninterrupted_first_255_ticks=uninterrupted,notes_reached=m[S['tune_pos']],distinct_lead_pitches=len({n[1]for n in notes}),notes=notes))
car=next(R.glob('Phoenix*.car'));report=dict(method=__doc__,car_sha256=hashlib.sha256(car.read_bytes()).hexdigest(),cases=results,arcade_source='https://www.computerarcheology.com/Arcade/Phoenix/Code.html#L2552')
if not args.expect_bug:
 out=R/'evidence/victory-audio';out.mkdir(parents=True,exist_ok=True);(out/'regression.json').write_text(json.dumps(report,indent=2))
print(json.dumps({**report,'cases':[{k:v for k,v in row.items() if k!='notes'}for row in results]},indent=2))
