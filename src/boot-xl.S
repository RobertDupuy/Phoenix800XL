# MegaCart bank zero occupies $8000-$BFFF after power-on.
# The resident game occupies $4000-$7FFF; banked data/code stay at $8000.
.include "build/main-symbols.inc"
.section .boot,"ax",@progbits
.global xl_boot,xl_cart_init,xl_loader,xl_loader_end
xl_cart_init:
 rts
xl_boot:
 sei
 cld
 lda #0
 sta 0xd40e
 sta 0xd400
 sta 0xd20e
 sta 0xd01d
 # Select the PIA data register, then disable OS, BASIC and self-test ROM.
 lda #0x3c
 sta 0xd303
 lda #0xfe
 sta 0xd301
 # Preserve the original code's addresses and its tightly timed raster code.
 ldx #0
xl_platform_copy:
 .irp page,0,256,512,768,1024,1280,1536,1792,2048,2304,2560,2816,3072,3328,3584,3840
 lda 0xa000+\page,x
 sta 0xc000+\page,x
 .endr
 inx
 bne xl_platform_copy
 # One-time copy of background phases and placement tables under the OS ROM.
 lda #0
 sta 0x70
 sta 0x72
 lda #0x80
 sta 0x71
 lda #0xe3
 sta 0x73
 ldy #0
xl_background_copy:
 lda (0x70),y
 sta (0x72),y
 iny
 bne xl_background_copy
 inc 0x71
 inc 0x73
 lda 0x73
 cmp #0xff
 bne xl_background_copy
 ldx #0
xl_loader_copy:
 lda xl_loader_image,x
 sta 0x700,x
 inx
 cpx #xl_loader_end-xl_loader
 bne xl_loader_copy
 jmp 0x700

.section .loader,"ax",@progbits
xl_loader:
 lda #1
 sta 0xd500
 lda #0
 sta 0x70
 sta 0x72
 lda #0x80
 sta 0x71
 lda #0x40
 sta 0x73
 ldy #0
xl_fixed_copy:
 lda (0x70),y
 sta (0x72),y
 iny
 bne xl_fixed_copy
 inc 0x71
 inc 0x73
 lda 0x73
 cmp #0x80
 bne xl_fixed_copy
 lda #2
 sta 0xd500
 jmp entry
xl_loader_end:

# Identical run stub in all runtime banks makes OS warm-start safe.
.section .cart_tail,"ax",@progbits
 lda #0
 sta 0xd500
 jmp xl_boot
 .fill 0x29-8,1,0xff
 rts
 .word 0xbfd0
 .byte 0,4
 .word 0xbff9
