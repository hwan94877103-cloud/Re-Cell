"""D-03 셀·냉각판·가열 작업대 단면도 (R03): 2 sheets from tool03_r03 + bench_r03 solids.
1/2 단면 A-A (셀 길이 방향), 단면 B-B (셀 두께 방향, 냉각 노즐)
2/2 코일 구역 평면 (구 D-05 통합), 상세 F (층 구성), 필링 자세, 가열 원리·순서 주기"""
import math
import numpy as np
import shapely.geometry as sg

from common import T, load, CUT_NOS, DATE, WORK, STATUS, TEAM, HERE
import bench_r03 as BM
from draw_lib import Sheet, View, project, dedupe
from d02 import HATCH, disp, rect_break, detail_frame

OUT = HERE / 'out'
P = T.P
parts, QTY, ITEM = load()
TB = dict(work=WORK, dwg_no='D-03', date=DATE, rev='R03', status=STATUS, team=TEAM)
tool_cut = [p for p in parts if p['no'] in CUT_NOS]
tool_whole = [p for p in parts if p['no'] not in CUT_NOS and not p['no'].startswith('CM')]


def combo_section(v, p0, bench_items, tool=True, rot=None, rot_bench_names=()):
    """Section through tool + bench. rot(deg) rotates the tool and named bench items (peeling posture)."""
    R = (lambda s: BM.rotate_about_pivot(s, rot)) if rot else (lambda s: s)
    cut, specs, whole = [], {}, []
    if tool:
        for p in tool_cut:
            specs[len(cut)] = dict(angle=HATCH[p['no']][0], spacing=HATCH[p['no']][1])
            cut.append(R(p['solid']))
        whole += [R(disp(p)) for p in tool_whole]
    for b in bench_items:
        s = R(b['solid']) if b['name'] in rot_bench_names else b['solid']
        if b['role'] == 'layer':
            specs[len(cut)] = dict(angle=b['hatch'][0], spacing=b['hatch'][1])
            cut.append(s)
        elif b['role'] == 'thin':
            specs[len(cut)] = dict(solid=True)
            cut.append(s)
        else:
            whole.append(s)
    return v.section([], p0, cut, whole, hatch_specs=specs)


def note(sh, tip, knee, text, side=1, end='dot'):
    sh.leader(tip, knee, text, h=2.3, end=end, side=side)


