# Supplied 5200 alien: three unscaled, single-line PMG color planes.
# PM0..2 belong to the cockpit above line 192, and to the player below it.
.set pilot_pending_y,0x1100
.set pilot_pending_frame,0x1102
.set pilot_old_y,0x1104
.set pilot_old_frame,0x1105
.set pilot_new_y,0x1106
.set pilot_new_frame,0x1107
.set pilot_rows,0x1108

.section .expanded_code,"ax",@progbits
pilot_prepare:
 ldx back_buffer
 lda #0
 sta pilot_pending_y,x
 lda boss_status
 cmp #3
 bcs 2f
 lda #72
 sec
 sbc boss_scroll
 cmp #24
 bcc 2f
 cmp #177
 bcs 2f
 sta pilot_pending_y,x
 lda boss_body+64
 and #6
 asl
 asl
 asl
 sta pilot_pending_frame,x
2: rts

.section .text,"ax",@progbits
pilot_commit:
 lda #0
 ldx large_shown
 cpx #3
 bne 1f
 ldx front_buffer
 lda pilot_pending_frame,x
 sta pilot_new_frame
 lda pilot_pending_y,x
1: sta pilot_new_y
 cmp pilot_old_y
 bne pilot_move
 beq pilot_same_y
pilot_move:
 ldy pilot_old_y
 beq pilot_copy
 # The descent advances one scanline at a time. Only the uncovered top
 # scanline needs clearing; the new sprite overwrites the other fifteen.
 tya
 clc
 adc #1
 cmp pilot_new_y
 bne 2f
 lda #0
 sta 0x1400,y
 sta 0x1500,y
 sta 0x1600,y
 jmp xl_pilot_descend
2:
 ldx #16
 lda #0
1: sta 0x1400,y
 sta 0x1500,y
 sta 0x1600,y
 iny
 dex
 bne 1b
 jmp pilot_copy
pilot_same_y:
 lda pilot_new_frame
 cmp pilot_old_frame
 bne pilot_copy
 rts
pilot_copy:
 lda pilot_new_y
 sta pilot_old_y
 bne 1f
 rts
1:
 tay
 ldx pilot_new_frame
 stx pilot_old_frame
 jmp xl_pilot_copy
pilot_commit_done:
 rts

pilot_start:
 lda pilot_old_y
 beq 1f
 lda #128
1: sta 0xd000
 sta 0xd001
 sta 0xd002
 lda #170
 sta 0xd012
 lda #100
 sta 0xd013
 lda #102
 sta 0xd014
 rts

player_restore_dli:
 pha
 lda shield_pmg_pose
 cmp #4
 bcs 1f
 lda 0x338
 sta 0xd40a
 sta 0xd000
 clc
 adc #8
 sta 0xd001
 sec
 sbc #4
 sta 0xd002
 lda #198
 sta 0xd012
 sta 0xd013
 lda #70
 sta 0xd014
 jmp 2f
1: lda ship_hpos
 sta 0xd40a
 sta 0xd000
 sta 0xd001
 sta 0xd002
 lda #14
 sta 0xd012
 lda #70
 sta 0xd013
 lda #44
 sta 0xd014
2: lda #<shield_palette_dli
 sta 0x206
 lda #>shield_palette_dli
 sta 0x207
 pla
 rti

shield_palette_dli:
 pha
 lda shield_pmg_pose
 cmp #4
 bcs 1f
shield_palette_set:
 lda #14
 sta 0xd40a
 sta 0xd016
 lda #44
 sta 0xd017
 lda #100
 sta 0xd018
1: pla
 rti

.section .tables,"a",@progbits
pilot_cyan: .incbin "build/pilot-cyan.bin"
pilot_purple: .incbin "build/pilot-purple.bin"
pilot_pink: .incbin "build/pilot-pink.bin"
