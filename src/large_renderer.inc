# Three independent 64/64/72-line character regions. Every occupied map cell
# owns its glyph, allowing the arcade's global one-pixel Y scroll and clipping.
.set lg_next,0x3d80
.set lg_saved_x,0x3d83
.set lg_cell,0x74
.set lg_col,0x3d84
.set lg_row,0x3d85
.set lg_first_row,0x3d86
.set lg_offset,0x3d87
.set lg_phase,0x3d88
.set lg_first_col,0x3d89
.set lg_left,0x3d8a
.set lg_right,0x3d8b
.set lg_value,0x3d8c
.set lg_mask,0x3d90
.set lg_maskptr,0x76
.section .text,"ax",@progbits
.global large_render,large_draw_one,large_cell_glyph,large_stamp_native,large_soft_glyph,large_draw_shield
large_render:
 lda front_buffer
 eor #1
 sta back_buffer
 tax
 lda large_buffer,x
 sta large_old_mode
 lda large_mode
 sta large_buffer,x
 lda back_buffer
 asl
 asl
 clc
 adc #0x28
 sta map_hi
 sta map_ptr+1
 lda large_old_mode
 beq 7f
 jsr large_clear_footprints
 jmp large_map_clean
7: lda #0
 ldx #0
 ldy back_buffer
 bne large_clear_map1
large_clear_map0:
 .rept 4
 sta 0x2800,x
 sta 0x2900,x
 sta 0x2a00,x
 inx
 .endr
 bne large_clear_map0
 ldx #31
1: sta 0x2b00,x
 dex
 bpl 1b
 jmp large_map_clean
large_clear_map1:
 .rept 4
 sta 0x2c00,x
 sta 0x2d00,x
 sta 0x2e00,x
 inx
 .endr
 bne large_clear_map1
 ldx #31
1: sta 0x2f00,x
 dex
 bpl 1b
large_map_clean:
 ldx back_buffer
 lda state
 sta 0x332,x
 lda explosion_left
 sta 0x334,x
 lda #1
 sta lg_next
 sta lg_next+1
 sta lg_next+2
 lda #0
 sta draw_palette
 sta draw_row
 ldx #0
large_zero_fonts:
 lda lg_font_bases,x
 clc
 adc back_buffer
 adc back_buffer
 adc back_buffer
 adc back_buffer
 sta dst_ptr+1
 lda #0
 sta dst_ptr
 ldy #7
5: sta (dst_ptr),y
 dey
 bpl 5b
 inx
 cpx #3
 bne large_zero_fonts
 lda state
 cmp #1
 beq large_scene_birds
 cmp #3
 bne large_scene_effects
 lda death_timer
 cmp #33
 bcc large_scene_effects
large_scene_birds:
 jsr large_art_bank
 ldx #7
large_scene_slot:
 stx large_index
 lda enemy_on,x
 beq large_scene_next
 jsr large_draw_one
large_scene_next:
 ldx large_index
 dex
 bpl large_scene_slot
 lda 0xbfc0
 lda 0xbfd0
large_scene_effects:
 jsr supplied_palette_build
 jsr large_effect_cache_clear
 ldx #2
1: lda lg_next,x
 cmp max_chars
 bcc 2f
 sta max_chars
2: dex
 bpl 1b
 jsr draw_bursts
 jsr draw_bonus
 jsr draw_explosion
 jsr draw_shield
 jsr draw_soft_bomb
 jsr draw_soft_shot
 jsr draw_second_shot
 lda #0x20
 ldx back_buffer
 beq 1f
 lda #0x24
1: sta font_hi
 jmp render_complete

.section .text,"ax",@progbits
large_draw_one:
 lda large_pose,x
 clc
 adc #0x80
 sta large_src+1
 lda large_x,x
 lsr
 lsr
 lsr
 cmp #29
 bcc 1f
 sec
 sbc #32
1: clc
 adc #7
 sta lg_first_col
 lda large_y,x
 and #7
 sta lg_phase
 lda large_y,x
 lsr
 lsr
 lsr
 sec
 sbc #4
 and #31
 sta lg_first_row
 txa
 pha
 lda back_buffer
 asl
 asl
 asl
 ora large_index
 tay
 lda lg_first_col
 sta large_previous,y
 lda lg_first_row
 sta large_previous+16,y
 pla
 tax
 lda #8
 sec
 sbc lg_phase
 sta lg_offset
 lda large_left,x
 jsr lg_trim
 sta lg_left
 lda large_right,x
 jsr lg_trim
 sta lg_value
 lda #8
 sec
 sbc lg_value
 sta lg_right
 lda #0
 sta draw_palette
