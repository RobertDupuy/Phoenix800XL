from pathlib import Path
R=Path(__file__).resolve().parents[1];B=R/"build";A=R/"src/arcade-assets"
def prepare():
 # Three original arcade HUD rows, 26 columns at six low-resolution pixels/char.
 glyphs=(A/'hud-glyphs.bin').read_bytes()
 labels=[0,19,3,15,18,5,33,0,0,8,9,43,19,3,15,18,5,0,0,19,3,15,18,5,34,0]
 digits=[0]+[32]*6+[0]*3+[32]*6+[0]*3+[32]*6+[0]
 icons=[0,0,0,127,35,0,0,0,0,0,3,15,9,14,32,32,0,0,0,0,0,127,32,0,0,0]
 font=bytearray(1024)
 def put(code,row,col):
  phase=(col*6+2)%4;cell=(col*6+2)//4
  src=glyphs[code*32+phase//2*16:code*32+phase//2*16+16]
  for i,v in enumerate(src):font[(row*40+cell)*8+i]|=v
 for row,codes in enumerate([labels,digits,icons]):
  for col,code in enumerate(codes):put(code,row,col)
 (B/'hud-initial.bin').write_bytes(font)
 # Score update records precomposed per decimal pair: aligned to three cells.
 pairsfont=bytearray()
 for p in range(100):
  # original 6px glyph with phase 0, then phase 2; final cell overlap is OR.
  out=bytearray(24)
  for k,code in enumerate([32+p//10,32+p%10]):
   src=glyphs[code*32+k*16:code*32+k*16+16]
   for j,v in enumerate(src):out[k*8+j]|=v
  pairsfont+=out
 (B/'hud-pairs.bin').write_bytes(pairsfont)
 (B/'hud-lives.bin').write_bytes(b''.join(glyphs[(32+i)*32+16:(32+i)*32+32] for i in range(10)))
 # A game-over message replaces only the center of the bottom HUD row.
 original=bytes(font[744:856]);font[744:856]=bytes(112)
 text='GAME OVER'
 for i,c in enumerate(text):
  code=0 if c==' ' else ord(c)-64;x=52+i*6;phase=x%4;cell=x//4
  src=glyphs[code*32+phase//2*16:code*32+phase//2*16+16]
  for j,v in enumerate(src):font[640+cell*8+j]|=v
 (B/'hud-gameover.bin').write_bytes(font[744:856]);(B/'hud-credit.bin').write_bytes(original)
