"""Build the organised R03 package: one folder per drawing number (drawings / 3D_parts / 3D_assembly) and
00_ALL with the complete assembly, the concept video, all drawings, README and reports. ASCII names only."""
import json
import shutil
import sys
import zipfile
from collections import OrderedDict
from pathlib import Path

import cadquery as cq
import pymupdf

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tool03_r03 as T
import bench_r03 as BM
import scene_r03 as S
import mesh_export as MX

DWG = HERE / 'drawings' / 'out'
ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'package' / 'CTP_R03'
if ROOT.exists():
    shutil.rmtree(ROOT)

NAME03 = {
    '03-001': 'nose_PEEK', '03-002': 'housing_body', '03-003': 'top_plate_t10', '03-004': 'retainer_front',
    '03-005': 'retainer_rear_left', '03-006': 'retainer_rear_right', '03-007': 'cup_bracket', '03-008': 'IR_clamp_rear',
    '03-009': 'IR_clamp_front', '03-010': 'nozzle_block', '03-011': 'loadcell_adapter_plate',
    '03-101': 'oval_cup_30x20', '03-102': 'cup_nipple_M5', '03-103': 'nut_M5_thin', '03-104': 'IR_sensor_D18x40',
    '03-105': 'IR_cable', '03-106': 'push_in_fitting_M5', '03-107': 'vacuum_unit', '03-108': 'load_cell_D80x25',
    '03-109': 'changer_tool_plate_D100', '03-110': 'pass_through_module_tool_side', '03-201': 'SHCS_M4x18_retainer',
    '03-203': 'SHCS_M3x25', '03-204': 'SHCS_M3x30', '03-205': 'SHCS_M3x8_cup', '03-206': 'insert_M3_PEEK',
    '03-207': 'SHCS_M3x12', '03-208': 'SHCS_M4x20', '03-209': 'SHCS_M5x12_loadcell_lower',
    '03-210': 'SHCS_M5x12_loadcell_upper', '03-211': 'SHCS_M5x12_changer', '03-212': 'SHCS_M3x8_unit', '03-213': 'O_ring_P6',
    '03-301': 'vacuum_hose_OD4', '03-302': 'cooling_air_hose_OD4', 'CM-01': 'common_changer_master',
    'CM-02': 'common_pass_through_module_master', 'CM-03': 'common_tilt_unit',
}
GROUP01 = OrderedDict([('fence', 'safety_fence'), ('conveyor', 'intake_conveyor'), ('bench', 'heating_bench'),
                       ('pack', 'virtual_CTP_pack'), ('gantry', 'gantry_frame_rails'), ('moving', 'gantry_bridge_Z_theta_tilt'),
                       ('rack', 'tool_rack'), ('top', 'top_fixed_equipment')])
STATION01 = OrderedDict([('셀 측정대', 'cell_measurement_station'), ('측정 지그', 'cell_measurement_station'),
                         ('비상 침수조', 'emergency_immersion_tank'), ('침수조 받침', 'emergency_immersion_tank'),
                         ('회수함', 'recovery_bins'), ('셀 회수함', 'recovery_bins'), ('커버 거치대', 'cover_table'),
                         ('거치대 다리', 'cover_table'), ('냉각수 회수 탱크', 'coolant_tank')])
NAME_BENCH = OrderedDict([('셀 A+0', 'cell_148x91x26.5'), ('단자 A+0', 'cell_terminal'), ('잔여 버스바 A+0', 'busbar_residue'),
                          ('압축 패드 A+0', 'compression_pad_2'), ('접착층 A+0', 'adhesive_layer_1'),
                          ('코일 A+0', 'induction_coil_racetrack_130x22'), ('페라이트 A+0', 'ferrite_t5'),
                          ('온도 센서 A+0', 'temperature_sensor_fiber'), ('Al 냉각판', 'cooling_plate_Al_5_block'),
                          ('비금속 상판', 'bench_top_plate_nonmetal_t4'), ('코일 지지판', 'coil_support_plate'),
                          ('블록 경계 부재', 'block_end_member')])
COLG = dict(fence='#c9d3da59', conveyor='#9aa5ad', bench='#9aa5ad', pack='#7c8790', gantry='#d9822b',
            moving='#e0913b', rack='#a7b4bd', station='#a7b4bd', top='#8a96a0', tool01='#b0a16f', tool02='#6f8fa6',
            cells='#7fa3b8')