2: lda large_pose,x
 lsr
 lsr
 lsr
 clc
 adc #0xa0
 sta lg_maskptr+1
 lda large_pose,x
 asl
 asl
 asl
 asl
 asl
 sta lg_maskptr
 lda lg_phase
 asl
 asl
 ora lg_maskptr
 sta lg_maskptr
 lda 0xbfc0
 lda 0xbfd4
 .irp b,0,1,2
 ldy #\b
 lda (lg_maskptr),y
 sta lg_mask+\b
 .endr
 jsr large_art_bank
 lda lg_first_col
 cmp #7
 bcs 1f
 lda #7
 sec
 sbc lg_first_col
 cmp lg_left
 bcc 1f
 sta lg_left
1: lda #33
 sec
 sbc lg_first_col
 cmp lg_right
 bcs 2f
 sta lg_right
2: ldx lg_left
 lda lg_clip_left,x
 ldx lg_right
 and lg_clip_right,x
 sta lg_value
 lda #0
 sta lg_row
large_row:
 lda lg_first_row
 clc
 adc lg_row
 and #31
 sta draw_row
 cmp #25
 bcc 1f
 jmp large_row_next
1: ldy lg_row
 lda lg_mask,y
 and lg_value
 sta lg_bits
 bne 2f
 jmp large_row_next
2: lda draw_row
 lsr
 lsr
 lsr
 cmp #3
 bcc 3f
 lda #2
3: sta lg_region
 tax
 lda lg_font_bases,x
 sta font_hi
 lda back_buffer
 asl
 asl
 clc
 adc font_hi
 sta font_hi
 lda lg_first_col
 sta draw_col
 jsr row_pointer
 lda lg_offset
 sta large_src
 lda #8
 sta lg_col
large_fast_tile:
 lsr lg_bits
 bcs 8f
 jmp large_fast_next
8: ldy #0
 lda (map_ptr),y
 and #127
 bne large_fast_merge
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
 # Inline the hot pointer lookup: avoids JSR/RTS per occupied tile.
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
 jmp large_fast_next
large_fast_merge:
 # Inline the hot pointer lookup: avoids JSR/RTS per occupied tile.
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
large_fast_next:
 clc
 lda large_src
 adc #32
 sta large_src
 inc map_ptr
 bne 1f
 inc map_ptr+1
1: dec lg_col
 beq large_row_next
 jmp large_fast_tile
large_row_next:
 clc
 lda lg_offset
 adc #8
 sta lg_offset
 inc lg_row
 lda lg_row
 cmp #3
 beq large_fast_done
 jmp large_row
large_fast_done:
 rts

lg_trim:
 cmp #0
 beq 1f
 cmp #16
 bcc 2f
 cmp #32
 bcc 3f
 lda #3
 rts
2: lda #1
 rts
3: lda #2
1: rts

# Map pointer + Y identifies the cell. Region follows the actual map address,
# including effect tile offsets. Return its unique glyph at dst_ptr.
large_cell_glyph:
 stx lg_saved_x
 tya
 clc
 adc map_ptr
 sta lg_cell
 lda map_ptr+1
 adc #0
 sta lg_cell+1
 and #3
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
 lda (lg_cell),y
 and #127
 bne large_existing_cell
 lda large_mode
 cmp #3
 bne 4f
 jsr boss_allocate_glyph
 jmp large_allocated_cell
4:
 lda lg_next,x
 cmp #128
 bcc 2f
 inc layout_faults
 lda #127
2: inc lg_next,x
large_allocated_cell:
 pha
 cmp max_chars
 bcc 3f
 sta max_chars
3: # Inline the hot pointer lookup: avoids JSR/RTS per occupied tile.
 tax
 lda glyph_lo,x
 sta dst_ptr
 lda glyph_hi,x
 ora font_hi
 sta dst_ptr+1
 pla
 ora draw_palette
 ldy #0
 sta (lg_cell),y
 ldx lg_saved_x
 sec
 rts
large_existing_cell:
 pha
 # Inline the hot pointer lookup: avoids JSR/RTS per occupied tile.
 tax
 lda glyph_lo,x
 sta dst_ptr
 lda glyph_hi,x
 ora font_hi
 sta dst_ptr+1
 pla
