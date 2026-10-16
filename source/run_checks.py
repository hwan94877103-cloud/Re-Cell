"""R03 checks: solid validity, static overlap, near contacts, service access, IR line of sight,
peeling sweep (rigid bodies), mass properties, exports. Results -> R03_checks.json + console."""
import itertools, json, math, csv, time
from pathlib import Path
import cadquery as cq
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
import tool03_r03 as T

OUT = Path(__file__).resolve().parent
t0 = time.time()
parts = T.build()
refs = T.reference()
LOS = T.ir_line_of_sight()


def bbox_gap(a, b):
    ba, bb = a.BoundingBox(), b.BoundingBox()
    return max(ba.xmin - bb.xmax, bb.xmin - ba.xmax, ba.ymin - bb.ymax, bb.ymin - ba.ymax, ba.zmin - bb.zmax, bb.zmin - ba.zmax)


def inter_vol(a, b):
    if bbox_gap(a, b) > 1e-6:
        return 0.0
    try:
        return a.intersect(b).Volume()
    except Exception:
        return -1.0


def mind(a, b):
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    d.Perform()
    return d.Value()


res = {'revision': 'R03 provisional (design assumptions)', 'unit': 'mm', 'cadquery': cq.__version__}
# ------------------------------------------------------------------ 1. validity
res['valid_parts'] = all(p['solid'].isValid() for p in parts)
res['valid_refs'] = all(r['solid'].isValid() for r in refs)
res['n_parts'] = len(parts)
res['n_refs'] = len(refs)

# ------------------------------------------------------------------ 2. static overlap (tool + reference at working pose)
allsol = [(p['name'], p['solid']) for p in parts] + [(r['name'], r['solid']) for r in refs if r['role'] != 'adhesive_target']
clashes = []
for (na, a), (nb, b) in itertools.combinations(allsol, 2):
    v = inter_vol(a, b)
    if v > 0.01 or v < 0:
        clashes.append({'a': na, 'b': nb, 'mm3': round(v, 3)})
res['static_clashes'] = clashes
print('static clashes:', len(clashes))
for c in clashes:
    print('  ', c)

# ------------------------------------------------------------------ 3. near contacts between parts that are not meant to touch
mating = set()
near = []
for (na, a), (nb, b) in itertools.combinations([(p['name'], p['solid']) for p in parts], 2):
    if bbox_gap(a, b) > 1.5:
        continue
    d = mind(a, b)
    if 0 < d < 1.5:
        near.append({'a': na, 'b': nb, 'gap': round(d, 3)})
near.sort(key=lambda r: r['gap'])
res['near_gaps_under_1p5'] = near
print('near gaps (0<d<1.5):', len(near))
for n in near[:40]:
    print('  ', n)

# ------------------------------------------------------------------ 4. service access envelopes (top plate removed, tool on bench)
def zc(r, z0, z1, x, y):
    return T.cz(r, z0, z1, x, y)


acc = []
for x in (-60, 60):
    for y in (-18, 18):
        acc.append(('M4 누름판 볼트 육각렌치(위)', zc(4.5, 80.2, 140, x, y), [f'M4x18 볼트 누름판']))
for xs in (-4, 28):
    s = T.cyl(4, 20, (xs, -45.2, 76), (0, 1, 0)).fuse(zc(4, 76, 140, xs, -41))
    acc.append((f'IR 조임 볼트 x={xs} L렌치(뒤쪽)', s, ['M3x30 볼트 IR 조임']))
for xs in (6, 18):
    acc.append((f'IR 발 볼트 x={xs} 렌치(위)', zc(3.5, 83.2, 140, xs, -18), ['M3x25 볼트 IR 발']))
for tag, (x, y) in T.P['nozzle_xy'].items():
    for xx in (x - 9, x + 9):
        acc.append((f'노즐 블록 볼트 {tag} x={xx:+.0f}', zc(3.5, 67.2, 140, xx, y), ['M3x12 볼트 노즐']))
    acc.append((f'푸시인 피팅 해제 공간 {tag}', zc(6.5, 84.2, 96, x, y).cut(zc(2.2, 83, 97, x, y)), ['냉각 공기 호스']))
for x in (-52, -28, 28, 52):
    acc.append((f'컵 브래킷 볼트 x={x} (컵 제거 후, 아래)', zc(3.0, -25, 10.2, x, 0), ['M3x8 볼트 컵', '타원 흡착컵']))
