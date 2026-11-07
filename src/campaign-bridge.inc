# Fixed-bank gates: all interrupt routines remain mapped during banked work.
.section .text,"ax",@progbits
.macro campaign_gate name,offset
\name:
 lda #3
 sta 0xd500
 jsr 0x8000+\offset
 pha
 lda #2
 sta 0xd500
 pla
 rts
.endm
campaign_gate campaign_choose,0
campaign_gate mothership_init,3
campaign_gate mothership_tick,6
campaign_gate mothership_background,9
campaign_gate campaign_wipe,12
campaign_gate campaign_layout,15
campaign_gate mothership_collision,18
campaign_gate mothership_stamp,21
campaign_gate arcade_bird_bomb,27

mothership_blast:
 lda #8
 sta 0xd500
 jsr 0x8000
 jmp victory_return
mothership_award:
 lda #8
 sta 0xd500
 jsr 0x8003
victory_return:
 lda #2
 sta 0xd500
 rts

.section .expanded_code,"ax",@progbits
campaign_reset:
 jsr campaign_choose
 lda cycle_stage
 cmp #4
 beq 1f
 jmp large_reset
1: jsr arcade_reset
 jmp mothership_init
campaign_tick:
 lda wipe_timer
 beq campaign_tick_play
 inc wipe_timer
 lda wipe_timer
 cmp #56
 bcc 1f
 lda #0
 sta wipe_timer
 jsr campaign_next
1: rts
campaign_tick_play:
 lda state
 cmp #1
 beq 7f
 jmp game_tick_regular
7:
 lda boss_status
 cmp #1
 bne 8f
 # The arcade arrival is a presentation phase, with no player controls.
 jsr mothership_tick
 jmp boss_discard_entry_input
8:
 cmp #2
 bne 9f
 lda boss_entrance_shown
 beq 9f
boss_discard_entry_input:
 lda #0
 sta fire_edge
 sta shield_edge
 rts
9:
 lda boss_status
 beq 2f
 jsr mothership_tick
 lda boss_score_pending
 beq 3f
 lda #0
 sta boss_score_pending
 ldx boss_award
 beq 8f
 stx boss_t3
4: lda #100
 jsr score_add
 dec boss_t3
 bne 4b
8: lda boss_award_low
 beq 3f
 sta boss_t3
5: lda #10
 jsr score_add
 dec boss_t3
 bne 5b
3: lda campaign_advance
 beq 2f
 inc waves_done
 bne 6f
 inc waves_done+1
6: jmp campaign_next
2: lda boss_status
 cmp #3
 bcc 7f
 rts
7: jmp game_tick_regular
campaign_next:
 inc wave
 lda wave
 cmp #81
 bcc 1f
 lda #1
 sta wave
1: jsr wave_reset
 jmp begin_wave
boss_shot_collision:
 # Escorts are drawn in front of the mothership and take a matching shot first.
 # Do not hit hidden birds during entry, explosion or the score display.
 lda boss_status
 cmp #2
 bne 1f
 jsr shot_collision
 jmp mothership_collision
1: rts
boss_play:
 lda boss_status
 cmp #2
 beq 1f
 rts
1: jsr arcade_step
 lda aliens_left
 bne 2f
 # Keep the last hit visible and let its award finish before replenishing.
 lda burst_count
 ora burst_count+1
 ora burst_count+2
 ora bonus_count
 ora bonus_count+1
 ora pending_scores
 bne 2f
 jsr arcade_reset
2: rts
boss_render:
 jsr mothership_background
 jsr pilot_prepare
 lda #0
 sta grouped_scene
 sta draw_index
 lda #1
 sta direct_scene
 lda boss_status
 cmp #2
 bne boss_render_effects
 lda state
 cmp #1
 beq boss_render_birds
 cmp #3
 bne boss_render_effects
boss_render_birds:
 ldx draw_index
 lda display_enemy_on,x
 beq 1f
 jsr draw_bird
1: inc draw_index
 lda draw_index
 cmp #16
 bcc boss_render_birds
boss_render_effects:
 jsr draw_bursts
 jsr draw_bonus
 jsr draw_explosion
 jsr draw_shield
 jsr draw_soft_bomb
 jsr draw_soft_shot
 jsr mothership_picture
 lda #32
 ldx back_buffer
 beq 1f
 lda #36
1: sta font_hi
 rts
campaign_render:
 jsr render_scene_regular
 lda wipe_timer
 beq 1f
 jsr campaign_wipe
1: rts

.section .text,"ax",@progbits
boss_copy_tile:
 lda #5
 sta 0xd500
 .irp row,0,1,2,3,4,5,6,7
 ldy #\row
 lda (src_data),y
 ora (boss_src2),y
 sta (dst_ptr),y
 .endr
 lda #3
 sta 0xd500
 rts

.section .text,"ax",@progbits
boss_load_atlas:
 lda #6
 sta 0xd500
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
 lda boss_fine
 asl
 clc
 adc #128
 sta src_data+1
 lda #0
 sta src_data
 ldx boss_fine
 lda boss_atlas_counts,x
 tax
 ldy #0
2:
 # Only 26..37 of the 64 atlas slots contain shapes. The maps never
 # reference the unused slots, and dynamic glyphs start at slot 64.
 .rept 8
 lda (src_data),y
 sta (dst_ptr),y
 iny
 .endr
 bne 3f
 inc src_data+1
 inc dst_ptr+1
3:
 dex
 bne 2b
 lda #3
 sta 0xd500
 rts

# Counts live immediately after the atlases in the same mapped ROM bank.
.set boss_atlas_counts,0x9000

.section .expanded_code,"ax",@progbits
mothership_picture:
 lda boss_status
 cmp #3
 bcc boss_picture_done
 bne boss_show_award
 lda boss_timer
 cmp #33
 bcc boss_show_award
 jmp mothership_blast
boss_picture_done:
 rts
boss_show_award:
 jmp mothership_award

.section .text,"ax",@progbits
# Six persistent caches share slots 64..127 with the current foreground.
boss_cache_select:
 lda back_buffer
 asl
 clc
 adc back_buffer
 sta boss_t3
 txa
 clc
 adc boss_t3
 tax
 lda boss_key_lo,x
 sta glyph_owner
 lda boss_key_hi,x
 sta glyph_owner+1
 lda boss_epoch_lo,x
 sta cache_ptr
 lda boss_epoch_hi,x
 sta cache_ptr+1
 rts
boss_allocate_glyph:
 jsr boss_cache_select
 ldy boss_free_cursor,x
1: cpy #64
 bcs 3f
 lda (cache_ptr),y
 cmp boss_cache_epoch
 bne 2f
 iny
 jmp 1b
3: inc layout_faults
 ldy #63
2: lda boss_cache_epoch
 sta (cache_ptr),y
 lda #255
 sta (glyph_owner),y
 iny
 tya
 sta boss_free_cursor,x
 dey
 tya
 clc
 adc #64
 rts
boss_key_lo: .byte 0,128,0,128,0,128
boss_key_hi: .byte 57,57,58,58,59,59
boss_epoch_lo: .byte 0,64,128,192,0,64
boss_epoch_hi: .byte 60,60,60,60,61,61