BENCH_COL = [('셀', '#7fa3b8'), ('단자', '#c49a62'), ('잔여 버스바', '#b87333'), ('접착층', '#d7a266'),
             ('압축 패드', '#e6c26b'), ('코일 지지판', '#9aa5ad'), ('코일', '#b87333'), ('페라이트', '#3a3f44'),
             ('온도 센서', '#d64545'), ('Al 냉각판', '#a5b8bf'), ('비금속 상판', '#e8e2d0'), ('블록 경계 부재', '#8d99a6')]
COL02 = {'Ø80 흡착컵': '#30363a', '컵 스프링 홀더': '#555b60', '프레임 (40×40)': '#9aa5ad', '중앙 허브판': '#b8c4cc',
         '어댑터판': '#c4ccd2', '교환기 툴 플레이트': '#598aad', '통과 모듈 툴측': '#58717d',
         '공압 슬라이드 (스트로크 80)': '#5d6b78', '절단 스핀들 Ø40': '#c4ccd2', '엔드밀 Ø6': '#555b60',
         '칩 흡입 후드 Ø40': '#4b89b3', '칩 흡입 호스 Ø25': '#4b89b3', '냉각수 흡입 노즐 Ø10': '#4ca6b8'}


def bench_color(name):
    return next((c for k, c in BENCH_COL if name.startswith(k)), '#a7b0b6')


# ASCII part names for STEP/GLB trees (Korean names can garble in some viewers)
EN = {'안전 펜스': 'safety_fence', '팩 입고 컨베이어': 'intake_conveyor', '롤러': 'roller',
      '가열 작업대 (코일 구역부)': 'heating_bench_coil_zone', '작업대 다리': 'bench_leg', '팩 클램프': 'pack_clamp',
      '팩 프레임': 'pack_frame', '냉각판 (팩 바닥)': 'pack_cooling_plate', '셀 블록 (2×12)': 'cell_block_2x12',
      '블록 경계 부재': 'block_end_member', '갠트리 기둥': 'gantry_column', 'X 레일 빔': 'X_rail_beam',
      'Y 브리지': 'Y_bridge', 'Z 캐리지': 'Z_carriage', 'Z 램': 'Z_ram', '회전축 (θ)': 'rotary_axis_theta',
      '기울임축 유닛': 'tilt_unit', '근접 카메라 + 링 조명': 'close_camera_ring_light',
      '공구 거치대 (01·03)': 'tool_rack_01_03', '02 거치 레일': 'tool02_rack_rail', '거치대 다리': 'stand_leg',
      '셀 측정대 (전압·절연)': 'cell_measurement_station', '측정 지그 (스프링 핀)': 'measurement_jig_spring_pins',
      '침수조 받침': 'immersion_tank_stand', '비상 침수조 400×300×300': 'emergency_immersion_tank',
      '회수함: 나사·칩': 'bin_screws_chips', '회수함: 전장품': 'bin_electrical_parts',
      '셀 회수함 (재사용/재활용)': 'bin_cells_reuse_recycle', '커버 거치대': 'cover_table',
      '냉각수 회수 탱크': 'coolant_tank', '상부 고정 프레임': 'top_fixed_frame', '전체 카메라': 'overview_camera',
      '열화상 카메라': 'thermal_camera', '배기 후드': 'exhaust_hood', '배기 덕트': 'exhaust_duct',
      '가스 감지기': 'gas_detector', '01 외형 (팀원 설계, 가정)': 'tool01_envelope_team_design',
      '교환기 툴 플레이트': 'changer_tool_plate',
      '셀': 'cell', '단자': 'terminal', '잔여 버스바': 'busbar_residue', '접착층': 'adhesive_layer',
      '압축 패드': 'compression_pad', '코일 지지판': 'coil_support_plate', '코일': 'coil', '페라이트': 'ferrite',
      '온도 센서': 'temp_sensor', 'Al 냉각판': 'cooling_plate_Al', '비금속 상판': 'top_plate_nonmetal'}
EN_KEYS = sorted(EN, key=len, reverse=True)


def en_label(name):
    k = next((k for k in EN_KEYS if name.startswith(k)), None)
    if k is None:
        return ''
    rest = ''.join(c if c.isascii() and (c.isalnum() or c in '+-') else '_' for c in name[len(k):].strip()).strip('_')
    return EN[k] + (f'_{rest}' if rest else '')


