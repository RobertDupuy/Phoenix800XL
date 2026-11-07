# XL hardware support, copied to RAM under the OS before the game starts.
# Keep the 5200 dispatch latency: existing DLIs depend on these 16 cycles.
.section .platform,"ax",@progbits
.global xl_nmi,xl_install_interrupts
xl_nmi:
 bit 0xd40f
 sta 0xd40f
 bmi xl_dli
 bvc xl_other_nmi
 jmp (0x202)
xl_dli:
 jmp (0x206)
xl_other_nmi:
 rti

xl_install_interrupts:
 lda #<xl_nmi
 sta 0xfffa
 lda #>xl_nmi
 sta 0xfffb
 lda #<irq_stub
 sta 0xfffe
 lda #>irq_stub
 sta 0xffff
 lda #0xd0
 sta 0xfffc
 lda #0xbf
 sta 0xfffd
 # PIA port A is input on all eight joystick direction lines.
 lda #0x38
 sta 0xd302
 lda #0
 sta 0xd300
 lda #0x3c
 sta 0xd302
 rts

input_sample:
 lda fire_now
 sta fire_prev
 lda 0xd010
 eor #1
 and #1
 sta fire_now
 lda state
 cmp #1
 beq xl_fire_sampled
 # START also starts a game; fire retains the existing restart delay.
 lda 0xd01f
 eor #1
 and #1
 ora fire_now
 sta fire_now
xl_fire_sampled:
 lda fire_now
 beq xl_no_fire_edge
 lda fire_prev
 bne xl_no_fire_edge
 lda #1
 sta fire_edge
xl_no_fire_edge:
 jsr shield_input
 # A page-aligned lookup keeps the VBI cost close to the original pot read.
 # Opposite horizontal directions together are neutral.
 ldx 0xd300
 lda xl_directions,x
 sta stick_x
 rts

shield_input:
 lda shield_now
 sta shield_prev
 lda 0xd300
 eor #255
 and #2
 sta shield_now
 beq shield_input_done
 lda shield_prev
 bne shield_input_done
 lda #1
 sta shield_edge
shield_input_done:
 rts

.balign 256
xl_directions:
 .set xl_direction,0
 .rept 256
 .if (xl_direction & 12) == 8
 .byte 0
 .elseif (xl_direction & 12) == 4
 .byte 228
 .else
 .byte 114
 .endif
 .set xl_direction,xl_direction+1
 .endr

# Shield expiry used to copy pose zero and then copy the moving pose again.
# Restore the correct full pose once, including the shield-covered constant
# rows. Unrolling avoids the loop/indexed-store overhead in the short VBI.
xl_restore_ship:
 lda video_ship_x
 clc
 adc #4
 lsr
 and #3
 sta ship_pose
 asl
 asl
 asl
 asl
 tax
 .include "build/xl-restore-ship.inc"
 rts

# Equal rows share a load, preserving every pixel while shortening the VBI.
xl_pilot_copy:
 .include "build/xl-pilot-copy.inc"
 rts

xl_pilot_descend:
 lda pilot_new_y
 sta pilot_old_y
 tay
 ldx pilot_new_frame
 stx pilot_old_frame
 .include "build/xl-pilot-descend.inc"
 rts

# Eighteen dedicated small-wave glyphs avoid displacing cached bird artwork.
# Copy four 36-byte groups from the selected pre-shifted RAM page. This code
# resides in RAM; only foreground-owned operand high bytes are patched.
xl_draw_scenery:
 lda star_phase
 clc
 adc #0xe3
 .irp n,0,1,2,3
 sta xl_space_load\n+2
 .endr
 lda font_hi
 clc
 adc #2
 .irp n,0,1,2,3
 sta xl_space_store\n+2
 .endr
 ldy #35
xl_space_copy:
 .irp n,0,1,2,3
xl_space_load\n:
 lda 0xe300+36*\n,y
xl_space_store\n:
 sta 0x2200+36*\n,y
 .endr
 dey
 bpl xl_space_copy
 rts

# Select one sparse placement list for the shared whole-cell scroll position.
xl_bg_select:
 tax
 lda xl_bg_lo,x
 sta xl_bg_erase_lo+1
 sta xl_bg_paint_lo+1
 clc
 adc #80
 sta xl_bg_erase_hi+1
 sta xl_bg_paint_hi+1
 lda xl_bg_hi,x
 sta xl_bg_erase_lo+2
 sta xl_bg_paint_lo+2
 adc #0
 sta xl_bg_erase_hi+2
 sta xl_bg_paint_hi+2
 rts
xl_bg_erase:
 ldy #0
 ldx #0
xl_bg_erase_next:
xl_bg_erase_hi:
 lda 0xeb50,x
 bmi xl_bg_erase_skip
 ora map_hi
 sta map_ptr+1
xl_bg_erase_lo:
 lda 0xeb00,x
 sta map_ptr
 lda #0
 sta (map_ptr),y
xl_bg_erase_skip:
 inx
 cpx #80
 bcc xl_bg_erase_next
 rts
xl_bg_paint:
 ldy #0
 ldx #0
xl_bg_paint_next:
xl_bg_paint_hi:
 lda 0xeb50,x
 bmi xl_bg_paint_skip
 ora map_hi
 sta map_ptr+1
xl_bg_paint_lo:
 lda 0xeb00,x
 sta map_ptr
 lda xl_bg_codes,x
 sta (map_ptr),y
xl_bg_paint_skip:
 inx
 cpx #80
 bcc xl_bg_paint_next
 rts
.include "build/xl-background.inc"
