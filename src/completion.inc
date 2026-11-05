# Additions to the verified small-bird foundation. Startup data preparation
# runs with ANTIC/NMI disabled, before fresh gameplay frames are scheduled.
.set start_requested,0x760
.set burst_score,0x76c
.set bonus_count,0x770
.set bonus_score,0x772
.set bonus_x,0x774
.set bonus_y,0x776
.set bonus_shown,0x778
.set bonus_digits,0x77a
.set bonus_old_row,0x77c
.set bonus_slot,0x784
.set bonus_distance,0x785
.set bonus_half,0x786
.set bonus_value,0x787
.section .expanded_code,"ax",@progbits
.global bomb_collision_one
bomb_collision_one:
 lda invuln
 bne bomb_one_done
 lda raw_bomb_y,x
 cmp #220
 bcc bomb_one_done
 cmp #233
 bcs bomb_one_done
 lda raw_bomb_x,x
 cmp ship_left
 bcc bomb_one_done
 beq bomb_one_done
 cmp ship_right
 beq bomb_one_hit
 bcs bomb_one_done
bomb_one_hit:
 txa
 pha
 jsr damage_player
 pla
 tax
bomb_one_done:
 rts
.section .text,"ax",@progbits
.global expand_startup_fonts,prepare_gameplay
expand_startup_fonts:
 lda #<intro_fonts
 sta src_data
 lda #>intro_fonts
 sta src_data+1
 lda #0
 sta dst_ptr
 lda #0x10
 sta dst_ptr+1
startup_unpack_packet:
 jsr startup_get_byte
 tax
 bmi startup_unpack_run
 inx
startup_unpack_literal:
 jsr startup_get_byte
 jsr startup_put_byte
 dex
 bne startup_unpack_literal
 jmp startup_unpack_next
startup_unpack_run:
 and #127
 tax
 inx
 jsr startup_get_byte
startup_unpack_repeat:
 jsr startup_put_byte
 dex
 bne startup_unpack_repeat
startup_unpack_next:
 lda src_data+1
 cmp #>intro_fonts_end
 bne startup_unpack_packet
 lda src_data
 cmp #<intro_fonts_end
 bne startup_unpack_packet
 rts

.section .expanded_code,"ax",@progbits
.global score_service,set_hit_counter,clear_bonus,draw_bonus
set_hit_counter:
 ldy 0x38e
 bpl set_normal_counter
 pha
 tya
 and #1
 tay
 pla
 sta bonus_count,y
 rts
set_normal_counter:
 sta burst_count,y
 rts
score_service:
 ldx #1
score_normal_slot:
 lda burst_count,x
 cmp #1
 bne score_normal_next
 lda burst_score,x
 beq score_normal_next
 pha
 lda #0
 sta burst_score,x
 txa
 pha
 tsx
 lda 0x102,x
 jsr score_add
 pla
 tax
 pla
score_normal_next:
 dex
 bpl score_normal_slot
 ldx #1
score_bonus_slot:
 lda bonus_count,x
 cmp #1
 bne score_bonus_next
 lda bonus_score,x
 beq score_bonus_next
 pha
 lda #0
 sta bonus_score,x
 txa
 pha
 tsx
 lda 0x102,x
 jsr score_add
 pla
 tax
 pla
score_bonus_next:
 dex
 bpl score_bonus_slot
 jmp deferred_score_service

# Erase only the two previous wings and the three numeral cells. All birds
# and effects are rebuilt afterwards, so overlapping old footprints are safe.
clear_bonus:
 lda back_buffer
 asl
 sta bonus_slot
 clc
 adc #2
 sta bonus_half
bonus_clear_next:
 ldx bonus_slot
 lda bonus_old_row,x
 beq bonus_clear_skip
 sec
 sbc #1
 sta draw_row
 lda 0x3c00,x
 sta draw_col
 jsr clear_bonus_wing
 ldx bonus_slot
 lda 0x3c04,x
 sta draw_col
 jsr clear_bonus_wing
 ldx bonus_slot
 lda 0x3c08,x
 sta draw_col
 jsr row_pointer
 lda #0
 sta tile_index
