.include "build/main-symbols.inc"
.include "src/campaign-defs.inc"
.section .boss_code,"ax",@progbits
.global boss_entries
boss_entries:
 jmp campaign_select
 jmp boss_init
 jmp boss_tick
 jmp boss_background
 jmp wipe_render
 jmp campaign_positions
 jmp boss_projectile
 jmp boss_foreground_glyph
 jmp boss_death_picture
 jmp large_bomb_spawn
campaign_select:
 lda wave
 sec
 sbc #1
 ldx #0
1: cmp #5
 bcc 2f
 sec
 sbc #5
 inx
 bne 1b
2: sta cycle_stage
 txa
 asl
 asl
 asl
 asl
 sta cycle_round
 ldy #3
 cpx #1
 bcc 8f
 iny
 cpx #2
 bcc 8f
 iny
8: sty bomb_limit
 ldx cycle_stage
 lda campaign_phases,x
 ora cycle_round
 sta level_round
 lda #0
 sta boss_status
 sta boss_entrance_shown
 sta campaign_advance
 rts
campaign_positions:
 lda level_round
 lsr
 and #15
 tax
 lda boss_position_ptrs,x
 tay
 ldx #0
1: lda boss_positions,y
 sta raw_enemy_x,x
 iny
 lda boss_positions,y
 sta raw_enemy_y,x
 iny
 inx
 cpx #16
 bne 1b
 lda cycle_stage
 cmp #4
 bne 3f
 lda #escort_population
 sta aliens_left
 lda #0
 ldx #15
2: sta enemy_on,x
 sta display_enemy_on,x
 dex
 cpx #escort_population-1
 bne 2b
3: rts
boss_init:
 lda #255
 ldx #0
10:
 sta 0x3900,x
 sta 0x3a00,x
 sta 0x3b00,x
 inx
 bne 10b
 lda #0
 sta boss_cache_epoch
 ldx #127
11:
 sta 0x3c00,x
 sta 0x3c80,x
 sta 0x3d00,x
 dex
 bpl 11b
 lda #3
 sta large_mode
 lda #1
 sta boss_status
 sta boss_entrance_shown
 lda #120
 sta boss_timer
 lda #113
 sta boss_scroll
 lda #0
 sta boss_anim
 sta boss_pilot
 sta boss_score_pending
 lda #255
 ldx #5
8: sta boss_atlas_phase,x
 dex
 bpl 8b
 lda #0
 sta large_buffer
 sta large_buffer+1
 sta entrance_timer
 sta entrance_handoff
 sta wave_wait
 sta burst_count
 sta burst_count+1
 sta burst_count+2
 sta bonus_count
 sta bonus_count+1
 ldx #9
7: sta boss_dirty_rows,x
 dex
 bpl 7b
 ldx #255
9: sta 0x1200,x
 dex
 cpx #255
 bne 9b
 ldx #233
1: lda boss_initial,x
 sta boss_body,x
 dex
 cpx #255
 bne 1b
 rts
boss_tick:
 lda boss_status
 cmp #1
 bne .Lfar1
 jmp boss_entry_tick
.Lfar1:
 cmp #3
 bcc .Lfar2
 jmp boss_end_tick
.Lfar2:
 jsr boss_drop_bomb
 # Arcade 24C4 runs on alternate logical ticks.
 lda phase
 and #1
 bne .Lfar3
 jmp boss_tick_done
.Lfar3:
 lda boss_anim
 and #15
 bne 1f
 lda boss_scroll
 cmp #160
 bcc 1f
 dec boss_scroll
1: inc boss_anim
 lda boss_anim
 and #3
 bne .Lfar4
 jmp boss_rotate
