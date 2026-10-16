"""R03 process steps 4-7 (01 / 02 tools): assumed geometry for the virtual pack cover, cover screws, seal-cut line,
electronics, coolant ports and the busbar bridges of the target block, plus tool docking data and a builder that
turns a simulation pose into world solids (for per-step STEP files).

Everything here is a design assumption made for the concept simulation and the process-sequence figures:
the real pack cover, screw count, sealant, electronics and coolant ports are unknown. The 01 head is the team
member's design and appears only as its layout envelope (cylinder 180 x 280)."""
import math

import cadquery as cq

import scene_r03 as S
import bench_r03 as BM
import tool03_r03 as T
from tool03_r03 import bx, cz

ZC = S.ZC
PX0, PX1, PY0, PY1 = S.PACK                      # 350, 2550, -800, 800
FRAME_TOP = ZC + 40.0                            # 940, top of the pack tray walls
COVER = dict(t=3.0, h=40.0, flange=60.0, cut_inset=25.0, screw_inset=10.0, mass_kg=25.0)
SCREW = dict(d=10.0, h=6.0, pitch=200.0)
ELEC = (2240.0, 2480.0, -200.0, 200.0, ZC + 10.0, ZC + 60.0)     # electronics (BMS/BDU) envelope, virtual
PORTS = [(2570.0, -420.0), (2570.0, 420.0)]       # coolant ports (virtual), pipe top Z 980
PORT_TOP = FRAME_TOP + 40.0
BIN = {11: (2800.0, -675.0), 12: (3150.0, -675.0), 13: (3475.0, -675.0)}

# tools: tilt-axis centre above the tool's own origin when coupled (tool plate top + 70 = changer master + tilt unit)
TOOL_DOCK = {1: 305.0 + 70.0, 2: 185.0 + 70.0, 3: S.TILT_TO_CUP}
PARK = {1: (S.RACK['st']['01'][0], S.RACK['st']['01'][1], S.RACK['z_top']),
        2: (S.RACK['st']['02'][0], S.RACK['st']['02'][1], S.RACK['z_top'] + 10.0 - 90.0),
        3: (S.RACK['st']['03'][0], S.RACK['st']['03'][1], S.RACK['z_top'] - 58.0)}
T2 = dict(spindle=(150.0, 0.0), tip_z=-60.0, stroke=80.0, nozzle=(192.0, 37.0), nozzle_tip_z=-50.0)
SLIDER_02 = ('절단 스핀들 Ø40', '엔드밀 Ø6', '칩 흡입 후드 Ø40', '칩 흡입 호스 Ø25', '냉각수 흡입 노즐 Ø10')


# ------------------------------------------------------------------ cover
def cover_solids(h=None):
    """Virtual cover: 3 mm sheet, flange 60 mm on the tray walls, raised 'hat' of height h. Returns (body, rim):
    body = what 02 lifts after the seal cut, rim = flange strip outside the cut line (stays on the tray)."""
    h = COVER['h'] if h is None else h
    t, f = COVER['t'], COVER['flange']
    z0 = FRAME_TOP
    flange = bx(PX0, PX1, PY0, PY1, z0, z0 + t)
    hat = bx(PX0 + f, PX1 - f, PY0 + f, PY1 - f, z0, z0 + h)
    cavity = bx(PX0 + f + t, PX1 - f - t, PY0 + f + t, PY1 - f - t, z0 - 1, z0 + h - t)
    cover = flange.fuse(hat).cut(cavity)
    c = COVER['cut_inset']
    inner = bx(PX0 + c, PX1 - c, PY0 + c, PY1 - c, z0 - 5, z0 + h + 5)
    body = cover.intersect(inner)
    rim = cover.cut(inner)
    for (x, y) in screw_xy():                                  # screw holes in the rim
        rim = rim.cut(cz(3.4, z0 - 1, z0 + t + 1, x, y))
    return body, rim


def screw_xy():
    """Cover screws on the tray wall centre line (10 mm in from the edge), pitch about 200 (assumed): 38 screws."""
    s = COVER['screw_inset']
    xa, xb, ya, yb = PX0 + s, PX1 - s, PY0 + s, PY1 - s
    nx = round((xb - xa) / SCREW['pitch']) + 1
    ny = round((yb - ya) / SCREW['pitch']) + 1
    pts = []
    for k in range(nx):
        x = xa + (xb - xa) * k / (nx - 1)
        pts += [(x, ya), (x, yb)]
    for k in range(1, ny - 1):
        y = ya + (yb - ya) * k / (ny - 1)
        pts += [(xa, y), (xb, y)]
    return [(round(x, 2), round(y, 2)) for x, y in pts]


def screw_solid(x, y):
    """Screw head on the flange plus the shank through the flange only (the threaded hole in the tray wall is not
    modelled, so the shank stops at the wall top)."""
    z = FRAME_TOP + COVER['t']
    return cz(SCREW['d'] / 2, z, z + SCREW['h'], x, y).fuse(cz(3.0, FRAME_TOP, z, x, y))