acc.append(('IR 센서 위로 빼기 (앞 클램프 분리 후)', zc(9.0, 80.2, 140, T.P['ir_x'], 0), ['IR 케이블', 'IR 클램프 앞']))
for tag, (x0, x1, y0, y1) in {'L': (-50, 20, -66, -50), 'R': (-20, 50, 50, 66)}.items():
    acc.append((f'진공 유닛 {tag} 위로 빼기', T.bx(x0, x1, y0, y1, 124.2, 160), ['진공 유닛', f'진공 호스 {tag}']))
removed_for_service = ('상판', 'M4x20 볼트 상판', '로드셀', 'M5x12 볼트 로드셀', '로드셀 어댑터판', 'M5x12 볼트 교환기',
                       '교환기 툴 플레이트', '통과 모듈', '교환기 마스터', '기울임축')
access = []
for nm, env, exclude in acc:
    hits = []
    for p in parts:
        if p['name'].startswith(removed_for_service) or any(p['name'].startswith(e) for e in exclude):
            continue
        v = inter_vol(env, p['solid'])
        if v > 0.01:
            hits.append((p['name'], round(v, 2)))
    access.append({'envelope': nm, 'blocked_by': hits})
res['service_access'] = access
print('access envelopes blocked:', sum(1 for a in access if a['blocked_by']))
for a in access:
    if a['blocked_by']:
        print('  ', a)
