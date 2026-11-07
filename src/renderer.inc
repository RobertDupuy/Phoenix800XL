# Double-buffered ANTIC 4 renderer. Foreground tiles replace whole cells,
# as in MAME. Transparent pixels expose the background star, not older birds.
.set back_buffer,0x9a
.set front_buffer,0x9b
.set map_ptr,0xd0
.set dst_ptr,0xd2
.set src_mask,0xd4
.set src_data,0xd6
.set font_hi,0xd8
.set map_hi,0xd9
.set next_char,0xda
.set draw_index,0xdb
.set tile_index,0xdc
.set draw_flags,0xdd
.set draw_col,0xde
.set draw_variant,0xdf
.set draw_bg,0xe0
.set plot_tmp,0xe1
.set scene_pose,0xe2
.set work_due,0xe3
.set render_ready,0xe4
.set render_busy,0xe5
.set video_phase,0xe6
.set display_active,0xe7
.set fire_edge,0xe8
.set gameplay_font,0xe9
.set record_ptr,0xea
.set cache_ptr,0xec
.set tile_offset,0xee
.set cache_count,0xef
.set glyph_owner,0xb0
.set cache_epoch,0x339
.set grouped_scene,0x33a
.set grouped_last,0x33b
.set draw_row,0xf0
.set tiles_left,0xf1
.set draw_template,0xf2
.set draw_palette,0xf3
.set pending_count,0xf4
.set direct_scene,0x336
.set cow_ptr,0xf5
.set draw_id,0xf7
.set sim_updates,0x318
.set fresh_commits,0x31c
.set missed_ready,0x320
.set last_commit,0x322
.set gap_errors,0x326
.set sim_steps,0x328
.set max_chars,0x32c
.set layout_faults,0x32d
.set pending_frame,0x32e
.include "build/native-count.inc"
.section .renderer,"ax",@progbits
.global renderer_init,render_scene,clear_back,draw_bird,stamp_tile,render_complete,glyph_pointer,allocate_glyph
.section .expanded_code,"ax",@progbits
renderer_init:
 # No previous projectile footprint exists on either buffer at cold boot.
 # Column zero is outside the narrow playfield and must never be cleared.
 jsr init_projectile_footprints
 ldx #TEMPLATE_COUNT-1
initial_cache:
 lda native_cache,x
 sta 0x3000,x
 sta 0x3200,x
 dex
 cpx #255
 bne initial_cache
 lda #0
 sta cache_count
 sta cache_epoch
 ldx #127
cache_owner_init:
 sta 0x3800,x
 sta 0x3900,x
 sta 0x3a00,x
 dex
 bpl cache_owner_init
 ldx #127
static_metadata_init:
 lda #0
 sta 0x3100,x
 dex
 bpl static_metadata_init
 lda #1
 sta 0x3101
 lda large_ready
 beq renderer_fonts_needed
 lda #0
 sta large_ready
 rts
renderer_fonts_needed:
 ldx #0
renderer_font_init:
 lda native_static,x
 sta 0x2000,x
 sta 0x2400,x
 lda native_static+256,x
 sta 0x2100,x
 sta 0x2500,x
 inx
 bne renderer_font_init
 rts
render_scene:
 jmp campaign_render
.section .renderer,"ax",@progbits
render_scene_regular:
 lda large_mode
 cmp #3
 bne 8f
 jmp boss_render
8:
 lda large_mode
 beq render_small_scene
 jmp large_render
render_small_scene:
 lda front_buffer
 eor #1
 sta back_buffer
 tax
 lda #0
 sta large_buffer,x
 txa
 asl
 asl
 clc
 adc #0x20
 sta font_hi
 clc
 adc #8
 sta map_hi
 jsr clear_back
 # Each display buffer keeps its own template -> glyph cache and reverse
 # ownership. Epoch tags protect glyphs already used by this scene.
 lda #0
 sta cache_ptr
 sta glyph_owner
 lda back_buffer
 clc
 adc #0x38
 sta glyph_owner+1
 lda back_buffer
 asl
 clc
 adc #0x30
 sta cache_ptr+1
 inc cache_epoch
 bne cache_epoch_ready
 lda #0
 ldx #127
