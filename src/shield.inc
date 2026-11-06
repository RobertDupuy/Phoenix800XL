# Shield control follows Amstar $08C4/$0AA0 and table $1770.
# CPU input/audio: video rate. Counter/collisions: logical arcade tick rate.
.set shield_count,0x37a
.set shield_locked,0x37b
.set shield_pose,0x37c
.set shield_edge,0x37d
.set shield_now,0x37e
.set shield_prev,0x37f
.set shield_pmg_pose,0x6f4
.set shield_old_col,0x6f5
.section .text,"ax",@progbits
.global shield_reset,shield_input,shield_update,shield_bomb_cell,shield_body_collision
.global clear_shield,draw_shield,shield_players
shield_reset:
 jsr shield_font_init
 lda #0
 sta shield_count
 sta shield_locked
 sta shield_edge
 lda #255
 sta shield_pose
 rts
shield_input:
 lda shield_now
 sta shield_prev
 lda 0xe80f
 and #8
 eor #8
 sta shield_now
 beq shield_input_done
 lda shield_prev
 bne shield_input_done
 lda #1
 sta shield_edge
shield_input_done:
 rts
.section .shield_code,"ax",@progbits
shield_update:
 ldx shield_edge
 lda #0
 sta shield_edge
 lda shield_locked
 bne shield_tick
 lda shield_count
 beq shield_try
 dec shield_count
 clc
 rts
shield_try:
 cpx #0
 beq shield_free
 lda #1
 sta shield_locked
 lda #254
 sta shield_count
 lda #64
 sta audio_shield_count
shield_free:
 clc
 rts
shield_tick:
 dec shield_count
 lda shield_count
 cmp #192
 beq shield_expire
 and #12
 lsr
 lsr
 sta shield_pose
 sec
 rts
shield_expire:
 lda #0
 sta shield_locked
 lda #255
 sta shield_pose
 lda raw_ship_x
 and #248
 ora #3
 sta raw_ship_x
 sec
 rts
# The arcade bomb checks its previous screen cell after moving four pixels.
# Only rim characters E8..FF absorb it; central/gap cells do not.
shield_bomb_cell:
 lda shield_pose
 cmp #255
 beq shield_bomb_done
 # Reject horizontal misses before decoding the shield row.
 lda raw_ship_x
 and #248
 sec
 sbc #8
 sta atmp
 lda raw_bomb_x,x
 sec
 sbc atmp
 cmp #32
 bcs shield_bomb_done
 and #248
 lsr
 sta atmp
 lda raw_bomb_y,x
 sec
 sbc #player_shield_bomb_y
 cmp #32
 bcs shield_bomb_done
 lsr
 lsr
 lsr
 ora atmp
 sta atmp2
 lda shield_pose
 asl
 asl
 asl
 asl
 ora atmp2
 tay
 lda shield_codes,y
 cmp #232
 bcc shield_bomb_done
 lda #0
 sta bomb_on,x
shield_bomb_done:
 rts
# Shield body window follows the raised ship; X is still [ship-14,ship+31).
# Character-map collision gating is deferred; this preserves the passing bounded object path.
shield_body_collision:
 lda raw_ship_x
 sec
 sbc #14
 sta axcmp
 clc
 adc #45
 sta aycmp
 ldx #0
shield_body_loop:
 lda enemy_on,x
 beq shield_body_next
 lda raw_enemy_y,x
 cmp #player_shield_body_min_y
 bcc shield_body_next
 cmp #player_shield_body_max_y
 bcs shield_body_next
 lda raw_enemy_x,x
 cmp axcmp
 bcc shield_body_next
 cmp aycmp
 bcs shield_body_next
 lda #2
 jsr kill_alien
 # Shield hits use the 13-count animation, but score 20 points.
 lda #13
 jmp set_hit_counter
shield_body_next:
 inx
 cpx #16
 bcc shield_body_loop
 rts
.section .text,"ax",@progbits
clear_shield:
 ldx back_buffer
 lda shield_old_col,x
 beq shield_clear_done
 sta draw_col
 lda #0
 sta shield_old_col,x
 lda #player_shield_row
 sta draw_row
 jsr row_pointer
 lda #0
 .irp off,0,1,2,3,32,33,34,35,64,65,66,67,96,97,98,99
 ldy #\off
 sta (map_ptr),y
 .endr
shield_clear_done:
 rts
draw_shield:
 lda large_mode
 beq 9f
 jmp large_draw_shield
9: lda state
 cmp #1
 beq 1f
 rts
1:
 lda shield_pose
 cmp #255
 bne 1f
 rts
1:
 lda #0
 sta src_mask
 lda back_buffer
 beq 1f
 lda #128
 sta src_mask
1:
 lda #0x3b
 sta src_mask+1
 lda raw_ship_x
 lsr
 lsr
 lsr
 clc
 adc #6
 sta draw_col
 ldx back_buffer
 sta shield_old_col,x
 lda #player_shield_row
 sta draw_row
 jsr row_pointer
 ldx shield_pose
 lda shield_map_offsets,x
 tax
 stx effect_cursor
 lda #0
 sta effect_cell
shield_draw_cell:
 ldx effect_cell
 ldy shield_cell_offsets,x
 ldx effect_cursor
 lda shield_maps,x
 pha
 lda large_mode
 bne 8f
 pla
 and #127
 jmp 9f