# ============================================================================ 1/2
def sheet1():
    sh = Sheet()
    sh.frame()
    sh.title_block(dict(TB, title='셀·냉각판·가열 작업대 단면도', scale='1:1', sheet='1/2'))
    bl = BM.bench(rows=(0, 1), cells=range(-2, 3))
    # ---------------- A-A (Y = 0), viewed from -Y
    boxA = (-95.0, -132.0, 95.0, 80.0)
    vA = View(sh, 'front', 1.0, (122, 160), ref=(0, -25), clip=sg.box(*boxA))
    combo_section(vA, (0, 0, 0), bl)
    rect_break(sh, vA, *boxA)
    sh.view_label('단면 A-A (셀 길이 방향)', (122, 271))
    for x in (-40, 40, 12):
        vA.axis((x, -4), (x, 30), ext=0)
    vA.axis((0, -128), (0, -96), ext=0)
    vA.dim((-74, -91), (74, -91), at=vA.P(0, -132)[1] - 9)
    vA.dim((-65, -105), (65, -105), at=vA.P(0, -132)[1] - 17, text='<> (코일)')
    vA.dim((-79, -40), (-74, -40), at=vA.P(0, -40)[1], text='5')
    bal = [(1, vA, (-20, -45), (100, 150)), (2, vA, (85, -45), (100, 120)), (3, vA, (64, 4), (150, 150)),
           (5, vA, (-50, -91.5), (60, 120)), (6, vA, (-50, -94.5), (70, 112)), (7, vA, (-30, -99), (80, 104)),
           (10, vA, (-30, -120), (90, 96)), (11, vA, (0, -112), (128, 120)), (12, vA, (-84, -60), (55, 160)),
           (13, vA, (-55, 40), (60, 215)), (14, vA, (-46, 4), (70, 160)), (15, vA, (12, 60), (150, 215))]
    for n, v_, uv, bp in bal:
        sh.balloon(n, bp, v_.P(*uv))

    # ---------------- B-B (X = 55), viewed from +X
    boxB = (-50.0, -132.0, 50.0, 80.0)
    vB = View(sh, 'right', 1.0, (298, 160), ref=(0, -25), clip=sg.box(*boxB))
    combo_section(vB, (55, 0, 0), bl)
    rect_break(sh, vB, *boxB)
    sh.view_label('단면 B-B (셀 두께 방향, X=55)', (298, 271))
    for y in (-28.5, 0, 28.5):
        vB.axis((y, -96), (y, 4), ext=0)
    vB.axis((31, 40), (31, 60), ext=0)
    # cooling air jet (phantom arrow) from nozzle R onto neighbour cell +1
    sh.line(vB.P(31, 43), vB.P(31, 7), 'PHANTOM')
    sh.arrow(vB.P(31, 6), vB.P(31, 12), L=3.0, W=1.2, layer='PHANTOM')
    vB.dim((-13.25, -60), (13.25, -60), at=vB.P(0, -60)[1])
    vB.dim((0, -30), (28.5, -30), at=vB.P(0, -30)[1] - 10, text='<> 피치')
    vB.dim((-50, -91), (-50, 0), at=vB.P(-50, 0)[0] - 7, orient='v')
    vB.dim((-11, -105), (11, -105), at=vB.P(0, -132)[1] - 9, text='<> (코일)')
    vB.dim((31, 0), (31, 44), at=vB.P(44, 0)[0], orient='v', text='<> 토출 높이')
    for n, uv, bp in [(4, (14.25, -70), (360, 160)), (5, (40, -91.5), (360, 138)), (6, (40, -94.5), (360, 128)),
                      (7, (40, -99), (360, 118)), (8, (-37.5, -103), (238, 76)), (9, (40, -107.5), (360, 108)),
                      (10, (40, -120), (360, 98)), (16, (37, 51), (343, 224))]:
        sh.balloon(n, bp, vB.P(*uv))
    legend = [['1', '대상 셀'], ['2', '이웃 셀'], ['3', '단자·잔여 버스바'], ['4', '압축 패드 2'], ['5', '바닥 접착층 1'],
              ['6', 'Al 냉각판 5'], ['7', '비금속 상판 t4'], ['8', '유도가열 코일'], ['9', '페라이트 t5'],
              ['10', '코일 지지판'], ['11', '온도 센서'], ['12', '블록 경계 부재'], ['13', '03 노즈 (PEEK)'],
              ['14', '흡착컵 30×20 ※'], ['15', 'IR 센서 Ø18 ※'], ['16', '냉각 노즐 블록']]
    sh.text('구성 (모두 가정)', (358, 278), 2.5)
    sh.table(356, 275, [8, 42], ['번', '이름'], legend, rh=5.2, hh=5.5, h=2.2, align=['C', 'L'])
    sh.lines_of_text([
        '주기  1. Z=0 = 셀 윗면. 가상 CTP 블록 (2열 × 12셀) 기준, 실제 제조사 규격 아님.',
        '         2. 팩 하부 보호판은 입고 전 제거. 냉각수는 회수·압축 공기 퍼지 후 가열.',
        '         3. 단면도에서 셀·볼트·호스·센서는 해칭하지 않음. 접착층·패드는 검게 칠함.',
        '         4. 층 두께는 2/2 상세 F, 코일 구역 배치는 2/2 평면 참조.',
    ], (25, 24), h=2.3, gap=1.6)
    return sh


