ENTRY(victory_entries)
SECTIONS {
 .victory 0x8000 : { *(.victory) }
 /DISCARD/ : { *(.comment) *(.llvm_addrsig) }
}
