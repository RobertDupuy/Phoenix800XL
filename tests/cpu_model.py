"""NMOS6502 harness for the 32–512 KiB CARs, without DMA/WSYNC."""
from pathlib import Path
import json
from py65.devices.mpu6502 import MPU
R=Path(__file__).resolve().parents[1];S=json.loads((R/'build/symbols.json').read_text())
class Memory:
 def __init__(self):
  self.b=bytearray(65536);self.rom=(R/'build/Phoenix-First-Flight.rom').read_bytes();self.bank=15;self.high=12;self.low=3;self.switches=0;self.fire=0;self.pot=114;self.nmist=64
 def __getitem__(self,a):
  if isinstance(a,slice):return bytes(self[i] for i in range(a.start or 0,a.stop,a.step or 1))
  if 0x4000<=a<0xc000:
   if len(self.rom)>32768:
    if 0xbfc0<=a<=0xbfcf:self.high=a&12
    if 0xbfd0<=a<=0xbfdf:self.low=(a>>2)&3
    self.bank=(self.high|self.low)&(len(self.rom)//32768-1)
    return self.rom[self.bank*32768+a-0x4000]
   return self.rom[a-0x4000]
  if a==0xc010:return 1-self.fire
  if a==0xe800:return self.pot
  if a==0xe80f:return 247 if getattr(self,"shield",False) else 255
  if a==0xd40f:return self.nmist
  if a==0xd40b:return 128 # zero-wait synthetic interrupt entry; elapsed raster tested in Altirra
  return self.b[a]
 def __setitem__(self,a,v):
  if isinstance(a,slice):self.b[a]=v;return
  if a<0x4000 or a>=0xc000:self.b[a]=v
class Model:
 def __init__(self):self.m=Memory();self.c=MPU(memory=self.m,pc=S['entry'])
 def call(self,name,limit=300000):
  c=self.c;m=self.m;a=S[name];m.b[0x7f0:0x7f4]=bytes([32,a&255,a>>8,234]);c.pc=0x7f0;t=c.processorCycles
  n=0
  while c.pc!=0x7f3:
   c.step();n+=1
   assert n<limit,(name,hex(c.pc))
  return c.processorCycles-t
 def init(self):
  self.m[0xbfc0];self.m[0xbfd0] # normal entry selects code bank zero
  self.call('renderer_init');self.call('hardware_init');self.call('hud_init');self.call('game_reset');self.m.b[0x80]=1;self.m.b[0x71a]=0;self.m.b[0x736]=0;self.call('latch_aliens')
  for a in [0x520,0x560]:self.m.b[a:a+16]=bytes([127]*16)
