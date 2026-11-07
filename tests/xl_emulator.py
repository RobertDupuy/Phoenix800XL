"""Stock 64 KiB XL/XE emulator session; no accelerated CPU or extra hardware."""
from pathlib import Path
import json, os, re, subprocess, sys, time

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = Path(os.environ['ALTIRRA_BRIDGE_PACKAGE']).resolve()
sys.path.insert(0, str(PACKAGE / 'sdk/python'))
from altirra_bridge import AltirraBridge

class XL:
    def __init__(self, out, machine='800XL', video='ntsc'):
        self.out = Path(out).resolve()
        self.out.mkdir(parents=True, exist_ok=True)
        self.log = (self.out / 'emulator.log').open('w')
        self.proc = subprocess.Popen([
            str(PACKAGE/'AltirraBridgeServer'), '--machine='+machine,
            '--memory=64K', '--bridge=tcp:127.0.0.1:0'],
            stdout=self.log, stderr=self.log, env=dict(os.environ, SDL_AUDIODRIVER='dummy'))
        for _ in range(100):
            log = (self.out/'emulator.log').read_text()
            match = re.search(r'token-file: (\S+)', log)
            if match:
                break
            time.sleep(.05)
        else:
            self.proc.terminate()
            raise RuntimeError(log)
        # The server can announce its token file just before its socket listens.
        for attempt in range(100):
            try:
                self.a = AltirraBridge.from_token_file(match[1])
                break
            except ConnectionRefusedError:
                if attempt == 99:
                    self.proc.terminate()
                    self.proc.wait(timeout=10)
                    self.log.close()
                    raise
                time.sleep(.05)
        self.a.pause()
        self.a.config('video', video)
        self.a.config('addons', 'stock')
        self.a.config('fastboot', 'false')
        if os.environ.get('ATARI_XL_OS'):
            self.a.config('kernel', os.environ['ATARI_XL_OS'])
        self.config = self.a.config()
        assert self.config['machine'] == machine and self.config['memory'] == '64K'
        assert not self.config['rapidus'] and not self.config['vbxe']
        self.a.boot(str(ROOT/'Phoenix800XL.car'))
    def close(self):
        self.proc.terminate()
        self.proc.wait(timeout=10)
        self.log.close()
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        self.close()

if __name__ == '__main__':
    S = json.loads((ROOT/'build/symbols.json').read_text())
    with XL(ROOT/'evidence/xl/boot') as e:
        a = e.a
        a.frame(700)
        a.screenshot(path=str(e.out/'title.png'))
        print('config', e.config, 'regs', a.regs())
        print({k:list(a.peek(S[k], 4 if k=='frames' else 1)) for k in ['frames','state','wave','lives','start_requested']})
        print('bank', a.peek(0xd500), 'portb', a.peek(0xd301), 'vectors', a.peek(0xfffa,6))
        a.joy(0, fire=True); a.frame(8); a.joy(0,fire=False); a.frame(300)
        a.screenshot(path=str(e.out/'wave1.png'))
        print('game', {k:list(a.peek(S[k], 4 if k=='frames' else 1)) for k in ['frames','state','wave','lives','start_requested','late_frames','layout_faults']})
