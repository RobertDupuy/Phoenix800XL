"""Compare optimized rendering with the published v0.30 ROM, pixel for pixel.

Both ROMs receive identical seven-bird/five-escort fixtures, including edges,
overlaps, damage, buffer reuse, eggs, shields and death. This is a CPU fixture;
real ANTIC timing and raster output are checked separately.
"""
from pathlib import Path
import argparse, hashlib, importlib.util, json
import numpy as np
from cpu_model import Model, R, S

p=argparse.ArgumentParser();p.add_argument('--baseline',type=Path,required=True);args=p.parse_args()
spec=importlib.util.spec_from_file_location('baseline_cpu',args.baseline/'tests/cpu_model.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
models=[(old.Model(),old.S),(Model(),S)]
for t,_ in models:t.init()

def put(t,s,values):
    for name,value in values.items():
        data=bytes(value if isinstance(value,list) else [value])
        t.m.b[s[name]:s[name]+len(data)]=data

def pixels(t,s):
    m=t.m.b;b=m[s['back_buffer']];out=np.empty((200,128),np.uint8)
    for row in range(25):
        font=(0x1800,0x2000,0x3000)[min(row//8,2)]+b*1024
        for col in range(32):
            code=m[0x2800+b*1024+row*32+col]
            tile=m[font+(code&127)*8:font+(code&127)*8+8]
            for y,v in enumerate(tile):
                for x in range(4):
                    pen=v>>(6-x*2)&3
                    out[row*8+y,col*4+x]=4 if pen==3 and code&128 else pen
    return out

def raster(t,s):
    m=t.m.b;b=m[s['back_buffer']];commands=m[0x3dc0+b*32:0x3dc0+b*32+25]
    count=sum(i%8==0 or c&128!=0 for i,c in enumerate(commands))
    return [bytes(m[0x1000+b*64:0x1000+b*64+36]),bytes(commands)]+[bytes(m[s[name]+b*32:s[name]+b*32+count]) for name in ('supplied_fonts','supplied_delay','supplied_color0','supplied_color1','supplied_color2')]

large_cases=0;boss_cases=0;cycles={'large':[0,0],'boss':[0,0]}
for wave in (3,4):
    for t,s in models:put(t,s,{'wave':wave});t.call('wave_reset')
    for frame in range(72):
        poses=[16+(frame+i*7)%44 for i in range(8)]
        if frame%9<2:poses[frame%7]=(frame%4)*4
        xs=[232,248,8,64,120,176,208,0] if frame%4 else [56+i*8 for i in range(8)]
        ys=[(24+i*24+frame%8)&255 for i in range(8)] if frame%3 else [216+(frame%8)]*8
        settings={'front_buffer':frame%2,'state':3 if frame%11==0 else 1,'death_timer':80,'explosion_left':12,'shield_pose':frame%4 if frame%7<2 else 255,'raw_ship_x':100,'enemy_on':[1]*7+[0]*9,'display_enemy_on':[0]*16,'aliens_left':7,'large_x':xs,'large_y':ys,'large_pose':poses,'large_left':[0]*8,'large_right':[0]*8,'shot_on':0,'second_on':0,'bomb_on':[0]*5}
        got=[];plans=[]
        for j,(t,s) in enumerate(models):
            put(t,s,settings);cycles['large'][j]+=t.call('render_scene');got.append(pixels(t,s));plans.append(raster(t,s))
            assert not t.m.b[s['layout_faults']],('large allocation',wave,frame,j)
        assert np.array_equal(*got),('large pixels',wave,frame,np.count_nonzero(got[0]!=got[1]))
        assert plans[0]==plans[1],('large raster schedule',wave,frame)
        large_cases+=1

for t,s in models:put(t,s,{'wave':5});t.call('wave_reset')
for frame in range(128):
    scroll=249-(frame%90)
    got=[]
    for j,(t,s) in enumerate(models):
        settings={'front_buffer':frame%2,'state':1,'boss_status':2,'boss_scroll':scroll,'boss_entrance_shown':0,'shield_pose':frame%4 if frame%9<4 else 255,'raw_ship_x':100,'enemy_on':[1]*5+[0]*11,'display_enemy_on':[1]*5+[0]*11,'aliens_left':5,'enemy_x':[(16+i*31+frame*7)%192 for i in range(16)],'enemy_y':[40+((i*3+frame)%17)*8 for i in range(16)],'display_enemy_shape':[32+((i+frame)%12)*2 for i in range(16)],'shot_on':0,'second_on':0,'bomb_on':[0]*5,'boss_dirty_rows':[1]*10}
        put(t,s,settings)
        for off in range(234):
            value=t.m.b[s['boss_body']+off]
            if 76<=value<=79 and (off+frame)%17==0:
                t.m.b[s['boss_body']+off]=max(0,value-1) if value>76 else 0
                t.m.b[0x1200+off]=1
        cycles['boss'][j]+=t.call('render_scene');got.append(pixels(t,s))
        assert not t.m.b[s['layout_faults']],('boss allocation',frame,j)
    assert np.array_equal(*got),('boss pixels',frame,np.count_nonzero(got[0]!=got[1]))
    boss_cases+=1

report=dict(method=__doc__,car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),baseline_sha256=hashlib.sha256((args.baseline/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),large_scenes=large_cases,boss_scenes=boss_cases,pixel_errors=0,raster_schedule_errors=0,cpu_cycles=cycles)
out=R/'evidence/v031';out.mkdir(parents=True,exist_ok=True);(out/'optimized-pixels.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
