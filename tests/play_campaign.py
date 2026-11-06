"""Controller-only completion attempt on AltirraSDL with the original BIOS.
Inputs use its physical-key frontend. RAM is observed for targeting and telemetry;
there are no memory writes, invulnerability, stage skips, or loaded states.
The player decides at eight-frame intervals, with ordinary fire edges and shield.
"""
from pathlib import Path
import os,sys,json,subprocess,select,re,time,shutil,random,argparse,hashlib,socket
sys.path.insert(0,os.environ['ALTIRRA_BRIDGE_SDK'])
from altirra_bridge import AltirraBridge
R=Path(__file__).resolve().parents[1]
class Frontend:
 def __init__(self,out,exe,record=False):
  self.out=out;out.mkdir(parents=True,exist_ok=True);self.frames=0;self.previous=0;self.actions=[];self.record=record
  from emulator import make_config
  make_config(out)
  self.car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest()
  ir,iw=os.pipe();orr,ow=os.pipe()
  env=dict(os.environ,XDG_CONFIG_HOME=str(out/'config'),ALTIRRA_TESTMODE_IN_FD=str(ir),ALTIRRA_TESTMODE_OUT_FD=str(ow))
  for k in ['ALTIRRA_TESTMODE_SCRIPT','ALTIRRA_TESTMODE_OUTPUT','LD_PRELOAD']:env.pop(k,None)
  if os.environ.get('ALTIRRA_FRONTEND_SHIM'):env['LD_PRELOAD']=os.environ['ALTIRRA_FRONTEND_SHIM']
  self.log=(out/'frontend.log').open('w')
  self.proc=subprocess.Popen([str(exe),'--headless','--test-mode','--renderer','sdlrenderer','--bridge=tcp:127.0.0.1:0','--hardware','5200','--memsize','16k','--kernelref','Original Atari 5200 four-port BIOS','--ntsc','--cart',str(R/'build/Phoenix-First-Flight.car')],env=env,stdout=self.log,stderr=self.log,pass_fds=(ir,ow))
  os.close(ir);os.close(ow)
  if os.environ.get('ALTIRRA_FRONTEND_SHIM'):
   os.close(iw);os.close(orr)
   for _ in range(300):
    text=(out/'frontend.log').read_text();port=re.search(r'loopback-port: ([0-9]+)',text)
    if port:break
    if self.proc.poll() is not None:raise RuntimeError('frontend startup failed')
    time.sleep(.02)
   else:raise RuntimeError('frontend startup timeout')
   self.sock=socket.create_connection(('127.0.0.1',int(port[1])),timeout=40)
   self.sock.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
   self.uw=self.sock.makefile('wb',buffering=0);self.ur=self.sock.makefile('rb',buffering=0)
  else:
   self.uw=os.fdopen(iw,'wb',buffering=0);self.ur=os.fdopen(orr,'rb',buffering=0)
  self.ui('pause');self.ui('set_speed 800');self.ui('set_window_size 336 256');self.ui('wait_frames 2')
  log=(out/'frontend.log').read_text();self.a=AltirraBridge();self.a.connect(re.search(r'listening on (tcp:\S+)',log)[1]);self.a.hello(re.search(r'\[Bridge\] token: (\S+)',log)[1]);self.a.pause()
  if record:self.start_recording()
  self.a.cold_reset();self.a.frame(400);self.a.ping();self.frames=400
  self.a.screenshot(path=str(out/'boot.png'))
 def ui(self,cmd):
  self.uw.write((cmd+'\n').encode())
  if not select.select([self.ur],[],[],40)[0]:raise RuntimeError('UI timeout '+cmd)
  r=json.loads(self.ur.readline());assert r.get('ok'),(cmd,r)
  return r
 def start_recording(self):
  def click(w,l):self.ui(f'click "{w}" "{l}"');self.ui('wait_frames 5')
  def enter(w,l,s,submit=False):
   click(w,l);self.ui('key ctrl+a');self.ui('wait_frames 3');self.ui('send_text '+str(s));self.ui('wait_frames 3')
   if submit:self.ui('key enter');self.ui('wait_frames 5')
  self.ui('file_dialog_builtin on');self.ui('set_window_size 1280 900');self.ui('wait_frames 5')
  click('##MainMenuBar','Record');click('Record###Menu_00','Record Video...');click('Record Video','Record')
  enter('Save File','##path',self.out,True);enter('Save File','##filename','native-capture.avi');click('Save File','Save')
  self.ui('set_window_size 336 256');self.a.pause()
 def step(self,action,n=8):
  keys={1:'Right',2:'Left',4:'Left Ctrl',8:'Left Shift'};changed=action!=self.previous
  if changed:
   for bit,key in keys.items():
    if (action^self.previous)&bit:self.ui(f'physical_key {"down" if action&bit else "up"} {key}')
   self.ui('wait_frames 1');self.a.pause()
  self.actions.append([self.frames,n,action]);self.previous=action
  if n-int(changed):self.a.frame(n-int(changed))
  self.a.ping();self.frames+=n
  return self.a.memdump(0,16384)
 def close(self):
  if self.record:
   self.ui('click "##MainMenuBar" "Record"');self.ui('wait_frames 5');self.ui('click "Record###Menu_00" "Stop Recording"');self.ui('wait_frames 5')
  self.a.quit();self.proc.wait(timeout=30);self.log.close();(self.out/'controller-inputs.json').write_text(json.dumps(self.actions))
