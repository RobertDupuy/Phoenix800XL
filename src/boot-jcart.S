# J(atari)Cart boots bank zero at $A000-$BFFF. No ROM occupies $8000.
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
 lda #0x3c
 sta 0xd303
 lda #0xfe
 sta 0xd301
 ldx #0
xl_platform_copy:
 .irp page,0,256,512,768,1024,1280,1536,1792,2048,2304,2560,2816,3072,3328,3584,3840
 lda 0xa000+\page,x
 sta 0xc000+\page,x
 .endr
 inx
 bne xl_platform_copy
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
 ldx #1
 lda #0x40
 ldy #0x60
 jsr xl_copy_bank
 ldx #2
 lda #0x60
 ldy #0x80
 jsr xl_copy_bank
 ldx #3
 lda #0x80
 ldy #0xa0
 jsr xl_copy_bank
 ldx #5
 lda #0xe3
 ldy #0xff
 jsr xl_copy_bank
 ldx #6
 lda #0xd8
 ldy #0xdd
 jsr xl_copy_bank
 sta 0xd504
 jmp entry
xl_copy_bank:
 sta 0xd500,x
 sta 0x73
 sty xl_copy_limit+1
 lda #0xa0
 sta 0x71
 lda #0
 sta 0x70
 sta 0x72
 tay
xl_copy_page:
 lda (0x70),y
 sta (0x72),y
 iny
 bne xl_copy_page
 inc 0x71
 inc 0x73
 lda 0x73
xl_copy_limit:
 cmp #0
 bne xl_copy_page
 rts
xl_loader_end:
.section .cart_tail,"ax",@progbits
 lda #0
 sta 0xd500
 jmp xl_boot
 .fill 0x29-8,1,0xff
 rts
 .word 0xbfd0
 .byte 0,4
 .word 0xbff9
