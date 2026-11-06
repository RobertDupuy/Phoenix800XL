# v0.7: measured first/second small-bird wave entry and second player shot.
.set second_on,0x710
.set second_x,0x711
.set second_y,0x712
.set second_raw_x,0x713
.set second_raw_y,0x714
.set entrance_timer,0x71a
.set star_index,0x71b
.set star_phase,0x71c
.set star_previous,0x71d
.set entrance_shown,0x71f
.set second_old_col,0x720
.set second_old_row,0x722
.set entrance_initial_wait,0x763
.set entrance_handoff,0x764
.section .expanded_code,"ax",@progbits
.global begin_wave,entrance_tick,player_shots,swap_shots,draw_second_shot,clear_second_shot
begin_wave:
 lda large_mode
 beq begin_small_wave
 rts
begin_small_wave:
 lda #1
 sta entrance_initial_wait
 lda #0
 sta entrance_handoff
 lda #100
 sta raw_ship_x
 sta video_ship_x
 lda #126
 sta ship_x
 lda #255
 ldx cycle_stage
 cpx #1
 bne 1f
 lda #160
1:
 sta entrance_timer
 lda #0
 ldx #15
2:
 sta display_enemy_on,x
 dex
 bpl 2b
 rts
entrance_tick:
 lda entrance_initial_wait
 beq entrance_count
 dec entrance_initial_wait
 rts
entrance_count:
 dec entrance_timer
 beq entrance_done
 lda entrance_timer
 cmp #21
 bcs entrance_return
 lsr
 lsr
 tax
 lda fade_shapes,x
 sta temp
 ldx #15
entrance_birds:
 lda temp
 sta display_enemy_shape,x
 lda #1
 sta display_enemy_on,x
 dex
 bpl entrance_birds
entrance_return:
 rts
entrance_done:
 lda #1
 sta entrance_handoff
 rts
.global entrance_finish
entrance_finish:
 lda #0
 sta entrance_handoff
 sta fire_edge
 sta shield_edge
 jmp latch_aliens
player_shots:
 jsr boss_intro_pending
 bne entrance_return
 jsr shot_update
 lda large_mode
 beq small_player_collision
 cmp #3
 bne 1f
 jmp boss_shot_collision
1: jmp large_collision
small_player_collision:
 jsr shot_collision
 lda level_round
 and #15
 cmp #3
 bne entrance_return
 jsr swap_shots
 jsr shot_update
 jsr shot_collision
swap_shots:
 .irp pair,0,1,2,3,4
 .if \pair == 0
 .set primary,shot_on
 .elseif \pair == 1
 .set primary,shot_x
 .elseif \pair == 2
 .set primary,shot_y
 .elseif \pair == 3
 .set primary,raw_shot_x
 .else
 .set primary,raw_shot_y
 .endif
 ldx primary
 lda second_on+\pair
 sta primary
 stx second_on+\pair
 .endr
 rts
clear_second_shot:
 ldx back_buffer
 lda second_old_row,x
 cmp #127
 beq clear_second_done
 sta draw_row
 lda second_old_col,x
 sta draw_col
 lda #127
 sta second_old_row,x
 jsr row_pointer
 lda #0
 ldy #0
 sta (map_ptr),y
 lda draw_row
 cmp #24
 bcs clear_second_done
 lda #0
 ldy #32
 sta (map_ptr),y
clear_second_done:
 rts
draw_second_shot:
 jsr projectiles_visible
 bcc second_return
 lda second_on
 beq second_return
 lda second_x
 sta 0x6fd
 lda second_y
 cmp #40
 bcc second_return
 cmp #238
 bcs second_return
 # Use common bounded pixel writer, with separate saved footprint.
 lda 0x6fe
 pha
 lda #0x30
 sta 0x6fe
 lda second_y
 jsr soft_common
 pla
 sta 0x6fe
second_return:
 rts
.global seed_stars,scroll_stars
seed_stars:
 ldx back_buffer
 lda star_previous,x
 ora entrance_timer
 bne scroll_stars
 jmp seed_stars_static
scroll_stars:
 lda entrance_timer
 sta star_previous,x
 # Four page stores per iteration bound the map clear to 6,419 CPU cycles.
 ldy #0
 lda #0
 cpx #0
 bne scroll_clear_one
scroll_clear_zero:
 .irp page,0x2800,0x2900,0x2a00,0x2b00
 sta \page,y
 .endr
 iny
 bne scroll_clear_zero
 beq scroll_map_clear
scroll_clear_one:
 .irp page,0x2c00,0x2d00,0x2e00,0x2f00
 sta \page,y
 .endr
 iny
 bne scroll_clear_one
