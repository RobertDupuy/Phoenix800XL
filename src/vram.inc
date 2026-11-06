# Original foreground character codes, independent of the authored 5200 art.
# This bounded 1 KiB map preserves arcade erase/draw order for collision gates.
.set collision_vram,0x1800
.set vr_old_lo,0x1c00
.set vr_old_hi,0x1c20
.set vr_old_kind,0x1c40       // 0 absent; otherwise original kind plus one
.set bomb_shape,0x1c60
.set screen_enemy_x,0x38c0
.set screen_enemy_y,0x38d0
.set vr_on,0x790
.set vr_kind,0x791
.set vr_shape,0x792
.set vr_x,0x793
.set vr_y,0x794
.set vr_slot,0x795
.set vr_next_kind,0x796
.set vr_next_shape,0x797
.set vr_zero,0x798
.set vr_bomb,0x799
.set vr_width,0x79a
.set vr_height,0x79b
.set vr_scan_row,0x79c
.set vr_saved_x,0x79d
.set vr_effect_slot,0x79e
.section .expanded_code,"ax",@progbits
.global vram_clear,vram_pointer,vram_read,vram_aliens,vram_players,vram_bombs,vram_body_gate
vram_clear:
 lda #0
 ldx #0
1:
 sta 0x1800,x
 sta 0x1900,x
 sta 0x1a00,x
 sta 0x1b00,x
 sta 0x1c00,x
 inx
 bne 1b
 ldx #4
 lda #0x58
1:
 sta bomb_shape,x
 dex
 bpl 1b
 rts
# A/Y = arcade pixel X/Y; returns C set outside original foreground RAM.
vram_pointer:
 stx vr_saved_x
 lsr
 lsr
 lsr
 tax
 lda vram_hi,x
 sta aptr+1
 tya
 lsr
 lsr
 lsr
 ora vram_lo,x
 sta aptr
 ldx vr_saved_x
 lda aptr+1
 cmp #0x18
 bcc vram_invalid
 cmp #0x1c
 rts
vram_invalid:
 sec
 rts
vram_read:
 jsr vram_pointer
 bcs vram_read_zero
 ldy #0
 lda (aptr),y
 rts
vram_read_zero:
 lda #0
 rts

vram_object:
 stx vr_slot
 lda vr_kind
 sta vr_next_kind
 lda vr_shape
 sta vr_next_shape
 lda vr_old_kind,x
 beq vram_object_new
 sec
 sbc #1
 sta vr_kind
 lda vr_old_lo,x
 sta aptr
 lda vr_old_hi,x
 sta aptr+1
 lda #1
 sta vr_zero
 jsr vram_plot
vram_object_new:
 ldx vr_slot
 lda #0
 sta vr_old_kind,x
 sta vr_zero
 lda vr_on
 beq vram_object_done
 lda vr_x
 ldy vr_y
 jsr vram_pointer
 lda aptr
 sta vr_old_lo,x
 lda aptr+1
 sta vr_old_hi,x
 lda vr_next_kind
 sta vr_kind
 clc
 adc #1
 sta vr_old_kind,x
 lda vr_next_shape
 sta vr_shape
 jsr vram_plot
vram_object_done:
 ldx vr_slot
 rts
# Two bounds checks per object, with unrolled one/two-row columns.
# Erasing never reads ROM; drawing indexes the immutable source block once.
vram_plot:
 lda aptr+1
 cmp #0x18
 bcs 9f
 jmp vram_plot_slow
9:
 cmp #0x1c
 bcc 9f
 jmp vram_plot_slow
9:
 lda aptr
 and #31
 cmp #31
 bne 9f
 jmp vram_plot_slow
9:
 lda aptr
 sec
 sbc #32
 sta aptr
 lda aptr+1
 sbc #0
 sta aptr+1
 cmp #0x18
 bcc vram_fast_revert
 lda vr_zero
 bne vram_zero_fast
 ldy #32
 lda vr_kind
 beq vram_code_fast
 ldx vr_shape
 lda sprite_character_block_shapes,x
 sta (aptr),y
 inx
 lda vr_kind
 cmp #3
 bcc 1f
 iny
 lda sprite_character_block_shapes,x
 sta (aptr),y
 inx
1:
 lda vr_kind
 cmp #1
 beq 2f
 cmp #4
 bne vram_fast_return
2:
 ldy #0
 lda sprite_character_block_shapes,x
 sta (aptr),y
 lda vr_kind
 cmp #4
 bne vram_fast_return
 inx
 iny
 lda sprite_character_block_shapes,x
 sta (aptr),y
vram_fast_return:
 rts
vram_code_fast:
 lda vr_shape
 sta (aptr),y
 rts
vram_zero_fast:
 lda #0
 ldy #32
 sta (aptr),y
 ldx vr_kind
 cpx #3
 bcc 1f
 iny
 sta (aptr),y
1:
 cpx #1
 beq 2f
 cpx #4
 bne vram_fast_return
2:
 ldy #0
 sta (aptr),y
 cpx #4
 bne vram_fast_return
 iny
 sta (aptr),y
 rts
