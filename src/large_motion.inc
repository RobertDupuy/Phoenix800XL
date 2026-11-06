# Amstar 8085 routines 2600..26FD, 3560..3754 translated to NMOS 6502.
# Eight original 8-byte bird records and a single scrolling background layer.
.set bird_records,0x3d00
.set bird_scroll,0x3d40
.set bird_target_delta,0x3d41
.set bird_speed_cap,0x3d42
.set bird_random,0x3d43
.set bird_frame,0x3d44
.set bird_elapsed,0x3d45
.set bird_round,0x3d46
.set bird_threshold,0x3d48
.set bird_scroll_band,0x3d49
.set bird_climb_timer,0x3d4a
.set bird_climb_speed,0x3d4b
.set bird_descent,0x3d4c
.set bird_height,0x3d4d
.set bird_span,0x3d4e
.set bird_tmp,0x3d50
.set bird_tmp2,0x3d51
.set bird_step,0x3d52
.set bird_slot,0x3d53
.set bird_script,0x3d54
.set bird_end,0x3d55
.set bird_latched_x,0x3d60
.set bird_latched_pose,0x3d68
.section .expanded_code,"ax",@progbits
.global large_motion_reset,large_motion_tick,large_vertical,large_behavior,large_flight_params
large_motion_reset:
 lda #0
 ldx #127
1: sta bird_records,x
 dex
 bpl 1b
 lda #0
 sta bird_frame
 lda large_mode
 asl
 clc
 adc #3
 ora cycle_round
 sta bird_round
 lda #64
 ldx large_mode
 cpx #2
 beq 2f
 lda #0
2: tay
 ldx #0
3: lda bird_initial_data,y
 sta bird_records,x
 iny
 inx
 cpx #64
 bne 3b
 ldx #0
4: jsr large_motion_latch
 txa
 clc
 adc #8
 tax
 cpx #64
 bne 4b
 rts
large_motion_tick:
 inc bird_frame
 bne 1f
 inc bird_elapsed
1: jsr large_vertical
 jsr large_flight_params
 lda aliens_left
 cmp #4
 bcc large_update_all
 lda bird_frame
 and #1
 beq large_update_first
 lda #64
 sta bird_end
 ldx #32
 bne large_update_bank
large_update_first:
 lda #32
 sta bird_end
 ldx #0
 beq large_update_bank
large_update_all:
 lda #64
 sta bird_end
 ldx #0
large_update_bank:
 stx bird_slot
 jsr large_motion_latch
 jsr large_behavior
 ldx bird_slot
 txa
 clc
 adc #8
 tax
 cpx bird_end
 bne large_update_bank
 rts
large_motion_latch:
 txa
 lsr
 lsr
 lsr
 tay
 lda bird_records,x
 sta enemy_on,y
 beq 9f
 sec
 sbc #1
 asl
 asl
 sta bird_tmp
 lda bird_records+3,x
 lsr
 and #3
 ora bird_tmp
 sta bird_latched_pose,y
 sta large_pose,y
 lda bird_records+2,x
 and #31
 asl
 asl
 asl
 sta large_world_y,y
 lda bird_records+2,x
 and #224
 sta bird_tmp
 lda #32
 sec
 sbc bird_tmp
 sta bird_tmp
 lda #0x4b
 sbc bird_records+1,x
 lsr
 ror bird_tmp
 lsr
 ror bird_tmp
 lda bird_tmp
 clc
 adc #8
 sta large_x,y
 lda bird_records+4,x
 sta large_age,y
9: rts

large_flight_params:
 lda bird_frame
 lsr
 lsr
 lsr
 lsr
 lsr
 clc
 adc raw_ship_x
 and #15
 sta bird_tmp
 asl
 asl
 sta bird_tmp2
 asl
 asl
 ora bird_tmp
 sta bird_random
 lda bird_round
 cmp #64
 bcc 1f
 lda #48
1: and #48
 lsr
 sta bird_tmp
 lda aliens_left
 sec
 sbc #1
 cmp #4
 bcc 2f
 lda #3
2: asl
 ora bird_tmp
 sta bird_tmp
 lda bird_elapsed
 asl
 asl
 and #32
 ora bird_tmp
 tay
 lda bird_formation,y
 sta bird_speed_cap
 lda bird_formation+1,y
 clc
 adc bird_tmp2
 and #248
 sta bird_target_delta
 rts

large_vertical:
 lda bird_scroll
 eor #255
 lsr
 lsr
 lsr
 sta bird_scroll_band
 lda bird_frame
 asl
 asl
 and #12
 sta bird_tmp
 lda bird_threshold
 cmp bird_climb_timer
 bcc large_climbing
 lda bird_descent
 and #3
 ora bird_tmp
 tay
 lda bird_descent
 lsr
 lsr
 and #7
 clc
 adc bird_scroll_steps,y
 sta bird_tmp
 lda bird_scroll
 sec
 sbc bird_tmp
 jmp large_scroll_store
