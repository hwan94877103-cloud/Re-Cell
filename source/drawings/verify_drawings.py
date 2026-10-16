"""Consistency checks between the R03 drawings (DXF) and the R03 solids. Not a design verification.
1) DXF audit + text style font  2) D-02 balloons cover every BOM item  3) BOM qty = model instance count
4) every D-04 DIMENSION value is a distance that exists in the part solid (vertex/hole coordinates)
5) nose hole table rows = cylindrical faces found in the 03-001 solid"""
import itertools
import json
import math
import re
from collections import defaultdict
from pathlib import Path

import ezdxf
import numpy as np
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder

from common import load, BOM_INFO, HERE

OUT = HERE / 'out'
parts, QTY, ITEM = load()
res = {}


def dim_value(d):
    ds = d.doc.dimstyles.get(d.dxf.dimstyle)
    lfac = ds.dxf.get('dimlfac', 1.0)
    return round(d.get_measurement() * lfac, 3), d.dxf.get('text', '<>')


# ---------------------------------------------------------------- 1) audit, fonts
files = sorted(OUT.glob('D-0*_R03_*.dxf'))
files = [f for f in files if 'of3' not in f.name or f.name.startswith('D-02')]
audit = {}
for f in files:
    doc = ezdxf.readfile(f)
    a = doc.audit()
    audit[f.name] = dict(errors=len(a.errors), fixes=len(a.fixes), font=doc.styles.get('KS').dxf.font,
                         entities=len(doc.modelspace()))
res['dxf_audit'] = audit

# ---------------------------------------------------------------- 2) balloons on D-02
nums = set()
for f in [f for f in files if f.name.startswith('D-02')]:
    msp = ezdxf.readfile(f).modelspace()
    centres = [(round(c.dxf.center.x, 3), round(c.dxf.center.y, 3)) for c in msp.query('CIRCLE[layer=="BALLOON"]')]
    for t in msp.query('TEXT'):
        p = (round(t.dxf.align_point.x, 3), round(t.dxf.align_point.y, 3)) if t.dxf.hasattr('align_point') else None
        if p in centres and t.dxf.text.isdigit():
            nums.add(int(t.dxf.text))
need = set(ITEM.values())
res['balloons'] = dict(found=sorted(nums), missing=sorted(need - nums), extra=sorted(nums - need))

# ---------------------------------------------------------------- 3) BOM quantity vs model
res['bom_qty'] = {no: QTY.get(no, 0) for no in BOM_INFO}
res['bom_items_without_model_part'] = [no for no in BOM_INFO if QTY.get(no, 0) == 0]
res['model_parts_without_bom_row'] = sorted({p['no'] for p in parts if p['no'] not in BOM_INFO and not p['no'].startswith('CM')})


# ---------------------------------------------------------------- 4) D-04 dims vs part geometry
def part_solids(no, tag=None):
    return [p['solid'] for p in parts if p['no'] == no and (tag is None or p['name'].endswith(tag))]


def char_coords(s):
    xs, ys, zs = set(), set(), set()
    for v in s.Vertices():
        xs.add(round(v.X, 3)); ys.add(round(v.Y, 3)); zs.add(round(v.Z, 3))
    bbx = s.BoundingBox()
    xs.add(round((bbx.xmin + bbx.xmax) / 2, 3)); ys.add(round((bbx.ymin + bbx.ymax) / 2, 3)); zs.add(round((bbx.zmin + bbx.zmax) / 2, 3))
    rad = set()
    for f in s.Faces():
        ad = BRepAdaptor_Surface(f.wrapped)
        if ad.GetType() == GeomAbs_Cylinder:
            cy = ad.Cylinder()
            loc, r = cy.Axis().Location(), cy.Radius()
            xs.add(round(loc.X(), 3)); ys.add(round(loc.Y(), 3)); zs.add(round(loc.Z(), 3))
            rad.add(round(2 * r, 3))
            for c in (loc.X() - r, loc.X() + r):
                xs.add(round(c, 3))
            for c in (loc.Y() - r, loc.Y() + r):
                ys.add(round(c, 3))
    dist = set(rad)
    for S in (xs, ys, zs):
        for a, b in itertools.combinations(S, 2):
            dist.add(round(abs(a - b), 3))
    return dist


