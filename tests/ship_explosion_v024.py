"""Event-level regression: real damage/collision entry points select arcade durations."""
from cpu_model import *
import csv,hashlib,os

def driven_ticks(t):
 m=t.m.b;values=[]
 for _ in range(80):
  t.call('music_tick');values.append(m[S['g_sound_a']])
 return sum(bool(a&128) for a in values)

ship_cases=[]
for wave in range(1,6):
 t=Model();t.init();m=t.m.b
 m[S['wave']]=wave;t.call('wave_reset');m[S['state']]=1;m[S['invuln']]=0
 m[0x3e00:0x3e50]=bytes(80);m[S['g_sound_b']]=15
 t.call('damage_player');assert m[S['state']]==3
 assert m[S['audio_death_pending']]==16
 t.call('damage_player');assert m[S['audio_death_pending']]==16
 count=driven_ticks(t);assert count==16,(wave,count)
 ship_cases.append(dict(wave=wave,gate_ticks=count))

# Follow the real exposed-core collision route, not a manually assigned sound flag.
t=Model();t.init();m=t.m.b;m[S['wave']]=5;t.call('wave_reset')
m[S['state']]=1;m[S['boss_status']]=2;m[S['boss_scroll']]=248
m[S['boss_body']+116]=0x65;m[S['boss_body']+90]=126
m[S['shot_on']]=1;m[S['raw_shot_x']]=104;m[S['raw_shot_y']]=88
t.call('mothership_collision');assert m[S['boss_status']]==3
assert m[S['audio_death_pending']]==64
boss_ticks=driven_ticks(t);assert boss_ticks==64

rows=list(csv.DictReader(Path(os.environ['PHOENIX_ARCADE_WRITES']).open()))
runs=[];start=None;count=0
for r in rows:
 if int(r['address'])&0xf800!=0x6000:continue
 value=int(r['value']);time=float(r['time'])
 if value&128:
  if start is None:start=time;count=0
  count+=1
 elif start is not None:
  runs.append(dict(start_s=start,gate_ticks=count,gate_seconds=time-start));start=None
assert len(runs)==3 and all(r['gate_ticks']==16 for r in runs),runs
report=dict(car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),ship_cases=ship_cases,mothership_gate_ticks=boss_ticks,arcade_recorded_ship_deaths=runs,method=__doc__)
(R/'evidence/v024/ship-events.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
