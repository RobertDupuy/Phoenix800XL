ENTRY(entry)
MEMORY { ROM (rx) : ORIGIN = 0x4000, LENGTH = 0x8000
 PLATFORM (rx) : ORIGIN = 0xc000, LENGTH = 0x1000 }
SECTIONS {
 .text 0x4000 : { *(.text) *(.renderer) *(.startup) *(.rodata) *(.tables) *(.display) *(.intro_lists) *(.ship_audio) fixed_end = .; } > ROM
 .expanded 0x8000 : { *(.large_code) *(.expanded_code) *(.large_data) *(.native_data) *(.effects) *(.shield_code) *(.font) *(.bank0_data) *(.ship_audio_expanded) expanded_end = .; } > ROM
 .platform 0xc000 : { *(.platform) *(.platform_assets) platform_end = .; } > PLATFORM
 .header 0xbfe8 : { *(.header) } > ROM
 pattern_base_a = alien_movement_cluster_a >> 8;
 pattern_base_b = alien_movement_cluster_b >> 8;
 /DISCARD/ : { *(.comment) *(.llvm_addrsig) *(.bird_data) }
}
