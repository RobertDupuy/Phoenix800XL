# Phoenix800XL v1.0 — based on Phoenix5200 v0.31.
# Seven large birds and five mothership escorts; standard 64 KiB XL/XE.
# All code executed by the console is NMOS 6502 assembly.
# Foreground builds buffered graphics independently of the arcade-rate clock.
# VBI samples input and publishes audio each video frame, committing ready graphics
# after at least two frames; busy scenes may use a third display frame.
.set simulation_frame,0x3ee0
.set simulation_delta,0x3ee1
.set state,       0x80 // 0 title, 1 playing, 2 game over
.set ship_x,      0x81
.set lives,       0x82
.set wave,        0x83
.set invuln,      0x84
.set fire_now,    0x85
.set fire_prev,   0x86
.set stick_x,     0x87
.set shot_on,     0x88
.set shot_x,      0x89
.set shot_y,      0x8a
.set shot_old_y,  0x8b
.set shot_old_on, 0x8c
.set phase,       0x8d
.set wave_wait,   0x8e
.set sound_time,  0x8f
.set sound_kind,  0x90
.set temp,        0x91
.set temp2,       0x92
.set banner_old,  0x93
.set intro_page,  0x94
.set intro_ticks, 0x95             // 16-bit counter, startup only
.set intro_next_font,0x97
.set ship_hpos,   0x98             // both ship layers share hide/blink position
.set ship_pose,   0x99             // last committed original animation pose
.set enemy_on,    0x0400 // sixteen entries per enemy array
.set enemy_x,     0x0410
.set enemy_y,     0x0420
.set enemy_dx,    0x0430
.set enemy_old_y, 0x0440
.set bomb_on,     0x0480
.set bomb_x,      0x0485
.set bomb_y,      0x048a
.set bomb_old_y,  0x048f
.set bomb_old_on, 0x0494
.set formation_clock,0x9c
.set formation_offset,0x9d
.set formation_dir,0x9e
.set formation_fraction,0x9f
.set bomb_clock,0xa0
.set bomb_source,0xa1
.set score_digits,0xc0 // six numeric decimal digits
.set frames,      0x300 // monotonically increasing 32-bit counters
.set commits,     0x304
.set late_frames, 0x308 // 16 bit; never reset on game restart
.set vbi_start,   0x30a
.set vbi_end,     0x30b
.set kills,       0x30c // 16-bit test telemetry
.set deaths,      0x30e
.set starts,      0x310
.set waves_done,  0x312
.set ready,       0x314
.set SC,          0x0800
.set MISSILES,    0x1300
.set SHIP,        0x1400
.set SHIP_RED,    0x1500           // P1: original red ship layer; no vertical sharing

.include "src/player-geometry.inc"
.include "src/campaign-defs.inc"
.section .text,"ax",@progbits
.global entry,nmi_handler,idle,frame_done
.global hardware_init,screen_init,game_reset,wave_reset,input_sample
.global game_tick,player_update,shot_update,bombs_update
.global shot_collision,bomb_collision,damage_player,wave_update,score_add
.global sound_update,render_players,render_missiles,render_hud,render_banner
.global animate_ship
.global irq_stub

entry:
 lda #2
 sta 0xd500
 sei
 cld
 ldx #255
 txs
 lda #0
 sta 0xd40e
 sta 0xd20e
 sta 0xd400
 ldx #0