sheet_parts = {'D-04_R03_1of5.dxf': [('03-001', None)],
               'D-04_R03_2of5.dxf': [('03-007', 'R'), ('03-010', 'R')],
               'D-04_R03_3of5.dxf': [('03-008', None), ('03-009', None), ('03-004', None), ('03-005', None), ('03-006', None)],
               'D-04_R03_4of5.dxf': [('03-002', None)],
               'D-04_R03_5of5.dxf': [('03-003', None), ('03-011', None)]}
d04 = {}
for fname, plist in sheet_parts.items():
    doc = ezdxf.readfile(OUT / fname)
    allowed = set()
    for no, tag in plist:
        for s in part_solids(no, tag):
            allowed |= char_coords(s)
    if fname.endswith('3of5.dxf'):       # clamp pair: dimensions across both halves
        allowed |= char_coords(part_solids('03-008')[0].fuse(part_solids('03-009')[0]))
    rows = []
    for d in doc.modelspace().query('DIMENSION'):
        val, txt = dim_value(d)
        ok = any(abs(val - a) < 0.01 for a in allowed)
        rows.append(dict(value=val, text=txt, in_model=ok))
    d04[fname] = dict(n=len(rows), not_in_model=[r for r in rows if not r['in_model']],
                      values=sorted({r['value'] for r in rows}))
res['d04_dimensions'] = d04

# D-02 dims: list values for the record (assembly dims are differences of model Z/X levels)
d02 = {}
for f in [f for f in files if f.name.startswith('D-02')]:
    doc = ezdxf.readfile(f)
    d02[f.name] = sorted(dim_value(d)[0] for d in doc.modelspace().query('DIMENSION'))
res['d02_dimension_values'] = d02
P_ = __import__('common').T.P
expected_d02 = {16: 'cup+bracket (Z0-16)', 42: 'Z16-58', 76: 'housing 66 + plate 10', 60: 'Z134-194',
                194: 'Z0-194', 264: 'Z0-tilt axis', 64: 'Z0-flange seat', 80: 'cup pitch', 12: 'IR X', 24: 'nose width',
                160: 'housing X', 140: 'housing Y', 55: 'nozzle X', 31: 'nozzle Y', 6: 'bracket', 10: 'cup height',
                3: 'cup edge to terminal (assumed)', 14: 'nozzle block', 18: 'M3 spacing'}
res['d02_unexplained'] = {k: [v for v in vals if round(v) not in expected_d02 or abs(v - round(v)) > 1e-6]
                          for k, vals in d02.items()}

# ---------------------------------------------------------------- 5) nose hole table vs solid
nose = part_solids('03-001')[0]
holes = defaultdict(set)
for f in nose.Faces():
    ad = BRepAdaptor_Surface(f.wrapped)
    if ad.GetType() == GeomAbs_Cylinder:
        cy = ad.Cylinder()
        loc, r = cy.Axis().Location(), cy.Radius()
        bb = f.BoundingBox()
        holes[round(2 * r, 2)].add((round(loc.X(), 2), round(loc.Y(), 2), round(bb.zmin, 2), round(bb.zmax, 2)))
import ks_spec as KS
table = {KS.CLEAR_2['M4']: sorted([(x, y) for x in (-60, 60) for y in (-18, 18)] + [(-52, 0), (-28, 0), (28, 0), (52, 0)]),
         KS.CLEAR_2['M3']: [(6, -18), (18, -18)], KS.IR_BORE_NOSE: [(12, 0)],
         6.0: [(-40, 0), (40, 0)], 12.4: [(-40, 0), (40, 0)]}
depth = {12.4: 14.0, 4.5: '관통 4곳 / 8 (H6) 4곳'}
nose_chk = {}
for d, pos in table.items():
    found = sorted({(h[0], h[1]) for h in holes.get(d, set())})
    ok_pos = sorted(pos) == found
    dz = {round(h[3] - h[2], 2) for h in holes.get(d, set())}
    nose_chk[f'Ø{d}'] = dict(table=sorted(pos), solid=found, match=ok_pos, solid_face_heights=sorted(dz),
                             table_depth=depth.get(d, '관통/포켓까지'))
res['nose_hole_table'] = nose_chk

