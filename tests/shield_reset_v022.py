"""Reused font/cache memory must not survive a shield reset.

The hostile glyph fixture represents fonts overwritten by another stage. It is
synthetic, separate from the controller-driven screenshots and pixel checks.
"""
from cpu_model import *
import hashlib
T=Model();T.init();m=T.m.b
maps=(R/'build/shield-maps.bin').read_bytes();glyphs=(R/'build/shield-unique.bin').read_bytes()
cases=0
for cache_byte in (1,127,255):
 # $3Bxx is initialized to FF by the mothership. All values are stale here.
 m[0x3b00:0x3c00]=bytes([cache_byte])*256
 for font in (0x2000,0x2400):m[font+800:font+1024]=bytes([255])*224
 T.call('shield_reset')
 for font in (0x2000,0x2400):
  assert m[font+800:font+1024]==glyphs
  cases+=28
report=dict(car_sha256=hashlib.sha256((R/'build/Phoenix-First-Flight.car').read_bytes()).hexdigest(),reset_glyph_checks=cases,stale_metadata_values=[1,127,255],buffers=2,method=__doc__)
(R/'evidence/v022/shield-reset.json').write_text(json.dumps(report,indent=2));print(report)
