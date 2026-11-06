.set tune,15872
.set tune_pos,15873
.set env0,15874
.set env1,15875
.set fr0,15876
.set fr1,15877
.set noise_env,15878
.set old_noise,15879
.set music_phase,15880
.set audio_ticks,15882
.set mod_phase,15884
.set slow_phase,15886
.set mod_level,15888
.set c22_level,15889
.set c7_level,15890
.set product_low,15891
.set product_high,15892
.set product_bits,15893
.set cap_delta,15894
.set noise_shot_level,15895
.set noise_death_level,15896
.set noise_death_kind,15897
.set noise_extra_freq,15898
.set noise_extra_control,15899
.section .text,"ax",@progbits
.global audio_tick
audio_tick:
 lda g_sound_b
 lsr
 lsr
 lsr
 lsr
 lsr
 lsr
 cmp tune
 beq audio_tune_clock
 sta tune
 lda #0
 sta tune_pos
 sta env0
 sta env1
 lda #0x11
 sta music_phase
 lda #0x32
 sta music_phase+1
audio_tune_clock:
 clc
 lda music_phase
 adc #0xe8
 sta music_phase
 lda music_phase+1
 adc #3
 sta music_phase+1
 cmp #0x32
 bcc audio_envelopes
 bne audio_next_note
 lda music_phase
 cmp #0x11
 bcc audio_envelopes
audio_next_note:
 sec
 lda music_phase
 sbc #0x11
 sta music_phase
 lda music_phase+1
 sbc #0x32
 sta music_phase+1
 lda tune
 beq audio_envelopes
 ldx tune_pos
 cpx #96
 bcs audio_envelopes
 sec
 sbc #1

audio_music_address:
 asl
 tax
 lda music_ptr,x
 sta 0x70
 lda music_ptr+1,x
 sta 0x71
 lda tune_pos
 asl
 tay
 lda (0x70),y
 beq audio_voice1
 sta fr0
 lda #31
 sta env0
audio_voice1:
 iny
 lda (0x70),y
 beq audio_note_done
 sta fr1
 lda #64
 sta env1
audio_note_done:
 inc tune_pos
audio_envelopes:
 lda env0
 beq audio_env1
 dec env0
audio_env1:
 lda env1
 beq audio_music_output
 dec env1
audio_music_output:
 lda fr0
 sta 0x3e60
 ldx env0
 lda volume0,x
 sta 0x3e61
 lda fr1
 sta 0x3e62
 ldx env1
 lda volume1,x
 sta 0x3e63
 jsr audio_circuit
 jsr audio_pitch_a
 sta 0x3e64
 ldx #0
 cmp #64
 bcc 1f
 ldx #32
1: stx 0x3e68
 lda g_sound_a
 and #15
 cmp #15
 beq audio_fx_a_silent
 lda g_sound_a
 and #32
 beq audio_fx_a_loud
 lda #0xa4
 bne audio_fx_a_volume
audio_fx_a_loud:
 lda #0xa8
 bne audio_fx_a_volume
audio_fx_a_silent:
 lda #0
audio_fx_a_volume:
 sta 0x3e65
audio_fx_b:
 jsr audio_pitch_b
 sta 0x3e66
 lda g_sound_b
 and #15
 cmp #15
 beq audio_fx_b_silent
 lda g_sound_b
 and #32
 beq audio_fx_b_tone
 # The original filter attenuates a tone; it is not a noise generator.
 ldx 0x3e66
 lda audio_filter_volume,x
 bne audio_fx_b_volume
audio_fx_b_tone:
 lda #0xa8
 bne audio_fx_b_volume
audio_fx_b_silent:
 lda #0
audio_fx_b_volume:
 sta 0x3e67
 # Soften the arrival on POKEY: the cabinet's filtered oscillator becomes
 # a harsh square wave here. Keep its cadence, two octaves lower and quiet.
 lda boss_status
 cmp #1
 bne audio_mix_noise
 lda 0x3e66
 asl
 bcs audio_entry_lowest
 asl
 bcs audio_entry_lowest
 ora #3
 bne audio_entry_pitch
audio_entry_lowest:
 lda #255
audio_entry_pitch:
 sta 0x3e66
 lda 0x3e67
 and #15
 beq audio_mix_noise
 lda #0xa3
 sta 0x3e67
audio_mix_noise:
 jsr audio_noise
 bcc audio_output_done
 # Noise must not erase the large-bird pulse on every shot. Borrow an
 # idle voice, keeping both music channels when their notes are sounding.
 lda 0x3e63
 and #15
 beq audio_noise_voice2
 lda 0x3e65
 and #15
 beq audio_noise_voice3
 lda 0x3e61
 and #15
 beq audio_noise_voice1
 ldx #6
 bne audio_noise_store
audio_noise_voice1:
 ldx #0
 beq audio_noise_store
audio_noise_voice3:
 lda #0
 sta 0x3e68
 ldx #4
 bne audio_noise_store
audio_noise_voice2:
 ldx #2
audio_noise_store:
 lda 0x3e69
 sta 0x3e60,x
 lda 0x3e6a
 sta 0x3e61,x
 jsr audio_extra_mix
audio_output_done:

 inc audio_ticks
 bne audio_return
 inc audio_ticks+1
audio_return:
 rts
music_ptr:
 .word music_ntsc,music_ntsc+192,music_ntsc+384

