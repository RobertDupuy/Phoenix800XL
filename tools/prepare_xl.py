"""Generate exact PMG copies with one load for rows equal in every pose."""
from collections import defaultdict
from pathlib import Path

B = Path(__file__).resolve().parents[1] / 'build'


def emit_copy(rows, output):
    groups = defaultdict(list)
    for values, source, destination in rows:
        groups[values].append((source, destination))
    code = ['# Generated from the unchanged packed artwork; every destination is written.']
    for values, group in groups.items():
        code.append(f' lda #{values[0]}' if len(set(values)) == 1 else f' lda {group[0][0]},x')
        code.extend(f' sta {destination}' for _, destination in group)
    (B / output).write_text('\n'.join(code) + '\n')


def prepare():
    green = (B / 'shield-green.bin').read_bytes()
    emit_copy([
        (tuple(green[pose * 64 + i] for pose in range(4)), f'shield_green+{i}',
         f'{"SHIP" if i < 32 else "SHIP_RED"}+player_shield_pm_y+{i % 32}')
        for i in range(64)
    ], 'xl-shield-copy.inc')
    rows = []
    descending_rows = []
    for name, base in [('cyan', 0x1400), ('purple', 0x1500), ('pink', 0x1600)]:
        plane = (B / f'pilot-{name}.bin').read_bytes()
        for row in range(16):
            item = (tuple(plane[pose * 16 + row] for pose in range(4)),
                    f'pilot_{name}+{row}', f'{base + row},y')
            rows.append(item)
            # On a one-line descent, only new ink or old ink one row below
            # can alter this destination. Other bytes are already zero.
            if any(item[0]) or (row < 15 and any(plane[pose*16+row+1] for pose in range(4))):
                descending_rows.append(item)
    emit_copy(rows, 'xl-pilot-copy.inc')
    emit_copy(descending_rows, 'xl-pilot-descend.inc')
    rows = []
    for name, base in [('white', 'SHIP'), ('red', 'SHIP_RED'), ('yellow', '0x1600')]:
        plane = (B / f'ship-{name}.bin').read_bytes()
        if len(plane) == 16:
            plane *= 4
        for row in range(16):
            rows.append((tuple(plane[pose * 16 + row] for pose in range(4)),
                         f'ship_{name}+{row}', f'{base}+player_pm_y+{row}'))
    for base in ['SHIP', 'SHIP_RED']:
        for row in list(range(8)) + list(range(24,32)):
            rows.append(((0,0,0,0), 'unused', f'{base}+player_shield_pm_y+{row}'))
    emit_copy(rows, 'xl-restore-ship.inc')
