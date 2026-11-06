"""Quantized source-asset compositor. Tests blitting, not arcade equivalence.
The separate mame_display test checks actual observed arcade VRAM/phase.
"""
from cpu_model import R
import json,numpy as np
M=json.loads((R/'build/sprite-manifest.json').read_text());P={p['shape']:p for p in M['poses']};SH=json.loads((R/'build/shield-manifest.json').read_text())
def background(timer=0):
 a=np.zeros((200,160),dtype=np.uint8)
 for row,col in json.loads((R/'src/arcade-assets/stars-irregular.json').read_text())['cells']:
  y=row*8+3
  for yy in ([y,y+192] if y<63 and timer else [y]):
   if 0<=yy-timer<200:a[yy-timer,col*4+2]=4
 return a
def scene(m,base=None):
 bg=background(m[0x71a]);a=bg.copy() if base is None else base.copy()
 def put(cx,cy,tile,flag=0):
  if not(7<=cx<33 and 0<=cy<25):return
  for y,v in enumerate(tile):
   for x in range(4):
    p=v>>(6-2*x)&3
    a[cy*8+y,cx*4+x]=p if m[0x33c]==0 else ((4 if p==3 and flag else p) if p else bg[cy*8+y,cx*4+x])
 if m[0x80] in (1,3) and not(m[0x80]==3 and m[0x377]<=32):
  for i in range(16):
   if not m[0x4d0+i]:continue
   p=P[m[0x4c0+i]];cx=7+m[0x410+i]//8;cy=m[0x420+i]//8-4
   for j,tid in enumerate(p['tiles']):
    if not tid:continue
    x=cx+j%2;y=cy+j//2
    if m[0x80]==3 and y>=11 and m[0x379]<=x<m[0x379]+16:continue
    put(x,y,M['tiles'][tid],M['flags'][tid])
  for i in range(3):
   if not m[0x380+i] or m[0x389+i]==255:continue
   for j,tid in enumerate(M['bursts'][m[0x389+i]]):put(m[0x383+i]+j//2,m[0x386+i]+j%2,M['tiles'][tid],M['flags'][tid])
  for i in range(2):
   if not m[0x770+i] or not m[0x778+i]:continue
   d=((15-m[0x778+i])&14)//2;x=m[0x774+i];y=m[0x776+i]
   for start,cx in [(0,x-3-d),(6,x+d+1)]:
    for j,tid in enumerate(M['bonus_parts'][start:start+6]):put((cx+j//2)&255,y+j%2,M['tiles'][tid],M['flags'][tid])
   if m[0x77a+i]:
    for j,v in enumerate([m[0x787+i]//10,m[0x787+i]%10,0]):
     tid=M['bonus_numbers'][v];put((x-1+j)&255,y,M['tiles'][tid],M['flags'][tid])
 if m[0x80]==1 and m[0x37c]!=255:
  cx=6+m[0xa5]//8
  for y,row in enumerate(SH['pixels'][m[0x37c]]):
   for x,v in enumerate(row):a[168+y,cx*4+x]=0 if v==5 else 3 if v==4 and m[0x33c]==0 else v
 if m[0x80]==3 and 33<=m[0x377]<96:
  for cell,tid in M['explosions'][(95-m[0x377])//2]:put(m[0x379]+cell//16,11+cell%16,M['tiles'][tid],M['flags'][tid])
 if (m[0x80]==1 or (m[0x80]==3 and m[0x377]>=33)) and m[0x480] and 40<=m[0x48a]<238:
  y=m[0x48a]-40;x=m[0x485]-48;a[y:y+3,x]=1
 if (m[0x80]==1 or (m[0x80]==3 and m[0x377]>=33)) and m[0x37c]!=255 and m[0x88] and 40<=m[0x8a]<238:
  y=m[0x8a]-40;x=m[0x89]-48;a[y:y+3,x]=1
 if (m[0x80]==1 or (m[0x80]==3 and m[0x377]>=33)) and m[0x710] and 40<=m[0x712]<238:
  y=m[0x712]-40;x=m[0x711]-48;a[y:y+3,x]=1
 return a
