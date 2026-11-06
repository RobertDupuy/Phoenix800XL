"""Same-latch comparison: recovered arcade circuit vs actual Altirra POKEY.

This is an isolated sound bench, not a cabinet recording or gameplay video.
The reference is the checked-in MAME-derived C circuit/TMS implementation.
The port register streams execute each ROM's real 6502 audio_tick routine.
AltirraSDL renders those streams on its POKEY, with no waveform synthesis here.
Dependencies: ALTIRRA_SDL, ALTIRRA_BRIDGE_PACKAGE, ATARI5200_BIOS; optional
PHOENIX_PREVIOUS_ROOT selects a previously built source tree for before/after.
"""
from pathlib import Path
import ctypes,hashlib,importlib.util,json,os,re,struct,subprocess,sys,tempfile,time,wave
import numpy as np
from scipy.signal import butter,sosfilt,welch
R=Path(__file__).resolve().parents[1];O=R/'evidence/v023/explosion';O.mkdir(parents=True,exist_ok=True)
SDK=Path(os.environ['ALTIRRA_BRIDGE_PACKAGE']).resolve();sys.path.insert(0,str(SDK/'sdk/python'))
from altirra_bridge import AltirraBridge
CASES={'death':(180,lambda f:(143 if f<64 else 15,15))}
def wav(path,x,rate):
 with wave.open(str(path),'wb') as w:w.setparams((1,2,rate,0,'NONE','not compressed'));w.writeframes(np.asarray(x,dtype='<i2').tobytes())
def metrics(path):
 with wave.open(str(path)) as w:rate=w.getframerate();x=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(float)
 # Remove DC/sub-audible capacitor offsets before comparing RMS or spectra.
 x=sosfilt(butter(2,40,'highpass',fs=rate,output='sos'),x)
 f,p=welch(x,rate,nperseg=min(8192,len(x)));energy=p.sum();rms=np.sqrt(np.mean(x*x));
 return dict(duration_s=round(len(x)/rate,3),rms=round(float(rms),2),spectral_centroid_hz=round(float((f*p).sum()/max(energy,1e-10)),1),energy_above_2khz_pct=round(float(p[f>2000].sum()/max(energy,1e-10)*100),2))
def model(root,tag):
 spec=importlib.util.spec_from_file_location('cpu_'+tag,root/'tests/cpu_model.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
profiles={'updated':R}
if os.environ.get('PHOENIX_PREVIOUS_ROOT'):profiles['previous']=Path(os.environ['PHOENIX_PREVIOUS_ROOT']).resolve()
streams={};hashes={};cycle_max={}
for tag,root in profiles.items():
 mod=model(root,tag);hashes[tag]=hashlib.sha256((root/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest();peak=0
 for name,(n,fn) in CASES.items():
  t=mod.Model();t.init();m=t.m.b;m[0x3e00:0x3e50]=bytes(80)
  for _ in range(122):m[mod.S['g_sound_a']]=m[mod.S['g_sound_b']]=15;t.call('audio_tick')
  regs=[];fraction=0
  for f in range(n):
   ca,cb=fn(int(f*61/60));m[mod.S['g_sound_a']]=ca;m[mod.S['g_sound_b']]=cb;fraction+=1217
   for _ in range(1+(fraction>>16)):peak=max(peak,t.call('audio_tick'))
   fraction&=65535;regs.append(list(m[0x3e60:0x3e68])+[m[0x3e68]])
  streams[(tag,name)]=regs
 cycle_max[tag]=peak
with tempfile.TemporaryDirectory(prefix='phoenix-sound-bench-') as d:
 d=Path(d);lib=d/'reference.so'
 subprocess.run(['cc','-O2','-shared','-fPIC',*[str(R/'reference/c'/n) for n in ['sound.c','sound_discrete.c','tms36xx.c','mame_lofi_resampler.c']],'-lm','-o',str(lib)],check=True)
 ref=ctypes.CDLL(str(lib));buf=(ctypes.c_int16*1024)();ref.sound_render_frame.argtypes=[ctypes.POINTER(ctypes.c_int16)]
 for name,(n,fn) in CASES.items():
  ref.sound_init()
  for _ in range(120):ref.sound_set_frame_sample_index(0);ref.sound_write_control_a(15);ref.sound_write_control_b(15);ref.sound_render_frame(buf)
  pcm=[]
  for f in range(n):
   ca,cb=fn(int(f*61/60));ref.sound_set_frame_sample_index(0);ref.sound_write_control_a(ca);ref.sound_write_control_b(cb);count=ref.sound_render_frame(buf);pcm.extend(buf[:count])
  wav(O/('arcade-reference-'+name+'.wav'),pcm,48000)
 # Minimal 5200 cart keeps the CPU idle while POKEY receives real ROM-produced
 # register values. Firmware still executes the ordinary console boot.
 rom=bytearray(32768);code=bytes([0x78,0xa9,0,0x8d,0x0e,0xd4,0x8d,0,0xd4,0xa9,2,0x8d,0x0f,0xe8,0x4c,0x0e,0x40]);rom[:len(code)]=code
 original=(R/'build/Phoenix-First-Flight.rom').read_bytes();rom[-24:]=original[32768-24:32768];rom[-2:]=struct.pack('<H',0x4000)
 cart=d/'sound-bench.car';cart.write_bytes(b'CART'+struct.pack('>III',4,sum(rom)&0xffffffff,0)+rom)
 logpath=d/'private.log';log=logpath.open('w');p=subprocess.Popen([os.environ['ALTIRRA_SDL'],'--headless','--test-mode','--renderer','sdlrenderer','--bridge=tcp:127.0.0.1:0'],stdout=log,stderr=log,env=dict(os.environ,SDL_AUDIODRIVER='dummy',SDL_VIDEODRIVER='dummy',XDG_CONFIG_HOME=str(d/'config')))
 try:
  for _ in range(200):
   match=re.search(r'token-file: (\S+)',logpath.read_text())
   if match:break
   if p.poll() is not None:raise RuntimeError('emulator exited')
   time.sleep(.025)
  else:raise RuntimeError('emulator startup timeout')
  a=AltirraBridge.from_token_file(match[1]);a.pause();a.config('machine','5200');a.config('memory','16K');a.config('video','ntsc');a.config('kernel',os.environ['ATARI5200_BIOS']);a.boot(str(cart));a.frame(500)
  assert a.regs()['PC'] in ('$400e','$400E','$4011'),a.regs()
  print('POKEY bench ready',flush=True)
  example=None
  for (tag,name),regs in streams.items():
   a.memload(0xe800,bytes(9));a.frame(30)
   dest=O/(tag+'-'+name+'.wav');a._cmd_ok('AUDIO_RECORD start path='+str(dest))
   for r in regs:a.memload(0xe800,bytes(r));a.frame(1)
   a.ping();a._cmd_ok('AUDIO_RECORD stop')
   with wave.open(str(dest)) as w:duration=w.getnframes()/w.getframerate()
   assert abs(duration-len(regs)/59.922743)<.12,(tag,name,duration)
   if name=='eight_small_birds' and tag=='updated':example=a.audio_state()
   print(tag,name,flush=True)
  a.quit()
 finally:
  try:p.wait(timeout=3)
  except subprocess.TimeoutExpired:p.kill();p.wait()
  log.close()
report=dict(method=__doc__,car_sha256=hashes,maximum_audio_tick_cpu_cycles=cycle_max,high_clock_example=example,cases={})
for name in CASES:
 report['cases'][name]={tag:metrics(O/(tag+'-'+name+'.wav')) for tag in ['arcade-reference',*profiles]}
(O/'sound-study.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
