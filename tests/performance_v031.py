"""Original-BIOS NTSC timing/profile fixtures; stage selection is injected.

Between stage setup and observations the cartridge runs its normal code.
The only periodic RAM write refreshes invulnerability to preserve enemy load.
"""
from pathlib import Path
import argparse, hashlib, json, os, re, subprocess, sys, tempfile, time

p = argparse.ArgumentParser()
p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
p.add_argument('--out', type=Path, required=True)
p.add_argument('--frames', type=int, default=600)
p.add_argument('--profile', action='store_true')
a = p.parse_args()
R = a.root.resolve(); O = a.out.resolve(); O.mkdir(parents=True, exist_ok=True)
S = json.loads((R/'build/symbols.json').read_text())
CS = json.loads((R/'build/campaign-symbols.json').read_text())
B = Path(os.environ['ALTIRRA_BRIDGE_PACKAGE']).resolve()
sys.path.insert(0, str(B/'sdk/python'))
from altirra_bridge import AltirraBridge

with tempfile.TemporaryDirectory(prefix='phoenix-profile-') as tmp:
    logpath = Path(tmp)/'server.log'
    with logpath.open('w') as log:
        proc = subprocess.Popen([str(B/'AltirraBridgeServer'), '--machine=5200', '--memory=16K', '--bridge=tcp:127.0.0.1:0'], stdout=log, stderr=log, env=dict(os.environ, SDL_AUDIODRIVER='dummy'))
        try:
            for _ in range(100):
                match = re.search(r'token-file: (\S+)', logpath.read_text())
                if match: break
                time.sleep(.05)
            emu = AltirraBridge.from_token_file(match[1]); emu.pause()
            emu.config('video','ntsc'); config = emu.config('kernel',os.environ['ATARI5200_BIOS'])
            emu.boot(str(R/'build/Phoenix-First-Flight.car')); emu.frame(500)
            emu.joy(0,fire=True); emu.frame(8); emu.joy(0,fire=False); emu.frame(480)
            rows=[]
            for wave in (3,4,5):
                emu.bp_set(S['simulation_update']); emu.cycles(240000)
                assert int(emu.regs()['PC'][1:],16)==S['simulation_update']
                emu.bp_clear_all()
                values={'wave':wave-1,'cycle_stage':wave-2,'wave_wait':1,'enemy_on':[0]*16,'display_enemy_on':[0]*16,'aliens_left':0,'entrance_timer':0,'entrance_handoff':0,'wipe_timer':0,'state':1,'large_mode':0,'boss_status':0,'boss_entrance_shown':0,'shield_pose':255,'shield_locked':0,'shield_count':0,'bomb_on':[0]*5,'invuln':255,'lives':3}
                for name,v in values.items(): emu.memload(S[name],bytes(v if isinstance(v,list) else [v]))
                for _ in range(8): emu.poke(S['invuln'],255); emu.frame(100)
                before = emu.memdump(0,16384)
                assert before[S['wave']]==wave and before[S['state']]==1
                emu.screenshot(path=str(O/f'wave{wave}.png'))
                if a.profile: emu.profile_start('callgraph')
                emu.pokey_trace_start(32000)
                for i in range(a.frames):
                    if i%100==0: emu.poke(S['invuln'],255)
                    emu.frame(1)
                    if i%10==0:
                        m=emu.memdump(0,16384)
                        assert m[S['state']]==1 and m[S['aliens_left']]==before[S['aliens_left']]
                after = emu.memdump(0,16384)
                emu.pokey_trace_stop(); events=[]
                while True:
                    trace=emu.pokey_trace_read(4096)
                    assert trace['valid'] and not trace['dropped']; events+=trace['events']
                    if not trace['queued']: break
                if a.profile:
                    emu.profile_stop(); profile=emu.profile_dump_tree()
                    (O/f'wave{wave}-profile.json').write_text(json.dumps(profile,indent=2))
                    hot=[]
                    for n in sorted(profile,key=lambda n:n['excl_cycles'],reverse=True)[:20]:
                        addr=int(n['addr'].lstrip('$'),16) if isinstance(n['addr'],str) else n['addr']
                        names=[k for k,v in S.items() if v==addr]+[k for k,v in CS.items() if v==addr]
                        hot.append(dict(name='/'.join(names) or hex(addr),**n))
                    print('PROFILE',wave,json.dumps(hot[:12]),flush=True)
                def delta(name,n):
                    return (int.from_bytes(after[S[name]:S[name]+n],'little')-int.from_bytes(before[S[name]:S[name]+n],'little'))%(1<<(n*8))
                frames=delta('frames',4)
                ticks=[e['tick'] for e in events if e['chip']==1 and e['reg']==1]
                gaps=[y-x for x,y in zip(ticks,ticks[1:])]
                row=dict(wave=wave,enemies=after[S['aliens_left']],video_frames=frames,render_fps=round(delta('fresh_commits',4)/frames*59.922743,3),simulation_hz=round(delta('sim_steps',4)/frames*59.922743,3),late_vbi=delta('late_frames',2),audio_underruns=delta('audio_underruns',2),missing_audio_frames=sum(max(0,round(g/(262*114))-1)for g in gaps),max_audio_gap_clocks=max(gaps),layout_faults=after[S['layout_faults']])
                rows.append(row); print('TIMING',row,flush=True)
            report=dict(method=__doc__,car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),config={k:config[k] for k in ['machine','memory','video','rapidus','vbxe']},timing=rows)
            (O/'report.json').write_text(json.dumps(report,indent=2))
        finally:
            proc.terminate(); proc.wait(timeout=5)
