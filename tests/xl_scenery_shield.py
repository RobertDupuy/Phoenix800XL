"""Crowded bird/shield scenes with the 18 reserved scenery glyphs."""
from cpu_model import Model, S, R
from scene_oracle import scene, M
import hashlib, json

t=Model(); t.init(); m=t.m.b
worst=0; high=0; cases=0
for pose in range(4):
    for phase in range(8):
        for buffer in range(2):
            m[S['front_buffer']]=buffer
            m[S['state']]=1
            m[S['entrance_timer']]=0
            m[S['shield_pose']]=pose
            m[S['xl_star_scroll']]=(250+phase)&255
            for i in range(16):
                m[S['enemy_on']+i]=1
                m[S['raw_enemy_x']+i]=8+(i%4)*56
                m[S['raw_enemy_y']+i]=32+(i//4)*48
                m[S['enemy_shape']+i]=M['poses'][(pose*17+phase*5+i*7)%len(M['poses'])]['shape']
            t.call('latch_aliens')
            cycles=t.call('render_scene'); worst=max(worst,cycles)
            assert not m[S['layout_faults']],(pose,phase,buffer,'glyph exhaustion')
            base=0x2800+m[S['back_buffer']]*1024
            font=0x2000+m[S['back_buffer']]*1024
            actual=bytearray()
            for y in range(200):
                for col in range(40):
                    ch=m[base+y//8*32+col-4] if 4<=col<36 else 0
                    p=m[font+(ch&127)*8+y%8]
                    actual.extend(4 if v==3 and ch&128 else v
                                  for v in (p>>6,p>>4&3,p>>2&3,p&3))
            assert actual==scene(m).tobytes(),(pose,phase,buffer,'pixels')
            high=max(high,m[S['next_char']]); cases+=1

report=dict(car_sha256=hashlib.sha256((R/('Phoenix800XL-512K.car' if json.loads((R/'build/symbols.json').read_text()).get('XL_JCART') else 'Phoenix800XL.car')).read_bytes()).hexdigest(),
            cases=cases,pixel_errors=0,layout_faults=0,max_render_cpu_cycles=worst,
            max_next_char=high,method=__doc__)
out=R/'evidence/xl/scroll';out.mkdir(parents=True,exist_ok=True)
(out/'shield.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
