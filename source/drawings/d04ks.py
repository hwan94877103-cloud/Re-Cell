"""D-04 03 공구 부품도 (R03, KS 개정) - 규격집 형식(거칠기 기호, 끼워맞춤, 기하공차·데이텀, 주서, 부품란).
값은 ks_spec.py 하나에서 읽는다 (근거서와 같은 값).
1/5 03-001 노즈 | 2/5 03-007 컵 브래킷·03-010 노즐 블록 | 3/5 03-008·009 IR 클램프·03-004~006 누름판
4/5 03-002 하우징 | 5/5 03-003 상판·03-011 어댑터판"""
import math
import numpy as np
import cadquery as cq
import shapely.geometry as sg

from common import T, load, plist, DATE, WORK, STATUS, TEAM, HERE
from draw_lib import Sheet, View
import ks_spec as K

OUT = HERE / 'out'
OUT.mkdir(exist_ok=True)
P = T.P
parts, QTY, ITEM = load()
TB = dict(work=WORK, dwg_no='D-04', date=DATE, rev='R03', status=STATUS, team=TEAM)
S = K.S
CL = K.CLEAR_2


def solid(no, tag=None):
    for p in parts:
        if p['no'] == no and (tag is None or p['name'].endswith(tag)):
            return p['solid']
    raise KeyError(no)


def head(sh, p, no, label=None):
    base, others = S[no]['rough']
    return sh.part_head(p, ITEM[no], base, others, label)


def notes(sh, p, extra=(), letters=('w', 'x', 'y'), peek_only=False):
    lines = list(K.NOTES_COMMON)
    if peek_only:   # PEEK part: no anodising line
        lines = [l for l in lines if not l.startswith(('4.', '   나사부'))]
        lines = [l.replace('5. ※', '4. ※').replace('6. 표면', '5. 표면') for l in lines]
    return sh.notes_ks(p, lines, letters, rough_vals=K.ROUGH, extra=extra)


def hole_table(sh, x, y, rows, cols=(9, 44, 8, 36, 36), h=2.3):
    """rows: [tag, hole, qty, position, (kind, value, datums, dia) | text]"""
    hdr = ['기호', '구멍', '수량', '위치 (X, Y) TED', '위치도']
    plain = [r[:4] + ['' if isinstance(r[4], tuple) else r[4]] for r in rows]
    yb = sh.table(x, y, list(cols), hdr, plain, rh=7.0, hh=6.0, h=h, align=['C', 'L', 'C', 'L', 'L'])
    xs = x + sum(cols[:4]) + 1.0
    yy = y - 6.0
    for r in rows:
        if isinstance(r[4], tuple):
            kind, val, dts, dia = r[4]
            sh.fcf((xs, yy - 7.0 + 0.6), kind, val, dts, h=2.3, diameter=dia)
        yy -= 7.0
    return yb


def tag(sh, v, uv, s, dx=3.0, dy=3.0):
    p = v.P(*uv)
    sh.text(s, (p[0] + dx, p[1] + dy), 2.5, 'MIDDLE_CENTER')


def thread_top(sh, v, c, d_major):
    """Tapped hole end view: thin 3/4 circle at the major diameter (KS)."""
    sh.msp.add_arc(v.P(*c), d_major / 2 * v.scale, 0, 270, dxfattribs={'layer': 'THREAD'})


def thread_sec(sh, v, x, z_top, depth, d_major, down=True):
    """Tapped hole in a section, axis vertical: thin major-diameter lines + thick thread end line."""
    r = d_major / 2
    sg_ = -1 if down else 1
    for s_ in (-1, 1):
        sh.line(v.P(x + s_ * r, z_top), v.P(x + s_ * r, z_top + sg_ * depth), 'THREAD')
    sh.line(v.P(x - r, z_top + sg_ * depth), v.P(x + r, z_top + sg_ * depth), 'OUTLINE')


def datum_on_line(sh, y, x_feat, x_end, letter, below=True, fcf=None):
    """Extension line from a horizontal face at paper y, datum triangle on it, optional form frame above."""
    sh.line((x_feat, y), (x_end, y), 'DIM')
    xm = x_end + (3.0 if x_end > x_feat else -3.0)
    sh.datum(letter, (xm, y), (xm, y + (-11.0 if below else 11.0)))
    if fcf:
        kind, val, dts = fcf
        fx = xm - 20.0 if x_end < x_feat else xm + 2.0
        fr = sh.fcf((fx, y + 6.5), kind, val, dts)
        xa = (fr[0] + fr[2]) / 2 if x_end < x_feat else fr[0] + 3.0
        xa = xm + (5.5 if x_end < x_feat else -5.5)
        sh.line((xa, fr[1]), (xa, y + 0.2), 'DIM')
        sh.arrow((xa, y), (xa, fr[1]))


