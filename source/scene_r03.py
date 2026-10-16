"""Work cell layout (D-01), tool 02 outline (D-09) and animation scene. All dimensions are design assumptions.

World frame: floor Z=0, X along the gantry rails, Y across. Local tool/bench frame (tool03_r03, bench_r03)
maps to world by (X+BX, Y+BY, Z+ZC). ZC = 900: cell top surface is 900 above the floor (assumed).
"""
import math
import cadquery as cq

from tool03_r03 import bx, cz, cyl, P as P3

# ---------------------------------------------------------------- layout parameters (assumed)
FENCE = (0.0, 5400.0, -1500.0, 1500.0, 2000.0)
PACK = (350.0, 2550.0, -800.0, 800.0)          # 2200 x 1600 virtual CTP pack
ZC = 900.0                                      # cell top (world)
BENCH_TOP = ZC - 97.0                           # top of the non-metal bench plate (world)
BLOCK_NX, BLOCK_NY = 6, 4
BLOCK_W, BLOCK_D = 298.0, 342.0                 # 2 rows x 12 cells
TARGET_BLOCK = (2, 1)
STROKE = dict(X=4050.0, Y=1800.0, Z=800.0)      # X 350..4400, Y +-900 (assumed)
RAIL_Y = 1350.0
RAIL_Z = (2150.0, 2300.0)
BRIDGE_Z = (2300.0, 2450.0)
TILT_TO_CUP = 264.0                             # tool 03: tilt axis centre above the cup sealing plane
RACK = dict(x=(2620.0, 3700.0), y=(300.0, 900.0), z_top=1000.0, st={'01': (2720.0, 600.0), '03': (2900.0, 600.0), '02': (3350.0, 600.0)})
COVER_TABLE = (3750.0, 5150.0, -1000.0, 1000.0, 900.0)


def block_centre(i, k):
    px = (PACK[1] - PACK[0]) / BLOCK_NX
    py = (PACK[3] - PACK[2]) / BLOCK_NY
    return PACK[0] + px * (i + 0.5), PACK[2] + py * (k + 0.5)


def local_offset():
    """(BX, BY) so that bench_r03 local coordinates of the target block land in the pack."""
    cx, cy = block_centre(*TARGET_BLOCK)
    return cx - 75.0, cy + 14.25


def W(s, dx=0.0, dy=0.0, dz=0.0):
    return s.translate(cq.Vector(dx, dy, dz))


# ---------------------------------------------------------------- tool 02 (outline level, assumed)
def tool02():
    """Local frame: Z=0 = cup contact plane. Returns list of (name, solid, group)."""
    out = []
    a = lambda n, s, g='02': out.append((n, s, g))
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = 300 * sx, 200 * sy
            cup = cz(40, 0, 10, x, y).fuse(cz(32, 10, 28, x, y)).fuse(cz(26, 28, 40, x, y))
            a(f'Ø80 흡착컵', cup)
            a('컵 스프링 홀더', cz(10, 40, 90, x, y).fuse(cz(16, 70, 90, x, y)))
    # frame: two long beams along X at y=+-200 and three cross beams
    for sy in (-1, 1):
        a('프레임 (40×40)', bx(-340, 340, 200 * sy - 20, 200 * sy + 20, 90, 130))
    for x in (-300, 0, 300):
        a('프레임 (40×40)', bx(x - 20, x + 20, -180, 180, 90, 130))
    a('중앙 허브판', bx(-100, 100, -100, 100, 130, 150))
    a('어댑터판', cz(50, 150, 160))
    a('교환기 툴 플레이트', cz(50, 160, 185), 'common')
    a('통과 모듈 툴측', bx(50, 90, -15, 15, 160, 185), 'common')
    # cutting spindle on a pneumatic slide (extended position: tip 60 below the cup plane)
    sxp, syp = 150.0, 0.0
    a('공압 슬라이드 (스트로크 80)', bx(sxp - 30, sxp + 30, syp + 22, syp + 52, 60, 230))
    a('절단 스핀들 Ø40', cz(20, -10, 120, sxp, syp))
    a('엔드밀 Ø6', cz(3, -60, -10, sxp, syp))
    hood = cz(20, -55, -15, sxp, syp).cut(cz(17, -56, -14, sxp, syp))
    a('칩 흡입 후드 Ø40', hood)
    a('칩 흡입 호스 Ø25', cyl(12.5, 160, (sxp - 36, syp, -35), (0, 0, 1)).fuse(cyl(12.5, 15.5, (sxp - 36, syp, -35), (1, 0, 0))))
    a('냉각수 흡입 노즐 Ø10', cz(5, -50, 70, sxp + 42, syp + 37).fuse(cz(8, 50, 70, sxp + 42, syp + 37)).fuse(bx(sxp + 30, sxp + 42, syp + 29, syp + 45, 60, 70)))
    return out


