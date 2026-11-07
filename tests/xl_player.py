"""Controller-only player: observes game RAM, sends joystick input, never edits RAM."""
import random
class Player:
 def __init__(self,seed,step_frames=8):self.rng=random.Random(seed);self.prev=None;self.stepno=0;self.step_frames=step_frames
 def action(self,m):
  self.stepno+=1;fire=4 if self.stepno%2 else 0
  if m[0x80] in [0,2]:return fire
  if m[0x80]!=1 or m[0x71a] or m[0x7a2] or m[0x7a3] in [1,3,4]:return 0
  sx=m[0x730];targets=[];threats=[]
  if m[0x33c] in [1,2]:
   for i in range(8):
    if not m[0x400+i]:continue
    x=m[0x3810+i];y=m[0x3870+i]
    if x>224:x-=256
    centre=x+28
    if 24<y<210:
     vx=0 if self.prev is None else max(-1.5,min(1.5,((m[0x3810+i]-self.prev[0x3810+i]+128)%256-128)/self.step_frames))
     aim=centre+vx*(212-y)/8-4
     targets.append((abs(aim-sx)*.65+(200-y)*.15,aim))
     if y>168:threats.append((centre,max(0,(210-y)/1.0),24))
  else:
   for i in range(16):
    if not m[0x400+i]:continue
    x=m[0x430+i];y=m[0x440+i]
    if 24<y<212:
     aim=x+4;targets.append((abs(aim-sx)*.8+(200-y)*.12,aim))
     if y>180:threats.append((x+8,(216-y)/2,12))
  aim=100 if m[0x33c]==3 else (min(targets)[1] if targets else 100)
  aim=max(14,min(190,aim))
  for i in range(5):
   if m[0x480+i] and m[0x4b8+i]>140:threats.append((m[0x4b0+i],(216-m[0x4b8+i])/2,7))
  options=[]
  for d in [-1,0,1]:
   x=max(12,min(192,sx+d*(1.75*self.step_frames)));cost=abs(x-aim)*.055+abs(d)*.02
   for tx,tt,r in threats:cost+=max(0,1-abs(x-tx)/(r+8))*max(0,38-tt)*.9
   options.append((cost,d))
  d=min(options)[1];danger=any(tt<20 and abs(tx-sx)<r+5 for tx,tt,r in threats)
  shield=8 if danger and m[0x37a]==0 else 0
  self.prev=m
  return (1 if d>0 else 2 if d<0 else 0)|fire|shield
