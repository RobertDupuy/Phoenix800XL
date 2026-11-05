from cpu_model import *
from collections import Counter
import os
D=(R/os.environ.get('MAME_TRACE','reference/mame-large/trace.bin')).read_bytes();F=[D[i+4:i+3076] for i in range(0,len(D),3076)]
t=Model();t.init();m=t.m.b;errors=Counter();examples=[];n=0;external=[]
# One-step comparison reseeds from observed arcade state; collision/death frames
# are reported separately, never silently accepted as motion equivalence.
for f in range(2,len(F)+1):
 a,b=F[f-2:f]
 if a[0x3a4]!=3 or b[0x3a4]!=3:continue
 if not a[0x3bb] or not b[0x3bb]:continue
 if a[0x3b8] not in (5,7) or b[0x3b8]!=a[0x3b8]:continue
 if b[0x39b]!=(a[0x39b]+1)&255:continue
 if any((a[0xb70+i*8]!=0)!=(b[0xb70+i*8]!=0) for i in range(8)):continue
 m[0x3d00:0x3d40]=a[0xb70:0xbb0]
 for dest,src in [(0x3d40,0x3b9),(0x3d41,0x36d),(0x3d42,0x36e),(0x3d43,0x36f),(0x3d44,0x39b),(0x3d45,0x39a),(0x3d46,0x3b8)]:m[dest]=a[src]
 m[0x3d48:0x3d4f]=a[0xbd1:0xbd8];m[0xa5]=b[0x3c2];m[0x374]=a[0x3bb];m[0x33c]=1
 t.call('large_motion_tick');n+=1
 pairs=[('birds',bytes(m[0x3d00:0x3d40]),b[0xb70:0xbb0]),('vertical',bytes(m[0x3d48:0x3d4f]),b[0xbd1:0xbd8]),('scroll',m[0x3d40],b[0x3b9]),('params',bytes(m[0x3d41:0x3d44]),b[0x36d:0x370])]
 for name,got,want in pairs:
  if got!=want:
   # Original fake player bullet can remove a wing during the same frame.
   # Only that independently identified damage transition is outside this
   # motion-only routine; all 63 remaining bytes must still agree.
   if name=='birds':
    changes=[j for j in range(64) if got[j]!=want[j]]
    if len(changes)==1 and changes[0]%8==0 and got[changes[0]]==11 and want[changes[0]] in (12,13):
     external.append(dict(frame=f,slot=changes[0]//8,kind='arcade collision removed wing'));continue
   errors[name]+=1
   if len(examples)<15:examples.append((f,name,got.hex() if isinstance(got,bytes) else got,want.hex() if isinstance(want,bytes) else want))
print(n,errors,examples,sep='\n')
assert n>300 and not errors,(n,errors)
import hashlib
report=dict(car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),trace=os.environ.get('MAME_TRACE','reference/mame-large/trace.bin'),frames=n,errors=dict(errors),external_collision_frames=external,method='Reseed each single 61.035156 Hz step from MAME RAM; compare all eight bird records, scroll, seven vertical state bytes and three flight parameters. Synthetic fixtures cover both large waves and 8 through 1 surviving birds; fixture setup is explicit in Lua.')
(R/'evidence/v011'/('motion-'+Path(report['trace']).parent.name+'.json')).write_text(json.dumps(report,indent=2))
