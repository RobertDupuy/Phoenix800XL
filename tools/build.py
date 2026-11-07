"""Assemble the Atari XL program and package its MegaCart cartridge image."""
from pathlib import Path
import argparse, os, subprocess, struct, json, re, hashlib, shutil
from prepare_large import prepare as prepare_large
from prepare_flight_art import prepare as prepare_flight_art
from prepare_hud import prepare as prepare_hud
from prepare_native import prepare as prepare_native
from prepare_campaign import prepare as prepare_campaign
from prepare_intro import prepare as prepare_intro
from prepare_art import prepare
from prepare_formation import prepare as prepare_formation
from prepare_victory import prepare as prepare_victory
from prepare_xl import prepare as prepare_xl
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--cart-size',type=int,choices=(256,512),default=256,
                    help='MegaCart ROM capacity in KiB (default: 256)')
args=parser.parse_args()
cart_type={256:30,512:31}[args.cart_size]
cart_name='Phoenix800XL' if args.cart_size==256 else 'Phoenix800XL-512K'
R=Path(__file__).resolve().parents[1]
B=R/'build'; B.mkdir(exist_ok=True)
MOS=Path(os.environ['LLVM_MOS'])/'bin' if os.environ.get('LLVM_MOS') else Path(shutil.which('mos-common-clang') or '/missing/mos-common-clang').parent
if not (MOS/'mos-common-clang').is_file():raise SystemExit('Set LLVM_MOS to your LLVM-MOS SDK directory.')
prepare()
prepare_formation()
prepare_hud()
prepare_native()
native=(B/'native-tiles.bin').read_bytes()
(B/'native-masks.bin').write_bytes(bytes((~sum(3 << shift for shift in (0,2,4,6) if (v >> shift) & 3)) & 255 for v in native))
prepare_large()
prepare_flight_art()
prepare_campaign()
prepare_xl()
prepare_intro()
prepare_victory()
(B/'intro-size.inc').write_text(".set intro_fonts_end,"+str(0xa400+len((B/'intro-fonts-packed.bin').read_bytes()))+"\n")
screen=bytearray(b' '*960)
screen[10:16]=b'SCORE1'
screen[50:55]=b'00000'
screen[62]=127;screen[63]=ord('3')
(B/'screen.bin').write_bytes(screen)
(B/'tens.bin').write_bytes(bytes(48+i//10 for i in range(100)))
(B/'units.bin').write_bytes(bytes(48+i%10 for i in range(100)))
header='      PHOENIX       '+'80'
assert len(header)==22
(B/'header.bin').write_bytes(bytes((ord(c)-32)|0x40 for c in header))
subprocess.run([str(MOS/'mos-common-clang'),'-c','src/game.S','-o','build/game.o'],cwd=R,check=True)
subprocess.run([str(MOS/'ld.lld'),'-T','src/cart.ld','build/game.o','-o','build/game.elf','-Map=build/game.map'],cwd=R,check=True)
subprocess.run([str(MOS/'llvm-objcopy'),'-O','binary','--remove-section=.platform','build/game.elf','build/game-base.bin'],cwd=R,check=True)
rom=(B/'game-base.bin').read_bytes()
assert len(rom)==32768,len(rom)
# Check the final binary against every allocated ELF data/code section. This
# catches unexpected load-segment gap padding from toolchain/linker changes.
elf=(B/'game.elf').read_bytes()
shoff=struct.unpack_from('<I',elf,32)[0]
shsize,shnum=struct.unpack_from('<HH',elf,46)
for i in range(shnum):
 name,typ,flags,addr,off,size,*_=struct.unpack_from('<10I',elf,shoff+i*shsize)
 if typ==1 and flags&2 and size and addr<0xc000:
  assert 0x4000<=addr and addr+size<=0xc000
  assert rom[addr-0x4000:addr-0x4000+size]==elf[off:off+size],hex(addr)
nm=subprocess.check_output([str(MOS/'llvm-nm'),'build/game.elf'],cwd=R,text=True)
symbols={m[3]:int(m[1],16) for line in nm.splitlines() if (m:=re.match(r'^([0-9A-Fa-f]+)\s+(\w)\s+(.+)$',line))}
(B/'main-symbols.inc').write_text('\n'.join('.set '+k+','+str(v) for k,v in symbols.items() if (k in ('boss_copy_tile','boss_load_atlas','boss_cache_select') or not k.startswith(('boss_','cycle_','wipe_','campaign_'))) and re.match(r'^\w+$',k))+'\n')
subprocess.run([str(MOS/'mos-common-clang'),'-c','src/campaign.S','-o','build/campaign.o'],cwd=R,check=True)
subprocess.run([str(MOS/'ld.lld'),'-T','src/campaign.ld','build/campaign.o','-o','build/campaign.elf','-Map=build/campaign.map'],cwd=R,check=True)
subprocess.run([str(MOS/'llvm-objcopy'),'-O','binary','build/campaign.elf','build/campaign.bin'],cwd=R,check=True)
cnm=subprocess.check_output([str(MOS/'llvm-nm'),'build/campaign.elf'],cwd=R,text=True)
cs={m[3]:int(m[1],16) for line in cnm.splitlines() if (m:=re.match(r'^([0-9A-Fa-f]+)\s+(\w)\s+(.+)$',line))}
assert cs['boss_code_end']<=0xa000,hex(cs['boss_code_end'])
assert cs['boss_data_end']<=0xbfc0,hex(cs['boss_data_end'])
(B/'campaign-symbols.json').write_text(json.dumps(cs,indent=2))
subprocess.run([str(MOS/'mos-common-clang'),'-c','src/victory.S','-o','build/victory.o'],cwd=R,check=True)
subprocess.run([str(MOS/'ld.lld'),'-T','src/victory.ld','build/victory.o','-o','build/victory.elf'],cwd=R,check=True)
subprocess.run([str(MOS/'llvm-objcopy'),'-O','binary','build/victory.elf','build/victory.bin'],cwd=R,check=True)
# Every bank keeps the lower 16 KiB and vectors identical.
base=rom
banks=[bytearray(base) for _ in range(8)]
victory=(B/'victory.bin').read_bytes()
assert len(victory)<=0x3fc0,len(victory)
banks[6][0x4000:0x4000+len(victory)]=victory
banks[4][0x4000:0x5000]=(B/'boss-atlases.bin').read_bytes()
banks[4][0x5000:0x5008]=(B/'boss-atlas-counts.bin').read_bytes()
overlay=(B/'campaign.bin').read_bytes()
banks[1][0x4000:0x4000+len(overlay)]=overlay
banks[3][0x4000:0x6000]=(B/'boss-halves.bin').read_bytes()
banks[3][0x6000:0x6400]=(B/'hud-initial.bin').read_bytes()
masks=(B/'flight-masks.bin').read_bytes()
banks[1][0x6000:0x6000+len(masks)]=masks
padded=(B/'large-padded.bin').read_bytes()
banks[2][0x4000:0x7fc0]=padded+bytes(0x3fc0-len(padded))
padded2=(B/'large-padded2.bin').read_bytes()
banks[5][0x4000:0x7fc0]=padded2+bytes(0x3fc0-len(padded2))
packed=(B/'intro-fonts-packed.bin').read_bytes();maps=(B/'intro-maps.bin').read_bytes()
banks[3][0x6400:0x6400+len(packed)]=packed
banks[3][0x7800:0x7800+len(maps)]=maps
# Convert the banked 5200 layout into ten 16 KiB MegaCart banks, then pad
# to the requested capacity. The larger cartridge keeps identical game banks.
# Bank 0: boot/platform. Bank 1: resident code copied into $4000-$7FFF.
# Banks 2..9: the eight original upper windows, now selected through $D500.
subprocess.run([str(MOS/'llvm-objcopy'),'-O','binary','--only-section=.platform','build/game.elf','build/platform.bin'],cwd=R,check=True)
platform=(B/'platform.bin').read_bytes()
assert len(platform)<=4096
subprocess.run([str(MOS/'mos-common-clang'),'-c','src/boot-xl.S','-o','build/boot-xl.o'],cwd=R,check=True)
subprocess.run([str(MOS/'ld.lld'),'-T','src/boot-xl.ld','build/boot-xl.o','-o','build/boot-xl.elf','-Map=build/boot-xl.map'],cwd=R,check=True)
boot=bytearray([255])*4096
for section,offset,capacity in [('boot',0,256),('loader',256,256),('cart_tail',0xfd0,48)]:
 subprocess.run([str(MOS/'llvm-objcopy'),'-O','binary','--only-section=.'+section,'build/boot-xl.elf','build/'+section+'.bin'],cwd=R,check=True)
 data=(B/(section+'.bin')).read_bytes()
 assert len(data)<=capacity,(section,len(data))
 boot[offset:offset+len(data)]=data
(B/'boot-xl.bin').write_bytes(boot)
xlbanks=[bytearray([255])*16384 for _ in range(args.cart_size//16)]
background=(B/'xl-background.bin').read_bytes()
assert len(background)==7168
xlbanks[0][:len(background)]=background
xlbanks[0][0x2000:0x2000+len(platform)]=platform
xlbanks[0][0x3000:]=boot
xlbanks[1][:]=base[:0x4000]
for n,bank in enumerate(banks):
 xlbanks[n+2][:]=bank[0x4000:]
 xlbanks[n+2][0x3fd0:]=boot[0xfd0:]
rom=b''.join(xlbanks)
(B/(cart_name+'.rom')).write_bytes(rom)
car=b'CART'+struct.pack('>III',cart_type,sum(rom)&0xffffffff,0)+rom
(B/(cart_name+'.car')).write_bytes(car)
(R/(cart_name+'.car')).write_bytes(car)
nm=subprocess.check_output([str(MOS/'llvm-nm'),'build/game.elf'],cwd=R,text=True)
symbols={m[3]:int(m[1],16) for line in nm.splitlines() if (m:=re.match(r'^([0-9A-Fa-f]+)\s+(\w)\s+(.+)$',line))}
assert symbols['large_collision']<0xa400
assert symbols['fixed_end']<=0x8000,hex(symbols['fixed_end'])
assert symbols['expanded_end']<=0xbfc0,hex(symbols['expanded_end'])
assert symbols['alien_movement_cluster_a']%256==symbols['alien_movement_cluster_b']%256==0
for page in range(48):
 expected=(symbols['alien_movement_cluster_a']//256+page-16) if page<32 else (symbols['alien_movement_cluster_b']//256+page-44)
 assert base[symbols['pattern_pages']-0x4000+page]==expected
(B/'symbols.json').write_text(json.dumps(symbols,indent=2))
assert rom[0x3ffa:0x4000]==bytes([0xd0,0xbf,0,4,0xf9,0xbf])
assert len(rom)==args.cart_size*1024
assert symbols['platform_end']<=0xd000
print(json.dumps({'payload_bytes':len(rom),'car_type':cart_type,'file':cart_name+'.car','entry':hex(symbols['entry']),'sha256':hashlib.sha256(car).hexdigest()},indent=2))