.Lfar4:
 lda #1
 sta boss_dirty_rows
 sta boss_dirty_rows+1
 sta boss_dirty_rows+2
 sta boss_dirty_rows+3
 inc boss_pilot
 lda boss_pilot
 and #7
 asl
 asl
 asl
 tax
 ldy #12
 .irp off,0,26,52,78
 lda boss_pilot_shapes,x
 sta boss_body+\off,y
 lda #1
 sta 0x1200+\off,y
 inx
 .endr
 iny
 .irp off,0,26,52,78
 lda boss_pilot_shapes,x
 sta boss_body+\off,y
 lda #1
 sta 0x1200+\off,y
 inx
 .endr
boss_tick_done:
 rts
boss_entry_tick:
 dec boss_scroll
 dec boss_timer
 beq .Lfar5
 jmp boss_tick_done
.Lfar5:
 lda #2
 sta boss_status
 lda #100
 sta raw_ship_x
 sta video_ship_x
 lda #126
 sta ship_x
 rts
boss_rotate:
 lda #1
 sta boss_dirty_rows+4
 lda boss_body+104+21
 sta boss_t0
 ldx #4
1: lda boss_t0
 and #3
 asl
 asl
 sta boss_t1
 lda boss_body+104,x
 sta boss_t0
 and #12
 lsr
 lsr
 ora boss_t1
 ora #96
 sta boss_body+104,x
 lda #1
 sta 0x1200+104,x
 inx
 cpx #22
 bne 1b
 rts
boss_end_tick:
 dec boss_timer
 lda boss_status
 cmp #4
 bne .Lfar6
 jmp boss_award_tick
.Lfar6:
 lda boss_timer
 cmp #32
 bne 1f
 # Original 240A: rotated scroll plus round, BCD adjusted, capped at 9000.
 lda boss_scroll
 clc
 adc #96
 lsr
 bcc 2f
 ora #128
2: clc
 adc cycle_round
 bcs 3f
 cmp #144
 bcc 4f
3: lda #144
4: sta boss_t0
 and #15
 cmp #10
 bcc 5f
 lda boss_t0
 clc
 adc #6
 sta boss_t0
5: lda boss_t0
 lsr
 lsr
 lsr
 lsr
 sta boss_award
 lda boss_t0
 and #15
 sta boss_award_low
 lda #1
 sta boss_score_pending
1: lda boss_timer
 beq .Lfar7
 jmp boss_tick_done
.Lfar7:
 lda #4
 sta boss_status
 lda #64
 sta boss_timer
 lda g_sound_b
 and #63
 ora #128
 sta g_sound_b
 lda #0
 sta arcade_clock+1
 sta bird_elapsed
 rts
boss_award_tick:
 lda boss_timer
 and #1
 beq 1f
 dec boss_scroll
1: lda boss_timer
 beq .Lfar8
 jmp boss_tick_done
.Lfar8:
 lda #1
 sta campaign_advance
 rts
boss_projectile:
 lda boss_status
 cmp #2
 beq .Lfar9
 jmp boss_hit_done
.Lfar9:
 lda shot_on
 bne .Lfar10
 jmp boss_hit_done
.Lfar10:
 lda raw_shot_x
 lsr
 lsr
 lsr
 sec
 sbc #1
 cmp #26
 bcc .Lfar11
 jmp boss_hit_done
.Lfar11:
 sta boss_c
 # Original collision uses character row, then adds scroll in whole rows.
 lda raw_shot_y
 lsr
 lsr
 lsr
 sta boss_t0
 lda boss_scroll
 lsr
 lsr
 lsr
 clc
 adc boss_t0
 and #31
 sec
 sbc #6
 cmp #9
 bcc .Lfar12
 jmp boss_hit_done
.Lfar12:
 sta boss_collision_row
 tax
 lda boss_row_offsets,x
 clc
 adc boss_c
 tax
 lda boss_body,x
 sta boss_t0
 and #252
 cmp #76
 bne .Lfar13
 jmp boss_hit_armor
.Lfar13:
 lda boss_t0
 and #240
 cmp #96
 bne .Lfar14
 jmp boss_hit_belt
.Lfar14:
boss_hit_done:
 rts
