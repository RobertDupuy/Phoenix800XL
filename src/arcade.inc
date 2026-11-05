# Opening-wave rules translated into bounded 6502 routines from the recovered
# Amstar ROM tables. Tests compare raw coordinates/scheduler state with MAME.
.set raw_ship_x,0xa5
.set raw_shot_x,0xa6
.set raw_shot_y,0xa7
.set arcade_fraction,0xa8
.set bonus_stage,0xaa
.set ship_left,0xab
.set ship_right,0xac
.set aptr,0xb6
.set atmp,0xb8
.set atmp2,0xb9
.set aidx,0xba
.set aloop,0xbb
.set axcmp,0xbc
.set aycmp,0xbd
.set chr_found,0xbe
.set raw_enemy_x,0x430
.set raw_enemy_y,0x440
.set pattern_lo,0x450
.set pattern_hi,0x460
.set enemy_kind,0x470
.set enemy_shape,0x4a0
.set raw_bomb_x,0x4b0
.set raw_bomb_y,0x4b8
.set sched_phase,0x360
.set sched_new_hi,0x361
.set sched_new_lo,0x362
.set sched_count,0x363
.set sched_start,0x364
.set sched_delay,0x365
.set sched_old,0x366
.set sched_breakouts,0x367
.set sched_breakdelay,0x368
.set sched_slots,0x369
.set main_phase,0x36f
.set sched_counter,0x370
.set base_lo,0x371
.set arcade_clock,0x372
.set aliens_left,0x374
.set fast_aliens,0x375
.set level_round,0x376
.set display_enemy_x,0x410
.set display_enemy_y,0x420
.set display_enemy_shape,0x4c0
.set display_enemy_on,0x4d0
.section .text,"ax",@progbits
.global arcade_reset,arcade_step,arcade_random,arcade_schedule,alien_move,alien_animate,alien_map,pattern_byte
arcade_reset:
 lda #16
 sta respawn_population
 jmp arcade_population_init
.global arcade_resume
arcade_resume:
 lda aliens_left
 sta respawn_population
.section .expanded_code,"ax",@progbits
arcade_population_init:
 lda #0
 ldx #0x16
arcade_clear:
 sta 0x360,x
 dex
 bpl arcade_clear
 lda cycle_stage
 asl
 ora #1
 ldx cycle_stage
 cpx #4
 bne 1f
 lda #11
1: ora cycle_round
 sta level_round
 lda respawn_population
 sta aliens_left
 ldx #15
arcade_enemy_init:
 lda #0
 cpx aliens_left
 bcs 2f
 lda #1
2:
 sta enemy_on,x
 lda #1
 sta enemy_kind,x
 lda #0x20
 sta enemy_shape,x
 lda #0
 sta pattern_lo,x
 lda #0x10
 sta pattern_hi,x
 dex
 bpl arcade_enemy_init
 jsr campaign_layout
 lda #0
 sta burst_count
 sta burst_count+1
 sta burst_count+2
 sta burst_score
 sta burst_score+1
 sta bonus_count
 sta bonus_count+1
 lda #255
 sta burst_pose
 sta burst_pose+1
 sta burst_pose+2
 jsr refresh_alien_screen
 jsr prepare_shot_bounds
 jmp latch_aliens
.section .text,"ax",@progbits
player_update:
 # One atomic coordinate snapshot for this logical collision tick. The VBI
 # owns live movement; it never touches the foreground's coordinate/scratch.
 lda video_ship_x
 sta raw_ship_x
 jsr shield_update
 bcc player_positioned
 lda raw_ship_x
 sta video_ship_x
player_positioned:
 ldx raw_ship_x
 txa
 lsr
 clc
 adc #76
 sta ship_x
 txa
 and #7
 asl
 tax
 lda raw_ship_x
 sec
 sbc player_x_position_mapping,x
 sta ship_left
 lda raw_ship_x
 clc
 adc player_x_position_mapping+1,x
 sta ship_right
 rts