# ============================================================================ 1/5 nose
def sheet1():
    sh = Sheet()
    sh.frame()
    sh.title_block(dict(TB, title='03-001 노즈 부품도', scale='1:1', sheet='1/5'))
    s = S['03-001']
    nose = solid('03-001')
    X0 = 126
    vt = View(sh, 'top', 1.0, (X0, 226))
    vf = View(sh, 'front', 1.0, (X0, 120), ref=(0, 16))
    vb = View(sh, 'bottom', 1.0, (X0, 60))
    vr = View(sh, 'right', 1.0, (238, 120), ref=(0, 16))
    vt.outline([nose])
    vb.outline([nose])
    vr.outline([nose], hidden=False)
    vf.section([], (0, 0, 0), [nose], hatch_specs={0: dict(angle=45, spacing=2.4)})
    # centre lines
    vt.axis((-80, 0), (80, 0), ext=0)
    vt.axis((0, -26), (0, 26), ext=0)
    for x in (-60, 60):
        for y in (-18, 18):
            vt.cmark((x, y), CL['M4'] / 2)
    for x in (6, 18):
        vt.cmark((x, -18), 1.7)
    vt.cmark((12, 0), K.IR_BORE_NOSE / 2, ext=2.5)
    for x in (-40, 40):
        vt.cmark((x, 0), 3.0, both=False)
        vt.axis((x, -5), (x, 5), ext=0)
    vb.axis((-80, 0), (80, 0), ext=0)
    vb.axis((0, -26), (0, 26), ext=0)
    for x in (-40, 40):
        vb.axis((x, -9), (x, 9), ext=0)
    for x in (-52, -28, 28, 52):
        vb.axis((x, -4.5), (x, 4.5), ext=0)
    vb.axis((12, -12), (12, 12), ext=0)
    for x in (-52, -40, -28, 12, 28, 40, 52):
        vf.axis((x, 13), (x, 75), ext=0)
    vf.axis((0, 13), (0, 75), ext=0)
    vr.axis((0, 13), (0, 75), ext=0)
    sh.cutline(vt.P(-74, 0), vt.P(74, 0), 'A', (0, 1), ext=7.0)
    sh.view_label('단면 A-A', (X0, 180))
    # dimensions (TED = boxed)
    vt.dim((-74, 22), (74, 22), at=262)
    vt.dim((-60, 18), (60, 18), at=255, basic=True)
    vt.dim((0, 18), (12, 0), at=248.5, basic=True)
    vt.dim((-60, -18), (-60, 18), at=vt.P(-80, 0)[0] - 5, orient='v', basic=True)
    vt.dim((0, -18), (6, -18), at=vt.P(0, -22)[1] - 6, basic=True)
    vt.dim((0, -18), (18, -18), at=vt.P(0, -22)[1] - 12.5, basic=True)
    vt.dim((24, 0), (18, -18), at=vt.P(28, 0)[0], orient='v', basic=True)
    vb.dim((-70, -12), (70, -12), at=vb.P(0, -22)[1] - 16)
    vb.dim((-40, -12), (40, -12), at=vb.P(0, -22)[1] - 8, basic=True)
    vb.dim((28, 12), (52, 12), at=vb.P(0, 22)[1] + 7, basic=True)
    vr.dim((-22, 72), (22, 72), at=vr.P(0, 72)[1] + 8)
    vr.dim((-12, 16), (12, 16), at=vr.P(0, 16)[1] - 8)
    vr.dim((22, 16), (22, 64), at=vr.P(22, 0)[0] + 8, orient='v')
    vr.dim((22, 64), (22, 72), at=vr.P(22, 0)[0] + 8, orient='v')
    vr.dim((22, 16), (22, 72), at=vr.P(22, 0)[0] + 16, orient='v')
    # hole tags
    for x in (-60, 60):
        for y in (-18, 18):
            tag(sh, vt, (x, y), 'H1', 4.5, 3.5)
    for x in (6, 18):
        tag(sh, vt, (x, -18), 'H2', 0.0, -4.5)
    tag(sh, vt, (12, 0), 'H3', 9.5, 9.0)
    for x in (-40, 40):
        tag(sh, vt, (x, 0), 'H4', 4.5, 4.5)
        tag(sh, vb, (x, 0), 'H5', 0.0, 8.7)
    for x in (-52, -28, 28, 52):
        tag(sh, vb, (x, 0), 'H6', 0.0, -6.0)
    # datum A = flange underside (front section, left), flatness; B = H1 pattern
    yA = vf.P(0, 64)[1]
    x_l = vf.P(-74, 64)[0]
    sh.line((x_l - 1.0, yA), (x_l - 19, yA), 'DIM')
    sh.datum('A', (x_l - 15.0, yA), (x_l - 15.0, yA - 11.0))
    fr = sh.fcf((x_l - 22.0, yA + 7.0), 'flat', s['flat_A'])
    xa = fr[2] - 3.0
    sh.line((xa, fr[1]), (xa, yA + 0.2), 'DIM')
    sh.arrow((xa, yA), (xa, fr[1]))
    sh.rough_leader(vf.P(72.5, 64), (vf.P(72.5, 0)[0] + 5.0, yA - 10.0), 'x')
    sh.callout(vt.P(-60 - 2.25 * 0.7071, 18 + 2.25 * 0.7071), (25, 276), [f'4-Ø{CL["M4"]} 관통 (H1)'],
               [('pos', s['pos_H1'], ('A',), True)], side=1, datum='B')
    # body bottom: parallel to A, roughness x
    yb = vf.P(0, 16)[1]
    sh.callout(vf.P(-58, 16), (vf.P(-58, 0)[0] - 4, yb - 10), [], [('par', s['par_bot'], ('A',), False)], side=-1)
    sh.rough_leader(vf.P(-20, 16), (vf.P(-20, 0)[0] + 4, yb - 8), 'x')
    # hole table
    rows = [
        ['H1', f'4-Ø{CL["M4"]} 관통', 4, '(±60, ±18)', ('pos', s['pos_H1'], ('A',), True)],
        ['H2', f'2-Ø{CL["M3"]} 관통', 2, '(6, -18), (18, -18)', ('pos', s['pos_H2'], ('A', 'B'), True)],
        ['H3', f'Ø{K.IR_BORE_NOSE:g} 관통', 1, '(12, 0)', ('pos', s['pos_H3'], ('A', 'B'), True)],
        ['H4', 'Ø6, H5까지', 2, '(±40, 0)', '일반 공차'],
        ['H5', 'Ø12.4 ↧14 (아랫면)', 2, '(±40, 0)', ('pos', s['pos_H5'], ('A', 'B'), True)],
        ['H6', 'Ø4.5 ↧8 (아랫면) ※', 4, '(±28, 0), (±52, 0)', ('pos', s['pos_H6'], ('A', 'B'), True)],
    ]
    sh.text('구멍 표 (원점: H1 패턴 중심 = 데이텀 B)', (283, 171), 2.6)
    hole_table(sh, 283, 168, rows, cols=(9, 38, 8, 34, 36))
    head(sh, (283, 276), '03-001', '노즈')
    notes(sh, (283, 266), peek_only=True, letters=('w', 'x'),
          extra=['데이텀 A: 플랜지 아랫면 (하우징 바닥에 안착)', '데이텀 B: H1 체결 구멍 패턴',
                 'PEEK: 절연 후보, 절연·내열·크리프 미검증'])
    sh.parts_list(plist(['03-001'], QTY, ITEM, {'03-001': '절연 후보'}))
    return sh


