"""D-02 03 셀 분리 공구 조립도 (R03) - 3 sheets, generated from the R03 solids (tool03_r03.build())."""
import math
import numpy as np
import cadquery as cq
import shapely.geometry as sg

from common import T, load, bom_rows, BOM_INFO, CUT_NOS, DATE, WORK, STATUS, TEAM, HERE
import draw_lib as DL
from draw_lib import Sheet, View, project, dedupe

OUT = HERE / 'out'
OUT.mkdir(exist_ok=True)
P = T.P

parts, QTY, ITEM = load()
is_cm = lambda p: p['no'].startswith('CM')
cut_parts = [p for p in parts if p['no'] in CUT_NOS]
whole_parts = [p for p in parts if p['no'] not in CUT_NOS and not is_cm(p)]
cm_parts = [p for p in parts if is_cm(p)]
tool_solids = [p['solid'] for p in parts if not is_cm(p)]
cm_solids = [p['solid'] for p in cm_parts]

HATCH = {'03-001': (45, 2.4), '03-002': (135, 2.0), '03-003': (45, 2.0), '03-004': (135, 1.6), '03-005': (135, 1.6),
         '03-006': (135, 1.6), '03-007': (135, 1.5), '03-008': (45, 1.5), '03-009': (135, 1.5), '03-010': (45, 1.5),
         '03-011': (135, 2.0)}

n_pic = np.array([1, -1.2, -0.5]) / np.linalg.norm([1, -1.2, -0.5])
DL.VIEWDIR['pic'] = (tuple(n_pic), tuple(np.array([-n_pic[1], n_pic[0], 0.0]) / np.linalg.norm(n_pic[:2])))

TB = dict(work=WORK, title='03 셀 분리 공구 조립도', dwg_no='D-02', date=DATE, rev='R03', status=STATUS, team=TEAM)


def B(no):
    return ITEM[no]


_ROD = {}


def disp(p):
    """Display solid for sections: hoses/cable as solid rods so a cut does not expose the bore."""
    if p.get('path'):
        k = id(p)
        if k not in _ROD:
            pts, R, ro = p['path']
            _ROD[k] = T.tube(pts, R, ro, 0.0)
        return _ROD[k]
    return p['solid']


def section_view(v, p0, box=None, whole_box=None, phantom=True, spacing_k=1.0):
    cs = [p['solid'] for p in cut_parts]
    specs = {i: dict(angle=HATCH[p['no']][0], spacing=HATCH[p['no']][1] * spacing_k) for i, p in enumerate(cut_parts)}
    return v.section(parts, p0, cs, [disp(p) for p in whole_parts], cm_solids if phantom else (), box=box,
                     hatch_specs=specs, whole_box=whole_box)


def cell_phantom_front(v, depth=10.0):
    L = P['cell'][0] / 2
    v.phantom_poly([(-L, -depth), (-L, 0), (L, 0), (L, -depth)])
    for s in (-1, 1):
        a, b = sorted((s * 58, s * 70))
        v.phantom_poly([(a, 0), (a, 3), (b, 3), (b, 0)])
        v.phantom_poly([(a + 1, 3), (a + 1, 5), (b - 1, 5), (b - 1, 3)])


def cell_phantom_right(v, depth=10.0):
    T_ = P['cell'][1] / 2
    for yc in (-P['pitch_y'], 0, P['pitch_y']):
        v.phantom_poly([(yc - T_, -depth), (yc - T_, 0), (yc + T_, 0), (yc + T_, -depth)])
    v.phantom_poly([(-8, 0), (-8, 3), (8, 3), (8, 0)])
    v.phantom_poly([(-10, 3), (-10, 5), (10, 5), (10, 3)])


def balloons(sh, items):
    for no, view, uv, bp in items:
        sh.balloon(B(no), bp, view.P(*uv))