clear_ram:
 # Sixteen KiB, fixed addresses: no zero-page pointer can clear itself.
 .irp page,0x0000,0x0100,0x0200,0x0300,0x0400,0x0500,0x0600,0x0700,0x0800,0x0900,0x0a00,0x0b00,0x0c00,0x0d00,0x0e00,0x0f00,0x1000,0x1100,0x1200,0x1300,0x1400,0x1500,0x1600,0x1700,0x1800,0x1900,0x1a00,0x1b00,0x1c00,0x1d00,0x1e00,0x1f00,0x2000,0x2100,0x2200,0x2300,0x2400,0x2500,0x2600,0x2700,0x2800,0x2900,0x2a00,0x2b00,0x2c00,0x2d00,0x2e00,0x2f00,0x3000,0x3100,0x3200,0x3300,0x3400,0x3500,0x3600,0x3700,0x3800,0x3900,0x3a00,0x3b00,0x3c00,0x3d00,0x3e00,0x3f00
 sta \page,x
 .endr
 inx
 beq clear_finished
 jmp clear_ram
clear_finished:
 jsr xl_install_interrupts
 ldx #15
 lda #127
init_footprints:
 sta 0x520,x
 sta 0x560,x
 dex
 bpl init_footprints
 jsr renderer_init
 jsr hardware_init
 jsr hud_init
 jsr game_reset
 lda #0
 sta state
 lda #255
 sta banner_old
 jsr render_banner
 jsr render_players
 jsr render_hud
 lda #1
 sta ready
 jsr startup_init
 .fill 7,1,0xea                   // retain the existing entry/idle layout
idle:
 lda start_requested
 beq idle_game
 lda #2
 sta 0xd500
 jsr prepare_gameplay
idle_game:
 lda work_due
 beq idle
 lda #0
 sta work_due
 lda #1
 sta render_busy
 jsr simulation_update
 jsr audio_prepare
 jsr render_scene
 jsr render_hud
 jsr render_banner
 inc sim_updates
 bne update_counted
 inc sim_updates+1
 bne update_counted
 inc sim_updates+2
 bne update_counted
 inc sim_updates+3
update_counted:
 lda frames
 sta pending_frame
 lda #1
 sta render_ready
 lda #0
 sta render_busy
 jmp idle
.global simulation_update
simulation_update:
 lda frames
 sec
 sbc simulation_frame
 sta simulation_delta
 lda frames
 sta simulation_frame
 lda simulation_delta
 bne 1f
 lda #2
1: cmp #9
 bcc 2f
 lda #8
2: sta simulation_delta
simulation_video_tick:
 jsr counted_tick
 clc
 lda arcade_fraction
 adc #<1217
 sta arcade_fraction
 lda arcade_fraction+1
 adc #>1217
 sta arcade_fraction+1
 bcc 3f
 jsr counted_tick
3: dec simulation_delta
 bne simulation_video_tick
substeps_done:
 jsr map_bombs
 lda #0
 sta fire_edge
 rts
counted_tick:
 jsr game_tick
 jsr score_service
 inc sim_steps
 bne counted_done
 inc sim_steps+1
 bne counted_done
 inc sim_steps+2
 bne counted_done
 inc sim_steps+3
counted_done:
 rts

hardware_init:
 ldx #31
 lda #0
clear_gtia:
 sta 0xd000,x
 dex
 bpl clear_gtia
 lda #<nmi_handler
 sta 0x202
 lda #>nmi_handler
 sta 0x203
 lda #<irq_stub
 sta 0x200
 sta 0x206
 lda #>irq_stub
 sta 0x201
 sta 0x207
 lda #<display_list
 sta 0xd402
 lda #>display_list
 sta 0xd403
 lda front_buffer
 asl
 asl
 clc
 adc #8
 sta 0xd409
 lda #2
 sta 0xd401
 lda #0x10
 sta 0xd407
 lda #3
 sta 0xd01d
 sta 0xd20f
 lda #8
 sta 0xd01f                    // silence the console speaker
 lda #0
 sta 0xd208
 sta 0xd20e
 sta 0xd201
 sta 0xd203
 sta 0xd205
 sta 0xd207
 sta 0xd404
 sta 0xd405
 lda #0x01                      // M0/M2/M3 use their white player colors
 sta 0xd01b
 lda #0x0e
 sta 0xd012
 sta 0xd017
 sta 0xd019
 lda #0x2c
 sta 0xd013
 lda #0x2c
 sta 0xd014
 lda #0x2c
 sta 0xd015
 lda #0
 sta 0xd018
 sta 0xd01a
 ldx #15