def item_label(g, n):
    """ASCII label for an item of group g with (Korean) name or part number n."""
    if g == 'tool03':
        no = n if n in NAME03 else no_by_name.get(n[3:] if n.startswith('03 ') else n)
        return f'tool03_{no}_{NAME03[no]}' if no else 'tool03'
    if g == 'tool02':
        e = NAME02.get(n[3:] if n.startswith('02 ') else n, '')
        return f'tool02_{e}' if e else 'tool02'
    e = en_label(n)
    if not e:
        return g
    return e if e.startswith(g) else f'{g}_{e}'


NAME02 = {'Ø80 흡착컵': 'suction_cup_D80', '컵 스프링 홀더': 'cup_spring_holder', '프레임 (40×40)': 'frame_profile_40x40',
          '중앙 허브판': 'hub_plate', '어댑터판': 'adapter_plate', '교환기 툴 플레이트': 'changer_tool_plate_D100',
          '통과 모듈 툴측': 'pass_through_module_tool_side', '공압 슬라이드 (스트로크 80)': 'pneumatic_slide_stroke80',
          '절단 스핀들 Ø40': 'cutting_spindle_D40', '엔드밀 Ø6': 'end_mill_D6', '칩 흡입 후드 Ø40': 'chip_suction_hood_D40',
          '칩 흡입 호스 Ø25': 'chip_suction_hose_D25', '냉각수 흡입 노즐 Ø10': 'coolant_suction_nozzle_D10'}


def mk(*p):
    d = ROOT.joinpath(*p)
    d.mkdir(parents=True, exist_ok=True)
    return d


def comp(solids):
    return cq.Compound.makeCompound([s for s in solids])


def export_shape(shape, path):
    cq.exporters.export(shape, str(path))


MESH = {}


def export_asm(items, path, name, tol=0.1, ang=0.25, stl_skip=('fence',)):
    """items: (name, solid, colour). STEP (with colours) for CAD, GLB (colours, parts) and STL (one mesh) for 3D viewers."""
    a = MX.build_assembly(items, name)
    a.export(str(path))
    glb, stl = path.with_suffix('.glb'), path.with_suffix('.stl')
    MX.export_glb(a, glb, tol, ang)
    MX.export_stl([it[1] for it in items if it[0] not in stl_skip], stl, tol, ang)
    MESH[path.stem] = dict(MX.glb_info(glb), stl_bytes=stl.stat().st_size,
                           stl_skipped=[k for k in stl_skip if any(it[0] == k for it in items)])


def congruent(a, b, tol=0.05):
    ba, bb = a.BoundingBox(), b.BoundingBox()
    if abs(a.Volume() - b.Volume()) > tol * 10:
        return False
    if any(abs(x - y) > tol for x, y in [(ba.xlen, bb.xlen), (ba.ylen, bb.ylen), (ba.zlen, bb.zlen)]):
        return False
    m = b.translate(cq.Vector(ba.xmin - bb.xmin, ba.ymin - bb.ymin, ba.zmin - bb.zmin))
    try:
        return a.cut(m).Volume() < tol * 10
    except Exception:
        return False


def drawings(folder, names):
    d = mk(folder, 'drawings')
    doc = pymupdf.open()
    for n in names:
        doc.insert_pdf(pymupdf.open(DWG / f'{n}.pdf'))
        shutil.copy(DWG / f'{n}.dxf', d / f'{n}.dxf')
    doc.save(d / f'{folder.split("_")[0]}_R03.pdf', garbage=3, deflate=True)


log = {}
parts = T.build()
no_by_name = {p['name']: p['no'] for p in parts}
BX, BY = S.local_offset()


def t03(p):
    return (p['no'], p['solid'], p['color'], f"{p['no']}_{NAME03[p['no']]}")

# ---------------------------------------------------------------- D-02 (tool 03 assembly)
F2 = 'D-02_Tool03_Assembly'
drawings(F2, ['D-02_R03_1of3', 'D-02_R03_2of3', 'D-02_R03_3of3'])
p2 = mk(F2, '3D_parts')
groups = OrderedDict()
for p in parts:
    groups.setdefault(p['no'], []).append(p)
n_files = 0
for no, inst in groups.items():
    reps = []
    for p in inst:
        if not any(congruent(p['solid'], r['solid']) for r in reps):
            reps.append(p)
    for k, r in enumerate(reps):
        suf = '' if len(reps) == 1 else '_' + ('L' if r['name'].endswith('L') else 'R' if r['name'].endswith('R') else str(k))
        export_shape(r['solid'], p2 / f'{no}_{NAME03[no]}{suf}.step')
        n_files += 1
