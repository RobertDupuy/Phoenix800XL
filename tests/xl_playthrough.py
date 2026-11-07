"""Joystick-only play: RAM observations guide the player; no game memory writes."""
from xl_emulator import XL, ROOT
from xl_player import Player
import argparse, hashlib, json

p=argparse.ArgumentParser();p.add_argument('--frames',type=int,default=48000)
p.add_argument('--step',type=int,default=4);args=p.parse_args();O=ROOT/'evidence/xl/playthrough'
with XL(O) as e:
    a=e.a;a.frame(500);player=Player(1,args.step)
    m=a.memdump(0,16384);events=[];inputs=[];last=None;max_wave=0
    for f in range(0,args.frames,args.step):
        action=player.action(m)
        direction='right' if action&1 else 'left' if action&2 else 'centre'
        if action&8: direction='down'+('right' if action&1 else 'left' if action&2 else '')
        a.joy(0,direction,bool(action&4));a.frame(args.step)
        inputs.append([f,action]);m=a.memdump(0,16384)
        key=(m[0x83],m[0x80],m[0x82],m[0x7a3])
        max_wave=max(max_wave,m[0x83])
        if key!=last:
            event=dict(frame=f,wave=key[0],state=key[1],lives=key[2],boss=key[3],score=list(m[0xc0:0xc6]))
            events.append(event);last=key;print(event,flush=True)
            a.screenshot(path=str(O/f'event-{f:06}.png'))
        if m[0x83]>=6:break
    report=dict(method=__doc__,car_sha256=hashlib.sha256(e.car_path.read_bytes()).hexdigest(),
        frames=f+args.step,max_wave=max_wave,completed_first_cycle=max_wave>=6,events=events,
        late_vbi=int.from_bytes(m[0x308:0x30a],'little'),layout_faults=m[0x32d])
    (O/'report.json').write_text(json.dumps(report,indent=2))
    (O/'inputs.json').write_text(json.dumps(inputs))
    assert report['late_vbi']==report['layout_faults']==0,report
    print(report)