import bench_r03 as BMv, scene_r03 as SCv
exp_other = {
    'D-03_R03_1of2.dxf': {148: 'cell L', 130: 'coil L', 5: 'cell to block member', 26.5: 'cell T', 28.5: 'pitch',
                          91: 'cell H', 22: 'coil W', 44: 'nozzle exit Z (tool03 Z44)'},
    'D-03_R03_2of2.dxf': {130: 'coil L', 148: 'cell L', 28.5: 'pitch', 1: 'adhesive', 1.5: 'cp top wall / channel',
                          2: 'cp bottom wall', 4: 'top plate / coil', 5: 'ferrite'},
    'D-01_R03_1of1.dxf': {5400: 'fence X', 3000: 'fence Y', 900: 'cell top (ZC)', 2300: 'rail top',
                          3150: 'top equipment underside', 3400: 'top equipment top', 2700: 'rail spacing 2 x RAIL_Y'},
    'D-09_R03_1of1.dxf': {600: 'cup X pitch', 680: 'frame + cups', 400: 'cup Y pitch', 150: 'spindle X', 185: 'interface Z',
                          60: 'end mill below cup plane', 480: 'cup Y outer'},
}
chk_par = dict(cell=BMv.P['cell'], pitch=BMv.PITCH, coil=BMv.COIL, ZC=SCv.ZC, rail=SCv.RAIL_Z, fence=SCv.FENCE, pack=SCv.PACK)
other = {}
for fname, ex in exp_other.items():
    doc = ezdxf.readfile(OUT / fname)
    vals = [dim_value(d)[0] for d in doc.modelspace().query('DIMENSION')]
    other[fname] = dict(values=vals, unexplained=[v for v in vals if not any(abs(v - k) < 0.01 for k in ex)])
res['d03_d01_d09_dimensions'] = other
res['model_parameters_used'] = {k: (list(v) if isinstance(v, tuple) else v) for k, v in chk_par.items()}
print('other sheets:', {k: v['unexplained'] for k, v in other.items()})

# ---------------------------------------------------------------- 7) KS values: calc checks, drawing text = spec, model = spec
from OCP.BRepAdaptor import BRepAdaptor_Surface as _BAS
ks_calc = KS.checks()
res['ks_calc_checks'] = [dict(item=r[0], calc=r[1], criterion=r[2], result=r[3]) for r in ks_calc]
sheet_of = {'03-001': 'D-04_R03_1of5.dxf', '03-007': 'D-04_R03_2of5.dxf', '03-010': 'D-04_R03_2of5.dxf',
            '03-008': 'D-04_R03_3of5.dxf', '03-004': 'D-04_R03_3of5.dxf', '03-002': 'D-04_R03_4of5.dxf',
            '03-003': 'D-04_R03_5of5.dxf', '03-011': 'D-04_R03_5of5.dxf'}
texts = {}
for fn in set(sheet_of.values()):
    msp = ezdxf.readfile(OUT / fn).modelspace()
    texts[fn] = {t.dxf.text for t in msp.query('TEXT')} | {d.dxf.get('text', '') for d in msp.query('DIMENSION')}
missing = []
for no, fn in sheet_of.items():
    for key, val in KS.S[no].items():
        if key == 'rough':
            continue
        want = ('Ø' + val) if key.startswith(('pos', 'perp')) else val
        if want not in texts[fn]:
            missing.append((no, key, want, fn))
extra_want = [('D-04_R03_3of5.dxf', f'Ø{KS.IR_FIT["d"]:g} {KS.IR_FIT["hole"]} (짝가공)'),
              ('D-04_R03_2of5.dxf', f'Ø{KS.ORING_FACE["D_int"]}'),
              ('D-04_R03_2of5.dxf', f'{KS.ORING_FACE["H"]}±{KS.ORING_FACE["H_tol"]}'),
              ('D-04_R03_4of5.dxf', f'Ø{KS.PORT_BOSS["d"]:g}')]
for fn, want in extra_want:
    if want not in texts[fn]:
        missing.append(('-', 'text', want, fn))