large_cell_store:
 ora draw_palette
 ldy #0
 sta (lg_cell),y
 ldx lg_saved_x
 clc
 rts
large_stamp_native:
 lda large_mode
 cmp #3
 bne 9f
 jmp mothership_stamp
9:
 sty tile_offset
 txa
 bne 1f
 lda #0
 sta (map_ptr),y
 rts
1: lda native_flags,x
 sta draw_palette
 jsr large_effect_region
 ldy draw_template
 lda (cache_ptr),y
 beq large_native_new
 ldy tile_offset
 sta (map_ptr),y
 rts
large_native_new:
 lda #0
 ldy tile_offset
 sta (map_ptr),y
 jsr large_cell_glyph
 ldx draw_template
 .irp row,0,1,2,3,4,5,6,7
 lda native_tiles+(TEMPLATE_COUNT*\row),x
 ldy #\row
 sta (dst_ptr),y
 .endr
 ldy tile_offset
 lda (map_ptr),y
 ldy draw_template
 sta (cache_ptr),y
 ldx lg_region
 lda lg_cache_count,x
 cmp #64
 bcs 1f
 inc lg_cache_count,x
 clc
 adc lg_cache_bases,x
 tay
 lda draw_template
 sta 0x3c20,y
1: rts
large_effect_region:
 tya
 clc
 adc map_ptr
 lda map_ptr+1
 adc #0
 and #3
 cmp #3
 bcc 1f
 lda #2
1: sta lg_region
 clc
 adc #0x39
 sta cache_ptr+1
 lda #0
 sta cache_ptr
 rts
.section .expanded_code,"ax",@progbits
large_effect_cache_clear:
 ldx #2
large_cache_clear_region:
 txa
 clc
 adc #0x39
 sta cache_ptr+1
 lda #0
 sta cache_ptr
 lda large_old_mode
 bne large_cache_sparse
 ldy #0
1: sta (cache_ptr),y
 iny
 bne 1b
 sta lg_cache_count,x
 jmp large_cache_clear_next
large_cache_sparse:
 lda lg_cache_count,x
 beq large_cache_clear_next
 clc
 adc lg_cache_bases,x
 sta lg_end
 lda lg_cache_bases,x
 sta lg_cursor
2: ldy lg_cursor
 lda 0x3c20,y
 tay
 lda #0
 sta (cache_ptr),y
 inc lg_cursor
 lda lg_cursor
 cmp lg_end
 bne 2b
 lda #0
 sta lg_cache_count,x
large_cache_clear_next:
 dex
 bpl large_cache_clear_region
 rts
.section .text,"ax",@progbits
large_soft_glyph:
 ldy #0
 lda (map_ptr),y
 and #128
 sta draw_palette
 jsr large_effect_region
 ldx lg_region
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
 # Inline the hot pointer lookup: avoids JSR/RTS per occupied tile.
 tax
 lda glyph_lo,x
 sta dst_ptr
 lda glyph_hi,x
 ora font_hi
 sta dst_ptr+1
 lda dst_ptr
 sta cow_ptr
 lda dst_ptr+1
 sta cow_ptr+1
 lda #0
 ldy #0
 sta (map_ptr),y
 jsr large_cell_glyph
 .irp row,0,1,2,3,4,5,6,7
 ldy #\row
 lda (cow_ptr),y
 sta (dst_ptr),y
 .endr
 rts
.section .expanded_code,"ax",@progbits
large_draw_shield:
 lda state
 cmp #1
 beq 8f
 jmp large_shield_done
8:
 lda shield_pose
 cmp #255
 bne 8f
 jmp large_shield_done
8:
 tax
 lda shield_map_offsets,x
 sta effect_cursor
 lda raw_ship_x
 lsr
 lsr
 lsr
 clc
 adc #6
 sta draw_col
 ldx back_buffer
 sta shield_old_col,x
 lda #0
 sta effect_cell
large_shield_cell:
 ldx effect_cell
 lda lg_shield_rows,x
 sta draw_row
 jsr row_pointer
 ldx effect_cursor
 lda shield_maps,x
 pha
 and #128
 sta draw_palette
 ldy #0
 lda large_mode
 cmp #3
 bne 9f
 lda #0
 sta (map_ptr),y
9:
 jsr large_cell_glyph
 pla
 and #127
 beq large_shield_blank
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
 jmp large_shield_next
large_shield_blank:
 lda #0
 ldy #7