boss_hit_armor:
 ldy boss_collision_row
 lda #1
 sta boss_dirty_rows,y
 dey
 bmi 7f
 sta boss_dirty_rows,y
7: lda #1
 sta 0x1200,x
 dec boss_body,x
 lda boss_body,x
 cmp #75
 beq .Lfar15
 jmp boss_consume
.Lfar15:
 lda #0
 sta boss_body,x
 txa
 sec
 sbc #26
 tax
 lda boss_body,x
 cmp #94
 beq .Lfar16
 jmp boss_consume
.Lfar16:
 lda #79
 sta boss_body,x
 lda #1
 sta 0x1200,x
boss_consume:
 lda #0
 sta shot_on
 lda #5
 sta audio_impact_count
 inc boss_hits
 bne 1f
 inc boss_hits+1
1: rts
boss_hit_belt:
 lda #0
 sta shot_on
 lda raw_shot_x
 and #4
 bne .Lfar17
 jmp boss_hit_left
.Lfar17:
 lda boss_t0
 and #3
 cmp #1
 bne .Lfar18
 jmp boss_core_gate
.Lfar18:
 lda boss_t0
 and #15
 ora #16
 tay
 beq .Lfar19
 jmp boss_change_belt
.Lfar19:
boss_hit_left:
 lda boss_t0
 and #12
 cmp #4
 bne .Lfar20
 jmp boss_core_gate
.Lfar20:
 lda boss_t0
 and #15
 tay
boss_change_belt:
 lda #1
 sta 0x1200,x
 lda boss_damage,y
 sta boss_body,x
 jmp boss_consume
boss_core_gate:
 txa
 sec
 sbc #26
 tax
 lda boss_body,x
 and #240
 cmp #112
 beq .Lfar21
 jmp boss_hit_done
.Lfar21:
 lda #3
 sta boss_status
 lda #96
 sta boss_timer
 lda boss_scroll
 and #248
 sta boss_scroll
 lda #32
 sec
 sbc boss_scroll
 lsr
 lsr
 lsr
 sta boss_award_row
 lda #64
 sta audio_death_pending
 inc boss_victories
 bne 1f
 inc boss_victories+1
1: lda #0
 ldx #15
2: sta enemy_on,x
 sta display_enemy_on,x
 dex
 bpl 2b
 sta bomb_on
 sta bomb_on+1
 sta bomb_on+2
 sta bomb_on+3
 sta bomb_on+4
 sta shot_on
 sta second_on
 rts
# A full-screen background is rebuilt with shared immutable glyphs per region.
# A pair cache handles exact one-pixel scroll without allocating per-cell art.
boss_background:
 lda #0
 ldx #5
12: sta boss_free_cursor,x
 dex
 bpl 12b
 inc boss_cache_epoch
 bne 10f
 inc boss_cache_epoch
 lda #0
 ldx #127
11:
 sta 0x3c00,x
 sta 0x3c80,x
 sta 0x3d00,x
 dex
 bpl 11b
10:
 lda front_buffer
 eor #1
 sta back_buffer
 tax
 lda large_buffer,x
 sta large_old_mode
 lda #3
 sta large_buffer,x
 lda back_buffer
 asl
 asl
 clc
 adc #40
 sta map_hi
 sta map_ptr+1
 lda #0
 ldx #0
 ldy back_buffer
 beq .Latlasfar1
 jmp boss_map_one
.Latlasfar1:
boss_map_zero:
 .set map_row,0
 .rept 25
 sta 0x2800+map_row*32,x
 .set map_row,map_row+1
 .endr
 inx
 cpx #32
 beq .Latlasfar2
 jmp boss_map_zero
.Latlasfar2:
 jmp boss_map_ready
boss_map_one:
 .set map_row,0
 .rept 25
 sta 0x2c00+map_row*32,x
 .set map_row,map_row+1
 .endr
 inx
 cpx #32
 beq .Latlasfar3
 jmp boss_map_one
