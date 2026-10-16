"""Per-step STEP assemblies for the process-sequence figures.

The browser simulation (sim/sim.js) exports one pose per figure (head X/Y/Z/theta/tilt, tool on the head, 02 slide,
cover / electronics / cell matrices, remaining screws and busbar pieces). This script rebuilds the same scene from the
CadQuery models (scene_r03, bench_r03, tool03_r03, process_r03) and writes one STEP assembly per figure, then
- reads every STEP back (solid count, validity),
- runs a static overlap check between the moving side (gantry head, tools, carried parts) and everything else,
  and between the virtual process objects and the static scene.
Every shape and position is a design assumption (virtual cover, screws, electronics, ports; 01 = envelope only).

usage: python3 process_steps_r03.py POSES_DIR OUT_DIR [P01,P02,...]"""
import json
import sys
import time
from pathlib import Path

import cadquery as cq
import numpy as np
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.gp import gp_Trsf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tool03_r03 as T  # noqa: E402
import bench_r03 as BM  # noqa: E402
import scene_r03 as S  # noqa: E402
import process_r03 as PR  # noqa: E402
import names_r03 as NM  # noqa: E402
import mesh_export as MX  # noqa: E402

ROT_PARTS = ('회전축 (θ)', '기울임축 유닛', '근접 카메라 + 링 조명')
BX, BY = S.local_offset()
PARTS03 = T.build()
NO_BY_NAME = {p['name']: p['no'] for p in PARTS03}
BLK = [dict(b, solid=b['solid'].translate(cq.Vector(BX, BY, S.ZC))) for b in BM.bench(rows=(0, 1), cells=BM.CELL_J)]
_xs = [b['solid'].BoundingBox() for b in BLK if b['name'] in ('비금속 상판', '코일 지지판')]
POCKET = T.bx(min(b.xmin for b in _xs), max(b.xmax for b in _xs), min(b.ymin for b in _xs), max(b.ymax for b in _xs),
              min(b.zmin for b in _xs), S.ZC)
COVER_BODY, COVER_RIM = PR.cover_solids()
SCREWS = PR.screw_xy()
BARS = PR.bridges()
TOOLS = {n: PR.tool_items(n, PARTS03) for n in (1, 2, 3)}
HEAD = PR.head_items(PARTS03)
COL = dict(cover='#c7cfd4', screw='#3b4146', elec='#5f7a52', port='#4ca6b8', bar='#b87333')


def trs(s, m16):
    """Apply a row-major 4x4 (from the browser, float round-off) as a rigid transform: the rotation part is snapped
    to the nearest orthonormal matrix first (OCCT rejects slightly non-orthogonal matrices)."""
    m = np.array(m16, float).reshape(4, 4)
    u, _, vt = np.linalg.svd(m[:3, :3])
    r = u @ vt
    t = gp_Trsf()
    t.SetValues(r[0, 0], r[0, 1], r[0, 2], m[0, 3], r[1, 0], r[1, 1], r[1, 2], m[1, 3], r[2, 0], r[2, 1], r[2, 2], m[2, 3])
    return cq.Shape.cast(BRepBuilderAPI_Transform(s.wrapped, t, True).Shape())


def translation(x, y, z):
    return [1, 0, 0, x, 0, 1, 0, y, 0, 0, 1, z, 0, 0, 0, 1]


def scene_items(pose):
    """[(side, group, name, solid, colour, ascii label)] in world mm. side: 'move' (gantry head, tools on it,
    carried parts) or 'fix' (everything else)."""
    h = pose['head']
    hx, hy, hz, rot, tilt = h['x'], h['y'], h['z'], h['rot'], h['tilt']
    out = []

    def add(side, g, n, s, col, lab):
        out.append((side, g, n, s, col, lab))

    # layout with the gantry at the head position (rotary parts turned by theta like the browser 'rot' group)
    for d in S.layout(gantry_x=hx, gantry_y=hy, z_tilt=hz, with_cells=True):
        g, n, s = d['group'], d['name'], d['solid']
        if n in ('가열 작업대 (코일 구역부)', '냉각판 (팩 바닥)'):
            s = s.cut(POCKET)
        if g == 'moving' and n in ROT_PARTS and abs(rot) > 1e-9:
            s = s.rotate(cq.Vector(hx, hy, 0), cq.Vector(hx, hy, 1), rot)
        col = NM.COLG['cells'] if (g == 'pack' and n.startswith('셀')) else NM.COLG.get(g, '#a7b0b6')
        add('move' if g == 'moving' else 'fix', g, n, s, col, NM.label(g, n))
    # detailed target block: cells (with terminals and busbar residue) follow their simulated matrices
    cm = {c['key']: c for c in pose['cells']}
    for b in BLK:
        n, s = b['name'], b['solid']
        tok = n.split(' ')
        key = tok[-1] if tok[-1][:1] in ('A', 'B') else None
        side = 'fix'
        if key and n.startswith(('셀 ', '단자 ', '잔여 버스바 ')):
            c = cm[key]
            if c['M'] != translation(0, 0, 0):
                s = trs(s, c['M'])
            if c['status'] in ('held', 'carry'):
                side = 'move'
        add(side, 'bench_block', n, s, NM.bench_color(n), NM.en_label(n) or 'bench_block')
    # process objects (virtual)
    cov = pose['cover']
    add('move' if cov['state'] == 'carry' else 'fix', 'process', '커버 (가상)', trs(COVER_BODY, cov['M']), COL['cover'],
        'virtual_cover_body')
    add('fix', 'process', '커버 테두리 (가상)', COVER_RIM, COL['cover'], 'virtual_cover_rim')
    for k, (x, y) in enumerate(SCREWS):
        if pose['screws'][k]:
            add('fix', 'process', f'커버 나사 {k}', PR.screw_solid(x, y), COL['screw'], f'virtual_cover_screw_{k:02d}')
    el = pose['elec']
    add('move' if el['state'] == 'carry' else 'fix', 'process', '전장품 (가상)', trs(PR.electronics_solid(), el['M']),
        COL['elec'], 'virtual_electronics_BMS_BDU')
    for k, p in enumerate(PR.port_solids()):
        add('fix', 'process', f'냉각수 포트 {k}', p, COL['port'], f'virtual_coolant_port_{k}')
    for k, br in enumerate(BARS):
        if pose['bars'][k]:
            add('fix', 'process', f'버스바 연결부 {br["key"]}', br['solid'], COL['bar'], f'busbar_bridge_{br["key"]}')
    # tools: on the head (pose matrix) or parked in the rack
    hm = PR.head_matrix(hx, hy, hz, rot, tilt)
    for n in (1, 2, 3):
        on = pose['tool'] == n
        p = PR.PARK[n]
        M = hm if on else translation(p[0], p[1], p[2] + PR.TOOL_DOCK[n])
        for name, s, col in TOOLS[n]:
            if n == 2 and name[3:] in PR.SLIDER_02:
                s = s.translate(cq.Vector(0, 0, pose['slide'] if on else 80.0))
            g = f'tool0{n}'
            lab = 'tool01_envelope_team_design' if (n == 1 and '외형' in name) else (
                'tool01_changer_tool_plate' if n == 1 else NM.label(g, name, NO_BY_NAME))
            add('move' if on else 'fix', g, name, trs(s, M), col, lab)
    for name, s, col in HEAD:
        no = name.split(' ')[-1]
        add('move', 'head', name, trs(s, hm), col, f'head_{no}_{NM.NAME03.get(no, "")}')
    return out


