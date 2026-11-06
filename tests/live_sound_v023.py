"""Controller-only Phoenix gameplay with native audio and POKEY bus tracing.

RAM is read only for the test player's aiming and diagnostics. No game-state,
input-port or invulnerability writes; no stages skipped or loaded save states.
Uses AltirraSDL physical-key events; frontend_tcp.c changes IPC transport only.
"""
from pathlib import Path
import argparse,gzip,hashlib,json,os,re,socket,subprocess,sys,tempfile,time,wave
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,os.environ['ALTIRRA_BRIDGE_SDK'])
from altirra_bridge import AltirraBridge
from emulator import make_config
from play_campaign import Player
P=argparse.ArgumentParser();P.add_argument('--out',type=Path,required=True);P.add_argument('--frames',type=int,default=2600);P.add_argument('--opening-delay',type=int,default=0);P.add_argument('--goal-wave',type=int,default=6);args=P.parse_args()
O=args.out.resolve();O.mkdir(parents=True,exist_ok=True);S=json.loads((R/'build/symbols.json').read_text());car=R/'build/Phoenix-First-Flight.car'
private=tempfile.TemporaryDirectory(prefix='phoenix-live-audio-');d=Path(private.name);make_config(d)
logpath=d/'frontend.log';log=logpath.open('w');p=subprocess.Popen([os.environ['ALTIRRA_SDL'],'--headless','--test-mode','--renderer','sdlrenderer','--bridge=tcp:127.0.0.1:0','--hardware','5200','--memsize','16k','--kernelref','Original Atari 5200 four-port BIOS','--ntsc','--cart',str(car)],stdout=log,stderr=log,env=dict(os.environ,SDL_AUDIODRIVER='dummy',SDL_VIDEODRIVER='dummy',XDG_CONFIG_HOME=str(d/'config'),LD_PRELOAD=os.environ['ALTIRRA_FRONTEND_SHIM']))
a=None;u=None;recording=False;events=[];samples=[];actions=[];writes=[];frames=400;previous=0;won=False;shield_seen=set();clear_seen=set();car_hash=hashlib.sha256(car.read_bytes()).hexdigest()
try:
 for _ in range(300):
  text=logpath.read_text();b=re.search(r'token-file: (\S+)',text);sock=re.search(r'loopback-port: ([0-9]+)',text)
  if b and sock:break
  if p.poll() is not None:raise RuntimeError('emulator exited before startup')
  time.sleep(.02)
 else:
  safe=re.sub(r'(?im)^.*token.*$', '',logpath.read_text());print(safe[-5000:]);raise RuntimeError('frontend startup timeout')
 u=socket.create_connection(('127.0.0.1',int(sock[1])),timeout=40);u.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1);uf=u.makefile('rwb',buffering=0)
 def ui(cmd):
  commands=cmd if isinstance(cmd,list) else [cmd]
  uf.write(('\n'.join(commands)+'\n').encode())
  for command in commands:
   v=json.loads(uf.readline());assert v.get('ok'),(command,v)
  return v
 ui('pause');ui('set_window_size 336 256');ui('set_speed 800')
 a=AltirraBridge.from_token_file(b[1]);a.pause();a.cold_reset();a.frame(400);a.ping()
 # Check keyboard-derived analogue input works; there is no direct pot injection.
 a.screenshot(path=str(O/'boot.png'))
 a._cmd_ok('AUDIO_RECORD start path='+str(O/'gameplay.wav'));recording=True;start_tick=a.clock()['tick'];a.pokey_trace_start(32000)
 player=Player(1);m=a.memdump(0,16384);last=None;first_live=None;start_underruns=int.from_bytes(m[0x3ef2:0x3ef4],'little')
 def drain():
  while True:
   t=a.pokey_trace_read(4096);assert t['valid'] and not t['dropped'];writes.extend(t['events'])
   if not t['queued']:break
 for f in range(0,args.frames,8):
  action=player.action(m)
  if m[S['state']]==1 and first_live is None:first_live=frames
  if first_live is not None and frames<first_live+args.opening_delay:action&=~4
  # Exercise one ordinary shield button press during the opening wave.
  if first_live is not None and 336<=frames-first_live<344:action|=8
  changed=action!=previous
  if changed:
   commands=[]
   for bit,key in {1:'Right',2:'Left',4:'Left Ctrl',8:'Left Shift'}.items():
    if (action^previous)&bit:commands.append(f'physical_key {"down" if action&bit else "up"} {key}')
   commands.append('wait_frames 1');ui(commands);a.pause()
  actions.append([frames,8,action]);previous=action;a.frame(8-int(changed));a.ping();frames+=8;m=a.memdump(0,16384)
  tick=a.clock()['tick'];key=(m[S['wave']],m[S['state']],m[S['lives']],m[S['boss_status']])
  row=dict(frame=int.from_bytes(m[S['frames']:S['frames']+4],'little'),tick=tick,wave=key[0],state=key[1],lives=key[2],boss=key[3],mode=m[S['large_mode']],ship_x=m[S['raw_ship_x']],pot=m[S['stick_x']],audio_head=m[S['audio_head']],audio_tail=m[S['audio_tail']],sound_a=m[S['g_sound_a']],sound_b=m[S['g_sound_b']],music_ticks=int.from_bytes(m[S['music_ticks']:S['music_ticks']+2],'little'),audio_ticks=int.from_bytes(m[S['audio_ticks']:S['audio_ticks']+2],'little'),queue=list(m[0x3e80:0x3ec8]),audible=list(m[0x3e60:0x3e69]),audio_state=list(m[0x3e00:0x3e50]),late=int.from_bytes(m[S['late_frames']:S['late_frames']+2],'little'),layout=m[S['layout_faults']],underruns=int.from_bytes(m[0x3ef2:0x3ef4],'little'),wave_wait=m[S['wave_wait']],wipe=m[S['wipe_timer']],bird_count=m[S['audio_bird_count']],bird_stage=m[S['audio_bird_stage']],survivors=m[S['aliens_left']],shapes=list(m[S['enemy_shape']:S['enemy_shape']+16]),enemy_on=list(m[S['enemy_on']:S['enemy_on']+16]),entrance=m[S['entrance_timer']])
  samples.append(row)
  if key!=last:
   events.append({k:row[k] for k in ['frame','tick','wave','state','lives','boss','ship_x','pot']});print(events[-1],flush=True);last=key;a.screenshot(path=str(O/f'event-{frames:06}.png'))
  if f%160==0:drain()
  if f%960==0:print('progress',row['frame'],'wave',row['wave'],'underruns',row['underruns']-start_underruns,flush=True)
  pose=m[S['shield_pmg_pose']];shield_key=(row['wave'],row['lives'],pose)
  if pose<4 and row['state']==1 and shield_key not in shield_seen:
   shield_seen.add(shield_key);prefix=O/f"shield-w{row['wave']}-l{row['lives']}-p{pose}";a.screenshot(path=str(prefix)+'.png');Path(str(prefix)+'.bin').write_bytes(m)
  if row['wave_wait'] and row['wave'] not in clear_seen:
   clear_seen.add(row['wave']);print('wave clear',row['frame'],row['wave'],'control',row['sound_a'],row['sound_b'],flush=True)
  if row['wave']>=args.goal_wave:
   won=True
   if f>160:break
 drain();a.pokey_trace_stop();end_tick=a.clock()['tick'];a._cmd_ok('AUDIO_RECORD stop');recording=False
 with wave.open(str(O/'gameplay.wav')) as w:duration=w.getnframes()/w.getframerate()
 assert abs(duration-(end_tick-start_tick)/1789772.5)<.1,(duration,(end_tick-start_tick)/1789772.5)
 bus=[e for e in writes if e['chip']==1 and e['reg']==1];gaps=[]
 for x,y in zip(bus,bus[1:]):
  delta=y['tick']-x['tick'];missing=max(0,round(delta/29868)-1)
  if missing:gaps.append(dict(tick=x['tick'],missing=missing,clocks=delta))
 report=dict(method=__doc__,car_sha256=car_hash,completed_first_cycle=won,events=events,audio_duration_s=duration,start_tick=start_tick,end_tick=end_tick,audio_publishes=len(bus),missing_audio_updates=sum(g['missing'] for g in gaps),audio_gaps=gaps,audio_underruns=int.from_bytes(m[0x3ef2:0x3ef4],'little')-start_underruns,max_gap_clocks=max((y['tick']-x['tick'] for x,y in zip(bus,bus[1:])),default=0),final_counters=list(m[0x300:0x330]))
 (O/'playthrough.json').write_text(json.dumps(report,indent=2));(O/'controller-inputs.json').write_text(json.dumps(actions))
 with gzip.open(O/'sound-trace.json.gz','wt') as z:json.dump(dict(samples=samples,writes=writes),z)
 print('RESULT',json.dumps({k:report[k] for k in ['car_sha256','completed_first_cycle','audio_duration_s','missing_audio_updates','max_gap_clocks']}),flush=True)
finally:
 if a:
  try:
   if recording:a._cmd_ok('AUDIO_RECORD stop')
   a.quit()
  except Exception:pass
 try:p.wait(timeout=3)
 except subprocess.TimeoutExpired:p.kill();p.wait()
 if u:u.close()
 log.close();private.cleanup()
