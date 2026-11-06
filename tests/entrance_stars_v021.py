"""Player/input gate through the published mothership entrance, and palettes."""
from cpu_model import *
import hashlib
T=Model();T.init();m=T.m.b;m[S['wave']]=5;T.call('wave_reset');m[S['state']]=1
assert S['escort_population']==4 and S['escort_fast_threshold']==3
for tick in range(120):
 m[S['fire_edge']]=m[S['shield_edge']]=1;m[S['video_ship_x']]=150
 T.call('campaign_tick')
 assert m[S['shot_on']]==m[S['second_on']]==m[S['shield_locked']]==0
 assert m[S['fire_edge']]==m[S['shield_edge']]==0
assert m[S['boss_status']]==2 and m[S['boss_entrance_shown']]==1
for _ in range(8):
 m[S['fire_edge']]=m[S['shield_edge']]=1;m[S['video_ship_x']]=150
 T.call('campaign_tick');T.call('video_player_tick');T.call('render_live_ship')
 assert m[S['shot_on']]==m[S['second_on']]==m[S['shield_locked']]==0
 assert m[S['raw_ship_x']]==100 and m[S['ship_hpos']]==0
# Publishing the combat frame is the only event that opens the gate.
T.c.pc=S['publish_frame']
for _ in range(5):T.c.step()
assert m[S['boss_entrance_shown']]==0
m[S['fire_edge']]=1;T.call('campaign_tick');assert m[S['shot_on']]==1
palette_checks=0
for stage in range(4):
 for rn in range(0,256,16):
  m[S['large_shown']]=stage;m[S['level_round']]=rn+1;m[S['entrance_shown']]=0
  T.call('large_frame_palette')
  assert m[0xc019]==(0x82 if stage in (0,3) else 70)
  palette_checks+=1
report=dict(car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),entry_ticks=120,pending_display_ticks=8,fire_and_shield_ignored_during_entry=True,player_centered_after_entry=True,palette_checks=palette_checks,star_colour='GTIA $82 dark blue',escorts=4,fast_mode_below=3)
(R/'evidence/v021/entrance-stars.json').write_text(json.dumps(report,indent=2));print(report)
