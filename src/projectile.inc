# One white bomb replaces M1, whose GTIA color is shared with the red ship.
# At most two copied glyphs per shot. While shielding, the player shot also
# uses this routine, retaining white despite the green PM0 shield layer.
.set soft_row,0xfc
.set soft_mask,0xfd
.set soft_bits,0xfe
.set soft_lines,0xff
.section .text,"ax",@progbits
.global clear_soft_bomb,draw_soft_bomb,soft_bomb_glyph
clear_soft_bomb:
 jsr clear_second_shot
 jsr clear_soft_shot
 ldx back_buffer
 lda 0x6f2,x
 cmp #127
 beq soft_clear_done
 sta draw_row
 lda 0x6f0,x
 sta draw_col
 lda #127
 sta 0x6f2,x
 jsr row_pointer
 lda #0
 ldy #0
 sta (map_ptr),y
 lda draw_row
 cmp #24
 bcs soft_clear_done
 lda #0
 ldy #32
 sta (map_ptr),y
soft_clear_done:
 rts
draw_soft_bomb:
 jsr projectiles_visible
 bcc soft_clear_done
 lda bomb_on
 beq soft_clear_done
 lda bomb_x
 sta 0x6fd
 lda #0
 sta 0x6fe
 lda bomb_y
 cmp #40
 bcc soft_clear_done
 cmp #238
 bcs soft_clear_done
soft_common:
 sec
 sbc #40
 pha
 and #7
 sta soft_row
 pla
 lsr
 lsr
 lsr
 sta draw_row
 lda 0x6fd
 sec
 sbc #48
 pha
 and #3
 tax
 lda soft_masks,x
 sta soft_mask
 lda soft_pixels,x
 sta soft_bits
 pla
 lsr
 lsr
 sta draw_col
 ldx back_buffer
 pha
 txa
 clc
 adc 0x6fe
 tax
 pla
 sta 0x6f0,x
 lda draw_row
 sta 0x6f2,x
 jsr row_pointer
 lda #3
 sta soft_lines
 jsr soft_bomb_glyph
soft_bomb_pixel:
 ldy soft_row
 lda (dst_ptr),y
 and soft_mask
 ora soft_bits
 sta (dst_ptr),y
 dec soft_lines
 beq soft_bomb_done
 inc soft_row
 lda soft_row
 cmp #8
 bcc soft_bomb_pixel
 lda #0
 sta soft_row
 clc
 lda map_ptr
 adc #32
 sta map_ptr
 bcc 1f
 inc map_ptr+1
1:
 inc draw_row
 jsr soft_bomb_glyph
 jmp soft_bomb_pixel
soft_bomb_done:
 rts
soft_bomb_glyph:
 lda large_mode
 beq 9f
 jmp large_soft_glyph
9: ldy #0
 lda (map_ptr),y
 pha
 and #127
 jsr glyph_pointer
 lda dst_ptr
 sta cow_ptr
 lda dst_ptr+1
 sta cow_ptr+1
 jsr large_soft_source
 pla
 and #128
 sta draw_palette
 lda #0
 sta tile_offset
 jsr allocate_glyph
 .irp row,0,1,2,3,4,5,6,7
 ldy #\row
 lda (cow_ptr),y
 sta (dst_ptr),y
 .endr
 rts
.section .tables,"a",@progbits
soft_masks: .byte 0x3f,0xcf,0xf3,0xfc
soft_pixels: .byte 0x40,0x10,0x04,0x01

.section .text,"ax",@progbits
.global clear_soft_shot,draw_soft_shot
clear_soft_shot:
 ldx back_buffer
 lda 0x6fa,x
 cmp #127
 beq soft_shot_clear_done
 sta draw_row
 lda 0x6f8,x
 sta draw_col
 lda #127
 sta 0x6fa,x
 jsr row_pointer
 lda #0
 ldy #0
 sta (map_ptr),y
 lda draw_row
 cmp #24
 bcs soft_shot_clear_done
 lda #0
 ldy #32
 sta (map_ptr),y
soft_shot_clear_done:
 rts
draw_soft_shot:
 jsr projectiles_visible
 bcc soft_shot_clear_done
 lda shield_pose
 cmp #255
 beq soft_shot_clear_done
 lda shot_on
 beq soft_shot_clear_done
 lda shot_x
 sta 0x6fd
 lda #8
 sta 0x6fe
 lda shot_y
 cmp #40
 bcc soft_shot_clear_done
 cmp #238
 bcs soft_shot_clear_done
 jmp soft_common

.global projectiles_visible
projectiles_visible:
 lda state
 cmp #1
 beq projectile_is_visible
 cmp #3
 bne projectile_is_hidden
 lda death_timer
 cmp #33
 rts
projectile_is_visible:
 sec
 rts
projectile_is_hidden:
 clc
 rts
