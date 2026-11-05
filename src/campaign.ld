ENTRY(boss_entries)
SECTIONS {
 .code 0x8000 : { *(.boss_code) boss_code_end = .; }
 .data 0xa800 : { *(.boss_data) boss_data_end = .; }
 /DISCARD/ : { *(.comment) *(.llvm_addrsig) }
}
