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
 # The old still image had two wholly empty rows. A looping background makes
 # these conspicuous moving bands, so fill them without changing other stars.
 scroll += [(12*8+3,20),(20*8+3,12)]
 assert {y//8 for y,x in scroll}==set(range(32))
 assert len(scroll)+18<=128, 'XL background footprint cache: 128 entries/buffer'
 (B/'scroll-stars.inc').write_text('scroll_star_y: .byte '+','.join(str(y) for y,x in scroll)+'\nscroll_star_x: .byte '+','.join(str(x) for y,x in scroll)+'\n.set SCROLL_STARS,'+str(len(scroll))+'\n')

 # Original arcade comet and approved right-hand shape in the existing blue.
 # Eight fine-Y positions are prepared on the host, not shifted during play.
 tiles=json.loads((A/'arcade-bg-colors.json').read_text())['tiles']
 custom=json.loads((A/'xl-space-objects.json').read_text())
 objects=[]; scenery=bytearray()
 for name,shape,col,y in [('ringed-planet',0,9,27),('comet',4,27,115),('atom',5,18,203)]:
  pix=[[int(tiles[0x20+shape*2+(yy//8)*16+xx//4][yy%8][xx%4]!=0)
        for xx in range(8)] for yy in range(16)]
  objects.append(dict(name=name,arcade_shape=shape,col=col,y=y,pixels=pix))
 for index,key in [(0,'left_comet')]:
  recipe=custom[key]; shape=recipe['arcade_shape']; pens=recipe['blue_pens']
  assert 0<=shape<8 and set(pens)<={1,2,3}
  pix=[[int(tiles[0x20+shape*2+(yy//8)*16+xx//4][yy%8][xx%4] in pens)
        for xx in range(8)] for yy in range(16)]
  objects[index].update(name=key.replace('_','-'),arcade_shape=shape,
                        blue_pens=pens,pixels=pix)
 # Retain the fixed three-slot layout; the removed planet's slot shows only
 # the underlying stars. No renderer, placement or timing changes are needed.
 objects[2].update(name='stars-only',arcade_shape=None,pixels=[[0]*8 for _ in range(16)])
 for fine in range(8):
  phase=bytearray()
  for obj in objects:
   canvas=[[0]*8 for _ in range(24)]
   for yy,row in enumerate(obj['pixels']):canvas[yy+fine]=row.copy()
   for sy,sx in scroll:
    row=sy//8-obj['y']//8; col=sx-obj['col']
    if 0<=row<3 and 0<=col<2:canvas[row*8+fine][col*4+2]=1
   for row in range(3):
    for col0 in range(2):
     phase.extend(sum(canvas[row*8+yy][col0*4+xx]*3<<(6-xx*2)
                      for xx in range(4)) for yy in range(8))
  scenery.extend(phase+bytes(112))
 assert len(scenery)==2048
 (B/'xl-scenery.bin').write_bytes(scenery)
 positions=[(y//8,x,129) for y,x in scroll]
 for n,obj in enumerate(objects):
  positions.extend((obj['y']//8+row,obj['col']+col,192+n*6+row*2+col)
                   for row in range(3) for col in range(2))
 assert len(positions)==80
 maps=bytearray()
 for coarse in range(32):
  offsets=[((row+coarse)&31)*32+col-4 for row,col,ch in positions]
  maps.extend(v&255 for v in offsets)
  maps.extend(v>>8 if v<800 else 255 for v in offsets)
 assert len(maps)==5120
 (B/'xl-background.bin').write_bytes(scenery+maps)
 (B/'xl-background.inc').write_text(
  'xl_bg_codes: .byte '+','.join(str(ch) for row,col,ch in positions)+'\n'+
  'xl_bg_lo: .byte '+','.join(str((0xeb00+c*160)&255) for c in range(32))+'\n'+
  'xl_bg_hi: .byte '+','.join(str((0xeb00+c*160)>>8) for c in range(32))+'\n')

 (B/'scenery-manifest.json').write_text(json.dumps(dict(objects=objects,
     color='Existing dark-blue star color only',source='Original set-B shapes 2 (comet) and 4 (right), with a stars-only middle slot; xl-space-objects.json defines comet mapping from arcade-bg-colors.json'),indent=2))

 # Opening formation coordinates directly observed in MAME, compressed 3:4
 # to retain the approved native ship/bird pixel dimensions on the 5200.
 xy=[(96,72),(96,88),(72,88),(120,88),(56,80),(136,80),(40,72),(152,72),(24,64),(168,64),(24,48),(168,48),(40,40),(152,40),(56,32),(136,32)]
 (B/'formation.inc').write_text('formation_x: .byte '+','.join(str(50+x*3//4) for x,y in xy)+'\nformation_y: .byte '+','.join(str(34+y*3//4) for x,y in xy)+'\n')
if __name__=='__main__':prepare()
