"""Explicit late-wave diagnostic fixture; not an unassisted gameplay run."""
from emulator import *
S=json.loads((ROOT/'build/symbols.json').read_text());O=ROOT/'tests/campaign-fixture'
e=Emulator(O,ROOT/'build/Phoenix-First-Flight.car',boot_frames=400,extra_commands=['physical_key down Left Ctrl','wait_frames 4','physical_key up Left Ctrl','wait_frames 500'])
try:
 e.a.bp_set(S['simulation_update']);e.a.cycles(180000);assert int(e.a.regs()['PC'][1:],16)==S['simulation_update'];e.a.bp_clear_all()
 for a,b in [(0x83,[4]),(0x7a0,[3]),(0x8e,[1]),(0x400,[0]*16),(0x4d0,[0]*16),(0x374,[0]),(0x71a,[0])]:e.a.memload(a,bytes(b))
 rows=[]
 for f in range(500):
  e.step(1)
  m=e.a.peek(0x300,48);g=e.a.peek(0x7a0,16)
  rows.append([f,list(m),list(g),list(e.a.peek(0x80,16)),list(e.a.peek(0x377,3))])
  if f in [15,35,55,75,110,170,240,300,450]:e.shot('frame-'+str(f))
 (O/'timing.json').write_text(json.dumps(rows))
 print('final',list(e.a.peek(0x80,16)),list(e.a.peek(0x300,48)),list(e.a.peek(0x7a0,16)))
finally:e.close()