large_climbing:
 lda bird_tmp
 clc
 adc bird_climb_speed
 tay
 lda bird_scroll
 clc
 adc bird_scroll_steps,y
large_scroll_store:
 sta bird_scroll
 lda bird_frame
 and #1
 bne large_vertical_schedule
 # Original reverse slot scan: ordinal zero is bird seven.
 lda #128
 sta bird_tmp
 lda #0
 sta bird_tmp2
 ldx #56
 ldy #0
large_vertical_scan:
 lda bird_records,x
 beq 1f
 lda bird_tmp
 bpl 2f
 sty bird_tmp
2: sty bird_tmp2
1: iny
 txa
 sec
 sbc #8
 tax
 bpl large_vertical_scan
 lda bird_scroll_band
 clc
 adc bird_tmp
 clc
 adc bird_tmp2
 and #31
 sta bird_height
 lda bird_tmp2
 sec
 sbc bird_tmp
 sta bird_span
 rts
large_vertical_schedule:
 lda bird_speed_cap
 ldx bird_elapsed
 cpx #24
 bcc 1f
 clc
 adc #1
1: cpx #16
 bcc 2f
 clc
 adc #1
2: # Small aliens count is zero throughout the large-bird waves.
 clc
 adc #1
 ldx bird_height
 cmp bird_descent_caps,x
 bcc 3f
 lda bird_descent_caps,x
3: ldx aliens_left
 cpx #4
 bcs 4f
 clc
 adc #1
4: cpx #2
 bcs 5f
 clc
 adc #1
5: sta bird_descent
 lda bird_climb_timer
 beq large_schedule_climb
 dec bird_climb_timer
 rts
large_schedule_climb:
 lda bird_height
 cmp #22
 bcs 9f
 cmp #8
 bcc 9f
 sec
 sbc bird_span
 asl
 adc #0
 sta bird_tmp
 lda bird_random
 and #3
 sta bird_climb_speed
 eor #3
 clc
 adc #1
 tax
 clc
 adc bird_tmp
 clc
 adc bird_tmp
 dex
 beq 6f
 clc
 adc bird_tmp
 dex
 beq 6f
 clc
 adc bird_tmp
 dex
 beq 6f
 asl
6: sta bird_climb_timer
 lda #8
 sec
 sbc aliens_left
 asl
 clc
 adc bird_elapsed
 asl
 sta bird_tmp
 lda bird_random
 and #30
 clc
 adc bird_tmp
 sta bird_threshold
9: rts

large_behavior:
 lda bird_records,x
 bne 1f
 rts
1: asl
 asl
 asl
 sta bird_script
 lda bird_records+4,x
 beq 2f
 dec bird_records+4,x
2: ldy bird_script
 lda bird_scripts+6,y
 cmp #0x35
 beq large_behavior_move
 # Original animation increments the 3-bit shape phase every other update.
 lda bird_records+4,x
 and #1
 bne large_behavior_continue
 inc bird_records+3,x
 lda bird_records+3,x
 and #7
 sta bird_records+3,x
 jmp large_behavior_continue
large_behavior_move:
 jsr large_move_phase
large_behavior_continue:
 ldy bird_script
 lda bird_scripts+5,y
 cmp #0xcc
 beq large_behavior_done
 lda bird_records+4,x
 bne large_behavior_done
 lda bird_scripts+5,y
 cmp #0xd2
 beq large_behavior_transform
 lda bird_records+6,x
 and #15
 bne large_behavior_done
large_behavior_transform:
 lda bird_scripts,y
 sta bird_records+4,x
 lda bird_scripts+2,y
 sta bird_records,x
 lda bird_scripts+5,y
 cmp #0x0a
 bne large_behavior_done
 lda bird_random
 and bird_scripts+3,y
 and #240
 bne large_behavior_done
 lda bird_scripts+3,y
 and #15
 sta bird_records,x
 lda bird_scripts+1,y
 sta bird_records+4,x
large_behavior_done:
 rts
large_move_phase:
 lda bird_records+6,x
 cmp #16
 bcc 8f
 jmp large_move_left
8:
 sta bird_step
 clc
 adc bird_records+5,x
 sta bird_records+5,x
 lda bird_step
 clc
 adc bird_records+3,x
 sta bird_records+3,x
 cmp #8
 bcs large_move_right_cell
 lda bird_step
 beq 8f
 jmp large_move_return
8:
 inc bird_records+6,x
large_move_return:
 rts
large_move_right_cell:
 and #7
 sta bird_records+3,x
 lda bird_records+2,x
 sec
 sbc #32
 sta bird_records+2,x
 bcs 1f
 dec bird_records+1,x
