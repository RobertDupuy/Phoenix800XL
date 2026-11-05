# Raw arcade-unit player coordinates; only display projection uses 3:4 mapping.
.set raw_ship_x,0xa5
.set raw_shot_x,0xa6
.set raw_shot_y,0xa7
.set arcade_fraction,0xa8
.set bonus_stage,0xaa
.set ship_left,0xab
.set ship_right,0xac
.section .rodata,"a",@progbits
map_x:
 .set x,0
 .rept 256
 .if (50+x*3/4)>255
 .byte 255
 .else
 .byte (50+x*3/4)
 .endif
 .set x,x+1
 .endr
map_y:
 .set y,0
 .rept 256
 .if (34+y*3/4)>255
 .byte 255
 .else
 .byte (34+y*3/4)
 .endif
 .set y,y+1
 .endr
player_x_position_mapping: .byte 0,8,1,9,2,10,3,11,3,11,2,10,1,9,0,8
