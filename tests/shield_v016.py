"""Original shield silhouette, crowded small scenes, and actual controller capture.

CPU fixtures are synthetic. The Altirra capture cold-boots and uses controller
buttons only; it neither writes game RAM nor loads an emulator state.
"""
from pathlib import Path
import argparse, hashlib, json, sys
import numpy as np
from PIL import Image
from cpu_model import Model, R, S
from scene_oracle import scene

sys.path.insert(0, str(R/'tools'))
from prepare_native import tables

sh = json.loads((R/'build/shield-manifest.json').read_text())
fg = json.loads((R/'src/arcade-assets/foreground-rgb.json').read_text())['fg']
codes = tables()['shield_table']
# Each native horizontal pixel represents two arcade pixels. No vertical
# source row may be dropped, repeated, shifted or clipped.
assert sh['vertical_rows'] == list(range(32))
for pose in range(4):
    for y in range(32):
        for x in range(16):
            occupied = any(any(fg[str(codes[pose*16+(sx//8)*4+y//8])][y%8][sx%8])
                           for sx in (x*2, x*2+1))
            assert bool(sh['pixels'][pose][y][x]) == occupied, (pose, x, y)

intro = json.loads((R/'build/intro-art-manifest.json').read_text())
title = intro['pages_pixels'][0]
for gap in (16,22,36,42,56):
    assert not any(title[40+y][24+gap] for y in range(32,72)), gap

art = json.loads((R/'build/sprite-manifest.json').read_text())
poses = [p['shape'] for p in art['poses'] if p['kind']]
t=Model();t.init();m=t.m.b;cases=0;worst=0
for frame in range(160):
    m[S['front_buffer']] ^= 1
    m[S['shield_pose']] = frame%4
    m[S['raw_ship_x']] = (12,100,192)[frame%3]
    for i in range(16):
        m[S['enemy_on']+i]=1
        m[S['raw_enemy_x']+i]=(i*13+frame*3)%208
        m[S['raw_enemy_y']+i]=32+(i*17+frame*11)%200
        m[S['enemy_shape']+i]=poses[(i*7+frame)%len(poses)]
    t.call('latch_aliens')
    worst=max(worst,t.call('render_scene'))
    b=m[S['back_buffer']];base=0x2800+b*0x400;font=0x2000+b*0x400
    actual=np.zeros((200,160),np.uint8)
    for y in range(200):
        for cell in range(4,36):
            code=m[base+(y//8)*32+cell-4]
            row=m[font+(code&127)*8+y%8]
            for x in range(4):
                v=row>>(6-x*2)&3
                actual[y,cell*4+x]=4 if v==3 and code&128 else v
    assert np.array_equal(actual,scene(m)), (frame,np.argwhere(actual!=scene(m))[:8])
    assert not m[S['layout_faults']], frame
    cases+=1

report=dict(car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),
            original_arcade_silhouette_samples=2048, vertical_source_rows=32,
            title_internal_empty_columns=5, crowded_small_shield_scenes=cases,
            pixel_errors=0, layout_faults=0, maximum_fixture_cpu_cycles=worst)
p=argparse.ArgumentParser();p.add_argument('--exe',type=Path);p.add_argument('--out',type=Path,default=R/'evidence/v016/shield')
args=p.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
if args.exe:
    from play_campaign import Frontend
    e=Frontend(out,args.exe.resolve());found={};ended=False
    try:
        for _ in range(200):
            m=e.step(4,2)
            if m[S['state']]==1 and not m[S['entrance_timer']]:break
        else:raise AssertionError('game did not start')
        m=e.step(0,4)
        for frame in range(140):
            action=8 if frame<4 else 0
            m=e.step(action,2 if action!=e.previous else 1)
            pose=m[S['shield_pmg_pose']]
            if pose<4 and pose not in found:
                path=out/f'shield-{pose}.png';e.a.screenshot(path=str(path))
                pixels=np.asarray(Image.open(path).convert('RGB'))
                x=8+(6+m[S['raw_ship_x']]//8)*8
                actual=pixels[192:224,x:x+32].max(axis=2)>0
                expected=np.repeat(np.asarray(sh['pixels'][pose])>0,2,axis=1)
                # Wait for the complete frame if capture occurs during a commit.
                if np.array_equal(actual,expected):found[pose]=dict(file=path.name,frame=e.frames)
            elif len(found)==4 and pose==255:
                e.a.screenshot(path=str(out/'shield-ended.png'))
                for page in (S['SHIP'],S['SHIP_RED']):
                    assert not any(m[page+208:page+216])
                    assert not any(m[page+232:page+240])
                ended=True;break
        assert len(found)==4 and ended,(found,ended)
        report.update(emulator_shield_frames=found,emulator_silhouette_errors=0,
                      shield_expiry_clean=True,method=__doc__)
    finally:e.close()
(out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
