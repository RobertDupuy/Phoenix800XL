# Eight arcade-derived birds with original shared vertical scrolling.
# Three character-font regions and two buffers cover all fine-Y offsets.
.set large_mode,0x33c
.set large_shown,0x33d
.set large_buffer,0x33e
.set large_dli_phase,0x78b
.set gameplay_color,0x78c
.set large_previous,0x3da0
.set large_clock,0x3800
.set large_bomber,0x3801
.set large_x,0x3810
.set large_dir,0x3818
.set large_age,0x3820
.set large_pose,0x3828
.set large_anim,0x3830
.set large_left,0x3840
.set large_right,0x3848
.set large_index,0x3850
.set large_src,0xb2
.set large_dst,0xb4
.set large_temp,0x3851
.set large_start,0xb6
.set large_end,0xb7
.set large_old_mode,0x3854
.set large_hit_x,0x3855
.set large_hit_y,0x3856
.set large_hit_count,0x3857
.set large_star_col,0x3858
.set large_star_byte,0x3859
# Foreground-only aliases of the small-wave engine's aptr/atmp scratch.
# NMI/DLI handlers do not use these bytes. Star merging reuses the spent mask.
.set large_mask,0xb6
.set large_mask_saved,0xb8
.set large_upper_effects,0x385e
.set large_ready,0x385f
.set large_base,0xa400
.section .large_code,"ax",@progbits
.global large_reset,large_tick,large_collision,large_render,large_resume
large_reset:
 lda large_mode
 sta large_old_mode
 lda cycle_stage
 cmp #2
 bcs large_reset_yes
 lda #0
 sta large_mode
 lda large_old_mode
 beq large_reset_small
 # Restore the approved small-wave resident glyphs and maps after wave four.
 jsr renderer_init
large_reset_small:
 jmp arcade_reset
large_reset_yes:
 pha
 lda #0
 sta large_ready
 sta large_buffer
 sta large_buffer+1
 lda #255
 ldx #15
large_previous_init:
 sta large_previous,x
 dex
 bpl large_previous_init
 pla
 sec
 sbc #1
 sta large_mode
 lda #0
 sta entrance_timer
 sta entrance_handoff
 sta large_clock
 sta large_bomber
 sta burst_count
 sta burst_count+1
 sta burst_count+2
 sta bonus_count
 sta bonus_count+1
 // level_round retains the complete round nibble
 ldx #15
large_reset_clear:
 sta enemy_on,x
 sta display_enemy_on,x
 dex
 bpl large_reset_clear
 lda #6
 sta aliens_left
 ldx #7
large_reset_slot:
 lda #1
 sta enemy_on,x
 txa
 and #1
 sta large_dir,x
 txa
 asl
 asl
 clc
 adc #112
 sta large_age,x
 lda large_initial_x,x
 sta large_x,x
 lda #0
 sta large_anim,x
 lda #6
 sta large_pose,x
 lda #0
 sta large_left,x
 sta large_right,x
 dex
 bpl large_reset_slot
 jsr large_motion_reset
 lda #0
 sta bird_records+48
 sta bird_records+56
 sta enemy_on+6
 sta enemy_on+7
 rts
large_resume:
 jsr clear_projectiles
 lda #0
 sta burst_count
 sta burst_count+1
 sta burst_count+2
 sta bonus_count
 sta bonus_count+1
 rts
large_tick:
 inc large_clock
 jsr large_motion_tick
 ldx #7
1: lda large_world_y,x
 sec
 sbc bird_scroll
 sta large_y,x
 lda large_left,x
 beq 2f
 dec large_left,x
2: lda large_right,x
 beq 3f
 dec large_right,x
3: dex
 bpl 1b
large_tick_effects:
 jsr large_collision
 jsr large_ship_contact
 lda bird_frame
 and #1
 beq 8f
 jsr burst_tick
 jmp large_tick_done
8: jsr bombs_update
 jsr arcade_bird_bomb
large_tick_done:
 rts

.section .text,"ax",@progbits
large_collision:
 lda shot_on
 bne large_collision_active
 rts
large_collision_active:
 ldx #7
large_collision_slot:
 lda enemy_on,x
 bne 8f
 jmp large_collision_next
8:
 lda raw_shot_x
 sec
 sbc large_x,x
 cmp #56
 bcc 8f
 jmp large_collision_next
8:
 sta large_hit_x
 lda raw_shot_y
 clc
 adc #7
 sec
 sbc large_y,x
 cmp #23
 bcc 8f
 jmp large_collision_next
8:
 stx large_index
 lda raw_shot_y
 sec
 sbc large_y,x
 sta large_hit_y
 lda #8
 sta large_hit_count
 # Pixel-test the swept eight-pixel projectile segment against this pose.
 lda large_pose,x
 clc
 adc #0x80
 sta large_src+1
 lda #0
 sta large_src
 jsr large_art_bank
large_collision_pixel:
 lda large_hit_y
 cmp #16
 bcs large_pixel_next
 sta large_temp
 lda large_hit_x
 and #248
 asl
 asl
 clc
 adc #8
 clc
 adc large_temp
 tay
 lda (large_src),y
 sta large_temp
 lda large_hit_x
 lsr
 and #3
 tay
 lda large_pixel_masks,y
 and large_temp
 bne large_pixel_hit
