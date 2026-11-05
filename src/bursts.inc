# Small-bird hit animation: arcade $17B0 sequence, six cells (3 by 2).
# Two normal slots and two bonus slots follow the recovered arcade effects.
# Displaced graphics keep their pending award in a separate bounded queue.
.set burst_count,0x380
.set burst_x,0x383
.set burst_y,0x386
.set burst_pose,0x389
.set burst_total,0x38c
.set burst_slot,0xfb
.section .expanded_code,"ax",@progbits
.global burst_start,burst_tick,draw_bursts,clear_bursts
burst_start:
 pha
 cmp #10
 bcc 8f
 ldy large_mode
 beq 8f
 jmp burst_bonus_requested
8: cmp #20
 beq burst_bonus_requested
 ldy #0
 lda burst_count
 beq burst_free
 iny
 lda burst_count+1
 beq burst_free
 # Exactly as the arcade: a third ordinary hit spills into bonus slot zero.
 ldy #0
 beq burst_bonus_allocated
burst_bonus_requested:
 ldy #0
 lda bonus_count
 beq burst_bonus_allocated
 iny
 lda bonus_count+1
 beq burst_bonus_allocated
 # The original overwrites its next slot if both are occupied. Bounded here
 # to the two real effect slots, retaining the most recently triggered hit.
 ldy #1
burst_bonus_allocated:
 jsr preserve_displaced_score
 tya
 ora #128
 sta 0x38e
 pla
 sta bonus_score,y
 sta bonus_value,y
 cmp #20
 beq 3f
 pha
 lda large_mode
 beq 9f
 pla
 jmp 3f
9: pla
 lda #12
 bne 4f
3:
 lda #16
4:
 sta bonus_count,y
 lda #0
 sta bonus_shown,y
 sta bonus_digits,y
 lda screen_enemy_x,x
 lsr
 lsr
 lsr
 clc
 adc #7
 sta bonus_x,y
 lda screen_enemy_y,x
 lsr
 lsr
 lsr
 sec
 sbc #4
 sta bonus_y,y
 rts
burst_free:
 sty 0x38e
 pla
 sta burst_score,y
 lda #12
 sta burst_count,y
 lda #255
 sta burst_pose,y
 lda screen_enemy_x,x
 lsr
 lsr
 lsr
 clc
 adc #6
 sta burst_x,y
 lda screen_enemy_y,x
 lsr
 lsr
 lsr
 sec
 sbc #4
 sta burst_y,y
 inc burst_total
 bne 2f
 inc burst_total+1
2:
 rts
burst_tick:
 jsr deferred_score_tick
 ldx #2
burst_tick_loop:
 lda burst_count,x
 beq burst_tick_next
 lsr
 sta burst_pose,x
 dec burst_count,x
burst_tick_next:
 dex
 bpl burst_tick_loop
 ldx #1
bonus_tick_loop:
 lda bonus_count,x
 beq bonus_tick_next
 dec bonus_count,x
 lda bonus_count,x
 sta bonus_shown,x
 and #1
 bne bonus_tick_next
 lda #1
 sta bonus_digits,x
bonus_tick_next:
 dex
 bpl bonus_tick_loop
 rts

# Previous footprints are independent for the two screen buffers.
clear_bursts:
 lda back_buffer
 asl
 asl
 asl
 sta burst_slot
 clc
 adc #3
 sta tiles_left
burst_clear_slot:
 ldx burst_slot
 lda 0x6d0,x
 cmp #127
 beq burst_clear_slot_next
 sta draw_row
 lda 0x6c0,x
 sta draw_col
 lda #127
 sta 0x6d0,x
 jsr row_pointer
 lda draw_col
 cmp #7
 bcc burst_clear_slow
 cmp #31
 bcs burst_clear_slow
 lda draw_row
 cmp #24
 bcs burst_clear_slow
 lda #0
 .irp off,0,32,1,33,2,34
 ldy #\off
 sta (map_ptr),y
 .endr
 jmp burst_clear_slot_next
burst_clear_slow:
 lda #0
 sta tile_index
burst_clear_cell:
 jsr burst_clip
 bcs burst_clear_next
 lda #0
 sta (map_ptr),y
burst_clear_next:
 inc tile_index
 lda tile_index
 cmp #6
 bcc burst_clear_cell
burst_clear_slot_next:
 inc burst_slot
 lda burst_slot
 cmp tiles_left
 bcc burst_clear_slot
 rts
draw_bursts:
 lda state
 cmp #1
 beq burst_draw_begin
 cmp #3
 beq 1f
 rts
