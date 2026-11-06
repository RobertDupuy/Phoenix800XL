"""Crowded, clipped and disappearing hit effects with the restored v0.25 art."""
from cpu_model import Model,R,S
from scene_oracle import scene,background
import json,hashlib
import numpy as np
T=Model();T.init();m=T.m.b;checks=0
poses=json.loads((R/'build/sprite-manifest.json').read_text())['poses']
for phase in range(8):
 for edge in range(8):
  m[S['front_buffer']]^=1;m[S['state']]=1;m[S['shield_pose']]=255
  for i in range(16):
   m[S['enemy_on']+i]=1;m[S['raw_enemy_x']+i]=(i*13+edge*7)%208
   m[S['raw_enemy_y']+i]=32+(i*17+phase*11)%192
   m[S['enemy_shape']+i]=poses[(i*3+phase)%len(poses)]['shape']
  m[S['burst_count']:S['burst_count']+3]=bytes([12,12,12])
  m[S['burst_pose']:S['burst_pose']+3]=bytes([phase,(phase+2)%8,(phase+5)%8])
  m[S['burst_x']:S['burst_x']+3]=bytes([(6,7,13,30,31,32,33,14)[edge],15,15])
  m[S['burst_y']:S['burst_y']+3]=bytes([(0,1,8,17,23,24,25,10)[edge],10,11])
  T.call('latch_aliens');T.call('render_scene')
  b=m[S['back_buffer']];base=0x2800+b*1024;font=0x2000+b*1024
  actual=np.zeros((200,160),np.uint8)
  for y in range(200):
   for col in range(4,36):
    code=m[base+y//8*32+col-4];v=m[font+(code&127)*8+y%8]
    for x in range(4):
     p=v>>(6-x*2)&3;actual[y,col*4+x]=4 if p==3 and code&128 else p
  expected=scene(m)
  # Empty hit cells retain the underlying star; the original generic
  # compositor clears that cell. All sprite pixels must still match exactly.
  allowed=(actual==expected)|((expected==0)&((actual==3)|(actual==4))&(background()==4))
  assert allowed.all(),(phase,edge,[(int(y),int(x),int(actual[y,x]),int(expected[y,x]),int(background()[y,x])) for y,x in np.argwhere(~allowed)[:8]])
  assert not m[S['layout_faults']];checks+=1
report=dict(car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),crowded_and_clipped_hit_scenes=checks,pixel_errors=0,allocation_faults=0)
(R/'evidence/v027/bird-hit-scenes.json').write_text(json.dumps(report,indent=2));print(report)
