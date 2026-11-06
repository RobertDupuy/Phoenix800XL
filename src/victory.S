.include "build/main-symbols.inc"
.include "src/campaign-defs.inc"
.section .victory,"ax",@progbits
.global victory_entries
victory_entries:
 jmp blast_draw
 jmp award_draw
blast_draw:
 lda #95
 sec
 sbc boss_timer
 cmp #63
 bcc 1f
 rts
1: asl
 tax
 lda blast_frames,x
 sta record_ptr
 lda blast_frames+1,x
 sta record_ptr+1
 ldy #0
 lda (record_ptr),y
 sta effect_count
 jsr blast_advance
 lda #8
 sec
 sbc boss_scroll
 lsr
 lsr
 lsr
 sec
 sbc #4
 sta effect_origin_y
blast_cell:
 ldy #0
 lda (record_ptr),y
 sta effect_cell
 iny
 lda (record_ptr),y
 sta draw_template
 jsr blast_advance
 jsr blast_advance
 lda effect_cell
 and #15
 clc
 adc effect_origin_y
 and #31
 cmp #25
 bcc 1f
 jmp blast_next
1:
 sta draw_row
 lda effect_cell
 lsr
 lsr
 lsr
 lsr
 clc
 adc #13
 sta draw_col
 jsr row_pointer
 jsr blast_destination
 lda draw_template
 asl
 tax
 lda blast_tiles,x
 sta src_data
 lda blast_tiles+1,x
 sta src_data+1
 .irp row,0,1,2,3,4,5,6,7
 ldy #\row+8
 lda (src_data),y
 ldy #\row
 and (boss_bgptr),y
 ora (src_data),y
 sta (dst_ptr),y
 .endr
blast_next:
 dec effect_count
 beq 1f
 jmp blast_cell
1: rts
blast_advance:
 inc record_ptr
 bne 1f
 inc record_ptr+1
1: rts
blast_destination:
 lda draw_row
 lsr
 lsr
 lsr
 cmp #3
 bcc 1f
 lda #2
1: tax
 lda lg_font_bases,x
 sta font_hi
 lda back_buffer
 asl
 asl
 clc
 adc font_hi
 sta font_hi
 ldy #0
 lda (map_ptr),y
 and #127
 tax
 lda glyph_lo,x
 sta boss_bgptr
 lda glyph_hi,x
 ora font_hi
 sta boss_bgptr+1
 lda #0
 sta (map_ptr),y
 sta draw_palette
 jmp large_cell_glyph
award_draw:
 lda boss_award_row
 cmp #25
 bcc 1f
 rts
1: sta draw_row
 lda #0
 sta boss_number_index
award_cell:
 lda boss_number_index
 clc
 adc #19
 sta draw_col
 jsr row_pointer
 jsr blast_destination
 lda #0
 ldx boss_number_index
 cpx #2
 bcs 1f
 lda boss_award_low
 cpx #1
 beq 1f
 lda boss_award
1: asl
 asl
 asl
 tax
 .irp row,0,1,2,3,4,5,6,7
 lda award_digit_0+\row,x
 ldy #\row
 sta (dst_ptr),y
 .endr
 inc boss_number_index
 lda boss_number_index
 cmp #4
 bcc award_cell
 rts
.include "build/victory-art.inc"
victory_end:
