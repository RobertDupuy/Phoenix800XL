"""ROM-only shifted two-color bird tiles, recovered from original port assets."""
from pathlib import Path
import json
R=Path(__file__).resolve().parents[1];B=R/'build';A=R/'src/arcade-assets'
def prepare():
 art=(A/'art-bank1.bin').read_bytes();data=bytearray();flags=[]
 for pose in range(3):
  bird=[[art[y*256+0x60+pose*2+x//4]>>(6-2*(x%4))&3 for x in range(8)] for y in range(8)]
  for sy in range(8):
   for sx in range(4):
    canvas=[[0]*12 for _ in range(16)]
    for y in range(8):
     for x in range(8):canvas[y+sy][x+sx]=bird[y][x]
    f=0
    for tile in range(6):
     rows=[];mask=[]
     for y in range(8):
      row=canvas[(tile//3)*8+y][(tile%3)*4:(tile%3)*4+4]
      rows.append(sum(p<<(6-x*2) for x,p in enumerate(row)))
      mask.append(sum((0 if p else 3)<<(6-x*2) for x,p in enumerate(row)))
     if any(rows):f|=1<<tile
     data.extend(mask);data.extend(rows)
    flags.append(f)
 assert len(data)==9216
 # Cache identical opaque/transparent tile patterns within a frame. IDs >=255
 # bypass caching; their full artwork still follows the original drawing path.
 tile_ids=[];unique={}
 for i in range(0,len(data),16):
  p=bytes(data[i+8:i+16]);tid=unique.setdefault(p,len(unique))
  tile_ids.append(min(255,tid))
 (B/'tile-ids.bin').write_bytes(bytes(tile_ids))
 (B/'shifted-birds.bin').write_bytes(data);(B/'bird-tile-flags.bin').write_bytes(bytes(flags))
 # Preserve the existing star locations, offset into a forty-column playfield.
 stars=[row*40+col for row,col in json.loads((A/'stars-irregular.json').read_text())['cells']]
 (B/'star-offsets.inc').write_text('star_lo: .byte '+','.join(str(v&255) for v in stars)+'\nstar_hi: .byte '+','.join(str(v>>8) for v in stars)+'\n.set STAR_COUNT,'+str(len(stars))+'\n')
 (B/'star-draw.inc').write_text('seed_stars_static:\n lda back_buffer\n beq seed_stars_zero\n jmp seed_stars_one\nseed_stars_zero:\n lda #129\n'+''.join(f' sta {0x2800+(v//40)*32+v%40-4}\n' for v in stars)+' rts\nseed_stars_one:\n lda #129\n'+''.join(f' sta {0x2c00+(v//40)*32+v%40-4}\n' for v in stars)+' rts\n')

 scroll=[((v//40)*8+3,v%40) for v in stars]
 scroll += [(y+192,x) for y,x in scroll if y<63]
 (B/'scroll-stars.inc').write_text('scroll_star_y: .byte '+','.join(str(y) for y,x in scroll)+'\nscroll_star_x: .byte '+','.join(str(x) for y,x in scroll)+'\n.set SCROLL_STARS,'+str(len(scroll))+'\n')

 # Opening formation coordinates directly observed in MAME, compressed 3:4
 # to retain the approved native ship/bird pixel dimensions on the 5200.
 xy=[(96,72),(96,88),(72,88),(120,88),(56,80),(136,80),(40,72),(152,72),(24,64),(168,64),(24,48),(168,48),(40,40),(152,40),(56,32),(136,32)]
 (B/'formation.inc').write_text('formation_x: .byte '+','.join(str(50+x*3//4) for x,y in xy)+'\nformation_y: .byte '+','.join(str(34+y*3//4) for x,y in xy)+'\n')
if __name__=='__main__':prepare()