# ============================================================================ 2/5 cup bracket + nozzle block
def detail_frame(sh, v, c, r, label, lab_dy=5.0):
    pc = v.P(*c)
    sh.circle(pc, r * v.scale, 'BREAK')
    sh.view_label(label, (pc[0], pc[1] + r * v.scale + lab_dy))


def sheet2():
    sh = Sheet()
    sh.frame()
    sh.title_block(dict(TB, title='03-007 컵 브래킷 · 03-010 노즐 블록', scale='2:1, 5:1', sheet='2/5'))
    # ---------------- 03-007 cup bracket (R instance, centre X=40), 2:1
    s7 = S['03-007']
    cb, cbd = K.CBORE['M3']
    br = solid('03-007', 'R')
    vt = View(sh, 'top', 2.0, (110, 222), ref=(40, 0))
    vf = View(sh, 'front', 2.0, (110, 166), ref=(40, 13))
    vt.outline([br], hidden=True)
    vf.section([], (0, 0, 0), [br], hatch_specs={0: dict(angle=45, spacing=2.0)})
    vt.axis((16, 0), (64, 0), ext=0)
    for x in (28, 40, 52):
        vt.axis((x, -13), (x, 13), ext=0)
        vf.axis((x, 8), (x, 18), ext=0)
    sh.cutline(vt.P(20, 0), vt.P(60, 0), 'A', (0, 1), ext=6.0)
    sh.view_label('단면 A-A', (110, 184))
    vt.dim((20, 10), (60, 10), at=vt.P(0, 10)[1] + 14)
    vt.dim((28, 0), (52, 0), at=vt.P(0, 10)[1] + 7, basic=True)
    vt.dim((20, -10), (20, 10), at=vt.P(20, 0)[0] - 8, orient='v')
    vf.dim((60, 10), (60, 16), at=vf.P(60, 0)[0] + 8, orient='v')
    vf.dim((52 + cb / 2, 10), (52 + cb / 2, 10 + cbd), at=vf.P(60, 0)[0] + 16, orient='v')
    sh.callout(vt.P(28 - 1.7 * 0.7071, -1.7 * 0.7071), (28, 200), [f'2-Ø{CL["M3"]} 관통', f'아래 ⌴Ø{cb} ↧{cbd}'],
               [('pos', s7['pos_B'], ('A',), True)], side=1, datum='B')
    sh.callout(vt.P(40 + 2.75 * 0.7071, 2.75 * 0.7071), (150, 256), ['Ø5.5 관통 (니플 M5 ※)'],
               [('pos', s7['pos_nip'], ('A', 'B'), True)], side=1)
    yA = vf.P(0, 16)[1]
    x0 = vf.P(20, 0)[0]
    sh.line((x0 - 1, yA), (x0 - 16, yA), 'DIM')
    sh.datum('A', (x0 - 12, yA), (x0 - 12, yA + 11))
    sh.rough(vf.P(46, 16), 'x')
    yb = vf.P(0, 10)[1]
    sh.callout(vf.P(56, 10), (vf.P(60, 0)[0] + 4, yb - 9), [], [('par', s7['par_bot'], ('A',), False)], side=1)
    sh.rough_leader(vf.P(24, 10), (vf.P(24, 0)[0] - 14, yb - 8), 'x')
    head(sh, (28, 276), '03-007', '컵 브래킷 (2개, L/R 같음)')

    # ---------------- 03-010 nozzle block (R instance, centre (55, 31)), 2:1
    s10 = S['03-010']
    o = K.ORING_FACE
    ro, ri = o['D_int'] / 2, o['D_int'] / 2 - o['G']
    nz = solid('03-010', 'R')
    cx, cy = 55.0, 31.0
    vt2 = View(sh, 'top', 2.0, (296, 222), ref=(cx, cy))
    vf2 = View(sh, 'front', 2.0, (296, 160), ref=(cx, 51))
    vt2.outline([nz], hidden=False)
    vf2.section([], (0, cy, 0), [nz], hatch_specs={0: dict(angle=135, spacing=2.0)})
    for x in (cx - 9, cx + 9):
        thread_top(sh, vt2, (x, cy), 3.0)
        vt2.cmark((x, cy), 1.5, ext=2.0)
        thread_sec(sh, vf2, x, 58, 6, 3.0)
        vf2.axis((x, 48), (x, 60), ext=0)
    vt2.cmark((cx, cy), ro, ext=2.5)
    vf2.axis((cx, 42), (cx, 61), ext=0)
    sh.cutline(vt2.P(cx - 13, cy), vt2.P(cx + 13, cy), 'B', (0, 1), ext=10.0)
    sh.view_label('단면 B-B', (296, 194))
    vt2.dim((cx - 13, cy + 8), (cx + 13, cy + 8), at=vt2.P(0, cy + 8)[1] + 14)
    vt2.dim((cx - 9, cy), (cx + 9, cy), at=vt2.P(0, cy + 8)[1] + 7, basic=True)
    vt2.dim((cx + 13, cy - 8), (cx + 13, cy + 8), at=vt2.P(cx + 13, 0)[0] + 18, orient='v')
    vf2.dim((cx + 13, 44), (cx + 13, 58), at=vf2.P(cx + 13, 0)[0] + 8, orient='v')
    vf2.dim((cx - ro, 58), (cx + ro, 58), at=vf2.P(0, 58)[1] + 8, text=f'Ø{o["D_int"]}')
    sh.callout(vt2.P(cx - 9 - 1.25 * 0.7071, cy + 1.25 * 0.7071), (232, 258),
               ['2-M3 ↧6', '기초 Ø2.5 ↧8'], [('pos', s10['pos_B'], ('A',), True)], side=1, datum='B')
    sh.callout(vf2.P(cx - 1.25, 47), (232, 132), ['Ø2.5 관통 (토출구)'], [], side=1)
    yA2 = vf2.P(0, 58)[1]
    xl = vf2.P(cx - 13, 0)[0]
    sh.line((xl - 1, yA2), (xl - 30, yA2), 'DIM')
    sh.datum('A', (xl - 9, yA2), (xl - 9, yA2 + 11))
    fr = sh.fcf((xl - 33, yA2 + 15.5), 'flat', s10['flat_A'])
    sh.line((fr[2] - 3, fr[1]), (fr[2] - 3, yA2 + 0.2), 'DIM')
    sh.arrow((fr[2] - 3, yA2), (fr[2] - 3, fr[1]))
    sh.rough(vf2.P(cx - 11.0, 58), 'y')
    # detail C: O-ring groove (KS P6 face groove), 5:1
    cC = (cx + (ri + ro) / 2, 58 - o['H'] / 2)
    sh.circle(vf2.P(*cC), 3.6 * 2.0, 'DIM')
    sh.text('C', (vf2.P(*cC)[0] + 9.0, vf2.P(*cC)[1] + 6.0), 3.5, 'MIDDLE_CENTER')
    vC = View(sh, 'front', 5.0, (370, 150), ref=cC, clip=sg.Point(*cC).buffer(3.6, 128))
    vC.section([], (0, cy, 0), [nz], hatch_specs={0: dict(angle=135, spacing=2.0)})
    detail_frame(sh, vC, cC, 3.6, '상세 C (5:1)', lab_dy=12.0)
    vC.dim((cx + ri, 58), (cx + ro, 58), at=vC.P(0, 58)[1] + 6, tol=o['G_tol'])
    vC.dim((cx + ro - 0.3, 58 - o['H']), (cx + ro + 0.4, 58), at=vC.P(cx + ro + 4.4, 0)[0], orient='v',
           text=f'{o["H"]}±{o["H_tol"]}')
    sh.leader(vC.P(cx + ro - 0.1, 58 - o['H'] + 0.1), (382, 124), f'R{o["R_max"]} 이하', end='arrow', side=1)
    sh.rough(vC.P(cx + ri + 0.6, 58 - o['H']), 'y')
    sh.lines_of_text([f'O링 {o["name"]} 평면 홈 (내압용)', f'규격집 36항: D Ø{o["D_int"]}, G {o["G"]}, H {o["H"]}',
                      f'O링 굵기 {o["cs"]}±{o["cs_tol"]} (35항)'], (343, 112), h=2.3, gap=1.6)
    head(sh, (232, 276), '03-010', '노즐 블록 (2개, L/R 같음)')

    notes(sh, (28, 120), letters=('w', 'x', 'y'),
          extra=['데이텀 - 03-007: A 윗면(노즈 아랫면에 안착), B 2-Ø3.4', '           03-010: A 윗면(밀봉면), B 2-M3'])
    sh.parts_list(plist(['03-007', '03-010'], QTY, ITEM, {'03-007': 'L/R 같음', '03-010': 'L/R 같음, O링 P6'}))
    return sh


