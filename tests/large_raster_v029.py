"""Inspect real large-wave ANTIC output against the published display buffer.
Stages/invulnerability are explicit fixtures. The emulator runs the original
BIOS and cartridge normally between samples. Stop before VBI publication so
RAM and the finished raster refer to the same picture.
"""
from pathlib import Path
import argparse,hashlib,io,json,os,re,subprocess,sys,tempfile,time
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1]
P=argparse.ArgumentParser();P.add_argument('--out',type=Path,required=True);P.add_argument('--samples',type=int,default=200);P.add_argument('--check',action='store_true');args=P.parse_args();O=args.out;O.mkdir(parents=True,exist_ok=True)
S=json.loads((R/'build/symbols.json').read_text());B=Path(os.environ['ALTIRRA_BRIDGE_PACKAGE']);sys.path.insert(0,str(B/'sdk/python'))
from altirra_bridge import AltirraBridge
private=tempfile.TemporaryDirectory(prefix='phoenix-large-');logpath=Path(private.name)/'server.log';log=logpath.open('w')
p=subprocess.Popen([str(B/'AltirraBridgeServer'),'--machine=5200','--memory=16K','--bridge=tcp:127.0.0.1:0'],stdout=log,stderr=log,env=dict(os.environ,SDL_AUDIODRIVER='dummy'))
def decode(m,pal):
 b=m[S['front_buffer']];pens=np.zeros((200,128),np.uint8)
 for row in range(25):
  font=(0x1800,0x2000,0x3000)[min(row//8,2)]+b*1024
  for col in range(32):
   c=m[0x2800+b*1024+row*32+col]
   for y in range(8):
    v=m[font+(c&127)*8+y]
    for x in range(4):
     pen=v>>(6-x*2)&3;pens[row*8+y,col*4+x]=4 if pen==3 and c&128 else pen
 colors=np.empty((200,5),np.uint8);colors[:]=[0,170,236,86,70]
 commands=m[0x3dc0+b*32:0x3dc0+b*32+25]
 for row,c in enumerate(commands):
  if c&128:
   start=row*8+((c>>2)&7);colors[start:]=[0,*[(170,236,86),(130,44,14),(14,44,100)][c&3],70]
 codes=colors[np.arange(200)[:,None],pens]
 return np.repeat(pal[codes],2,1),pens,list(commands)
try:
 for _ in range(100):
  match=re.search(r'token-file: (\S+)',logpath.read_text())
  if match:break
  time.sleep(.05)
 a=AltirraBridge.from_token_file(match[1]);a.pause();a.config('video','ntsc');a.config('kernel',os.environ['ATARI5200_BIOS']);a.boot(str(R/'build/Phoenix-First-Flight.car'));a.frame(500)
 a.joy(0,fire=True);a.frame(8);a.joy(0,fire=False);a.frame(480)
 pal=np.frombuffer(a.palette(),np.uint8).reshape(256,3);(O/'palette.bin').write_bytes(pal.tobytes());results=[];timing=[]
 for wave in (3,4):
  a.bp_set(S['simulation_update']);a.cycles(240000);assert int(a.regs()['PC'][1:],16)==S['simulation_update'];a.bp_clear_all()
  values={'wave':wave-1,'cycle_stage':wave-2,'wave_wait':1,'enemy_on':[0]*16,'display_enemy_on':[0]*16,'aliens_left':0,'entrance_timer':0,'entrance_handoff':0,'wipe_timer':0,'state':1,'large_mode':0,'boss_status':0,'boss_entrance_shown':0,'shield_pose':255,'shield_locked':0,'shield_count':0,'bomb_on':[0]*5,'invuln':255,'lives':3}
  for k,v in values.items():a.memload(S[k],bytes(v if isinstance(v,list) else [v]))
  for _ in range(180):
   a.frame(1)
   if a.peek(S['large_shown'])[0]==wave-2 and a.peek(S['wave'])[0]==wave:break
  else:raise AssertionError('large wave did not publish')
  a.frame(3)
  before=a.memdump(0,16384);trace=[];a.pokey_trace_start(32000)
  def drain():
   while True:
    tr=a.pokey_trace_read(4096);assert tr['valid'] and not tr['dropped'];trace.extend(tr['events'])
    if not tr['queued']:break
  for i in range(args.samples):
   a.poke(S['invuln'],255);a.frame(7)
   a.bp_set(S['nmi_handler']);a.cycles(40000);assert int(a.regs()['PC'][1:],16)==S['nmi_handler'];a.bp_clear_all()
   m=a.memdump(0,16384);gt=a.hwstate()['gtia'];png=a.screenshot();actual=np.asarray(Image.open(io.BytesIO(png)).convert('RGB'))[24:224,40:296]
   expected,pens,commands=decode(m,pal)
   # Compare the whole 200-scanline playfield, including the lower font.
   actual=actual[:200];expected=expected[:200]
   # Hardware projectiles legitimately cover bird pixels. Exclude only
   # occupied PMG bits, using the actual hardware positions and DMA bytes.
   pmg=np.zeros((200,256),bool)
   for n in range(4):
    hp=int(gt[f'HPOSP{n}'].lstrip('$'),16);xx=(hp-48)*2-32
    for yy in range(200):
     v=m[0x1400+n*256+yy+40]
     for bit in range(8):
      if v&(128>>bit):
       for dx in range(2):
        px=xx+bit*2+dx
        if 0<=px<256:pmg[yy,px]=True
    hp=int(gt[f'HPOSM{n}'].lstrip('$'),16);xx=(hp-48)*2-32
    for yy in range(200):
     if m[0x1300+yy+40]&(2<<(n*2)):
      for px in range(max(0,xx),min(256,xx+2)):pmg[yy,px]=True
   missing=(np.any(expected,2)&~np.any(actual,2));extra=(~np.any(expected,2)&np.any(actual,2));color=(np.any(actual!=expected,2)&np.any(expected,2)&np.any(actual,2))
   missing&=~pmg;extra&=~pmg;color&=~pmg
   row=dict(wave=wave,sample=i,missing=int(missing.sum()),extra=int(extra.sum()),color=int(color.sum()),missing_rows=np.where(missing.any(1))[0].tolist(),color_rows=np.where(color.any(1))[0].tolist(),poses=list(m[S['large_pose']:S['large_pose']+8]),commands=commands,late=int.from_bytes(m[S['late_frames']:S['late_frames']+2],'little'))
   results.append(row)
   if i%10==0 or row['missing'] or row['color']:
    prefix=O/f'wave{wave}-{i:03}';prefix.with_suffix('.png').write_bytes(png);prefix.with_suffix('.bin').write_bytes(m)
   if i%20==0:drain();print(row,flush=True)
  a.pokey_trace_stop();drain();after=a.memdump(0,16384)
  ticks=[v['tick']for v in trace if v['chip']==1 and v['reg']==1];gaps=[y-x for x,y in zip(ticks,ticks[1:])]
  def delta(name,n):return (int.from_bytes(after[S[name]:S[name]+n],'little')-int.from_bytes(before[S[name]:S[name]+n],'little'))%(1<<(8*n))
  timing.append(dict(wave=wave,video_frames=delta('frames',4),render_fps=round(delta('fresh_commits',4)/delta('frames',4)*59.922743,3),simulation_hz=round(delta('sim_steps',4)/delta('frames',4)*59.922743,3),late_vbi=delta('late_frames',2),missing_audio_updates=sum(max(0,round(g/(262*114))-1)for g in gaps),max_audio_gap_clocks=max(gaps),layout_faults=after[S['layout_faults']]))
 report=dict(car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),method=__doc__,compared_playfield_pixels=len(results)*200*256,timing=timing,samples=results,extra=sum(r['extra']for r in results),missing=sum(r['missing']for r in results),color=sum(r['color']for r in results))
 (O/'report.json').write_text(json.dumps(report,indent=2));print('TOTAL',report['missing'],report['extra'],report['color'],timing,flush=True)
 if args.check:
  assert report['missing']==report['extra']==report['color']==0
  assert all(t['late_vbi']==t['layout_faults']==t['missing_audio_updates']==0 for t in timing)
finally:p.terminate();p.wait(timeout=5);log.close();private.cleanup()