vram_fast_revert:
 lda aptr
 clc
 adc #32
 sta aptr
 bcc vram_plot_slow
 inc aptr+1
vram_plot_slow:
 lda vr_zero
 bne vram_erase_fast
 lda vr_kind
 beq vram_single_fast
 ldx vr_shape
 jsr vram_draw_column
 lda vr_kind
 cmp #1
 beq vram_draw_right
 cmp #4
 bne vram_fast_done
vram_draw_right:
 jsr vram_right
 jsr vram_draw_column
vram_fast_done:
 rts
vram_draw_column:
 lda aptr+1
 cmp #0x18
 bcc vram_skip_column
 cmp #0x1c
 bcs vram_skip_column
 ldy #0
 lda sprite_character_block_shapes,x
 sta (aptr),y
 inx
 lda vr_kind
 cmp #3
 bcc vram_fast_done
 inc aptr
 lda sprite_character_block_shapes,x
 sta (aptr),y
 dec aptr
 inx
 rts
vram_skip_column:
 inx
 lda vr_kind
 cmp #3
 bcc vram_fast_done
 inx
 rts
vram_single_fast:
 lda aptr+1
 cmp #0x18
 bcc vram_fast_done
 cmp #0x1c
 bcs vram_fast_done
 ldy #0
 lda vr_shape
 sta (aptr),y
 rts
vram_erase_fast:
 jsr vram_erase_column_fast
 lda vr_kind
 cmp #1
 beq vram_erase_right
 cmp #4
 bne vram_fast_done
vram_erase_right:
 jsr vram_right
vram_erase_column_fast:
 lda aptr+1
 cmp #0x18
 bcc vram_fast_done
 cmp #0x1c
 bcs vram_fast_done
 lda #0
 ldy #0
 sta (aptr),y
 lda vr_kind
 cmp #3
 bcc vram_fast_done
 inc aptr
 lda #0
 sta (aptr),y
 dec aptr
 rts
vram_right:
 lda aptr
 sec
 sbc #32
 sta aptr
 bcs 1f
 dec aptr+1
1:
 rts
vram_aliens:
 ldx #0
vram_alien_loop:
 lda enemy_on,x
 sta vr_on
 lda enemy_kind,x
 sta vr_kind
 lda enemy_shape,x
 sta vr_shape
 lda raw_enemy_x,x
 sta vr_x
 lda raw_enemy_y,x
 sta vr_y
 jsr vram_object
 inx
 cpx #16
 bcc vram_alien_loop
 rts
vram_players:
 lda #1
 sta vr_on
 lda #4
 sta vr_kind
 lda raw_ship_x
 sta vr_x
 and #7
 tay
 lda alien_shape_offset_page,y
 sta vr_shape
 lda #player_raw_y
 sta vr_y
 ldx #16
 jsr vram_object
 lda shot_on
 sta vr_on
 lda #0
 sta vr_kind
 lda raw_shot_x
 sta vr_x
 and #7
 tay
 lda alien_shape_offset_page+32,y
 sta vr_shape
 lda raw_shot_y
 sta vr_y
 ldx #17
 jsr vram_object
 lda second_on
 sta vr_on
 lda #0
 sta vr_kind
 lda second_raw_x
 sta vr_x
 and #7
 tay
 lda alien_shape_offset_page+32,y
 sta vr_shape
 lda second_raw_y
 sta vr_y
 ldx #18
 jmp vram_object
vram_bombs:
 lda #0
 sta vr_bomb
vram_bomb_loop:
 ldx vr_bomb
 lda bomb_on,x
 sta vr_on
 lda #0
 sta vr_kind
 lda bomb_shape,x
 sta vr_shape
 lda raw_bomb_x,x
 sta vr_x
 lda raw_bomb_y,x
 sta vr_y
 txa
 clc
 adc #19
 tax
 jsr vram_object
 inc vr_bomb
 lda vr_bomb
 cmp #5
 bcc vram_bomb_loop
 rts

# Original 2x2 ship or 4x4 shield character gate, before object window tests.
# Returns C set only if a character $60..$BF is present.
vram_body_gate:
 lda #2
 sta vr_width
 sta vr_height
 lda raw_ship_x
 ldy #player_raw_y
 ldx shield_count
 cpx #192
 bcc 1f
 clc
 adc #8
 ldy #player_shield_raw_y
 ldx #4
 stx vr_width
 stx vr_height
1:
 jsr vram_pointer
vram_gate_column:
 ldy #0
vram_gate_row:
 lda aptr+1
 cmp #0x18
 bcc vram_gate_next
 cmp #0x1c
 bcs vram_gate_next
 lda (aptr),y
 cmp #96
 bcc vram_gate_next
 cmp #192
 bcc vram_gate_hit
vram_gate_next:
 iny
 cpy vr_height
 bcc vram_gate_row
 jsr vram_right
 dec vr_width
 bne vram_gate_column
 clc
 rts
vram_gate_hit:
 sec
 rts
