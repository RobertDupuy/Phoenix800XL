"""Cold boot/input/reset plus explicit stage fixtures on stock 64 KiB XL.

Stage setup and periodic invulnerability are test fixtures. Once set up, the
real cartridge performs movement, rendering, interrupts and sound normally.
"""
from xl_emulator import XL, ROOT
import hashlib, json

S = json.loads((ROOT/'build/symbols.json').read_text())
O = ROOT/'evidence/xl/integration'

def set_values(a, values):
    for name, value in values.items():
        a.memload(S[name], bytes(value if isinstance(value,list) else [value]))

def stage(a, wave):
    a.bp_set(S['simulation_update']); a.cycles(240000)
    assert int(a.regs()['PC'][1:],16) == S['simulation_update']
    a.bp_clear_all()
    set_values(a,dict(wave=wave-1,cycle_stage=(wave-2)%5,wave_wait=1,
        enemy_on=[0]*16,display_enemy_on=[0]*16,aliens_left=0,
        entrance_timer=0,entrance_handoff=0,wipe_timer=0,state=1,
        large_mode=0,boss_status=0,boss_entrance_shown=0,
        shield_pose=255,shield_locked=0,shield_count=0,bomb_on=[0]*5,
        invuln=255,lives=3))
    for _ in range(8):
        a.poke(S['invuln'],255); a.frame(100)
    assert a.peek(S['wave'])[0] == wave

if __name__ == '__main__':
    with XL(O) as e:
        a=e.a; a.frame(500)
        assert a.peek(S['state'])[0] == 0
        assert a.peek(0xd301)[0] == 254
        assert int.from_bytes(a.peek(0xfffa,2),'little') == S['xl_nmi']
        # No writes to game RAM before the input checks.
        a.screenshot(path=str(O/'title.png'))
        a.joy(0,fire=True); a.frame(8); a.joy(0); a.frame(480)
        assert a.peek(S['state'])[0] == 1
        x0=a.peek(S['video_ship_x'])[0]
        a.joy(0,'left'); a.frame(20); x1=a.peek(S['video_ship_x'])[0]
        a.joy(0,'right'); a.frame(20); x2=a.peek(S['video_ship_x'])[0]
        a.joy(0); a.frame(10); x3=a.peek(S['video_ship_x'])[0]
        assert x1<x0 and x2>x1 and x3==x2,(x0,x1,x2,x3)
        a.joy(0,'down'); a.frame(8)
        assert a.peek(S['shield_locked'])[0] == 1
        a.screenshot(path=str(O/'shield.png')); a.joy(0)
        rows=[]
        for wave in range(1,6):
            stage(a,wave)
            for _ in range(3): a.poke(S['invuln'],255); a.frame(100)
            before=a.memdump(0,16384)
            a.pokey_trace_start(32000)
            for _ in range(6): a.poke(S['invuln'],255); a.frame(100)
            after=a.memdump(0,16384)
            a.pokey_trace_stop(); events=[]
            while True:
                tr=a.pokey_trace_read(4096)
                assert tr['valid'] and not tr['dropped']
                events.extend(tr['events'])
                if not tr['queued']: break
            def delta(name,n):
                return (int.from_bytes(after[S[name]:S[name]+n],'little')-
                    int.from_bytes(before[S[name]:S[name]+n],'little'))%(1<<(n*8))
            ticks=[ev['tick'] for ev in events if ev['reg']==1]
            gaps=[b-a for a,b in zip(ticks,ticks[1:])]
            row=dict(wave=wave,enemies=after[S['aliens_left']],
                video_frames=delta('frames',4),
                render_fps=round(delta('fresh_commits',4)/delta('frames',4)*59.922743,3),
                simulation_hz=round(delta('sim_steps',4)/delta('frames',4)*59.922743,3),
                late_vbi=delta('late_frames',2),audio_underruns=delta('audio_underruns',2),
                layout_faults=after[S['layout_faults']],
                missing_audio_frames=sum(max(0,round(g/(262*114))-1) for g in gaps),
                max_audio_gap_clocks=max(gaps))
            assert row['late_vbi']==row['audio_underruns']==row['layout_faults']==row['missing_audio_frames']==0,row
            assert row['enemies']==([16,16,7,7,5][wave-1]),row
            a.screenshot(path=str(O/f'wave{wave}.png')); rows.append(row)
            print(row,flush=True)
        # Warm reset must remap the boot bank and return to the attract screen.
        a.warm_reset(); a.frame(700)
        assert a.peek(S['state'])[0] == 0
        assert int.from_bytes(a.peek(S['frames'],4),'little')>200
        a.screenshot(path=str(O/'warm-reset.png'))
        a.cold_reset(); a.frame(700)
        assert a.peek(S['state'])[0] == 0
        report=dict(method=__doc__,config=e.config,
            car_sha256=hashlib.sha256((ROOT/'Phoenix800XL.car').read_bytes()).hexdigest(),
            joystick_positions=[x0,x1,x2,x3],shield_down=True,
            cold_boot=True,warm_reset=True,cold_reset=True,timing=rows)
        (O/'report.json').write_text(json.dumps(report,indent=2))
