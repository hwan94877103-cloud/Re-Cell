"""Zone-heated work bench + virtual CTP block (R03, all values are design assumptions).

Datum shared with tool03_r03: Z=0 = cell top surface. X = cell length, Y = cell thickness (stacking direction).
Stack below a cell (top -> bottom, assumed):
  cell 91 | adhesive 1 | Al cooling plate 5 (top wall 1.5, channel 1.5, bottom wall 2) |
  non-metal bench top plate 4 | racetrack induction coil 4 | ferrite 5 | non-metal coil support 20
The pack bottom protection plate is removed before intake. Coolant is drained and purged before heating.
"""
import math
import cadquery as cq

from tool03_r03 import P, bx, cz

CELL_L, CELL_T, CELL_H = P['cell']
PITCH = P['pitch_y']
ROW_X = (0.0, 150.0)                  # row A (target row) and row B centres, 2 mm end pad between rows
CELL_J = range(-6, 6)                 # 12 cells per row, target cell j = 0 at Y = 0
Z_ADH = (-92.0, -91.0)
Z_CP = (-97.0, -92.0)
CP_CH = (-95.0, -93.5)                # coolant channel (drained before heating)
Z_TOP = (-101.0, -97.0)               # non-metal bench top plate t4
Z_COIL = (-105.0, -101.0)
Z_FER = (-110.0, -105.0)
Z_SUP = (-130.0, -110.0)
COIL = dict(L=130.0, W=22.0, w=6.0)   # racetrack outer length/width, conductor band width
CH_X = [-64.0 + 16.0 * k for k in range(9)]   # channel centres relative to the row centre, width 10
Y0, Y1 = -6 * PITCH - CELL_T / 2 - 8, 5 * PITCH + CELL_T / 2 + 8
X0, X1 = -95.0, 245.0


def racetrack(cx, cy, z0, z1, L, W, w):
    outer = cq.Workplane('XY').workplane(offset=z0).center(cx, cy).slot2D(L, W).extrude(z1 - z0).val()
    inner = cq.Workplane('XY').workplane(offset=z0 - 1).center(cx, cy).slot2D(L - 2 * w, W - 2 * w).extrude(z1 - z0 + 2).val()
    return outer.cut(inner)


def bench(rows=(0, 1), cells=CELL_J, local=False):
    """Returns list of dict(name, solid, role) with role in
    'cell' (workpiece, drawn uncut-style), 'layer' (hatched when cut), 'thin' (solid-filled when cut), 'part'."""
    out = []

    def add(name, s, role, hatch=None):
        out.append(dict(name=name, solid=s, role=role, hatch=hatch))

    yl0 = min(cells) * PITCH - CELL_T / 2 - 8
    yl1 = max(cells) * PITCH + CELL_T / 2 + 8
    xl0, xl1 = (X0, X1) if len(rows) > 1 else (X0, 85.0)
    for r in rows:
        xc = ROW_X[r]
        for j in cells:
            yc = j * PITCH
            tag = f'{"AB"[r]}{j:+d}'
            c = bx(xc - CELL_L / 2, xc + CELL_L / 2, yc - CELL_T / 2, yc + CELL_T / 2, -CELL_H, 0).cut(cz(7.0, -0.3, 0.1, xc, yc))
            add('셀 ' + tag, c, 'cell')
            for sx in (-1, 1):
                a, b = sorted((xc + sx * 58, xc + sx * 70))
                add('단자 ' + tag, bx(a, b, yc - 8, yc + 8, 0, 3), 'cell')
                add('잔여 버스바 ' + tag, bx(a + 1, b - 1, yc - 10, yc + 10, 3, 5), 'cell')
            add('접착층 ' + tag, bx(xc - CELL_L / 2, xc + CELL_L / 2, yc - CELL_T / 2, yc + CELL_T / 2, *Z_ADH), 'thin')
            if j < max(cells):
                y0 = yc + CELL_T / 2
                add('압축 패드 ' + tag, bx(xc - 72, xc + 72, y0, y0 + 2.0, -89, -2), 'thin')
            # coil, ferrite, temperature probe under every cell (one heating zone per cell)
            add('코일 ' + tag, racetrack(xc, yc, *Z_COIL, COIL['L'], COIL['W'], COIL['w']), 'layer', (45, 0.9))
            fe = bx(xc - 63, xc + 63, yc - 10, yc + 10, *Z_FER).cut(cz(2.0, Z_FER[0] - 1, Z_FER[1] + 1, xc, yc))
            add('페라이트 ' + tag, fe, 'layer', (135, 0.9))
            add('온도 센서 ' + tag, cz(1.5, Z_SUP[0] + 2, Z_CP[0], xc, yc), 'part')
    # cooling plate with drained channels (along Y), per row
    cp = bx(xl0 + 5, xl1 - 5, yl0, yl1, *Z_CP)
    for r in rows:
        for dx in CH_X:
            x = ROW_X[r] + dx
            cp = cp.cut(bx(x - 5, x + 5, yl0 + 6, yl1 - 6, *CP_CH))
    add('Al 냉각판', cp, 'layer', (45, 1.6))
    top = bx(xl0 - 15, xl1 + 15, yl0 - 20, yl1 + 20, *Z_TOP)
    sup = bx(xl0 - 15, xl1 + 15, yl0 - 20, yl1 + 20, *Z_SUP)
    for r in rows:
        for j in cells:
            top = top.cut(cz(2.0, Z_TOP[0] - 1, Z_TOP[1] + 1, ROW_X[r], j * PITCH))
            sup = sup.cut(cz(2.0, Z_SUP[0] - 1, Z_SUP[1] + 1, ROW_X[r], j * PITCH))
    add('비금속 상판', top, 'layer', (135, 1.2))
    add('코일 지지판', sup, 'layer', (45, 2.4))
    # block end members (assumed), left end of row A and right end of row B
    add('블록 경계 부재', bx(-CELL_L / 2 - 15, -CELL_L / 2 - 5, yl0, yl1, -CELL_H, -10), 'layer', (135, 2.0))
    if len(rows) > 1:
        add('블록 경계 부재 R', bx(ROW_X[1] + CELL_L / 2 + 5, ROW_X[1] + CELL_L / 2 + 15, yl0, yl1, -CELL_H, -10),
            'layer', (135, 2.0))
    return out


def rotate_about_pivot(s, deg, pivot_x=-CELL_L / 2, pivot_z=-CELL_H):
    """Peeling: rigid rotation of the target cell (and the tool holding it) about its X- bottom edge (axis // Y).
    Positive angle lifts the X+ end."""
    return s.rotate(cq.Vector(pivot_x, 1, pivot_z), cq.Vector(pivot_x, 0, pivot_z), deg)