# ============================================================================ 3/5 IR clamp pair + retainers
def heads_multi(sh, p, nos, label):
    x, y = p
    for no in nos:
        sh.circle((x + 4.2, y + 3.2), 4.2, 'BALLOON')
        sh.text(str(ITEM[no]), (x + 4.2, y + 3.2), 3.5, 'MIDDLE_CENTER')
        x += 10.0
    base, others = S[nos[0]]['rough']
    xe = sh.rough_group((x + 2.0, y - 0.5), base, others)
    sh.text(label, (xe + 2.0, y), 2.5, 'BOTTOM_LEFT')


def sheet3():
    sh = Sheet()
    sh.frame()
    sh.title_block(dict(TB, title='03-008·009 IR 클램프 · 03-004~006 누름판', scale='2:1, 1:1', sheet='3/5'))
    s8 = S['03-008']
    rb = K.IR_FIT['d'] / 2
    rear, front = solid('03-008'), solid('03-009')
    c = (12.0, 0.0)
    vt = View(sh, 'top', 2.0, (112, 216), ref=(12, -4.5))
    vf = View(sh, 'front', 2.0, (112, 150), ref=(12, 76))
    vs = View(sh, 'right', 2.0, (222, 150), ref=(-4.5, 76))
    vt.outline([rear, front], hidden=True)
    vf.outline([rear, front], hidden=False)
    vs.section([], (28, 0, 0), [rear, front], hatch_specs={0: dict(angle=45, spacing=1.6), 1: dict(angle=135, spacing=1.6)})
    for xs in (-4, 28):
        vt.axis((xs, -25), (xs, 16), ext=0)
    vt.cmark(c, rb, ext=3.0)
    for xs in (6, 18):
        vt.cmark((xs, -18), 1.7)
    vf.axis((-14, 76), (38, 76), ext=0)
    vf.axis((12, 69), (12, 83), ext=0)
    vs.axis((-25, 76), (16, 76), ext=0)
    for s_ in (-1, 1):
        sh.line(vs.P(0.25, 76 + s_ * 1.5), vs.P(8.25, 76 + s_ * 1.5), 'THREAD')
    sh.line(vs.P(8.25, 74.5), vs.P(8.25, 77.5), 'OUTLINE')
    sh.cutline(vt.P(28, -22), vt.P(28, 13), 'C', (-1, 0), ext=6.0)
    sh.view_label('단면 C-C', (222, 166))
    vt.dim((-10, 13), (34, 13), at=vt.P(0, 13)[1] + 16)
    vt.dim((-4, 13), (28, 13), at=vt.P(0, 13)[1] + 9, basic=True)
    vt.dim((34, -22), (34, 13), at=vt.P(34, 0)[0] + 16, orient='v')
    vt.dim((34, -22), (34, -0.25), at=vt.P(34, 0)[0] + 8, orient='v')
    vt.dim((34, 0.25), (34, 13), at=vt.P(34, 0)[0] + 8, orient='v')
    vt.dim((6, -22), (18, -22), at=vt.P(0, -22)[1] - 8, basic=True)
    vt.dim((-10, -18), (-10, 0), at=vt.P(-10, 0)[0] - 8, orient='v', basic=True)
    vf.dim((34, 72), (34, 80), at=vf.P(34, 0)[0] + 8, orient='v')
    vf.dim((-10, 72), (-10, 76), at=vf.P(-10, 0)[0] - 8, orient='v')
    sh.callout(vt.P(12 - rb * 0.7071, rb * 0.7071), (60, 264), [f'Ø{K.IR_FIT["d"]:g} {K.IR_FIT["hole"]} (짝가공)'],
               [('perp', s8['perp'], ('A',), True), ('pos', s8['pos_bore'], ('A', 'B'), True)], side=-1)
    sh.callout(vt.P(6 - 1.7 * 0.7071, -18 - 1.7 * 0.7071), (26, 190), [f'2-Ø{CL["M3"]} 관통 (03-008)'],
               [('pos', s8['pos_B'], ('A',), True)], side=1, datum='B')
    sh.callout(vs.P(-12, 76), (172, 126), [f'2-Ø{CL["M3"]} 관통 (03-008)', '2-M3 ↧8, 기초 Ø2.5 ↧10 (03-009)'], [], side=1)
    sh.leader(vt.P(-9.5, 0.0), (52, 228), '조임 틈 0.5', end='arrow', side=-1)
    yA = vf.P(0, 72)[1]
    xA = vf.P(16, 72)[0]
    sh.datum('A', (xA, yA), (xA, yA - 11))
    sh.rough(vt.P(12 + rb * 0.94, rb * 0.34), 'y', rot=-20)
    sh.rough_leader(vf.P(30, 72), (vf.P(30, 0)[0] + 6, yA - 9), 'x')
    sh.rough_leader(vs.P(-0.25, 78.5), (vs.P(-0.25, 0)[0] + 4, vs.P(0, 80)[1] + 7), 'x')
    heads_multi(sh, (26, 276), ['03-008', '03-009'], 'IR 클램프 뒤·앞 (짝가공, 짝 단위 교체)')
    sh.lines_of_text([
        '03-008·03-009 가공 순서 (가정)',
        '1) 한 블록에서 외형·구멍·M3 탭 가공',
        '2) Y=0에서 폭 0.5로 분할',
        f'3) 틈 0.5 끼운 채 M3×30으로 조립 후 Ø{K.IR_FIT["d"]:g} {K.IR_FIT["hole"]} 보링',
        '4) 짝 표시 후 분리. 짝 단위로만 교체',
    ], (262, 276), h=2.4, gap=1.65)

    # ---------------- retainers 1:1
    s4 = S['03-004']
    hd = CL['M4']
    r4, r5, r6 = solid('03-004'), solid('03-005'), solid('03-006')
    v4 = View(sh, 'top', 1.0, (110, 100), ref=(0, 18))
    v4f = View(sh, 'front', 1.0, (110, 84), ref=(0, 74))
    v5 = View(sh, 'top', 1.0, (110, 56), ref=(0, -18))
    v6 = View(sh, 'top', 1.0, (110, 56), ref=(0, -18))
    v4.outline([r4])
    v4f.outline([r4])
    v5.outline([r5])
    v6.outline([r6])
    for v_, xs, yc in ((v4, (-60, 60), 18), (v5, (-60,), -18), (v6, (60,), -18)):
        for x in xs:
            v_.cmark((x, yc), hd / 2)
    for x in (-60, 60):
        v4f.axis((x, 70), (x, 78), ext=0)
    sh.text('03-004 누름판 앞', (40, 113), 2.5)
    sh.text('03-005 누름판 뒤 좌', (40, 69), 2.5)
    sh.text('03-006 누름판 뒤 우', (146, 69), 2.5)
    v4.dim((-70, 22), (70, 22), at=v4.P(0, 22)[1] + 4)
    v4.dim((-60, 14), (60, 14), at=v4.P(0, 14)[1] - 6, basic=True)
    v4.dim((70, 14), (70, 22), at=v4.P(70, 0)[0] + 7, orient='v')
    v4f.dim((70, 72), (70, 76), at=v4f.P(70, 0)[0] + 7, orient='v')
    v5.dim((-70, -22), (-12, -22), at=v5.P(0, -22)[1] - 6)
    v5.dim((-70, -14), (-60, -14), at=v5.P(0, -14)[1] + 4)
    v6.dim((36, -22), (70, -22), at=v6.P(0, -22)[1] - 6)
    v5.dim((-12, -22), (-12, -14), at=v5.P(-12, 0)[0] + 7, orient='v')
    v6.dim((60, -14), (70, -14), at=v6.P(0, -14)[1] + 4)
    v6.dim((70, -22), (70, -14), at=v6.P(70, 0)[0] + 7, orient='v')
    sh.callout(v4.P(60 + hd / 2 * 0.7071, 18 + hd / 2 * 0.7071), (196, 112), [f'Ø{hd} 관통 (M4, 3종 모두)'],
               [('pos', s4['pos'], ('A',), True)], side=1)
    yA4 = v4f.P(0, 72)[1]
    xl4 = v4f.P(-70, 0)[0]
    sh.line((xl4 - 1, yA4), (xl4 - 12, yA4), 'DIM')
    sh.datum('A', (xl4 - 8, yA4), (xl4 - 8, yA4 - 10))
    sh.rough_leader(v4f.P(-40, 72), (v4f.P(-40, 0)[0] - 8, yA4 - 8), 'x')
    heads_multi(sh, (196, 92), ['03-004', '03-005', '03-006'], '누름판 (두께 4)')

    notes(sh, (262, 240), letters=('w', 'x', 'y'),
          extra=['데이텀 - 클램프: A 아랫면(노즈 플랜지 윗면에 안착), B 2-Ø3.4',
                 '           누름판: A 아랫면(노즈 플랜지를 누르는 면)',
                 f'※ Ø18 {K.IR_FIT["hole"]}: 센서 외경 h8 가정, 선정 후 확인'])
    sh.parts_list(plist(['03-004', '03-005', '03-006', '03-008', '03-009'], QTY, ITEM,
                        {'03-008': '03-009와 짝가공', '03-009': '03-008과 짝가공'}))
    return sh