1: sta (dst_ptr),y
 dey
 bpl 1b
large_shield_next:
 inc effect_cursor
 inc effect_cell
 ldx effect_cell
 lda lg_shield_next,x
 beq 1f
 inc draw_col
1: cpx #16
 bcs large_shield_done
 jmp large_shield_cell
large_shield_done:
 rts
.section .text,"ax",@progbits
large_lower_dli:
 pha
 lda front_buffer
 asl
 asl
 clc
 adc #0x20
 sta 0xd40a
 sta 0xd409
 lda #<large_bottom_dli
 sta 0x206
 lda #>large_bottom_dli
 sta 0x207
 pla
 rti
large_bottom_dli:
 pha
 lda front_buffer
 asl
 asl
 clc
 adc #0x30
 sta 0xd40a
 sta 0xd409
 lda #<player_restore_dli
 sta 0x206
 lda #>player_restore_dli
 sta 0x207
 pla
 rti
.section .tables,"a",@progbits
lg_font_bases: .byte 0x18,0x20,0x30
lg_shield_rows: .byte 21,22,23,24,21,22,23,24,21,22,23,24,21,22,23,24
lg_shield_next: .byte 0,0,0,0,1,0,0,0,1,0,0,0,1,0,0,0,0

.set lg_bits,0x3d94
.set lg_region,0x3d95
lg_clip_left: .byte 255,254,252,248,240,224,192,128,0
lg_clip_right: .byte 0,1,3,7,15,31,63,127,255

.section .expanded_code,"ax",@progbits
large_clear_footprints:
 jsr clear_shield
 jsr clear_soft_bomb
 jsr clear_bursts
 jsr clear_bonus
 lda #0
 sta large_index
large_clear_bird:
 lda back_buffer
 asl
 asl
 asl
 ora large_index
 tax
 lda large_previous,x
 cmp #255
 bne 8f
 jmp large_clear_next
8:
 sta draw_col
 lda #255
 sta large_previous,x
 lda large_previous+16,x
 sta draw_row
 lda draw_col
 cmp #7
 bcc large_clear_edge
 cmp #26
 bcs large_clear_edge
 lda draw_row
 cmp #23
 bcs large_clear_edge
 jsr row_pointer
 lda #0
 .irp off,0,1,2,3,4,5,6,7,32,33,34,35,36,37,38,39,64,65,66,67,68,69,70,71
 ldy #\off
 sta (map_ptr),y
 .endr
 jmp large_clear_next
large_clear_edge:
 lda #3
 sta lg_row
1: lda draw_row
 cmp #25
 bcs 4f
 jsr row_pointer
 ldy #0
2: tya
 clc
 adc draw_col
 cmp #7
 bcc 3f
 cmp #33
 bcs 3f
 lda #0
 sta (map_ptr),y
3: iny
 cpy #8
 bcc 2b
4: inc draw_row
 lda draw_row
 and #31
 sta draw_row
 dec lg_row
 bne 1b
large_clear_next:
 inc large_index
 lda large_index
 cmp #8
 beq large_clear_finish
 jmp large_clear_bird
large_clear_finish:
 ldx back_buffer
 lda 0x332,x
 cmp #3
 bne 2f
 lda 0x334,x
 clc
 adc #<(player_explosion_row*32-4)
 sta map_ptr
 lda map_hi
 adc #1
 sta map_ptr+1
 ldx #25-player_explosion_row
1: lda #0
 ldy #15
3: sta (map_ptr),y
 dey
 bpl 3b
 clc
 lda map_ptr
 adc #32
 sta map_ptr
 bcc 4f
 inc map_ptr+1
4: dex
 bne 1b
2: rts


.set lg_cache_count,0x3d9a
.set lg_cursor,0x3d9d
.set lg_end,0x3d9e
.section .tables,"a",@progbits
lg_cache_bases: .byte 0,64,128

# Palette commands are published with the matching double-buffered picture.
# Each command changes colors at the exact fine-Y position, not a tile edge.
# Homogeneous stretches skip WSYNC waits and color writes.
.set supplied_palettes,0x3dc0
.set supplied_palette_current,0x78d
.section .expanded_code,"ax",@progbits
supplied_palette_build:
 lda back_buffer
 asl
 asl
 asl
 asl
 asl
 sta large_temp
 tax
 lda #0
 ldy #32
1: sta supplied_palettes,x
 inx
 dey
 bne 1b
 # Ends first, then starts: adjacent eggs retain the same palette.
 lda #0
 sta large_index