cache_epoch_clear:
 sta 0x3a00,x
 dex
 bpl cache_epoch_clear
 inc cache_epoch
cache_epoch_ready:
 lda #82
 sta next_char
 sta cache_count
 jsr reserve_shield_glyphs
 jsr xl_draw_scenery
 lda #1
 sta direct_scene
 lda #0
 sta grouped_scene
 sta draw_index
 sta pending_count
 jsr draw_coincident_birds
 bcs scene_all_done
scene_bird:
 lda state
 cmp #1
 beq scene_live
 cmp #3
 bne scene_all_done
 lda death_timer
 cmp #33
 bcc scene_all_done
scene_live:
 ldx draw_index
 lda display_enemy_on,x
 beq scene_next
 jsr draw_bird
scene_next:
 inc draw_index
 lda draw_index
 cmp #16
 bcc scene_bird
scene_all_done:
 lda #0
 sta grouped_scene
 jsr draw_bursts
 jsr draw_bonus
 jsr draw_explosion
 jsr resolve_tiles
 jsr draw_shield
 jsr draw_soft_bomb
 jsr draw_soft_shot
 jsr draw_second_shot
 lda next_char
 cmp max_chars
 bcc render_complete
 sta max_chars
render_complete:
 rts
.macro clear_cached cols,rows,lo,hi
 ldx #15
.Lold_loop\@:
 lda \rows,x
 cmp #127
 beq .Lold_next\@
 sta draw_row
 lda \cols,x
 sta draw_col
 lda \lo,x
 sta map_ptr
 lda \hi,x
 sta map_ptr+1
 lda draw_col
 cmp #32
 bcs .Lold_slow\@
 lda draw_row
 cmp #24
 bcs .Lold_slow\@
 lda #0
 .irp off,0,1,32,33
 ldy #\off
 sta (map_ptr),y
 .endr
 jmp .Lold_mark\@
.Lold_slow\@:
 jsr clear_clipped
.Lold_mark\@:
 lda #127
 sta \rows,x
.Lold_next\@:
 dex
 bpl .Lold_loop\@
.endm
clear_back:
 jsr clear_shield
 jsr clear_soft_bomb
 jsr clear_bursts
 jsr clear_bonus
 ldx back_buffer
 lda 0x332,x
 cmp #3
 bne clear_effect_done
 lda 0x334,x
 clc
 adc #<(player_explosion_row*32-4)
 sta map_ptr
 lda map_hi
 adc #1
 sta map_ptr+1
 ldx #25-player_explosion_row
clear_effect_row:
 lda #0
 ldy #0
 .rept 16
 sta (map_ptr),y
 iny
 .endr
 clc
 lda map_ptr
 adc #32
 sta map_ptr
 bcc 1f
 inc map_ptr+1
1:
 dex
 bne clear_effect_row
clear_effect_done:
 ldx back_buffer
 lda state
 sta 0x332,x
 lda explosion_left
 sta 0x334,x
 lda back_buffer
 beq clear_buffer0
 clear_cached 0x540,0x560,0x5a0,0x5e0
 jmp seed_stars
clear_buffer0:
 clear_cached 0x500,0x520,0x580,0x5c0
 jmp seed_stars
.include "build/star-draw.inc"
clear_clipped:
 stx draw_index
 lda #0
 sta tile_index
clear_cells:
 ldx tile_index
 jsr clip_tile
 bcs clear_skip
 lda #0
 sta (map_ptr),y
clear_skip:
 inc tile_index
 lda tile_index
 cmp #4
 bcc clear_cells
 ldx draw_index
 rts
row_pointer:
 lda draw_row
 clc
 adc #4
 tax
 lda row_lo,x
 clc
 adc draw_col
 sta map_ptr
 lda row_hi,x
 adc map_hi
 sta map_ptr+1
 rts
clip_tile:
 lda tile_rows,x
 clc
 adc draw_row
 cmp #25
 bcs clipped_tile
 lda tile_cols,x
 clc
 adc draw_col
 cmp #33
 bcs clipped_tile
 ldy tile_offsets,x
 clc
 rts