# ============================================================================ sheet 1/3
def sheet1():
    sh = Sheet()
    sh.frame()
    sh.title_block(dict(TB, scale='1:2', sheet='1/3'))
    S = 0.5
    vf = View(sh, 'front', S, (112, 124))
    vr = View(sh, 'right', S, (240, 124))
    vb = View(sh, 'bottom', S, (112, 68))

    # ---------------- front: full section A-A at Y = 0
    section_view(vf, (0, 0, 0))
    cell_phantom_front(vf)
    for x in (-40, 40):
        vf.axis((x, -14), (x, 30), ext=0)
    vf.axis((12, -9), (12, 84), ext=0)
    vf.axis((0, -9), (0, 300), ext=0)
    vf.axis((-6, 264), (6, 264), ext=0, layer='PHANTOM')
    sh.text('기울임축 중심 (공통부)', vf.P(8, 266), 2.5)
    sh.view_label('단면 A-A', (vf.P(0, 0)[0], 278))
    # dims (front)
    vf.dim((-40, 0), (40, 0), at=112)
    vf.dim((0, -9), (12, -9), at=106.5)
    vf.dim((74, 0), (74, 64), at=166, orient='v')
    # detail B circle
    c = vf.P(40, 15)
    sh.detail_circle(c, 11.5, 'B', (c[0] + 11, c[1] - 11))
    # cutting plane D-D (Z = 75.5), end marks only
    yD = vf.P(0, 75.5)[1]
    for xa, xb in ((60, 69), (164, 155)):
        sh.line((xa, yD), (xb, yD), 'CUT_THK')
        tip = (xa + (xb - xa) * 0.35, yD - 6.0)
        sh.line(((xa + (xb - xa) * 0.35), yD), (tip[0], tip[1] + 2.5), 'DIM')
        sh.arrow(tip, (tip[0], yD))
        sh.text('D', (tip[0] - 3.2 if xa < 100 else tip[0] + 3.2, tip[1] + 1.0), 3.5, 'MIDDLE_CENTER')
    # balloons (front)
    balloons(sh, [
        ('03-109', vf, (-35, 185), (48, 230)), ('03-011', vf, (-25, 164), (48, 220)),
        ('03-108', vf, (-30, 146), (48, 210)), ('03-208', vf, (-70, 136.5), (48, 200)),
        ('03-003', vf, (-55, 129), (48, 190)), ('03-002', vf, (-78, 100), (48, 178)),
        ('03-004', vf, (-45, 74), (48, 164)), ('03-001', vf, (-58, 40), (48, 148)),
        ('03-007', vf, (-57, 13), (48, 135)), ('03-101', vf, (-46, 3.5), (48, 123)),
        ('03-110', vf, (80, 182), (180, 226)), ('03-211', vf, (45, 162), (180, 208)),
        ('03-107', vf, (45, 95), (180, 190)),
        ('03-301', vf, (40.0, 50), (180, 150)), ('03-104', vf, (16, 56), (180, 140)),
    ])

    # ---------------- right side view (exterior)
    vr.outline(tool_solids)
    pv, _ = project(cm_solids, 'right')
    vr.draw_prims(dedupe(pv), 'PHANTOM')
    cell_phantom_right(vr)
    vr.axis((0, -9), (0, 300), ext=0)
    vr.axis((-6, 264), (6, 264), ext=0, layer='PHANTOM')
    x1 = vr.P(73, 0)[0]
    vr.dim((60, 0), (60, 16), at=x1 + 10, orient='v')
    vr.dim((60, 16), (60, 58), at=x1 + 10, orient='v')
    vr.dim((70, 58), (70, 134), at=x1 + 10, orient='v')
    vr.dim((50, 134), (50, 194), at=x1 + 10, orient='v', text='<> ※')
    vr.dim((60, 0), (50, 194), at=x1 + 19, orient='v')
    vr.dim((60, 0), (0, 264), at=x1 + 28, orient='v', text='(<>)')
    vr.dim((-12, 16), (12, 16), at=vr.P(0, -18)[1])
    balloons(sh, [('03-010', vr, (31, 50), (268, 138)), ('03-212', vr, (-71.5, 104), (197, 166)),
                  ('03-105', vr, (25, 142), (262, 214)), ('03-302', vr, (33, 146), (275, 205))])

    # ---------------- bottom view (exterior)
    vb.outline(tool_solids)
    vb.axis((0, -75), (0, 75), ext=0)
    vb.axis((-86, 0), (94, 0), ext=0)
    for (x, y) in P['nozzle_xy'].values():
        vb.cmark((x, -y), 1.25, ext=2.0)
    for x in (-40, 40):
        vb.cmark((x, 0), 4.0, ext=2.0)
    vb.cmark((12, 0), 9.2, ext=2.0)
    vb.dim((-80, -70), (80, -70), at=24)
    vb.dim((-80, -70), (-80, 70), at=62, orient='v')
    # nozzle R at (55, 31) -> (u, v) = (55, -31); nozzle L at (-55, -31) -> (-55, 31)
    vb.dim((0, -31), (55, -31), at=vb.P(0, -62)[1])
    vb.dim((55, 0), (55, -31), at=vb.P(73, 0)[0], orient='v')
    vb.dim((0, 31), (-55, 31), at=vb.P(0, 48)[1])
    vb.dim((-55, 0), (-55, 31), at=vb.P(-73, 0)[0], orient='v')
    sh.cutline(vb.P(-80, 0), vb.P(90, 0), 'A', (0, -1), ext=5.0)
    sh.cutline(vb.P(40, -31), vb.P(70, -31), 'C', (0, -1), ext=3.0)

    # ---------------- pictorial (reference, from below)
    vi = View(sh, 'pic', 1 / 3, (352, 168))
    vi.outline(tool_solids)
    pv, _ = project(cm_solids, 'pic')
    vi.draw_prims(dedupe(pv), 'PHANTOM')
    sh.view_label('참고 입체도 (아래쪽에서, 1:3)', (352, 276))

    # ---------------- notes
    sh.lines_of_text([
        '주기',
        '1. 모든 치수는 설계 가정값이다. 실물·구매품 확인 전 제작 지시용이 아니다.',
        '2. Z=0은 셀 상면 = 컵 밀봉면 (가정). 셀·단자·잔여 버스바는 가상선.',
        '3. 교환기 마스터·마스터측 모듈·기울임축은 공통부 (가상선, 03 부품표 제외).',
        '4. 단면도에서 볼트·너트·인서트·호스·센서·구매품은 길이 방향 단면·해칭을 하지 않음.',
        '5. ※ : 구매품 선정 후 확정할 치수 (선정 필요).',
        '6. 상세·단면 B~E는 2/3, 부품표는 3/3.',
        '7. CAD 검사·계산 범위는 3/3 참조 (검증 아님).',
        '   조립·필링·강도·열·진공 유지·전기 절연·비상 대응은 미검증.',
    ], (196, 104), h=2.5, gap=1.65)
    return sh