1: jsr supplied_egg_command
 inc large_index
 lda large_index
 cmp #8
 bcc 1b
 lda #8
 sta large_index
1: jsr supplied_egg_command
 inc large_index
 lda large_index
 cmp #16
 bcc 1b
 lda state
 cmp #3
 beq 8f
 lda shield_pose
 cmp #255
 beq supplied_palette_list
8: ldx large_temp
 lda #0x82
 sta supplied_palettes+21,x
 lda #0
 sta supplied_palettes+22,x
 sta supplied_palettes+23,x
 sta supplied_palettes+24,x
supplied_palette_list:
 # Only interrupt at real palette changes and the two font boundaries.
 # $1000-$107F is unused PMG prefix RAM during gameplay (startup-only fonts).
 lda back_buffer
 asl
 asl
 asl
 asl
 asl
 asl
 sta dst_ptr
 lda #0x10
 sta dst_ptr+1
 ldy #35
1: lda large_list0,y
 sta (dst_ptr),y
 dey
 bpl 1b
 lda #4
 ldy #26
 sta (dst_ptr),y
 ldy #28
 sta (dst_ptr),y
 # Begin large-wave preparation one HUD row early. The handler waits for
 # line 40 before changing the font/width, leaving the score intact.
 ldy #5
 sta (dst_ptr),y
 lda #0x84
 dey
 sta (dst_ptr),y
 lda back_buffer
 asl
 asl
 clc
 adc #0x28
 ldy #8
 sta (dst_ptr),y
 lda dst_ptr
 ldy #34
 sta (dst_ptr),y
 lda #0x10
 iny
 sta (dst_ptr),y
 lda #0
 sta large_index
 sta large_hit_count
supplied_palette_scan:
 lda large_index
 ora large_temp
 tax
 lda supplied_palettes,x
 bpl supplied_palette_scan_next
 and #3
 cmp large_hit_count
 bne 2f
 lda #0
 sta supplied_palettes,x
 beq supplied_palette_scan_next
2: sta large_hit_count
 lda large_index
 beq supplied_palette_scan_next
 clc
 adc #7
 cmp #8
 bne 3f
 lda #6
3: tay
 lda (dst_ptr),y
 ora #128
 sta (dst_ptr),y
supplied_palette_scan_next:
 inc large_index
 lda large_index
 cmp #25
 bcc supplied_palette_scan
 jmp supplied_raster_build
supplied_egg_command:
 lda large_index
 and #7
 tax
 lda enemy_on,x
 beq 9f
 lda large_pose,x
 cmp #16
 bcs 9f
 lda large_y,x
 sec
 sbc #32
 sta large_hit_y
 lda large_index
 cmp #8
 bcs 1f
 lda large_hit_y
 clc
 adc #16
 sta large_hit_y
1: lda large_hit_y
 cmp #232
 bcc 2f
 lda #0
 sta large_hit_y
2: cmp #200
 bcs 9f
 lda large_hit_y
 and #7
 asl
 asl
 ora #0x80
 sta large_hit_x
 lda large_index
 cmp #8
 bcc 3f
 inc large_hit_x
3: lda large_hit_y
 lsr
 lsr
 lsr
 ora large_temp
 tax
 lda large_hit_x
 sta supplied_palettes,x
9: rts

.set supplied_fonts,0x1080
.set supplied_delay,0x10c0
.set supplied_palette_base,0x1109
.set supplied_event,0x110a
.set supplied_color0,0x1140
.set supplied_color1,0x1180
.set supplied_color2,0x11c0
.section .text,"ax",@progbits
# All raster decisions are made by the foreground renderer, alongside the
# matching display list. The interrupt changes CHBASE immediately after
# WSYNC, before ANTIC fetches the first scanline of the new character set.
supplied_bird_first:
 pha
 txa
 pha
 tya
 pha
 lda #<supplied_bird_dli
 sta 0x206
 lda #>supplied_bird_dli
 sta 0x207
 ldx supplied_event
 lda supplied_fonts,x
 sta 0x110b
 lda supplied_delay,x
 and #7
 bne supplied_first_default
 lda supplied_color0,x
 sta 0x110c
 lda supplied_color1,x
 pha
 lda supplied_color2,x
 tay
 pla
 tax
 jmp supplied_first_wait
supplied_first_default:
 lda #170
 sta 0x110c
 ldx #236
 ldy #86
supplied_first_wait:
 lda #19
