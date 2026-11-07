# Straight-line eight-column renderer in XL RAM. Blank tiles perform only
# the occupancy test; occupied tiles retain unique glyphs and exact OR merges.
.section .platform,"ax",@progbits
xl_large_row:
 lsr lg_bits
 bcs xl_large_col_0
 jmp xl_large_next_0
xl_large_col_0:
 lda lg_offset
 clc
 adc #0
 sta large_src
 ldy #0
 lda (map_ptr),y
 and #127
 bne xl_large_merge_0
 ldx lg_region
 lda lg_next,x
 inc lg_next,x
 cmp #128
 bcc 1f
 inc layout_faults
 lda #127
1: ora draw_palette
 sta (map_ptr),y
 and #127
 tax
 lda glyph_lo,x
 sta dst_ptr
 lda glyph_hi,x
 ora font_hi
 sta dst_ptr+1
 .irp row,0,1,2,3,4,5,6,7
 ldy #\row
 lda (large_src),y
 sta (dst_ptr),y
 .endr
 jmp xl_large_next_0
xl_large_merge_0:
 tax
 lda glyph_lo,x
 sta dst_ptr
 lda glyph_hi,x
 ora font_hi
 sta dst_ptr+1
 .irp row,0,1,2,3,4,5,6,7
 ldy #\row
 lda (large_src),y
 ora (dst_ptr),y
 sta (dst_ptr),y
 .endr
xl_large_next_0:
 lsr lg_bits
 bcs xl_large_col_1
 jmp xl_large_next_1
xl_large_col_1:
 lda lg_offset
 clc
 adc #32
 sta large_src
 ldy #1
 lda (map_ptr),y
 and #127
 bne xl_large_merge_1
 ldx lg_region
 lda lg_next,x
 inc lg_next,x
 cmp #128
 bcc 1f
 inc layout_faults
 lda #127
1: ora draw_palette
 sta (map_ptr),y
 and #127
 tax
 lda glyph_lo,x
 sta dst_ptr
 lda glyph_hi,x
 ora font_hi
 sta dst_ptr+1
 .irp row,0,1,2,3,4,5,6,7
 ldy #\row
 lda (large_src),y
 sta (dst_ptr),y
 .endr
 jmp xl_large_next_1
xl_large_merge_1:
 tax
 lda glyph_lo,x
 sta dst_ptr
 lda glyph_hi,x
 ora font_hi
 sta dst_ptr+1
 .irp row,0,1,2,3,4,5,6,7
 ldy #\row
 lda (large_src),y
 ora (dst_ptr),y
 sta (dst_ptr),y
 .endr
xl_large_next_1:
 lsr lg_bits
 bcs xl_large_col_2
 jmp xl_large_next_2
xl_large_col_2:
 lda lg_offset
 clc
 adc #64
 sta large_src
 ldy #2
 lda (map_ptr),y
 and #127
 bne xl_large_merge_2
 ldx lg_region
 lda lg_next,x
 inc lg_next,x
 cmp #128
 bcc 1f
 inc layout_faults
 lda #127
1: ora draw_palette
 sta (map_ptr),y
 and #127
 tax
 lda glyph_lo,x
 sta dst_ptr
 lda glyph_hi,x
 ora font_hi
 sta dst_ptr+1
 .irp row,0,1,2,3,4,5,6,7
 ldy #\row
 lda (large_src),y
 sta (dst_ptr),y
 .endr
 jmp xl_large_next_2
xl_large_merge_2:
 tax
 lda glyph_lo,x
 sta dst_ptr
 lda glyph_hi,x
 ora font_hi
 sta dst_ptr+1
 .irp row,0,1,2,3,4,5,6,7
 ldy #\row
 lda (large_src),y
 ora (dst_ptr),y
 sta (dst_ptr),y
 .endr
xl_large_next_2:
 lsr lg_bits
 bcs xl_large_col_3
 jmp xl_large_next_3
xl_large_col_3:
 lda lg_offset
 clc
 adc #96
 sta large_src
 ldy #3
 lda (map_ptr),y
 and #127
 bne xl_large_merge_3
 ldx lg_region
 lda lg_next,x
 inc lg_next,x
 cmp #128
 bcc 1f
 inc layout_faults
 lda #127
1: ora draw_palette
 sta (map_ptr),y
 and #127
 tax
 lda glyph_lo,x
 sta dst_ptr
 lda glyph_hi,x
 ora font_hi
 sta dst_ptr+1
 .irp row,0,1,2,3,4,5,6,7
 ldy #\row
 lda (large_src),y
 sta (dst_ptr),y
 .endr
 jmp xl_large_next_3
xl_large_merge_3:
 tax
 lda glyph_lo,x
 sta dst_ptr
 lda glyph_hi,x
 ora font_hi
 sta dst_ptr+1
 .irp row,0,1,2,3,4,5,6,7
 ldy #\row
 lda (large_src),y
 ora (dst_ptr),y
 sta (dst_ptr),y
 .endr
