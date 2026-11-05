"""Compile the recovered arcade mothership, wipe and round tables."""
from pathlib import Path
from prepare_native import tables
R=Path(__file__).resolve().parents[1];B=R/'build';A=R/'src/arcade-assets'
def prepare():
 t=tables();raw=t['mothership_tile_page'];body=bytes(v if v>=64 else 0 for row in reversed(range(9)) for v in raw[row*26:row*26+26])
 (B/'boss-body.bin').write_bytes(body)
 art=(A/'original-art-bank2.bin').read_bytes()
 glyphs=bytes(sum({0:0,1:1,2:3,3:2}[(art[2048+y*256+c]>>(6-2*x))&3]<<(6-2*x) for x in range(4)) for c in range(128) for y in range(8))
 (B/'boss-glyphs.bin').write_bytes(glyphs)
 half=[]
 for lower in (False,True):
  for code in range(64,128):
   g=bytes(8) if code==95 else glyphs[code*8:code*8+8]
   for phase in range(8):half.extend((bytes(8-phase)+g[:phase]) if lower else (g[phase:]+bytes(phase)))
 (B/'boss-halves.bin').write_bytes(bytes(half))
 atlases=bytearray();maps=bytearray();counts=[]
 for fine in range(8):
  tiles=[bytes(8),bytes([0,0,0,192,0,0,0,0])];mp=[]
  for row in range(-1,9):
   for col in range(26):
    u=body[row*26+col] if row>=0 else 0;d=body[(row+1)*26+col] if row<8 else 0
    tile=glyphs[u*8+fine:u*8+8]+glyphs[d*8:d*8+fine]
    if tile not in tiles:tiles.append(tile)
    mp.append(tiles.index(tile))
  assert len(tiles)<=64,len(tiles)
  counts.append(len(tiles));atlases.extend(b''.join(tiles)+bytes((64-len(tiles))*8));maps.extend(bytes(mp))
 (B/'boss-atlases.bin').write_bytes(atlases)
 (B/'boss-maps.bin').write_bytes(maps)
 (B/'boss-atlas-counts.bin').write_bytes(bytes(counts))
 import json
 stars=json.loads((A/'stars-irregular.json').read_text())['cells']
 (B/'boss-stars.inc').write_text('boss_seed_stars:\n lda back_buffer\n beq boss_stars_zero\n jmp boss_stars_one\nboss_stars_zero:\n lda #129\n'+''.join(f' sta {0x2800+row*32+col-4}\n' for row,col in stars)+' rts\nboss_stars_one:\n lda #129\n'+''.join(f' sta {0x2c00+row*32+col-4}\n' for row,col in stars)+' rts\n')
 a=(A/'original-art-bank1.bin').read_bytes()
 (B/'wipe-glyph.bin').write_bytes(bytes(sum((1 if ((a[y*256+31]>>(6-2*x))&3) else 0)<<(6-2*x) for x in range(4))for y in range(8)))

 for name in ['alien_position_pointer_table','alien_position_layout_page','alien_wave_animation_shapes','mothership_explosion_pointers','bird_dive_spawn_positions']:
  (B/(name+'.bin')).write_bytes(t[name])
 # Per-cell expansion radius, transcribed from 2260's actual column-major writes.
 rad=[255]*832
 for a in range(13):
  d=((a>>3)|(a<<5))&255;e=d&31;s=(d&224)+176;h=e+65+(s>>8);l=((s&255)-a)&255;addr=h*256+l;c=a+1
  for row in range(c*2):
   for col in range(c*2):
    q=addr+col;rawx=(0x4320-(q&0xffe0))//4+8;rawy=(q&31)*8
    x=7+rawx//8;y=rawy//8-4
    if 7<=x<33 and 0<=y<25:rad[y*32+x-4]=min(rad[y*32+x-4],a)
   addr-=32
 (B/'wipe-radius.bin').write_bytes(bytes(rad))
 (B/'boss-campaign.json').write_text(__import__('json').dumps({'stages':[1,3,5,7,11],'wipe_phases':28,'wipe_ticks':55,'mothership_rows':9,'mothership_columns':26,'large_bird_limit':6,'escort_limit':2,'source':'Original Phoenix ROM tables and 8085 routines 2204..2442,24C4..253F,0610..0638'},indent=2))
if __name__=='__main__':prepare()
