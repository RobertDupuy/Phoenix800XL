# Third-Party Notices and Provenance

This document records known third-party material, references, and code
lineage in Phoenix Arcade. It is a provenance inventory, **not** a grant of
rights in any third-party work. The root [LICENSE](LICENSE) applies MIT only
to original Phoenix Arcade contributions; its exclusions and the applicable
third-party terms take precedence. This inventory will be updated as the
licence review is completed.

## MAME

[MAME](https://www.mamedev.org/) is an important technical reference for the
Phoenix hardware, palette, and sound emulation. The MAME project states in its
[COPYING file](https://github.com/mamedev/mame/blob/master/COPYING) that MAME
as a whole is GPL-2.0-or-later, while individual source files can carry a
different, less restrictive licence in their own headers.

The following files declare MAME-derived or MAME-aligned lineage in their
source comments and require a source-by-source licence and notice review
before a project licence is selected:

- `jphoenix-emulator-port/Sound.java` and
  `c-phoenix/sound_discrete.c` / `sound_discrete.h`: discrete sound-netlist
  implementation, with the C version ported from the Java version.
- `jphoenix-emulator-port/TMS36XX.java` and
  `c-phoenix/tms36xx.c` / `tms36xx.h`: software model of the TMS36XX-family
  music chip, with the C version ported from the Java version.
- `jphoenix-emulator-port/MameLofiResampler.java` and
  `c-phoenix/mame_lofi_resampler.c` / `mame_lofi_resampler.h`: low-fidelity
  resampling implementation, with the C version ported from the Java version.
- `jphoenix-emulator-port/PhoenixPalette.java` and
  `c-phoenix/platform_sdl.c`: palette-decoding work described in the source
  as MAME-accurate and ported through the Java implementation.

Before publishing under a licence, trace each implementation to its upstream
MAME source file and revision, preserve the applicable header and notices, and
apply the terms of that specific source file. Do not assume that a name or a
technical comparison alone determines the licence.

## Earlier Phoenix and Java emulator work

`jphoenix-emulator-port/Phoenix.java` contains an existing attribution to
Murilo Saraiva de Queiroz, Richard Davies, the MAME project, Jasper (by Adam
Davidson and Andrew Pollard, stated there as used with permission), and Phoenix
hardware information from Ralph Kimmlingen. This attribution must remain
attached to its provenance review.

The original sources, permissions, and terms for material inherited from those
projects have not yet been fully reconstructed. No relicensing claim is made
for that material here.

## Computer Archeology

[Computer Archeology's Phoenix material](https://computerarcheology.com/Arcade/Phoenix/)
is cited through `c-phoenix/context/ComputerArcheology.md` in the annotated
hardware and graphics documentation. It is used as a research and attribution
source. Its pages remain subject to their own terms; copying text, diagrams, or
other expressive content requires separate review.

## Runtime dependencies

The optional Java frontend declares third-party dependencies through Gradle,
including LibGDX and LWJGL. They are not relicensed by this repository. A
distributed binary release must include the notices and licence information
required by the exact dependency versions that it ships.

## Phoenix game material and ROMs

Phoenix game code, graphics ROMs, colour PROMs, and other original arcade
assets are not covered by a Phoenix Arcade project licence. They require
separate rights or an authorised personal dump. This also applies to generated
or derived representations of such bytes: this repository grants no right to
redistribute them.

## Release checklist

Before making the repository public or selecting a project licence:

1. Complete the source-by-source provenance and licence review for all
   MAME-derived or possibly inherited code.
2. Preserve upstream copyright notices and add required licence texts or a
   distribution notice file.
3. Audit the current repository and its Git history for original ROM bytes,
   generated equivalents, or other material that may not be publicly
   redistributed.
4. Add a project `LICENSE` only after steps 1–3 establish what may be
   licensed and under which terms.
