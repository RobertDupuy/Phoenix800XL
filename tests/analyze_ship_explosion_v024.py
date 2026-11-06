"""Compare native recordings statistically; do not equate noise sample phases.

Spectral distance uses equally weighted third-octave bands, after matching
steady-burst RMS. Three independently timed arcade deaths supply the reference.
Envelope distance uses 50 ms RMS windows through the full 1.5 second effect.
No processing is applied to the native recordings themselves.
"""
from pathlib import Path
import csv,json,os,wave
import numpy as np
from scipy.signal import resample_poly,welch,butter,sosfilt
from math import gcd
R=Path(__file__).resolve().parents[1];V=Path(os.environ['PHOENIX_VALIDATION']).resolve()
RATE=44100
def read(path):
 with wave.open(str(path)) as w:
  rate=w.getframerate();x=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').reshape(-1,w.getnchannels()).mean(1)
 g=gcd(rate,RATE);return resample_poly(x,RATE//g,rate//g)
def features(x):
 x=sosfilt(butter(2,40,'highpass',fs=RATE,output='sos'),x)
 core=x[round(.03*RATE):round(.23*RATE)];scale=np.std(core);x=x/max(scale,1e-9)
 f,p=welch(x[round(.03*RATE):round(.25*RATE)],RATE,nperseg=2048)
 edges=40*2**(np.arange(24)/3)
 bands=np.array([np.trapezoid(p[(f>=a)&(f<b)],f[(f>=a)&(f<b)]) for a,b in zip(edges,edges[1:])])
 energy=float(sum(bands));bands/=max(energy,1e-20)
 env=np.array([np.sqrt(np.mean(x[round(t*RATE):round((t+.05)*RATE)]**2)) for t in np.arange(0,1.5,.05)])
 # Repeating buzz produces stronger long-lag waveform correlation.
 c=core-core.mean();ac=np.correlate(c,c,'full')[len(c)-1:];ac/=max(ac[0],1e-9)
 periodic=float(np.max(np.abs(ac[round(.012*RATE):round(.05*RATE)])))
 return dict(scale=float(scale),audible=bool(scale>1),bands=bands,env=env,periodicity=periodic,centroid=float((f*p).sum()/max(p.sum(),1e-20)))

rows=list(csv.DictReader((V/'arcade-multiple/sound-writes.csv').open()));starts=[];active=False
for r in rows:
 if int(r['address'])&0xf800!=0x6000:continue
 v=bool(int(r['value'])&128)
 if v and not active:starts.append(float(r['time']))
 active=v
assert len(starts)==3
full=read(V/'arcade-multiple/gameplay.wav')
refs=[features(full[round(t*RATE):round((t+1.5)*RATE)]) for t in starts]
rb=np.mean([r['bands'] for r in refs],0);re=np.mean([r['env'] for r in refs],0)
results=[]
for file in sorted((V/'bench').glob('*.wav')):
 z=features(read(file));delta=10*np.log10(np.maximum(z['bands'],1e-10)/np.maximum(rb,1e-10))
 results.append(dict(name=file.stem,audible=z['audible'],spectral_band_error_db=float(np.mean(np.abs(delta))) if z['audible'] else None,envelope_rmse=float(np.sqrt(np.mean((z['env']-re)**2))),centroid_hz=z['centroid'],long_lag_correlation=z['periodicity'],bands=z['bands'].tolist(),envelope=z['env'].tolist()))
results.sort(key=lambda r:r['spectral_band_error_db'] if r['spectral_band_error_db'] is not None else 999)
report=dict(method=__doc__,arcade_starts_s=starts,reference_centroids_hz=[r['centroid'] for r in refs],reference_long_lag_correlations=[r['periodicity'] for r in refs],reference_bands=rb.tolist(),reference_envelope=re.tolist(),results=results)
(V/'comparison.json').write_text(json.dumps(report,indent=2))
for r in results:print(r['name'], 'band error dB',round(r['spectral_band_error_db'],3) if r['audible'] else 'silent; rejected','envelope RMSE',round(r['envelope_rmse'],3),'periodicity',round(r['long_lag_correlation'],3))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.size':10})
fig,ax=plt.subplots(1,2,figsize=(10,3.7),layout='constrained')
times=np.arange(0,1.5,.05)+.025
ax[0].plot(times,re,label='Arcade (3 deaths)',color='black',lw=2)
for key,label,color in [('previous','Previous port','#be3346'),('timing-fixed','Revised port','#187eaa')]:
 row=next(r for r in results if r['name']==key);ax[0].plot(times,row['envelope'],label=label,color=color,lw=1.6)
ax[0].set(xlabel='Seconds after ship death',ylabel='RMS / initial burst RMS',title='Explosion length and fade',ylim=(0,1.3));ax[0].legend();ax[0].grid(alpha=.2)
centers=40*2**((np.arange(23)+.5)/3)
ax[1].semilogx(centers,10*np.log10(np.maximum(rb,1e-10)),label='Arcade',color='black',lw=2)
for key,label,color in [('previous','Previous port','#be3346'),('timing-fixed','Revised port','#187eaa')]:
 row=next(r for r in results if r['name']==key);ax[1].semilogx(centers,10*np.log10(np.maximum(row['bands'],1e-10)),label=label,color=color,lw=1.5)
ax[1].set(xlabel='Frequency (Hz)',ylabel='Relative band power (dB)',title='Burst frequency balance',ylim=(-55,0),xlim=(40,6000));ax[1].grid(alpha=.2)
fig.suptitle('Phoenix player-ship explosion: native MAME and Altirra recordings')
fig.savefig(V/'ship-explosion-comparison.png',dpi=160)
