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
 lda g_sound_a
 and #0xc0
 cmp old_noise
 beq audio_noise_decay
 sta old_noise
 cmp #0
 beq audio_noise_decay
 ldx #24
 and #128
 beq audio_noise_start
 ldx #48
audio_noise_start:
 stx noise_env
audio_noise_decay:
 ldx noise_env
 beq audio_fx_b
 dex
 stx noise_env
 lda noise_frequency,x
 sta 0x3e66
 lda noise_volume,x
 sta 0x3e67
 jmp audio_output_done
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
 lda #0xa4
 bne audio_fx_b_volume
audio_fx_b_tone:
 lda #0xa8
 bne audio_fx_b_volume
audio_fx_b_silent:
 lda #0
audio_fx_b_volume:
 sta 0x3e67
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
 txa
 clc
 adc #>audio_rc
 sta 0x71
 lda #0
 sta 0x70
 ldy c22_level
 lda (0x70),y
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
.set audio_c7,audio_rc+1536
.set audio_vco_a,audio_rc+1792
.set audio_vco_b,audio_rc+2560
