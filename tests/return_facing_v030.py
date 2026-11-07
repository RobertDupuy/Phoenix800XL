"""Check arcade direction selection and exact reflected source poses.

The original movement/animation tables choose separate shape families for
directions 7 (up/right) and 8 (up/left). Test those ROM entry points, rather
than deriving direction from the replacement artwork's metadata.
"""
from cpu_model import Model, R, S
from pathlib import Path
import hashlib, json, sys
import numpy as np
sys.path.insert(0, str(R / 'tools'))
import supplied_art as art

poses = {p['shape']: p for p in json.loads((R/'build/sprite-manifest.json').read_text())['poses']}
right = (192, 196, 200, 204)
left = (208, 212, 216, 220)
source_frames = (3, 2, 1, 0)
def crop(a):
    a = np.asarray(a); x,y,r,b = art.bbox(a)
    return a[y:b,x:r]
for rs,ls,frame in zip(right,left,source_frames):
    source = art.pixels('small-pose-row-05',frame)
    assert np.array_equal(crop(poses[rs]['pixels']),crop(source))
    assert np.array_equal(crop(poses[ls]['pixels']),crop(source[:,::-1]))
    assert not np.array_equal(crop(poses[rs]['pixels']),crop(poses[ls]['pixels']))

t=Model();t.init();m=t.m.b;cases=[]
cluster=(R/'build/alien_movement_cluster_a.bin').read_bytes()
for wave in (1,2):
    m[S['wave']]=wave;t.call('wave_reset');m[S['state']]=1
    m[S['enemy_on']:S['enemy_on']+16]=bytes([1]+[0]*15)
    for direction,shapes,dx in ((7,right,4),(8,left,-4)):
        offset=cluster.index(direction)
        for shape,(xf,yf) in zip(shapes,((0,0),(4,2),(0,4),(4,6))):
            m[S['raw_enemy_x']]=96+xf;m[S['raw_enemy_y']]=96+yf
            m[S['pattern_hi']]=0x10+(offset>>8);m[S['pattern_lo']]=offset&255
            t.call('alien_animate')
            assert m[S['enemy_shape']]==shape,(wave,direction,xf,yf,m[S['enemy_shape']],shape)
            assert m[S['enemy_kind']]==4
            t.call('latch_aliens')
            assert m[S['display_enemy_shape']]==shape
            x,y=m[S['raw_enemy_x']],m[S['raw_enemy_y']]
            t.call('alien_move')
            assert (m[S['raw_enemy_x']],m[S['raw_enemy_y']])==(x+dx,y-2)
            cases.append(dict(wave=wave,direction=direction,shape=shape,delta=[dx,-2]))
report=dict(car_sha256=hashlib.sha256((R/'build/Phoenix800XL.car').read_bytes()).hexdigest(),
            source_pose_checks=8,movement_and_animation_cases=cases,errors=0)
out=R/'evidence/v030';out.mkdir(parents=True,exist_ok=True)
(out/'return-facing.json').write_text(json.dumps(report,indent=2))
print('PASS:',len(cases),'direction/phase cases, eight exact source-pose checks')