# ============================================================================ 4/5 housing
def thread_mark_side(sh, v, x, z_top, depth, d_major, down=True):
    r = d_major / 2
    sgn = -1 if down else 1
    for s_ in (-1, 1):
        sh.line(v.P(x + s_ * r, z_top), v.P(x + s_ * r, z_top + sgn * depth), 'THREAD')
    sh.line(v.P(x - r, z_top + sgn * depth), v.P(x + r, z_top + sgn * depth), 'OUTLINE')


def sheet4():
    sh = Sheet()
    sh.frame()
    sh.title_block(dict(TB, title='03-002 하우징 몸체 부품도', scale='1:1', sheet='4/5'))
    s2 = S['03-002']
    pb, pt = K.PORT_BOSS, K.PORT
    hb = solid('03-002')
    vt = View(sh, 'top', 1.0, (124, 196))
    vf = View(sh, 'front', 1.0, (124, 40), ref=(0, 58))
    vs = View(sh, 'right', 1.0, (296, 234), ref=(0, 91))
    vt.outline([hb])
    vf.outline([hb])
    vs.section([], (70, 0, 0), [hb], hatch_specs={0: dict(angle=45, spacing=2.0)})
    vt.axis((-86, 0), (86, 0), ext=0)
    vt.axis((0, -76), (0, 76), ext=0)
    bosses = [(70, 60), (-70, 60), (70, -60), (-70, -60), (70, -30), (-70, 30)]
    for (x, y) in bosses:
        vt.cmark((x, y), 1.65, ext=2.0)
        thread_top(sh, vt, (x, y), 4.0)
    for x in (-60, 60):
        for y in (-18, 18):
            vt.cmark((x, y), 1.65, ext=2.0)
            thread_top(sh, vt, (x, y), 4.0)
    for x in (6, 18):
        vt.cmark((x, -18), 1.25, ext=1.5)
        thread_top(sh, vt, (x, -18), 3.0)
    for (x, y) in P['nozzle_xy'].values():
        vt.cmark((x, y), pb['d'] / 2, ext=2.0)
        thread_top(sh, vt, (x, y), 5.0)
        for xx in (x - 9, x + 9):
            vt.cmark((xx, y), 1.7, ext=1.5)
    for x in (-35, 5):
        vf.cmark((x, 104), 1.7, ext=2.0)
    for y in (-60, -30, 60):
        vs.axis((y, 106), (y, 128), ext=0)
        thread_mark_side(sh, vs, y, 124, 10, 4.0)
    for y in (-31, 31):
        vs.axis((y, 55), (y, 72), ext=0)
    sh.cutline(vt.P(70, -70), vt.P(70, 70), 'B', (-1, 0), ext=6.0)
    sh.view_label('단면 B-B', (296, 274))
    # dimensions
    vt.dim((-80, 70), (80, 70), at=vt.P(0, 70)[1] + 12)
    vt.dim((-70, 60), (70, 60), at=vt.P(0, 70)[1] + 6, basic=True)
    vt.dim((-80, -70), (-80, 70), at=vt.P(-80, 0)[0] - 12, orient='v')
    vt.dim((-70, -60), (-70, 60), at=vt.P(-80, 0)[0] - 6, orient='v', basic=True)
    vt.dim((-71, -13.3), (71, -13.3), at=vt.P(0, -6)[1])
    vt.dim((78, -13.3), (78, 13.3), at=vt.P(80, 0)[0] + 7, orient='v')
    vt.dim((76, -40), (80, -40), at=vt.P(0, -40)[1], text='4')
    vf.dim((80, 58), (80, 124), at=vf.P(80, 0)[0] + 8, orient='v')
    vf.dim((-35, 124), (5, 124), at=vf.P(0, 124)[1] + 6, basic=True)
    vf.dim((0, 124), (5, 124), at=vf.P(0, 124)[1] + 12, basic=True)
    vf.dim((60, 104), (60, 124), at=vf.P(60, 0)[0], orient='v', basic=True)
    vs.dim((-36, 90), (-36, 124), at=vs.P(-36, 0)[0] - 4, orient='v')
    vs.dim((-13.3, 58), (-13.3, 64), at=vs.P(-4, 0)[0], orient='v')
    vs.dim((31 + pb['d'] / 2, 64), (31 + pb['d'] / 2, 64 + pb['h']), at=vs.P(31 + pb['d'] / 2, 0)[0] + 5, orient='v')
    vs.dim((31 - pb['d'] / 2, 64 + pb['h']), (31 + pb['d'] / 2, 64 + pb['h']), at=vs.P(0, 64 + pb['h'])[1] + 5,
           text=f'Ø{pb["d"]:g}')
    # datums A (floor top) and C (top face) on section B-B, roughness
    yA = vs.P(0, 64)[1]
    sh.datum('A', vs.P(-50, 64), (vs.P(-50, 0)[0], yA + 13))
    sh.fcf((vs.P(-50, 0)[0] + 5, yA + 10), 'flat', s2['flat_A'])
    yC = vs.P(0, 124)[1]
    sh.datum('C', vs.P(-45, 124), (vs.P(-45, 0)[0], yC + 11))
    sh.fcf((vs.P(-45, 0)[0] + 5, yC + 8), 'par', s2['par_C'], ('A',))
    sh.rough(vs.P(-20, 124), 'x')
    sh.rough_leader(vs.P(52, 64), (vs.P(42, 0)[0], vs.P(0, 64)[1] + 14), 'x')
    # O-ring sealing zones on the floor underside (front view bottom edge), 2 places
    for xz in (-55, 55):
        sh.zone_line(vf.P(xz + 7, 58), vf.P(xz - 7, 58), off=1.3)
    sh.rough_leader(vf.P(-55, 57.0), (vf.P(-55, 0)[0] - 18, vf.P(0, 58)[1] - 9), 'y')
    sh.text('O링 밀봉면 Ø14 범위, 2곳', (vf.P(-55, 0)[0] - 18, vf.P(0, 58)[1] - 14), 2.3)
    # hole tags
    for x in (-60, 60):
        for y in (-18, 18):
            tag(sh, vt, (x, y), 'K1', 5.0, 4.0)
    tag(sh, vt, (12, -18), 'K2', 0.0, -5.5)
    for (x, y) in P['nozzle_xy'].values():
        tag(sh, vt, (x, y), 'K3', 0.0, 8.5)
        tag(sh, vt, (x + 9, y), 'K5', 4.0, -3.5)
    for (x, y) in bosses:
        tag(sh, vt, (x, y), 'K6', -6.0 if x > 0 else 6.0, -5.0)
    for x in (-35, 5):
        tag(sh, vf, (x, 104), 'K7', 0.0, -5.0)
    rows = [
        ['K1', '4-M4 관통 (기초 Ø3.3)', 4, '(±60, ±18)', ('pos', s2['pos_K1'], ('A',), True)],
        ['K2', '2-M3 관통 (기초 Ø2.5)', 2, '(6, -18), (18, -18)', ('pos', s2['pos_K2'], ('A', 'B'), True)],
        ['K3', f'2-M5 ↧{pt["depth"]:g}, 기초 Ø4.2 ↧{pt["drill_depth"]:g} ※', 2, '(-55, -31), (55, 31)',
         ('pos', s2['pos_K3'], ('A', 'B'), True)],
        ['K4', 'Ø2.5, K3 바닥 → 아랫면', 2, 'K3과 동축', '일반 공차'],
        ['K5', f'4-Ø{CL["M3"]} 관통', 4, 'K3에서 X ±9', ('pos', s2['pos_K5'], ('A', 'B'), True)],
        ['K6', '6-M4 ↧10, 기초 Ø3.3 ↧14', 6, '(±70, ±60), (70, -30), (-70, 30)', ('pos', s2['pos_K6'], ('C', 'B'), True)],
        ['K7', f'4-Ø{CL["M3"]} 관통 (옆벽 Z104)', 4, '앞 (-35, 5), 뒤 (-5, 35)', ('pos', s2['pos_K7'], ('A',), True)],
    ]
    sh.text('구멍 표 (원점: K1 패턴 중심 = 데이텀 B)', (218, 196), 2.6)
    hole_table(sh, 218, 193, rows, cols=(9, 52, 8, 50, 32))
    head(sh, (218, 129), '03-002', '하우징 몸체')
    notes(sh, (300, 130), letters=('w', 'x', 'y'),
          extra=['데이텀 A 바닥 윗면, B K1 패턴, C 윗면'])
    sh.parts_list(plist(['03-002'], QTY, ITEM, {'03-002': '포트 보스 2곳'}))
    return sh