1: lda #16
 sta bird_records+6,x
 lda bird_records+7,x
 sec
 sbc bird_records+5,x
 beq large_aim_left
 sec
 sbc #1
 lsr
 lsr
 lsr
 cmp bird_step
 php
 clc
 adc #1
 sta bird_records+6,x
 plp
 bcs 8f
 jmp large_move_return
8:
 lda bird_speed_cap
 sta bird_records+6,x
 cmp bird_step
 bne 8f
 jmp large_move_return
8:
 lda bird_step
 clc
 adc #1
 sta bird_records+6,x
 rts
large_aim_left:
 lda raw_ship_x
 and #248
 cmp bird_records+5,x
 bcc 1f
 lda bird_records+5,x
1: sta bird_tmp
 lda bird_target_delta
 clc
 adc #8
 sta bird_target_delta
 lda #8
 sta bird_records+7,x
 # Calculate with the pre-increment delta, retaining the original borrow.
 lda bird_target_delta
 sec
 sbc #8
 sta bird_tmp2
 lda bird_tmp
 sec
 sbc bird_tmp2
 bcs 8f
 jmp large_move_return
8:
 cmp #8
 bcs 8f
 jmp large_move_return
8:
 sta bird_records+7,x
 rts
large_move_left:
 and #15
 bne large_move_left_step
 lda #17
 sta bird_records+6,x
 dec bird_records+5,x
 lda #7
 sta bird_records+3,x
 jmp large_move_left_cell_only
large_move_left_step:
 sta bird_step
 lda bird_records+5,x
 sec
 sbc bird_step
 sta bird_records+5,x
 lda bird_records+3,x
 sec
 sbc bird_step
 sta bird_records+3,x
 bcc large_move_left_cell
 lda bird_records+5,x
 cmp bird_records+7,x
 beq 8f
 jmp large_move_return
8:
 lda #0
 sta bird_records+6,x
 lda raw_ship_x
 and #248
 cmp bird_records+5,x
 bcs 1f
 lda bird_records+5,x
1: sta bird_tmp
 lda bird_target_delta
 clc
 adc #8
 sta bird_target_delta
 lda #200
 sta bird_records+7,x
 lda bird_target_delta
 clc
 adc bird_tmp
 bcc 8f
 jmp large_move_return
8:
 cmp #200
 bcc 8f
 jmp large_move_return
8:
 sta bird_records+7,x
 rts
large_move_left_cell:
 and #7
 sta bird_records+3,x
 jsr large_move_left_cell_only
 lda bird_records+5,x
 sec
 sbc bird_records+7,x
 lsr
 lsr
 lsr
 cmp bird_step
 php
 clc
 adc #1
 sta bird_tmp
 plp
 bcc 2f
 lda bird_speed_cap
 cmp bird_step
 beq 1f
 lda bird_step
 clc
 adc #1
1: sta bird_tmp
2: lda bird_tmp
 ora #16
 sta bird_records+6,x
 rts
large_move_left_cell_only:
 lda bird_records+2,x
 clc
 adc #32
 sta bird_records+2,x
 bcc 1f
 inc bird_records+1,x
1: rts

.section .tables,"a",@progbits
bird_initial_data: .incbin "build/bird_data_alt_page.bin"
.section .tables,"a",@progbits
bird_formation: .incbin "build/bird_formation_params.bin"
bird_scroll_steps: .incbin "build/bird_scroll_steps.bin"
bird_descent_caps: .incbin "build/bird_descent_caps.bin"
bird_scripts: .incbin "build/bird_behaviour_scripts.bin"
.section .expanded_code,"ax",@progbits
# The arcade reuses its projectile test at alternating ship edges when the
# flock enters the low band. Preserve the real shot while testing the ship.
large_ship_contact:
 lda invuln
 bne large_ship_done
 lda bird_scroll_band
 sec
 sbc #player_explosion_row
 cmp #17
 bcs large_ship_done
 lda shot_on
 pha
 lda raw_shot_x
 pha
 lda raw_shot_y
 pha
 lda bird_frame
 and #1
 tax
 lda ship_left,x
 sta raw_shot_x
 lda #player_raw_y
 sta raw_shot_y
 lda #1
 sta shot_on
 jsr large_collision
 lda shot_on
 beq large_ship_hit
 lda #player_raw_y+8
 sta raw_shot_y
 jsr large_collision
 lda shot_on
 bne large_ship_restore
large_ship_hit:
 lda shield_count
 cmp #192
 bcc 1f
 dec shield_count
 jmp large_ship_restore
1: jsr damage_player
large_ship_restore:
 pla
 sta raw_shot_y
 pla
 sta raw_shot_x
 pla
 sta shot_on
large_ship_done:
 rts