.Latlasfar3:
boss_map_ready:
 lda boss_scroll
 and #7
 sta boss_fine
 lda #64
 sta lg_next
 sta lg_next+1
 sta lg_next+2
 lda #255
 sta boss_prev_region
 ldx #2
atlas_zero:
 lda lg_font_bases,x
 sta dst_ptr+1
 lda back_buffer
 asl
 asl
 clc
 adc dst_ptr+1
 sta dst_ptr+1
 lda #0
 sta dst_ptr
 ldy #15
1: sta (dst_ptr),y
 dey
 bpl 1b
 lda #192
 ldy #11
 sta (dst_ptr),y
 dex
 bpl atlas_zero
 lda #0
 sta draw_row
 sta draw_palette
 lda boss_status
 cmp #4
 bcc 8f
 jsr boss_award_stars
 rts
8:
 jsr boss_seed_stars
 lda boss_status
 cmp #4
 bcc 1f
 rts
1: cmp #3
 beq .Latlasfar4
 jmp boss_bg_rows
.Latlasfar4:
 lda boss_timer
 cmp #32
 bcc .Latlasfar5
 jmp boss_bg_rows
.Latlasfar5:
 rts
boss_bg_rows:
 lda boss_status
 cmp #1
 bne 8f
 lda boss_scroll
 cmp #49
 bcc 8f
 cmp #128
 bcs 8f
 lda #120
 sec
 sbc boss_scroll
 sta boss_t0
 lda draw_row
 asl
 asl
 asl
 clc
 adc #32
 cmp boss_t0
 bcc 8f
 jmp boss_bg_nextrow
8:
 lda draw_row
 asl
 asl
 asl
 clc
 adc #32
 clc
 adc boss_scroll
 sec
 sbc #48
 lsr
 lsr
 lsr
 sta boss_r
 cmp #31
 bne 1f
 lda #255
 sta boss_r
 jmp boss_bg_drawrow
1: cmp #9
 bcs .Latlasfar6
 jmp boss_bg_drawrow
.Latlasfar6:
 jmp boss_bg_nextrow
boss_bg_drawrow:
 lda draw_row
 lsr
 lsr
 lsr
 cmp #3
 bcc 1f
 lda #2
1: sta boss_region
 cmp boss_prev_region
 beq atlas_loaded
 sta boss_prev_region
 tax
 jsr boss_cache_select
 lda back_buffer
 asl
 clc
 adc back_buffer
 clc
 adc boss_region
 tax
 lda boss_fine
 cmp boss_atlas_phase,x
 beq atlas_loaded
 sta boss_atlas_phase,x
 lda #255
 ldy #63
7: sta (glyph_owner),y
 dey
 bpl 7b
 ldx boss_region
 jsr boss_load_atlas
atlas_loaded:
 ldx boss_region
 lda lg_font_bases,x
 sta font_hi
 lda back_buffer
 asl
 asl
 clc
 adc font_hi
 sta font_hi
 lda #8
 sta draw_col
 jsr row_pointer
 lda boss_fine
 asl
 tax
 lda boss_map_ptrs,x
 sta boss_baseptr
 lda boss_map_ptrs+1,x
 sta boss_baseptr+1
 ldx boss_r
 inx
 lda boss_row_offsets,x
 clc
 adc boss_baseptr
 sta boss_baseptr
 bcc 1f
 inc boss_baseptr+1
1: ldx boss_r
 cpx #255
 bne 2f
 lda #0
 beq 3f
2: lda boss_row_offsets,x
3: sta boss_offset
 .set cell,0
 .rept 26
 ldy #cell
 lda (boss_baseptr),y
 sta (map_ptr),y
 .set cell,cell+1
 .endr
 ldx boss_r
 cpx #255
 bne 7f
 lda boss_dirty_rows
 jmp 8f
7: lda boss_dirty_rows,x
 ora boss_dirty_rows+1,x
8: bne 9f
 jmp boss_bg_nextrow