# ============================================================================ 5/5 top plate + adapter
def sheet5():
    sh = Sheet()
    sh.frame()
    sh.title_block(dict(TB, title='03-003 상판 · 03-011 로드셀 어댑터판', scale='1:2, 1:1', sheet='5/5'))
    s3, s11 = S['03-003'], S['03-011']
    cbd, cbh = K.CBORE['M5']
    tp = solid('03-003')
    ad = solid('03-011')
    # ---------------- top plate: top view 1:2, section A-A 1:1
    vt = View(sh, 'top', 0.5, (90, 232))
    vf = View(sh, 'front', 1.0, (110, 160), ref=(0, 129))
    vt.outline([tp], hidden=True)
    yS = 21.2132
    vf.section([], (0, yS, 0), [tp], hatch_specs={0: dict(angle=45, spacing=1.6)})
    vt.axis((-86, 0), (86, 0), ext=0)
    vt.axis((0, -76), (0, 76), ext=0)
    vt.pcd((0, 0), 30)
    for a_ in (45, 135):
        ca, sa = math.cos(math.radians(a_)), math.sin(math.radians(a_))
        vt.axis((-36 * ca, -36 * sa), (36 * ca, 36 * sa), ext=0)
    for (x, y) in [(70, 60), (-70, 60), (70, -60), (-70, -60), (70, -30), (-70, 30)]:
        vt.cmark((x, y), 2.25, ext=1.5)
    for (x, y) in P['pass_holes']:
        vt.cmark((x, y), 10.0, ext=1.5)
    sh.cutline(vt.P(-80, yS), vt.P(80, yS), 'A', (0, 1), ext=5.0)
    sh.text('상판 (1:2)', (25, 279), 2.5)
    sh.view_label('단면 A-A (1:1)', (110, 172))
    vt.dim((-80, 70), (80, 70), at=vt.P(0, 70)[1] + 10)
    vt.dim((-70, 60), (70, 60), at=vt.P(0, 70)[1] + 5, basic=True)
    vt.dim((-80, -70), (-80, 70), at=vt.P(-80, 0)[0] - 10, orient='v')
    vt.dim((-70, -60), (-70, 60), at=vt.P(-80, 0)[0] - 5, orient='v', basic=True)
    vt.dim((70, 0), (70, -30), at=vt.P(80, 0)[0] + 5, orient='v', basic=True)
    vt.dim((55, 28), (55, -28), at=vt.P(80, 0)[0] + 11, orient='v')
    vt.dim((0, -70), (55, -70), at=vt.P(0, -70)[1] - 5)
    vf.dim((80, 124), (80, 134), at=vf.P(80, 0)[0] + 6, orient='v')
    for (x, y) in [(70, 60), (-70, 60), (70, -60), (-70, -60), (70, -30), (-70, 30)]:
        tag(sh, vt, (x, y), 'T1', -4.5 if x > 0 else 4.5, -3.0)
    for k in range(4):
        a_ = math.radians(45 + 90 * k)
        tag(sh, vt, (30 * math.cos(a_), 30 * math.sin(a_)), 'T2', 5.0 * math.cos(a_), 5.0 * math.sin(a_))
    for (x, y) in P['pass_holes']:
        tag(sh, vt, (x, y), 'T3', 0.0, 7.5)
    # datum A = underside (right end), flatness; top face // A with y zone (load cell seat)
    yA = vf.P(0, 124)[1]
    xr = vf.P(80, 0)[0]
    sh.line((xr + 12, yA), (xr + 26, yA), 'DIM')
    sh.datum('A', (xr + 22, yA), (xr + 22, yA - 10))
    fr = sh.fcf((xr + 12, yA + 4.5), 'flat', s3['flat_A'])
    sh.line((fr[0] + 3, fr[1]), (fr[0] + 3, yA + 0.2), 'DIM')
    sh.arrow((fr[0] + 3, yA), (fr[0] + 3, fr[1]))
    sh.line((xr + 1, yA), (xr + 11, yA), 'DIM')
    sh.rough_leader(vf.P(-60, 124), (vf.P(-60, 0)[0] + 6, yA - 8), 'x')
    yT = vf.P(0, 134)[1]
    sh.zone_line(vf.P(-42, 134), vf.P(42, 134), off=-1.3)
    sh.rough(vf.P(-30, 134.0), 'y')
    sh.callout(vf.P(36, 134), (vf.P(52, 0)[0], yT + 9), ['로드셀 안착 Ø84 범위 y'],
               [('par', s3['par_top'], ('A',), False)], side=1)
    rows = [
        ['T1', f'6-Ø{CL["M4"]} 관통 (M4)', 6, '(±70, ±60), (70, -30), (-70, 30)', ('pos', s3['pos_T1'], ('A',), True)],
        ['T2', f'4-Ø5.5, 아래 ⌴Ø{cbd} ↧{cbh} ※', 4, 'PCD60, 45°', ('pos', s3['pos_T2'], ('A', 'B'), True)],
        ['T3', 'Ø20 관통 (배관·케이블)', 2, '(55, ±28)', '일반 공차'],
    ]
    sh.text('상판 구멍 표 (데이텀 B = T1 패턴)', (25, 137), 2.6)
    hole_table(sh, 25, 134, rows, cols=(9, 50, 8, 52, 32))
    head(sh, (150, 262), '03-003', '상판 t10')

    # ---------------- adapter plate 1:1
    va = View(sh, 'top', 1.0, (330, 224))
    vaf = View(sh, 'front', 1.0, (330, 146), ref=(0, 164))
    va.outline([ad], hidden=True)
    vaf.section([], (0, 0, 0), [ad], hatch_specs={0: dict(angle=135, spacing=1.6)})
    rot = ad.rotate(cq.Vector(0, 0, 0), cq.Vector(0, 0, 1), -45)
    vab = View(sh, 'front', 1.0, (330, 120), ref=(0, 164))
    vab.section([], (0, 0, 0), [rot], hatch_specs={0: dict(angle=45, spacing=1.6)})
    va.axis((-56, 0), (56, 0), ext=0)
    va.axis((0, -56), (0, 56), ext=0)
    va.pcd((0, 0), 30)
    va.pcd((0, 0), 45)
    for a_ in (45, 135):
        ca, sa = math.cos(math.radians(a_)), math.sin(math.radians(a_))
        va.axis((-36 * ca, -36 * sa), (36 * ca, 36 * sa), ext=0)
    sh.cutline(va.P(-50, 0), va.P(50, 0), 'C', (0, 1), ext=5.0)
    sh.view_label('단면 C-C', (330, 157))
    sh.text('단면 D-D (45° 방향, PCD60 통과)', (330, 129), 2.5, 'BOTTOM_CENTER')
    d45 = (36 * math.cos(math.radians(45)), 36 * math.sin(math.radians(45)))
    sh.cutline(va.P(-d45[0], -d45[1]), va.P(d45[0], d45[1]), 'D', (-0.7071, 0.7071), ext=8.0, thick=4.0)
    va.dia((0, 0), 50, ang=200)
    vaf.dim((50, 159), (50, 169), at=vaf.P(50, 0)[0] + 7, orient='v')
    vab.dim((30, 169), (30, 169 - cbh), at=vab.P(50, 0)[0] + 7, orient='v')
    for k in range(4):
        a_ = math.radians(45 + 90 * k)
        tag(sh, va, (30 * math.cos(a_), 30 * math.sin(a_)), 'P1', 7.0 * math.cos(a_), 7.0 * math.sin(a_))
        a2 = math.radians(90 * k)
        tag(sh, va, (45 * math.cos(a2), 45 * math.sin(a2)), 'P2', 9.0 * math.cos(a2 + 0.5), 9.0 * math.sin(a2 + 0.5))
    yAa = vaf.P(0, 159)[1]
    xla = vaf.P(-50, 0)[0]
    sh.line((xla - 1, yAa), (xla - 12, yAa), 'DIM')
    sh.datum('A', (xla - 8, yAa), (xla - 8, yAa - 10))
    fr2 = sh.fcf((xla - 34, yAa - 9), 'flat', s11['flat_A'])
    sh.line((fr2[2] - 3, fr2[3]), (fr2[2] - 3, yAa - 0.2), 'DIM')
    sh.arrow((fr2[2] - 3, yAa), (fr2[2] - 3, fr2[3]))
    sh.rough_leader(vaf.P(-40, 159), (vaf.P(-40, 0)[0] + 5, yAa - 6), 'y')
    frp = sh.fcf((vaf.P(26, 0)[0], vaf.P(0, 169)[1] + 6), 'par', s11['par_top'], ('A',))
    sh.line((frp[0] + 3, frp[1]), (frp[0] + 3, vaf.P(0, 169)[1] + 0.2), 'DIM')
    sh.arrow((frp[0] + 3, vaf.P(0, 169)[1]), (frp[0] + 3, frp[1]))
    sh.rough(vaf.P(-20, 169), 'x')
    rows2 = [
        ['P1', f'4-Ø5.5, 위 ⌴Ø{cbd} ↧{cbh} ※', 4, 'PCD60, 45°', ('pos', s11['pos_P1'], ('A',), True)],
        ['P2', f'4-Ø5.5, 아래 ⌴Ø{cbd} ↧{cbh} ※', 4, 'PCD90, 0°', ('pos', s11['pos_P2'], ('A', 'B'), True)],
    ]
    sh.text('어댑터판 구멍 표 (데이텀 B = P1 패턴)', (240, 106), 2.6)
    yb2 = hole_table(sh, 240, 103, rows2, cols=(9, 50, 8, 26, 32))
    head(sh, (240, 276), '03-011', '로드셀 어댑터판')
    sh.lines_of_text(['※ PCD60 = 로드셀, PCD90 = 교환기 툴 플레이트 패턴 (가정).',
                      '   선정 후 패턴·중심 맞춤(스피곳/핀)을 제조사 규격으로 바꿈.'], (240, yb2 - 5), h=2.3, gap=1.6)
    notes(sh, (25, 96), letters=('w', 'x', 'y'), extra=[])
    sh.parts_list(plist(['03-003', '03-011'], QTY, ITEM, {'03-003': '로드셀 안착 y', '03-011': '패턴 ※'}))
    return sh

SHEETS = {'1': sheet1, '2': sheet2, '3': sheet3, '4': sheet4, '5': sheet5}

if __name__ == '__main__':
    import sys
    which = sys.argv[1:] or list(SHEETS)
    for k in which:
        sh = SHEETS[k]()
        stem = f'D-04_R03_{k}of5'
        sh.save(OUT / f'{stem}.dxf')
        sh.render(OUT / f'{stem}.pdf', OUT / f'{stem}.png', dpi=150)
    print('ok')