init_ship:
 lda ship_white,x
 sta SHIP+player_pm_y,x
 lda ship_red,x
 sta SHIP_RED+player_pm_y,x
 lda ship_yellow,x
 sta 0x1600+player_pm_y,x
 dex
 bpl init_ship
 ldx #7
init_static_glyphs:
 lda star_glyph_data,x
 sta 0x2008,x
 sta 0x2408,x
 dex
 bpl init_static_glyphs
 rts

screen_init:
 rts

game_reset:
 lda #0
 sta pending_scores
 sta pending_score_fault
 ldx #15
clear_pending_scores:
 sta pending_age,x
 sta pending_award,x
 dex
 bpl clear_pending_scores
 jsr high_score_update
 lda #1
 sta music_pending
 lda #1
 sta state
 sta wave
 lda #3
 sta lives
 lda #100
 sta raw_ship_x
 sta video_ship_x
 lda #126
 sta ship_x
 lda #0
 sta invuln
 sta shot_on
 sta wave_wait
 sta phase
 sta sound_time
 sta bonus_stage
 sta arcade_fraction
 sta arcade_fraction+1
 ldx #5
reset_score:
 sta score_digits,x
 dex
 bpl reset_score
 lda #3
 sta hud_dirty
 sta life_dirty
 jsr wave_reset
 lda #4
 sta state
 lda #128
 sta respawn_timer
 lda #1
 sta respawn_new_game
 sta respawn_stage
 lda #0
 sta entrance_timer
 sta entrance_initial_wait
 sta entrance_handoff
 rts

wave_reset:
 lda #0
 sta second_on
 sta shot_on
 jsr shield_reset
 jsr campaign_reset
 ldx #4
 lda #0
reset_bombs:
 sta bomb_on,x
 dex
 bpl reset_bombs
 rts


nmi_handler:
 pha
 txa
 pha
 tya
 pha
 cld
 lda 0xd40b
 sta vbi_start
 inc frames
 bne frame_count_done
 inc frames+1
 bne frame_count_done
 inc frames+2
 bne frame_count_done
 inc frames+3
frame_count_done:
 jsr input_sample
 jsr video_player_update
 jsr music_update
 lda #<playfield_dli
 sta 0x206
 lda #>playfield_dli
 sta 0x207
 lda #0x3e
 ldx restart_blank
 beq 1f
 lda #0
1:
 sta 0xd400
 # Every video frame begins with the original arcade HUD font/palette.
 lda front_buffer
 asl
 asl
 clc
 adc #8
 sta 0xd409
 lda #0xa8
 sta 0xd016
 lda #0x46
 sta 0xd017
 lda #0x5a
 sta 0xd018
 lda video_phase
 eor #1
 sta video_phase
 lda frames
 sec
 sbc last_commit
 cmp #2
 bcs commit_due
 jmp nmi_commit
commit_due:
 lda render_ready
 bne publish_frame
 lda display_active
 bne 6f
 jmp release_work
6:
 lda frames
 sec
 sbc last_commit
 cmp #4
 bcs 7f
 jmp release_work
7:
 inc missed_ready
 beq missed_high
 jmp release_work
missed_high:
 inc missed_ready+1
 jmp release_work
publish_frame:
 lda #0
 ldx boss_status
 cpx #1
 bne 1f
 lda #1
1: sta boss_entrance_shown
 lda entrance_timer
 sta entrance_shown
 lda #0x46
 sta 0xd019
 ldx back_buffer
 lda large_buffer,x
 sta large_shown
 lda back_buffer
 sta front_buffer
 asl
 asl
 clc
 adc #8
 sta 0xd409
 lda front_buffer
 asl
 tax
 lda large_shown
 beq publish_small_list
 cmp #3
 beq 1f
 lda supplied_dl,x
 sta 0xd402
 lda supplied_dl+1,x
 bne publish_list_high