bonus_clear_number:
 lda draw_row
 cmp #25
 bcs bonus_clear_number_next
 lda draw_col
 clc
 adc tile_index
 cmp #7
 bcc bonus_clear_number_next
 cmp #33
 bcs bonus_clear_number_next
 ldy tile_index
 lda #0
 sta (map_ptr),y
bonus_clear_number_next:
 inc tile_index
 lda tile_index
 cmp #3
 bcc bonus_clear_number
bonus_clear_skip:
 ldx bonus_slot
 lda #0
 sta bonus_old_row,x
 inc bonus_slot
 lda bonus_slot
 cmp bonus_half
 bcc bonus_clear_next
 rts
clear_bonus_wing:
 jsr row_pointer
 lda draw_col
 cmp #7
 bcc bonus_clear_wing_slow
 cmp #31
 bcs bonus_clear_wing_slow
 lda draw_row
 cmp #24
 bcs bonus_clear_wing_slow
 lda #0
 .irp off,0,32,1,33,2,34
 ldy #\off
 sta (map_ptr),y
 .endr
 rts
bonus_clear_wing_slow:
 lda #0
 sta tile_index
bonus_clear_wing_cell:
 jsr burst_clip
 bcs bonus_clear_wing_next
 lda #0
 sta (map_ptr),y
bonus_clear_wing_next:
 inc tile_index
 lda tile_index
 cmp #6
 bcc bonus_clear_wing_cell
 rts

draw_bonus:
 lda state
 cmp #1
 beq bonus_begin
 cmp #3
 beq 1f
 rts
1:
 lda death_timer
 cmp #33
 bcs 1f
 rts
1:
bonus_begin:
 lda #0
 sta bonus_slot
bonus_draw_slot:
 ldx bonus_slot
 lda bonus_count,x
 beq bonus_next_slot
 lda bonus_shown,x
 beq bonus_next_slot
 lda bonus_y,x
 sta draw_row
 clc
 adc #1
 pha
 lda back_buffer
 asl
 clc
 adc bonus_slot
 tax
 pla
 sta bonus_old_row,x
 ldx bonus_slot
 lda #15
 sec
 sbc bonus_shown,x
 and #14
 lsr
 sta bonus_distance
 lda bonus_x,x
 sec
 sbc #3
 sec
 sbc bonus_distance
 sta draw_col
 jsr bonus_footprint_index
 lda draw_col
 sta 0x3c00,x
 lda #0
 sta bonus_half
 jsr draw_bonus_half
 ldx bonus_slot
 lda bonus_x,x
 clc
 adc bonus_distance
 adc #1
 sta draw_col
 jsr bonus_footprint_index
 lda draw_col
 sta 0x3c04,x
 ldx bonus_slot
 lda bonus_x,x
 sec
 sbc #1
 pha
 jsr bonus_footprint_index
 pla
 sta 0x3c08,x
 lda #6
 sta bonus_half
 jsr draw_bonus_half
 ldx bonus_slot
 lda bonus_digits,x
 beq bonus_next_slot
 jsr draw_bonus_number
bonus_next_slot:
 inc bonus_slot
 lda bonus_slot
 cmp #2
 bcs bonus_done
 jmp bonus_draw_slot
bonus_done:
 rts
bonus_footprint_index:
 lda back_buffer
 asl
 clc
 adc bonus_slot
 tax
 rts
draw_bonus_half:
 jsr row_pointer
 lda draw_col
 cmp #7
 bcc bonus_half_slow
 cmp #31
 bcs bonus_half_slow
 lda draw_row
 cmp #24
 bcs bonus_half_slow
 .set cell,0
 .irp off,0,32,1,33,2,34
 ldx bonus_half
 lda bonus_parts+cell,x
 sta draw_template
 tax
 ldy #\off
 jsr stamp_tile
 .set cell,cell+1
 .endr
 rts
