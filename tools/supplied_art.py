"""Lossless import of the user's RIGHT-HAND Atari 5200 GIF artwork.

Each captured logical pixel is a uniform 4 x 2 block. Reading that block once
removes capture zoom; it does not resize, filter, or redraw a sprite.
The four left-return poses horizontally reflect the supplied right-return art.
Colors below are semantic GTIA pens; source RGB remains in the manifest/PNGs.
"""
from pathlib import Path
from PIL import Image
import numpy as np
R=Path(__file__).resolve().parents[1]
A=R/'src/supplied-5200/frames-5200'
SMALL_MAP={
32:(0,2),34:(0,1),36:(0,0),38:(0,3),
40:(1,1),42:(1,1),44:(2,1),46:(2,1),48:(1,3),50:(1,3),52:(2,3),54:(2,3),
56:(1,0),58:(1,0),60:(2,0),62:(2,0),64:(1,2),66:(1,2),68:(2,2),70:(2,2),
72:(1,0),74:(1,3),76:(1,2),78:(1,1),80:(3,0),82:(3,3),84:(3,2),86:(3,1),
88:(1,0),90:(4,1),92:(1,1),94:(4,2),96:(1,2),98:(4,3),100:(1,3),102:(4,0),
104:(1,0),108:(4,1),112:(1,1),116:(4,2),120:(1,2),124:(4,3),128:(1,3),132:(4,0),
160:(2,2),168:(2,1),172:(2,3),192:(5,3),196:(5,2),200:(5,1),204:(5,0),
208:(5,3),212:(5,2),216:(5,1),220:(5,0)}
LARGE_MAP={1:[0,1,2,3],2:[4]*4,3:[5]*4,4:[6]*4,5:[7,7,7,8],
6:[9,10,11,12],7:[13,17,18,19],8:[8,7,7,7],9:[12,11,10,9],
10:[19,18,17,13],11:[19,20,21,22],12:[19,20,21,22],
13:[19,20,21,22],14:[19,20,21,22],15:[13,14,15,16]}
def rgb(group,frame):
 a=np.asarray(Image.open(A/group/f'frame-{frame:03}.png').convert('RGB'))
 native=a[::2,::4].copy()
 assert np.array_equal(a,native.repeat(2,0).repeat(4,1)),(group,frame,'nonuniform pixel block')
 return native

def pixels(group,frame):
 a=rgb(group,frame);out=np.zeros(a.shape[:2],dtype=np.uint8)
 for c in np.unique(a.reshape(-1,3),axis=0):
  r,g,b=map(int,c)
  if not max(r,g,b):v=0
  elif group=='player-ship':v=1 if min(r,g,b)>200 else 2 if g>100 else 3
  elif group=='shield':v=1 if min(r,g,b)>200 else 5 if g>r else 3
  elif group=='explosion':v=2
  elif group=='small-pose-row-06':v=1 if g>100 else 2 if r<190 else 3
  elif group=='large-bird':v=2 if r>150 and g>150 and b<100 else 3 if r>150 else 1
  else:v=2 if r>200 and g>200 and b<100 else 1 if g>100 else 3
  out[np.all(a==c,axis=2)]=v
 return out

def bbox(a):
 yy,xx=np.nonzero(a)
 return int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)

def place(p,w,h,dx,dy):
 out=np.zeros((h,w),dtype=np.uint8)
 for y,x in zip(*np.nonzero(p)):
  assert 0<=x+dx<w and 0<=y+dy<h,(p.shape,w,h,dx,dy,x,y)
  out[y+dy,x+dx]=p[y,x]
 return out.tolist()

def small(shape,kind,old_pixels):
 row,frame=SMALL_MAP[shape];p=pixels(f'small-pose-row-{row:02}',frame)
 # Arcade return direction 8 has separate left-facing shapes $D0..$DC.
 # The supplied row 05 contains only right-facing art; reflect its pixels
 # for those four shapes, retaining their phase and the existing anchor.
 mirror_x=shape in (208,212,216,220)
 if mirror_x:p=p[:,::-1].copy()
 # Align whole source pixels to the old drawing anchor. Never crop live pixels.
 x0,y0,x1,y1=bbox(p);ox,oy,_,_=bbox(old_pixels)
 h=8 if y1-y0<=8 and kind==1 else 16
 dx=max(-x0,min(ox-x0,8-x1));dy=max(-y0,min(oy-y0,h-y1))
 provenance=dict(group=f'small-pose-row-{row:02}',frame=frame,translation=[dx,dy])
 if mirror_x:provenance['mirror_x']=True
 return place(p,8,h,dx,dy),provenance