1:
 lda death_timer
 cmp #33
 bcs 1f
 rts
1:
burst_draw_begin:
 lda #0
 sta burst_slot
burst_draw_slot:
 ldx burst_slot
 lda burst_count,x
 beq burst_draw_next
 lda burst_x,x
 sta draw_col
 lda burst_y,x
 sta draw_row
 lda burst_pose,x
 cmp #255
 beq burst_draw_next
 asl
 sta draw_id
 asl
 clc
 adc draw_id
 sta draw_id
 lda back_buffer
 asl
 asl
 asl
 clc
 adc burst_slot
 tax
 lda draw_col
 sta 0x6c0,x
 lda draw_row
 sta 0x6d0,x
 jsr row_pointer
 lda #0
 sta draw_flags
 lda draw_col
 cmp #7
 bcc burst_inside_done
 cmp #31
 bcs burst_inside_done
 lda draw_row
 cmp #24
 bcs burst_inside_done
 inc draw_flags
burst_inside_done:
 lda draw_flags
 beq 8f
 jsr draw_burst_fast
 jmp burst_draw_next
8:
 lda #0
 sta tile_index
burst_draw_cell:
 lda draw_flags
 beq burst_draw_clipped
 ldx tile_index
 ldy burst_offsets,x
 jmp burst_draw_visible
burst_draw_clipped:
 jsr burst_clip
 bcs burst_draw_cell_next
burst_draw_visible:
 ldx draw_id
 lda burst_shapes,x
 sta draw_template
 tax
 jsr stamp_tile
burst_draw_cell_next:
 inc draw_id
 inc tile_index
 lda tile_index
 cmp #6
 bcc burst_draw_cell
burst_draw_next:
 inc burst_slot
 lda burst_slot
 cmp #3
 bcs 9f
 jmp burst_draw_slot
9:
burst_draw_done:
 rts
burst_clip:
 ldx tile_index
 lda burst_rows,x
 clc
 adc draw_row
 cmp #25
 bcs burst_clipped
 lda burst_cols,x
 clc
 adc draw_col
 cmp #7
 bcc burst_clipped
 cmp #33
 bcs burst_clipped
 ldy burst_offsets,x
 clc
 rts
burst_clipped:
 sec
 rts
.section .tables,"a",@progbits
burst_shapes: .incbin "build/burst-shapes.bin"
burst_rows: .byte 0,1,0,1,0,1
burst_cols: .byte 0,0,1,1,2,2
burst_offsets: .byte 0,32,1,33,2,34

.section .shield_code,"ax",@progbits
.global draw_burst_fast
draw_burst_fast:
 .set cell,0
 .irp offset,0,32,1,33,2,34
 ldx draw_id
 lda burst_shapes+cell,x
 sta draw_template
 tax
 ldy #\offset
 jsr stamp_tile
 .set cell,cell+1
 .endr
 rts

.section .expanded_code,"ax",@progbits
.set pending_scores,0x789
.set pending_score_fault,0x78a
.set pending_age,0x3d00
.set pending_award,0x3d10
preserve_displaced_score:
 lda bonus_score,y
 beq displaced_done
 lda bonus_count,y
 beq displaced_done
 txa
 pha
 tya
 pha
 ldx #15
displaced_find:
 lda pending_age,x
 beq displaced_free
 dex
 bpl displaced_find
 # Defensive fallback; sixteen records already cover every bird in a wave.
 inc pending_score_fault
 lda bonus_score,y
 jsr score_add
 jmp displaced_restore
displaced_free:
 lda bonus_count,y
 sta pending_age,x
 lda bonus_score,y
 sta pending_award,x
 inc pending_scores
displaced_restore:
 pla
 tay
 pla
 tax
displaced_done:
 rts
deferred_score_tick:
 lda pending_scores
 beq deferred_tick_done
 ldx #15
deferred_tick_loop:
 lda pending_age,x
 cmp #2
 bcc deferred_tick_next
 dec pending_age,x
deferred_tick_next:
 dex
 bpl deferred_tick_loop
deferred_tick_done:
 rts
deferred_score_service:
 lda pending_scores
 beq deferred_service_done
 ldx #15
deferred_service_loop:
 lda pending_age,x
 cmp #1
 bne deferred_service_next
 lda #0
 sta pending_age,x
 dec pending_scores
 txa
 pha
 lda pending_award,x
 jsr score_add
 pla
 tax
deferred_service_next:
 dex
 bpl deferred_service_loop
deferred_service_done:
 rts