# ============================================================================ 2/2
def sheet2():
    sh = Sheet()
    sh.frame()
    sh.title_block(dict(TB, title='작업대 코일 구역 · 층 구성 · 필링 자세', scale='1:2, 5:1', sheet='2/2'))
    # ---------------- coil zone plan (top view, 1:2), cells as phantom
    full = BM.bench(rows=(0, 1), cells=BM.CELL_J)
    vP = View(sh, 'top', 0.5, (112, 158), ref=(75, -8))
    coils = [b['solid'] for b in full if (b['name'].startswith('코일 ') and '지지판' not in b['name']) or b['name'].startswith('온도 센서')]
    vP.outline(coils)
    cells = [b['solid'] for b in full if b['name'].startswith('셀 ')]
    pv, _ = project(cells, 'top')
    vP.draw_prims(dedupe(pv), 'PHANTOM')
    sh.view_label('코일 구역 평면 (1블록, 1:2)', (112, 262))
    # zone numbers and target / neighbours
    for r in (0, 1):
        for k, j in enumerate(BM.CELL_J):
            x, y = BM.ROW_X[r], j * BM.PITCH
            zn = f'{"AB"[r]}{k + 1}'
            p = vP.P(x - 50, y)
            sh.text(zn, p, 2.0, 'MIDDLE_CENTER')
    tgt = vP.P(0, 0)
    sh.pline([vP.P(-74, -13.25), vP.P(74, -13.25), vP.P(74, 13.25), vP.P(-74, 13.25)], 'OUTLINE', closed=True)
    vP.dim((-65, -171 - 14), (65, -171 - 14), at=vP.P(0, -195)[1] - 6, text='<> 코일', style_over=None)
    vP.dim((150 - 74, 142.5), (150 + 74, 142.5), at=vP.P(0, 160)[1] + 6, text='<> 셀')
    vP.dim((-74 - 21, 0), (-74 - 21, 28.5), at=vP.P(-95, 0)[0] - 6, orient='v', text='<> 피치')
    sh.lines_of_text([
        '굵은 테두리: 가열 구역 (대상 셀 A7). A6·A8: 이웃 셀 (가열 off + 냉각 공기).',
        '◎: 온도 센서 (각 구역 코일 창 안, 냉각판 아랫면 접촉). 가는 2점 쇄선: 셀 (가상선).',
        '구역 = 셀 1개, 2열 × 12 = 24 구역. 코일 130×22 레이스트랙, 창 118×10 (가정).',
    ], (25, 47), h=2.3, gap=1.6)

    # ---------------- detail F: layer stack under one cell, 5:1 (section B-B region)
    bl = BM.bench(rows=(0,), cells=range(-1, 2))
    cF = (8.0, -100.5)
    vF = View(sh, 'right', 5.0, (258, 196), ref=cF, clip=sg.box(2.0, -112.0, 14.0, -89.0))
    combo_section(vF, (48, 0, 0), bl, tool=False)
    rect_break(sh, vF, 2.0, -112.0, 14.0, -89.0, amp=1.2, wl=8.0)
    sh.view_label('상세 F (5:1, X=48 단면)', (258, 262))
    xr = vF.P(14, 0)[0] + 6
    for z0, z1 in [(-92, -91), (-93.5, -92), (-95, -93.5), (-97, -95), (-101, -97), (-105, -101), (-110, -105)]:
        vF.dim((14, z0), (14, z1), at=xr, orient='v')
    for z, yk, txt in [(-91, 254, '셀 바닥'), (-91.5, 246, '접착층'), (-92.75, 238, '냉각판 윗벽'),
                       (-94.25, 230, '유로 (비움)'), (-96, 222, '아랫벽 2 ← 주 가열 위치'),
                       (-99, 214, '비금속 상판'), (-103, 206, '코일 도체'), (-107.5, 198, '페라이트')]:
        pass
    sh.lines_of_text(['위부터: 접착층 1 / 냉각판 윗벽 1.5', '유로 1.5 (비움) / 아랫벽 2 (주 가열)',
                      '비금속 상판 4 / 코일 4 / 페라이트 5', '(모두 가정)'], (226, 132), h=2.2, gap=1.55)

    # ---------------- peeling posture (section A-A, 2 deg), 1:2
    ang = 2.0
    target = {'셀 A+0', '단자 A+0', '잔여 버스바 A+0'}
    boxK = (-100.0, -100.0, 90.0, 80.0)
    vK = View(sh, 'front', 0.5, (352, 196), ref=(-5, -10), clip=sg.box(*boxK))
    combo_section(vK, (0, 0, 0), [b for b in bl if not b['name'].startswith(('코일 지지판',))], rot=ang,
                  rot_bench_names=target)
    rect_break(sh, vK, *boxK, amp=0.6, wl=5.0)
    sh.view_label(f'필링 자세 ({ang:g}°, 1:2)', (352, 262))
    pv = vK.P(-74, -91)
    sh.circle(pv, 1.2, 'DIM')
    sh.leader((pv[0] - 0.9, pv[1] - 0.9), (pv[0] - 6.0, pv[1] - 13.0), '회전 중심', h=2.2, end='arrow', side=-1)
    sh.lines_of_text([
        '기울임축(셀 두께 방향과 평행) + X·Z 보정으로',
        '셀 X- 아래 모서리를 축으로 회전 (가정 제어).',
        '가정 형상에서 3.15°에 블록 경계 부재와 접촉.',
    ], (300, 132), h=2.2, gap=1.55)

    # ---------------- heating principle and sequence
    sh.lines_of_text([
        '가열 원리 (설계 가설, 미검증)',
        '1. 유도가열은 코일에 가장 가까운 금속을 데운다 → 하부 보호판 제거, 작업대 윗면은 비금속.',
        '2. 50 kHz 이상에서 알루미늄 표피 깊이 약 0.37 mm (계산값) → 냉각판 아랫벽에서 주로 흡수.',
        '3. 아랫벽 → 전도 → 바닥 접착층 연화. 셀 바닥도 일부 가열됨 → 짧게 끊어 가열, 이웃 셀 냉각.',
        '4. 온도: 광섬유 센서 또는 가열 off 구간 열전대 측정 + 노즈 IR 센서 (대상 셀 윗면).',
        '5. 흡착 → 가열 → 필링. 하중이 기준을 넘으면 더 당기지 않고 가열 유지 (v0.3 원칙).',
        '접착 분리 온도·시간, 상판 강도·내열·절연, 코일 간격, 표피 깊이 모델은 시험·해석 전 미확정.',
    ], (226, 112), h=2.3, gap=1.6)
    return sh


if __name__ == '__main__':
    import sys
    for k, fn in (('1', sheet1), ('2', sheet2)):
        if k in (sys.argv[1:] or ['1', '2']):
            sh = fn()
            stem = f'D-03_R03_{k}of2'
            sh.save(OUT / f'{stem}.dxf')
            sh.render(OUT / f'{stem}.pdf', OUT / f'{stem}.png', dpi=150)
    print('ok')
