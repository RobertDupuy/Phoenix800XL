"""Recover existing Phoenix artwork; no runtime renderer or generated redesign."""
from pathlib import Path
import json,re
import supplied_art as supplied
R=Path(__file__).resolve().parents[1];A=R/'src/arcade-assets';B=R/'build'

def prepare():
 B.mkdir(exist_ok=True)
 # Three independent PMG colors preserve every pixel in the supplied ship.
 planes={1:bytearray(),2:bytearray(),3:bytearray()}
 for pose in range(4):
  pixels=supplied.pixels('player-ship',pose)
  assert not pixels[:,:4].any() and not pixels[:,12:].any()
  for color,out in planes.items():
   out.extend(sum(int(pixels[y,x+4]==color)<<(7-x) for x in range(8))for y in range(16))
 for color,name in [(1,'white'),(2,'yellow'),(3,'red')]:
  if color==2:
   assert all(planes[color][i:i+16]==planes[color][:16] for i in range(0,64,16))
  (B/f'ship-{name}.bin').write_bytes(planes[color][:16] if color==2 else planes[color])
 # Two recovered small-bird formation poses. Same 12-byte slots and copy code.
 art=(A/'art-bank1.bin').read_bytes();birds=bytearray()
 for pose in range(2):
  rows=[]
  for y in range(8):
   row=0
   for col in range(2):
    packed=art[y*256+0x60+pose*2+col]
    for x in range(4):
     if (packed>>(6-2*x))&3:row|=128>>(col*4+x)
   rows.append(row)
  birds.extend(bytes(rows)+bytes(4))
 (B/'birds.bin').write_bytes(birds)
 # Recover the previous port's arcade alphabet, using the existing 1bpp text mode.
 source=(A/'hud-glyphs.bin').read_bytes();font=bytearray(1024)
 lookup={**{chr(65+i):1+i for i in range(26)},**{str(i):32+i for i in range(10)},
         '-':43,'.':42,'*':31,':':44,'?':47}
 def glyph(code):
  out=[]
  for y in range(8):
   row=0
   for col in range(2):
    b=source[code*32+col*8+y]
    for x in range(4):
     if (b>>(6-2*x))&3:row|=128>>(col*4+x)
   out.append(row)
  return bytes(out)
 for c,n in lookup.items():font[ord(c)*8:ord(c)*8+8]=glyph(n)
 font[127*8:128*8]=glyph(127)
 font[8:16]=bytes([0,0,0,0x10,0,0,0,0])
 (B/'font.bin').write_bytes(font)
 # The separate startup compiler consumes the generated gameplay sprite data.
 (B/'art-manifest.json').write_text(json.dumps({
  'sprite_method':'supplied white/red/yellow ship on P0/P1/P2; exact multicolor bird frames; third extra bomb rendered in playfield',
  'ship_poses':4,'ship_pose_selection':'((raw arcade X + 4) >> 1) & 3; idle holds its pose','ship_changed_rows':{'white':[1,2,3,4,5,6,7,10,11,12,13,14,15],'red':[3,4,5,6,8,9,10,11,12,13,14],'yellow':[]},
  'combat_dlis':1,'startup_font_copies_per_combat_update':0,'dynamic_glyph_capacity':96},indent=2))

if __name__=='__main__':prepare()