def tool01_envelope():
    """Tool 01 (team member's design): outline envelope only."""
    return [('01 외형 (팀원 설계, 가정)', cz(90, 0, 280), '01'), ('교환기 툴 플레이트', cz(50, 280, 305), 'common')]


# ---------------------------------------------------------------- layout scene (world)
def layout(gantry_x=1270.0, gantry_y=-200.0, z_tilt=None, with_cells=False):
    """Returns list of dict(name, solid, group). group: fence, conveyor, bench, pack, gantry, moving, rack, station."""
    out = []

    def a(n, s, g):
        out.append(dict(name=n, solid=s, group=g))

    x0, x1, y0, y1, h = FENCE
    t = 30.0
    for (ax0, ax1, ay0, ay1) in [(x0, x1, y0, y0 + t), (x0, x1, y1 - t, y1), (x1 - t, x1, y0 + t, y1 - t)]:
        a('안전 펜스', bx(ax0, ax1, ay0, ay1, 0, h), 'fence')
    a('안전 펜스', bx(x0, x0 + t, y0 + t, -950, 0, h), 'fence')
    a('안전 펜스', bx(x0, x0 + t, 950, y1 - t, 0, h), 'fence')
    # intake conveyor
    a('팩 입고 컨베이어', bx(-900, 290, -900, 900, 620, BENCH_TOP - 63), 'conveyor')
    for k in range(10):
        xr = -850 + k * 120
        a('롤러', cyl(25, 1700, (xr, -850, BENCH_TOP - 33), (0, 1, 0)), 'conveyor')
    # heating bench: coil platform + legs
    a('가열 작업대 (코일 구역부)', bx(300, 2600, -880, 880, BENCH_TOP - 160, BENCH_TOP), 'bench')
    for (lx, ly) in [(330, -850), (2570, -850), (330, 850), (2570, 850)]:
        a('작업대 다리', bx(lx - 40, lx + 40, ly - 40, ly + 40, 0, BENCH_TOP - 160), 'bench')
    a('팩 클램프', bx(318, 348, -300, 300, BENCH_TOP, BENCH_TOP + 120), 'bench')
    a('팩 클램프', bx(2552, 2582, -300, 300, BENCH_TOP, BENCH_TOP + 120), 'bench')
    # virtual pack: tray walls, blocks, cross members
    px0, px1, py0, py1 = PACK
    zt0, zt1 = BENCH_TOP, ZC + 40
    for (ax0, ax1, ay0, ay1) in [(px0, px1, py0, py0 + 20), (px0, px1, py1 - 20, py1), (px0, px0 + 20, py0 + 20, py1 - 20),
                                 (px1 - 20, px1, py0 + 20, py1 - 20)]:
        a('팩 프레임', bx(ax0, ax1, ay0, ay1, zt0, zt1), 'pack')
    a('냉각판 (팩 바닥)', bx(px0 + 20, px1 - 20, py0 + 20, py1 - 20, BENCH_TOP, BENCH_TOP + 5), 'pack')
    for i in range(BLOCK_NX):
        for k in range(BLOCK_NY):
            cx, cy = block_centre(i, k)
            if with_cells and (i, k) == TARGET_BLOCK:
                continue
            a('셀 블록 (2×12)', bx(cx - BLOCK_W / 2, cx + BLOCK_W / 2, cy - BLOCK_D / 2, cy + BLOCK_D / 2, ZC - 91, ZC), 'pack')
    for i in range(BLOCK_NX + 1):
        xm = px0 + (px1 - px0) / BLOCK_NX * i
        if 0 < i < BLOCK_NX:
            a('블록 경계 부재', bx(xm - 15, xm + 15, py0 + 20, py1 - 20, BENCH_TOP + 5, ZC - 10), 'pack')
    # gantry
    for (cx, cy) in [(120, -RAIL_Y), (120, RAIL_Y), (5280, -RAIL_Y), (5280, RAIL_Y)]:
        a('갠트리 기둥', bx(cx - 75, cx + 75, cy - 75, cy + 75, 0, RAIL_Z[0]), 'gantry')
    for sy in (-1, 1):
        a('X 레일 빔', bx(45, 5355, sy * RAIL_Y - 75, sy * RAIL_Y + 75, *RAIL_Z), 'gantry')
    if z_tilt is None:
        z_tilt = ZC + TILT_TO_CUP + 300
    gx, gy = gantry_x, gantry_y
    for sx in (-1, 1):
        a('Y 브리지', bx(*sorted((gx + sx * 150, gx + sx * 230)), -RAIL_Y - 90, RAIL_Y + 90, *BRIDGE_Z), 'moving')
    a('Z 캐리지', bx(gx - 150, gx + 150, gy - 160, gy + 160, BRIDGE_Z[0] - 150, BRIDGE_Z[1]).cut(
        bx(gx - 76, gx + 76, gy - 76, gy + 76, BRIDGE_Z[0] - 160, BRIDGE_Z[1] + 10)), 'moving')
    a('Z 램', bx(gx - 75, gx + 75, gy - 75, gy + 75, z_tilt + 130, z_tilt + 1130), 'moving')
    a('회전축 (θ)', cz(80, z_tilt + 30, z_tilt + 130, gx, gy), 'moving')
    a('기울임축 유닛', bx(gx - 40, gx + 40, gy - 40, gy + 40, z_tilt - 30, z_tilt + 30), 'moving')
    a('근접 카메라 + 링 조명', bx(gx + 80, gx + 140, gy - 30, gy + 30, z_tilt + 40, z_tilt + 120), 'moving')
    # tool rack with 01 / 02 / 03 stations
    rx0, rx1 = RACK['x']
    ry0, ry1 = RACK['y']
    a('공구 거치대 (01·03)', bx(rx0, 3000, ry0, ry1, RACK['z_top'] - 40, RACK['z_top']).cut(
        bx(2828, 2972, 558, 642, RACK['z_top'] - 50, RACK['z_top'] + 10)), 'rack')
    for yr in (400, 800):
        a('02 거치 레일', bx(3100, 3600, yr - 20, yr + 20, RACK['z_top'] - 60, RACK['z_top'] - 40 + 50), 'rack')
    for lx in (rx0 + 30, rx1 - 30):
        for ly in (ry0 + 30, ry1 - 30):
            a('거치대 다리', bx(lx - 25, lx + 25, ly - 25, ly + 25, 0, RACK['z_top'] - 60), 'rack')
    # stations (all inside the gantry reach)
    a('셀 측정대 (전압·절연)', bx(2700, 2950, -250, 50, 0, 880), 'station')
    a('측정 지그 (스프링 핀)', bx(2740, 2910, -200, 0, 880, 905), 'station')
    a('침수조 받침', bx(3040, 3460, -260, 60, 0, 500), 'station')
    tank = bx(3050, 3450, -250, 50, 500, 800).cut(bx(3070, 3430, -230, 30, 520, 820))
    a('비상 침수조 400×300×300', tank, 'station')
    for (bx0, bx1, name) in [(2650, 2950, '회수함: 나사·칩'), (3000, 3300, '회수함: 전장품'),
                             (3350, 3600, '셀 회수함 (재사용/재활용)')]:
        a(name, bx(bx0, bx1, -900, -450, 0, 700).cut(bx(bx0 + 15, bx1 - 15, -885, -465, 40, 720)), 'station')
    tx0, tx1, ty0, ty1, tz = COVER_TABLE
    a('커버 거치대', bx(tx0, tx1, ty0, ty1, tz - 40, tz), 'station')
    for lx in (tx0 + 40, tx1 - 40):
        for ly in (ty0 + 40, ty1 - 40):
            a('거치대 다리', bx(lx - 30, lx + 30, ly - 30, ly + 30, 0, tz - 40), 'station')
    a('냉각수 회수 탱크', cz(220, 0, 700, 2900, 1200), 'station')
    # top fixed frame and sensors (above the bridge travel, Z > 2450)
    a('상부 고정 프레임', bx(300, 2600, -40, 40, 3270, 3340), 'top')
    a('전체 카메라', bx(560, 660, -60, 60, 3150, 3270), 'top')
    a('열화상 카메라', bx(2250, 2350, -60, 60, 3150, 3270), 'top')
    a('배기 후드', bx(900, 2000, -300, 300, 3150, 3270).cut(bx(920, 1980, -280, 280, 3140, 3250)), 'top')
    a('배기 덕트', bx(1400, 1500, 300, 400, 3230, 3400), 'top')
    a('가스 감지기', cz(40, 1800, 1900, 2700, -1420), 'top')
    return out


def rack_tools(tool03_parts):
    """Tools parked in the rack (world). tool03_parts: tool03_r03.build() output (group 'tool' and 'common')."""
    out = []
    x3, y3 = RACK['st']['03']
    dz3 = RACK['z_top'] - 58.0
    for p in tool03_parts:
        if p['no'].startswith('CM'):
            continue
        out.append(dict(name='03 ' + p['name'], solid=W(p['solid'], x3, y3, dz3), group='tool03'))
    x2, y2 = RACK['st']['02']
    dz2 = RACK['z_top'] + 10 - 90.0
    for n, s_, g in tool02():
        out.append(dict(name='02 ' + n, solid=W(s_, x2, y2, dz2), group='tool02'))
    x1, y1 = RACK['st']['01']
    for n, s_, g in tool01_envelope():
        out.append(dict(name=n, solid=W(s_, x1, y1, RACK['z_top']), group='tool01'))
    return out
