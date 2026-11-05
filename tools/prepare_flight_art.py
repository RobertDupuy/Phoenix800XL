from pathlib import Path
import json
from prepare_native import tables
R=Path(__file__).resolve().parents[1];A=R/'src/arcade-assets';B=R/'build'
def prepare():
 t=tables();colors=json.loads((A/'arcade-bg-colors.json').read_text());art=(A/'original-art-bank2.bin').read_bytes();sh=t['bird_shape_data_page'];frames=[];padded=bytearray();frames2=[];padded2=bytearray()
 for kind in range(1,16):
  cols=7-((t['bird_draw_entries'][kind]-32)//8)
  for phase in range(4):
   ptr=int.from_bytes(t['bird_shape_pointers'][kind*8+phase*2:kind*8+phase*2+2],'big')-0x3c00
   pix=[[0]*32 for _ in range(16)];pix2=[[0]*32 for _ in range(16)]
   for c in range(cols):
    for y in range(16):
     code=sh[ptr+c*2+y//8];v=art[2048+y%8*256+code]
     for x in range(4):
      pen=colors['tiles'][code][y%8][x]
      for bank,dest,targets in [(0,pix,[(2,3,3),(3,3,0),(0,0,3)]),(1,pix2,[(2,3,0),(3,0,2),(0,2,3)])]:
       rgb=colors['palettes'][bank][code][pen]
       dest[y][c*4+x]=0 if not pen else 1+min(range(3),key=lambda k:sum((rgb[j]-targets[k][j])**2 for j in range(3)))
   if kind==11:
    occupied=[x for row in pix for x,v in enumerate(row) if v]
    if occupied:
     lo,hi=min(occupied),max(occupied)
     for image in [pix,pix2]:
      for row in image:
       for x in range(lo,(lo+hi)//2+1):row[lo+hi-x]=row[x]
   frames.append(pix);frames2.append(pix2)
   for pixels,output in [(pix,padded),(pix2,padded2)]:
    for c in range(8):output+=bytes(8)+bytes(sum(pixels[y][c*4+x]<<(6-2*x) for x in range(4)) for y in range(16))+bytes(8)
 masks=bytearray()
 for pose in range(60):
  for fine in range(8):
   mask=sum(int(any(padded[pose*256+c*32+8-fine+r*8:pose*256+c*32+16-fine+r*8]))<<(r*8+c) for c in range(8) for r in range(3))
   masks+=mask.to_bytes(4,'little')
 (B/'flight-masks.bin').write_bytes(masks)
 assert len(padded)==15360
 (B/'large-padded.bin').write_bytes(padded)
 (B/'large-padded2.bin').write_bytes(padded2)
 catalogs=[];ids=[];counts=[];glyphdata=bytearray(16320)
 for fine in range(8):
  tiles=[bytes(8)];lookup={bytes(8):0};desc=[]
  for pose in range(60):
   row=[]
   for r in range(3):
    for c in range(8):
     tile=bytes(padded[pose*256+c*32+8-fine+r*8:pose*256+c*32+16-fine+r*8])
     if tile not in lookup:lookup[tile]=len(tiles);tiles.append(tile)
     row.append(lookup[tile])
   desc.append(row)
  catalogs.append(desc);counts.append(len(tiles))
  for i,tile in enumerate(tiles):glyphdata[fine*2048+i*8:fine*2048+i*8+8]=tile
 for pose in range(60):
  for fine in range(8):ids.extend(catalogs[fine][pose])
 (B/'flight-ids.bin').write_bytes(bytes(ids));(B/'flight-glyphs.bin').write_bytes(glyphdata)
 (B/'flight-pointers.inc').write_text('flight_ptr_lo: .byte '+','.join(str((0x8000+p*192)&255) for p in range(60))+'\nflight_ptr_hi: .byte '+','.join(str((0x8000+p*192)>>8) for p in range(60))+'\nflight_tile_counts: .byte '+','.join(map(str,counts))+'\n')
 (B/'flight-art.json').write_text(json.dumps(dict(frames=frames,second_palette_frames=frames2,kinds=15,phases=4,columns=[7-((v-32)//8) for v in t['bird_draw_entries'][1:]])))
if __name__=='__main__':prepare()
