"""TOOL03 R03 - cell separation tool, dimension-based assembly (all values are design assumptions).

Datum: Z=0 = cell top surface = cup sealing plane. X = cell length, Y = cell thickness, Z = up.
R02 -> R03 changes (see R03_change_log.md):
  * cup line: elbow + rear groove removed; nipple (M5 male, assumed) + thin nut on bracket, hose straight up a
    vertical bore through the nose; insert holes reduced below insert envelope (self-tapping/heat-set, TBD)
  * IR clamp: screws and threads added, foot screws moved so they no longer cross the clamp screws
  * cooling nozzles: moved from nose sides to blocks under the housing floor, air fed through the floor (O-ring)
  * lid -> structural top plate t10 on 6 bosses; load cell / adapter / changer tool with assumed bolt patterns
  * tool-side pass-through module, two vacuum units, pass holes, hoses and IR cable with bend radii
R03 KS revision (values from ks_spec.py, reasons in the KS rationale table):
  * nose retainer bolts M5x18 -> M4x18 (M5 head dk max 8.72 > retainer width 8), holes 4.5 / taps M4
  * nozzle block O-ring groove -> KS P6 face groove (D 9.2, G 2.5, H 1.4), O-ring P6 added as part 03-213
  * IR clamp bore 18.2 -> 18 H8 (nominal 18 in the model), nose IR bore 18.4 -> 19
  * fitting ports on 4 mm bosses so the M5 thread has full length after the incomplete-thread allowance
"""
import math
import numpy as np
import cadquery as cq
import ks_spec as KS

V = lambda p: cq.Vector(*[float(c) for c in p])

# ----------------------------------------------------------------------------- parameters (all "assumed")
P = dict(
    cell=(148.0, 26.5, 91.0), pad_t=2.0, pitch_y=28.5,
    nose_body=(140.0, 24.0, 48.0), nose_z0=16.0, flange=(148.0, 44.0, 8.0),
    housing_xy=(160.0, 140.0), housing_z0=58.0, floor_t=6.0, wall_t=4.0, body_top=124.0, top_t=10.0,
    cup_x=40.0, bracket=(40.0, 20.0, 6.0), ir_x=12.0, ir_d=18.0, ir_len=40.0, ir_z0=40.0,
    hose_od=4.0, hose_id=2.0, hose_R=16.0, cable_d=4.0, cable_R=15.0, air_R=15.0,
    nozzle_xy={'L': (-55.0, -31.0), 'R': (55.0, 31.0)},
    pass_holes=[(55.0, 28.0), (55.0, -28.0)], pass_hole_d=20.0,
    lc_d=80.0, lc_h=25.0, adapter=(100.0, 10.0), changer_tool=(100.0, 25.0), changer_master=(100.0, 40.0),
    tilt=(80.0, 80.0, 60.0), module=(40.0, 30.0, 25.0),
    pcd_lc=60.0, pcd_tool=90.0,
)
Z_FLANGE_BOT = P['nose_z0'] + P['nose_body'][2]          # 64
Z_FLANGE_TOP = Z_FLANGE_BOT + P['flange'][2]              # 72
Z_TOP = P['body_top'] + P['top_t']                         # 134
Z_LC_TOP = Z_TOP + P['lc_h']                               # 159
Z_AD_TOP = Z_LC_TOP + P['adapter'][1]                      # 169
Z_TOOL_TOP = Z_AD_TOP + P['changer_tool'][1]               # 194
Z_MASTER_TOP = Z_TOOL_TOP + P['changer_master'][1]         # 234
Z_TILT_C = Z_MASTER_TOP + P['tilt'][2] / 2                 # 264


def box(x, y, z, cx=0, cy=0, cz=0):
    return cq.Workplane('XY').box(x, y, z).translate((cx, cy, cz)).val()