clipped_tile:
 sec
 rts
draw_bird:
 lda display_enemy_shape,x
 tay
 lda shape_ids,y
 cmp #255
 bne valid_shape
 inc layout_faults
 rts
valid_shape:
 asl
 asl
 sta draw_id
 lda display_enemy_x,x
 lsr
 lsr
 lsr
 clc
 adc #7
 sta draw_col
 lda display_enemy_y,x
 lsr
 lsr
 lsr
 sec
 sbc #4
 sta draw_row
 lda back_buffer
 beq save_zero
 lda draw_row
 sta 0x560,x
 lda draw_col
 sta 0x540,x
 jmp saved_bounds
save_zero:
 lda draw_row
 sta 0x520,x
 lda draw_col
 sta 0x500,x
saved_bounds:
 jsr row_pointer
 ldx draw_index
 lda back_buffer
 beq save_ptr0
 lda map_ptr
 sta 0x5a0,x
 lda map_ptr+1
 sta 0x5e0,x
 jmp save_ptr_done
save_ptr0:
 lda map_ptr
 sta 0x580,x
 lda map_ptr+1
 sta 0x5c0,x
save_ptr_done:
 lda #0
 sta draw_flags
 lda draw_col
 cmp #32
 bcs drawing_clipped
 lda draw_row
 cmp #24
 bcs drawing_clipped
 inc draw_flags
 lda grouped_scene
 bne drawing_clipped
 lda state
 cmp #3
 beq drawing_clipped
 jmp draw_bird_fast
drawing_clipped:
 lda #0
 sta tile_index
bird_tile:
 lda grouped_scene
 beq bird_regular_tile
 ldx tile_index
 lda 0x600,x
 jmp bird_tile_loaded
bird_regular_tile:
 ldx draw_id
 lda native_shapes,x
bird_tile_loaded:
 beq bird_tile_next
 sta draw_template
 ldx tile_index
 lda draw_flags
 bne tile_inside
 jsr clip_tile
 bcs bird_tile_next
tile_inside:
 lda state
 cmp #3
 bne tile_visible
 lda tile_rows,x
 clc
 adc draw_row
 cmp #player_explosion_row
 bcc tile_visible
 lda tile_cols,x
 clc
 adc draw_col
 sec
 sbc explosion_left
 cmp #16
 bcc bird_tile_next
tile_visible:
 ldy tile_offsets,x
 ldx draw_template
 jsr stamp_tile
bird_tile_next:
 inc draw_id
 inc tile_index
 lda tile_index
 cmp #4
 bcc bird_tile
 rts
# Direct stamps preserve only the background star under overlapping cells.
# Resident templates are reused across frames; no mutable glyph can be evicted
# after any cell in the current scene has referenced it.
stamp_tile:
 lda large_mode
 beq 9f
 jmp large_stamp_native
9: lda large_mode
 beq stamp_effect_marked
 lda draw_row
 cmp #12
 bcs stamp_effect_marked
 lda #1
 sta large_upper_effects
stamp_effect_marked:
 sty tile_offset
 lda #0
 sta draw_palette
 lda (map_ptr),y
 beq stamp_plain
 and #127
 tax
 lda large_mode
 beq stamp_star_tag
 cpx #2
 bcc stamp_star_tag
 cpx #66
 bcs stamp_star_tag
 lda draw_row
 cmp #12
 bcc stamp_star_tag
 txa
 ora #128
 tax
stamp_star_tag:
 lda 0x3100,x
 beq stamp_plain
 lda #1
 sta (map_ptr),y
 ldx draw_template
 jmp fresh_star
stamp_plain:
 ldx draw_template
 bne blank_tile
 lda #0
 sta (map_ptr),y
 rts
.global resolve_tiles,commit_tile
resolve_tiles:
 rts
commit_tile:
 jmp stamp_tile
blank_tile:
 ldx draw_template
 lda large_mode
 bne lookup_dynamic_cache
 lda native_cache,x
 beq lookup_dynamic_cache
 and #127
 ldy tile_offset
 sta (map_ptr),y
 rts
