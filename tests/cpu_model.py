"""NMOS6502 harness for the XL MegaCart and J(atari)Cart CARs, without DMA/WSYNC."""
from pathlib import Path
import json
from py65.devices.mpu6502 import MPU
R=Path(__file__).resolve().parents[1];S=json.loads((R/'build/symbols.json').read_text())
class Memory:
 def __init__(self):
  self.b=bytearray(65536);self.jcart=bool(S.get('XL_JCART',0))
  self.rom=(R/('build/Phoenix800XL-512K.rom' if self.jcart else 'build/Phoenix800XL.rom')).read_bytes()
  if self.jcart:
   self.b[0x4000:0xa000]=self.rom[0x2000:0x8000]
   self.b[0xd800:0xdcf0]=(R/'build/native-masks.bin').read_bytes()
  else:self.b[0x4000:0x8000]=self.rom[0x4000:0x8000]
  platform=(R/'build/platform.bin').read_bytes();self.b[0xc000:0xc000+len(platform)]=platform
  self.b[0xe300:0xff00]=(R/'build/xl-background.bin').read_bytes()
  self.bank=0;self.switches=0;self.fire=0;self.pot=114;self.nmist=64;self.console=7
 def __getitem__(self,a):
  if isinstance(a,slice):return bytes(self[i] for i in range(a.start or 0,a.stop,a.step or 1))
  if self.jcart and 0xa000<=a<0xc000:return self.rom[self.bank*8192+a-0xa000]
  if not self.jcart and 0x8000<=a<0xc000:return self.rom[(self.bank+2)*16384+a-0x8000]
  if a==0xd010:return 1-self.fire
  if a==0xd01f:return self.console
  if a==0xd300:
   return 255 ^ (4 if self.pot<82 else 8 if self.pot>=146 else 0) ^ (2 if getattr(self,'shield',False) else 0)
  if a==0xd40f:return self.nmist
  if a==0xd40b:return 128
  return self.b[a]
 def __setitem__(self,a,v):
  if isinstance(a,slice):self.b[a]=v;return
  if self.jcart and 0xd500<=a<0xd600:self.bank=a&63;self.switches+=1
  elif a==0xd500:self.bank=(v&15)-2;self.switches+=1
  elif not (0xa000 if self.jcart else 0x8000)<=a<0xc000:self.b[a]=v
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
  self.m.bank=4 if self.m.jcart else 0 # resident XL code has already been copied to RAM
  self.call('renderer_init');self.call('hardware_init');self.call('hud_init');self.call('game_reset');self.m.b[0x80]=1;self.m.b[0x71a]=0;self.m.b[0x736]=0;self.call('latch_aliens')
  for a in [0x520,0x560]:self.m.b[a:a+16]=bytes([127]*16)