# O-ring groove width tolerance is carried by the dimension style (dimtp/dimtm)
g_ok = False
for d in ezdxf.readfile(OUT / 'D-04_R03_2of5.dxf').modelspace().query('DIMENSION'):
    v = dim_value(d)[0]
    ds = d.doc.dimstyles.get(d.dxf.dimstyle)
    if abs(v - KS.ORING_FACE['G']) < 1e-6 and ds.dxf.get('dimtol', 0) == 1 and abs(ds.dxf.get('dimtp', 0) - KS.ORING_FACE['G_tol'][0]) < 1e-9:
        g_ok = True
res['ks_drawing_text'] = dict(missing=missing, groove_G_tolerance_in_dim=g_ok)


def cyl_faces(solid):
    out = []
    for f in solid.Faces():
        ad = _BAS(f.wrapped)
        if ad.GetType() == GeomAbs_Cylinder:
            cy = ad.Cylinder()
            loc, r = cy.Axis().Location(), cy.Radius()
            bb = f.BoundingBox()
            out.append((round(2 * r, 3), round(loc.X(), 2), round(loc.Y(), 2), round(bb.zmin, 2), round(bb.zmax, 2)))
    return out


def has(solid, d, x=None, y=None, z0=None, z1=None):
    for (dd, xx, yy, a, b) in cyl_faces(solid):
        if abs(dd - d) > 1e-3 or (x is not None and abs(xx - x) > 1e-2) or (y is not None and abs(yy - y) > 1e-2):
            continue
        if z0 is not None and abs(a - z0) > 1e-2:
            continue
        if z1 is not None and abs(b - z1) > 1e-2:
            continue
        return True
    return False


o = KS.ORING_FACE
hz0 = 58.0
model = {
    'nose H1 Ø4.5 (M4)': all(has(part_solids('03-001')[0], KS.CLEAR_2['M4'], x, y) for x in (-60, 60) for y in (-18, 18)),
    'nose H3 Ø19': has(part_solids('03-001')[0], KS.IR_BORE_NOSE, 12, 0),
    'retainers Ø4.5': all(has(part_solids(no)[0], KS.CLEAR_2['M4']) for no in ('03-004', '03-005', '03-006')),
    'housing K1 Ø3.3 (M4 drill)': all(has(part_solids('03-002')[0], KS.THREAD['M4']['drill'], x, y) for x in (-60, 60) for y in (-18, 18)),
    'housing port drill Ø4.2, Z59-68': all(has(part_solids('03-002')[0], KS.THREAD['M5']['drill'], x, y, 59.0, 68.0)
                                       for (x, y) in P_['nozzle_xy'].values()),
    'housing port boss Ø11 top Z68': all(has(part_solids('03-002')[0], KS.PORT_BOSS['d'], x, y, None, 68.0)
                                     for (x, y) in P_['nozzle_xy'].values()),
    'IR clamp bore Ø18 (both halves)': all(has(part_solids(no)[0], KS.IR_FIT['d'], 12, 0) for no in ('03-008', '03-009')),
    'nozzle groove Ø9.2 / Ø4.2, depth 1.4': all(has(s, o['D_int'], None, None, hz0 - o['H'], hz0) and
                                                has(s, o['D_int'] - 2 * o['G'], None, None, hz0 - o['H'], hz0)
                                                for s in part_solids('03-010')),
    'retainer bolts M4x18 (head Ø7)': len([p for p in parts if p['no'] == '03-201' and p['name'].startswith('M4x18')]) == 4,
    'O-ring P6 parts': QTY.get('03-213', 0) == 2,
}
res['ks_model_values'] = model
print('KS calc NG:', [r for r in ks_calc if r[3] != 'OK'])
print('KS drawing text missing:', missing, 'G tol in dim:', g_ok)
print('KS model values:', model)
(OUT / 'R03_drawing_checks.json').write_text(json.dumps(res, ensure_ascii=False, indent=1))
print(json.dumps({k: res[k] for k in ('dxf_audit', 'balloons', 'bom_items_without_model_part',
                                      'model_parts_without_bom_row')}, ensure_ascii=False, indent=1))
for k, v in d04.items():
    print(k, 'dims', v['n'], 'not in model:', v['not_in_model'])
print('d02 unexplained:', res['d02_unexplained'])
for k, v in nose_chk.items():
    print(k, v['match'], v['solid'], v['solid_face_heights'])
