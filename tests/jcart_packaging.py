"""Check type 110, boot layout and lossless artwork repacking independently."""
from pathlib import Path
import hashlib,json,struct
R=Path(__file__).resolve().parents[1];B=R/'build';S=json.loads((B/'symbols.json').read_text())
car=(R/'Phoenix800XL-512K.car').read_bytes();rom=car[16:]
assert car[:4]==b'CART'
kind,checksum,reserved=struct.unpack('>III',car[4:16])
assert (kind,len(rom),checksum,reserved)==(110,512*1024,sum(rom)&0xffffffff,0)
def bank(n):return rom[n*8192:(n+1)*8192]
base=(B/'game-base.bin').read_bytes()
assert bank(1)+bank(2)+bank(3)==base[:0x6000]
assert bank(4)[:0x1fd0]==base[0x6000:0x7fd0]
assert bank(5)[:7168]==(B/'xl-background.bin').read_bytes()
assert bank(6)[:1264]==(B/'native-masks.bin').read_bytes()
assert S['native_tiles']+1264<=0xa000
poses=0
for start,f in [(13,'large-padded.bin'),(15,'large-padded2.bin')]:
 art=(B/f).read_bytes()
 for p in range(60):
  n=start+p//30;offset=p%30*256
  assert bank(n)[offset:offset+256]==art[p*256:(p+1)*256]
  poses+=1
halves=(B/'boss-halves.bin').read_bytes()
for half in range(2):
 for shape in range(64):
  offset=half*3072+(shape if shape<48 else 31)*64
  assert bank(9)[offset:offset+64]==halves[half*4096+shape*64:half*4096+(shape+1)*64]
for n in [0,4,7,8,9,10,11,12,13,14,15,16]:
 assert bank(n)[0x1fd0:]==(B/'cart_tail.bin').read_bytes(),n
assert bank(10)[:4104]==(B/'boss-atlases.bin').read_bytes()+(B/'boss-atlas-counts.bin').read_bytes()
assert bank(11)[:(B/'victory.bin').stat().st_size]==(B/'victory.bin').read_bytes()
assert bank(12)[:1920]==(B/'flight-masks.bin').read_bytes()
normal=(R/'Phoenix800XL.car').read_bytes()
assert hashlib.sha256(normal).hexdigest()=='902bbd1b8110c43eac3cef7ddf032f11d159e899051f0e2ee63133ee7e22ddf0'
report=dict(car_sha256=hashlib.sha256(car).hexdigest(),car_type=kind,rom_bytes=len(rom),file_bytes=len(car),checksum=checksum,large_poses_verified=poses,mothership_halves_verified=128,runtime_reset_stubs_verified=12,normal_car_unchanged=True,method=__doc__)
out=R/'evidence/xl/512k';out.mkdir(parents=True,exist_ok=True);(out/'packaging.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