shot_update:
 lda shot_on
 beq shot_try_fire
 lda raw_shot_y
 sec
 sbc #8
 sta raw_shot_y
 cmp #31
 bcs shot_map
 lda #0
 sta shot_on
 rts
shot_try_fire:
 lda fire_edge
 beq arcade_shot_done
 lda #0
 sta fire_edge
 lda #1
 sta shot_on
 lda raw_ship_x
 clc
 adc #4
 sta raw_shot_x
 lda #208
 sta raw_shot_y
 lda #1
 sta audio_shot_pending
 lda sound_kind
 cmp #2
 bcs shot_map
 lda #1
 sta sound_kind
 lda #8
 sta sound_time
shot_map:
 ldx raw_shot_x
 txa
 lsr
 clc
 adc #76
 sta shot_x
 ldx raw_shot_y
 txa
 clc
 adc #8
 bcc 1f
 lda #255
1:
 sta shot_y
arcade_shot_done:
 rts
arcade_step:
 inc arcade_clock
 bne arcade_clock_ok
 inc arcade_clock+1
arcade_clock_ok:
 lda main_phase
 inc main_phase
 and #3
 sta atmp
 lda aliens_left
 bne aliens_still_active
 lda atmp
 and #1
 beq empty_wave_tick_done
 jsr bombs_update
 jmp burst_tick
empty_wave_tick_done:
 rts
aliens_still_active:
 cmp #5
 bcs normal_alien_rate
 lda atmp
 bne check_fast
 lda #1
 sta fast_aliens
check_fast:
 lda fast_aliens
 beq normal_alien_rate
 lda atmp
 and #1
 bne fast_move
 jsr latch_aliens
 jsr arcade_schedule
 jsr alien_body_collision
 jsr bomb_spawn
 jmp bombs_update
fast_move:
 jsr alien_move
 jsr alien_animate
 jsr refresh_alien_screen
 jmp burst_tick
normal_alien_rate:
 lda atmp
 beq schedule_phase
 cmp #1
 beq move_phase
 cmp #2
 beq animation_phase
 jsr bombs_update
 jsr refresh_alien_screen
 jmp burst_tick
schedule_phase:
 jsr latch_aliens
 jsr arcade_schedule
 jmp alien_body_collision
move_phase:
 jsr bombs_update
 jsr alien_move
 jmp burst_tick
animation_phase:
 jsr alien_animate
 jmp bomb_spawn

# Snapshot coordinates and fine-phase artwork together at the actual arcade
# draw phase (normal phase 0; accelerated even phases). The simulation may
# change coordinates one tick before artwork; those states must not be drawn.
.global latch_aliens
latch_aliens:
 ldx #15
latch_alien_loop:
 lda raw_enemy_x,x
 sta display_enemy_x,x
 lda raw_enemy_y,x
 sta display_enemy_y,x
 lda enemy_shape,x
 sta display_enemy_shape,x
 lda enemy_on,x
 sta display_enemy_on,x
 dex
 bpl latch_alien_loop
 rts

# X = alien slot. A = original pattern byte. X preserved.
pattern_byte:
 # Both recovered pattern clusters are page aligned. One ROM lookup replaces
 # repeated bank-range arithmetic; this does not switch cartridge banks.
 lda pattern_lo,x
 sta aptr
 ldy pattern_hi,x
 lda pattern_pages,y
 sta aptr+1
 ldy #0
 lda (aptr),y
 rts
alien_move:
 lda #255
 sta shot_bounds_min
 sta shot_bounds_left
 lda #0
 sta shot_bounds_max
 sta shot_bounds_right
 ldx #15
alien_move_loop:
 lda enemy_on,x
 beq alien_move_next
 jsr pattern_byte
 asl
 tay
 lda raw_enemy_x,x
 clc
 adc alien_direction_vectors,y
 sta raw_enemy_x,x
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
 clc
 adc alien_direction_vectors+1,y
 sta raw_enemy_y,x
 and #248
 sta collision_cell_y,x
 cmp shot_bounds_min
 bcs 8f
 sta shot_bounds_min
