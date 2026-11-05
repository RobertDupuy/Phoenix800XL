"""Original-BIOS, cold-boot validation. No game RAM or input-port injection.

Physical-key frontend commands drive controls; bridge reads observe timing/RAM.
Set ALTIRRA_BRIDGE_SDK, ALTIRRA_SDL and ATARI5200_BIOS to local installations.
"""
from pathlib import Path
import argparse, hashlib, json, os, shutil, socket, subprocess, sys, time
sys.path.insert(0, os.environ['ALTIRRA_BRIDGE_SDK'])
from altirra_bridge import AltirraBridge
ROOT=Path(__file__).resolve().parents[1]
BIOS_SHA='06b250f18983d058c0f156ce7ee88ae48b6eaf11e6f10f21dccf6ac7ffb6a6af'

def make_config(out):
 bios=Path(os.environ['ATARI5200_BIOS']).resolve()
 assert hashlib.sha256(bios.read_bytes()).hexdigest()==BIOS_SHA
 fid=14695981039346656037
 for c in str(bios).lower():fid=((fid^ord(c))*1099511628211)&0xffffffffffffffff
 fid|=0x8000000000000000
 sections={
  'User\\AltirraSDL':{'ShownSetupWizard':1},
  'User\\AltirraSDL\\Profiles':{'Defaults inited':1,'Current profile':1},
  'User\\AltirraSDL\\Profiles\\00000001':{'_Name':'First Flight assembly test','_Visible':1,
   '_Category Mask':'hardware,firmware,inputMaps,input,acceleration',
   '_Saved Category Mask':'hardware,firmware,inputMaps,input,acceleration',
   'Hardware mode':2,'Memory mode':7,'Input: Active map names':'Keyboard -> 5200 Controller (absolute; port 1)',
   'Kernel: Fast boot enabled':0},
  f'User\\AltirraSDL\\Firmware\\Available\\{fid:016X}':{'Name':'Original Atari 5200 four-port BIOS','Path':str(bios),'Type':'kernel5200','Flags':0}}
 cfg=out/'config/altirra/settings.ini';cfg.parent.mkdir(parents=True,exist_ok=True)
 cfg.write_text('\n'.join('['+s+']\n'+'\n'.join('"'+k+'" = '+(str(v) if isinstance(v,int) else '"'+v+'"') for k,v in d.items()) for s,d in sections.items())+'\n')

class Emulator:
 def __init__(self,out,car,controls=False,boot_frames=900,extra_commands=None,capture_audio=None):
  self.out=out;out.mkdir(parents=True,exist_ok=True);self.actions=[]
  make_config(out)
  commands=out/'commands.txt';responses=out/'responses.jsonl'
  responses.unlink(missing_ok=True)
  cmd=['set_window_size 336 256','set_speed 800',f'wait_frames {min(180,boot_frames)}',f'screenshot {out}/bios.png']
  if boot_frames>180:cmd.append(f'wait_frames {boot_frames-180}')
  if controls:
   cmd+=['physical_key down 1','wait_frames 12','physical_key up 1','wait_frames 120',
    'physical_key down F2','wait_frames 24','physical_key up F2','wait_frames 900']
   for k in range(12):
    direction='Left' if k%2==0 else 'Right'
    cmd+=[f'screenshot {out}/control-{k:02d}-before.png',f'physical_key down {direction}','wait_frames 24',
     f'screenshot {out}/control-{k:02d}-held.png',f'physical_key up {direction}','wait_frames 6',
     f'screenshot {out}/control-{k:02d}-released.png','wait_frames 18',f'screenshot {out}/control-{k:02d}-settled.png']
   for k in range(12):cmd+=['physical_key down Left Ctrl','wait_frames 6','physical_key up Left Ctrl','wait_frames 6']
  if extra_commands:cmd+=extra_commands
  cmd+=['pause'];self.actions=cmd
  commands.write_text('\n'.join(cmd)+'\n')
  env=dict(os.environ,XDG_CONFIG_HOME=str(out/'config'),ALTIRRA_TESTMODE_SCRIPT=str(commands),ALTIRRA_TESTMODE_OUTPUT=str(responses))
  self.log=(out/'frontend.log').open('w')
  self.proc=subprocess.Popen([os.environ['ALTIRRA_SDL'],'--headless','--test-mode','--renderer','sdlrenderer',
    '--bridge=tcp:127.0.0.1:0','--hardware','5200','--memsize','16k','--kernelref',
    'Original Atari 5200 four-port BIOS','--ntsc','--cart',str(car)],env=env,stdout=self.log,stderr=self.log)
  deadline=time.monotonic()+int(os.environ.get('ALTIRRA_TEST_TIMEOUT','900'))
  audio_client=None
  while True:
   log=(out/'frontend.log').read_text()
   import re
   match=re.search(r'token-file: (\S+)',log)
   if match and capture_audio and audio_client is None:
    audio_client=AltirraBridge();audio_client.connect(re.search(r'listening on (tcp:\S+)',log)[1]);audio_client.hello(re.search(r'\[Bridge\] token: (\S+)',log)[1]);audio_client.pause()
    self.audio_start_tick=audio_client.clock()['tick']
    result=audio_client._send_command('AUDIO_RECORD start path='+str(capture_audio))
    assert result['ok'],result
    audio_client.resume()
   if match and responses.exists() and len(responses.read_text().splitlines())>=len(cmd):break
   if self.proc.poll() is not None or time.monotonic()>deadline:
    self.proc.terminate();raise RuntimeError('Altirra frontend script did not complete before exit/host timeout; see frontend.log')
   time.sleep(.05)
  assert all(json.loads(line).get('ok') for line in responses.read_text().splitlines())
  # Each isolated test process can have the same PID. Read this process's
  # address/token from its private log, not the shared PID-named token file.
  if audio_client:self.a=audio_client
  else:
   self.a=AltirraBridge();self.a.connect(re.search(r'listening on (tcp:\S+)',log)[1]);self.a.hello(re.search(r'\[Bridge\] token: (\S+)',log)[1])
  self.a.pause()
  if capture_audio:
   self.audio_end_tick=self.a.clock()['tick']
   assert self.a._send_command('AUDIO_RECORD stop')['ok']
  assert hashlib.sha256(self.a.peek(0xf800,2048)).hexdigest()==BIOS_SHA
 def step(self,n):self.a.frame(n);self.a.ping()
 def shot(self,name):self.a.screenshot(path=str(self.out/(name+'.png')))
 def close(self):
  self.a.quit();self.proc.wait(timeout=20);self.log.close()
  (self.out/'physical-inputs.json').write_text(json.dumps(self.actions,indent=2))
