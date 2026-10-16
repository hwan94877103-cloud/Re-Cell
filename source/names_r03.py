"""Shared ASCII part names and colours for STEP/GLB exports (copied from package_r03.py so that other builders
can use them without running the package build)."""
from collections import OrderedDict

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

NAME02 = {'Ø80 흡착컵': 'suction_cup_D80', '컵 스프링 홀더': 'cup_spring_holder', '프레임 (40×40)': 'frame_profile_40x40',
          '중앙 허브판': 'hub_plate', '어댑터판': 'adapter_plate', '교환기 툴 플레이트': 'changer_tool_plate_D100',
          '통과 모듈 툴측': 'pass_through_module_tool_side', '공압 슬라이드 (스트로크 80)': 'pneumatic_slide_stroke80',
          '절단 스핀들 Ø40': 'cutting_spindle_D40', '엔드밀 Ø6': 'end_mill_D6', '칩 흡입 후드 Ø40': 'chip_suction_hood_D40',
          '칩 흡입 호스 Ø25': 'chip_suction_hose_D25', '냉각수 흡입 노즐 Ø10': 'coolant_suction_nozzle_D10'}


def label(g, n, no_by_name=None):
    """ASCII label for an item of group g with (Korean) name or part number n (see package_r03.item_label)."""
    if g == 'tool03':
        key = n[3:] if n.startswith('03 ') else n
        no = key if key in NAME03 else (no_by_name or {}).get(key)
        return f'tool03_{no}_{NAME03[no]}' if no else 'tool03'
    if g == 'tool02':
        e = NAME02.get(n[3:] if n.startswith('02 ') else n, '')
        return f'tool02_{e}' if e else 'tool02'
    e = en_label(n)
    if not e:
        return g
    return e if e.startswith(g) else f'{g}_{e}'
