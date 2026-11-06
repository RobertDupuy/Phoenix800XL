"""Native MAME/Altirra comparison; no synthetic audio or perceptual-fidelity score.

The controlled replay feeds recorded arcade latch writes to each cartridge's
6502 audio code. Separate controller-only recordings verify integration.
Presentation copies use resampling and a single gain, with no equalization.
"""
from pathlib import Path
import argparse,csv,gzip,hashlib,json,subprocess,wave
from math import gcd
import numpy as np
from scipy.signal import butter,resample_poly,sosfilt,welch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image,ImageDraw,ImageFont

P=argparse.ArgumentParser()
for k in ('reference','bench','before-live','after-live','out'):P.add_argument('--'+k,type=Path,required=True)
A=P.parse_args();O=A.out.resolve();O.mkdir(parents=True,exist_ok=True);RATE=44100

def read(path):
 with wave.open(str(path)) as w:
  rate=w.getframerate();x=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').reshape(-1,w.getnchannels()).mean(1)/32768
 q=gcd(rate,RATE)
 return resample_poly(x,RATE//q,rate//q)

def write(path,x):
 assert np.max(np.abs(x))<1
 with wave.open(str(path),'wb') as w:
  w.setnchannels(1);w.setsampwidth(2);w.setframerate(RATE)
  w.writeframes(np.round(x*32767).astype('<i2').tobytes())

def native_crop(source,dest,start,duration):
 with wave.open(str(source)) as w:
  params=w.getparams();first=round(start*w.getframerate());count=round(duration*w.getframerate());w.setpos(first);data=w.readframes(count)
 with wave.open(str(dest),'wb') as w:w.setparams(params);w.writeframes(data)
 return dict(source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),first_frame=first,frames=count,rate=params.framerate,channels=params.nchannels)

rows=list(csv.DictReader((A.reference/'sound-writes.csv').open()))
start=next(float(r['time']) for r in rows if int(r['address'])&0xf800==0x6000 and int(r['value'])&128)
crop=native_crop(A.reference/'gameplay.wav',O/'arcade-native.wav',start-1,3)
paths=[O/'arcade-native.wav',A.bench/'previous.wav',A.bench/'revised.wav']
labels=['Arcade / MAME','Port v0.24','Port v0.25']
tracks=[read(p)[:RATE*3] for p in paths]
hp=butter(2,40,'highpass',fs=RATE,output='sos')
normalized=[];gains=[]
for x in tracks:
 y=sosfilt(hp,x);core=np.std(y[round(1.03*RATE):round(1.23*RATE)])
 normalized.append(y/core);gains.append(.08/core)

band_rows=[]
for label,x in zip(labels,normalized):
 f,p=welch(x[round(1.40*RATE):round(1.57*RATE)],RATE,nperseg=2048)
 values=[]
 for lo,hi in [(50,200),(200,1000),(1000,4000)]:
  select=(f>=lo)&(f<hi);values.append(float(np.trapezoid(p[select],f[select])))
 band_rows.append(dict(label=label,relative_band_power=values))
for row in band_rows:
 row['band_difference_from_arcade_db']=(10*np.log10(np.array(row['relative_band_power'])/np.array(band_rows[0]['relative_band_power']))).tolist()

def gameplay(path,label):
 report=json.loads((path/'playthrough.json').read_text());trace=json.load(gzip.open(path/'sound-trace.json.gz','rt'))
 regs=[0]*9;frames=[];base=report['start_tick']
 for e in trace['writes']:
  if e['chip']!=1 or e['reg']>8:continue
  regs[e['reg']]=e['value']
  if e['reg']==8:
   tm=(e['tick']-base)/1789772.5
   low=any(regs[c]==159 and regs[c+1]&0xf0==0x80 and regs[c+1]&15 for c in range(0,8,2))
   frames.append((tm,low,list(regs)))
 death=next(e for e in report['events'] if e['state']==3)
 tm=(death['tick']-base)/1789772.5
 onset=next(f[0] for f in frames if tm-.3<f[0]<tm+.1 and f[1])
 selection=[f for f in frames if onset-.001<=f[0]<onset+1.4]
 last=max(i for i,f in enumerate(selection) if f[1]);gaps=[];gap=None
 for i in range(last+2):
  f=selection[i]
  if i<=last and not f[1] and gap is None:gap=f[0]
  elif f[1] and gap is not None:gaps.append([gap-onset,f[0]-onset]);gap=None
 active=[r for r in trace['samples'] if r['state']==1]
 assert active
 data=dict(car_sha256=report['car_sha256'],duration_s=report['audio_duration_s'],
  explosion_onset_s=onset,low_blast_gaps_s=gaps,missing_audio_updates=report['missing_audio_updates'],
  startup_empty_queue_count=active[0]['underruns'],
  active_underruns=max(r['underruns'] for r in active)-active[0]['underruns'],
  late_vbi=max(r['late'] for r in trace['samples']),layout_faults=max(r['layout'] for r in trace['samples']),
  final_wave=max(r['wave'] for r in trace['samples']),
  crop=native_crop(path/'gameplay.wav',O/(label+'-gameplay-native.wav'),onset-.25,2.5))
 return data