1: lda large_dl,x
 sta 0xd402
 lda large_dl+1,x
 bne publish_list_high
publish_small_list:
 lda game_dl,x
 sta 0xd402
 lda game_dl+1,x
publish_list_high:
 sta 0xd403
 lda front_buffer
 asl
 asl
 clc
 adc #0x20
 sta large_dli_phase
 ldx large_shown
 beq publish_font_ready
 sec
 sbc #8
publish_font_ready:
 sta gameplay_font
 jsr render_players
 jsr render_missiles
 jsr pilot_commit

 lda restart_blank
 beq 1f
 lda #0
 sta restart_blank
 lda #3
 sta 0xd01d
 lda #0x3e
 sta 0xd400
 lda #0xc0
 sta 0xd40e
1:

 lda #0
 sta render_ready
 lda display_active
 beq first_commit
 lda frames
 sec
 sbc last_commit
 cmp #4
 bcc first_commit
 inc gap_errors
 bne first_commit
 inc gap_errors+1
first_commit:
 lda #1
 sta display_active
 lda frames
 sta last_commit
 inc fresh_commits
 bne release_work
 inc fresh_commits+1
 bne release_work
 inc fresh_commits+2
 bne release_work
 inc fresh_commits+3
release_work:
 lda render_busy
 ora render_ready
 bne nmi_commit
 lda #1
 sta work_due
.global nmi_commit
nmi_commit:
 jsr large_frame_palette
 jsr render_live_ship
 lda large_shown
 cmp #3
 bne 1f
 lda #0
 sta 0xd000
 sta 0xd001
 sta 0xd002
1:
 inc commits
 bne commit_count_done
 inc commits+1
 bne commit_count_done
 inc commits+2
 bne commit_count_done
 inc commits+3
commit_count_done:
 lda 0xd40b
 sta vbi_end
 # VBI starts at scanline248. The current HUD begins at scanline16.
 # Guard at scanline8, leaving eight scanlines for return/dispatch margin.
 cmp #124
 bcs frame_done
 cmp #4
 bcc frame_done
 inc late_frames
 bne frame_done
 inc late_frames+1
frame_done:
 pla
 tay
 pla
 tax
 pla
irq_stub:
 rti

game_tick:
 jmp campaign_tick
game_tick_regular:
 lda entrance_handoff
 beq 8f
 jmp entrance_finish
8:
 lda entrance_timer
 beq 9f
 jmp entrance_tick
9:
 lda state
 cmp #3
 bne 1f
 jmp death_tick
1:
 cmp #4
 bne 2f
 jmp respawn_tick
2:
 lda state
 cmp #2
 bne 8f
 jmp gameover_tick
8:
 cmp #1
 beq play_tick
 lda fire_edge
 beq game_tick_return
 jsr game_reset
 inc starts
 bne game_tick_return
 inc starts+1
game_tick_return:
 rts
play_tick:
 inc phase
 lda invuln
 beq no_invuln
 dec invuln
no_invuln:
 jsr player_update
 jsr player_shots
 lda large_mode
 cmp #3
 bne 8f
 jmp boss_play
8: beq tick_small_birds
 lda large_mode
 beq tick_small_birds
 jsr large_tick
 jmp tick_wave_update
tick_small_birds:
 jsr arcade_step
tick_wave_update:
 jsr wave_update
 rts

damage_player:
 lda state
 cmp #1
 bne damage_done
 lda invuln
 bne damage_done
 inc deaths
 bne death_count_done
 inc deaths+1
