"""Export the R03 CAD scene for the browser process simulation (sim/scene.json).
Geometry comes straight from the CadQuery models (scene_r03, bench_r03, tool03_r03, process_r03).
Frames: world mm, Z up. Moving gantry parts at gx = gy = 0 with the tilt centre at Z = 0. Each tool and the
head-side changer master are exported in their coupled tilt-centre frame. Every value is a design assumption."""
import base64
import json
import sys
from pathlib import Path

import numpy as np
import cadquery as cq

R03 = Path('/home/claude/ctp/R03')
sys.path.insert(0, str(R03))
import tool03_r03 as T
import bench_r03 as BM
import scene_r03 as S
import process_r03 as PR

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else R03 / 'sim' / 'scene.json'
BX, BY = S.local_offset()
ZC, TC = S.ZC, S.TILT_TO_CUP

COLG = dict(fence='#c9d3da', conveyor='#9aa5ad', bench='#a9b2b8', pack='#7c8790', gantry='#d9822b',
            moving='#e0913b', rack='#a7b4bd', station='#a7b4bd', top='#8a96a0')
BENCH_COL = [('셀', '#8fb0c4'), ('단자', '#c49a62'), ('잔여 버스바', '#b87333'), ('접착층', '#e0b260'),
             ('압축 패드', '#e6c26b'), ('코일 지지판', '#a9b3b9'), ('코일', '#b87333'), ('페라이트', '#3a3f44'),
             ('온도 센서', '#d64545'), ('Al 냉각판', '#b4c6cc'), ('비금속 상판', '#ece6d3'), ('블록 경계 부재', '#8d99a6')]


def bench_color(name):
    return next((c for k, c in BENCH_COL if name.startswith(k)), '#a7b0b6')


def tess(shape, tol, ang):
    v, t = shape.tessellate(tol, ang)
    return np.array([(p.x, p.y, p.z) for p in v], np.float32), np.array(t, np.uint32).reshape(-1, 3)


