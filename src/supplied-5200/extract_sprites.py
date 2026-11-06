"""Extract the supplied Phoenix comparison GIFs without changing artwork.

5200 artwork is the RIGHT member of EACH comparison pair. GIF disposal and
palette updates are decoded before cropping. PNGs retain capture dimensions.
The optional 2bpp data removes only exact 4x2 repeated display-pixel blocks.
Reconstruction from both packed layouts must reproduce every source pixel.
"""
from pathlib import Path
import argparse,hashlib,json,shutil,zipfile
from PIL import Image

P=argparse.ArgumentParser(description=__doc__)
P.add_argument('--large-gif',type=Path,required=True)
P.add_argument('--various-gif',type=Path,required=True)
P.add_argument('--out',type=Path,required=True)
A=P.parse_args();O=A.out.resolve();O.mkdir(parents=True,exist_ok=True)
manifest={'format_version':1,'selection':'Right member of every comparison pair is Atari 5200; left member is Atari 7800.',
 'pixel_policy':'Exact RGB crops. No drawing, color reduction, smoothing, interpolation, outline change, or sprite scaling.',
 'native_encoding':{'source_block_width':4,'source_block_height':2,'bpp':2,'bit_order':'Leftmost pixel is bits 7..6.',
  'background_index':0,'rowmajor':'Rows top to bottom; bytes left to right.',
  'tiles':'4x8 native pixels per tile; tiles across, then down; each tile has eight row bytes.'},
 'sources':{},'assets':[],'atlases':{}}

def digest(data):return hashlib.sha256(data).hexdigest()
def save_png(im,path):
 path.parent.mkdir(parents=True,exist_ok=True);im.save(path)
 assert Image.open(path).convert('RGB').tobytes()==im.tobytes()

def decode(source,name):
 dest=O/'sources'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
 gif=Image.open(source);frames=[];durations=[]
 for i in range(gif.n_frames):
  gif.seek(i);frame=gif.convert('RGB').copy();frames.append(frame);durations.append(gif.info.get('duration',0))
  save_png(frame,O/'full-comparison-frames'/name.removesuffix('.gif')/f'frame-{i:03d}.png')
 manifest['sources'][name]={'sha256':digest(source.read_bytes()),'size':list(gif.size),'frame_count':len(frames),
  'frame_durations_ms':durations,'loop':gif.info.get('loop'),'composited_frames':True}
 return frames,durations

