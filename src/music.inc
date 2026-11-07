# Complete MM6221AA tune selection and two discrete oscillator approximations.
# The circuit cannot have identical analogue timbre on POKEY; pitches, tune
# sequences, RC envelopes and control-byte cadence come from the reference.
.set music_pending,0x6e0
.set music_fraction,0x6e4
.set music_ticks,0x6ea
.set music_active,0x6ec
.set g_sound_a,0x3e30
.set g_sound_b,0x3e31
.set audio_age,0x3e32
.set audio_bird_stage,0x3e34
.set audio_bird_count,0x3e35
.set audio_shot_pending,0x3e40
.set audio_hit_pending,0x3e41
.set audio_death_pending,0x3e42
.set audio_wing_pending,0x3e43
.set audio_shot_count,0x3e44
.set audio_hit_count,0x3e45
.set audio_death_count,0x3e46
.set audio_wing_count,0x3e47
.set audio_shield_count,0x3e48
.set audio_impact_count,0x3e49
.set audio_bonus_count,0x3e4a
.set audio_victory_count,0x3e4b
.section .expanded_code,"ax",@progbits
.global music_update,music_compute,audio_prepare,music_tick,audio_controls,audio_select_tune
music_compute:
 lda music_pending
 beq audio_clock
 lda #0
 sta music_pending
 sta music_fraction
 sta music_fraction+1
 sta audio_age
 sta audio_age+1
 ldx #0x4f
1: sta 0x3e00,x
 dex
 bpl 1b
 lda #15
 sta g_sound_a
 lda #0xcf
 sta g_sound_b
 lda #1
 sta music_active
audio_clock:
 clc
 lda music_fraction
 adc #<1217
 sta music_fraction
 lda music_fraction+1
 adc #>1217
 sta music_fraction+1
 bcc audio_once
 jsr music_tick
audio_once:
 jsr music_tick
 rts
music_tick:
 inc music_ticks
 bne 1f
 inc music_ticks+1
1: jsr audio_controls
 jmp audio_tick
# A=0..3 selects the MM6221AA tune through the original sound latch.
audio_select_tune:
 and #3
 asl
 asl
 asl
 asl
 asl
 asl
 sta 0x72
 lda g_sound_b
 and #63
 ora 0x72
 sta g_sound_b
 rts
.section .expanded_code,"ax",@progbits
audio_controls:
 lda #15
 sta g_sound_a
 lda g_sound_b
 ora #15
 sta g_sound_b
 inc audio_age
 bne 1f
 inc audio_age+1
1: lda state
 cmp #1
 beq 2f
 jmp audio_events
2:
 lda wave_wait
 ora wipe_timer
 ora entrance_timer
 beq 3f
 jmp audio_events
3:
 lda large_mode
 cmp #3
 beq audio_mothership
 lda large_mode
 beq audio_small
 lda aliens_left
 bne 4f
 jmp audio_events
4:
 lda audio_bird_stage
 and #1
 asl
 asl
 ora #32
 sta 0x72
 lda g_sound_b
 and #192
 ora 0x72
 sta g_sound_b
 lda audio_bird_count
 inc audio_bird_count
 cmp #0
 beq audio_bird_pulse
 ldx bird_height
 lda bird_cadence,x
 cmp audio_bird_count
 bcs audio_events
 lda #0
 sta audio_bird_count
 beq audio_events
audio_bird_pulse:
 inc audio_bird_stage
 lda g_sound_b
 ora #16
 sta g_sound_b
 bne audio_events
audio_mothership:
 lda boss_status
 cmp #1
 bne 1f
 # The small-bird clock is stopped during descent. Use the actual entry
 # countdown so the arrival modulation advances while the ship descends.
 lda #10
 sta g_sound_b
 lda boss_timer
 eor #255
 and #96
 bne audio_events
 lda boss_timer
 eor #255
 and #2
 clc
 adc #28
 sta g_sound_b
 jmp audio_events
1: lda boss_status
 cmp #2
 bne audio_events
audio_small:
 ldx #15
 ldy #0
1: lda enemy_on,x
 beq 2f
 # Arcade $3A98 tests the shape byte, not Y: $20..$27 are formation.
 lda enemy_shape,x
 cmp #0x28
 bcc 2f
 iny
2: dex
 bpl 1b
 cpy #0
 beq audio_events
 cpy #8
 bcc 3f
 ldy #8
3: tya
 clc
 adc #0x25
 sta 0x72
 lda g_sound_a
 and #192
 ora 0x72
 sta g_sound_a
audio_events:
 lda audio_bonus_count
 beq 7f
 dec audio_bonus_count
 # The bonus life is still awarded. Consume its timer silently during the
 # victory melody, so its repeating beep cannot play now or be queued later.
 ldx audio_victory_count
 bne 7f
 ldx tune
 cpx #2
 beq 7f
 and #8
 ora #7
 sta g_sound_b
7:
 lda audio_shield_count
 beq 8f
 dec audio_shield_count
 lda audio_shield_count
 and #6
 asl
 sta g_sound_b