def bx(x0, x1, y0, y1, z0, z1):
    return box(x1 - x0, y1 - y0, z1 - z0, (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)


def cyl(r, h, p=(0, 0, 0), v=(0, 0, 1)):
    return cq.Solid.makeCylinder(r, h, V(p), V(v))


def cz(r, z0, z1, x=0.0, y=0.0):
    return cyl(r, z1 - z0, (x, y, z0))


def hexprism(af, z0, z1, x, y):
    r = af / math.sqrt(3)
    pts = [(x + r * math.cos(math.radians(30 + 60 * i)), y + r * math.sin(math.radians(30 + 60 * i))) for i in range(6)]
    return cq.Workplane('XY').workplane(offset=z0).polyline(pts).close().extrude(z1 - z0).val()


def route_wire(pts, R):
    """3D polyline with every corner replaced by a tangent arc of radius R."""
    Pn = [np.array(p, float) for p in pts]
    edges, cur = [], Pn[0]
    for i in range(1, len(Pn) - 1):
        a, b, c = Pn[i - 1], Pn[i], Pn[i + 1]
        d1 = (b - a) / np.linalg.norm(b - a)
        d2 = (c - b) / np.linalg.norm(c - b)
        phi = math.acos(float(np.clip(np.dot(d1, d2), -1, 1)))
        if phi < 1e-6:
            continue
        t = R * math.tan(phi / 2)
        A, B = b - d1 * t, b + d2 * t
        u = d2 - np.dot(d2, d1) * d1
        u /= np.linalg.norm(u)
        C = A + u * R
        m = (b - C) / np.linalg.norm(b - C)
        M = C + m * R
        if np.linalg.norm(A - cur) > 1e-6:
            edges.append(cq.Edge.makeLine(V(cur), V(A)))
        edges.append(cq.Edge.makeThreePointArc(V(A), V(M), V(B)))
        cur = B
    if np.linalg.norm(Pn[-1] - cur) > 1e-6:
        edges.append(cq.Edge.makeLine(V(cur), V(Pn[-1])))
    return cq.Wire.assembleEdges(edges)


def tube(pts, R, ro, ri=0.0):
    w = route_wire(pts, R)
    p0, p1 = np.array(pts[0], float), np.array(pts[1], float)
    d = (p1 - p0) / np.linalg.norm(p1 - p0)
    outer = cq.Wire.makeCircle(ro, V(p0), V(d))
    inner = [cq.Wire.makeCircle(ri, V(p0), V(d))] if ri > 0 else []
    return cq.Solid.sweep(outer, inner, w, True, False, None, 'right')


def shcs(axis_pt, direction, L, d_model, head_d, head_h):
    """Socket head cap screw envelope. axis_pt = centre of head seat, direction = into the work (unit)."""
    p = np.array(axis_pt, float)
    v = np.array(direction, float)
    v /= np.linalg.norm(v)
    shank = cyl(d_model / 2, L, tuple(p), tuple(v))
    head = cyl(head_d / 2, head_h, tuple(p - v * head_h), tuple(v))
    return shank.fuse(head)


# ----------------------------------------------------------------------------- build
def build():
    parts = []

    def add(no, name, solid, color, mat, kind, group='tool', note='', explode=(0, 0, 0), qty_group=None, path=None):
        parts.append(dict(no=no, name=name, solid=solid, color=color, mat=mat, kind=kind, group=group,
                          note=note, explode=explode, qty_group=qty_group or no, path=path))
        return solid

    nb, fl = P['nose_body'], P['flange']
    zb0, zb1 = P['nose_z0'], Z_FLANGE_BOT
    cx = P['cup_x']

    # ---------------- 03-001 nose (PEEK)
    nose = bx(-nb[0] / 2, nb[0] / 2, -nb[1] / 2, nb[1] / 2, zb0, zb1).fuse(
        bx(-fl[0] / 2, fl[0] / 2, -fl[1] / 2, fl[1] / 2, Z_FLANGE_BOT, Z_FLANGE_TOP))
    nose = nose.cut(cz(KS.IR_BORE_NOSE / 2, zb0 - 1, Z_FLANGE_TOP + 1, P['ir_x'], 0))   # IR bore D19 through
    for x in (-cx, cx):
        nose = nose.cut(cz(6.2, zb0 - 1, 30, x, 0))                                # pocket D12.4 x14 for nut/barb
        nose = nose.cut(cz(3.0, 29, Z_FLANGE_TOP + 1, x, 0))                       # hose bore D6 straight up
        for xx in (x - 12, x + 12):
            nose = nose.cut(cz(2.25, zb0 - 1, zb0 + 8, xx, 0))                     # insert pilot D4.5 x8
    for x in (-60, 60):
        for y in (-18, 18):
            nose = nose.cut(cz(KS.CLEAR_2[KS.NOSE_BOLT] / 2, Z_FLANGE_BOT - 1, Z_FLANGE_TOP + 1, x, y))   # M4 clearance D4.5
    for x in (6, 18):
        nose = nose.cut(cz(1.7, Z_FLANGE_BOT - 1, Z_FLANGE_TOP + 1, x, -18))      # M3 clearance D3.4 (IR foot)
    add('03-001', '노즈', nose, '#d2b78c', 'PEEK (가정)', '가공', explode=(0, 0, -40),
        note='몸체140x24x48 + 플랜지148x44x8, 호스 수직 구멍 D6, M4 체결 D4.5, IR 구멍 D19')

    # ---------------- 03-002 housing body (Al)
    HX, HY = P['housing_xy']
    hz0, ft, wt, top = P['housing_z0'], P['floor_t'], P['wall_t'], P['body_top']
    hb = bx(-HX / 2, HX / 2, -HY / 2, HY / 2, hz0, top).cut(
        bx(-HX / 2 + wt, HX / 2 - wt, -HY / 2 + wt, HY / 2 - wt, hz0 + ft, top + 1))
    bosses = [(sx * 70, sy * 60) for sx in (-1, 1) for sy in (-1, 1)] + [(70, -30), (-70, 30)]   # side bosses clear module
    for (x, y) in bosses:
        zb = hz0 + ft - 0.5 if abs(y) == 60 else 90.0   # side bosses hang from Z90 to clear flange/strips
        hb = hb.fuse(bx(x - 6, x + 6, y - 6, y + 6, zb, top))
    zpb = hz0 + ft + KS.PORT_BOSS['h']                                              # fitting port boss top (Z68)
    for (x, y) in P['nozzle_xy'].values():
        hb = hb.fuse(cz(KS.PORT_BOSS['d'] / 2, hz0 + ft - 0.5, zpb, x, y))
    hb = hb.cut(bx(-71, 71, -13.3, 13.3, hz0 - 1, hz0 + ft + 1))                    # nose opening 142x26.6
    for (x, y) in bosses:
        hb = hb.cut(cz(1.65, top - 14, top + 1, x, y))                              # M4 tap drill D3.3 x14
    for x in (-60, 60):
        for y in (-18, 18):
            hb = hb.cut(cz(KS.THREAD[KS.NOSE_BOLT]['drill'] / 2, hz0 - 1, hz0 + ft + 1, x, y))   # M4 tap drill D3.3 through
    for x in (6, 18):
        hb = hb.cut(cz(1.25, hz0 - 1, hz0 + ft + 1, x, -18))                      # M3 tap drill through
    for k, (x, y) in P['nozzle_xy'].items():
        hb = hb.cut(cz(KS.THREAD['M5']['drill'] / 2, zpb - KS.PORT['drill_depth'], zpb + 1, x, y))   # M5 port drill 9
        hb = hb.cut(cz(1.25, hz0 - 1, zpb - KS.PORT['drill_depth'] + 0.5, x, y))     # air passage D2.5
        for xx in (x - 9, x + 9):
            hb = hb.cut(cz(1.7, hz0 - 1, hz0 + ft + 1, xx, y))                    # M3 clearance
    for (x, y, sg) in [(-35, -HY / 2, 1), (5, -HY / 2, 1), (-5, HY / 2, -1), (35, HY / 2, -1)]:
        hb = hb.cut(cyl(1.7, wt + 2, (x, y - sg * 1, 104), (0, sg, 0)))            # unit screws through wall
    add('03-002', '하우징 몸체', hb, '#9baab5', 'Al6061-T6 (가정)', '가공', explode=(0, 0, 40),
        note='160x140, 몸체 높이66(Z58~124), 벽4/바닥6, 보스6(M4), 포트 보스 D11x4, 노즐 공기 통로')

    # ---------------- 03-003 top plate (structural)
    tp = bx(-HX / 2, HX / 2, -HY / 2, HY / 2, top, Z_TOP)
    for (x, y) in bosses:
        tp = tp.cut(cz(2.25, top - 1, Z_TOP + 1, x, y))                            # M4 clearance D4.5
    for i in range(4):
        a = math.radians(45 + 90 * i)
        x, y = P['pcd_lc'] / 2 * math.cos(a), P['pcd_lc'] / 2 * math.sin(a)
        tp = tp.cut(cz(2.75, top - 1, Z_TOP + 1, x, y)).cut(cz(4.75, top - 1, top + 5.5, x, y))
    for (x, y) in P['pass_holes']:
        tp = tp.cut(cz(P['pass_hole_d'] / 2, top - 1, Z_TOP + 1, x, y))
    add('03-003', '상판', tp, '#b8c4cc', 'Al6061-T6 (가정)', '가공', explode=(0, 0, 110),
        note='t10 구조 상판, M4x6 체결, 로드셀 4xM5 PCD60(가정), 통과 구멍 D20x2')

    # ---------------- 03-004~006 retainers
    for no, nm, x0, x1, y0, y1 in [('03-004', '누름판 앞', -70, 70, 14, 22), ('03-005', '누름판 뒤 좌', -70, -12, -22, -14),
                                   ('03-006', '누름판 뒤 우', 36, 70, -22, -14)]:
        s = bx(x0, x1, y0, y1, Z_FLANGE_TOP, Z_FLANGE_TOP + 4)
        for x in (-60, 60):
            if x0 < x < x1:
                s = s.cut(cz(KS.CLEAR_2[KS.NOSE_BOLT] / 2, Z_FLANGE_TOP - 1, Z_FLANGE_TOP + 5, x, (y0 + y1) / 2))
        add(no, nm, s, '#6d808a', 'Al6061-T6 (가정)', '가공', explode=(0, 0, 70))

    # ---------------- cup line x2
    for tag, x in (('L', -cx), ('R', cx)):
        b = bx(x - 20, x + 20, -10, 10, 10, 16)
        b = b.cut(cz(2.75, 9, 17, x, 0))                                            # D5.5 for nipple M5
        for xx in (x - 12, x + 12):
            b = b.cut(cz(1.7, 9, 17, xx, 0)).cut(cz(3.25, 9, 13.3, xx, 0))          # D3.4 + cbore D6.5x3.3
        add('03-007', '컵 브래킷 ' + tag, b, '#798b95', 'Al6061-T6 (가정)', '가공', explode=(0, 0, -70))
        # nipple (purchased envelope): shoulder D8 Z7.5-10, M5 Z10-22 (modelled D4.8), barb D3.2 Z22-28, bore D2
        nip = cz(4, 7.5, 10, x, 0).fuse(cz(2.4, 10, 22, x, 0)).fuse(cz(1.6, 22, 28, x, 0)).cut(cz(1.0, 7, 29, x, 0))
        add('03-102', '컵 니플 ' + tag, nip, '#b2b5b6', '구매품', '구매', explode=(0, 0, -95),
            note='M5 수나사/바브 D4 호스용 (가정, 선정 필요)')
        nut = hexprism(8.0, 16.0, 18.7, x, 0).cut(cz(2.5, 15, 20, x, 0))
        add('03-103', 'M5 얇은 너트 ' + tag, nut, '#555b60', '강 (가정)', '체결', explode=(0, 0, -30))
        cup = cq.Workplane('XY').ellipse(15, 10).workplane(offset=3).ellipse(13, 8).workplane(offset=7).ellipse(5, 4).loft().val().translate((x, 0, 0))
        cup = cup.cut(cq.Workplane('XY').ellipse(13.5, 8.5).extrude(2).val().translate((x, 0, -0.1)))
        cup = cup.cut(cz(4.05, 7.4, 10.1, x, 0)).cut(cz(1.0, -1, 11, x, 0))
        add('03-101', '타원 흡착컵 ' + tag, cup, '#30363a', '구매품', '구매', explode=(0, 0, -115),
            note='30x20, 끼움식(가정), 유효 흡착 면적 미확정')
        for i, xx in enumerate((x - 12, x + 12)):
            ins = cz(2.25, 16, 22, xx, 0).cut(cz(1.25, 15, 23, xx, 0))
            add('03-206', f'M3 인서트 {tag}{i}', ins, '#b9a276', '황동 (가정)', '구매', explode=(0, 0, -40),
                note='PEEK용 M3 인서트 외형 D4.5x6(나사산 생략), 형식 선정 필요')
            sc = shcs((xx, 0, 13.3), (0, 0, 1), 8, 2.4, 5.5, 3.0)
            add('03-205', f'M3x8 볼트 컵 {tag}{i}', sc, '#555b60', '강 8.8 (가정)', '체결', explode=(0, 0, -85))
        hp = [(x, 0, 28), (x, 0, 104), (x, -47 if tag == 'L' else 47, 104)]
        hose = tube(hp, P['hose_R'], 2.0, 1.0)
        add('03-301', '진공 호스 ' + tag, hose, '#238dc2', 'PU OD4/ID2 (가정)', '구매', explode=(0, 0, 30),
            note='굽힘 R16 (최소 굽힘반경 선정 필요), 바브 끼움 6 생략', path=(hp, P['hose_R'], 2.0))

    # ---------------- IR sensor + split clamp + cable
    irx = P['ir_x']
    add('03-104', 'IR 센서', cz(9.0, P['ir_z0'], P['ir_z0'] + P['ir_len'], irx, 0), '#555c66', '구매품', '구매',
        explode=(0, 0, 80), note='D18x40 외형, 측정거리40, 광점/방사율 미선정')
    rb = KS.IR_FIT['d'] / 2                                                          # D18 H8 (nominal in the model)
    rear = bx(-10, 34, -22, -0.25, Z_FLANGE_TOP, Z_FLANGE_TOP + 8).cut(cz(rb, 70, 82, irx, 0))
    front = bx(-10, 34, 0.25, 13.0, Z_FLANGE_TOP, Z_FLANGE_TOP + 8).cut(cz(rb, 70, 82, irx, 0))
    for xs in (-4, 28):
        rear = rear.cut(cyl(1.7, 24, (xs, -23, 76), (0, 1, 0)))
        front = front.cut(cyl(1.25, 10.0, (xs, 0.2, 76), (0, 1, 0)))
    for xs in (6, 18):
        rear = rear.cut(cz(1.7, 70, 82, xs, -18))
    add('03-008', 'IR 클램프 뒤', rear, '#878a8d', 'Al6061-T6 (가정)', '가공', explode=(0, -25, 90))
    add('03-009', 'IR 클램프 앞', front, '#878a8d', 'Al6061-T6 (가정)', '가공', explode=(0, 25, 90))
    for i, xs in enumerate((-4, 28)):
        add('03-204', f'M3x30 볼트 IR 조임{i}', shcs((xs, -22, 76), (0, 1, 0), 30, 2.4, 5.5, 3.0), '#555b60',
            '강 8.8 (가정)', '체결', explode=(0, -45, 90))
    for i, xs in enumerate((6, 18)):
        add('03-203', f'M3x25 볼트 IR 발{i}', shcs((xs, -18, 80), (0, 0, -1), 25, 2.4, 5.5, 3.0), '#555b60',
            '강 8.8 (가정)', '체결', explode=(0, 0, 100))
    cp = [(irx, 0, 80), (irx, 0, 114), (51, 25, 114), (51, 25, 150)]
    cab = tube(cp, P['cable_R'], 2.0)
    add('03-105', 'IR 케이블', cab, '#343b43', '구매품', '구매', explode=(0, 0, 80),
        note='D4 가정, 굽힘 R15, 커넥터/최소 굽힘반경 선정 필요', path=(cp, P['cable_R'], 2.0))

    # ---------------- retainer bolts M4x18 (retainer 4 + flange 8 + floor 6)
    for ix, x in enumerate((-60, 60)):
        for iy, y in enumerate((-18, 18)):
            add('03-201', f'M4x18 볼트 누름판{ix}{iy}', shcs((x, y, Z_FLANGE_TOP + 4), (0, 0, -1), 18, 3.2, 7.0, 4.0),
                '#51575c', '강 8.8 (가정)', '체결', explode=(0, 0, 90), note='토크/와셔 사양은 PEEK 크리프 검토 후')

    # ---------------- cooling nozzle blocks (under floor) + air fittings + hoses
    for tag, (x, y) in P['nozzle_xy'].items():
        nbk = bx(x - 13, x + 13, y - 8, y + 8, 44, hz0)
        nbk = nbk.cut(cz(1.25, 43, hz0 + 1, x, y))                                   # orifice D2.5
        o = KS.ORING_FACE                                                            # KS P6 face groove (36)
        r_out, r_in = o['D_int'] / 2, o['D_int'] / 2 - o['G']
        nbk = nbk.cut(cz(r_out, hz0 - o['H'], hz0 + 1, x, y).cut(cz(r_in, hz0 - 2, hz0 + 2, x, y)))
        for xx in (x - 9, x + 9):
            nbk = nbk.cut(cz(1.25, hz0 - 8, hz0 + 1, xx, y))                          # M3 tap drill 8
            add('03-207', f'M3x12 볼트 노즐 {tag}{xx:+.0f}', shcs((xx, y, hz0 + ft), (0, 0, -1), 12, 2.4, 5.5, 3.0),
                '#555b60', '강 8.8 (가정)', '체결', explode=(0, 0, 60))
        add('03-010', '노즐 블록 ' + tag, nbk, '#808b92', 'Al6061-T6 (가정)', '가공', explode=(0, 0, -30),
            note='26x16x14, 수직 토출 D2.5, 상면 O링 홈 P6 (규격집 36항)')
        ring = cz(r_out - 0.02, hz0 - o['H'] + 0.02, hz0 - 0.02, x, y).cut(cz(r_in + 0.4, hz0 - 2, hz0 + 1, x, y))
        add('03-213', 'O링 P6 ' + tag, ring, '#2b2b2b', 'FKM (가정)', '구매', explode=(0, 0, -20),
            note='압축 상태 외형 (가정), 굵기 1.9, 재질 내열 확인 필요')
        fit = cz(2.05, zpb - 5, zpb, x, y).fuse(hexprism(8, zpb, zpb + 4, x, y)).fuse(
            cz(3.5, zpb + 4, zpb + 16, x, y)).cut(cz(1.0, zpb - 6, zpb + 17, x, y))
        add('03-106', '푸시인 피팅 M5-D4 ' + tag, fit, '#4b89b3', '구매품', '구매', explode=(0, 0, 40),
            note='외형 가정, 선정 필요')
    zf = zpb + 16                                                                    # fitting top (Z84)
    apL = [(-55, -31, zf), (-55, -31, 110), (53, -33, 110), (53, -33, 150)]
    apR = [(55, 31, zf), (55, 31, 100), (53, 33, 150)]
    air_L = tube(apL, P['air_R'], 2.0, 1.0)
    air_R = tube(apR, P['air_R'], 2.0, 1.0)
    add('03-302', '냉각 공기 호스 L', air_L, '#4ca6b8', 'PU OD4 (가정)', '구매', explode=(0, 0, 60), path=(apL, P['air_R'], 2.0))
    add('03-302', '냉각 공기 호스 R', air_R, '#4ca6b8', 'PU OD4 (가정)', '구매', explode=(0, 0, 60), path=(apR, P['air_R'], 2.0))

    # ---------------- vacuum units (ejector+valves+switch+check valve, integrated, assumed envelope)
    for tag, (x0, x1, y0, y1, px, py0, py1, sx) in {
            'L': (-50, 20, -66, -50, -40, -50, -47, (-35, 5)),
            'R': (-20, 50, 50, 66, 40, 47, 50, (-5, 35))}.items():
        unit = bx(x0, x1, y0, y1, 84, 124)
        for xs in sx:                                                   # tapped M3 mounting holes (assumed)
            yi = y0 if tag == 'L' else y1
            unit = unit.cut(cyl(1.25, 7, (xs, yi - (1 if tag == 'L' else -1), 104), (0, 1 if tag == 'L' else -1, 0)))
        unit = unit.fuse(cyl(3.0, abs(py1 - py0), (px, min(py0, py1), 104), (0, 1, 0)))
        cy0 = y1 if tag == 'L' else y0 - 6
        unit = unit.fuse(cyl(4.0, 6, (12 if tag == 'L' else -12, cy0, 116), (0, 1, 0)))   # connector (assumed)
        add('03-107', '진공 유닛 ' + tag, unit, '#5d6b78', '구매품', '구매', explode=(0, -60 if tag == 'L' else 60, 0),
            note='이젝터·공급/파기 밸브·진공 스위치·역지 밸브 일체형 가정 70x16x40, 선정 필요')
        wall_y = -HY / 2 if tag == 'L' else HY / 2
        sg = 1 if tag == 'L' else -1
        for xs in sx:
            add('03-212', f'M3x8 볼트 유닛 {tag}{xs:+.0f}', shcs((xs, wall_y, 104), (0, sg, 0), 8, 2.4, 5.5, 3.0),
                '#555b60', '강 8.8 (가정)', '체결', explode=(0, -80 if tag == 'L' else 80, 0))

    # ---------------- top plate screws, load cell, adapter, changer tool, module (tool side)
    for (x, y) in bosses:
        add('03-208', f'M4x20 볼트 상판{x:+.0f}{y:+.0f}', shcs((x, y, Z_TOP), (0, 0, -1), 20, 3.2, 7.0, 4.0),
            '#555b60', '강 8.8 (가정)', '체결', explode=(0, 0, 120))
    lc = cz(P['lc_d'] / 2, Z_TOP, Z_LC_TOP)
    for i in range(4):
        a = math.radians(45 + 90 * i)
        x, y = 30 * math.cos(a), 30 * math.sin(a)
        lc = lc.cut(cz(2.1, Z_TOP - 1, Z_TOP + 9, x, y)).cut(cz(2.1, Z_LC_TOP - 9, Z_LC_TOP + 1, x, y))
        add('03-209', f'M5x12 볼트 로드셀 하{i}', shcs((x, y, top + 5.5), (0, 0, 1), 12, 4.1, 8.5, 5.0), '#555b60',
            '강 8.8 (가정)', '체결', explode=(0, 0, 100))
    add('03-108', '로드셀', lc, '#a3abb0', '구매품', '구매', 'common', explode=(0, 0, 140),
        note='D80x25, 측정 범위 500 N 가정(허용 인장력 아님), 패턴 4xM5 PCD60 가정')
    ad = cz(50, Z_LC_TOP, Z_AD_TOP)
    for i in range(4):
        a = math.radians(45 + 90 * i)
        x, y = 30 * math.cos(a), 30 * math.sin(a)
        ad = ad.cut(cz(2.75, Z_LC_TOP - 1, Z_AD_TOP + 1, x, y)).cut(cz(4.75, Z_AD_TOP - 5.5, Z_AD_TOP + 1, x, y))
        add('03-210', f'M5x12 볼트 로드셀 상{i}', shcs((x, y, Z_AD_TOP - 5.5), (0, 0, -1), 12, 4.1, 8.5, 5.0),
            '#555b60', '강 8.8 (가정)', '체결', explode=(0, 0, 160))
        a2 = math.radians(90 * i)
        x2, y2 = 45 * math.cos(a2), 45 * math.sin(a2)
        ad = ad.cut(cz(2.75, Z_LC_TOP - 1, Z_AD_TOP + 1, x2, y2)).cut(cz(4.75, Z_LC_TOP - 1, Z_LC_TOP + 5.5, x2, y2))
        add('03-211', f'M5x12 볼트 교환기{i}', shcs((x2, y2, Z_LC_TOP + 5.5), (0, 0, 1), 12, 4.1, 8.5, 5.0),
            '#555b60', '강 8.8 (가정)', '체결', explode=(0, 0, 150))
    add('03-011', '로드셀 어댑터판', ad, '#c4ccd2', 'Al6061-T6 (가정)', '가공', explode=(0, 0, 150),
        note='D100x10, 하면 PCD60/상면 PCD90 패턴은 구매품 선정 후 확정')
    ct = cz(50, Z_AD_TOP, Z_TOOL_TOP)
    for i in range(4):
        a2 = math.radians(90 * i)
        ct = ct.cut(cz(2.1, Z_AD_TOP - 1, Z_AD_TOP + 11, 45 * math.cos(a2), 45 * math.sin(a2)))
    add('03-109', '교환기 툴 플레이트', ct, '#598aad', '구매품', '구매', 'common', explode=(0, 0, 170),
        note='D100x25 외형, 하면 4xM5 PCD90 가정, 위치 핀 미모델')
    m = P['module']
    add('03-110', '통과 모듈 툴측', bx(50, 50 + m[0], -m[1] / 2, m[1] / 2, Z_AD_TOP, Z_AD_TOP + m[2]), '#58717d', '구매품',
        '구매', 'common', explode=(0, 0, 170), note='공압6+신호12 가정, 포트 상세 미정')
    # common (not part of tool 03 BOM): master, master module, tilt
    add('CM-01', '교환기 마스터', cz(50, Z_TOOL_TOP, Z_MASTER_TOP), '#9aa3a8', '구매품', '공통', 'common',
        explode=(0, 0, 190))
    add('CM-02', '통과 모듈 마스터측', bx(50, 50 + m[0], -m[1] / 2, m[1] / 2, Z_TOOL_TOP, Z_TOOL_TOP + m[2]), '#58717d',
        '구매품', '공통', 'common', explode=(0, 0, 190))
    tx, ty, tz = P['tilt']
    add('CM-03', '기울임축 유닛', bx(-tx / 2, tx / 2, -ty / 2, ty / 2, Z_MASTER_TOP, Z_MASTER_TOP + tz), '#618ba5',
        '구매품', '공통', 'common', explode=(0, 0, 200), note='80x80x60, Y축, +-15도는 기계 범위')
    return parts


# ----------------------------------------------------------------------------- reference cell geometry
def reference(term_inner=58.0, term_outer=70.0, term_h=3.0, res_h=2.0):
    """Virtual CTP cells with assumed vent/terminal/busbar residue/pads. All assumed."""
    L, T, H = P['cell']
    refs = []

    def r(name, s, color, role):
        refs.append(dict(name=name, solid=s, color=color, role=role))

    for i in (-1, 0, 1):
        yc = i * P['pitch_y']
        r(f'REF_셀{i:+d}', bx(-L / 2, L / 2, yc - T / 2, yc + T / 2, -H, 0).cut(cz(7.0, -0.3, 0.1, 0, yc)),
          '#709bae' if i == 0 else '#93a9b4', 'target' if i == 0 else 'static')
        for sx in (-1, 1):
            xa, xb = sorted((sx * term_inner, sx * term_outer))
            r(f'REF_단자{i:+d}{"L" if sx < 0 else "R"}', bx(xa, xb, yc - 8, yc + 8, 0, term_h), '#c9a96e',
              'target' if i == 0 else 'static')
            r(f'REF_버스바잔여{i:+d}{"L" if sx < 0 else "R"}', bx(xa + 1, xb - 1, yc - 10, yc + 10, term_h, term_h + res_h),
              '#b87333', 'target' if i == 0 else 'static')
        r(f'REF_벤트{i:+d}', cz(7.0, -0.3, 0.0, 0, yc), '#e0e0e0', 'target' if i == 0 else 'static')
        r(f'REF_접착층{i:+d}', bx(-L / 2, L / 2, yc - T / 2, yc + T / 2, -H - 1, -H), '#d7a266',
          'adhesive_target' if i == 0 else 'static')
    for sg in (-1, 1):
        y0 = sg * (T / 2)
        r(f'REF_패드{"+" if sg > 0 else "-"}', bx(-72, 72, min(y0, y0 + sg * P['pad_t']), max(y0, y0 + sg * P['pad_t']), -89, -2),
          '#e6c26b', 'static')
    r('REF_X이웃셀', bx(L / 2 + 2, L / 2 + 2 + L, -T / 2, T / 2, -H, 0), '#93a9b4', 'static')
    r('REF_X끝패드', bx(L / 2, L / 2 + 2, -12, 12, -89, -2), '#e6c26b', 'static')
    r('REF_블록경계부재', bx(-L / 2 - 15, -L / 2 - 5, -50, 50, -H, -10), '#8d99a6', 'static')
    r('REF_냉각판', bx(-90, 230, -50, 50, -H - 6, -H - 1), '#a5b8bf', 'static')
    return refs


def ir_line_of_sight(aperture_d=8.0, spot_d=6.0):
    """Assumed optical envelope: lens aperture at Z=40 to spot on cell top (Z=0)."""
    x = P['ir_x']
    return cq.Workplane('XY').workplane(offset=0.05).center(x, 0).circle(spot_d / 2).workplane(
        offset=P['ir_z0'] - 0.1).circle(aperture_d / 2).loft().val()