def extract(frame,box,group,index,source,duration,atlas_box):
 crop=frame.crop(box);w,h=crop.size;pixels=list(crop.getdata())
 name=f'{group}/frame-{index:03d}'
 path=O/'frames-5200'/(name+'.png');save_png(crop,path)
 assert w%4==h%2==0
 nw,nh=w//4,h//2
 native=[crop.getpixel((x*4,y*2)) for y in range(nh) for x in range(nw)]
 palette=[(0,0,0)]+sorted(set(native)-{(0,0,0)})
 assert len(palette)<=4,(name,palette)
 lookup={rgb:i for i,rgb in enumerate(palette)}
 indices=[lookup[p] for p in native]
 assert nw%4==nh%8==0
 row=bytes(sum(indices[y*nw+x+j]<<(6-2*j) for j in range(4)) for y in range(nh) for x in range(0,nw,4))
 tiles=bytes(row[(ty+y)*(nw//4)+tx] for ty in range(0,nh,8) for tx in range(nw//4) for y in range(8))
 npath=O/'packed-5200'/name;npath.parent.mkdir(parents=True,exist_ok=True)
 npath.with_suffix('.row2bpp').write_bytes(row);npath.with_suffix('.tiles2bpp').write_bytes(tiles)
 # Decode both layouts and compare against all original RGB pixels, not just
 # the sampled block corner. This rejects any hidden resampling/color loss.
 for layout,data in [('rows',row),('tiles',tiles)]:
  restored=[0]*(nw*nh)
  if layout=='tiles':
   unpacked=bytearray(len(row));i=0
   for ty in range(0,nh,8):
    for tx in range(nw//4):
     for y in range(8):unpacked[(ty+y)*(nw//4)+tx]=data[i];i+=1
   data=unpacked
  for y in range(nh):
   for x in range(nw):restored[y*nw+x]=palette[(data[y*(nw//4)+x//4]>>(6-2*(x%4)))&3]
  expanded=[restored[(y//2)*nw+x//4] for y in range(h) for x in range(w)]
  assert pixels==expanded,(name,layout)
 asset={'id':name,'source':source,'source_frame':index,'duration_ms':duration,
  'source_crop_xyxy':list(box),'capture_size':[w,h],'native_grid_size':[nw,nh],
  'palette_rgb':[list(p) for p in palette],'rgba_background_policy':'Original opaque black retained.',
  'png':str(path.relative_to(O)),'pixel_sha256':digest(crop.tobytes()),
  'row2bpp':str(npath.with_suffix('.row2bpp').relative_to(O)),
  'tiles2bpp':str(npath.with_suffix('.tiles2bpp').relative_to(O)),
  'atlas_xywh':atlas_box,'roundtrip_pixel_difference_count':0}
 manifest['assets'].append(asset)
 return crop

large,ld=decode(A.large_gif,'big-bird-32.gif')
various,vd=decode(A.various_gif,'various3.gif')
assert all(im.size==(192,32) for im in large)
assert all(im.size==(224,224) for im in various)

big_atlas=Image.new('RGB',(384,32*((len(large)+3)//4)),(0,0,0))
for i,im in enumerate(large):
 x=i%4*96;y=i//4*32
 crop=extract(im,(96,0,192,32),'large-bird',i,'big-bird-32.gif',ld[i],[x,y,96,32]);big_atlas.paste(crop,(x,y))
big_name='Phoenix5200-Large-Bird-Sprites.png';save_png(big_atlas,O/big_name)
manifest['atlases'][big_name]={'size':list(big_atlas.size),'order':'Four columns, frame order left to right then down. Empty final cell is padding.','asset_prefix':'large-bird/'}

other_atlas=Image.new('RGB',(256,384),(0,0,0))
for f,im in enumerate(various):
 for row in range(7):
  crop=extract(im,(32,32*row,64,32*(row+1)),f'small-pose-row-{row:02d}',f,'various3.gif',vd[f],[f*32,row*32,32,32])
  other_atlas.paste(crop,(f*32,row*32))
 for name,box,y in [('player-ship',(160,0,224,32),224),('shield',(160,32,224,96),256),('explosion',(160,96,224,160),320)]:
  crop=extract(im,box,name,f,'various3.gif',vd[f],[f*64,y,64,box[3]-box[1]])
  other_atlas.paste(crop,(f*64,y))
other_name='Phoenix5200-Various-Sprites.png';save_png(other_atlas,O/other_name)
manifest['atlases'][other_name]={'size':list(other_atlas.size),'order':'Frames 0,1,2,3 left to right. Seven small-pose rows at y=0..223; ship at y=224; shield at y=256; explosion at y=320.','source':'various3.gif'}

for name,atlas in [(big_name,big_atlas),(other_name,other_atlas)]:
 for asset in manifest['assets']:
  if (name==big_name)!=(asset['source']=='big-bird-32.gif'):continue
  x,y,w,h=asset['atlas_xywh'];raw=Image.open(O/asset['png']).convert('RGB')
  assert atlas.crop((x,y,x+w,y+h)).tobytes()==raw.tobytes()
manifest['verification']={'decoded_gif_frames':len(large)+len(various),'extracted_5200_sprite_frames':len(manifest['assets']),
 'maximum_colors_including_background':max(len(a['palette_rgb']) for a in manifest['assets']),
 'native_row_and_tile_roundtrips_exact':True,'atlas_crops_exact':True,
 'right_hand_large_unique_frames':len({a['pixel_sha256'] for a in manifest['assets'] if a['source']=='big-bird-32.gif'}),
 'total_pixel_differences':0}
(O/'sprite-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(O/'README.txt').write_text('''PHOENIX — EXACT ATARI 5200 SPRITES FROM THE SUPPLIED GIFS

The right-hand artwork is used. The left-hand 7800 examples are retained only
inside the original GIFs and full comparison frames for reference.

23 large-bird animation frames and four various-sprite animation frames were
decoded. The various GIF has multiple LEFT/RIGHT pairs: it must not be split
down its overall midpoint. Its 5200 small sprites are x=32..63, while the 5200
ship, shield and explosion are x=160..223. All crop bounds are in the manifest.

PRIMARY FILES
Phoenix5200-Large-Bird-Sprites.png: four columns of 96x32 capture-size cells;
read left to right, then down. All 23 original 5200 animation frames are retained. The last cell is padding.

Phoenix5200-Various-Sprites.png: four animation frames left to right. The first
seven rows are 32x32 small-pose cells. These occupy the left 128 pixels. The
ship row begins at y=224 (64x32 cells); shield at y=256 (64x64); explosion at
y=320 (64x64). The source order, including the position of the ship, is kept.

frames-5200/: every selected sprite frame as an individual lossless RGB PNG.
full-comparison-frames/: all 27 original composite frames, retaining both systems.
sources/: byte-identical original GIFs with short names.
sprite-manifest.json: source hashes, crop rectangles, palettes, frame timing,
native dimensions, atlas positions and pixel-exact verification results.

NO ARTWORK WAS REDRAWN, SMOOTHED, RECOLORED OR STRETCHED.
Black backgrounds, all colored pixels and each sprite's placement within its
original cell are retained. The primary PNGs keep the GIF's original dimensions.

PACKED DATA
Every 5200 crop lies exactly on a repeated 4x2 source-pixel grid and uses at
most four colors including black. packed-5200/ contains a lossless two-bit
encoding of that grid, both row order and 4x8 tile order. Palettes are per-frame
RGB lists in sprite-manifest.json; black is index zero. These are extracted
asset bytes, not a rebuilt game cartridge or inferred GTIA color-register map.

Large-bird data is 24x16 grid samples; small-pose data is 8x16; ship data is
16x16; shield/explosion data is 16x32. To reproduce the supplied GIF dimensions,
repeat every grid sample four times horizontally and twice vertically. This
step exactly recovers the source pixels; it is not an interpolating resize.

Both binary layouts were decoded and checked against every original RGB pixel.
All extracted frames and atlas placements passed with zero differing pixels.

REPRODUCE
Requires Python 3 and Pillow:
python3 extract_sprites.py --large-gif sources/big-bird-32.gif --various-gif sources/various3.gif --out rebuilt

The displayed GIF delays are retained as metadata (large-bird: 100 ms/frame;
various: 200 ms/frame). Game animation cadence is a separate implementation choice.
''')
shutil.copyfile(Path(__file__),O/'extract_sprites.py')
print(json.dumps(manifest['verification'],indent=2))
