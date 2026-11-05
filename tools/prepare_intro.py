"""Build attract pages from the same pixel arrays used by the game renderers.

The legacy pages supply lettering only. Bird silhouettes are neither resized
nor reconstructed from those old pictures.
"""
from pathlib import Path
import json

R=Path(__file__).resolve().parents[1]
A=R/'src/arcade-assets'
B=R/'build'
WIDTH,HEIGHT=160,192
SMALL=[0,14,44,90]
LARGE=[0,172,44,134]
BOSS=[0,26,44,90]
OLD=[0,168,90,44,14]
START_ROWS=[0,4,8,12,16,19,21]

def old_lettering(n):
 data=(A/f'presentation-{n}.bin').read_bytes()
 out=[[0]*WIDTH for _ in range(HEIGHT)]
 for r in range(24):
  for c in range(40):
   ch=data[6144+r*40+c]
   tile=data[(r//4)*1024+(ch&127)*8:(r//4)*1024+(ch&127)*8+8]
   for y,v in enumerate(tile):
    for x in range(4):
     pen=(v>>(6-x*2))&3
     out[r*8+y][c*4+x]=OLD[4 if pen==3 and ch&128 else pen]
 return out

def pack_fonts(pages,palettes):
 fonts=[];maps=bytearray();font_tables=[]
 for page,palette in zip(pages,palettes):
  for i in range(1,len(START_ROWS)):
   if palette[i]!=palette[i-1]:
    assert not any(page[START_ROWS[i]*8-1]),('palette boundary',i)
  page_map=bytearray();font_ids=[]
  for band,start_row in enumerate(START_ROWS):
   tiles=[bytes(8)]
   end_row=START_ROWS[band+1] if band+1<len(START_ROWS) else 24
   for r in range(start_row,end_row):
    colors=palette[band]
    for c in range(40):
     block=[row[c*4:c*4+4]for row in page[r*8:r*8+8]]
     has3=any(colors[2] in row for row in block)
     has4=any(colors[3] in row for row in block)
     assert not(has3 and has4),(r,c,'mixed ANTIC alternate color')
     flag=128 if has4 else 0
     lookup={0:0,colors[0]:1,colors[1]:2,(colors[3] if flag else colors[2]):3}
     tile=bytes(sum(lookup[v]<<(6-x*2)for x,v in enumerate(row))for row in block)
     if tile not in tiles:tiles.append(tile)
     page_map.append(tiles.index(tile)|flag)
   assert len(tiles)<=128,(band,len(tiles))
   font=b''.join(tiles)+bytes((128-len(tiles))*8)
   if font not in fonts:fonts.append(font)
   font_ids.append(0x10+4*fonts.index(font))
  font_tables.extend(font_ids)
  if maps:maps.extend(bytes(64))
  maps.extend(page_map)
 assert len(fonts)<=12,len(fonts)
 # Palette bytes occupy the existing 64-byte gap before the second map.
 all_palettes=palettes[0]+palettes[1]
 color_bytes=bytes(p[k]for k in range(4)for p in all_palettes)
 assert len(color_bytes)==56
 maps[960:1016]=color_bytes
 raw=b''.join(fonts);packed=bytearray();i=0
 while i<len(raw):
  n=1
  while i+n<len(raw) and raw[i+n]==raw[i] and n<128:n+=1
  if n>=3:
   packed.extend([127+n,raw[i]]);i+=n
  else:
   start=i;i+=n
   while i<len(raw) and i-start<128:
    n=1
    while i+n<len(raw) and raw[i+n]==raw[i] and n<128:n+=1
    if n>=3 or i+n-start>128:break
    i+=n
   packed.append(i-start-1);packed.extend(raw[start:i])
 (B/'intro-fonts.bin').write_bytes(raw)
 (B/'intro-fonts-packed.bin').write_bytes(packed)
 (B/'intro-maps.bin').write_bytes(maps)
 (B/'intro-font-table.bin').write_bytes(bytes(font_tables))
 return dict(unique_rom_fonts=len(fonts),font_bytes=len(raw),packed_font_bytes=len(packed),map_bytes=len(maps))

def prepare():
 native=json.loads((B/'sprite-manifest.json').read_text())
 poses={p['shape']:p['pixels']for p in native['poses']}
 large=json.loads((B/'flight-art.json').read_text())['frames']
 glyphs=(B/'boss-glyphs.bin').read_bytes()
 title=[[0]*WIDTH for _ in range(HEIGHT)]
 old_title=old_lettering(9)
 for y in list(range(24))+list(range(168,192)):title[y]=old_title[y][:]
 stars=json.loads((A/'stars-irregular.json').read_text())['cells']
 for row,col in stars:
  y=row*8+3;x=col*4
  if 24<=y<168 and not(62<=y<114):title[y][x]=168
 copies=[]
 def stamp(page,pixels,x,y,palette,source):
  copies.append(dict(page='title' if page is title else 'scores',source=source,x=x,y=y,pixels=pixels,palette=palette))
  for yy,row in enumerate(pixels):
   for xx,v in enumerate(row):
    if v and 0<=x+xx<WIDTH and 0<=y+yy<HEIGHT:
     assert page[y+yy][x+xx]==0,(source,x+xx,y+yy)
     page[y+yy][x+xx]=palette[v]
 # Each occupied letter cell is an intact gameplay pose, copied at 1:1.
 letters={
  'P':['111','101','111','100','100'],
  'H':['101','101','111','101','101'],
  'O':['111','101','101','101','111'],
  'E':['111','100','110','100','111'],
  'N':['1001','1101','1011','1001','1001'],
  'I':['1','1','1','1','1'],
  'X':['101','101','010','101','101'],
 }
 cursor=0
 for char in 'PHOENIX':
  rows=letters[char]
  for row,line in enumerate(rows):
   for col,v in enumerate(line):
    if v=='1':stamp(title,poses[32],2+(cursor+col)*6,64+row*10,SMALL,dict(kind='small',shape=32,letter=char))
  cursor+=len(rows[0])+1
 scores=old_lettering(8)
 # Leave the last line before the large-bird palette blank. This shifts only
 # the 200-point text by one line; the sprite pixels retain their native size.
 text200=[row[50:] for row in scores[120:128]]
 for y in range(120,128):scores[y][50:]=[0]*(WIDTH-50)
 for y,row in enumerate(text200):scores[119+y][50:]=row
 # Remove every old illustration, keeping the original score text and footer.
 for y in range(100,168):scores[y][:50]=[0]*50
 stamp(scores,poses[36],23,104,SMALL,dict(kind='small',shape=36))
 # These are the two actual gameplay poses named by the original score table.
 stamp(scores,poses[220],20,112,SMALL,dict(kind='small',shape=220))
 stamp(scores,poses[204],28,112,SMALL,dict(kind='small',shape=204))
 stamp(scores,large[40],12,134,LARGE,dict(kind='large',pose=40))
 pilot=[[0]*8 for _ in range(16)]
 for cx,codes in enumerate([[0x74,0x7c],[0x75,0x7d]]):
  for cy,code in enumerate(codes):
   for y,v in enumerate(glyphs[code*8:code*8+8]):
    for x in range(4):pilot[cy*8+y][cx*4+x]=(v>>(6-x*2))&3
 stamp(scores,pilot,24,152,BOSS,dict(kind='pilot',tiles=[0x74,0x7c,0x75,0x7d]))
 base=[14,44,90,168]
 title_palette=[OLD[1:][:]for _ in START_ROWS]
 title_palette[2]=base[:]
 title_palette[3]=base[:]
 score_palette=[OLD[1:][:]for _ in START_ROWS]
 score_palette[3]=base[:]
 score_palette[4]=[172,44,134,90]
 score_palette[5]=[26,44,90,168]
 score_palette[6]=score_palette[5][:]
 for y in range(168,192):
  scores[y]=[168 if v else 0 for v in scores[y]]
 # Text in the large-bird band uses its cyan and alternate pink, so no part of
 # the bird is recolored to fit a separate presentation palette.
 for y in range(128,152):
  for x in range(50,WIDTH):
   if scores[y][x]==168:scores[y][x]=172
 info=pack_fonts([title,scores],[title_palette,score_palette])
 info.update(pages=['gameplay-sprite PHOENIX title','gameplay-sprite score table'],startup_font_ram=[4096,4096+info['font_bytes']],sprite_method='Unscaled gameplay pixels; legacy page graphics discarded',title_shape=32,title_birds=sum(c['page']=='title'for c in copies),band_start_rows=START_ROWS,colors=[title_palette,score_palette])
 (B/'intro-art-manifest.json').write_text(json.dumps(dict(**info,sprite_copies=copies,pages_pixels=[title,scores])))
 manifest=json.loads((B/'art-manifest.json').read_text());manifest.update(info)
 (B/'art-manifest.json').write_text(json.dumps(manifest,indent=2))
 print('Startup: gameplay sprite copies,',info['title_birds'],'title birds,',info['unique_rom_fonts'],'fonts,',info['packed_font_bytes'],'packed bytes')

if __name__=='__main__':prepare()
