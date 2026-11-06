"""Original $2400 mothership blast: $2A00 particles, $2B00 masks, $1B90 core.
No vertical scaling. A separate art bank avoids changing the gameplay tile cache.
"""
from pathlib import Path
import json
from prepare_native import tables
R=Path(__file__).resolve().parents[1];B=R/'build';A=R/'src/arcade-assets'
def prepare():
 t=tables();pg=t['explosion_particle_page'];ptrs=t['mothership_explosion_pointers']
 fg=json.loads((A/'foreground-rgb.json').read_text())['fg']
 bg=json.loads((A/'explosion-art.json').read_text())['bg']
 colors=[(0,0,0),(255,255,255),(246,246,68),(211,31,210),(202,22,24)]
 def classify(rgb):
  i=min(range(5),key=lambda k:sum((rgb[j]-colors[k][j])**2 for j in range(3)))
  return 3 if i==4 else i
 tiles=[];frames=[];foreground=[0]*256;core=None;fgcodes=[];bgcodes=[]
 for counter in range(95,32,-1):
  if counter&1:
   ctrl=0x300+0xe0-(((counter-32)<<2)&0xe0)
   foreground=[pg[0x200+i] if pg[ctrl+i//8]&(1<<(i%8)) else 0 for i in range(256)]
  else:
   off=0x50+((counter>>2)&14);addr=int.from_bytes(ptrs[off:off+2],'big')
   core=bytes(16) if addr==0x17f0 else ptrs[addr-0x1b40:addr-0x1b40+16]
  fgcodes.append(foreground[:]);bgcodes.append(list(core) if core is not None else None)
  cells=[]
  for cx in range(16):
   for cy in range(16):
    inside=core is not None and 6<=cx<10 and 5<=cy<9
    f=fg[str(foreground[cx*16+cy])]
    b=bg[str(core[(cx-6)*4+cy-5])] if inside else None
    data=[];masks=[]
    for y in range(8):
     vals=[];mask=[]
     for x in range(4):
      pair=[]
      for xx in (x*2,x*2+1):
       # The mothership uses palette bank 1: the core's solid pen is pink
       # (MAME RGB 209,30,170), unlike the player's yellow bank-0 core.
       pair.append(classify(f[y][xx]) if any(f[y][xx]) else 3 if b and any(b[y][xx]) else 0)
      v=1 if 1 in pair else next((q for q in pair if q),0)
      vals.append(v);mask.append(0 if inside or v else 3)
     data.append(sum(v<<(6-x*2) for x,v in enumerate(vals)))
     masks.append(sum(v<<(6-x*2) for x,v in enumerate(mask)))
    tile=bytes(data+masks)
    if masks==[255]*8:continue
    if tile not in tiles:tiles.append(tile)
    cells.append([cx*16+cy,tiles.index(tile)])
  assert len(cells)<256
  frames.append(cells)
 assert len(tiles)<256,len(tiles)
 inc=['blast_frames: .word '+','.join('blast_frame_'+str(i) for i in range(len(frames))),
      'blast_tiles: .word '+','.join('blast_tile_'+str(i) for i in range(len(tiles)))]
 for i,frame in enumerate(frames):inc.append('blast_frame_'+str(i)+': .byte '+','.join(map(str,[len(frame)]+[v for c in frame for v in c])))
 for i,tile in enumerate(tiles):inc.append('blast_tile_'+str(i)+': .byte '+','.join(map(str,tile)))
 for digit in range(10):
  f=fg[str(32+digit)]
  inc.append('award_digit_'+str(digit)+': .byte '+','.join(str(sum(int(any(f[y][x*2]) or any(f[y][x*2+1]))<<(6-x*2) for x in range(4))) for y in range(8)))
 (B/'victory-art.inc').write_text('\n'.join(inc)+'\n')
 (B/'victory-manifest.json').write_text(json.dumps(dict(frames=frames,tiles=[list(v) for v in tiles],foreground_codes=fgcodes,core_codes=bgcodes,source='Original arcade ROM $2400, $2A00/$2B00, $1B90',vertical_scaling=False,red_particles_mapped_to_pink=True),separators=(',',':')))
 print('Mothership victory:',len(frames),'frames,',len(tiles),'tiles, max',max(map(len,frames)),'cells')