live=[gameplay(A.before_live,'v024'),gameplay(A.after_live,'v025')]
assert live[0]['low_blast_gaps_s'] and not live[1]['low_blast_gaps_s']
assert all(live[1][k]==0 for k in ('missing_audio_updates','active_underruns','late_vbi','layout_faults'))
bench=json.loads((A.bench/'bench.json').read_text())
assert [r['car_sha256'] for r in live]==[bench['previous']['car_sha256'],bench['updated']['car_sha256']]

fig,axes=plt.subplots(3,1,figsize=(10,7.4),layout='constrained',sharex=True,sharey=True)
for ax,label,x in zip(axes,labels,normalized):
 ax.specgram(x,NFFT=2048,Fs=RATE,noverlap=1792,cmap='magma',vmin=-65,vmax=-20,xextent=(-1,2))
 ax.set(yscale='log',ylim=(50,6000),xlim=(-.1,1.3),ylabel='Hz',title=label)
 ax.axvspan(.40,.57,facecolor='none',edgecolor='#44dfc0',linewidth=1.2)
 ax.set_yticks([100,400,1000,4000],['100','400','1k','4k'])
axes[-1].set_xlabel('Seconds after explosion; green box marks the old loss of rumble')
fig.suptitle('Ship explosion with an overlapping shot\nNative recordings, normalized to initial burst RMS',fontsize=14)
fig.savefig(O/'ship-mixing-comparison.png',dpi=150);plt.close(fig)

# Labeled 12-second listening comparison. Original WAVs remain unprocessed.
fontroot=Path('/usr/share/fonts/truetype/dejavu')
font=lambda size:ImageFont.truetype(str(fontroot/'DejaVuSans.ttf'),size)
bold=lambda size:ImageFont.truetype(str(fontroot/'DejaVuSans-Bold.ttf'),size)
for i,(label,x,gain) in enumerate(zip(labels,tracks,gains)):
 x=x.copy()*gain;edge=round(.008*RATE)
 x[:edge]*=np.linspace(0,1,edge);x[-edge:]*=np.linspace(1,0,edge)
 audio=np.concatenate([np.zeros(RATE//2),x,np.zeros(RATE//2)])
 write(O/f'part-{i}.wav',audio)
 im=Image.new('RGB',(1280,720),'#101624');d=ImageDraw.Draw(im)
 d.text((76,64),'PHOENIX  /  SHIP EXPLOSION',font=bold(30),fill='#6de2c4')
 d.text((76,157),label,font=bold(58),fill='white')
 detail=['Original arcade gameplay','Previous build: one noise voice','Revised build: blast and shot together'][i]
 d.text((78,246),detail,font=font(31),fill='#d7dce8')
 d.line((78,326,1202,326),fill='#33445b',width=2)
 d.text((78,371),'Explosion starts 1.5 seconds into this section.',font=font(26),fill='#d7dce8')
 d.text((78,421),'Listen for the low rumble beneath the returning shot.',font=font(26),fill='#d7dce8')
 d.text((78,582),'Burst loudness matched; no EQ. Raw recordings included.',font=font(23),fill='#9fadc2')
 d.text((78,626),'Port clips replay the same arcade controls through real POKEY emulation.',font=font(21),fill='#9fadc2')
 im.save(O/f'part-{i}.png')
 subprocess.run(['ffmpeg','-loglevel','error','-y','-loop','1','-framerate','30','-i',str(O/f'part-{i}.png'),'-i',str(O/f'part-{i}.wav'),'-t','4','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','256k','-movflags','+faststart',str(O/f'part-{i}.mp4')],check=True)
(O/'concat.txt').write_text(''.join("file 'part-%d.mp4'\n"%i for i in range(3)))
subprocess.run(['ffmpeg','-loglevel','error','-y','-f','concat','-safe','0','-i',str(O/'concat.txt'),'-c','copy','-movflags','+faststart',str(O/'Phoenix5200-Explosion-Comparison.mp4')],check=True)
output=dict(method=__doc__,arcade_explosion_time=start,arcade_crop=crop,
 comparison_window_after_death_s=[.40,.57],bands_hz=[[50,200],[200,1000],[1000,4000]],
 band_measurements=band_rows,live=live,presentation_gain=gains,
 presentation_edits='Mono 44.1 kHz, one constant gain per recording, 8 ms fades at outer edges one second before/two seconds after death; no EQ.',
 limitation='Independent noise phases; these measurements do not establish subjective identity. Isolated blast output is unchanged from v0.24. MAME is the reference, not a physical arcade recording.')
(O/'comparison.json').write_text(json.dumps(output,indent=2))
for row in band_rows:print(row)
for row in live:print({k:v for k,v in row.items() if k!='crop'})
for p in O.glob('part-*'):p.unlink()
(O/'concat.txt').unlink()
