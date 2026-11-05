# Arcade death count: 96 logical ticks; particle/core writes occupy counts 95..33.
# The foreground clears at 32. Life deduction follows at zero. The next round
# waits 128 ticks, with separate setup/handoff ticks and score flashing.
.set death_timer,0x377
.set respawn_timer,0x378
.set explosion_left,0x379
.set effect_count,0xf8
.set effect_cursor,0xf9
.set effect_cell,0xfa
.set respawn_population,0x761
.set respawn_new_game,0x762
.set respawn_stage,0x765
.section .expanded_code,"ax",@progbits
.global death_tick,respawn_tick,draw_explosion
death_tick:
 lda death_timer
 and #1
 beq death_burst_done
 jsr burst_tick
death_burst_done:
 dec death_timer
 lda death_timer
 cmp #32
 bne death_keep_projectiles
 jsr clear_projectiles
death_keep_projectiles:
 lda death_timer
 bne death_tick_done
 dec lives
 lda #3
 sta life_dirty
 lda lives
 beq death_game_over
 lda #4
 sta state
 lda #0
 sta respawn_new_game
 lda #128
 sta respawn_timer
 lda #2
 sta respawn_stage
 rts
death_game_over:
 lda #2
 sta state
death_tick_done:
 rts
respawn_tick:
 lda #3
 sta hud_dirty
 lda respawn_stage
 cmp #2
 bne respawn_flash
 dec respawn_stage
 rts
respawn_flash:
 lda respawn_timer
 beq respawn_initialize
 dec respawn_timer
 rts
respawn_initialize:
 lda #100
 sta raw_ship_x
 sta video_ship_x
 lda #126
 sta ship_x
 lda #0
 sta invuln
 sta fire_edge
 lda #1
 sta state
 lda respawn_new_game
 beq respawn_survivors
 lda #0
 sta respawn_new_game
 jsr begin_wave
 lda #0
 sta entrance_initial_wait
 rts
respawn_survivors:
 jsr shield_reset
 lda large_mode
 cmp #3
 bne 8f
 jsr clear_projectiles
 jmp arcade_reset
8: lda large_mode
 beq respawn_small
 jmp large_resume
respawn_small:
 jsr arcade_resume
 rts
draw_explosion:
 lda #12
 sta effect_origin_y
 lda boss_picture_flag
 beq 8f
 lda #0
 sec
 sbc boss_scroll
 lsr
 lsr
 lsr
 and #31
 sta effect_origin_y
 lda #12
 sta effect_origin_x
 lda boss_timer
 jmp 9f
8:
 lda state
 cmp #3
 bne effect_done
 lda explosion_left
 sta effect_origin_x
 lda death_timer
9: sta effect_timer
 cmp #33
 bcc effect_done
 cmp #96
 bcs effect_done
 lda #95
 sec
 sbc effect_timer
 lsr
 tax
 lda explosion_index,x
 asl
 tax
 lda explosion_ptrs,x
 sta record_ptr
 lda explosion_ptrs+1,x
 sta record_ptr+1
 ldy #0
 lda (record_ptr),y
 sta effect_count
 lda #1
 sta effect_cursor
effect_cell_loop:
 ldy effect_cursor
 lda (record_ptr),y
 sta effect_cell
 and #15
 clc
 adc effect_origin_y
 sta draw_row
 iny
 lda (record_ptr),y
 sta draw_template
 iny
 sty effect_cursor
 lda draw_row
 cmp #25
 bcs effect_next
 lda effect_cell
 lsr
 lsr
 lsr
 lsr
 clc
 adc effect_origin_x
 cmp #7
 bcc effect_next
 cmp #33
 bcs effect_next
 sta draw_col
 jsr row_pointer
 ldx draw_template
 ldy #0
 jsr stamp_tile
effect_next:
 dec effect_count
 bne effect_cell_loop
effect_done:
 rts
.section .tables,"a",@progbits
explosion_index: .incbin "build/explosion-index.bin"
.include "build/explosion-pointers.inc"
.section .effects,"a",@progbits
.include "build/explosion-data.inc"
