"""3D pictures for the explainer page. Each scene returns (PIL image, {anchor key: (x%, y%)}).
Anchor keys are 'label' or 'label#n' (several marks with one label). Coordinates: tool/bench frame
(Z=0 = cell top) or work-cell world frame (D-01)."""
import sys
from collections import OrderedDict

import cadquery as cq

sys.path[:0] = ['/home/claude/ctp/R03', '/home/claude/ctp/R03/explain']
import tool03_r03 as T
import scene_r03 as S
import bench_r03 as BM
import r3d

PARTS = T.build()
NOT_03 = ('CM-01', 'CM-02', 'CM-03')
BENCH_COL = [('셀', '#8fb0c4'), ('단자', '#c49a62'), ('잔여 버스바', '#b87333'), ('접착층', '#e0b260'),
             ('압축 패드', '#e6c26b'), ('코일 지지판', '#a9b3b9'), ('코일', '#b87333'), ('페라이트', '#3a3f44'),
             ('온도 센서', '#d64545'), ('Al 냉각판', '#b4c6cc'), ('비금속 상판', '#ece6d3'), ('블록 경계 부재', '#8d99a6')]


def bench_color(name):
    return next((c for k, c in BENCH_COL if name.startswith(k)), '#a7b0b6')


def part(no, tag=None):
    return [p for p in PARTS if p['no'] == no and (tag is None or p['name'].endswith(tag))]


def tr(shape, v):
    return shape.translate(cq.Vector(*v))


# ------------------------------------------------------------------------- D-01: work cell
def cell():
    BX, BY = S.local_offset()
    work = S.layout(gantry_x=BX, gantry_y=BY, z_tilt=S.ZC + S.TILT_TO_CUP, with_cells=True)
    COLG = dict(fence='#c9d3da', conveyor='#9aa5ad', bench='#a9b2b8', pack='#7c8790', gantry='#d9822b',
                moving='#e0913b', rack='#a7b4bd', station='#a7b4bd', top='#8a96a0', tool01='#b0a16f',
                tool02='#6f8fa6')
    sc = r3d.Scene()
    for d in work:
        g, n = d['group'], d['name']
        col = '#8fb0c4' if (g == 'pack' and n.startswith('셀')) else COLG.get(g, '#a7b0b6')
        if g == 'fence':
            sc.add_wire(d['solid'], '#8e9aa3')
        else:
            sc.add(d['solid'], col, tol=1.5)
    for d in S.rack_tools(PARTS):
        if d['group'] in ('tool01', 'tool02'):
            sc.add(d['solid'], COLG[d['group']], tol=1.0)
    for p in PARTS:
        if p['no'] != 'CM-03':
            sc.add(tr(p['solid'], (BX, BY, S.ZC)), p['color'], tol=1.0)
    A = OrderedDict([
        ('1', (5400, -1500, 1000)), ('2', (-300, 0, 795)), ('3', (1450, -830, 803)), ('4', (1900, 300, 900)),
        ('5', (3600, -1350, 2300)), ('6', (1002, 900, 2450)), ('7', (1192, -261, 1750)), ('8', (2905, 600, 1000)),
        ('9', (2825, -250, 450)), ('10', (3250, -250, 650)), ('11', (2800, -675, 700)), ('12', (3150, -675, 700)),
        ('13', (3475, -675, 700)), ('14', (4450, 0, 900)), ('15', (1450, 0, 3340)), ('16', (2900, 1200, 700)),
        ('17', (BX, BY - 70, S.ZC + 100)), ('18', (3350, 600, 1150)), ('19', (2720, 600, 1305)),
        ('20', (2700, -1420, 1850))])
    return r3d.render(sc, (-0.85, -1.5, 1.75), A, size=(1500, 1100), zoom=1.05, edge_w=0.9)


# ------------------------------------------------------------------------- D-02: tool 03 cut at Y=0
def tool03_cut():
    sc = r3d.Scene()
    for p in PARTS:
        if p['no'] not in NOT_03:
            sc.add_cut(p['solid'], p['color'])
    A = OrderedDict([
        ('12', (40, 0, 5)), ('7', (55, 0, 13)), ('1', (-55, 0, 40)), ('4', (-40, 14, 76)), ('15', (12, 0, 60)),
        ('34', (40, 0, 45)), ('18', (15, 44, 96)), ('10', (68, 31, 51)), ('2', (-78, 0, 95)), ('3', (-60, 0, 129)),
        ('19', (-30, 0, 146)), ('11', (-45, 0, 164)), ('20', (-30, 0, 181)), ('21', (80, 0, 181)),
        # D-02 2/3 detail marks
        ('B', (40, 0, 12)), ('E', (28, 0.2, 77)), ('C', (68, 31, 51)), ('D', (-40, 14, 76)),
        # D-02 3/3 groups
        ('가#1', (-55, 0, 40)), ('가#2', (-78, 0, 95)), ('가#3', (-60, 0, 129)),
        ('나#1', (40, 0, 5)), ('나#2', (12, 0, 60)), ('나#3', (-30, 0, 146)), ('나#4', (-30, 0, 181)),
        ('다#1', (60, 18, 80)), ('다#2', (40, 0, 45))])
    return r3d.render(sc, (0.55, -1.0, 0.32), A, size=(1200, 1300), out_scale=1.5)