8:
 cmp shot_bounds_max
 bcc 9f
 sta shot_bounds_max
9:
 lda alien_direction_vectors+1,y
 beq movement_x_boundary
 lda raw_enemy_y,x
 jmp movement_boundary
movement_x_boundary:
 lda raw_enemy_x,x
movement_boundary:
 and #7
 bne alien_move_next
 inc pattern_lo,x
alien_move_next:
 dex
 bpl alien_move_loop
 jmp validate_shot_bounds
alien_animate:
 ldx #15
alien_animate_loop:
 lda enemy_on,x
 beq alien_animate_next
 stx aidx
 jsr pattern_byte
 bne animate_vector
 lda #0x10
 sta pattern_hi,x
 lda base_lo
 sta pattern_lo,x
 jsr pattern_byte
animate_vector:
 sta atmp
 asl
 clc
 adc atmp
 clc
 adc #0xa0
 tay
 lda alien_shape_offset_page,y
 sta enemy_kind,x
 lda alien_shape_offset_page+1,y
 and #1
 beq animate_not_xy
 lda raw_enemy_x,x
 and #4
 sta atmp
 lda raw_enemy_y,x
 lsr
 and #3
 clc
 adc atmp
 jmp animate_offset
animate_not_xy:
 lda alien_shape_offset_page+1,y
 and #2
 beq animate_y
 lda raw_enemy_x,x
 jmp animate_axis
animate_y:
 lda raw_enemy_y,x
animate_axis:
 lsr
 and #3
animate_offset:
 clc
 adc alien_shape_offset_page+2,y
 tay
 lda alien_shape_offset_page,y
 sta enemy_shape,x
alien_animate_next:
 dex
 bpl alien_animate_loop
 rts
alien_map:
 # Legacy PM projection retained as a reference helper. The native renderer
 # reads raw coordinates; no gameplay path needs this duplicate projection.
 ldx #15
alien_map_loop:
 lda raw_enemy_x,x
 and #248
 lsr
 clc
 adc #76
 sta enemy_x,x
 lda raw_enemy_y,x
 and #248
 clc
 adc #8
 sta enemy_y,x
 dex
 bpl alien_map_loop
 rts
arcade_random:
 lda arcade_clock
 lsr
 lsr
 lsr
 lsr
 lsr
 clc
 adc raw_ship_x
 and #15
 rts
arcade_schedule:
 lda sched_counter
 inc sched_counter
 and #7
 asl
 tax
 lda scheduler_jumps,x
 sta aptr
 lda scheduler_jumps+1,x
 sta aptr+1
 jmp (aptr)
sched_rotate:
 lda base_lo
 sta sched_old
 clc
 adc #1
 and #15
 sta base_lo
 lda sched_phase
 cmp #5
 bcc sched_return
 lda #0
 sta sched_phase
 lda sched_count
 beq sched_return
 sta aloop
 ldx sched_start
retarget_loop:
 lda pattern_hi,x
 cmp #0x10
 bne retarget_next
 lda pattern_lo,x
 cmp sched_old
 bne retarget_next
 lda sched_new_hi
 sta pattern_hi,x
 lda sched_new_lo
 sta pattern_lo,x
retarget_next:
 inx
 txa
 and #15
 tax
 dec aloop
 bne retarget_loop
sched_return:
 rts
.global breakout_delay
breakout_delay:
 lda level_round
 lsr
 and #7
 eor #7
 sta atmp2
 lda level_round
 lsr
 lsr
 lsr
 lsr
 cmp #8
 bcc delay_round_ok
 lda #7
delay_round_ok:
 eor #7
 clc
 adc atmp2
 sta atmp2
 lda aliens_left
 cmp #5
 bcs delay_population
 lda #21
