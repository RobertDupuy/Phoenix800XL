"""NTSC Altirra timing and entrance fixtures; includes real DMA/interrupt time.

This is a staged diagnostic, not a controller-only playthrough. Stage/scene
fixtures write RAM at a simulation boundary; the ROM then runs normally.
Requires ALTIRRA_BRIDGE_PACKAGE and ATARI5200_BIOS. Neither dependency is shipped.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,sys,tempfile,time
parser=argparse.ArgumentParser();parser.add_argument("--trial-six",action="store_true");args=parser.parse_args()
R=Path(__file__).resolve().parents[1]
S=json.loads((R/'build/symbols.json').read_text())
B=Path(os.environ['ALTIRRA_BRIDGE_PACKAGE']).resolve()
sys.path.insert(0,str(B/'sdk/python'))
from altirra_bridge import AltirraBridge
out=R/'evidence/v028';out.mkdir(parents=True,exist_ok=True)
BIOS=Path(os.environ['ATARI5200_BIOS']).resolve()
assert hashlib.sha256(BIOS.read_bytes()).hexdigest()=='06b250f18983d058c0f156ce7ee88ae48b6eaf11e6f10f21dccf6ac7ffb6a6af'
private=tempfile.TemporaryDirectory(prefix='phoenix-v021-emulator-')
logpath=Path(private.name)/'server.log';log=logpath.open('w')
p=subprocess.Popen([str(B/'AltirraBridgeServer'),'--machine=5200','--memory=16K','--bridge=tcp:127.0.0.1:0'],stdout=log,stderr=log,env=dict(os.environ,SDL_AUDIODRIVER='dummy'))
try:
 for _ in range(100):
  match=re.search(r'token-file: (\S+)',logpath.read_text())
  if match:break
  if p.poll() is not None:raise RuntimeError('emulator exited')
  time.sleep(.05)
 else:raise RuntimeError('emulator startup timeout')
 a=AltirraBridge.from_token_file(match[1]);a.pause()
 a.config('video','ntsc');config=a.config('kernel',str(BIOS))
 a.boot(str(R/'build/Phoenix-First-Flight.car'));a.frame(500)
 a.joy(0,fire=True);a.frame(8);a.joy(0,fire=False);a.frame(480)
 assert a.peek(S['state'])[0]==1
 a.screenshot(path=str(out/'dark-blue-stars.png'))
 def memory():return a.memdump(0,16384)
 def put(values):
  for key,value in values.items():a.memload(S.get(key,key),bytes(value if isinstance(value,(list,bytes,bytearray)) else [value]))
 def boundary():
  a.bp_clear_all();a.bp_set(S['simulation_update']);a.cycles(240000)
  assert int(a.regs()['PC'][1:],16)==S['simulation_update']
  a.bp_clear_all()
 def stage(wave):
  boundary()
  put({'wave':wave-1,'cycle_stage':3,'wave_wait':1,'enemy_on':[0]*16,'display_enemy_on':[0]*16,'entrance_timer':0,'entrance_handoff':0,'wipe_timer':0,'state':1,'large_mode':0,'boss_status':0,'boss_entrance_shown':0,'invuln':0,'lives':3})
  for _ in range(100):
   a.frame(1)
   if a.peek(S['boss_status'])[0]==1:return
  raise AssertionError('mothership entry did not begin')
 entry_checks=0
 stage(5)
 for frame in range(160):
  a.joy(0,fire=bool(frame&1));a.frame(1);m=memory()
  if m[S['boss_entrance_shown']] and m[S['large_shown']]==3:
   assert m[S['ship_hpos']]==0 and m[S['shot_on']]==m[S['second_on']]==0, (frame,m[S['ship_hpos']],m[S['shot_on']],m[S['second_on']],m[S['boss_status']])
   assert m[S['shield_locked']]==0
   entry_checks+=1
   if frame==35:a.screenshot(path=str(out/'mothership-entry.png'))
  if m[S['boss_status']]==2 and not m[S['boss_entrance_shown']]:
   assert m[S['ship_hpos']]!=0
   break
 else:raise AssertionError('player did not appear after entry')
 a.joy(0,fire=False);a.frame(2)
 a.screenshot(path=str(out/('six-escorts.png' if args.trial_six else 'mothership-combat.png')))
 cases=[];steady=[]
 for round_number in (0,15):
  if round_number:
   stage(80);a.frame(180)
  for count in ((4,6) if args.trial_six else (4,)):
   for scenario in range(16):
    boundary()
    put({'state':1,'boss_status':2,'boss_entrance_shown':0,'boss_scroll':249-(scenario*5)%88,
         'enemy_on':[1]*count+[0]*(16-count),'aliens_left':count,'invuln':255,
         'raw_enemy_x':[(16+i*31+scenario*7)%192 for i in range(16)],
         'raw_enemy_y':[40+((i*3+scenario)%17)*8 for i in range(16)],
         'enemy_kind':[1]*16,'enemy_shape':[32+((i+scenario)%12)*2 for i in range(16)],
         'pattern_lo':[0]*16,'pattern_hi':[16]*16,'main_phase':0,'fast_aliens':0,
         'shield_pose':scenario%4 if scenario&1 else 255,'shield_locked':scenario&1,
         'shield_count':250 if scenario&1 else 0,'fire_edge':1,'shot_on':1,
         'raw_shot_x':100,'raw_shot_y':190,'bomb_on':[1]*5,
         'raw_bomb_x':[20,60,100,140,180],'raw_bomb_y':[80,110,140,170,190],
         'boss_dirty_rows':[1]*10})
    if scenario%4==0:put({'boss_atlas_phase':[255]*6})
    start=a.clock()['tick'];a.bp_set(S['update_counted']);a.cycles(240000)
    assert int(a.regs()['PC'][1:],16)==S['update_counted']
    elapsed=a.clock()['tick']-start;a.bp_clear_all()
    m=memory();assert not m[S['layout_faults']]
    cases.append(dict(round=round_number,escorts=count,scenario=scenario,foreground_clocks=elapsed))
    a.frame(5)
   # A long running six/four-bird flock, without destroying birds. Refresh
   # invulnerability only to hold the load stable, not to alter rendering.
   boundary()
   put({'state':1,'enemy_on':[1]*count+[0]*(16-count),'aliens_left':count,
        'pattern_lo':[0]*16,'pattern_hi':[16]*16,'enemy_shape':[32]*16,'enemy_kind':[1]*16,
        'raw_enemy_x':[16+i*28 for i in range(6)]+[0]*10,'raw_enemy_y':[64]*16,
        'shield_pose':255,'shield_locked':0,'shield_count':0,'shot_on':0,'fire_edge':0,
        'bomb_on':[0]*5,'boss_scroll':248,'invuln':255,'main_phase':0,'fast_aliens':0})
   a.joy(0,fire=False);a.frame(20);before=memory();a.pokey_trace_start(24000)
   for _ in range(6):
    a.poke(S['invuln'],255);a.frame(100)
   after=memory();a.pokey_trace_stop();events=[]
   while True:
    tr=a.pokey_trace_read(4096);assert tr['valid'] and not tr['dropped'];events+=tr['events']
    if not tr['queued']:break
   sound_ticks=[v['tick'] for v in events if v['chip']==1 and v['reg']==1]
   gaps=[b-a for a,b in zip(sound_ticks,sound_ticks[1:])]
   missing_audio_frames=sum(max(0,round(g/(262*114))-1) for g in gaps)

   def delta(name,n):return (int.from_bytes(after[S[name]:S[name]+n],'little')-int.from_bytes(before[S[name]:S[name]+n],'little'))%(1<<(n*8))
   frames=delta('frames',4);renders=delta('fresh_commits',4);sim=delta('sim_steps',4)
   steady.append(dict(round=round_number,escorts=count,video_frames=frames,render_fps=round(renders/frames*59.922743,3),simulation_hz=round(sim/frames*59.922743,3),late_vbi=delta('late_frames',2),layout_faults=after[S['layout_faults']],final_survivors=after[S['aliens_left']],audio_publishes=len(sound_ticks),missing_audio_frames=missing_audio_frames,max_audio_gap_clocks=max(gaps)))
   print('Steady',steady[-1],flush=True)
 # Four video frames are the existing mothership display interval. Every
 # stressed foreground update must finish before the fourth following VBI.
 limit=4*262*114-2048
 timing_pass=all(c['foreground_clocks']<limit for c in cases)
 if args.trial_six:
  for rn in (0,15):
   four=next(x for x in steady if x['round']==rn and x['escorts']==4)
   six=next(x for x in steady if x['round']==rn and x['escorts']==6)
   timing_pass &= six['render_fps']>=four['render_fps']-.2 and six['simulation_hz']>=60.5
 stable=all(x['late_vbi']==0 and x['layout_faults']==0 and x['final_survivors']==x['escorts'] and x['simulation_hz']>=60.5 and x['missing_audio_frames']==0 for x in steady)
 if not args.trial_six:assert stable,steady
 report=dict(car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),method=__doc__,emulator_sha256=hashlib.sha256((B/'AltirraBridgeServer').read_bytes()).hexdigest(),bios_sha256=hashlib.sha256(BIOS.read_bytes()).hexdigest(),entry_frames_checked=entry_checks,config={k:config[k] for k in ['machine','memory','video','rapidus','vbxe']},stress_cases=cases,steady_runs=steady,foreground_limit_clocks=limit,steady_runs_pass=stable,all_stress_frames_within_four_vbi=bool(timing_pass),six_escort_timing_pass=bool(timing_pass and stable) if args.trial_six else None)
 (out/('mothership-six-trial.json' if args.trial_six else 'mothership-emulator.json')).write_text(json.dumps(report,indent=2))
 print('Steady timing pass:',stable,'worst stress clocks',max(c['foreground_clocks'] for c in cases),flush=True)
finally:
 p.terminate();p.wait(timeout=5);log.close();private.cleanup()