9: ldx boss_offset
 lda boss_r
 cmp #255
 beq 20f
 jmp boss_dirty_normal
20:
 .set cell,0
 .rept 26
 lda 0x1200,x
 beq 19f
 ldy #cell
 jsr boss_dirty_cell
19: inx
 .set cell,cell+1
 .endr
 jmp boss_bg_nextrow
boss_dirty_normal:
 .set cell,0
 .rept 26
 lda 0x1200,x
 ora 0x1200+26,x
 beq 19f
 ldy #cell
 jsr boss_dirty_cell
19: inx
 .set cell,cell+1
 .endr
 jmp boss_bg_nextrow
boss_dirty_cell:
 stx boss_offset
 sty boss_c
 tya
 clc
 adc map_ptr
 sta map_ptr
 bcc 1f
 inc map_ptr+1
1:
 ldy boss_r
 cpy #255
 beq boss_bg_top
 lda boss_body,x
 sta boss_upper
 cmp boss_initial,x
 bne boss_bg_changed
 lda boss_fine
 bne .Ldirtyfar1
 jmp boss_bg_nextcell
.Ldirtyfar1:
 cpy #8
 bcc .Ldirtyfar2
 jmp boss_bg_nextcell
.Ldirtyfar2:
 lda boss_body+26,x
 cmp boss_initial+26,x
 bne .Ldirtyfar3
 jmp boss_bg_nextcell
.Ldirtyfar3:
 jmp boss_bg_changed
boss_bg_top:
 lda #0
 sta boss_upper
 lda boss_body,x
 cmp boss_initial,x
 bne .Latlasfar12
 jmp boss_bg_nextcell
.Latlasfar12:
 sta boss_lower
 jmp boss_bg_patch
boss_bg_changed:
 lda #0
 ldy boss_r
 cpy #8
 bcs 1f
 lda boss_body+26,x
1: sta boss_lower
boss_bg_patch:
 lda boss_upper
 ora boss_lower
 bne 1f
 ldy #0
 sta (map_ptr),y
 jmp boss_bg_nextcell
1: lda boss_upper
 asl
 asl
 clc
 adc boss_upper
 eor boss_lower
 and #63
 tay
boss_patch_find:
 lda (glyph_owner),y
 cmp boss_upper
 bne boss_patch_probe
 tya
 ora #64
 tay
 lda (glyph_owner),y
 cmp boss_lower
 bne boss_patch_lower_miss
 tya
 and #63
 tay
boss_patch_reuse:
 lda boss_cache_epoch
 sta (cache_ptr),y
 tya
 clc
 adc #64
 ldy #0
 sta (map_ptr),y
 jmp boss_bg_nextcell
boss_patch_lower_miss:
 tya
 and #63
 tay
boss_patch_probe:
 lda (cache_ptr),y
 cmp boss_cache_epoch
 bne boss_patch_new
 iny
 tya
 and #63
 tay
 jmp boss_patch_find
boss_patch_new:
 sty boss_hash
 lda boss_cache_epoch
 sta (cache_ptr),y
 lda boss_upper
 sta (glyph_owner),y
 tya
 ora #64
 tay
 lda boss_lower
 sta (glyph_owner),y
 lda boss_hash
 clc
 adc #64
 ldy #0
 sta (map_ptr),y
 tax
 lda glyph_lo,x
 sta dst_ptr
 lda glyph_hi,x
 ora font_hi
 sta dst_ptr+1
 lda boss_fine
 asl
 asl
 asl
 sta boss_t0
 lda boss_upper
 bne 1f
 lda #95
1: and #63
 tax
 lda boss_half_lo,x
 ora boss_t0
 sta src_data
 lda boss_half_hi,x
 sta src_data+1
 lda boss_lower
 bne 1f
 lda #95
1: and #63
 tax
 lda boss_half_lo,x
 ora boss_t0
 sta boss_src2
 lda boss_half_hi,x
 ora #16
 sta boss_src2+1
 jsr boss_copy_tile