delay_population:
 sec
 sbc #5
 clc
 adc atmp2
 sta atmp2
 jsr arcade_random
 and #7
 clc
 adc atmp2
 rts
sched_breakout:
 lda sched_breakouts
 cmp #3
 bcs sched_return
 lda sched_phase
 cmp #4
 bcs sched_return
 lda sched_breakdelay
 beq breakout_new
 dec sched_breakdelay
 bne sched_return
 inc sched_breakouts
 lda #4
 sta sched_phase
 lda #16
 sta sched_count
 lda #0
 sta sched_start
 sta sched_new_lo
 lda #0x2e
 sta sched_new_hi
 lda raw_ship_x
 and #1
 bne sched_return
 lda #0x40
 sta sched_new_lo
 rts
breakout_new:
 jsr breakout_delay
 sta atmp2
 lda sched_breakouts
 asl
 asl
 clc
 adc atmp2
 adc #7
 sta sched_breakdelay
 rts
sched_bombs:
 ldx #2
sched_tick_slots:
 lda sched_slots,x
 beq sched_slot_next
 dec sched_slots,x
sched_slot_next:
 dex
 bpl sched_tick_slots
 lda sched_phase
 bne sched_return2
 lda sched_delay
 beq sched_new_delay
 dec sched_delay
 bne sched_return2
 lda #1
 sta sched_phase
sched_return2:
 rts
sched_new_delay:
 jsr breakout_delay
 sta atmp2
 lda arcade_clock+1
 cmp #16
 bcc delay_age_ok
 lda #15
delay_age_ok:
 eor #15
 clc
 adc atmp2
 sta atmp2
 ldx #0
 ldy #1
free_slot_loop:
 lda sched_slots,x
 bne free_slot_next
 lsr atmp2
 cpy #0
 beq free_slot_next
 dey
 lda #12
 sta sched_slots,x
free_slot_next:
 inx
 cpx #3
 bcc free_slot_loop
 lda atmp2
 lsr
 lsr
 clc
 adc #1
 sta sched_delay
 rts
sched_count_scan:
 lda sched_phase
 cmp #1
 bne sched_return2
 inc sched_phase
 lda level_round
 lsr
 lsr
 and #15
 clc
 adc #5
 cmp #17
 bcc scan_max_ready
 lda #5
scan_max_ready:
 sec
 sbc sched_breakouts
 sta atmp2
 jsr arcade_random
 clc
 adc #1
 cmp atmp2
 bcc scan_count_ready
 lda #1
scan_count_ready:
 sta sched_count
 rts
sched_select:
 lda sched_phase
 cmp #2
 bne sched_return3
 jsr arcade_random
 tax
 lda #16
 sta aloop
select_loop:
 lda enemy_on,x
 beq select_next
 lda pattern_hi,x
 cmp #0x10
 bne select_next
 lda pattern_lo,x
 cmp sched_old
 bne select_next
 stx sched_start
 inc sched_phase
 rts
select_next:
 inx
 txa
 and #15
 tax
 dec aloop
 bne select_loop
sched_return3:
 rts
sched_pattern:
 lda sched_phase
 cmp #3
 bne sched_return3
 ldx sched_start
 lda raw_ship_x
 sec
 sbc raw_enemy_x,x
 bcs player_on_right
 eor #255
 clc
 adc #1
 ldy #0
 jmp distance_abs
player_on_right:
 ldy #4
distance_abs:
 sty atmp2
 lsr
 lsr
 lsr
 lsr
 lsr
 tay
 lda alien_distance_bands,y
 clc
 adc atmp2
 asl
 asl
 sta atmp2
 ldy sched_breakouts
 lda sched_count
 cmp #1
 bne height_ready
 ldy #0
 lda raw_enemy_y,x
 cmp #88
 bcc height_ready
 iny
 cmp #120
 bcc height_ready
 iny
 cmp #152
 bcc height_ready
 iny