# Continuous modulation. Oscillator duty ratios and RC targets come from
# the original resistor/capacitor network. Mode 0's above-frame-rate
# oscillator is averaged; the three slow modes retain their phase.
audio_circuit:
 lda g_sound_a
 lsr
 lsr
 lsr
 lsr
 and #3
 tax
 clc
 lda mod_phase
 adc mod_step_lo,x
 sta mod_phase
 lda mod_phase+1
 adc mod_step_hi,x
 sta mod_phase+1
 ldy #2
 cpx #0
 beq audio_mod_level
 ldy #0
 cmp #152
 bcs audio_mod_level
 iny
audio_mod_level:
 sty mod_level
 clc
 lda slow_phase
 adc #0xf4
 sta slow_phase
 lda slow_phase+1
 adc #3
 sta slow_phase+1
 cmp #171
 tya
 rol
 tax
 lda c22_target,x
 sec
 sbc c22_level
 bcc audio_rc_fall
 tax
 lda audio_rc,x
 clc
 adc c22_level
 jmp audio_rc_store
audio_rc_fall:
 eor #255
 clc
 adc #1
 tax
 lda c22_level
 sec
 sbc audio_rc,x
audio_rc_store:
 sta c22_level
 lda g_sound_b
 and #16
 beq audio_c7_charge
 lda #28
 bne audio_c7_store
audio_c7_charge:
 ldx c7_level
 lda audio_c7,x
audio_c7_store:
 sta c7_level
 rts

audio_pitch_a:
 lda mod_level
 clc
 adc #>audio_vco_a
 sta 0x71
 lda c22_level
 and #240
 sta 0x70
 lda g_sound_a
 and #15
 ora 0x70
 tay
 lda #0
 sta 0x70
 lda (0x70),y
 rts
audio_pitch_b:
 lda c7_level
 lsr
 lsr
 lsr
 lsr
 lsr
 lsr
 clc
 adc #>audio_vco_b
 sta 0x71
 lda c7_level
 asl
 asl
 and #240
 sta 0x70
 lda g_sound_b
 and #15
 ora 0x70
 tay
 lda #0
 sta 0x70
 lda (0x70),y
 rts

.section .bank0_data,"a",@progbits
.balign 256
audio_rc: .incbin "build/audio-lookup.bin"
.set audio_c7,audio_rc+256
.set audio_vco_a,audio_rc+512
.set audio_vco_b,audio_rc+1280
audio_noise_tables: .incbin "build/audio-noise.bin"
.set audio_shot_charge,audio_noise_tables
.set audio_shot_release,audio_noise_tables+64
.set audio_noise_frequency,audio_noise_tables+128
.set audio_noise_volume,audio_noise_tables+256
.set audio_filter_volume,audio_noise_tables+320
.section .tables,"a",@progbits
audio_death_charge8: .incbin "build/death-charge-8bit.bin"
.section .bank0_data,"a",@progbits
audio_death_release8: .incbin "build/death-release-8bit.bin"

.section .expanded_code,"ax",@progbits
# The arcade holds and releases capacitor envelopes; they are not triggered
# linear chirps. Death has the reference's much lower, roughly 400 Hz noise.
audio_noise:
 lda #0
 sta noise_extra_control
 ldx noise_shot_level
 lda g_sound_a
 and #64
 beq 1f
 lda audio_shot_charge,x
 jmp 2f
1: lda audio_shot_release,x
2: sta noise_shot_level
 ldx noise_death_level
 lda g_sound_a
 and #128
 beq 3f
 lda audio_death_charge8,x
 jmp 4f
3: lda audio_death_release8,x
4: sta noise_death_level
 # Keep capacitor precision until the final conversion to POKEY volume.
 lsr
 lsr
 tax
 jsr audio_ship_noise
 bcs 6f
 txa
 cmp noise_shot_level
 bcc 5f
 tax
 lda #159
 bne 6f
5: ldx noise_shot_level
 lda audio_noise_frequency,x
6: sta 0x3e69
 lda audio_noise_volume,x
 beq 7f
 sta 0x3e6a
 sec
 rts
7: clc
 rts

# C24 and C25 are summed in the arcade. A returning gunshot must not replace
# the player's decaying low-frequency blast. Keep that blast as the primary
# noise and add C24 on an idle voice, with both capacitors setting its clock.
# Append helpers after aligned data so this fix does not move graphics pages.
.section .ship_audio_expanded,"ax",@progbits
audio_ship_noise:
 lda noise_death_kind
 cmp #16
 bne 1f
 lda audio_noise_volume,x
 and #15
 beq 1f
 ldy noise_shot_level
 lda audio_noise_volume,y
 and #15
 beq 1f
 ora #0x80
 sta noise_extra_control
 txa
 clc
 adc noise_shot_level
 tay
 lda audio_noise_frequency,y
 sta noise_extra_freq
 lda #159
 sec
 rts
1: clc
 rts

.section .ship_audio,"ax",@progbits
audio_extra_mix:
 lda noise_extra_control
 beq 3f
 ldx #6
1: lda 0x3e61,x
 and #15
 beq 2f
 dex
 dex
 bpl 1b
 rts
2: cpx #4
 bne 4f
 lda 0x3e68
 and #223
 sta 0x3e68
4: lda noise_extra_freq
 sta 0x3e60,x
 lda noise_extra_control
 sta 0x3e61,x
3: rts