boss_bg_nextcell:
 sec
 lda map_ptr
 sbc boss_c
 sta map_ptr
 bcs 1f
 dec map_ptr+1
1: ldx boss_offset
 rts
boss_bg_nextrow:
 inc draw_row
 lda draw_row
 cmp #25
 bcc .Latlasfar14
 jmp boss_bg_done
.Latlasfar14:
 jmp boss_bg_rows
boss_bg_done:
 rts
# Copy-on-write foreground composition; map/shared background stays immutable.
boss_foreground_glyph:
 sty tile_offset
 lda (map_ptr),y
 and #127
 sta boss_t0
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
 ldx boss_t0
 lda glyph_lo,x
 sta boss_bgptr
 lda glyph_hi,x
 ora font_hi
 sta boss_bgptr+1
 lda #0
 ldy tile_offset
 sta (map_ptr),y
 ldx draw_template
 lda native_flags,x
 sta draw_palette
 jsr large_cell_glyph
 # Native tile bytes were copied into bank one in the same row-major format.
 .irp row,0,1,2,3,4,5,6,7
 ldx draw_template
 lda boss_native+(TEMPLATE_COUNT*\row),x
 sta boss_t1
 lsr
 ora boss_t1
 and #85
 sta boss_t2
 asl
 ora boss_t2
 eor #255
 ldy #\row
 and (boss_bgptr),y
 ora boss_t1
 sta (dst_ptr),y
 .endr
 rts
wipe_render:
 # Same display layout as the preceding frame; write radius masks over it.
 lda wipe_timer
 lsr
 sta boss_t0
 cmp #14
 bcc 1f
 sec
 sbc #14
 sta boss_t0
1: lda #0
 sta draw_row
wipe_row:
 lda draw_row
 lsr
 lsr
 lsr
 cmp #3
 bcc 1f
 lda #2
1: tax
 lda large_mode
 beq 2f
 lda lg_font_bases,x
 bne 3f
2: lda #32
3: sta font_hi
 lda back_buffer
 asl
 asl
 clc
 adc font_hi
 sta dst_ptr+1
 lda #248
 sta dst_ptr
 inc dst_ptr+1
 inc dst_ptr+1
 inc dst_ptr+1
 ldy #7
4: lda boss_wipe_glyph,y
 sta (dst_ptr),y
 dey
 bpl 4b
 lda #7
 sta draw_col
 jsr row_pointer
 lda map_ptr
 sta src_data
 lda map_ptr+1
 sec
 sbc map_hi
 clc
 adc #>boss_wipe_radius
 sta src_data+1
 ldy #0
wipe_cell:
 lda (src_data),y
 cmp #255
 bne .Lfar35
 jmp wipe_next
.Lfar35:
 cmp boss_t0
 bcc 1f
 beq 1f
 jmp wipe_next
1: lda #127
 ldx wipe_timer
 cpx #28
 bcc 2f
 lda #0
2: sta (map_ptr),y
wipe_next:
 iny
 cpy #26
 bcs .Lfar36
 jmp wipe_cell
.Lfar36:
 inc draw_row
 lda draw_row
 cmp #25
 bcs .Lfar37
 jmp wipe_row
.Lfar37:
 rts
boss_death_picture:
 rts
boss_award_stars:
 lda #65
 sec
 sbc boss_timer
 lsr
 sta boss_t0
 clc
 adc #3
 and #7
 clc
 adc #8
 sta boss_t1
 ldx #2
1: lda lg_font_bases,x
 sta dst_ptr+1
 lda back_buffer
 asl
 asl
 clc
 adc dst_ptr+1
 sta dst_ptr+1
 lda #0
 sta dst_ptr
 ldy #11
 sta (dst_ptr),y
 ldy boss_t1
 lda #192
 sta (dst_ptr),y
 dex
 bpl 1b
 lda #0
 sta boss_t2