scroll_map_clear:
 lda #8
 sta dst_ptr
 lda font_hi
 sta dst_ptr+1
 ldy #7
 lda #0
scroll_glyph_clear:
 sta (dst_ptr),y
 dey
 bpl scroll_glyph_clear
 lda #3
 sec
 sbc entrance_timer
 and #7
 sta star_phase
 tay
 lda #12
 sta (dst_ptr),y
 lda entrance_timer
 bne 2f
 jmp seed_stars_static
2:
 lda #0
 sta star_index
scroll_next:
 ldx star_index
 lda scroll_star_y,x
 sec
 sbc entrance_timer
 bcc scroll_skip
 cmp #200
 bcs scroll_skip
 lsr
 lsr
 lsr
 sta draw_row
 lda scroll_star_x,x
 sta draw_col
 jsr row_pointer
 lda #129
 ldy #0
 sta (map_ptr),y
scroll_skip:
 inc star_index
 lda star_index
 cmp #SCROLL_STARS
 bcc scroll_next
 rts
.section .tables,"a",@progbits
fade_shapes: .byte 244,243,242,241,240,240
.include "build/scroll-stars.inc"

# IRQ-owned coordinate/fraction. Foreground reads one byte atomically.
.set video_ship_x,0x730
.set ship_video_fraction,0x731
.section .text,"ax",@progbits
.global video_player_update,video_player_tick,render_live_ship
video_player_update:
 # Alternating 1216/1217 increments total 2433 per two video frames,
 # matching the foreground arcade clock without half-speed movement.
 lda video_phase
 clc
 adc #192
 clc
 adc ship_video_fraction
 sta ship_video_fraction
 lda ship_video_fraction+1
 adc #4
 sta ship_video_fraction+1
 bcc video_player_tick
 jsr video_player_tick
video_player_tick:
 jsr boss_intro_pending
 bne video_player_done
 lda state
 cmp #1
 bne video_player_done
 lda entrance_timer
 ora entrance_handoff
 ora shield_locked
 bne video_player_done
 lda stick_x
 cmp #82
 bcs video_player_right
 lda video_ship_x
 cmp #13
 bcc video_player_done
 dec video_ship_x
 rts
video_player_right:
 cmp #146
 bcc video_player_done
 lda video_ship_x
 cmp #192
 bcs video_player_done
 inc video_ship_x
video_player_done:
 rts
render_live_ship:
 jsr boss_intro_pending
 bne video_player_done
 lda display_active
 beq video_player_done
 lda state
 cmp #1
 bne video_player_done
 lda entrance_timer
 ora entrance_handoff
 ora entrance_shown
 bne video_player_done
 lda shield_pose
 and 0x337
 cmp #255
 bne video_player_done
 ldx front_buffer
 lda 0x332,x
 cmp #1
 bne video_player_done
 jsr animate_ship
 lda video_ship_x
 lsr
 clc
 adc #76
 sta ship_hpos
 sta 0xc000
 sta 0xc001
 sta 0xc002
 rts

.set shot_bounds_min,0x734
.set shot_bounds_max,0x735
.set shot_bounds_valid,0x736
.set collision_cell_x,0x740
.set collision_cell_y,0x750
.set shot_bounds_left,0x737
.set shot_bounds_right,0x738
.global prepare_shot_bounds
prepare_shot_bounds:
 # Conservative visible row range shared by both shots. It only rejects
 # empty rows; the existing per-cell hit tests still decide every hit.
 lda #255
 sta shot_bounds_min
 sta shot_bounds_left
 lda #0
 sta shot_bounds_max
 sta shot_bounds_right
 ldx #15
shot_bounds_loop:
 lda enemy_on,x
 beq shot_bounds_next
 lda raw_enemy_x,x
 and #248
 sta collision_cell_x,x
 cmp shot_bounds_left
 bcs 6f
 sta shot_bounds_left
6:
 cmp shot_bounds_right
 bcc 7f
 sta shot_bounds_right
7:
 lda raw_enemy_y,x
 and #248
 sta collision_cell_y,x
 cmp shot_bounds_min
 bcs 1f
 sta shot_bounds_min
1:
 cmp shot_bounds_max
 bcc shot_bounds_next
 sta shot_bounds_max
shot_bounds_next:
 dex
 bpl shot_bounds_loop
validate_shot_bounds:
 lda #0
 sta shot_bounds_valid
 lda shot_bounds_right
 cmp #248
 beq shot_bounds_done
 lda shot_bounds_max
 cmp #248
 beq shot_bounds_done
 lda #1
 sta shot_bounds_valid
shot_bounds_done:
 rts