height_ready:
 tya
 clc
 adc atmp2
 tay
 lda alien_pattern_selectors,y
 sta atmp2
 jsr arcade_random
 and #6
 clc
 adc atmp2
 sec
 sbc #0x30
 tay
 lda alien_closed_loop_pointers,y
 sta sched_new_hi
 lda alien_closed_loop_pointers+1,y
 sta sched_new_lo
 lda #5
 sta sched_phase
 rts
sched_all_home:
 lda sched_phase
 cmp #4
 bne sched_noop
 ldx #15
home_loop:
 lda enemy_on,x
 beq home_next
 lda pattern_hi,x
 cmp #0x10
 bne sched_noop
 lda pattern_lo,x
 cmp sched_old
 bne sched_noop
home_next:
 dex
 bpl home_loop
 lda #6
 sta sched_phase
sched_noop:
 rts

bomb_spawn:
 # Full slots cannot spawn: avoid a candidate scan with no observable effect.
 lda bomb_on
 and bomb_on+1
 and bomb_on+2
 beq 8f
 rts
8:
 lda sched_breakouts
 asl
 asl
 asl
 clc
 adc #173
 sta aycmp
 lda ship_left
 sec
 sbc #10
 sta axcmp
 lda ship_right
 clc
 adc #3
 sta atmp2
 lda sched_counter
 and #1
 asl
 asl
 asl
 tax
 lda #8
 sta aloop
bomber_scan:
 lda enemy_on,x
 beq bomber_next
 lda enemy_shape,x
 cmp #8
 beq bomber_next
 cmp #136
 bcs bomber_next
 lda raw_enemy_x,x
 cmp axcmp
 bcc bomber_next
 cmp atmp2
 bcs bomber_next
 lda raw_enemy_y,x
 cmp #128
 bcc bomber_next
 cmp aycmp
 bcs bomber_next
 ldy #0
bomb_free_scan:
 lda bomb_on,y
 beq bomb_free_found
 iny
 cpy bomb_limit                   // arcade round 1/2/3+: three/four/five
 bcc bomb_free_scan
 rts
bomb_free_found:
 lda #1
 sta bomb_on,y
 lda raw_enemy_x,x
 clc
 adc #4
 sta raw_bomb_x,y
 lda raw_enemy_y,x
 clc
 adc #12
 sta raw_bomb_y,y
 rts
bomber_next:
 inx
 dec aloop
 bne bomber_scan
 rts
bombs_update:
 ldx #4
bomb_update_loop:
 lda bomb_on,x
 beq bomb_update_next
 lda raw_bomb_y,x
 clc
 adc #4
 sta raw_bomb_y,x
 cmp #249
 bcc bomb_update_next
 lda #0
 sta bomb_on,x
bomb_update_next:
 lda bomb_on,x
 beq bomb_shield_done
 jsr bomb_collision_one
 jsr shield_bomb_cell
bomb_shield_done:
 dex
 bpl bomb_update_loop
 rts
# Projection is display work: once after all logical substeps, not per bomb tick.
map_bombs:
 ldx #4
bomb_map_loop:
 ldy raw_bomb_x,x
 tya
 lsr
 clc
 adc #76
 sta bomb_x,x
 ldy raw_bomb_y,x
 tya
 clc
 adc #8
 bcc 1f
 lda #255
1:
 sta bomb_y,x
 dex
 bpl bomb_map_loop
 rts
bomb_collision:
 lda invuln
 bne bomb_collision_done
 ldx #4
bomb_collision_loop:
 lda bomb_on,x
 beq bomb_collision_next
 lda raw_bomb_y,x
 cmp #220
 bcc bomb_collision_next
 cmp #233
 bcs bomb_collision_next
 lda raw_bomb_x,x
 cmp ship_left
 bcc bomb_collision_next
 beq bomb_collision_next
 cmp ship_right
 beq bomb_hits
 bcs bomb_collision_next
bomb_hits:
 lda #0
 sta bomb_on,x
 jmp damage_player
bomb_collision_next:
 dex
 bpl bomb_collision_loop