xl_large_next_3:
 lsr lg_bits
 bcs xl_large_col_4
 jmp xl_large_next_4
xl_large_col_4:
 lda lg_offset
 clc
 adc #128
 sta large_src
 ldy #4
 lda (map_ptr),y
 and #127
 bne xl_large_merge_4
 ldx lg_region
 lda lg_next,x
 inc lg_next,x
 cmp #128
 bcc 1f
 inc layout_faults
 lda #127
1: ora draw_palette
 sta (map_ptr),y
 and #127
 tax
 lda glyph_lo,x
 sta dst_ptr
 lda glyph_hi,x
 ora font_hi
 sta dst_ptr+1
 .irp row,0,1,2,3,4,5,6,7
 ldy #\row
 lda (large_src),y
 sta (dst_ptr),y
 .endr
 jmp xl_large_next_4
xl_large_merge_4:
 tax
 lda glyph_lo,x
 sta dst_ptr
 lda glyph_hi,x
 ora font_hi
 sta dst_ptr+1
 .irp row,0,1,2,3,4,5,6,7
 ldy #\row
 lda (large_src),y
 ora (dst_ptr),y
 sta (dst_ptr),y
 .endr
xl_large_next_4:
 lsr lg_bits
 bcs xl_large_col_5
 jmp xl_large_next_5
xl_large_col_5:
 lda lg_offset
 clc
 adc #160
 sta large_src
 ldy #5
 lda (map_ptr),y
 and #127
 bne xl_large_merge_5
 ldx lg_region
 lda lg_next,x
 inc lg_next,x
 cmp #128
 bcc 1f
 inc layout_faults
 lda #127
1: ora draw_palette
 sta (map_ptr),y
 and #127
 tax
 lda glyph_lo,x
 sta dst_ptr
 lda glyph_hi,x
 ora font_hi
 sta dst_ptr+1
 .irp row,0,1,2,3,4,5,6,7
 ldy #\row
 lda (large_src),y
 sta (dst_ptr),y
 .endr
 jmp xl_large_next_5
xl_large_merge_5:
 tax
 lda glyph_lo,x
 sta dst_ptr
 lda glyph_hi,x
 ora font_hi
 sta dst_ptr+1
 .irp row,0,1,2,3,4,5,6,7
 ldy #\row
 lda (large_src),y
 ora (dst_ptr),y
 sta (dst_ptr),y
 .endr
xl_large_next_5:
 lsr lg_bits
 bcs xl_large_col_6
 jmp xl_large_next_6
xl_large_col_6:
 lda lg_offset
 clc
 adc #192
 sta large_src
 ldy #6
 lda (map_ptr),y
 and #127
 bne xl_large_merge_6
 ldx lg_region
 lda lg_next,x
 inc lg_next,x
 cmp #128
 bcc 1f
 inc layout_faults
 lda #127
1: ora draw_palette
 sta (map_ptr),y
 and #127
 tax
 lda glyph_lo,x
 sta dst_ptr
 lda glyph_hi,x
 ora font_hi
 sta dst_ptr+1
 .irp row,0,1,2,3,4,5,6,7
 ldy #\row
 lda (large_src),y
 sta (dst_ptr),y
 .endr
 jmp xl_large_next_6
xl_large_merge_6:
 tax
 lda glyph_lo,x
 sta dst_ptr
 lda glyph_hi,x
 ora font_hi
 sta dst_ptr+1
 .irp row,0,1,2,3,4,5,6,7
 ldy #\row
 lda (large_src),y
 ora (dst_ptr),y
 sta (dst_ptr),y
 .endr
xl_large_next_6:
 lsr lg_bits
 bcs xl_large_col_7
 jmp xl_large_next_7
xl_large_col_7:
 lda lg_offset
 clc
 adc #224
 sta large_src
 ldy #7
 lda (map_ptr),y
 and #127
 bne xl_large_merge_7
 ldx lg_region
 lda lg_next,x
 inc lg_next,x
 cmp #128
 bcc 1f
 inc layout_faults
 lda #127
1: ora draw_palette
 sta (map_ptr),y
 and #127
 tax
 lda glyph_lo,x
 sta dst_ptr
 lda glyph_hi,x
 ora font_hi
 sta dst_ptr+1
 .irp row,0,1,2,3,4,5,6,7
 ldy #\row
 lda (large_src),y
 sta (dst_ptr),y
 .endr
 jmp xl_large_next_7
xl_large_merge_7:
 tax
 lda glyph_lo,x
 sta dst_ptr
 lda glyph_hi,x
 ora font_hi
 sta dst_ptr+1
 .irp row,0,1,2,3,4,5,6,7
 ldy #\row
 lda (large_src),y
 ora (dst_ptr),y
 sta (dst_ptr),y
 .endr
xl_large_next_7:
 rts