def detail_frame(sh, v, c, r, label, lab_dy=6.0):
    pc = v.P(*c)
    sh.circle(pc, r * v.scale, 'BREAK')
    sh.view_label(label, (pc[0], pc[1] + r * v.scale + lab_dy))


def rect_break(sh, v, x0, y0, x1, y1, amp=0.8, wl=6.0):
    """Thin freehand-like break boundary around a partial view (model rectangle)."""
    (a, b), (c, d) = v.P(x0, y0), v.P(x1, y1)
    def wav(p, q):
        p, q = np.array(p), np.array(q)
        L = np.linalg.norm(q - p)
        n = max(2, int(L / wl * 4))
        t = np.linspace(0, 1, n + 1)
        dirv = (q - p) / L
        nrm = np.array([-dirv[1], dirv[0]])
        return [tuple(p + dirv * L * ti + nrm * amp * math.sin(2 * math.pi * L * ti / wl)) for ti in t]
    for p, q in [((a, b), (c, b)), ((c, b), (c, d)), ((c, d), (a, d)), ((a, d), (a, b))]:
        sh.pline(wav(p, q), 'BREAK')


# ============================================================================ sheet 2/3
def sheet2():
    sh = Sheet()
    sh.frame()
    sh.title_block(dict(TB, scale='1:2, 2:1', sheet='2/3'))

    # ---------------- section D-D (Z = 75.5, looking down), 1:2
    vd = View(sh, 'top', 0.5, (90, 212))
    section_view(vd, (0, 0, 75.5), phantom=False)
    vd.axis((-86, 0), (86, 0), ext=0)
    vd.axis((0, -76), (0, 76), ext=0)
    sh.view_label('단면 D-D (1:2)', (90, 262))
    detail_frame(sh, vd, (12, -4.5), 24, '', 0)
    pe = vd.P(12 + 17, -4.5 - 17)
    sh.text('E', (pe[0] + 2.0, pe[1] - 3.0), 3.5, 'MIDDLE_CENTER')
    balloons(sh, [
        ('03-002', vd, (-78, 40), (34, 252)), ('03-201', vd, (-60, 18), (34, 240)),
        ('03-004', vd, (-30, 18), (34, 228)), ('03-001', vd, (-66, 6), (34, 214)),
        ('03-005', vd, (-40, -18), (34, 198)), ('03-301', vd, (-40, 0), (34, 186)),
        ('03-207', vd, (-64, -31), (34, 174)),
        ('03-106', vd, (55, 31), (140, 252)), ('03-006', vd, (55, -18), (140, 182)),
    ])

    # ---------------- detail E (IR clamp), 2:1
    cE = (12.0, -4.5)
    vE = View(sh, 'top', 2.0, (200, 210), ref=cE, clip=sg.Point(*cE).buffer(24, 128))
    section_view(vE, (0, 0, 75.5), phantom=False)
    detail_frame(sh, vE, cE, 24, '상세 E (2:1)')
    vE.cmark((12, 0), 9.0, ext=3.0)
    for xs in (-4, 28):
        vE.axis((xs, -24), (xs, 10), ext=0)
    balloons(sh, [('03-008', vE, (30, -15), (252, 172)), ('03-009', vE, (30, 8), (252, 250)),
                  ('03-204', vE, (-4, -12), (160, 176)), ('03-203', vE, (6, -18), (172, 160)),
                  ('03-104', vE, (12, 5), (224, 264))])
    sh.leader(vE.P(12 + 9.0 * 0.7071, -9.0 * 0.7071), (226, 156), 'Ø18 H8/h8 (센서 h8 가정 ※)', end='arrow', side=1)

    # ---------------- section C-C (Y = 31, nozzle R), 2:1
    box = (38.0, 42.0, 72.0, 90.0)
    vC = View(sh, 'front', 2.0, (300, 212), ref=(55, 64), clip=sg.box(*box))
    section_view(vC, (0, 31, 0), phantom=False)
    rect_break(sh, vC, *box)
    vC.axis((55, 43), (55, 85), ext=0)
    for xx in (46, 64):
        vC.axis((xx, 49), (xx, 68), ext=0)
    sh.view_label('단면 C-C (2:1)', (300, 271))
    vC.dim((42, 44), (42, 58), at=vC.P(36, 0)[0] - 2, orient='v')
    vC.dim((46, 44), (64, 44), at=vC.P(0, 42)[1] - 4)
    balloons(sh, [('03-010', vC, (66, 50), (348, 186)), ('03-207', vC, (64, 61), (348, 200)),
                  ('03-106', vC, (57.5, 77), (348, 230)), ('03-302', vC, (56.5, 87.5), (348, 248)),
                  ('03-002', vC, (70, 61), (348, 214)), ('03-213', vC, (58.6, 57.3), (348, 172))])
    sh.leader(vC.P(55, 44), (279, 152), '토출구 Ø2.5, Z44 (셀 상면 기준, 가정)', end='arrow', side=1)

    # ---------------- interface pattern: load cell / changer (top view of adapter), 1:2
    ad = [p['solid'] for p in parts if p['no'] in ('03-011', '03-210', '03-211')]
    vI = View(sh, 'top', 0.5, (382, 212))
    vI.outline(ad, hidden=True)
    vI.pcd((0, 0), 30)
    vI.pcd((0, 0), 45)
    vI.axis((-54, 0), (54, 0), ext=0)
    vI.axis((0, -54), (0, 54), ext=0)
    for a in (45, 135):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        vI.axis((-36 * ca, -36 * sa), (36 * ca, 36 * sa), ext=0)
    sh.view_label('접속 패턴 (상면, 1:2)', (382, 248))
    balloons(sh, [('03-011', vI, (-35, -30), (362, 180)),
                  ('03-210', vI, (21.21, 21.21), (404, 240)), ('03-209', vI, (-21.21, -21.21), (404, 186))])
    sh.lines_of_text([f'4×M5 PCD60, 45° ※ : 로드셀 ({B("03-209")}·{B("03-210")})', f'4×M5 PCD90, 0° ※ : 교환기 ({B("03-211")})',
                      '외곽 Ø100 ※ (구매품 외형 가정)'],
                     (356, 160), h=2.3, gap=1.6)

    # ---------------- detail B (cup line), 2:1
    cB = (44.0, 14.0)
    vB = View(sh, 'front', 2.0, (80, 104), ref=cB, clip=sg.Point(*cB).buffer(24, 128))
    section_view(vB, (0, 0, 0), phantom=False)
    cell_phantom_front(vB, depth=6.0)
    detail_frame(sh, vB, cB, 24, '상세 B (2:1)')
    vB.axis((40, -6), (40, 37), ext=0)
    for xx in (28, 52):
        vB.axis((xx, 8), (xx, 26), ext=0)
    xd = vB.P(73, 0)[0]
    vB.dim((55, 0), (60, 10), at=xd, orient='v', text='<> ※')
    vB.dim((60, 10), (60, 16), at=xd, orient='v')
    vB.dim((55, 0), (58, 0), at=vB.P(0, -3.5)[1], text='3')
    sh.leader(vB.P(64, 1.5), (146, 66), '단자 (가정)', end='dot', side=1)
    balloons(sh, [('03-101', vB, (30, 4), (26, 74)), ('03-007', vB, (23, 13), (26, 88)),
                  ('03-205', vB, (28, 11.5), (26, 102)), ('03-206', vB, (28, 19), (26, 116)),
                  ('03-001', vB, (25, 30), (26, 130)), ('03-301', vB, (40, 33), (146, 146)),
                  ('03-102', vB, (40, 25), (146, 132)), ('03-103', vB, (42, 17.3), (146, 118))])

    # ---------------- notes
    sh.lines_of_text([
        '조립·정비 주기 (가정, 미검증)',
        f'1. 컵({B("03-101")})은 니플({B("03-102")}) 어깨에 끼운다. 컵을 빼면 아래에서 M3×8({B("03-205")})에 접근해 브래킷({B("03-007")})을 교체한다.',
        f'2. 니플({B("03-102")})은 얇은 너트({B("03-103")})로 브래킷에 고정, 호스({B("03-301")})는 노즈의 Ø6 수직 구멍으로 위로 뺀다.',
        f'3. IR 센서({B("03-104")})는 위에서 넣고 클램프({B("03-008")}·{B("03-009")})를 M3×30({B("03-204")}) 2개로 조인다 (Ø18 H8/h8).',
        f'   클램프는 M3×25({B("03-203")})로 플랜지를 지나 바닥에 체결 - 센서를 노즈 Ø19 구멍 중심에 맞춘 뒤 조인다.',
        f'4. 노즈 플랜지는 누름판({B("03-004")}~{B("03-006")})과 M4×18({B("03-201")}) 4개로 하우징 바닥에 고정한다.',
        '   체결 토크 제안 1.2~1.6 N·m (예압 1.5~2.0 kN, K=0.2 가정) - PEEK 크리프·열 영향 미검증, 접시 스프링 와셔 검토.',
        f'5. 노즐 블록({B("03-010")})은 바닥 아래에서 M3×12({B("03-207")}) 2개로 고정하고 O링 P6({B("03-213")})으로 밀봉한다 (규격집 36항).',
        f'   노즐 L의 X-46 나사는 냉각 공기 호스 L({B("03-302")})을 분리한 뒤 접근한다.',
        f'6. 로드셀({B("03-108")})·교환기({B("03-109")}) 패턴 PCD60/PCD90, M5 물림 길이는 구매품 사양 확인 후 확정한다 (※).',
        f'7. 호스({B("03-301")}·{B("03-302")})와 케이블({B("03-105")})이 로드셀 위아래를 잇고 있어 측정 하중에 영향을 줄 수 있다 (검토 필요).',
    ], (160, 146), h=2.5, gap=1.7)
    return sh