bomb_collision_done:
 rts
alien_body_collision:
 lda shield_count
 cmp #192
 bcc normal_body_collision
 jmp shield_body_collision
normal_body_collision:
 lda invuln
 bne body_done
 ldx #15
body_loop:
 lda enemy_on,x
 beq body_next
 lda raw_enemy_y,x
 cmp #210
 bcc body_next
 cmp #231
 bcs body_next
 lda ship_left
 sec
 sbc #6
 cmp raw_enemy_x,x
 beq body_min_equal
 bcs body_next
body_min_equal:
 lda raw_enemy_x,x
 cmp ship_right
 bcs body_next
 stx aidx
 jsr damage_player
 ldx aidx
 lda #4
 jsr kill_alien
 lda #13
 jmp set_hit_counter
body_next:
 dex
 bpl body_loop
body_done:
 rts
# Reconstruct the original foreground cell beneath a shot. Later drawn aliens
# replace earlier cells; original ROM T1740 then supplies the formation window.
shot_collision:
 lda shot_on
 beq shot_early_return
 lda shot_bounds_valid
 beq shot_bounds_passed
 lda raw_shot_x
 and #248
 cmp shot_bounds_left
 bcc shot_early_return
 cmp shot_bounds_right
 bcc shot_bounds_y
 sec
 sbc shot_bounds_right
 cmp #9
 bcs shot_early_return
shot_bounds_y:
 lda raw_shot_y
 and #248
 cmp shot_bounds_min
 bcc shot_early_return
 cmp shot_bounds_max
 bcc shot_bounds_passed
 sec
 sbc shot_bounds_max
 cmp #9
 bcc shot_bounds_passed
shot_early_return:
 rts
shot_bounds_passed:
 lda raw_shot_x
 and #248
 sta axcmp
 lda raw_shot_y
 and #248
 sta aycmp
 lda #0
 sta chr_found
 ldx #0
shot_cell_loop:
 lda enemy_on,x
 beq shot_cell_next
 lda axcmp
 sec
 sbc collision_cell_x,x
 cmp #16
 bcs shot_cell_next
 lsr
 lsr
 lsr
 sta atmp
 lda aycmp
 sec
 sbc collision_cell_y,x
 cmp #16
 bcs shot_cell_next
 lsr
 lsr
 lsr
 sta atmp2
 lda enemy_kind,x
 cmp #1
 bne cell_not_horizontal
 lda atmp2
 bne shot_cell_next
 lda atmp
 jmp cell_shape
cell_not_horizontal:
 cmp #3
 bne cell_square
 lda atmp
 bne shot_cell_next
 lda atmp2
 jmp cell_shape
cell_square:
 lda atmp
 asl
 clc
 adc atmp2
cell_shape:
 clc
 adc enemy_shape,x
 tay
 lda sprite_character_block_shapes,y
 sta chr_found
shot_cell_next:
 inx
 cpx #16
 bcc shot_cell_loop
 lda chr_found
 cmp #96
 bcc shot_collision_done
 cmp #192
 bcs shot_collision_done
 cmp #104
 bcs shot_dive_test
 and #7
 asl
 asl
 tay
 lda raw_shot_x
 and #7
 cmp formation_hit_window,y
 bcs shot_collision_done
 cmp formation_hit_window+1,y
 bcc shot_collision_done
 lda axcmp
 clc
 adc formation_hit_window+2,y
 sta axcmp
 ldx #0
formation_hit_loop:
 lda enemy_on,x
 beq formation_hit_next
 lda collision_cell_y,x
 cmp aycmp
 bne formation_hit_next
 lda raw_enemy_x,x
 clc
 adc #2
 cmp axcmp
 bcc formation_hit_next
 lda raw_enemy_x,x
 sec
 sbc #3
 cmp axcmp
 bcs formation_hit_next
 lda #2
 jmp shot_kill
formation_hit_next:
 inx
 cpx #16
 bcc formation_hit_loop
