# Fixed switches retain the MegaCart instruction cost and register values.
# J(atari)Cart selects an 8 KiB bank by the ADDRESS of the write.
.macro xl_bank bank
 .if XL_JCART
  .if \bank == 2
   sta 0xd504
  .elseif \bank == 3
   sta 0xd507
  .elseif \bank == 5
   sta 0xd508
  .elseif \bank == 6
   sta 0xd50a
  .elseif \bank == 8
   sta 0xd50b
  .else
   .error "JCart switch requires an explicit data layout"
  .endif
 .else
  sta 0xd500
 .endif
.endm
