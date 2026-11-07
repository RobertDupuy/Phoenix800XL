"""Profile full-flock XL rendering with explicit stage/invulnerability fixtures."""
from xl_emulator import XL, ROOT
from xl_integration import stage
import hashlib, json

S = json.loads((ROOT/'build/symbols.json').read_text())
C = json.loads((ROOT/'build/campaign-symbols.json').read_text())
O = ROOT/'evidence/xl/profile'
results = []
with XL(O) as e:
    a = e.a
    a.frame(500)
    a.joy(0, fire=True); a.frame(8); a.joy(0); a.frame(480)
    for wave in (3, 5):
        stage(a, wave)
        for _ in range(3):
            a.poke(S['invuln'], 255); a.frame(100)
        before = a.memdump(0, 16384)
        a.profile_start('callgraph')
        for _ in range(6):
            a.poke(S['invuln'], 255); a.frame(100)
        a.profile_stop()
        tree = a.profile_dump_tree()
        after = a.memdump(0, 16384)
        for node in tree:
            addr = int(node['addr'].lstrip('$'), 16)
            node['main_symbols'] = [k for k,v in S.items() if v == addr]
            node['campaign_symbols'] = [k for k,v in C.items() if v == addr]
        def delta(name):
            p=S[name]
            return (int.from_bytes(after[p:p+4], 'little')-
                    int.from_bytes(before[p:p+4], 'little')) & 0xffffffff
        result = dict(wave=wave, video_frames=delta('frames'),
                      renders=delta('fresh_commits'), tree=tree)
        results.append(result)
        print('WAVE', wave, 'renders', result['renders'], flush=True)
        for node in sorted(tree, key=lambda n:n['excl_cycles'], reverse=True)[:18]:
            print(node, flush=True)
report = dict(method=__doc__,
              car_sha256=hashlib.sha256((ROOT/'Phoenix800XL.car').read_bytes()).hexdigest(),
              samples=results)
(O/'report.json').write_text(json.dumps(report, indent=2))