log['D-02 parts'] = n_files
export_asm([t03(p) for p in parts], mk(F2, '3D_assembly') / 'TOOL03_R03_assembly.step',
           'TOOL03_R03', tol=0.05, ang=0.2)

# ---------------------------------------------------------------- D-04 (tool 03 machined parts)
F4 = 'D-04_Tool03_Parts'
drawings(F4, [f'D-04_R03_{k}of5' for k in range(1, 6)])
for ext in ('pdf', 'xlsx'):
    shutil.copy(DWG / f'KS_적용_근거표_D-04_R03.{ext}', ROOT / F4 / 'drawings' / f'D-04_KS_rationale_R03.{ext}')
p4 = mk(F4, '3D_parts')
mach = [p for p in parts if p['kind'] == '가공']
done = set()
for p in mach:
    if p['no'] in done:
        continue
    done.add(p['no'])
    export_shape(p['solid'], p4 / f"{p['no']}_{NAME03[p['no']]}.step")
log['D-04 parts'] = len(done)
export_asm([t03(p) for p in mach], mk(F4, '3D_assembly') / 'TOOL03_machined_parts_in_place.step',
           'TOOL03_MACHINED', tol=0.05, ang=0.2)

# ---------------------------------------------------------------- D-03 (bench section)
F3 = 'D-03_Bench_Section'
drawings(F3, ['D-03_R03_1of2', 'D-03_R03_2of2'])
p3 = mk(F3, '3D_parts')
blk = BM.bench(rows=(0, 1), cells=BM.CELL_J)
seen = set()
for b in blk:
    nm = NAME_BENCH.get(b['name'])
    if nm and nm not in seen:
        seen.add(nm)
        export_shape(b['solid'], p3 / f'{nm}.step')
log['D-03 parts'] = len(seen)
a3 = mk(F3, '3D_assembly')
export_asm([('bench', b['solid'], bench_color(b['name']), en_label(b['name'])) for b in blk],
           a3 / 'BENCH_block_2x12_assembly.step', 'BENCH_BLOCK', tol=0.1, ang=0.25)
local_blk = BM.bench(rows=(0, 1), cells=range(-2, 3))
export_asm([('bench', b['solid'], bench_color(b['name']), en_label(b['name'])) for b in local_blk] +
           [t03(p) for p in parts],
           a3 / 'BENCH_with_TOOL03_working_pose.step', 'BENCH_TOOL03_WORK', tol=0.05, ang=0.2)

# ---------------------------------------------------------------- D-09 (tool 02 outline)
F9 = 'D-09_Tool02_Outline'
drawings(F9, ['D-09_R03_1of1'])
p9 = mk(F9, '3D_parts')
seen = set()
t02 = S.tool02()
for n, s, g in t02:
    nm = NAME02[n]
    if nm not in seen:
        seen.add(nm)
        export_shape(s, p9 / f'{nm}.step')
log['D-09 parts'] = len(seen)
export_asm([(NAME02[n], s, COL02.get(n)) for n, s, g in t02], mk(F9, '3D_assembly') / 'TOOL02_R03_outline_assembly.step',
           'TOOL02_R03', tol=0.1, ang=0.25)

# ---------------------------------------------------------------- D-01 (layout, tools parked in the rack)
F1 = 'D-01_Layout'
drawings(F1, ['D-01_R03_1of1'])
p1 = mk(F1, '3D_parts')
park = S.layout(gantry_x=3000.0, gantry_y=600.0, z_tilt=S.RACK['z_top'] + 300 + S.TILT_TO_CUP)
rack = S.rack_tools(parts)
bucket = OrderedDict()
for d in park:
    if d['group'] == 'station':
        key = next((v for k, v in STATION01.items() if d['name'].startswith(k)), 'stations_other')
    else:
        key = GROUP01[d['group']]
    bucket.setdefault(key, []).append(d['solid'])
bucket['tool01_envelope_team_design'] = [d['solid'] for d in rack if d['group'] == 'tool01']
for k, ss in bucket.items():
    export_shape(comp(ss), p1 / f'{k}.step')
log['D-01 parts'] = len(bucket)
col_by_name = {p['name']: p['color'] for p in parts}