.section .effects,"a",@progbits
vram_lo:
 .set vx,0
 .rept 32
 .byte ((0x1b20-vx*32)&255)
 .set vx,vx+1
 .endr

.section .expanded_code,"ax",@progbits
.global refresh_alien_screen,vram_effects
refresh_alien_screen:
 ldx #15
1:
 lda raw_enemy_x,x
 and #248
 sta screen_enemy_x,x
 lda raw_enemy_y,x
 and #248
 sta screen_enemy_y,x
 dex
 bpl 1b
 rts
vram_effect_pointer:
 ldx draw_col
 cpx #40
 bcs 1f
 lda effect_vram_hi,x
 sta aptr+1
 lda draw_row
 clc
 adc #4
 ora effect_vram_lo,x
 sta aptr
 rts
1:
 lda #0
 sta aptr+1
 rts
vram_erase_rect:
 jsr vram_effect_pointer
vram_erase_column:
 ldy #0
vram_erase_row:
 lda aptr
 clc
 adc vr_height
 lda aptr+1
 adc #0
 cmp #0x1c
 bcs vram_erase_skip
 lda aptr+1
 cmp #0x18
 bcc vram_erase_skip
 lda #0
 sta (aptr),y
vram_erase_skip:
 iny
 cpy vr_height
 bcc vram_erase_row
 jsr vram_right
 dec vr_width
 bne vram_erase_column
 rts
vram_effects:
 lda #0
 sta vr_effect_slot
vram_effect_normal:
 ldx vr_effect_slot
 lda burst_pose,x
 cmp #255
 beq vram_effect_normal_next
 lda burst_x,x
 sta draw_col
 lda burst_y,x
 sta draw_row
 lda #4
 sta vr_width
 lda #2
 sta vr_height
 jsr vram_erase_rect
 ldx vr_effect_slot
 lda burst_count,x
 bne vram_effect_normal_next
 lda #255
 sta burst_pose,x
vram_effect_normal_next:
 inc vr_effect_slot
 lda vr_effect_slot
 cmp #2
 bcc vram_effect_normal
 lda #0
 sta vr_effect_slot
vram_effect_bonus:
 ldx vr_effect_slot
 lda bonus_count,x
 beq vram_effect_bonus_end
 and #1
 bne vram_effect_bonus_wings
 lda bonus_x,x
 sec
 sbc #1
 sta draw_col
 lda bonus_y,x
 sta draw_row
 lda #3
 sta vr_width
 lda #1
 sta vr_height
 jsr vram_erase_rect
 jmp vram_effect_bonus_next
vram_effect_bonus_wings:
 lda #15
 sec
 sbc bonus_count,x
 and #14
 lsr
 sta bonus_distance
 lda bonus_x,x
 sec
 sbc #3
 sec
 sbc bonus_distance
 sta draw_col
 lda bonus_y,x
 sta draw_row
 lda #4
 sta vr_width
 lda #2
 sta vr_height
 jsr vram_erase_rect
 ldx vr_effect_slot
 lda bonus_x,x
 clc
 adc bonus_distance
 sta draw_col
 lda #5
 sta vr_width
 jsr vram_erase_rect
 jmp vram_effect_bonus_next
vram_effect_bonus_end:
 lda bonus_digits,x
 beq vram_effect_bonus_next
 lda #0
 sta bonus_digits,x
 lda bonus_y,x
 sta draw_row
 lda #7
 sta draw_col
 lda #26
 sta vr_width
 lda #2
 sta vr_height
 jsr vram_erase_rect
vram_effect_bonus_next:
 inc vr_effect_slot
 lda vr_effect_slot
 cmp #2
 bcs 1f
 jmp vram_effect_bonus
1:
 rts
.section .effects,"a",@progbits
effect_vram_lo:
 .set vx,0
 .rept 40
 .byte ((0x1b20-(vx-7)*32)&255)
 .set vx,vx+1
 .endr
effect_vram_hi:
 .set vx,0
 .rept 40
 .byte ((0x1b20-(vx-7)*32)>>8)
 .set vx,vx+1
 .endr

.section .expanded_code,"ax",@progbits
.global vram_shield,vram_shield_clear
vram_shield_clear:
 lda #1
 sta vr_zero
 bne vram_shield_rect
vram_shield:
 lda #0
 sta vr_zero
vram_shield_rect:
 lda raw_ship_x
 sec
 sbc #8
 ldy #player_shield_raw_y
 jsr vram_pointer
 lda shield_pose
 and #3
 asl
 asl
 asl
 asl
 tax
 lda #4
 sta vr_width
vram_shield_col:
 ldy #0
vram_shield_row:
 lda vr_zero
 bne 2f
 lda shield_codes,x
 jmp 1f
2:
 lda #0
1:
 sta (aptr),y
 inx
 iny
 cpy #4
 bcc vram_shield_row
 jsr vram_right
 dec vr_width
 bne vram_shield_col
 rts
vram_hi:
 .set vx,0
 .rept 32
 .byte ((0x1b20-vx*32)>>8)
 .set vx,vx+1
 .endr
