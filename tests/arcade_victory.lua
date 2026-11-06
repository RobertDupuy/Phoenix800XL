-- Explicit diagnostic fixture: original arcade mothership destruction at a
-- fixed aligned hit height. No port animation is used to generate this trace.
local m=manager.machine;local cpu=m.devices[':maincpu'];local mem=cpu.spaces['program']
local f=assert(io.open(os.getenv('PHOENIX_FIXTURE'),'rb'));local data=f:read('*a');f:close()
local dir=os.getenv('PHOENIX_OUT');local out=assert(io.open(dir..'/trace.bin','wb'));local frame=0
emu.register_frame_done(function()
 frame=frame+1
 if frame==30 then
  mem:write_u8(0x5000,2)
  for i=1,#data do mem:write_u8(0x3fff+i,data:byte(i)) end
  mem:write_u8(0x43a4,6);mem:write_u8(0x43a5,96)
  mem:write_u8(0x43b9,248);mem:write_u8(0x5800,248)
  mem:write_u8(0x4366,255)
  cpu.state['SP'].value=0x4bff;cpu.state['PC'].value=0x001d
 elseif frame>30 then
  out:write(string.pack('<I4',frame-30),mem:read_range(0x4000,0x4bff,8))
  if (frame-30)%4==1 then m.screens[':screen']:snapshot(dir..string.format('/frame-%03d.png',frame-30)) end
  if frame==210 then out:close();m:exit() end
 end
end)