def rack_color(d):
    if d['group'] == 'tool03':
        return col_by_name.get(d['name'][3:], '#a7b0b6')
    if d['group'] == 'tool02':
        return COL02.get(d['name'][3:], COLG['tool02'])
    return COLG.get(d['group'], '#a7b0b6')


export_asm([(d['group'], d['solid'], COLG.get(d['group']), item_label(d['group'], d['name'])) for d in park] +
           [(d['group'], d['solid'], rack_color(d), item_label(d['group'], d['name'])) for d in rack],
           mk(F1, '3D_assembly') / 'LAYOUT_R03_tools_parked.step', 'LAYOUT_R03', tol=0.5, ang=0.3)

# ---------------------------------------------------------------- 00_ALL: complete assembly in the working pose
FA = '00_ALL'
work = S.layout(gantry_x=BX, gantry_y=BY, z_tilt=S.ZC + S.TILT_TO_CUP, with_cells=True)
bl_world = [dict(b, solid=b['solid'].translate(cq.Vector(BX, BY, S.ZC))) for b in blk]
# pocket the simplified bench platform / pack cooling plate where the detailed target block sits
xs = [b['solid'].BoundingBox() for b in bl_world if b['name'] in ('비금속 상판', '코일 지지판')]
px0, px1 = min(b.xmin for b in xs), max(b.xmax for b in xs)
py0, py1 = min(b.ymin for b in xs), max(b.ymax for b in xs)
pz0 = min(b.zmin for b in xs)
pocket = T.bx(px0, px1, py0, py1, pz0, S.ZC)
items = []
for d in work:
    s = d['solid']
    if d['name'] in ('가열 작업대 (코일 구역부)', '냉각판 (팩 바닥)'):
        s = s.cut(pocket)
    items.append((d['group'], d['name'], s))
for d in S.rack_tools(parts):
    if d['group'] in ('tool01', 'tool02'):
        items.append((d['group'], d['name'], d['solid']))
col_by_no = {}
for p in parts:
    col_by_no.setdefault(p['no'], p['color'])
for p in parts:
    if p['no'] == 'CM-03':
        continue                                   # tilt unit already part of the gantry head
    items.append(('tool03', p['no'], p['solid'].translate(cq.Vector(BX, BY, S.ZC))))
for b in bl_world:
    items.append(('bench_block', b['name'], b['solid']))


def item_color(g, n):
    if g == 'tool03':
        return col_by_no.get(n, '#a7b0b6')
    if g == 'bench_block':
        return bench_color(n)
    if g in ('tool01', 'tool02'):
        return rack_color(dict(group=g, name=n))
    if g == 'pack' and n.startswith('셀'):
        return COLG['cells']
    return COLG.get(g, '#a7b0b6')


a0 = mk(FA)
export_asm([(g, s, item_color(g, n), item_label(g, n)) for g, n, s in items], a0 / 'CTP_R03_complete_assembly_working_pose.step',
           'CTP_R03_COMPLETE', tol=0.3, ang=0.3)
# static overlap check of the complete assembly (bbox pre-filter)
bbs = [s.BoundingBox() for g, n, s in items]
clash = []
for i in range(len(items)):
    for j in range(i + 1, len(items)):
        a, b = bbs[i], bbs[j]
        if a.xmax <= b.xmin or b.xmax <= a.xmin or a.ymax <= b.ymin or b.ymax <= a.ymin or a.zmax <= b.zmin or b.zmax <= a.zmin:
            continue
        try:
            v = items[i][2].intersect(items[j][2]).Volume()
        except Exception:
            v = -1
        if v > 0.5 or v < 0:
            clash.append(dict(a=f'{items[i][0]}:{items[i][1]}', b=f'{items[j][0]}:{items[j][1]}', volume_mm3=round(v, 1)))
log['complete assembly solids'] = len(items)
log['complete assembly static overlaps (> 0.5 mm3)'] = clash
# video, all drawings, reports
shutil.copy(HERE / 'video' / 'CTP_R03_process_concept.mp4', a0 / 'CTP_R03_process_concept_video.mp4')
shutil.copy(DWG / 'CTP_R03_drawings_all.pdf', a0 / 'CTP_R03_drawings_all_12_sheets.pdf')
for ext in ('pdf', 'xlsx'):
    shutil.copy(DWG / f'KS_적용_근거표_D-04_R03.{ext}', a0 / f'D-04_KS_rationale_R03.{ext}')