1: cmp 0xd40b
 bne 1b
 sta 0xd40a
 lda 0x110b
 sta 0xd40a
 sta 0xd409
 lda #0x3d
 sta 0xd400
 stx 0xc017
 sty 0xc018
 lda 0x110c
 sta 0xc016
 ldx supplied_event
 lda supplied_delay,x
 and #7
 tay
 beq supplied_raster_done
 # Initial font/width and three HUD-to-field color writes have already
 # consumed the first line's preparation window.
 dey
 beq supplied_raster_colors
 cpy #6
 beq supplied_raster_last
 jmp supplied_raster_wait
supplied_bird_dli:
 pha
 txa
 pha
 ldx supplied_event
 lda supplied_fonts,x
 sta 0xd40a
 sta 0xd409
 lda supplied_delay,x
 bmi supplied_raster_effect
 bne supplied_raster_delayed
 # No Y save or delay decoding may precede these three writes: the first
 # ANTIC character fetch leaves only a short color-update window.
 lda supplied_color0,x
 sta 0xc016
 lda supplied_color1,x
 sta 0xc017
 lda supplied_color2,x
 sta 0xc018
 jmp supplied_raster_zero_done
supplied_raster_effect:
 lda supplied_color2,x
 sta 0xc018
 lda supplied_color1,x
 sta 0xc017
 lda supplied_color0,x
 sta 0xc016
supplied_raster_zero_done:
 inc supplied_event
 pla
 tax
 pla
 rti
supplied_raster_delayed:
 tya
 pha
 ldy supplied_delay,x
 cpy #7
 beq supplied_raster_last
supplied_raster_wait:
 sta 0xd40a
 dey
 bne supplied_raster_wait
supplied_raster_colors:
 lda supplied_color2,x
 sta 0xc018
 lda supplied_color1,x
 sta 0xc017
 lda supplied_color0,x
 sta 0xc016
supplied_raster_done:
 inc supplied_event
 pla
 tay
 pla
 tax
 pla
 rti

# A palette change on the last scanline can meet the next font interrupt.
# Publish its successor before waiting, and write all three loaded colors
# before the next DLI arrives. No old color writes remain after a nested DLI.
supplied_raster_last:
 inc supplied_event
 dey
 dey
1: sta 0xd40a
 dey
 bne 1b
 lda supplied_color0,x
 sta 0x110d
 ldy supplied_color2,x
 lda supplied_color1,x
 tax
 lda 0x110d
 sta 0xd40a
 sta 0xd40a
 sta 0xc016
 stx 0xc017
 sty 0xc018
 pla
 tay
 pla
 tax
 pla
 rti

# Five byte arrays, two 32-event buffers, occupy unused PMG prefix RAM.
# Delay 128 selects an immediate egg palette (PF2 first); zero uses PF0 first.
# The pilot metadata at $1100..$1108 remains separate.
supplied_raster_build:
 lda back_buffer
 asl
 asl
 sta large_hit_y
 lda #0
 sta large_hit_count
 ldx large_temp
 stx large_index
supplied_raster_build_row:
 ldy large_index
 tya
 and #7
 beq supplied_raster_emit
 lda supplied_palettes,y
 bpl supplied_raster_next
supplied_raster_emit:
 tya
 and #31
 cmp #8
 bcc 1f
 cmp #16
 bcc 2f
 lda #0x30
 bne 3f
1: lda #0x18
 bne 3f
2: lda #0x20
3: clc
 adc large_hit_y
 sta supplied_fonts,x
 lda supplied_palettes,y
 bpl 4f
 pha
 and #3
 sta large_hit_count
 pla
 lsr
 lsr
 and #7
 jmp 5f
4: lda #0
5: bne 6f
 ldy large_hit_count
 cpy #1
 bne 6f
 lda #128
6: sta supplied_delay,x
 ldy large_hit_count
 lda supplied_c0,y
 sta supplied_color0,x
 lda supplied_c1,y
 sta supplied_color1,x
 lda supplied_c2,y
 sta supplied_color2,x
 inx
supplied_raster_next:
 inc large_index
 lda large_index
 and #31
 cmp #25
 bcc supplied_raster_build_row
 rts
.section .tables,"a",@progbits
supplied_c0: .byte 170,130,14
supplied_c1: .byte 236,44,44
supplied_c2: .byte 86,14,100
.section .display,"a",@progbits
supplied_dl: .word 0x1000,0x1040
