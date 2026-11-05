"""Precompute arcade-derived large-bird frames and all four horizontal phases.
These are ROM data, not code executed by the console. Full 28x16 fitted pixels.
"""
from pathlib import Path
import json
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[1];A=R/'src/arcade-assets';B=R/'build'
def prepare():
 art=(A/'original-art-bank2.bin').read_bytes();sh=(A/'original-bird-shapes.bin').read_bytes()
 # Six complete arcade silhouettes, followed by seven stages of hatching.
 specs=[(0,7),(14,7),(28,7),(42,7),(256,6),(268,7),
        (424,2),(428,2),(400,3),(376,3),(352,3),(320,4),(280,5)]
 frames=[];bank=bytearray();pal=[(0,0,0),(245,245,245),(246,188,54),(141,64,224)]
 for pose,(off,cols) in enumerate(specs):
  pix=[[0]*28 for _ in range(16)];left=(28-cols*4)//2
  for c in range(cols):
   for y in range(16):
    code=sh[off+c*2+y//8];v=art[2048+(y%8)*256+code]
    for x in range(4):pix[y][left+c*4+x]={0:0,1:2,2:3,3:2}[(v>>(6-2*x))&3]
  # The original extraction quantizes pairs. Mirror intact left halves to
  # retain the approved symmetrical presentation, preserving head/body detail.
  if pose<6:
   occupied=[x for row in pix for x,v in enumerate(row) if v]
   lo,hi=min(occupied),max(occupied)
   for row in pix:
    for x in range(lo,(lo+hi)//2+1):row[lo+hi-x]=row[x]
  frames.append(pix)
  for phase in range(4):
   canvas=[[0]*32 for _ in range(16)]
   for y in range(16):canvas[y][phase:phase+28]=pix[y]
   for col in range(8):
    for y in range(16):bank.append(sum(canvas[y][col*4+x]<<(6-2*x) for x in range(4)))
 assert len(bank)==13*512
 (B/'large-frames.bin').write_bytes(bank)
 padded=bytearray()
 for base in range(0,len(bank),128):
  for col in range(8):padded+=bytes(8)+bank[base+col*16:base+col*16+16]+bytes(8)
 (B/'large-padded.bin').write_bytes(padded)
 stars=set(tuple(v) for v in json.loads((A/'stars-irregular.json').read_text())['cells'])
 star_words=[]
 for band in range(8):
  for pos in range(19):
   cells=[c*2+r for c in range(8) for r in range(2) if (band*3+r,7+pos+c) in stars]
   assert len(cells)<=3
   star_words.append(sum(v<<(i*4) for i,v in enumerate(cells))|(len(cells)<<12))
 (B/'large-stars.bin').write_bytes(bytes(v&255 for v in star_words)+bytes(v>>8 for v in star_words))

 masks=[sum(int(any(bank[base+i*8:base+i*8+8]))<<i for i in range(16)) for base in range(0,len(bank),128)]
 (B/'large-masks.inc').write_text('large_mask_lo: .byte '+','.join(str(v&255) for v in masks)+'\nlarge_mask_hi: .byte '+','.join(str(v>>8) for v in masks)+'\n')
 (B/'large-manifest.json').write_text(json.dumps({'source':'Recovered arcade background glyphs and shape tables; intact silhouettes mirrored to eliminate quantization asymmetry.','size':[28,16],'horizontal_phases':4,'full_wing_poses':6,'hatching_poses':7,'specs':specs,'frames':frames},indent=2))
 im=Image.new('RGB',(4*144,4*104),(18,18,26));dr=ImageDraw.Draw(im)
 for i,pix in enumerate(frames):
  xx=(i%4)*144;yy=(i//4)*104;dr.text((xx+8,yy+4),str(i),fill='white')
  for y,row in enumerate(pix):
   for x,v in enumerate(row):
    if v:dr.rectangle((xx+8+x*4,yy+24+y*4,xx+11+x*4,yy+27+y*4),fill=pal[v])
 im.save(B/'large-atlas.png')
if __name__=='__main__':prepare()