src = mk(FA, 'source')
for f in ['tool03_r03.py', 'ks_spec.py', 'bench_r03.py', 'scene_r03.py', 'run_checks.py', 'strength_review.py',
          'export_r03.py', 'video_r03.py', 'make_rationale.py', 'package_r03.py', 'mesh_export.py']:
    shutil.copy(HERE / f, src / f)
srcd = mk(FA, 'source', 'drawings')
for f in ['common.py', 'draw_lib.py', 'd01.py', 'd02.py', 'd03.py', 'd04ks.py', 'd09.py', 'verify_drawings.py']:
    shutil.copy(HERE / 'drawings' / f, srcd / f)
# process sequence (steps 4-10 with tools 01/02/03), browser simulation and explainer page sources
for f in ['process_r03.py', 'process_figs.py', 'process_steps_r03.py', 'process_storyboard.py', 'names_r03.py']:
    shutil.copy(HERE / f, src / f)
srcs = mk(FA, 'source', 'sim')
for f in ['export_scene.py', 'sim.js', 'sim.css', 'sim.html']:
    shutil.copy(HERE / 'sim' / f, srcs / f)
srce = mk(FA, 'source', 'explain')
for f in ['page.html', 'make_page.py', 'build.py', 'content.py', 'scenes.py', 'r3d.py', 'dump_marks.py',
          'capture_process.py', 'process_assets.py', 'make_standalone.py']:
    shutil.copy(HERE / 'explain' / f, srce / f)

# ---------------------------------------------------------------- Process_Sequence (figures, storyboard, per-step STEP)
PROC = HERE / 'process'
if PROC.exists():
    FP = 'Process_Sequence'
    pf = mk(FP, 'figures')
    for f in sorted((PROC / 'figs').glob('P*.png')):
        shutil.copy(f, pf / f'CTP_R03_process_{f.name}')
    shutil.copytree(PROC / 'storyboard', mk(FP) / 'storyboard')
    ps = mk(FP, 'STEP_per_step')
    for f in sorted((PROC / 'step').glob('*.step')):
        shutil.copy(f, ps / f.name)
    shutil.copy(PROC / 'step' / 'process_steps_check.json', mk(FP) / 'process_steps_check.json')
    pp = mk(FP, 'poses')
    for f in sorted((PROC / 'poses').glob('P*.json')):
        shutil.copy(f, pp / f.name)
    shutil.copy(PROC / 'figs' / 'meta.json', pp / 'figures_meta.json')
    shutil.copytree(PROC / 'tools_01_02_STEP', mk(FP) / 'tools_01_02_STEP')
    (mk(FP) / 'README_KR.txt').write_bytes(b'\xef\xbb\xbf' + (PROC / 'README_KR.txt').read_text(encoding='utf-8').encode('utf-8'))
    chk = json.loads((PROC / 'step' / 'process_steps_check.json').read_text(encoding='utf-8'))
    log['process sequence'] = dict(figures=len(list(pf.glob('*.png'))), step_files=len(list(ps.glob('*.step'))),
                                   readback_all_valid=all(r['readback_valid'] for r in chk),
                                   overlaps={r['id']: [f"{c['kind']}: {c['a']} / {c['b']} {c['volume_mm3']} mm3" for c in r['overlaps']] for r in chk})
# standalone explainer page (one HTML file, opens offline; its download links point into this folder tree)
xp = HERE / 'explain' / 'dist' / 'CTP_R03_explainer.html'
if xp.exists():
    shutil.copy(xp, ROOT / xp.name)
    log['explainer html'] = dict(file=xp.name, bytes=xp.stat().st_size)
readme = HERE / 'README_KR.txt'
if readme.exists():
    (a0 / 'README_KR.txt').write_bytes(b'\xef\xbb\xbf' + readme.read_text(encoding='utf-8').encode('utf-8'))
rep = mk(FA, 'reports')
for f in ['R03_checks.json', 'R03_mass_table.csv', 'R03_parts_list.csv', 'R03_strength_review.csv',
          'R03_strength_review.json', 'R03_change_log.md']:
    shutil.copy(HERE / f, rep / f)
shutil.copy(DWG / 'R03_drawing_checks.json', rep / 'R03_drawing_checks.json')
log['viewer_files (GLB/STL per assembly)'] = MESH
(rep / 'package_build_log.json').write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(log, ensure_ascii=False, indent=1))