shot_collision_done:
 rts
shot_dive_test:
 ldx #0
dive_hit_loop:
 lda enemy_on,x
 beq dive_hit_next
 lda raw_shot_x
 cmp raw_enemy_x,x
 bcc dive_hit_next
 lda raw_enemy_x,x
 clc
 adc #8
 cmp raw_shot_x
 bcc dive_hit_next
 lda raw_enemy_y,x
 clc
 adc #4
 cmp aycmp
 bcc dive_hit_next
 lda raw_enemy_y,x
 sec
 sbc #8
 cmp aycmp
 bcs dive_hit_next
 jsr pattern_byte
 cmp #7
 bcc ordinary_dive_score
 cmp #9
 bcs ordinary_dive_score
 lda #20
 jmp shot_kill
ordinary_dive_score:
 lda #4
 jmp shot_kill
dive_hit_next:
 inx
 cpx #16
 bcc dive_hit_loop
 rts
shot_kill:
 pha
 lda #0
 sta shot_on
 pla
kill_alien:
 pha
 jsr burst_start
 lda #0
 sta enemy_on,x
 sta display_enemy_on,x
 dec aliens_left
 inc kills
 bne kill_counted
 inc kills+1
kill_counted:
 pla
 lda state
 cmp #3
 beq kill_sound_done
 lda #2
 sta sound_kind
 lda #15
 sta sound_time
 lda #1
 sta audio_hit_pending
kill_sound_done:
 rts
score_add:
 ldy #4
 cmp #10
 bcc score_normal
 ldx #0
score_hundreds:
 sec
 sbc #10
 inx
 cmp #10
 bcs score_hundreds
 txa
 dey
score_normal:
 clc
 adc score_digits,y
score_digit_carry:
 cmp #10
 bcc score_digit_store
 sec
 sbc #10
 sta score_digits,y
 dey
 bmi score_dirty
 lda score_digits,y
 clc
 adc #1
 jmp score_digit_carry
score_digit_store:
 sta score_digits,y
score_dirty:
 lda #3
 sta hud_dirty
 # Bonus thresholds: strictly greater than 3,000, then 30,000.
 ldx bonus_stage
 cpx #2
 bcs score_done
 lda score_digits
 bne bonus_award
 cpx #0
 bne bonus_second
 lda score_digits+1
 bne bonus_award
 lda score_digits+2
 cmp #3
 bcc score_done
 bne bonus_award
 lda score_digits+3
 ora score_digits+4
 ora score_digits+5
 bne bonus_award
 rts
bonus_second:
 lda score_digits+1
 cmp #3
 bcc score_done
 bne bonus_award
 lda score_digits+2
 ora score_digits+3
 ora score_digits+4
 ora score_digits+5
 beq score_done
bonus_award:
 inc bonus_stage
 inc lives
 lda #3
 sta life_dirty
score_done:
 rts
.section .tables,"a",@progbits
pattern_pages:
 # Fixed-layout page constants are asserted against linked symbols by build.py.
 .set page,0
 .rept 48
 .if page < 32
 .byte pattern_base_a+page-16
 .else
 .byte pattern_base_b+page-44
 .endif
 .set page,page+1
 .endr

.section .bank0_data,"a",@progbits
.balign 256
.global alien_movement_cluster_a,alien_movement_cluster_b
.include "build/arcade-tables.inc"

scheduler_jumps: .word sched_rotate,sched_breakout,sched_bombs,sched_count_scan,sched_select,sched_pattern,sched_all_home,sched_noop

.section .tables,"a",@progbits
wave_initial_x: .byte 96,96,72,120,56,136,40,152,24,168,24,168,40,152,56,136,80,112,96,96,80,112,64,128,48,144,32,160,24,168,96,96
wave_initial_y: .byte 72,88,88,88,80,80,72,72,64,64,48,48,40,40,32,32,32,32,40,56,64,64,56,56,48,48,56,56,72,72,72,88

.section .tables,"a",@progbits