2: ldx boss_t2
 lda boss_star_y,x
 clc
 adc boss_t0
 cmp #200
 bcs 3f
 lsr
 lsr
 lsr
 sta draw_row
 lda boss_star_x,x
 sta draw_col
 jsr row_pointer
 lda #129
 ldy #0
 sta (map_ptr),y
3: inc boss_t2
 lda boss_t2
 cmp #BOSS_STARS
 bcc 2b
 rts
large_bomb_spawn:
 lda bird_frame
 and #2
 beq bird_bomb_done
 lda #12
 sec
 sbc aliens_left
 sta boss_t0
 lda ship_left
 sec
 sbc boss_t0
 sta boss_t1
 lda ship_right
 clc
 adc boss_t0
 sta boss_t2
 lda bird_scroll_band
 and #30
 tax
 lda boss_dive_candidates,x
 sta boss_t3
 lda boss_dive_candidates+1,x
 sec
 sbc #112
 tax
bird_bomb_candidate:
 lda bird_records,x
 cmp #5
 bcc bird_bomb_next
 lda bird_records+5,x
 cmp boss_t1
 bcc bird_bomb_next
 cmp boss_t2
 bcs bird_bomb_next
 sta boss_t0
 lda bird_scroll_band
 clc
 adc bird_records+2,x
 and #31
 asl
 asl
 asl
 clc
 adc #20
 sta boss_t1
 jmp campaign_bomb_allocate
bird_bomb_next:
 txa
 clc
 adc #8
 tax
 dec boss_t3
 bne bird_bomb_candidate
bird_bomb_done:
 rts
boss_drop_bomb:
 lda phase
 and #3
 cmp #3
 bne bird_bomb_done
 jsr arcade_random
 clc
 adc #96
 sta boss_t0
 and #14
 and phase
 bne bird_bomb_done
 lda ship_left
 cmp boss_t0
 bcs bird_bomb_done
 lda ship_right
 cmp boss_t0
 bcc bird_bomb_done
 lda #0
 sec
 sbc boss_scroll
 and #248
 clc
 adc #84
 sta boss_t1
campaign_bomb_allocate:
 ldy #0
1: lda bomb_on,y
 beq 2f
 iny
 cpy bomb_limit
 bcc 1b
 rts
2: lda #1
 sta bomb_on,y
 lda boss_t0
 sta raw_bomb_x,y
 lda boss_t1
 sta raw_bomb_y,y
 rts
.section .boss_data,"a",@progbits
.balign 256
boss_gfx: .incbin "build/boss-glyphs.bin"
.include "build/award-stars.inc"
boss_dive_candidates: .incbin "build/bird_dive_spawn_positions.bin"
boss_initial: .incbin "build/boss-body.bin"
boss_pilot_shapes: .incbin "build/alien_wave_animation_shapes.bin"
boss_damage: .incbin "build/mothership_explosion_pointers.bin"
boss_position_ptrs: .incbin "build/alien_position_pointer_table.bin"
boss_positions: .incbin "build/alien_position_layout_page.bin"
campaign_phases: .byte 1,3,5,7,11
boss_row_offsets: .byte 0,26,52,78,104,130,156,182,208,234
boss_wipe_glyph: .incbin "build/wipe-glyph.bin"
.balign 256
boss_wipe_radius: .incbin "build/wipe-radius.bin"
boss_native: .incbin "build/native-tiles.bin"

boss_half_lo:
 .set n,0
 .rept 64
 .byte (n*64)&255
 .set n,n+1
 .endr
boss_half_hi:
 .set n,0
 .rept 64
 .byte 128+(n>>2)
 .set n,n+1
 .endr

.section .boss_code,"ax",@progbits
boss_maps: .incbin "build/boss-maps.bin"
boss_map_ptrs:
 .set n,0
 .rept 8
 .word boss_maps+n*260
 .set n,n+1
 .endr

.section .boss_code,"ax",@progbits
.include "build/boss-stars.inc"
