"""Compile explicitly authored symmetric bird pixels and recovered effect tiles.
All console execution remains 6502. Host Python generates immutable ROM data.
"""
from pathlib import Path
from collections import Counter
import re,json
R=Path(__file__).resolve().parents[1];B=R/'build';A=R/'src/arcade-assets'
def tables():
 s=(A/'phoenix_tables.c').read_text()
 return {m[1]:bytes(int(x,16) for x in re.findall(r'0x([0-9a-fA-F]{2})',m[2])) for m in re.finditer(r'const uint8_t phoenix_(\w+)\[[^]]*\]\s*=\s*\{(.*?)\};',s,re.S)}
def prepare():
 t=tables();inc=[]
 data=json.loads((A/'audio-circuit.json').read_text())
 look=bytearray()
 for target in data['c22_target']:
  for level in range(256):look.append((level+((abs(target-level)*14+128)>>8)*(1 if target>=level else -1))&255)
 for level in range(256):look.append((level+(((171-level)&255)*24+128>>8))&255)
 for which in ['a','b']:
  for lo,hi in zip(data['vco_'+which+'_ntsc_lo'],data['vco_'+which+'_ntsc_hi']):
   for nib in range(16):look.append(((((lo+256*hi)*(16-nib)+128)>>8)-1)&255)
 (B/'audio-lookup.bin').write_bytes(look)
 (B/'audio-tables.inc').write_text('\n'.join(k+': .byte '+','.join(map(str,v)) for k,v in data.items() if not k.startswith('vco_') and k!='c22_target')+'\n')
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
 authored=json.loads((A/'birds-symmetric.json').read_text())['poses']
 for kind,shape in sorted(pairs):
  w,h={0:(1,1),1:(2,1),3:(1,2),4:(2,2)}[kind];ids=[0]*4
  if kind:
   record=authored[str(shape)];assert record['kind']==kind
   w=len(record['rows'][0])//4;h=len(record['rows'])//8
   pixels=[[".WYP".index(c) for c in row] for row in record['rows']]
  else:
   code={240:108,241:109,242:110,243:111,244:104}[shape]
   pixels=[[{0:0,1:1,2:3,3:2}[art[y*256+code]>>(6-2*x)&3] for x in range(4)] for y in range(8)]
  for cx in range(w):
   for cy in range(h):
    tile=bytes(sum(pixels[cy*8+y][cx*4+x]<<(6-2*x) for x in range(4))for y in range(8))
    if tile not in tiles:tiles.append(tile)
    tid=tiles.index(tile);ids[cy*2+cx]=tid
    if tid and kind:freq[tid]+=1
  poses.append(dict(kind=kind,shape=shape,pixels=pixels,tiles=ids))
 # Death effects: 32 two-tick snapshots from the recovered ROM's alternating
 # particle and background-core writes. Keep source RGB in a separate asset.
 source=json.loads((A/'explosion-art.json').read_text());pg=t['explosion_particle_page'];ptrs=t['mothership_explosion_pointers']
 fg=[0]*256;bg=[0]*256;effects=[];flags=[0]*len(tiles);color_losses=0;sample_losses=0
 colors=[(0,0,0),(255,255,255),(246,246,68),(211,31,210),(202,22,24)]
 def classify(rgb):
  return min(range(5),key=lambda k:sum((rgb[i]-colors[k][i])**2 for i in range(3)))
 for counter in range(95,32,-2):
  if counter&2:
   ctrl=0x100+0xe0-(((counter-32)<<2)&0xe0)
   fg=[pg[i] if pg[ctrl+i//8]&(1<<(i%8)) else 0 for i in range(256)]
  else:
   off=0x50+((counter>>2)&14);addr=int.from_bytes(ptrs[off:off+2],'big')
   codes=bytes(16) if addr==0x17f0 else ptrs[addr-0x1b40:addr-0x1b40+16]
   for x in range(4):
    for y in range(4):bg[(x+6)*16+y+10]=codes[x*4+y]
  # Full foreground/background composition is fitted together, so decorative
  # foreground pixels remain attached to the background explosion core.
  # The 32-row core uses 24 rows; sparse lower particles occupy the last four.
  fitted=[[0]*128 for _ in range(104)]
  for cell in range(256):
   cx,cy=divmod(cell,16)
   fp=source['fg'][str(fg[cell])];bp=source['bg'][str(bg[cell])]
   for y in range(8):
    sy=cy*8+y
    fy=(sy*76//80) if sy<80 else (76+(sy-80)*3//4) if sy<112 else 100+(sy-112)//4
    for x in range(8):
     xx=cx*8+x;v=classify(fp[y][x] if any(fp[y][x]) else bp[y][x])
     old=fitted[fy][xx]
     if v:fitted[fy][xx]=1 if old==1 or v==1 else v
  cells=[]
  for cx in range(16):
   for cy in range(13):
    pixels=[]
    for y in range(8):
     row=[]
     for x in range(4):
      yy=cy*8+y;xx=cx*8+x*2
      pair=[fitted[yy][xx+i] for i in range(2)]
      sample_losses+=int(pair[0]!=pair[1] and all(pair))
      row.append(1 if 1 in pair else next((v for v in pair if v),0))
     pixels.append(row)
    if not any(map(any,pixels)):continue
    cnt=Counter(v for row in pixels for v in row)
    flag=128 if cnt[4]>=cnt[3] and cnt[4] else 0
    color_losses+=cnt[3] if flag else cnt[4]
    tile=bytes(sum((3 if v in (3,4) else v)<<(6-2*x) for x,v in enumerate(row)) for row in pixels)
    key=(tile,flag)
    found=next((i for i,p in enumerate(tiles) if (p,flags[i])==key),None)
    if found is None:found=len(tiles);tiles.append(tile);flags.append(flag)
    cells.append([cx*16+cy,found])
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
 # Original four shield arrangements; full composition fitted into 24 rows.
 # Green is carried by the two ship players, other colors by 12 fixed cells.
 shield=[];fonts=[];maps=[];green=[];losses=0
 sc=[(0,0,0),(255,255,255),(246,246,68),(165,24,165),(202,22,24),(35,173,36)]
 for pose in range(4):
  pixels=[]
  for y in range(24):
   sy=int((y+.5)*32/24);row=[]
   for x in range(16):
    pair=[sc.index(tuple(rgb[str(t['shield_table'][pose*16+(sx//8)*4+sy//8])][sy%8][sx%8])) for sx in [x*2,x*2+1]]
    row.append(next((c for c in [1,4,3,5,2] if c in pair),0))
   pixels.append(row)
  font=[];chars=[]
  for cx in range(4):
   for cy in range(3):
    block=[row[cx*4:cx*4+4] for row in pixels[cy*8:cy*8+8]]
    cnt=Counter(v for row in block for v in row);red=cnt[4]>cnt[3];losses+=min(cnt[4],cnt[3])
    chars.append(116+cx*3+cy+(128 if red else 0))
    for row in block:font.append(sum((0 if v==5 else 3 if v in (3,4) else v)<<(6-2*x) for x,v in enumerate(row)))
    for yy,row in enumerate(block):
     for xx,v in enumerate(row):
      if v in (3,4):pixels[cy*8+yy][cx*4+xx]=4 if red else 3
  mask=[sum(int(pixels[y][x+side*8]==5)<<(7-x) for x in range(8)) for side in range(2) for y in range(24)]
  fonts.extend(font);maps.extend(chars);green.extend(mask);shield.append(pixels)
 unique=[];staticmaps=[]
 for i,code in enumerate(maps):
  tile=bytes(fonts[(i//12)*96+(i%12)*8:(i//12)*96+(i%12)*8+8])
  if not any(tile):staticmaps.append(0);continue
  if tile not in unique:unique.append(tile)
  staticmaps.append(102+unique.index(tile)+(code&128))
 assert len(unique)==26
 spare=[]
 for pose in range(4):
  used={v&127 for v in staticmaps[pose*12:pose*12+12]}
  available=[v for v in range(102,128) if v not in used]
  assert len(available)>=14
  spare.extend(available[:14]+[0,0])
 (B/'shield-unique.bin').write_bytes(b''.join(unique));(B/'shield-spare.bin').write_bytes(bytes(spare));maps=staticmaps
 (B/'shield-fonts.bin').write_bytes(bytes(fonts));(B/'shield-maps.bin').write_bytes(bytes(maps));(B/'shield-green.bin').write_bytes(bytes(green));(B/'shield-codes.bin').write_bytes(t['shield_table'])
 (B/'shield-manifest.json').write_text(json.dumps(dict(pixels=shield,hue_conflicts=losses,source='Recovered MAME foreground RGB and ROM table $1770',vertical_rows=[int((y+.5)*32/24) for y in range(24)],horizontal_priority=[1,4,3,5,2],resident_glyphs=list(range(102,128)),resident_count=26,active_glyphs_per_pose_max=12,spare_slots_per_pose_min=14,green_player_color=198),indent=2))
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
 assert len(static)==62
 cache=bytearray(len(tiles));font=bytearray(512)
 font[8:16]=bytes([0,0,0,4,0,0,0,0])
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
 (B/'sprite-manifest.json').write_text(json.dumps(dict(art_variant='authored symmetry comparison',poses=poses,tiles=[list(p) for p in tiles],flags=flags,static_templates=static,explosions=effects,bursts=burstposes,bonus_parts=bonus_parts,bonus_numbers=bonus_numbers,explosion_color_conflict_pixels=color_losses,horizontal_pair_conflicts=sample_losses,geometry='MAME raw X/2 +76; raw Y+8. Sprite blocks use raw coordinate rounded down to 8; artwork itself supplies the fine phase.',dynamic_allocation_bound=None,shield_allocation_bound=None,shield_total_glyph_bound=None,death_allocation_bound=None,first_dynamic_glyph=64,allocation_bound_reason="Sixty-two immutable templates, plus protected persistent dynamic glyphs. Capacity is checked in 1,168 sprite/edge/death scenes, 480 effect-overlap scenes and original-BIOS elapsed fixtures; these are sampled checks, not an exhaustive proof over all possible states.",native_data_layout="Eight ROM rows; template id indexes one byte in each row. The background star uses a direct transparency test on its single row."),indent=2))
 print('Native arcade renderer:',len(poses),'poses,',len(tiles),'templates; 62 resident templates')
if __name__=='__main__':prepare()
