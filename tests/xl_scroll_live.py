"""Stock 64K NTSC XL: record both scrolling waves and check actual star pixels.

Wave placement and invulnerability are explicit fixtures; the cartridge runs
all movement, rendering, input, interrupts and audio. The movie is silent.
"""
from xl_emulator import XL, ROOT
from xl_integration import stage
from pathlib import Path
import hashlib, io, json, subprocess
import numpy as np
from PIL import Image

S=json.loads((ROOT/'build/symbols.json').read_text())
O=ROOT/'evidence/xl/scroll/live'; O.mkdir(parents=True,exist_ok=True)
movie=O/'Phoenix800XL-Scrolling.mp4'
ff=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','image2pipe',
    '-framerate','29.9613715','-vcodec','png','-i','-','-vf','scale=672:480:flags=neighbor',
    '-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(movie)],stdin=subprocess.PIPE)
results=[]
try:
 with XL(O) as e:
  a=e.a; a.frame(500); a.joy(0,fire=True); a.frame(8); a.joy(0); a.frame(480)
  palette=np.frombuffer(a.palette(),np.uint8).reshape(256,3)
  blue=palette[S['dark_blue_stars']]
  for wave in [1,2]:
   stage(a,wave); phases=set()
   counters=['frames','fresh_commits','late_frames','audio_underruns']
   sizes=[4,4,2,2]
   before=[int.from_bytes(a.peek(S[n],size),'little') for n,size in zip(counters,sizes)]
   for f in range(300):
    if f%40==0:a.poke(S['invuln'],255)
    a.joy(0,'down' if 130<=f<140 else 'left' if f<60 else 'right' if f<180 else 'centre')
    a.frame(2); ff.stdin.write(a.screenshot())
    phases.add(a.peek(S['xl_star_scroll'])[0])
   assert len(phases)>240,(wave,len(phases))
   after=[int.from_bytes(a.peek(S[n],size),'little') for n,size in zip(counters,sizes)]
   delta=[(b-a)%(1<<(8*size)) for a,b,size in zip(before,after,sizes)]
   timing=dict(video_frames=delta[0],render_fps=round(delta[1]/delta[0]*59.922743,3),
               late_vbi=delta[2],audio_underruns=delta[3],layout_faults=a.peek(S['layout_faults'])[0])
   assert timing['render_fps']>=29.8 and not any(timing[n] for n in ['late_vbi','audio_underruns','layout_faults']),timing
   a.joy(0)
   errors=0; points=0
   for sample in range(24):
    a.poke(S['invuln'],255); a.frame(7)
    a.bp_set(S['nmi_handler']); a.cycles(40000)
    assert int(a.regs()['PC'][1:],16)==S['nmi_handler']; a.bp_clear_all()
    m=a.memdump(0,16384); b=m[S['front_buffer']]
    expected=np.zeros((168,256),bool)
    for y in range(168):
     for col in range(32):
      ch=m[0x2800+b*1024+y//8*32+col]
      if not ch&128:continue
      bits=m[0x2000+b*1024+(ch&127)*8+y%8]
      for px in range(4):
       if bits>>(6-px*2)&3==3:expected[y,col*8+px*2:col*8+px*2+2]=True
    png=a.screenshot(); screen=np.asarray(Image.open(io.BytesIO(png)).convert('RGB'))
    actual=np.all(screen[24:192,40:296]==blue,axis=2)
    count=int(np.count_nonzero(actual!=expected));errors+=count;points+=int(expected.sum())
    assert count==0,(wave,sample,count)
    if sample in [0,12]:(O/f'wave{wave}-{sample}.png').write_bytes(png)
   results.append(dict(wave=wave,scroll_phases=len(phases),samples=24,
                       compared_pixels=24*168*256,star_pixels=points,pixel_errors=errors,**timing))
   print(results[-1],flush=True)
finally:
 ff.stdin.close(); assert ff.wait()==0
report=dict(method=__doc__,car_sha256=hashlib.sha256((ROOT/'Phoenix800XL.car').read_bytes()).hexdigest(),
            stars_rgb=blue.tolist(),results=results,movie_frames=600)
(O/'report.json').write_text(json.dumps(report,indent=2))
