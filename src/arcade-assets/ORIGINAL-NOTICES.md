# Attribution and source scope

Original Phoenix arcade game code, ROM data, graphics and tunes retain their
original ownership. This port does not claim ownership of those materials or
grant redistribution rights in them. Public availability of this port does not change those ownership or
license exclusions, or imply that the original game is open source.

The C starting point is `hhi/org.hhi.phoenix-arcade`, revision
`d58adc3f5fe6fd8dc3745100010eecb755f6d7ba`. Its original-contribution MIT license
and detailed exclusions are preserved as `upstream-LICENSE` and
`upstream-THIRD_PARTY_NOTICES.md`. Those exclusions remain applicable to the
derived C game logic and extracted data. Source address annotations and
upstream attribution have been preserved.

Computer Archeology's Phoenix disassembly and RAM documentation were used
to investigate instruction boundaries, structures and control flow:
https://computerarcheology.com/Arcade/Phoenix/

MAME source references included here identify BSD-3-Clause licensing:

- `phoenix.cpp`: Richard Davies.
- `phoenix_a.cpp`: Juergen Buchmueller and Derrick Renaud.
- `tms36xx.cpp`: Juergen Buchmueller.
- `phoenix_v.cpp`: copyright holders stated in its original file header.

Their original file headers remain intact. The derived tune and circuit
tables retain this attribution. A copy of the BSD-3-Clause terms is included
as `MAME-BSD-3-Clause.txt`. The HHi sound-model lineage is detailed in its
preserved third-party notices; no broader relicensing claim is made.

The optional test dependency under `vendor/atari800-test-source.tar.gz` is
Atari800 7.2.1 source under GPL-2.0-or-later. Its COPYING and original notices
are included in that archive. The local change adds the `hg_monitor_write`
observation call to the memory write macros, enabling deterministic fixture
injection and trace capture. The emulator is not linked into or included in
the Atari cartridge.

The 5200 port uses LLVM-MOS as an external build tool; its binaries are not
included. The optional emulator screenshots are direct cartridge output.
The external AltirraOS 5200 test ROM retains its permissive license in
`tests/fixtures/LICENSE-Altirra.txt`. Original Atari BIOS is not bundled.