def overlaps(items, min_vol=0.5):
    """Static overlap check: moving side vs fixed side, plus virtual process objects vs the fixed scene."""
    bbs = [it[3].BoundingBox() for it in items]
    res = []
    for i, a in enumerate(items):
        for j in range(i + 1, len(items)):
            b = items[j]
            pair_move = (a[0] == 'move') != (b[0] == 'move')
            pair_proc = (a[1] == 'process' or b[1] == 'process') and a[0] == b[0] == 'fix'
            if not (pair_move or pair_proc):
                continue
            A, B = bbs[i], bbs[j]
            if A.xmax <= B.xmin or B.xmax <= A.xmin or A.ymax <= B.ymin or B.ymax <= A.ymin or A.zmax <= B.zmin or B.zmax <= A.zmin:
                continue
            try:
                v = a[3].intersect(b[3]).Volume()
            except Exception:
                v = -1.0
            if v > min_vol or v < 0:
                res.append(dict(a=f'{a[1]}:{a[2]}', b=f'{b[1]}:{b[2]}', volume_mm3=round(v, 1), kind=classify(a, b)))
    return res


def classify(a, b):
    names = a[2] + ' | ' + b[2]
    if '엔드밀' in names and ('버스바 연결부' in names or '커버' in names):
        return 'intended_cut'          # the end mill inside the material it is cutting
    if '커버 나사' in names and '팩 프레임' in names:
        return 'screw_hole_not_modelled'
    if '노즐' in names and '냉각수 포트' in names:
        return 'nozzle_in_port'
    return 'check'


def build(pose_path, out_dir):
    pose = json.loads(Path(pose_path).read_text(encoding='utf-8'))
    t0 = time.time()
    items = scene_items(pose)
    name = f"CTP_R03_process_{pose['id']}_{pose['no'].replace('-', '_') if pose['no'].isascii() else 'emergency' if pose['no'] == '비상' else 'intake'}"
    path = Path(out_dir) / f'{name}.step'
    MX.build_assembly([(it[1], it[3], it[4], it[5]) for it in items], name).export(str(path))
    rb = cq.importers.importStep(str(path)).solids().vals()
    clash = overlaps(items)
    rep = dict(id=pose['id'], no=pose['no'], title=pose['title'], file=path.name, bytes=path.stat().st_size,
               solids=len(items), readback_solids=len(rb), readback_valid=all(s.isValid() for s in rb),
               tool=pose['tool'], head=pose['head'], slide=pose['slide'], cover=pose['cover']['state'],
               electronics=pose['elec']['state'], screws_left=sum(pose['screws']), bars_left=sum(pose['bars']),
               cells={st: sum(1 for c in pose['cells'] if c['status'] == st) for st in sorted({c['status'] for c in pose['cells']})},
               overlaps=clash, seconds=round(time.time() - t0, 1))
    return rep


if __name__ == '__main__':
    poses, out = Path(sys.argv[1]), Path(sys.argv[2])
    only = set(sys.argv[3].split(',')) if len(sys.argv) > 3 else None
    out.mkdir(parents=True, exist_ok=True)
    reps = []
    for p in sorted(poses.glob('P*.json')):
        if only and p.stem not in only:
            continue
        r = build(p, out)
        reps.append(r)
        print(r['id'], r['file'], r['bytes'] // 1024, 'KB', r['solids'], 'solids, readback', r['readback_solids'],
              r['readback_valid'], 'overlaps', [(c['a'], c['b'], c['volume_mm3'], c['kind']) for c in r['overlaps']], r['seconds'], 's')
    if not only:
        (out / 'process_steps_check.json').write_text(json.dumps(reps, ensure_ascii=False, indent=1), encoding='utf-8')
