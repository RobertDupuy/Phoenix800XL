# Called only by the small-bird movement engine, after the position step and
# before bounds/shape publication. axcmp/aycmp hold the previous raw Y/X.
# Only a previously fully clipped bird can be relocated, so no visible bird
# teleports or becomes invulnerable. Keep X's fine phase and the existing path.
.section .expanded_code,"ax",@progbits
.global safe_small_entry
safe_small_entry:
 lda raw_enemy_y,x
 cmp #232
 bcs safe_entry_done
 cmp #player_raw_y-24
 bcc safe_entry_done
 lda raw_enemy_x,x
 cmp #208
 bcs safe_entry_done
 lda axcmp
 cmp #232
 bcs safe_entry_distance
 lda aycmp
 cmp #208
 bcc safe_entry_done
safe_entry_distance:
 # Entry within 48 raw pixels of the current ship is too close. The chosen
 # lane leaves at least 64 pixels of separation, including fine X phase.
 lda raw_enemy_x,x
 sec
 sbc raw_ship_x
 clc
 adc #48
 cmp #96
 bcs safe_entry_done
 lda raw_ship_x
 cmp #104
 bcc safe_entry_right
 lda #24
 bne safe_entry_lane
safe_entry_right:
 lda #168
safe_entry_lane:
 sta atmp2
 lda raw_enemy_x,x
 and #7
 ora atmp2
 sta raw_enemy_x,x
 inc safe_entry_events
 bne safe_entry_done
 inc safe_entry_events+1
safe_entry_done:
 rts
