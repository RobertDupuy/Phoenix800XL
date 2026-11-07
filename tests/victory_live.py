"""Record the real emulator's victory transition, silent bonus and melody.
An explicit victory fixture is placed after normal boot/start and wave setup;
the cartridge then performs the score award, sound mixing and next-wave entry.
"""
from pathlib import Path
import argparse,os,sys,json,re,subprocess,tempfile,time,hashlib,wave
p=argparse.ArgumentParser();p.add_argument('--root',type=Path);p.add_argument('--machine',choices=['800XL','5200'],default='800XL');args=p.parse_args()
R=(args.root or Path(__file__).resolve().parents[1]).resolve();S=json.loads((R/'build/symbols.json').read_text());O=R/'evidence/victory-audio';O.mkdir(parents=True,exist_ok=True)
B=Path(os.environ['ALTIRRA_BRIDGE_PACKAGE']);sys.path.insert(0,str(B/'sdk/python'));from altirra_bridge import AltirraBridge
with tempfile.TemporaryDirectory(prefix='phoenix-audio-')as d:
 d=Path(d);log=(d/'private.log').open('w');proc=subprocess.Popen([os.environ['ALTIRRA_SDL'],'--headless','--test-mode','--renderer','sdlrenderer','--bridge=tcp:127.0.0.1:0'],stdout=log,stderr=log,env=dict(os.environ,SDL_AUDIODRIVER='dummy',SDL_VIDEODRIVER='dummy',XDG_CONFIG_HOME=str(d/'config')))
 try:
  for _ in range(600):
   match=re.search(r'token-file: (\S+)',(d/'private.log').read_text())
   if match:
    try:a=AltirraBridge.from_token_file(match[1]);break
    except ConnectionRefusedError:pass
   assert proc.poll() is None,'emulator exited during startup';time.sleep(.05)
  else:raise RuntimeError('emulator startup timeout')
  a.pause();a.config('machine',args.machine);a.config('memory','16K' if args.machine=='5200' else '64K');a.config('video','ntsc');a.config('addons','stock')
  if args.machine=='5200':a.config('kernel',os.environ['ATARI5200_BIOS'])
  else:a.config('basic','false')
  cart=R/('Phoenix5200.car' if args.machine=='5200' else 'Phoenix800XL.car');a.boot(str(cart));a.frame(500);a.joy(0,fire=True);a.frame(8);a.joy(0);a.frame(480)
  def write(values):
   for k,v in values.items():a.memload(S[k],bytes(v if isinstance(v,list) else [v]))
  a.bp_set(S['simulation_update']);a.cycles(240000);assert int(a.regs()['PC'][1:],16)==S['simulation_update'];a.bp_clear_all()
  write(dict(wave=4,cycle_stage=3,wave_wait=1,enemy_on=[0]*16,display_enemy_on=[0]*16,aliens_left=0,entrance_timer=0,entrance_handoff=0,wipe_timer=0,state=1,large_mode=0,boss_status=0,boss_entrance_shown=0,shield_pose=255,shield_locked=0,shield_count=0,bomb_on=[0]*5,invuln=255,lives=3))
  for _ in range(8):a.poke(S['invuln'],255);a.frame(100)
  assert a.peek(S['wave'])[0]==5
  a.bp_set(S['simulation_update']);a.cycles(240000);assert int(a.regs()['PC'][1:],16)==S['simulation_update'];a.bp_clear_all()
  write(dict(state=1,boss_status=3,boss_timer=96,boss_scroll=248,enemy_on=[0]*16,display_enemy_on=[0]*16,bomb_on=[0]*5,shot_on=0,second_on=0,score_digits=[0]*6,bonus_stage=0,audio_bonus_count=0,audio_death_pending=64,invuln=255,lives=3))
  before=a.memdump(0,16384);a.pokey_trace_start(65000);dest=O/('Phoenix-'+args.machine+'-victory.wav');a._cmd_ok('AUDIO_RECORD start path='+str(dest));rows=[]
  for f in range(780):
   if f%64==0:a.poke(S['invuln'],255)
   a.frame(1);m=a.memdump(0x3e00,0x70)
   rows.append([f,m[S['tune']-0x3e00],m[S['tune_pos']-0x3e00],m[S['audio_bonus_count']-0x3e00],m[0x67]&15])
  a.ping();a._cmd_ok('AUDIO_RECORD stop');a.pokey_trace_stop();events=[]
  while True:
   tr=a.pokey_trace_read(4096);assert tr['valid'] and not tr['dropped'];events+=tr['events']
   if not tr['queued']:break
  after=a.memdump(0,16384)
  def delta(k,n):return (int.from_bytes(after[S[k]:S[k]+n],'little')-int.from_bytes(before[S[k]:S[k]+n],'little'))%(1<<(8*n))
  start=next(i for i,r in enumerate(rows) if r[1]==2)
  assert all(r[1]==2 for r in rows[start:start+245]);assert max(r[2]for r in rows[start:])>=48
  bonus_during_music=[r for r in rows if r[1]==2 and r[3]>0]
  assert bonus_during_music and all(r[4]==0 for r in bonus_during_music), 'bonus beep mixed with victory music'
  assert after[S['wave']]==6 and after[S['lives']]==4
  ticks=[e['tick']for e in events if e['reg']==1];gaps=[b-a for a,b in zip(ticks,ticks[1:])]
  report=dict(car_sha256=hashlib.sha256(cart.read_bytes()).hexdigest(),method=__doc__,config=a.config(),video_frames=780,victory_tune_start_frame=start,notes_reached=max(r[2]for r in rows[start:]),next_wave=after[S['wave']],lives=after[S['lives']],late_vbi=delta('late_frames',2),audio_underruns=delta('audio_underruns',2),layout_faults=delta('layout_faults',1),missing_audio_frames=sum(max(0,round(g/(262*114))-1)for g in gaps),max_audio_gap_clocks=max(gaps),recording=dest.name)
  with wave.open(str(dest))as w:report['recorded_seconds']=w.getnframes()/w.getframerate()
  report['silent_bonus_frames']=len(bonus_during_music)
  assert report['late_vbi']==report['audio_underruns']==report['layout_faults']==report['missing_audio_frames']==0,report
  (O/'live.json').write_text(json.dumps(report,indent=2));(O/'tune-trace.json').write_text(json.dumps(rows));print(json.dumps(report,indent=2))
 finally:
  try:
   if 'a' in locals():a.quit()
   proc.wait(timeout=3)
  except Exception:
   proc.terminate()
   try:proc.wait(timeout=3)
   except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=3)
  log.close()