class Bucket:
    def __init__(self):
        self.P, self.I, self.n = [], [], 0

    def add(self, shape, tol=1.0, ang=0.6):
        p, i = tess(shape, tol, ang)
        if len(i) == 0:
            return
        self.P.append(p)
        self.I.append(i + self.n)
        self.n += len(p)

    def pack(self):
        P = np.concatenate(self.P)
        I = np.concatenate(self.I).ravel()
        it = 16 if self.n < 65536 else 32
        return dict(pos=base64.b64encode(P.astype('<f4').tobytes()).decode(),
                    idx=base64.b64encode(I.astype('<u2' if it == 16 else '<u4').tobytes()).decode(),
                    it=it, nv=int(self.n), nt=int(len(I) // 3))


_b = {}


def put(bkey, shape, color, tol=1.0, ang=0.6, **meta):
    k = (bkey, color)
    if k not in _b:
        _b[k] = (Bucket(), dict(meta, color=color))
    _b[k][0].add(shape, tol, ang)


def bb(shape):
    b = shape.BoundingBox()
    return [round(b.xmin, 1), round(b.xmax, 1), round(b.ymin, 1), round(b.ymax, 1), round(b.zmin, 1), round(b.zmax, 1)]


obstacles = []
parts = T.build()

# ------------------------------------------------------------------ static layout and the moving gantry
lay = S.layout(gantry_x=0.0, gantry_y=0.0, z_tilt=0.0, with_cells=True)
blk = [dict(b, solid=b['solid'].translate(cq.Vector(BX, BY, ZC))) for b in BM.bench(rows=(0, 1), cells=BM.CELL_J)]
xs = [b['solid'].BoundingBox() for b in blk if b['name'] in ('비금속 상판', '코일 지지판')]
pocket = T.bx(min(b.xmin for b in xs), max(b.xmax for b in xs), min(b.ymin for b in xs), max(b.ymax for b in xs),
              min(b.zmin for b in xs), ZC)
MOVE = {'Y 브리지': 'bridge', 'Z 캐리지': 'carriage', 'Z 램': 'ram'}
for d in lay:
    g, n, s = d['group'], d['name'], d['solid']
    if g == 'moving':
        grp = MOVE.get(n, 'rot')
        col = COLG['moving'] if grp in ('bridge', 'carriage') else ('#618ba5' if n == '기울임축 유닛' else '#d6dde2')
        put(('move', grp, col), s, col, tol=1.0, group=grp, kind='solid')
        continue
    if n in ('가열 작업대 (코일 구역부)', '냉각판 (팩 바닥)'):
        s = s.cut(pocket)
    col = '#8fb0c4' if (g == 'pack' and n.startswith('셀')) else COLG.get(g, '#a7b0b6')
    if g == 'fence':
        put(('fence',), s, col, tol=2.0, group='static', kind='fence')
        continue
    put(('static', g), s, col, tol=1.0, group='static', kind='solid')
    if g not in ('gantry', 'top', 'fence'):
        obstacles.append(dict(n=n, b=bb(s)))

# ------------------------------------------------------------------ detailed target block (world)
cells = {}
for b in blk:
    n, s = b['name'], b['solid']
    tok = n.split(' ')
    suffix = tok[-1] if tok[-1][:1] in ('A', 'B') else None
    col = bench_color(n)
    if suffix and n.startswith('셀 '):
        put(('cell', suffix, 'body'), s, col, tol=0.5, group='cell', kind='body', key=suffix)
        cells.setdefault(suffix, {})['body'] = bb(s)
    elif suffix and (n.startswith('단자') or n.startswith('잔여 버스바')):
        put(('cell', suffix, 'terms'), s, '#b98552', tol=0.5, group='cell', kind='terms', key=suffix)
    elif suffix and n.startswith('접착층'):
        put(('adh', suffix), s, col, tol=0.5, group='adh', kind='adh', key=suffix)
    elif suffix and n.startswith('압축 패드'):
        put(('pad', suffix), s, col, tol=0.5, group='pad', kind='pad', key=suffix)
    elif suffix and n.startswith('코일 ') and not n.startswith('코일 지지판'):
        put(('coil', suffix), s, col, tol=0.4, ang=0.4, group='coil', kind='coil', key=suffix)
    elif n in ('Al 냉각판', '비금속 상판', '코일 지지판'):
        put(('plate', n), s, col, tol=0.5, group='static', kind='plate')
    else:
        put(('static', 'blk', n.split(' ')[0]), s, col, tol=0.5, group='static', kind='blockpart')
obstacles.append(dict(n='대상 블록 셀', b=bb(cq.Compound.makeCompound(
    [b['solid'] for b in blk if b['name'].startswith(('셀', '단자', '잔여'))]))))

# ------------------------------------------------------------------ process objects (assumed)
body, rim = PR.cover_solids()
put(('coverBody',), body, '#c7cfd4', tol=1.0, group='coverBody', kind='solid')
put(('coverRim',), rim, '#c7cfd4', tol=1.0, group='static', kind='solid')
for k, (x, y) in enumerate(PR.screw_xy()):
    put(('screw', k), PR.screw_solid(x, y), '#3b4146', tol=0.3, ang=0.5, group='screw', kind='solid', key=k)
put(('elec',), PR.electronics_solid(), '#5f7a52', tol=0.5, group='elec', kind='solid')
for p in PR.port_solids():
    put(('ports',), p, '#4ca6b8', tol=0.3, ang=0.4, group='static', kind='solid')
    obstacles.append(dict(n='냉각수 포트', b=bb(p)))
brs = PR.bridges()
for k, br in enumerate(brs):
    put(('bar', k), br['solid'], '#b87333', tol=0.3, group='bar', kind='solid', key=k)

# ------------------------------------------------------------------ tools (coupled tilt-centre frames)
tool_bb = {}
for n in (1, 2, 3):
    items = PR.tool_items(n, parts)
    sl = []
    for name, s, col in items:
        grp = f'tool{n}'
        if n == 2 and name[3:] in PR.SLIDER_02:
            grp = 'tool2s'
            sl.append(s)
        put((grp, col), s, col, tol=0.3 if n != 2 else 0.5, ang=0.5, group=grp, kind='solid')
    tool_bb[str(n)] = bb(cq.Compound.makeCompound([s for _, s, _ in items]))
    if sl:
        tool_bb['2s'] = bb(cq.Compound.makeCompound(sl))
for name, s, col in PR.head_items(parts):
    put(('headout', col), s, col, tol=0.4, ang=0.5, group='headout', kind='solid')

MESHES = []
for (k, col), (bk, meta) in _b.items():
    m = dict(meta)
    m.update(bk.pack())
    MESHES.append(m)

# ------------------------------------------------------------------ constants for the simulation
const = dict(
    BX=round(BX, 3), BY=round(BY, 3), ZC=ZC, TILT=TC, CELL=dict(L=BM.CELL_L, T=BM.P['cell'][1], H=BM.CELL_H),
    ROW_X=list(BM.ROW_X), PITCH=BM.PITCH, CELL_J=list(BM.CELL_J),
    X=[350.0, 4400.0], Y=[-900.0, 900.0], ZT=[ZC + TC, ZC + TC + S.STROKE['Z']],
    HOME=[1270.0, -200.0, ZC + TC + 300.0],
    MEAS=dict(x=2825.0, y=-100.0, top=905.0), TANK=dict(x=3250.0, y=-100.0, rim=800.0, floor=520.0, inner=[3070, 3430, -230, 30]),
    BIN=dict(x=3475.0, y=-675.0, rim=700.0, floor=40.0, inner=[3365, 3585, -885, -465]),
    BINS={str(k): dict(x=v[0], y=v[1], rim=700.0, floor=40.0) for k, v in PR.BIN.items()},
    PEEL_LIMIT_DEG=3.15, END_GAP=5.0,
    cells={k: v['body'] for k, v in sorted(cells.items())},
    DOCK={str(k): v for k, v in PR.TOOL_DOCK.items()}, PARK={str(k): list(v) for k, v in PR.PARK.items()},
    TOOLBB=tool_bb, T2=PR.T2,
    COVER=dict(PR.COVER, z0=PR.FRAME_TOP, pack=list(S.PACK), body=bb(body)), SCREWS=PR.screw_xy(),
    SEAL=PR.seal_path(), ELEC=list(PR.ELEC), PORTS=[list(p) for p in PR.PORTS], PORT_TOP=PR.PORT_TOP,
    BARS=[dict(key=b['key'], x=b['x'], y=b['y']) for b in brs], TABLE=list(S.COVER_TABLE),
    FRAME_TOP=PR.FRAME_TOP)
scene = dict(units='mm', up='Z', note='R03 assumed geometry (CadQuery), coarse tessellation for the browser',
             const=const, obstacles=obstacles, meshes=MESHES)
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(scene, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
tot = sum(m['nt'] for m in MESHES)
print('meshes', len(MESHES), 'triangles', tot, 'bytes', OUT.stat().st_size)
by = {}
for m in MESHES:
    by[m['group']] = by.get(m['group'], 0) + m['nt']
print(by)
print('tool bb', tool_bb)