lookup_dynamic_cache:
 ldy draw_template
 lda (cache_ptr),y
 beq uncached_tile
 ldy tile_offset
 sta (map_ptr),y
 and #127
 tax
 cpx #64
 bcc cached_tile_done
 lda 0x3a00,x
 cmp cache_epoch
 beq cached_tile_tagged
 lda cache_epoch
 sta 0x3a00,x
 inc next_char
cached_tile_tagged:
 lda #0
 sta 0x3100,x
cached_tile_done:
 rts
uncached_tile:
 jsr allocate_glyph
 bcc 2f
 rts
2:
 lda plot_tmp
 ora draw_palette
 ldy draw_template
 sta (cache_ptr),y
 ldy plot_tmp
 lda draw_template
 sta (glyph_owner),y
 ldx draw_template
 .irp row,0,1,2,3,4,5,6,7
 ldy #\row
 lda native_tiles+(TEMPLATE_COUNT*\row),x
 sta (dst_ptr),y
 .endr
 rts
fresh_star:
 lda draw_template
 beq 1f
 # A star cell is wholly behind foreground artwork, never recoloring it.
 jmp blank_tile
1: rts

# Used by both the video interrupt and foreground; all banks map this code.
boss_intro_pending:
 lda boss_status
 cmp #1
 beq 1f
 lda boss_entrance_shown
 rts
1: lda #1
 rts
allocate_glyph:
 ldx cache_count
allocate_scan:
 cpx #128
 bcc allocate_check
 inc layout_faults
 sec
 rts
allocate_check:
 lda 0x3a00,x
 cmp cache_epoch
 bne allocate_ok
 inx
 jmp allocate_scan
allocate_ok:
 stx plot_tmp
 inx
 stx cache_count
 ldy plot_tmp
 lda (glyph_owner),y
 beq owner_cleared
 tax
 lda #0
 sta (glyph_owner),y
 txa
 tay
 lda #0
 sta (cache_ptr),y
owner_cleared:
 ldx plot_tmp
 lda cache_epoch
 sta 0x3a00,x
 lda #0
 sta 0x3100,x
 cpx #100
 bcc allocate_marked
 lda back_buffer
 beq allocate_buffer_zero
 txa
 ora #128
 tax
allocate_buffer_zero:
 lda #0
 sta 0x3b00,x
allocate_marked:
 inc next_char
 lda plot_tmp
 ldy tile_offset
 ora draw_palette
 sta (map_ptr),y
 lda plot_tmp
 jsr glyph_pointer
 clc
 rts
# Reserve this frame's shield codes before any ordinary glyph can use them.
reserve_shield_glyphs:
 lda state
 cmp #1
 bne reserve_shield_done
 lda shield_pose
 cmp #255
 beq reserve_shield_done
 tax
 lda shield_map_offsets,x
 tax
 stx draw_id
 lda #16
 sta tiles_left
reserve_shield_next:
 ldx draw_id
 lda shield_maps,x
 and #127
 beq reserve_shield_skip
 tay
 tax
 lda cache_epoch
 sta 0x3a00,x
 lda (glyph_owner),y
 beq reserve_shield_skip
 tax
 lda #0
 sta (glyph_owner),y
 txa
 tay
 lda #0
 sta (cache_ptr),y
reserve_shield_skip:
 inc draw_id
 dec tiles_left
 bne reserve_shield_next
reserve_shield_done:
 rts
glyph_pointer:
 tax
 lda glyph_lo,x
 sta dst_ptr
 lda glyph_hi,x
 ora font_hi
 sta dst_ptr+1
 rts
.section .text,"ax",@progbits
.global playfield_dli,playfield_dli_done
playfield_dli:
 pha
 lda gameplay_font
 sta 0xd40a
 sta 0xd409
 lda #0x3d
 sta 0xd400
 lda playfield_c0
 sta 0xd016
 lda playfield_c1
 sta 0xd017
 lda gameplay_color
 sta 0xd018
 lda large_shown
 bne 2f
 lda #<shield_palette_dli
 sta 0x206
 lda #>shield_palette_dli
 sta 0x207
 jmp playfield_dli_done
