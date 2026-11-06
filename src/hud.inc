# Original arcade 26-column, three-row HUD. Only changed digits are patched.
.set hud_dirty,0xa2
.set high_dirty,0xa3
.set life_dirty,0xa4
.set high_digits,0xc6
.set hud_src,0xb0
.set hud_dst,0xb2
.set hud_mask,0xb4
.set hud_index,0xb5
.set hud_bit,0xad
.set hud_clear,0xae
.set banner_states,0x330
.section .text,"ax",@progbits
.global hud_init,hud_digit,high_score_update
hud_init:
 lda 0xbfdc
 ldx #0
hud_init_loop:
 .irp p,0,256,512,768
 lda hud_initial+\p,x
 sta 0x0c00+\p,x
 sta 0x0800+\p,x
 .endr
 inx
 bne hud_init_loop
 lda 0xbfd0
 rts
high_score_update:
 ldx #0
high_compare:
 lda score_digits,x
 cmp high_digits,x
 bcc high_done
 bne high_copy
 inx
 cpx #6
 bcc high_compare
high_done:
 rts
high_copy:
 ldx #5
high_copy_loop:
 lda score_digits,x
 sta high_digits,x
 dex
 bpl high_copy_loop
 lda #3
 sta high_dirty
 rts
render_hud:
 ldx back_buffer
 lda hud_bits,x
 sta hud_bit
 eor #255
 sta hud_clear
 lda hud_dirty
 and hud_bit
 beq hud_high
 ldx #5
hud_score_loop:
 stx hud_index
 txa
 ldy back_buffer
 beq score_shadow_index
 clc
 adc #6
score_shadow_index:
 tay
 lda state
 cmp #4
 bne hud_normal_score
 lda respawn_timer
 and #8
 beq hud_normal_score
 lda #10
 bne hud_score_value
hud_normal_score:
 lda score_digits,x
hud_score_value:
 cmp 0x340,y
 beq score_shadow_same
 sta 0x340,y
 ldy hud_score_cols,x
 jsr hud_digit
score_shadow_same:
 ldx hud_index
 dex
 bpl hud_score_loop
 lda hud_dirty
 and hud_clear
 sta hud_dirty
hud_high:
 lda high_dirty
 and hud_bit
 beq hud_life
 ldx #5
hud_high_loop:
 stx hud_index
 txa
 ldy back_buffer
 beq high_shadow_index
 clc
 adc #6
high_shadow_index:
 tay
 lda high_digits,x
 cmp 0x34c,y
 beq high_shadow_same
 sta 0x34c,y
 ldy hud_high_cols,x
 jsr hud_digit
high_shadow_same:
 ldx hud_index
 dex
 bpl hud_high_loop
 lda high_dirty
 and hud_clear
 sta high_dirty
hud_life:
 lda life_dirty
 and hud_bit
 beq hud_return
 lda lives
 cmp #10
 bcc hud_life_valid
 lda #9
hud_life_valid:
 ldy #16                        // row 2 col 4
 jsr hud_digit
 lda life_dirty
 and hud_clear
 sta life_dirty
hud_return:
 rts
# A: decimal digit 0..9, Y: one of 17 fixed destinations, colors in source.
hud_digit:
 asl
 asl
 asl
 asl
 asl
 sta hud_src
 lda #0
 rol
 sta hud_src+1
 lda hud_dst_lo,y
 sta hud_dst
 lda hud_dst_hi,y
 ldx back_buffer
 bne hud_dst_ready
 sec
 sbc #4
hud_dst_ready:
 sta hud_dst+1
 lda hud_phase,y
 sta hud_mask
 clc
 adc hud_src
 adc #<hud_numbers
 sta hud_src
 lda hud_src+1
 adc #>hud_numbers
 sta hud_src+1
 lda hud_mask
 bne 1f
 jmp hud_phase_zero
1:
hud_phase_two:
 .irp row,0,1,2,3,4,5,6,7
 ldy #\row
 lda (hud_dst),y
 and #0xf0
 ora (hud_src),y
 sta (hud_dst),y
 .endr
 .irp row,8,9,10,11,12,13,14,15
 ldy #\row
 lda (hud_src),y
 sta (hud_dst),y
 .endr
 rts
hud_phase_zero:
 .irp row,0,1,2,3,4,5,6,7
 ldy #\row
 lda (hud_src),y
 sta (hud_dst),y
 .endr
 .irp row,8,9,10,11,12,13,14,15
 ldy #\row
 lda (hud_dst),y
 and #0x0f
 ora (hud_src),y
 sta (hud_dst),y
 .endr
 rts
render_banner:
 ldx back_buffer
 lda state
 cmp #2
 bne banner_not_over
 lda gameover_timer
 and #16
 beq banner_on
 lda #3
 bne banner_state_ready
banner_on:
 lda #2
 bne banner_state_ready
banner_not_over:
 lda #0
banner_state_ready:
 cmp banner_states,x
 beq banner_done
 sta banner_states,x
 cmp #3
 beq banner_blank
 cmp #2
 beq banner_over
 lda #<hud_credit
 sta hud_src
 lda #>hud_credit
 jmp banner_source
banner_over:
 lda #<hud_gameover
 sta hud_src
 lda #>hud_gameover
banner_source:
 sta hud_src+1
 lda #0xe8
 sta hud_dst
 lda back_buffer
 asl
 asl
 clc
 adc #0x0a
 sta hud_dst+1
 ldy #111
banner_copy:
 lda (hud_src),y
 sta (hud_dst),y
 dey
 bpl banner_copy
banner_done:
 rts
banner_blank:
 lda #0xe8
 sta hud_dst
 lda back_buffer
 asl
 asl
 clc
 adc #0x0a
 sta hud_dst+1
 lda #0
 ldy #111
1: sta (hud_dst),y
 dey
 bpl 1b
 rts
.section .rodata,"a",@progbits
hud_bits: .byte 1,2
hud_credit: .incbin "build/hud-credit.bin"
hud_gameover: .incbin "build/hud-gameover.bin"
hud_score_cols: .byte 0,1,2,3,4,5
hud_high_cols: .byte 6,7,8,9,10,11
hud_dst_lo:
 .irp col,1,2,3,4,5,6,10,11,12,13,14,15,19,20,21,22
 .byte ((0x0c00+320+((\col*6+2)/4)*8)&255)
 .endr
 .byte ((0x0c00+640+6*8)&255)
hud_dst_hi:
 .irp col,1,2,3,4,5,6,10,11,12,13,14,15,19,20,21,22
 .byte ((0x0c00+320+((\col*6+2)/4)*8)>>8)
 .endr
 .byte ((0x0c00+640+6*8)>>8)
hud_phase:
 .irp col,1,2,3,4,5,6,10,11,12,13,14,15,19,20,21,22,4
 .byte (((\col*6+2)&3)*8)
 .endr

.section .startup,"ax",@progbits
hud_numbers: .incbin "src/arcade-assets/hud-glyphs.bin",1024,320
 .fill 32,1,0                  // blank digit used by the arcade score flash

.section .font,"a",@progbits
.set hud_initial,0xa000
