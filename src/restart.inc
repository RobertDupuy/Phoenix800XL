# Three seconds at the arcade logical tick rate; release then press fire.
.section .shield_code,"ax",@progbits
gameover_tick:
 lda gameover_timer
 beq gameover_wait_release
 dec gameover_timer
 lda #0
 sta fire_edge
 rts
gameover_wait_release:
 lda fire_now
 bne gameover_wait_press
 lda #1
 sta gameover_armed
 rts
gameover_wait_press:
 lda gameover_armed
 beq gameover_wait_done
 lda fire_edge
 beq gameover_wait_done
 # Disable DLI and both display engines before shared fonts/maps are reused.
 # VBI keeps input/audio running, and reveals only the first completed frame.
 lda #1
 sta restart_blank
 lda #64
 sta 0xd40e
 lda #0
 sta 0xd400
 sta 0xd01d
 sta display_active
 sta render_ready
 sta gameover_armed
 ldx #0
restart_clear_maps:
 .irp page,0x2800,0x2900,0x2a00,0x2b00,0x2c00,0x2d00,0x2e00,0x2f00
 sta \page,x
 .endr
 inx
 bne restart_clear_maps
 jsr game_reset
 inc starts
 bne gameover_wait_done
 inc starts+1
gameover_wait_done:
 rts
