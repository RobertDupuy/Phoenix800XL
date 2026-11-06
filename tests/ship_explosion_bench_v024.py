"""Player-death POKEY comparison, using each cartridge's actual damage/audio code.

The primary reference is separate, unmodified MAME gameplay. This isolated
bench tests candidate register settings only; it is not a gameplay recording.
No host synthesizer generates the POKEY audio: Altirra renders every candidate.
"""
from pathlib import Path
import csv,hashlib,importlib.util,json,os,re,struct,subprocess,sys,tempfile,time,wave
R=Path(__file__).resolve().parents[1]
O=Path(os.environ['PHOENIX_BENCH_OUT']).resolve();O.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,os.environ['ALTIRRA_BRIDGE_SDK'])
from altirra_bridge import AltirraBridge

def stream(root):
 spec=importlib.util.spec_from_file_location('model_'+root.name,root/'tests/cpu_model.py')
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 t=mod.Model();t.init();m=t.m.b;S=mod.S
 m[0x3e00:0x3e50]=bytes(80);m[S['g_sound_b']]=15
 m[S['invuln']]=0;m[S['boss_status']]=0;m[S['large_mode']]=0
 for _ in range(122):
  m[S['g_sound_a']]=15;t.call('audio_tick')
 t.call('damage_player')
 regs=[];frac=0;gate=[];cycles=[]
 for f in range(120):
  frac+=1217
  for _ in range(1+(frac>>16)):
   cycles.append(t.call('music_tick'));gate.append(m[S['g_sound_a']])
  frac&=65535
  regs.append(list(m[0x3e60:0x3e69]))
 return regs,dict(car_sha256=hashlib.sha256((root/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),death_gate_ticks=sum(bool(a&128) for a in gate),maximum_music_tick_cycles=max(cycles))

def replay(root):
 spec=importlib.util.spec_from_file_location('model_'+root.name,root/'tests/cpu_model.py')
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 t=mod.Model();t.init();m=t.m.b;S=mod.S
 m[0x3e00:0x3e50]=bytes(80);m[S['g_sound_b']]=15
 m[S['invuln']]=0;m[S['boss_status']]=0;m[S['large_mode']]=0
 t.call('damage_player');t.call('audio_controls')
 rows=list(csv.DictReader(Path(os.environ['PHOENIX_OVERLAP_SOURCE']).open()))
 events=[(float(r['time']),int(r['address']),int(r['value'])) for r in rows]
 start=next(tm for tm,addr,val in events if addr&0xf800==0x6000 and val&128)
 regs=[];frac=0;i=0;ca=cb=15;cycles=[]
 for f in range(180):
  tm=start-1+f/59.922743
  while i<len(events) and events[i][0]<=tm:
   _,addr,val=events[i]
   if addr&0xf800==0x6000:ca=val
   elif addr&0xf800==0x6800:cb=val
   i+=1
  m[S['g_sound_a']]=ca;m[S['g_sound_b']]=cb;frac+=1217
  for _ in range(1+(frac>>16)):cycles.append(t.call('audio_tick'))
  frac&=65535;regs.append(list(m[0x3e60:0x3e69]))
 return regs,dict(car_sha256=hashlib.sha256((root/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),arcade_start_s=start,replay_start_s=start-1,maximum_audio_tick_cycles=max(cycles))

factory=replay if os.environ.get('PHOENIX_OVERLAP_SOURCE') else stream
current,meta=factory(R);old,oldmeta=factory(Path(os.environ['PHOENIX_PREVIOUS_ROOT']))
profiles={'previous':old,'timing-fixed':current}
for mode in ((0x00,0x40,0x80,0xc0) if os.environ.get('PHOENIX_SWEEP','1')=='1' else ()):
 for div in (111,135,159,183,207,231):
  regs=[]
  for original in current:
   r=original.copy()
   for c in range(0,8,2):
    if r[c+1]&0xf0==0x80 and r[c+1]&15:r[c]=div;r[c+1]=(r[c+1]&15)|mode
   regs.append(r)
  profiles[f'noise-{mode:02x}-{div}']=regs

with tempfile.TemporaryDirectory(prefix='phoenix-ship-bench-') as d:
 d=Path(d);rom=bytearray(32768)
 code=bytes([0x78,0xa9,0,0x8d,0x0e,0xd4,0x8d,0,0xd4,0xa9,2,0x8d,0x0f,0xe8,0x4c,0x0e,0x40]);rom[:len(code)]=code
 original=(R/'build/Phoenix-First-Flight.rom').read_bytes();rom[-24:]=original[32744:32768];rom[-2:]=struct.pack('<H',0x4000)
 cart=d/'bench.car';cart.write_bytes(b'CART'+struct.pack('>III',4,sum(rom)&0xffffffff,0)+rom)
 logpath=d/'frontend.log';log=logpath.open('w')
 p=subprocess.Popen([os.environ['ALTIRRA_SDL'],'--headless','--test-mode','--renderer','sdlrenderer','--bridge=tcp:127.0.0.1:0'],stdout=log,stderr=log,env=dict(os.environ,SDL_AUDIODRIVER='dummy',SDL_VIDEODRIVER='dummy',XDG_CONFIG_HOME=str(d/'config')))
 try:
  for _ in range(300):
   txt=logpath.read_text();endpoint=re.search(r'listening on (tcp:\S+)',txt);token=re.search(r'\[Bridge\] token: (\S+)',txt)
   if endpoint and token:break
   if p.poll() is not None:raise RuntimeError('Altirra exited during startup')
   time.sleep(.02)
  else:raise RuntimeError('Altirra startup timed out')
  a=AltirraBridge();a.connect(endpoint[1]);a.hello(token[1]);a.pause()
  a.config('machine','5200');a.config('memory','16K');a.config('video','ntsc');a.config('kernel',os.environ['ATARI5200_BIOS']);a.boot(str(cart));a.frame(500)
  assert a.regs()['PC'].lower() in ('$400e','$4011')
  for name,regs in profiles.items():
   a.memload(0xe800,bytes(9));a.frame(30)
   dest=O/(name+'.wav');a._cmd_ok('AUDIO_RECORD start path='+str(dest))
   for r in regs:a.memload(0xe800,bytes(r));a.frame(1)
   a.ping();a._cmd_ok('AUDIO_RECORD stop')
   with wave.open(str(dest)) as w:duration=w.getnframes()/w.getframerate()
   assert abs(duration-len(regs)/59.922743)<.03,duration
   print(name,flush=True)
  a.quit()
 finally:
  try:p.wait(timeout=3)
  except subprocess.TimeoutExpired:p.kill();p.wait()
  log.close()
(O/'bench.json').write_text(json.dumps(dict(method=__doc__,previous=oldmeta,updated=meta,candidate_count=len(profiles)-2,register_stream=current),indent=2))
print(json.dumps(dict(previous=oldmeta,updated=meta,candidate_count=len(profiles)-2)),flush=True)