death_count_done:
 # Arcade $0CD0 seeds the player explosion with 16 ticks, not the
 # mothership's 64-tick pulse. Pending carries the event's own duration.
 lda #16
 sta audio_death_pending
 lda #3
 sta state
 sta sound_kind
 lda #96
 sta death_timer
 lda raw_ship_x
 lsr
 lsr
 lsr
 sta explosion_left
 lda #30
 sta sound_time
 lda #0
 sta fire_edge
damage_done:
 rts
.global clear_projectiles
clear_projectiles:
 lda #0
 sta shot_on
 sta second_on
 sta bomb_on
 sta bomb_on+1
 sta bomb_on+2
 sta bomb_on+3
 sta bomb_on+4
 rts

wave_update:
 lda state
 cmp #1
 bne wave_done
 ldx #15
wave_count_loop:
 lda enemy_on,x
 bne wave_done
 dex
 bpl wave_count_loop
 lda wave_wait
 bne wave_wait_tick
 lda #96
 sta wave_wait
 inc waves_done
 bne wave_wait_tick
 inc waves_done+1
wave_wait_tick:
 jsr large_prepare_small
 dec wave_wait
 bne wave_done
 lda cycle_stage
 beq 1f
 lda #1
 sta wipe_timer
 jsr clear_projectiles
 rts
1: jmp campaign_next
wave_done:
 rts

sound_update:
 rts


animate_ship:
 # Four exact supplied poses, three independent color planes.
 lda video_ship_x
 clc
 adc #4
 lsr
 and #3
 cmp ship_pose
 bne 1f
 rts
1: sta ship_pose
 asl
 asl
 asl
 asl
 tax
 .irp row,1,2,3,4,5,6,7,10,11,12,13,14,15
 lda ship_white+\row,x
 sta SHIP+player_pm_y+\row
 .endr
 .irp row,3,4,5,6,8,9,10,11,12,13,14
 lda ship_red+\row,x
 sta SHIP_RED+player_pm_y+\row
 .endr
ship_pose_done:
 rts

render_players:
 jsr boss_intro_pending
 bne ship_hide
 jsr shield_players
 bcc normal_ship_players
 jmp render_enemies
normal_ship_players:
 lda #44
 sta 0xd014
 jsr animate_ship
 lda #0x46
 sta 0xd013
 lda entrance_timer
 ora entrance_handoff
 bne ship_hide
 lda state
 cmp #1
 bne ship_hide
 lda invuln
 and #4
 bne ship_hide
 lda ship_x
 sta ship_hpos
 sta 0xd000
 sta 0xd001
 sta 0xd002
 jmp render_enemies
ship_hide:
 lda #0
 sta ship_hpos
 sta 0xd000
 sta 0xd001
 sta 0xd002
render_enemies:
 jsr render_extra_bombs
 rts

.macro extra_bomb n,base,hpos
 ldy bomb_old_y+\n
 lda #0
 sta \base,y
 sta \base+1,y
 sta \base+2,y
 lda bomb_on+\n
 beq .Lextra_hide\@
 lda bomb_y+\n
 cmp #238
 bcs .Lextra_hide\@
 ldy bomb_y+\n
 sty bomb_old_y+\n
 lda #128
 sta \base,y
 sta \base+1,y
 sta \base+2,y
 lda bomb_x+\n
 sta \hpos
 jmp .Lextra_done\@
.Lextra_hide\@:
 lda #0
 sta \hpos
.Lextra_done\@:
.endm
.global render_extra_bombs
render_extra_bombs:
 lda #0x0e
 sta 0xd015
 extra_bomb 4,0x1700,0xd003
 rts

.macro draw_missile active,xpos,ypos,oldy,oldon,mask,clear,hpos
 lda \oldon
 beq .Lmissile_clean\@
 ldy \oldy
 .irp row,0,1,2
 lda MISSILES+\row,y
 and #\clear
 sta MISSILES+\row,y
 .endr
.Lmissile_clean\@:
 lda \active
 beq .Lmissile_visible\@
 lda \ypos
 cmp #238
 bcc .Lmissile_visible\@
 lda #0
 jmp .Lmissile_active\@
