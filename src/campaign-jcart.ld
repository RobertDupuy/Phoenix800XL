ENTRY(boss_entries)
SECTIONS {
 .code 0xa000 : { *(.boss_code) boss_code_end = .; }
 .data ALIGN(256) : { *(.boss_data) boss_data_end = .; }
 /DISCARD/ : { *(.comment) *(.llvm_addrsig) }
}