8:
 lda audio_hit_pending
 beq 1f
 lda #0
 sta audio_hit_pending
 sta audio_impact_count
 lda #32
 sta audio_hit_count
1: lda audio_wing_pending
 beq 2f
 lda #0
 sta audio_wing_pending
 sta audio_impact_count
 lda #16
 sta audio_wing_count
2: lda audio_hit_count
 beq audio_wing
 dec audio_hit_count
 lda audio_hit_count
 asl
 asl
 eor #255
 and #14
 sta g_sound_b
 jmp audio_shot
audio_wing:
 lda audio_wing_count
 beq audio_impact
 dec audio_wing_count
 lda audio_wing_count
 lsr
 eor #255
 and #7
 ora #16
 sta g_sound_a
 jmp audio_shot
audio_impact:
 lda audio_impact_count
 beq audio_shot
 dec audio_impact_count
 lda g_sound_a
 and #8
 ora #4
 sta g_sound_a
audio_shot:
 lda audio_shot_pending
 beq 1f
 lda #0
 sta audio_shot_pending
 lda #25
 sta audio_shot_count
1: lda audio_death_pending
 beq 2f
 sta audio_death_count
 sta noise_death_kind
 lda #0
 sta audio_death_pending
2: lda audio_death_count
 beq 3f
 dec audio_death_count
 lda #0x8f
 sta g_sound_a
 jmp audio_controls_done
3: lda audio_shot_count
 beq audio_controls_done
 cmp #25
 bcc 4f
 dec audio_shot_count
 lda g_sound_a
 and #191
 sta g_sound_a
 jmp audio_controls_done
4: dec audio_shot_count
 lda g_sound_a
 ora #64
 sta g_sound_a
audio_controls_done:
 # Arcade $255B/$3923 reasserts tune 2 while the score-display counter runs.
 # Extra-life beeps must not erase the melody by overwriting sound latch B.
 lda audio_victory_count
 beq 7f
 dec audio_victory_count
 lda g_sound_b
 and #63
 ora #128
 sta g_sound_b
7:
 lda boss_status
 cmp #3
 bcs 1f
 lda large_mode
 beq 8f
 lda bird_elapsed
 jmp 9f
8: lda arcade_clock+1
9:
 cmp #3
 bcc 1f
 lda g_sound_b
 and #63
 sta g_sound_b
1: rts
.include "src/audio_driver.inc"
.section .tables,"a",@progbits
.include "build/audio-tables.inc"
bird_cadence: .incbin "build/bird_sound_cadence.bin"

# Queue three frames for small birds, four for supplied large-bird art,
# and six for the heavier mothership and transitions.
# The eight-slot ring has room for seven frames. Its separate AUDCTL bytes must
# not overlap the eight-register slots. The VBI only publishes registers.
.set audio_head,0x3ef0
.set audio_tail,0x3ef1
.set audio_underruns,0x3ef2
.set audio_last_controls,0x3ec8
.section .text,"ax",@progbits
music_update:
 lda audio_tail
 cmp audio_head
 bne audio_publish
 jmp audio_underrun
audio_publish:
 asl
 asl
 asl
 tax
 .irp r,0,1,2,3,4,5,6,7
 lda 0x3e80+\r,x
 sta 0xd200+\r
 .if (\r & 1)
 sta audio_last_controls+(\r / 2)
 .endif
 .endr
 ldy audio_tail
 lda 0x3ec0,y
 sta 0xd208
 lda #2
 sta 0xd20f
 inc audio_tail
 lda audio_tail
 and #7
 sta audio_tail
audio_publish_done:
 rts
.section .text,"ax",@progbits
audio_underrun:
 # A delayed foreground frame must never leave an oscillator stuck on.
 # Fade the last published volumes without touching foreground scratch.
 inc audio_underruns
 bne 1f
 inc audio_underruns+1
1:
 .irp v,0,1,2,3
 lda audio_last_controls+\v
 and #15
 beq 2f
 dec audio_last_controls+\v
2: lda audio_last_controls+\v
 sta 0xd201+\v*2
 .endr
 rts
.section .expanded_code,"ax",@progbits
audio_prepare:
 lda audio_head
 sec
 sbc audio_tail
 and #7
 ldx wave_wait
 bne audio_boss_budget
 ldx wipe_timer
 bne audio_boss_budget
 ldx large_mode
 beq audio_small_budget
 cpx #3
 beq audio_boss_budget
 cmp #4
 bcs audio_prepared
 bcc audio_compute_frame
audio_small_budget:
 cmp #3
 bcs audio_prepared
 bcc audio_compute_frame
audio_boss_budget:
 cmp #6
 bcs audio_prepared
audio_compute_frame:
 jsr music_compute
 lda audio_head
 asl
 asl
 asl
 tax
 .irp r,0,1,2,3,4,5,6,7
 lda 0x3e60+\r
 sta 0x3e80+\r,x
 .endr
 ldy audio_head
 lda 0x3e68
 sta 0x3ec0,y
 inc audio_head
 lda audio_head
 and #7
 sta audio_head
 jmp audio_prepare
audio_prepared:
 rts