.Lmissile_visible\@:
 lda \active
.Lmissile_active\@:
 sta \oldon
 bne .Lmissile_draw\@
 lda #0
 sta \hpos
 jmp .Lmissile_end\@
.Lmissile_draw\@:
 lda \xpos
 sta \hpos
 lda \ypos
 sta \oldy
 tay
 .irp row,0,1,2
 lda MISSILES+\row,y
 ora #\mask
 sta MISSILES+\row,y
 .endr
.Lmissile_end\@:
.endm

render_missiles:
 lda shot_on
 sta 0x6fc
 lda shield_pose
 cmp #255
 beq 1f
 lda #0
 sta 0x6fc
1:
 draw_missile 0x6fc,shot_x,shot_y,shot_old_y,shot_old_on,0x02,0xfc,0xd004
 # M1 shares the red ship layer's color. Its bomb is drawn in the character
 # buffer, freeing COLPF3 for the arcade's red explosion pixels.
 lda #0
 sta 0xd005
 draw_missile bomb_on+1,bomb_x+1,bomb_y+1,bomb_old_y+1,bomb_old_on+1,0x20,0xcf,0xd006
 draw_missile bomb_on+2,bomb_x+2,bomb_y+2,bomb_old_y+2,bomb_old_on+2,0x80,0x3f,0xd007
 rts

.section .rodata,"a",@progbits
.balign 64
ship_white: .incbin "build/ship-white.bin"
ship_red: .incbin "build/ship-red.bin"
ship_yellow: .incbin "build/ship-yellow.bin"
.set intro_fonts,0xa400
.set intro_maps,0xb800
.include "build/intro-size.inc"
.section .intro_lists,"a",@progbits
.macro intro_list name,map
\name:
 .byte 0x70,0x70,0x70
 .irp row,0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23
 .if (\row==3)||(\row==7)||(\row==11)||(\row==15)||(\row==18)||(\row==20)
 .byte 0xc4
 .else
 .byte 0x44
 .endif
 .word \map+40*\row
 .endr
 .byte 0x41
 .word \name
.endm
intro_list intro_title_dl,intro_maps
intro_list intro_scores_dl,intro_maps+1024

.section .startup,"ax",@progbits
.global startup_init,startup_nmi,startup_dli,startup_select,startup_fonts,enter_gameplay
startup_init:
 lda #0
 sta 0xd40e
 sta 0xd01d
 sta intro_page
 lda #5
 sta 0xd500
 jsr expand_startup_fonts
 lda #<startup_nmi
 sta 0x202
 lda #>startup_nmi
 sta 0x203
 lda #<startup_dli
 sta 0x206
 lda #>startup_dli
 sta 0x207
 lda #0xa8
 sta 0xd016
 lda #0x5a
 sta 0xd017
 lda #0x2c
 sta 0xd018
 lda #0x0e
 sta 0xd019
 jsr startup_select
 lda #0x22                      // wide playfield, no player/missile DMA
 sta 0xd400
 lda #0xc0                      // startup pages only
 sta 0xd40e
 rts

startup_select:
 lda intro_page
 asl
 tax
 lda intro_dl,x
 sta 0xd402
 lda intro_dl+1,x
 sta 0xd403
 lda #<300
 sta intro_ticks
 lda #>300
 sta intro_ticks+1
 jsr startup_fonts
 rts

startup_fonts:
 ldx intro_page
 lda intro_font_offsets,x
 tax
 lda intro_font_table,x
 sta 0xd409
 jsr startup_colors
 inx
 stx intro_next_font
 rts

startup_nmi:
 pha
 txa
 pha
 tya
 pha
 cld
 lda 0xd40b
 sta vbi_start
 inc frames
 bne intro_count_done
 inc frames+1
 bne intro_count_done
 inc frames+2
 bne intro_count_done
 inc frames+3
