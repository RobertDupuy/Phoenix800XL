"""All scroll offsets against an independent pixel compositor, including wraps.

CPU fixtures place a full flock and exercise shield/death scenes explicitly.
This tests the rendered cartridge code, not the assembled source text.
"""
from cpu_model import Model, S, R
from scene_oracle import scene, background, M
import hashlib, json

t=Model(); t.init(); m=t.m.b

def picture():
    base=0x2800+m[S['back_buffer']]*1024
    font=0x2000+m[S['back_buffer']]*1024
    out=bytearray()
    for y in range(200):
        for col in range(40):
            ch=m[base+y//8*32+col-4] if 4<=col<36 else 0
            p=m[font+(ch&127)*8+y%8]
            out.extend(4 if v==3 and ch&128 else v
                       for v in (p>>6,p>>4&3,p>>2&3,p&3))
    return bytes(out)

cases=0; worst=0
for wave in [1,2]:
    m[S['wave']]=wave; t.call('wave_reset'); m[S['state']]=1
    m[S['entrance_timer']]=0; m[S['entrance_handoff']]=0
    for step in range(272):
        # Descending offset crosses 0/255 and all eight fine-pixel phases.
        m[S['xl_star_scroll']]=(-step)&255
        m[S['invuln']]=255
        for _ in range(2):t.call('arcade_step')
        # Include effects over the moving field without changing source art.
        m[S['state']]=3 if 200<=step<240 else 1
        m[S['death_timer']]=95-(step-200) if m[S['state']]==3 else 0
        m[S['explosion_left']]=12
        t.call('latch_aliens')
        cycles=t.call('render_scene'); worst=max(worst,cycles)
        b=m[S['back_buffer']]; cache=0x3000+b*512; font=0x2000+b*1024
        for tid,tile in enumerate(M['tiles']):
            code=m[cache+tid]&127
            if code>=82:
                assert m[font+code*8:font+code*8+8]==bytes(tile),('cache',wave,step,tid,code)
        got=picture(); expected=scene(m).tobytes()
        if got!=expected:
            bad=[(i%160,i//160,a,b) for i,(a,b) in enumerate(zip(got,expected)) if a!=b]
            raise AssertionError((wave,step,bad[:10]))
        assert not m[S['layout_faults']]
        m[S['front_buffer']]=m[S['back_buffer']]; cases+=1

# Entrance countdown must never expose the formerly blank part of the field.
# Check each of its 256 values, including the live-play handoff and seam.
m[S['wave']]=1; t.call('wave_reset'); m[S['state']]=1
m[S['display_enemy_on']:S['display_enemy_on']+16]=bytes(16)
for timer in range(256):
    m[S['entrance_timer']]=timer; m[S['xl_star_scroll']]=0
    t.call('render_scene')
    expected=background(timer,0)
    assert picture()==expected.tobytes(),('entrance',timer)
    assert all(expected[y:y+8].any() for y in range(193)),('blank band',timer)
    m[S['front_buffer']]=m[S['back_buffer']]

# Arcade $2160/$2180/$21B1 scroll one pixel on odd logical ticks only.
for wave in [1,2,5,6,7]:
    m[S['wave']]=wave; t.call('wave_reset')
    m[S['xl_star_scroll']]=0; m[S['main_phase']]=0
    for tick in range(64):
        t.call('arcade_step')
        expected=0 if wave==5 else (-((tick+1)//2))&255
        assert m[S['xl_star_scroll']]==expected,(wave,tick)

report=dict(car_sha256=hashlib.sha256((R/('Phoenix800XL-512K.car' if json.loads((R/'build/symbols.json').read_text()).get('XL_JCART') else 'Phoenix800XL.car')).read_bytes()).hexdigest(),
            pixel_cases=cases,pixels_compared=cases*32000,pixel_errors=0,
            timing_cases=320,entrance_cases=256,blank_eight_line_bands=0,
            max_render_cpu_cycles=worst,
            method=__doc__)
out=R/'evidence/xl/scroll'; out.mkdir(parents=True,exist_ok=True)
(out/'cpu.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