large_pixel_next:
 inc large_hit_y
 dec large_hit_count
 bne large_collision_pixel
 lda 0xbfc0
 lda 0xbfd0
 ldx large_index
large_collision_next:
 dex
 bmi large_collision_done
 jmp large_collision_slot
large_collision_done:
 rts
large_pixel_hit:
 lda 0xbfc0
 lda 0xbfd0
 ldx large_index
 lda enemy_on,x
 cmp #11
 bcc large_body_hit
 lda large_hit_x
 cmp #20
 bcc large_hit_left
 cmp #40
 bcs large_hit_right
large_body_hit:
 # Arcade 3844..389C: score depends on the actual growth type and timer.
 lda raw_shot_x
 and #248
 sta screen_enemy_x,x
 lda raw_shot_y
 and #248
 sta screen_enemy_y,x
 jsr large_score_value
 ldx large_index
 jsr kill_alien
 lda large_index
 asl
 asl
 asl
 tax
 lda #0
 sta bird_records,x
 jmp large_consume_shot
large_hit_left:
 lda large_left,x
 bne large_collision_done
 lda #180
 sta large_left,x
 bne large_wing_score
large_hit_right:
 lda large_right,x
 bne large_collision_done
 lda #180
 sta large_right,x
large_wing_score:
 lda #1
 sta audio_wing_pending
 lda #2
 jsr score_add
 lda #2
 sta sound_kind
 lda #8
 sta sound_time
large_consume_shot:
 lda #0
 sta shot_on
 rts

.section .large_code,"ax",@progbits
large_prepare_small:
 lda cycle_stage
 cmp #4
 bne large_prepare_done
 lda wave_wait
 cmp #48
 beq large_prepare_zero
 cmp #47
 bne large_prepare_done
 ldx #0
large_prepare_one:
 lda native_static,x
 sta 0x2400,x
 lda native_static+256,x
 sta 0x2500,x
 inx
 bne large_prepare_one
 lda #1
 sta large_ready
 rts
large_prepare_zero:
 ldx #0
large_prepare_zero_loop:
 lda native_static,x
 sta 0x2000,x
 lda native_static+256,x
 sta 0x2100,x
 inx
 bne large_prepare_zero_loop
large_prepare_done:
 rts
large_soft_source:
 rts

.section .text,"ax",@progbits
large_frame_palette:
 lda #70
 sta 0xc019
 lda #14
 sta playfield_c0
 lda #44
 sta playfield_c1
 lda large_shown
 cmp #3
 beq palette_boss
 cmp #2
 beq palette_large2
 cmp #1
 beq palette_large1
 lda entrance_shown
 beq palette_small
 lda #198
 bne palette_done
palette_small:
 lda level_round
 and #2
 beq palette_small1
 lda #92
 sta playfield_c0
 lda #200
 bne palette_done
palette_small1:
 lda #90
 bne palette_done
palette_boss:
 lda #134
 sta 0xc019
 lda #26
 sta playfield_c0
 lda #90
 bne palette_done
palette_large1:
 lda #172
 sta playfield_c0
 lda #134
 bne palette_done
palette_large2:
 lda #202
 sta playfield_c0
 lda #90
 sta playfield_c1
 lda #154
palette_done:
 sta gameplay_color
 rts
large_art_bank:
 lda large_mode
 cmp #2
 beq large_art_second
 lda 0xbfc0
 lda 0xbfd8
 rts
large_art_second:
 lda 0xbfc4
 lda 0xbfd4
 rts

.section .large_data,"a",@progbits
large_initial_x: .byte 8,104,48,128,24,80,140,56
.set large_y,0x3870
.set large_world_y,0x3878
large_band_rows: .byte 0,3,6,9,12,15,18,21
large_flap_order: .byte 0,1,2,3,4,5,4,3,2,1
large_awards: .byte 10,10,20,20,30,30,40,50
.section .tables,"a",@progbits
large_pixel_masks: .byte 192,48,12,3

.section .display,"a",@progbits
.macro large_list name,base
\name:
 .byte 0x70,0x44
 .word hud_map
 .byte 0x04,0x84,0x44
 .word \base
 .rept 6
 .byte 0x04
 .endr
 .byte 0x84
 .rept 7
 .byte 0x04
 .endr
 .byte 0x84
 .rept 9
 .byte 0x04
 .endr
 .byte 0x41
 .word \name
.endm
large_list large_list0,0x2800
large_list large_list1,0x2c00
large_dl: .word large_list0,large_list1

.section .expanded_code,"ax",@progbits
large_score_value:
 txa
 asl
 asl
 asl
 tay
 lda bird_records,y
 sta large_temp
 cmp #11
 bcs 1f
 lda #5
 rts
1: cmp #15
 bne 2f
 lda #10
 rts
2: lda bird_records+4,y
 lsr
 and #124
 clc
 adc #48
 ldx large_temp
 cpx #14
 beq 4f
 lsr
 cpx #12
 bcs 4f
 lsr
4: sta large_temp
 and #15
 cmp #10
 bcc 5f
 lda large_temp
 clc
 adc #6
 sta large_temp
5: lda large_temp
 cmp #154
 bcc 6f
 clc
 adc #96
 sta large_temp
6: lda large_temp
 lsr
 lsr
 lsr
 lsr
 asl
 sta temp2
 asl
 asl
 clc
 adc temp2
 sta temp2
 lda large_temp
 and #15
 clc
 adc temp2
 rts