intro_count_done:
 jsr input_sample
 lda fire_now
 beq intro_wait
 lda fire_prev
 bne intro_wait
 lda #1
 sta start_requested
 jmp frame_done
intro_wait:
 lda intro_ticks
 ora intro_ticks+1
 bne intro_countdown
 lda intro_page
 eor #1
 sta intro_page
 jsr startup_select
 jmp frame_done
intro_countdown:
 lda intro_ticks
 bne intro_tick_low
 dec intro_ticks+1
intro_tick_low:
 dec intro_ticks
 jsr startup_fonts
 # The gameplay VBI tail changes COLPF3 for sprites. Startup owns its palette.
 jmp frame_done

startup_dli:
 pha
 txa
 pha
 ldx intro_next_font
 jsr startup_colors
 # Each entire page uses one font, selected in VBI. There is no CHBASE write
 # here: a late interrupt must never replace the top scanlines of a character.
 inc intro_next_font
 pla
 tax
 pla
 rti

startup_colors:
 # Palette changes have blank guard scanlines on both sides of the boundary.
 lda intro_maps+960,x
 sta 0xd016
 lda intro_maps+974,x
 sta 0xd017
 lda intro_maps+988,x
 sta 0xd018
 lda intro_maps+1002,x
 sta 0xd019
 rts

enter_gameplay:
 lda frames
 sta simulation_frame
 sta last_commit
 lda #<nmi_handler
 sta 0x202
 lda #>nmi_handler
 sta 0x203
 lda #<playfield_dli
 sta 0x206
 lda #>playfield_dli
 sta 0x207
 inc starts
 bne intro_start_counted
 inc starts+1
intro_start_counted:
 lda #1
 sta banner_old
 sta work_due
 lda #0
 sta front_buffer
 sta video_phase
 sta display_active
 sta render_ready
 lda #0x20
 sta gameplay_font
 lda #0x0e
 sta 0xd012
 sta 0xd016
 sta 0xd017
 sta 0xd018
 sta 0xd019
 lda #0x46
 sta 0xd013
 lda front_buffer
 asl
 asl
 clc
 adc #8
 sta 0xd409
 lda #<display_list
 sta 0xd402
 lda #>display_list
 sta 0xd403
 jsr render_players
 jsr render_hud
 lda #3
 sta 0xd01d
 lda #0x3e
 sta 0xd400
 rts

intro_dl: .word intro_title_dl,intro_scores_dl
intro_font_offsets: .byte 0,7
intro_font_table: .incbin "build/intro-font-table.bin"

.section .display,"a",@progbits
.macro game_list name,base
\name:
 .byte 0x70,0x44
 .word hud_map
 .byte 0x04,0x84
 .byte 0x44
 .word \base
 .rept 19
 .byte 0x04
 .endr
 .byte 0x84
 .rept 4
 .byte 0x04
 .endr
 .byte 0x41
 .word \name
.endm
game_list display_list,0x2800
game_list display_list_1,0x2c00
game_dl: .word display_list,display_list_1
# ANTIC receives the full LMS address; this 120-byte map needs no alignment.
hud_map:
 .set h,0
 .rept 120
 .byte h
 .set h,h+1
 .endr



.section .header,"a",@progbits
 .incbin "build/header.bin"
 .word entry

.include "src/renderer.inc"
.include "src/hud.inc"
.include "src/arcade.inc"
.include "src/safe-entry.inc"

.include "src/death.inc"
.include "src/restart.inc"
.include "src/bursts.inc"
.include "src/music.inc"
.include "src/projectile.inc"
.include "src/shield.inc"

.include "src/wave.inc"

.include "src/completion.inc"



.include "src/large.inc"

.include "src/large_motion.inc"

.include "src/large_renderer.inc"

.include "src/campaign-bridge.inc"

.include "src/pilot.inc"

.include "src/platform-xl.inc"

.include "src/xl-large-row.inc"
