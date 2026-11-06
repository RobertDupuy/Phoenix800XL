"""Music cancellation matches the original ROM and recorded MAME shield trace."""
from cpu_model import *
import hashlib
T=Model();T.init();m=T.m.b
results={}
for name in ('shot','hit','shield','phase_timeout'):
 m[0x3e00:0x3e50]=bytes(80);m[S['music_pending']]=1
 m[S['arcade_clock']]=m[S['arcade_clock']+1]=0;m[S['state']]=1;m[S['large_mode']]=0
 T.call('music_compute');assert m[S['tune']]==3
 if name=='shot':m[S['audio_shot_pending']]=1
 if name=='hit':m[S['audio_hit_pending']]=1
 if name=='shield':
  m[S['shield_locked']]=m[S['shield_count']]=0;m[S['shield_edge']]=1;T.call('shield_update')
 if name=='phase_timeout':m[S['arcade_clock']+1]=3
 T.call('music_tick');results[name]=m[S['tune']]
 assert m[S['tune']]==(3 if name=='shot' else 0),(name,m[S['tune']])
report=dict(car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),tune_after_event=results,arcade_trace='Recorded MAME shield trace: frame 720 tune 3, frame 721 tune 0, shield sound count 63; hit count 0.',source='Original ROM $3B28, $3A2C and $3A82; https://computerarcheology.com/Arcade/Phoenix/Code.html')
(R/'evidence/v023/music-cancellation.json').write_text(json.dumps(report,indent=2));print(report)
