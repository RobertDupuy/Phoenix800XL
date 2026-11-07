ENTRY(xl_boot)
SECTIONS {
 .boot 0xb000 : { *(.boot) }
 .loader 0x0700 : AT(0xb100) { *(.loader) }
 xl_loader_image = LOADADDR(.loader);
 .cart_tail 0xbfd0 : { *(.cart_tail) }
 /DISCARD/ : { *(.comment) *(.llvm_addrsig) }
}
