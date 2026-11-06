"""Compile supplied 5200 bird pixels and effect tiles without redrawing.
All console execution remains 6502. Host Python generates immutable ROM data.
"""
from pathlib import Path
from collections import Counter
import re,json,math
import numpy as np
import supplied_art as supplied
R=Path(__file__).resolve().parents[1];B=R/'build';A=R/'src/arcade-assets'
def tables():
 s=(A/'phoenix_tables.c').read_text()
 return {m[1]:bytes(int(x,16) for x in re.findall(r'0x([0-9a-fA-F]{2})',m[2])) for m in re.finditer(r'const uint8_t phoenix_(\w+)\[[^]]*\]\s*=\s*\{(.*?)\};',s,re.S)}
def prepare():
 t=tables();inc=[]
 data=json.loads((A/'audio-circuit.json').read_text())
 look=bytearray()
 # One delta table replaces six copies of the same RC response.
 for delta in range(256):look.append((delta*14+128)>>8)
 for level in range(256):look.append(max(0,min(255,level+round((171-level)*24/256))))
 for which in ['a','b']:
  for lo,hi in zip(data['vco_'+which+'_ntsc_lo'],data['vco_'+which+'_ntsc_hi']):
   for nib in range(16):
    period=(lo+256*hi)*(16-nib)/256
    # Channel 3's independent 1.79 MHz clock removes the coarse 64 kHz
    # pitch staircase from high bird whistles, without changing channel 4.
    fast=round(period*28)-4
    value=fast if which=='a' and nib<15 and 64<=fast<=255 else round(period)-1
    look.append(max(0,min(255,value)))
 (B/'audio-lookup.bin').write_bytes(look)
 # C24/C25 values from MAME's Phoenix circuit, evaluated once per 61 Hz
 # control tick. Six-bit capacitor levels exceed POKEY's four-bit volume.
 noise=bytearray()
 for target,tau in [(63,.136),(0,.009044)]:
  for level in range(64):
   step=round((target-level)*(1-math.exp(-1/(61*tau))))
   if not step and target!=level:step=1 if target>level else -1
   noise.append(max(0,min(63,level+step)))
 # The upper half covers the sum of C24 and C25 during overlapping effects.
 # The unused six-bit C25 tables are removed; C25 uses eight-bit tables below.
 for level in range(128):noise.append(round((1789772.5/28)/(588+6325*min(level,126)/126))-1)
 for level in range(64):noise.append(0 if level<3 else 0x80+round(8*level/63))
 # The selected bird-siren filter has R=10k||100k and C=0.047 uF.
 # Match its fundamental attenuation; POKEY cannot reproduce its exact shape.
 cutoff=1/(2*math.pi*(10000*100000/110000)*.047e-6)
 for divisor in range(256):
  hz=1789772.5/(56*(divisor+1))
  noise.append(0xa0+max(1,round(8*.909/math.sqrt(1+(hz/cutoff)**2))))
 (B/'audio-noise.bin').write_bytes(noise)
 # Eight-bit explosion capacitors avoid the premature tail cutoff caused by
 # rounding every six-bit decay step to an integer (and then forcing -1).
 for label,target,tau in [('charge',255,.009044),('release',0,.3196)]:
  values=[]
  for level in range(256):
   step=round((target-level)*(1-math.exp(-1/(61*tau))))
   if not step and target!=level:step=1 if target>level else -1
   values.append(max(0,min(255,level+step)))
  (B/('death-'+label+'-8bit.bin')).write_bytes(bytes(values))
 (B/'audio-tables.inc').write_text('\n'.join(k+': .byte '+','.join(map(str,v)) for k,v in data.items() if not k.startswith('vco_') and k not in ('noise_frequency','noise_volume'))+'\n')
 for n in ['bird_data_alt_page','bird_formation_params','bird_scroll_steps','bird_descent_caps','bird_behaviour_scripts','bird_sound_cadence']:(B/(n+'.bin')).write_bytes(t[n])
 for n in ['alien_movement_cluster_a','alien_movement_cluster_b','alien_shape_offset_page','alien_direction_vectors','alien_distance_bands','alien_pattern_selectors','alien_closed_loop_pointers','formation_hit_window','player_x_position_mapping','sprite_character_block_shapes']:
  (B/(n+'.bin')).write_bytes(t[n]);inc.append(f'{n}: .incbin "build/{n}.bin"')
 (B/'arcade-tables.inc').write_text('\n'.join(inc)+'\n')
 (B/'map_x.bin').write_bytes(bytes(76+v//2 for v in range(256)))
 (B/'map_y.bin').write_bytes(bytes(min(255,8+v) for v in range(256)))
 a=t['alien_shape_offset_page'];sh=t['sprite_character_block_shapes'];pairs={(1,32)} | {(0,v) for v in range(240,245)}
 for v in range(1,32):
  kind,flags,base=a[0xa0+v*3:0xa3+v*3]
  if kind not in (0,1,3,4):continue
  for i in range(8 if flags&1 else 4):
   shape=a[base+i]
   if shape!=255:pairs.add((kind,shape))
 art=(A/'original-art-bank1.bin').read_bytes();tiles=[bytes(8)];poses=[];freq=Counter()
 original_rgb=json.loads((A/'foreground-rgb.json').read_text())['fg']
 for kind,shape in sorted(pairs):
  w,h={0:(1,1),1:(2,1),3:(1,2),4:(2,2)}[kind];ids=[0]*4
  if kind:
   original=np.zeros((h*8,w*4),dtype=np.uint8)
   for cx in range(w):
    for cy in range(h):
     tile=np.asarray(original_rgb[str(sh[shape+cx*h+cy])])
     original[cy*8:cy*8+8,cx*4:cx*4+4]=np.any(tile.reshape(8,4,2,3),axis=(2,3))
   pixels,provenance=supplied.small(shape,kind,original)
   w=2;h=len(pixels)//8
  else:
   code={240:108,241:109,242:110,243:111,244:104}[shape]
   pixels=[[{0:0,1:1,2:3,3:2}[art[y*256+code]>>(6-2*x)&3] for x in range(4)] for y in range(8)]
  for cx in range(w):
   for cy in range(h):
    tile=bytes(sum(pixels[cy*8+y][cx*4+x]<<(6-2*x) for x in range(4))for y in range(8))
    if tile not in tiles:tiles.append(tile)
    tid=tiles.index(tile);ids[cy*2+cx]=tid
    if tid and kind:freq[tid]+=1
  poses.append(dict(kind=kind,shape=shape,pixels=pixels,tiles=ids,source=provenance if kind else None))
 # Four exact yellow 5200 explosion frames, held eight two-tick snapshots
 # each. The death timer, collision lockout and sound duration are unchanged.
 effects=[];flags=[0]*len(tiles);color_losses=0;sample_losses=0
 colors=[(0,0,0),(255,255,255),(246,246,68),(211,31,210),(202,22,24)]
 def classify(rgb):
  return min(range(5),key=lambda k:sum((rgb[i]-colors[k][i])**2 for i in range(3)))
 for counter in range(32):
  pixels=np.pad(supplied.pixels('explosion',counter//8),((0,0),(2,2)));cells=[]
  for cx in range(5):
   for cy in range(4):
    tile=bytes(sum(int(pixels[cy*8+y,cx*4+x])<<(6-2*x) for x in range(4))for y in range(8))
    if not any(tile):continue
    found=next((i for i,p in enumerate(tiles) if p==tile and flags[i]==0),None)
    if found is None:found=len(tiles);tiles.append(tile);flags.append(0)
    cells.append([(cx+6)*16+cy+10,found])
  effects.append(cells)
 layouts=[];indexes=[]
 for cells in effects:
  if cells not in layouts:layouts.append(cells)
  indexes.append(layouts.index(cells))
 # Six foreground cells per hit burst, source table at arcade $17B8.
 rgb=json.loads((A/'foreground-rgb.json').read_text())['fg'];burstposes=[]
 def rgb_tile(code):
  # Same two-pixel quantization as ship effects, with transparent background.
  pix=rgb[str(code)];rows=[]
  for row in pix:
   out=[]
   for x in range(0,8,2):
    pair=[classify(v) for v in row[x:x+2]]
    out.append(1 if 1 in pair else next((v for v in pair if v),0))
   rows.append(out)
  cnt=Counter(v for row in rows for v in row);flag=128 if cnt[4]>=cnt[3] and cnt[4] else 0
  tile=bytes(sum((3 if v in (3,4) else v)<<(6-2*x) for x,v in enumerate(row)) for row in rows)
  found=next((i for i,p in enumerate(tiles) if (p,flags[i])==(tile,flag)),None)
  if found is None:found=len(tiles);tiles.append(tile);flags.append(flag)
  return found
 # Restore the pre-artwork bird-hit sequence. The purple creature in
 # supplied row 06 is not a bird explosion; keep that artwork unassigned.
 for index in range(8):
  off=t['alien_explosion_frames'][index]-0xb8
  codes=t['shield_and_drawnx2_shapes'][off:off+6]
  assert len(codes)==6
  burstposes.append([rgb_tile(c) for c in codes])
 (B/'burst-shapes.bin').write_bytes(bytes(v for p in burstposes for v in p))
 bonus_parts=[rgb_tile(c) for c in t['shield_and_drawnx2_shapes'][24:36]]
 bonus_numbers=[rgb_tile(32+c) for c in range(10)]
 (B/'bonus-parts.bin').write_bytes(bytes(bonus_parts))
 (B/'bonus-numbers.bin').write_bytes(bytes(bonus_numbers))
 # Original four 32-row shield arrangements, with no vertical compression.
 # Green is carried by the two ship players, other colors by 16 fixed cells.
 shield=[];fonts=[];maps=[];green=[];losses=0
 sc=[(0,0,0),(255,255,255),(246,246,68),(165,24,165),(202,22,24),(35,173,36)]
 for pose in range(4):
  pixels=supplied.pixels('shield',pose).tolist()
  # White/yellow ship pixels share the shield's playfield; red uses PM2.
  ship=supplied.pixels('player-ship',0)
  for yy in range(16):
   for xx in range(16):
    if ship[yy,xx] in (1,2):
     assert pixels[yy+8][xx]==0
     pixels[yy+8][xx]=int(ship[yy,xx])
  font=[];chars=[]
  for cx in range(4):
   for cy in range(4):
    block=[row[cx*4:cx*4+4] for row in pixels[cy*8:cy*8+8]]
    cnt=Counter(v for row in block for v in row);red=cnt[4]>cnt[3];losses+=min(cnt[4],cnt[3])
    chars.append(112+cx*4+cy+(128 if red else 0))
    for row in block:font.append(sum((0 if v==5 else 3 if v in (3,4) else v)<<(6-2*x) for x,v in enumerate(row)))
    for yy,row in enumerate(block):
     for xx,v in enumerate(row):
      if v in (3,4):pixels[cy*8+yy][cx*4+xx]=4 if red else 3
  mask=[sum(int(pixels[y][x+side*8]==5)<<(7-x) for x in range(8)) for side in range(2) for y in range(32)]
  fonts.extend(font);maps.extend(chars);green.extend(mask);shield.append(pixels)
 unique=[];staticmaps=[]
 for i,code in enumerate(maps):
  tile=bytes(fonts[i*8:i*8+8])
  if not any(tile):staticmaps.append(0);continue
  if tile not in unique:unique.append(tile)
  staticmaps.append(100+unique.index(tile)+(code&128))
 assert len(unique)<=28,('shield glyphs',len(unique))
 unique+= [bytes(8)]*(28-len(unique))
 (B/'shield-unique.bin').write_bytes(b''.join(unique));maps=staticmaps
 (B/'shield-fonts.bin').write_bytes(bytes(fonts));(B/'shield-maps.bin').write_bytes(bytes(maps));(B/'shield-green.bin').write_bytes(bytes(green));(B/'shield-codes.bin').write_bytes(t['shield_table'])
 (B/'shield-manifest.json').write_text(json.dumps(dict(pixels=shield,hue_conflicts=losses,source='Supplied 5200 shield plus unscaled player pose 0 centered at y=8; red player pixels on PM2',vertical_rows=list(range(32)),horizontal_priority=[1,4,3,5,2],resident_glyphs=list(range(100,128)),resident_count=28,active_glyphs_per_pose_max=16,green_player_color=198),indent=2))
 music=json.loads((A/'music-recovered.json').read_text())
 (B/'music-theme.bin').write_bytes(bytes(music['theme']))
 (B/'music-volume0.bin').write_bytes(bytes(music['volume0']))
 (B/'music-volume1.bin').write_bytes(bytes(music['volume1']))
 (B/'explosion-index.bin').write_bytes(bytes(indexes))
 (B/'native-flags.bin').write_bytes(bytes(flags))
 effectinc=[]
 for i,cells in enumerate(layouts):
  effectinc.append(f'explosion_{i}: .byte '+','.join(map(str,[len(cells)]+[n for c in cells for n in c])))
 (B/'explosion-data.inc').write_text('\n'.join(effectinc)+'\n')
 (B/'explosion-pointers.inc').write_text('explosion_ptrs: .word '+','.join('explosion_'+str(i) for i in range(len(layouts)))+'\n')
 static=[k for k,n in freq.most_common(30)]
 # Keep the score wings, digits and most-used hit tiles resident as well.
 # These appear together in crowded death scenes; making them immutable
 # avoids a burst of cold-cache copies exactly when the frame is busiest.
 effectfreq=Counter(bonus_parts*4+bonus_numbers*2+[v for p in burstposes for v in p])
 for tid,_ in effectfreq.most_common():
  if tid and tid not in static and len(static)<62:static.append(tid)
 for tid in range(1,len(tiles)):
  if tid not in static and len(static)<62:static.append(tid)
 assert len(static)==62
 assert len(tiles)<=256,('native template capacity',len(tiles))
 cache=bytearray(len(tiles));font=bytearray(512)
 font[8:16]=bytes([0,0,0,12,0,0,0,0])
 for ch,tid in enumerate(static,2):cache[tid]=ch|flags[tid];font[ch*8:ch*8+8]=tiles[tid]
 reverse=bytearray(128)
 for ch,tid in enumerate(static,2):reverse[ch]=tid
 (B/'native-last.bin').write_bytes(reverse)
 (B/'native-static.bin').write_bytes(font);(B/'native-cache.bin').write_bytes(cache)
 (B/'native-tiles.bin').write_bytes(bytes(tile[row] for row in range(8) for tile in tiles))
 (B/'native-masks.bin').write_bytes(bytes(sum((0 if tile[3]>>(6-2*x)&3 else 3)<<(6-2*x) for x in range(4)) for tile in tiles))
 shape_ids=bytearray([255]*256)
 for i,p in enumerate(poses):shape_ids[p['shape']]=i
 (B/'shape-ids.bin').write_bytes(shape_ids)
 (B/'native-shapes.bin').write_bytes(bytes(v for p in poses for v in p['tiles']))
 (B/'native-count.inc').write_text(f'.set TEMPLATE_COUNT,{len(tiles)}\n')
 (B/'sprite-manifest.json').write_text(json.dumps(dict(art_variant='supplied right-hand Atari 5200 GIF artwork; whole-pixel translations only',poses=poses,tiles=[list(p) for p in tiles],flags=flags,static_templates=static,explosions=effects,bursts=burstposes,burst_source="v0.25 bird-hit sequence; supplied purple creature excluded",bonus_parts=bonus_parts,bonus_numbers=bonus_numbers,explosion_color_conflict_pixels=color_losses,horizontal_pair_conflicts=sample_losses,geometry='MAME raw X/2 +76; raw Y+8. Sprite blocks use raw coordinate rounded down to 8; artwork itself supplies the fine phase.',dynamic_allocation_bound=None,shield_allocation_bound=None,shield_total_glyph_bound=None,death_allocation_bound=None,first_dynamic_glyph=64,allocation_bound_reason="Sixty-two immutable templates, plus protected persistent dynamic glyphs. Capacity is checked in 1,168 sprite/edge/death scenes, 480 effect-overlap scenes and original-BIOS elapsed fixtures; these are sampled checks, not an exhaustive proof over all possible states.",native_data_layout="Eight ROM rows; template id indexes one byte in each row. The background star uses a direct transparency test on its single row."),indent=2))
 print('Native arcade renderer:',len(poses),'poses,',len(tiles),'templates; 62 resident templates')
if __name__=='__main__':prepare()