8: pla
9: sta (map_ptr),y
 and #127
 tay
 lda (src_mask),y
 bne 1f
 tya
 jsr shield_restore_glyph
1:
 inc effect_cursor
 inc effect_cell
 lda effect_cell
 cmp #16
 bcc shield_draw_cell
shield_draw_done:
 rts
# PM0/1 carry the green ring; PM2 carries the ship red inside it.
# Restore every ship byte and force its pose refresh when the shield ends.
shield_players:
 lda state
 cmp #1
 beq 1f
 jmp shield_restore
1:
 lda shield_pose
 cmp #255
 bne 1f
 jmp shield_restore
1:
 cmp shield_pmg_pose
 bne 1f
 jmp shield_player_position
1:
 pha
 lda shield_pmg_pose
 cmp #255
 bne 2f
 ldx #15
1: lda ship_red,x
 sta 0x1600+player_pm_y,x
 dex
 bpl 1b
2: pla
 sta shield_pmg_pose
 tax
 lda shield_green_offsets,x
 tax
 .irp row,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31
 lda shield_green+\row,x
 sta SHIP+player_shield_pm_y+\row
 lda shield_green+32+\row,x
 sta SHIP_RED+player_shield_pm_y+\row
 .endr
shield_player_position:
 lda shield_pose
 sta 0x337
 lda #0xc6
 sta 0xc012
 sta 0xc013
 lda raw_ship_x
 and #248
 lsr
 clc
 adc #72
 sta 0xc000
 sta 0x338
 clc
 adc #8
 sta 0xc001
 sec
 sbc #4
 sta 0xc002
 lda #0x46
 sta 0xc014
 lda #0
 sta ship_hpos
 sec
 rts
shield_restore:
 lda #255
 sta 0x337
 lda shield_pmg_pose
 cmp #255
 beq shield_players_done
 lda #255
 sta shield_pmg_pose
 sta ship_pose
 lda #0x0e
 sta 0xc012
 ldx #7
 lda #0
shield_clear_pm_top:
 sta SHIP+player_shield_pm_y,x
 sta SHIP_RED+player_shield_pm_y,x
 sta SHIP+player_pm_y+16,x
 sta SHIP_RED+player_pm_y+16,x
 dex
 bpl shield_clear_pm_top
 ldx #15
shield_restore_ship:
 lda ship_white,x
 sta SHIP+player_pm_y,x
 lda ship_red,x
 sta SHIP_RED+player_pm_y,x
 lda ship_yellow,x
 sta 0x1600+player_pm_y,x
 dex
 bpl shield_restore_ship
shield_players_done:
 clc
 rts
.section .effects,"a",@progbits
shield_map_offsets: .byte 0,16,32,48
shield_green_offsets: .byte 0,64,128,192
shield_cell_offsets: .byte 0,32,64,96,1,33,65,97,2,34,66,98,3,35,67,99
shield_unique: .incbin "build/shield-unique.bin"
shield_maps: .incbin "build/shield-maps.bin"
shield_green: .incbin "build/shield-green.bin"
shield_codes: .incbin "build/shield-codes.bin"

.section .shield_code,"ax",@progbits
.global shield_font_init,shield_restore_glyph
# Wave/reset occurs with no surviving large font allocation on the visible page.
shield_font_init:
 jsr invalidate_shield_cache
 lda font_hi
 pha
 lda src_mask
 pha
 lda src_mask+1
 pha
 lda #0x3b
 sta src_mask+1
 lda #0
 sta src_mask
 lda #0x20
 sta font_hi
shield_init_buffer:
 lda #1
 ldy #0
 sta (src_mask),y
 ldx #100
shield_init_glyph:
 txa
 tay
 lda (src_mask),y
 bne shield_init_next
 stx effect_cursor
 txa
 jsr shield_restore_glyph
 ldx effect_cursor
shield_init_next:
 inx
 cpx #128
 bcc shield_init_glyph
 lda src_mask
 bne shield_init_done
 lda #128
 sta src_mask
 lda #0x24
 sta font_hi
 bne shield_init_buffer
shield_init_done:
 pla
 sta src_mask+1
 pla
 sta src_mask
 pla
 sta font_hi
 rts
shield_restore_glyph:
 sta plot_tmp
 tay
 lda #1
 sta (src_mask),y
 lda plot_tmp
 jsr glyph_pointer
 lda plot_tmp
 sec
 sbc #100
 asl
 asl
 asl
 tax
 .irp row,0,1,2,3,4,5,6,7
 lda shield_unique+\row,x
 ldy #\row
 sta (dst_ptr),y
 .endr
 rts

.section .shield_code,"ax",@progbits
invalidate_shield_cache:
 ldx #100
invalidate_shield_next:
 # These bytes are also mothership cache metadata. A nonzero byte after
 # a stage change/restart does not prove that a shield glyph is resident.
 lda #0
 sta 0x3b00,x
 sta 0x3b80,x
 ldy 0x3800,x
 beq 1f
 lda #0
 sta 0x3000,y
 sta 0x3800,x
1:
 ldy 0x3900,x
 beq 2f
 lda #0
 sta 0x3200,y
 sta 0x3900,x
2:
 inx
 cpx #128
 bcc invalidate_shield_next
 rts
