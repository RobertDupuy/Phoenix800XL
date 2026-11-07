ENTRY(victory_entries)
SECTIONS {
 .victory 0xa000 : { *(.victory) }
 /DISCARD/ : { *(.comment) *(.llvm_addrsig) }
}