# ------------------------------------------------------------------------- D-03 1/2: bench + tool cut at Y=0
def bench_cut():
    sc = r3d.Scene()
    for b in BM.bench(rows=(0, 1), cells=range(-2, 3)):
        sc.add_cut(b['solid'], bench_color(b['name']), tol=0.3)
    for p in PARTS:
        bb = p['solid'].BoundingBox()
        if p['no'] in NOT_03 or bb.zmin > 133:
            continue
        sc.add_cut(p['solid'], p['color'])
    A = OrderedDict([
        ('1', (-30, 0, -45)), ('2', (150, 0, -45)), ('3', (64, 0, 5)), ('4', (-15, 14.2, -2)), ('5', (-50, 0, -91.5)),
        ('6', (-12, 0, -94.5)), ('7', (26, 0, -99)), ('8', (-62, 0, -103)), ('9', (40, 0, -107.5)),
        ('10', (-25, 0, -122)), ('11', (0, 0, -116)), ('12', (-84, 0, -50)), ('13', (-55, 0, 40)), ('14', (40, 0, 5)),
        ('15', (12, 0, 60)), ('16', (68, 31, 51))])
    return r3d.render(sc, (0.5, -1.0, 0.3), A, size=(1400, 1300), out_scale=1.5, edge_w=1.0)


# ------------------------------------------------------------------------- D-03 2/2: exploded layers
def layers():
    """Slice of three cells (A6 A7 A8 = A-1 A+0 A+1), layers pulled apart downwards, plates cut to the slice."""
    blk = BM.bench(rows=(0,), cells=range(-1, 2))
    gap = {'접착층': -30, 'Al 냉각판': -60, '비금속 상판': -90, '코일': -120, '페라이트': -120, '온도 센서': -120,
           '코일 지지판': -150}
    crop = cq.Solid.makeBox(184, 90, 400, cq.Vector(-92, -45, -300))
    sc = r3d.Scene()
    for b in blk:
        n = b['name']
        k = '코일 지지판' if n.startswith('코일 지지판') else next((k for k in gap if n.startswith(k)), None)
        s = b['solid']
        if n in ('Al 냉각판', '비금속 상판', '코일 지지판'):
            s = s.intersect(crop)
        if n.startswith('블록 경계 부재') and n.endswith('R'):
            continue
        if k is not None:
            s = tr(s, (0, 0, gap[k]))
        col = bench_color(n)
        if n == '셀 A+0':
            col = '#e07a5f'
        if n == '코일 A+0':
            col = '#e8590c'
        if n in ('코일 A-1', '코일 A+1'):
            col = '#4ca6b8'
        sc.add(s, col, tol=0.3)
    zc = -101 - 120
    A = OrderedDict([
        ('A7#1', (0, 0, 0)), ('A7#2', (-30, -8, zc)), ('A6', (-30, -36.5, zc)), ('A8', (30, 20.5, zc)),
        ('F', (-92, -45, -94.5 - 60)), ('가', (74, 0, 0)), ('나', (20, -25, -92 - 60))])
    return r3d.render(sc, (-0.55, -1.0, 0.42), A, size=(1300, 1300), out_scale=1.4, edge_w=1.0)


# ------------------------------------------------------------------------- D-04 parts
def nose():
    s = part('03-001')[0]['solid']
    sc = r3d.Scene()
    sc.add(s, part('03-001')[0]['color'])
    top = r3d.render(sc, (0.35, -1.0, 0.95), OrderedDict([
        ('H1', (-60, -18, 72)), ('H2', (12, -18, 72)), ('H3', (12, 0, 72)), ('H4', (40, 0, 72)), ('1', (-40, -12, 40))]),
        size=(1000, 760), out_scale=1.2)
    bot = r3d.render(sc, (0.3, -0.6, -1.2), OrderedDict([
        ('H5', (40, 0, 16)), ('H6', (28, 0, 16)), ('A', (-30, -17, 64))]), size=(1000, 760), out_scale=1.2)
    return r3d.stacked([top, bot], gap=40)


