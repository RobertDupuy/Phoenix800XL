"""Recover existing Phoenix artwork; no runtime renderer or generated redesign."""
from pathlib import Path
import json,re
R=Path(__file__).resolve().parents[1];A=R/'src/arcade-assets';B=R/'build'

def prepare():
 B.mkdir(exist_ok=True)
 # Preserve both original PM layers and all eight animated poses, byte for byte.
 planes=[bytes(map(int,x.split(','))) for x in re.findall(r'\.byte ([^\n]+)',(A/'ship_native.inc').read_text())]
 assert len(planes)==2 and all(len(p)==128 for p in planes)
 assert len({planes[1][i:i+16] for i in range(0,128,16)})==1
 assert [y for y in range(16) if len({planes[0][p*16+y] for p in range(8)})>1]==[4,5,6,7,14,15]
 assert not any(a&b for a,b in zip(*planes))
 (B/'ship-white.bin').write_bytes(planes[0])
 (B/'ship-red.bin').write_bytes(planes[1][:16])
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
  'sprite_method':'original red/white ship on P0/P1; sixteen multicolor character birds; P2/P3 carry two bombs',
  'ship_poses':8,'ship_pose_selection':'(raw arcade X + 4) & 7; idle holds its pose','ship_changed_rows':[4,5,6,7,14,15],
  'combat_dlis':1,'startup_font_copies_per_combat_update':0,'dynamic_glyph_capacity':96},indent=2))

if __name__=='__main__':prepare()