2:
1: jsr pilot_start
 lda #<large_lower_dli
 sta 0x206
 lda #>large_lower_dli
 sta 0x207
playfield_dli_done:
 pla
 rti
.section .tables,"a",@progbits
shape_ids: .incbin "build/shape-ids.bin"
.section .native_data,"a",@progbits
native_shapes: .incbin "build/native-shapes.bin"
.section .tables,"a",@progbits
native_static: .incbin "build/native-static.bin"
native_cache: .incbin "build/native-cache.bin"
native_flags: .incbin "build/native-flags.bin"
tile_offsets: .byte 0,1,32,33
tile_rows: .byte 0,0,1,1
tile_cols: .byte 0,1,0,1
row_lo:
 .set v,-4
 .rept 32
 .byte ((v*32-4)&255)
 .set v,v+1
 .endr
row_hi:
 .set v,-4
 .rept 32
 .byte (((v*32-4)>>8)&255)
 .set v,v+1
 .endr
star_glyph_data: .byte 0,0,0,12,0,0,0,0

glyph_lo:
 .set g,0
 .rept 128
 .byte (g*8)&255
 .set g,g+1
 .endr
glyph_hi:
 .set g,0
 .rept 128
 .byte g>>5
 .set g,g+1
 .endr
.section .native_data,"a",@progbits
.balign 256
native_tiles: .incbin "build/native-tiles.bin"

.section .renderer,"ax",@progbits

# Complete on-screen birds use four bounded direct stamps. Edge clipping and
# death-window masking keep the original checked path above.
.section .shield_code,"ax",@progbits
.global draw_bird_fast
draw_bird_fast:
 .set cell,0
 .irp offset,0,1,32,33
 ldx draw_id
 lda native_shapes+cell,x
 beq 1f
 sta draw_template
 tax
 ldy #\offset
 jsr stamp_tile
1:
 .set cell,cell+1
 .endr
 rts

.section .shield_code,"ax",@progbits
init_projectile_footprints:
 lda #127
 .irp oldrow,0x6f2,0x6f3,0x6fa,0x6fb,0x722,0x723,0x726,0x727
 sta \oldrow
 .endr
 rts

.section .shield_code,"ax",@progbits
# If all live birds share one character anchor, only their final four cells
# are visible. Resolve those four cells from back to front; keep every enemy
# in simulation and in the arcade collision map.
draw_coincident_birds:
 lda state
 cmp #1
 beq grouped_find_last
 clc
 rts
grouped_find_last:
 ldx #15
grouped_find:
 lda display_enemy_on,x
 bne grouped_found
 dex
 bpl grouped_find
 clc
 rts
grouped_found:
 stx grouped_last
 lda display_enemy_x,x
 and #248
 sta draw_col
 lda display_enemy_y,x
 and #248
 sta draw_row
 dex
 bmi grouped_not_uniform
grouped_compare:
 lda display_enemy_on,x
 beq grouped_compare_next
 lda display_enemy_x,x
 and #248
 cmp draw_col
 bne grouped_not_uniform
 lda display_enemy_y,x
 and #248
 cmp draw_row
 bne grouped_not_uniform
grouped_compare_next:
 dex
 bpl grouped_compare
 lda #0
 sta tile_index
grouped_cell:
 ldx grouped_last
grouped_cell_search:
 lda display_enemy_on,x
 beq grouped_cell_next
 stx draw_index
 ldy display_enemy_shape,x
 lda shape_ids,y
 asl
 asl
 clc
 adc tile_index
 tay
 lda native_shapes,y
 bne grouped_cell_found
 ldx draw_index
grouped_cell_next:
 dex
 bpl grouped_cell_search
 lda #0
grouped_cell_found:
 ldx tile_index
 sta 0x600,x
 inc tile_index
 lda tile_index
 cmp #4
 bcc grouped_cell
 lda #1
 sta grouped_scene
 ldx grouped_last
 stx draw_index
 jsr draw_bird
 sec
 rts
grouped_not_uniform:
 clc
 rts
