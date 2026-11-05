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
# A=0..3 provides every chip tune. Gameplay selects the original start cue;
# tune 2 remains available for the mothership award when that stage is added.
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
.section .text,"ax",@progbits
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
 bne audio_events
 lda large_mode
 cmp #3
 beq audio_small
 lda large_mode
 beq audio_small
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
audio_small:
 ldx #15
 ldy #0
1: lda enemy_on,x
 beq 2f
 lda enemy_kind,x
 beq 2f
 lda raw_enemy_y,x
 cmp #40
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
 lda audio_hit_pending
 beq 1f
 lda #0
 sta audio_hit_pending
 lda #32
 sta audio_hit_count
1: lda audio_wing_pending
 beq 2f
 lda #0
 sta audio_wing_pending
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
 beq audio_shot
 dec audio_wing_count
 lda audio_wing_count
 lsr
 eor #255
 and #7
 ora #16
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
 lda #0
 sta audio_death_pending
 lda #64
 sta audio_death_count
2: lda audio_death_count
 beq 3f
 dec audio_death_count
 lda #0x8f
 sta g_sound_a
 jmp audio_cancel_tune
3: lda audio_shot_count
 beq audio_cancel_tune
 cmp #25
 bcc 4f
 dec audio_shot_count
 lda g_sound_a
 and #191
 sta g_sound_a
 jmp audio_cancel_tune
4: dec audio_shot_count
 lda g_sound_a
 ora #64
 sta g_sound_a
audio_cancel_tune:
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

# Foreground keeps a three-frame queue filled. The VBI only publishes eight POKEY
# registers, so circuit multiplication can never run across the HUD deadline.
.set audio_head,0x3ef0
.set audio_tail,0x3ef1
.section .text,"ax",@progbits
music_update:
 lda audio_tail
 cmp audio_head
 beq audio_publish_done
 asl
 asl
 asl
 tax
 .irp r,0,1,2,3,4,5,6,7
 lda 0x3e80+\r,x
 sta 0xe800+\r
 .endr
 lda #0
 sta 0xe808
 lda #2
 sta 0xe80f
 inc audio_tail
 lda audio_tail
 and #3
 sta audio_tail
audio_publish_done:
 rts
.section .expanded_code,"ax",@progbits
audio_prepare:
 lda audio_head
 sec
 sbc audio_tail
 and #3
 cmp #3
 bcs audio_prepared
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
 inc audio_head
 lda audio_head
 and #3
 sta audio_head
 jmp audio_prepare
audio_prepared:
 rts