def bracket_nozzle():
    sc = r3d.Scene()
    sc.add(part('03-007', 'R')[0]['solid'], part('03-007', 'R')[0]['color'])
    off = (40, -31, -40)
    sc.add(tr(part('03-010', 'R')[0]['solid'], off), part('03-010', 'R')[0]['color'])
    sc.add(tr(part('03-213', 'R')[0]['solid'], off), '#2b2b2b')
    A = OrderedDict([('7', (40, -10, 13)), ('10', (55 + 40, 23 - 31, 51 - 40)), ('C', (55 + 40, 31 - 31 - 3.35, 58 - 40))])
    return r3d.render(sc, (0.3, -1.0, 1.05), A, size=(1100, 700), out_scale=1.3)


def clamp():
    sc = r3d.Scene()
    keep = ('03-001', '03-004', '03-005', '03-006', '03-008', '03-009', '03-104', '03-201', '03-203', '03-204')
    for p in PARTS:
        if p['no'] in keep:
            sc.add(p['solid'], p['color'])
    A = OrderedDict([('8', (25, -14, 80)), ('9', (25, 8, 80)), ('가', (12, -9, 80)),
                     ('4', (-40, 18, 76)), ('5', (-40, -18, 76)), ('6', (53, -18, 76))])
    return r3d.render(sc, (0.45, -1.0, 1.0), A, size=(1200, 800), out_scale=1.3)


def housing():
    sc = r3d.Scene()
    sc.add(part('03-002')[0]['solid'], part('03-002')[0]['color'])
    A = OrderedDict([('2', (60, -70, 80)), ('K1', (-60, 18, 64)), ('K2', (12, -18, 64)), ('K3', (55, 31, 68)),
                     ('K5', (64, 31, 64)), ('K6', (70, 60, 124)), ('K7', (-35, -70, 104)), ('가', (-60, 0, 64))])
    return r3d.render(sc, (0.4, -1.0, 1.45), A, size=(1100, 900), out_scale=1.3)


def plates():
    sc = r3d.Scene()
    sc.add(part('03-003')[0]['solid'], part('03-003')[0]['color'])
    off = (175, 0, -35)
    sc.add(tr(part('03-011')[0]['solid'], off), part('03-011')[0]['color'])
    A = OrderedDict([('3', (0, -70, 129)), ('T1', (-70, -60, 134)), ('T2', (21.2, -21.2, 134)), ('T3', (55, -28, 134)),
                     ('11', (175 - 43.3, -25, 129)), ('P1', (175 + 21.2, -21.2, 134)), ('P2', (175, -45, 134))])
    return r3d.render(sc, (0.25, -1.0, 1.1), A, size=(1300, 700), out_scale=1.3)


# ------------------------------------------------------------------------- D-09: tool 02
def tool02():
    items = S.tool02()
    col = {'Ø80 흡착컵': '#30363a', '컵 스프링 홀더': '#555b60', '프레임 (40×40)': '#9aa5ad', '중앙 허브판': '#b8c4cc',
           '어댑터판': '#c4ccd2', '교환기 툴 플레이트': '#598aad', '통과 모듈 툴측': '#58717d',
           '공압 슬라이드 (스트로크 80)': '#5d6b78', '절단 스핀들 Ø40': '#c4ccd2', '엔드밀 Ø6': '#555b60',
           '칩 흡입 후드 Ø40': '#4b89b3', '칩 흡입 호스 Ø25': '#4b89b3', '냉각수 흡입 노즐 Ø10': '#4ca6b8'}
    sc = r3d.Scene()
    for n, s, g in items:
        sc.add(s, col.get(n, '#a7b0b6'), tol=0.6)
    A = OrderedDict([('1', (-300, -240, 20)), ('2', (-300, -216, 65)), ('3', (0, -220, 110)), ('4', (-100, -60, 150)),
                     ('5', (150, 22, 200)), ('6', (150, -20, -5)), ('7', (190, 37, 62)), ('8', (90, 0, 172)),
                     ('9', (-50, -30, 172)), ('10', (150, -20, -35))])
    return r3d.render(sc, (0.55, -1.3, 0.42), A, size=(1400, 1000), out_scale=1.3, edge_w=1.0)


ALL = OrderedDict([('cell', cell), ('tool03_cut', tool03_cut), ('bench_cut', bench_cut), ('layers', layers),
                   ('nose', nose), ('bracket_nozzle', bracket_nozzle), ('clamp', clamp), ('housing', housing),
                   ('plates', plates), ('tool02', tool02)])