class Player:
 def __init__(self,seed):self.rng=random.Random(seed);self.prev=None;self.stepno=0
 def action(self,m):
  self.stepno+=1;fire=4 if self.stepno%2 else 0
  if m[0x80] in [0,2]:return fire
  if m[0x80]!=1 or m[0x71a] or m[0x7a2] or m[0x7a3] in [1,3,4]:return 0
  sx=m[0x730];targets=[];threats=[]
  if m[0x33c] in [1,2]:
   for i in range(8):
    if not m[0x400+i]:continue
    x=m[0x3810+i];y=m[0x3870+i]
    if x>224:x-=256
    centre=x+28
    if 24<y<210:
     vx=0 if self.prev is None else max(-1.5,min(1.5,((m[0x3810+i]-self.prev[0x3810+i]+128)%256-128)/8))
     aim=centre+vx*(212-y)/8-4
     targets.append((abs(aim-sx)*.65+(200-y)*.15,aim))
     if y>168:threats.append((centre,max(0,(210-y)/1.0),24))
  else:
   for i in range(16):
    if not m[0x400+i]:continue
    x=m[0x430+i];y=m[0x440+i]
    if 24<y<212:
     aim=x+4;targets.append((abs(aim-sx)*.8+(200-y)*.12,aim))
     if y>180:threats.append((x+8,(216-y)/2,12))
  aim=100 if m[0x33c]==3 else (min(targets)[1] if targets else 100)
  aim=max(14,min(190,aim))
  for i in range(5):
   if m[0x480+i] and m[0x4b8+i]>140:threats.append((m[0x4b0+i],(216-m[0x4b8+i])/2,7))
  options=[]
  for d in [-1,0,1]:
   x=max(12,min(192,sx+d*14));cost=abs(x-aim)*.055+abs(d)*.02
   for tx,tt,r in threats:cost+=max(0,1-abs(x-tx)/(r+8))*max(0,38-tt)*.9
   options.append((cost,d))
  d=min(options)[1];danger=any(tt<20 and abs(tx-sx)<r+5 for tx,tt,r in threats)
  shield=8 if danger and m[0x37a]==0 else 0
  self.prev=m
  return (1 if d>0 else 2 if d<0 else 0)|fire|shield
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--exe',type=Path,required=True);p.add_argument('--frames',type=int,default=48000);p.add_argument('--opening-delay',type=int,default=0);p.add_argument('--seed',type=int,default=1);p.add_argument('--record',action='store_true');p.add_argument('--goal-wave',type=int,default=6);args=p.parse_args()
 out=args.out.resolve();e=Frontend(out,args.exe.resolve(),args.record);player=Player(args.seed);trace=[];events=[];escort_shot_hits=[];last=None;four_seen=False;safe_entries=[];first_live=None;m=e.a.memdump(0,16384);won=False;wall=time.monotonic()
 try:
  for f in range(0,args.frames,8):
   previous=m
   a=player.action(m)
   if m[0x80]==1 and first_live is None:first_live=e.frames
   if first_live is not None and e.frames<first_live+args.opening_delay:a&=~4
   m=e.step(a)
   if m[0x7eb:0x7ed]!=previous[0x7eb:0x7ed]:
    safe_entries.append(dict(frame=e.frames,wave=m[0x83],ship_x=m[0x730],counter=int.from_bytes(m[0x7eb:0x7ed],'little'),state=m[0x80]))
   if not four_seen and m[0x33c]==3 and m[0x7a3]==2 and all(m[0x4d0+i] and m[0x410+i]<208 and 32<=m[0x420+i]<232 for i in range(4)):
    e.a.screenshot(path=str(out/'four-escorts.png'));four_seen=True
   key=(m[0x83],m[0x80],m[0x82],m[0x7a3])
   if previous[0x33c]==m[0x33c]==3 and previous[0x7a3]==m[0x7a3]==2 and previous[0x80]==m[0x80]==1:
    for slot in range(4):
     # The shield/body collision region begins at Y=194. A disappearing bird
     # well above it during live boss combat is an observed shot kill.
     if previous[0x400+slot] and not m[0x400+slot] and 32<previous[0x440+slot]<176 and 32<m[0x440+slot]<176:
      hit=dict(frame=e.frames,slot=slot,x=previous[0x430+slot],y=previous[0x440+slot],shot_before=list(previous[0xa6:0xa8]))
      escort_shot_hits.append(hit);print('escort shot hit',hit,flush=True)
      e.a.screenshot(path=str(out/f'escort-hit-{e.frames:06}.png'))
   if key!=last:
    event=dict(frame=e.frames,wave=m[0x83],state=m[0x80],lives=m[0x82],boss=m[0x7a3],score=list(m[0xc0:0xc6]));events.append(event);last=key;print(event,flush=True)
    e.a.screenshot(path=str(out/f'event-{e.frames:06}.png'))
   if f%240==0:trace.append([e.frames,list(m[0x300:0x330]),list(m[0x7a0:0x7b0])])
   if m[0x83]>=args.goal_wave:
    won=True
    for _ in range(80):m=e.step(0)
    break
  print('complete',won,'wall seconds',time.monotonic()-wall,flush=True)
 finally:
  e.close();report=dict(completed_first_cycle=any(v['wave']>=6 for v in events),completed_requested_route=won,goal_wave=args.goal_wave,requested_step_frames=e.frames,video_frames=int.from_bytes(m[0x300:0x304],'little'),events=events,escort_shot_hits=escort_shot_hits,four_escorts_visible=four_seen,safe_return_events=safe_entries,telemetry=trace,car_sha256=e.car_sha256,method=__doc__,final_counters=list(m[0x300:0x330]));(out/'playthrough.json').write_text(json.dumps(report,indent=2))