def seal_path():
    """Seal-cut rectangle (25 mm in from the cover edge). Sides in cutting order with the rotation that keeps the
    02 slide, nozzle and chip hose outside the cover hat (local +Y pointing outwards)."""
    c = COVER['cut_inset']
    xa, xb, ya, yb = PX0 + c, PX1 - c, PY0 + c, PY1 - c
    return [dict(p0=(xa, ya), p1=(xb, ya), rot=180.0), dict(p0=(xb, ya), p1=(xb, yb), rot=-90.0),
            dict(p0=(xb, yb), p1=(xa, yb), rot=0.0), dict(p0=(xa, yb), p1=(xa, ya), rot=90.0)]


# ------------------------------------------------------------------ electronics, coolant ports
def electronics_solid():
    x0, x1, y0, y1, z0, z1 = ELEC
    return bx(x0, x1, y0, y1, z0, z1)


def port_solids():
    out = []
    for (x, y) in PORTS:
        out.append(bx(PX1, x + 20.0, y - 15.0, y + 15.0, ZC - 10.0, ZC + 5.0).fuse(cz(8.0, ZC + 5.0, PORT_TOP, x, y)).cut(
            cz(5.0, ZC + 20.0, PORT_TOP + 1, x, y)))
    return out


# ------------------------------------------------------------------ busbar bridges of the target block (world)
def bridges():
    """Busbar pieces between adjacent cells on the 4 terminal lines of the target block: 4 x 11 = 44 (assumed).
    After cutting, the 'residue' pieces already in bench_r03 remain on each terminal."""
    BX, BY = S.local_offset()
    out = []
    for r in (0, 1):
        for s in (-1, 1):
            xc = BX + BM.ROW_X[r] + s * 64.0
            for j in range(-6, 5):
                yc = BY + (j + 0.5) * BM.PITCH
                out.append(dict(key=f'{"AB"[r]}{"-+"[s > 0]}{j + 6}', x=round(xc, 3), y=round(yc, 3),
                                solid=bx(xc - 5.0, xc + 5.0, yc - 4.25, yc + 4.25, ZC + 3.0, ZC + 5.0)))
    return out


# ------------------------------------------------------------------ tools in their own tilt-centre frames
def tool_items(n, parts03=None):
    """[(name, solid, colour)] of tool n with the coupled tilt-axis centre at the origin (Z up)."""
    out = []
    if n == 1:
        for name, s, g in S.tool01_envelope():
            out.append(('01 ' + name, s.translate(cq.Vector(0, 0, -TOOL_DOCK[1])), '#b0a16f' if g == '01' else '#598aad'))
    elif n == 2:
        col = {'Ø80 흡착컵': '#30363a', '컵 스프링 홀더': '#555b60', '프레임 (40×40)': '#9aa5ad', '중앙 허브판': '#b8c4cc',
               '어댑터판': '#c4ccd2', '교환기 툴 플레이트': '#598aad', '통과 모듈 툴측': '#58717d',
               '공압 슬라이드 (스트로크 80)': '#5d6b78', '절단 스핀들 Ø40': '#c4ccd2', '엔드밀 Ø6': '#555b60',
               '칩 흡입 후드 Ø40': '#4b89b3', '칩 흡입 호스 Ø25': '#4b89b3', '냉각수 흡입 노즐 Ø10': '#4ca6b8'}
        for name, s, g in S.tool02():
            out.append(('02 ' + name, s.translate(cq.Vector(0, 0, -TOOL_DOCK[2])), col.get(name, '#6f8fa6')))
    else:
        parts03 = parts03 or T.build()
        for p in parts03:
            if p['no'].startswith('CM'):
                continue
            out.append(('03 ' + p['no'], p['solid'].translate(cq.Vector(0, 0, -TOOL_DOCK[3])), p['color']))
    return out


def head_items(parts03=None):
    """Head-side changer master and pass-through module (CM-01, CM-02) in the tilt-centre frame."""
    parts03 = parts03 or T.build()
    return [('head ' + p['no'], p['solid'].translate(cq.Vector(0, 0, -TOOL_DOCK[3])), p['color'])
            for p in parts03 if p['no'] in ('CM-01', 'CM-02')]


def mat(m16):
    """Row-major 4x4 list (16) -> cq.Matrix."""
    return cq.Matrix([[m16[0], m16[1], m16[2], m16[3]], [m16[4], m16[5], m16[6], m16[7]],
                      [m16[8], m16[9], m16[10], m16[11]]])


def head_matrix(x, y, z, rot_deg, tilt_deg):
    """T(x, y, z) * Rz(rot) * Ry(tilt) as a 16-list (row-major), same convention as the browser simulation."""
    a, b = math.radians(rot_deg), math.radians(tilt_deg)
    ca, sa, cb, sb = math.cos(a), math.sin(a), math.cos(b), math.sin(b)
    Rz = [[ca, -sa, 0], [sa, ca, 0], [0, 0, 1]]
    Ry = [[cb, 0, sb], [0, 1, 0], [-sb, 0, cb]]
    R = [[sum(Rz[i][k] * Ry[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    return [R[0][0], R[0][1], R[0][2], x, R[1][0], R[1][1], R[1][2], y, R[2][0], R[2][1], R[2][2], z, 0, 0, 0, 1]