bonus_half_slow:
 lda #0
 sta tile_index
bonus_half_cell:
 jsr burst_clip
 bcs bonus_half_skip
 lda tile_index
 clc
 adc bonus_half
 tax
 lda bonus_parts,x
 sta draw_template
 tax
 jsr stamp_tile
bonus_half_skip:
 inc tile_index
 lda tile_index
 cmp #6
 bcc bonus_half_cell
 rts
draw_bonus_number:
 lda bonus_x,x
 sec
 sbc #1
 sta draw_col
 lda #0
 sta bonus_half
 lda bonus_value,x
1: cmp #10
 bcc bonus_number_ready
 sec
 sbc #10
 inc bonus_half
 jmp 1b
bonus_number_ready:
 sta bonus_distance
 lda #0
 sta tile_index
bonus_number_cell:
 lda draw_col
 cmp #7
 bcc bonus_number_skip
 cmp #33
 bcs bonus_number_skip
 lda draw_row
 cmp #25
 bcs bonus_number_skip
 jsr row_pointer
 ldx tile_index
 lda #0
 cpx #2
 beq bonus_number_glyph
 cpx #0
 bne 1f
 lda bonus_half
 jmp bonus_number_glyph
1:
 lda bonus_distance
bonus_number_glyph:
 tax
 lda bonus_numbers,x
 sta draw_template
 tax
 ldy #0
 jsr stamp_tile
bonus_number_skip:
 inc draw_col
 inc tile_index
 lda tile_index
 cmp #3
 bcc bonus_number_cell
 rts
.section .effects,"a",@progbits
bonus_parts: .incbin "build/bonus-parts.bin"
bonus_numbers: .incbin "build/bonus-numbers.bin"
.section .expanded_code,"ax",@progbits
.section .text,"ax",@progbits
startup_get_byte:
 ldy #0
 lda (src_data),y
 inc src_data
 bne 1f
 inc src_data+1
1:
 rts
startup_put_byte:
 ldy #0
 sta (dst_ptr),y
 inc dst_ptr
 bne 1f
 inc dst_ptr+1
1:
 rts
prepare_gameplay:
 lda #0
 sta 0xd40e
 sta 0xd400
 sta start_requested
 # The startup fonts borrowed this RAM. Clear it before any game display.
 ldx #0
clear_startup_ram:
 .irp page,0x1000,0x1100,0x1200,0x1300,0x1400,0x1500,0x1600,0x1700,0x1800,0x1900,0x1a00,0x1b00,0x1c00,0x1d00,0x1e00,0x1f00,0x2000,0x2100,0x2200,0x2300,0x2400,0x2500,0x2600,0x2700,0x2800,0x2900,0x2a00,0x2b00,0x2c00,0x2d00,0x2e00,0x2f00,0x3000,0x3100,0x3200,0x3300,0x3400,0x3500,0x3600,0x3700,0x3800,0x3900,0x3a00,0x3b00
 sta \page,x
 .endr
 inx
 beq startup_ram_cleared
 jmp clear_startup_ram
startup_ram_cleared:
 jsr renderer_init
 jsr hardware_init
 jsr shield_reset
 jsr enter_gameplay
 lda #0xc0
 sta 0xd40e
 rts


.section .expanded_code,"ax",@progbits
.set screen_enemy_x,0x38c0
.set screen_enemy_y,0x38d0
.global refresh_alien_screen
refresh_alien_screen:
 ldx #15
1:
 lda raw_enemy_x,x
 and #248
 sta screen_enemy_x,x
 lda raw_enemy_y,x
 and #248
 sta screen_enemy_y,x
 dex
 bpl 1b
 rts