# ============================================================================ sheet 3/3 (parts list)
def sheet3():
    sh = Sheet()
    sh.frame()
    sh.title_block(dict(TB, title='03 셀 분리 공구 조립도 - 부품표', scale='-', sheet='3/3'))
    rows = bom_rows(QTY, ITEM)
    rows = [[r[0], r[1], r[2], r[3], r[4], r[5], r[6], 'R03 3D' if r[5] == '가공' else '가정', r[7]] for r in rows]
    cols = [9, 17, 50, 10, 30, 12, 48, 16, 14]
    sh.text('부품표 (03 공구, R03)', (25, 279), 3.5)
    y = sh.table(25, 276, cols, ['번', '품번', '품명', '수량', '재질', '구분', '구매 규격·비고', '근거', '도면'], rows,
                 rh=6.0, hh=7.0, h=2.5, align=['C', 'C', 'L', 'C', 'L', 'C', 'L', 'C', 'C'])
    sh.lines_of_text([
        '- 수량은 R03 3D 모델의 부품 인스턴스 수에서 자동 집계.',
        '- 공통부 CM-01 교환기 마스터, CM-02 통과 모듈 마스터측, CM-03 기울임축 유닛은 03 부품표에서 제외.',
        '- 품번은 R02 스크립트 순서(노즈 = 03-001)를 따름. v0.3 가이드 예시표(03-001 = 하우징)와 다름.',
        '- 체결품 길이는 R03 모델 기준 가정값. 실제 물림 길이·와셔는 구매품 선정 후 재확인.',
    ], (25, y - 6), h=2.5, gap=1.7)

    xr = 250
    sh.text('선정 필요 (※) 위치', (xr, 279), 3.5)
    sel = [
        ['타원 흡착컵', '끼움 구조, 자유 높이 10, 유효 흡착 면적'],
        ['컵 니플·얇은 너트', 'M5 어깨 Ø8, 바브 Ø4, 브래킷 Ø5.5 구멍'],
        ['M3 인서트', '형식(열압입/자가 탭), 노즈 구멍 Ø4.5×8'],
        ['IR 센서', 'Ø18×40, 측정 거리 40, 광점, 외경 공차 (클램프 Ø18 H8)'],
        ['진공 유닛', '70×16×40, 포트·커넥터 위치, 고정 나사'],
        ['푸시인 피팅·호스', 'M5-Ø4, 나사 길이 6 이하, 최소 굽힘 R16/R15'],
        ['노즐 O링', 'P6 (규격집 36항 홈), FKM 가정 - 내열 확인'],
        ['로드셀', 'Ø80×25, 범위, 4×M5 PCD60, 허용 모멘트'],
        ['교환기 툴 플레이트', 'Ø100×25, 4×M5 PCD90, 위치 핀'],
        ['통과 모듈', '40×30×25, 공압 6 + 신호 12 가정'],
    ]
    y2 = sh.table(xr, 276, [42, 113], ['항목', '이번 도면의 가정 치수'], sel, rh=6.0, hh=7.0, h=2.5, align=['L', 'L'])
    sh.text('검사·검증 상태', (xr, y2 - 9), 3.5)
    sh.lines_of_text([
        'CAD에서 수행 (검증 아님): 솔리드 유효성, 정지 상태 겹침 0건,',
        '   정비 공구 접근 외곽 21곳 중 1곳 막힘 (냉각 호스 L 분리 후 접근),',
        '   가정 셀·단자·패드 기준 필링 회전 간섭 계산, 질량·모멘트·체결 하중 수계산.',
        '미검증: 실물 조립, 필링 동작, 강도, 열, 진공 유지, 전기 절연, 비상 대응.',
        '규격집(2025 CAD 실기용 KS 발췌)을 참고한 검토도. KS 원문 대조·완전 적합·표준품 호환은 주장하지 않는다.',
        '공차·거칠기·끼워맞춤 근거는 D-04 근거표 (KS_적용_근거표) 참조.',
    ], (xr, y2 - 15), h=2.5, gap=1.7)
    return sh


if __name__ == '__main__':
    import sys
    which = sys.argv[1:] or ['1', '2', '3']
    for k, fn in (('1', sheet1), ('2', sheet2), ('3', sheet3)):
        if k in which:
            sh = fn()
            stem = f'D-02_R03_{k}of3'
            sh.save(OUT / f'{stem}.dxf')
            sh.render(OUT / f'{stem}.pdf', OUT / f'{stem}.png', dpi=150)
    print('ok')