# top plate screws: free height under module/changer
res['top_plate_screw_headroom'] = []
for p in parts:
    if p['name'].startswith('M4x20 볼트 상판'):
        bb = p['solid'].BoundingBox()
        col = zc(4.5, bb.zmax + 0.1, 260, (bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2)
        hit = [q['name'] for q in parts if q['group'] == 'common' and inter_vol(col, q['solid']) > 0.01]
        res['top_plate_screw_headroom'].append({'screw': p['name'], 'blocked_above_by': hit})

# ------------------------------------------------------------------ 5. IR line of sight (assumed aperture D8 -> spot D6)
los_hits = [(p['name'], round(inter_vol(LOS, p['solid']), 3)) for p in parts if p['name'] != 'IR 센서']
los_hits = [h for h in los_hits if h[1] > 0.01]
vent0 = [r for r in refs if r['name'] == 'REF_벤트+0'][0]['solid']
spot_to_vent = math.hypot(T.P['ir_x'], 0) - 3.0 - 7.0
cupR = [p for p in parts if p['name'] == '타원 흡착컵 R'][0]['solid']
res['ir_line_of_sight'] = {'assumed_aperture_d': 8, 'assumed_spot_d': 6, 'blocked_by': los_hits,
                           'spot_edge_to_vent_edge_mm': round(spot_to_vent, 2),
                           'los_to_cupR_min_mm': round(mind(LOS, cupR), 2)}
print('IR LOS:', res['ir_line_of_sight'])

# ------------------------------------------------------------------ 6. clearances tool <-> cell features at working pose
key = {}
for r in refs:
    if r['name'].startswith(('REF_단자+0', 'REF_버스바잔여+0', 'REF_벤트+0', 'REF_단자+1', 'REF_단자-1', 'REF_버스바잔여+1', 'REF_버스바잔여-1', 'REF_셀+1', 'REF_셀-1')):
        for p in parts:
            if p['group'] != 'tool':
                continue
            if bbox_gap(p['solid'], r['solid']) > 25:
                continue
            d = mind(p['solid'], r['solid'])
            k = r['name']
            if k not in key or d < key[k][1]:
                key[k] = (p['name'], round(d, 2))
res['working_pose_min_clearance'] = {k: {'nearest_tool_part': v[0], 'gap_mm': v[1]} for k, v in key.items()}
print('working-pose clearances:', res['working_pose_min_clearance'])

# ------------------------------------------------------------------ 7. peeling sweep: rigid rotation about bottom short edge X=-74, Z=-91
L, Tth, H = T.P['cell']
piv_a, piv_b = cq.Vector(-L / 2, 1, -H), cq.Vector(-L / 2, 0, -H)       # axis along -Y => +angle lifts X+ end
moving = [(p['name'], p['solid']) for p in parts] + [(r['name'], r['solid']) for r in refs if r['role'] == 'target']
static = [(r['name'], r['solid']) for r in refs if r['role'] == 'static']
test = moving[-1][1].rotate(piv_a, piv_b, 1.0).BoundingBox()
assert test.zmax > 0, 'rotation sense check'
angles = [0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 7.5, 10.0, 15.0]
first = {}
for ang in angles:
    for nm, s in moving:
        rs = s.rotate(piv_a, piv_b, ang)
        for sn, ss in static:
            key2 = (nm, sn)
            if key2 in first:
                continue
            v = inter_vol(rs, ss)
            if v > 0.01:
                first[key2] = ang
peel = [{'moving': k[0], 'static': k[1], 'first_contact_deg': v} for k, v in sorted(first.items(), key=lambda kv: kv[1])]
res['peeling_sweep'] = {'pivot': 'X=-74, Z=-91 (target bottom short edge), axis || Y', 'angles_deg': angles,
                        'first_contacts': peel,
                        'note': 'rigid bodies, pads/adhesive not deformed, sliding contact with pads is not an overlap'}
print('peeling first contacts:')
for p in peel:
    print('  ', p)
# compensation of tilt-axis centre for a pure rotation about the pivot
rx, rz = 0 - (-L / 2), T.Z_TILT_C - (-H)
comp = []
for a in (0.5, 1.0, 2.0, 3.0):
    ar = math.radians(a)
    comp.append({'deg': a, 'dX': round(rx * (math.cos(ar) - 1) - rz * math.sin(ar), 3),
                 'dZ': round(rx * math.sin(ar) + rz * (math.cos(ar) - 1), 3)})
res['tilt_axis_compensation'] = {'r_mm': [rx, rz], 'rows': comp}
print('compensation:', res['tilt_axis_compensation'])

# ------------------------------------------------------------------ 8. mass properties
dens = {'PEEK': 1.32e-6, 'Al6061': 2.70e-6, '강': 7.85e-6, '황동': 8.5e-6, 'PU': 1.2e-6, 'FKM': 1.9e-6}
assumed_mass = {'IR 센서': 0.060, 'IR 케이블': 0.020, '타원 흡착컵': 0.005, '컵 니플': 0.008, '푸시인 피팅': 0.006,
                '진공 유닛': 0.110, '로드셀': 0.450, '교환기 툴 플레이트': 0.450, '통과 모듈 툴측': 0.120,
                '교환기 마스터': 0.900, '통과 모듈 마스터측': 0.120, '기울임축 유닛': 2.200}
rows = []
for p in parts:
    src = 'assumed'
    m = None
    for k, v in assumed_mass.items():
        if p['name'].startswith(k) and p['kind'] in ('구매', '공통'):
            m = v
    if m is None:
        rho = next((v for k, v in dens.items() if p['mat'].startswith(k)), None)
        m = p['solid'].Volume() * rho if rho else 0.0
        src = 'volume x density'
    c = cq.Shape.centerOfMass(p['solid'])
    rows.append({'name': p['name'], 'no': p['no'], 'group': p['group'], 'mass_kg': m, 'src': src, 'c': (c.x, c.y, c.z)})


def agg(sel):
    M = sum(r['mass_kg'] for r in sel)
    cx = sum(r['mass_kg'] * r['c'][0] for r in sel) / M
    cy = sum(r['mass_kg'] * r['c'][1] for r in sel) / M
    czz = sum(r['mass_kg'] * r['c'][2] for r in sel) / M
    return {'mass_kg': round(M, 3), 'cog_mm': [round(cx, 1), round(cy, 1), round(czz, 1)]}


tool_only = [r for r in rows if r['group'] == 'tool' or r['no'] in ('03-108', '03-109', '03-110', '03-011')]
below_lc = [r for r in rows if r['group'] == 'tool' and r['no'] not in ('03-011',)]
stack = rows
res['mass'] = {'tool03_detachable (incl. load cell, adapter, changer tool plate, module)': agg(tool_only),
               'below_load_cell (what the load cell carries as tare)': agg(below_lc),
               'moving_stack_below_Z (tool03 + master + tilt unit)': agg(stack),
               'assumed_purchased_masses_kg': assumed_mass}
g = 9.81
mb = agg(stack)
res['mass']['static_moment_about_tilt_axis_Nm'] = round(mb['mass_kg'] * g * mb['cog_mm'][0] / 1000, 3)
print('mass:', json.dumps(res['mass'], ensure_ascii=False, indent=1))
with open(OUT / 'R03_mass_table.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['part', 'no', 'group', 'mass_kg', 'source', 'cog_x', 'cog_y', 'cog_z'])
    for r in rows:
        w.writerow([r['name'], r['no'], r['group'], round(r['mass_kg'], 4), r['src']] + [round(v, 1) for v in r['c']])

res['elapsed_s'] = round(time.time() - t0, 1)
(OUT / 'R03_checks.json').write_text(json.dumps(res, ensure_ascii=False, indent=1))
print('done', res['elapsed_s'], 's')
