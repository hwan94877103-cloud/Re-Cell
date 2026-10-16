"""R03 preliminary load / fastener review. Hand-calculation level, every input is an assumption.
Not a strength verification: no FEA, no preload test, no creep/thermal analysis."""
import json, math, csv
from pathlib import Path

OUT = Path(__file__).resolve().parent
chk = json.loads((OUT / 'R03_checks.json').read_text())

A = dict(dp_kPa=60.0, cup_area_mm2=942.5 / 2, F_check_N=500.0, x_cup_mm=40.0, F_lat_N=50.0, g=9.81, a_ms2=2.0,
         tau_al_MPa=207.0, proof_MPa=580.0, K_torque=0.2)
As = {'M3': 5.03, 'M4': 8.78, 'M5': 14.2}
F_suction_ideal = A['dp_kPa'] * 1e-3 * A['cup_area_mm2'] * 2          # N, both cups, outer contour area
M_check = A['F_check_N'] * A['x_cup_mm']                                 # N.mm, check load at one cup


def bolt_group(n, xs, F, M):
    s = sum(x * x for x in xs)
    return F / n + (M * max(abs(x) for x in xs) / s if s else 0.0)


def strip_al(D, Le):
    return math.pi * D * Le * 0.75 * A['tau_al_MPa']


rows = []


def row(joint, bolts, load_case, p_max, capacity_proof, strip, note):
    rows.append(dict(joint=joint, bolts=bolts, load_case=load_case, max_bolt_load_N=round(p_max, 1),
                     proof_load_N=round(capacity_proof), al_thread_strip_N=round(strip) if strip else '',
                     ratio_to_proof=round(p_max / capacity_proof, 3), note=note))


row('노즈 플랜지-하우징 바닥', '4×M4 (8.8 가정), 바닥 나사 물림 6 (1.5d)', f'검토 하중 {A["F_check_N"]:.0f} N, 한쪽 컵 X=40',
    bolt_group(4, [60, 60, -60, -60], A['F_check_N'], M_check), As['M4'] * A['proof_MPa'], strip_al(4, 6),
    'PEEK 플랜지 크리프·열에 의한 예압 감소가 실제 지배 요인 (미검증)')
row('상판-하우징 보스', '6×M4, 물림 10', '같음', bolt_group(6, [70] * 6, A['F_check_N'], M_check), As['M4'] * A['proof_MPa'],
    strip_al(4, 10), '보스 위치 X=±70')
row('로드셀 하면-상판', '4×M5 PCD60 (가정)', '같음', bolt_group(4, [21.21, 21.21, -21.21, -21.21], A['F_check_N'], M_check),
    As['M5'] * A['proof_MPa'], None, '로드셀 나사 깊이·허용 모멘트는 구매품 사양 필요')
row('어댑터-교환기 툴', '4×M5 PCD90 (가정)', '같음', bolt_group(4, [45, -45, 0, 0], A['F_check_N'], M_check),
    As['M5'] * A['proof_MPa'], None, '교환기 허용 하중/모멘트는 구매품 사양 필요')
row('컵 브래킷-노즈 인서트', '2×M3 / 컵', f'컵 1개 이상 흡착력 {F_suction_ideal / 2:.1f} N', F_suction_ideal / 2 / 2,
    As['M3'] * A['proof_MPa'], None, '진공이 풀리면 하중이 더 전달되지 않음. 인서트 인발 강도는 공급사 값 필요')
row('노즐 블록-하우징 바닥', '2×M3, 물림 6', '공급 압력 0.6 MPa(가정) × O링 P6 홈 바깥지름 Ø9.2 면적',
    0.6 * math.pi / 4 * 9.2 ** 2 / 2, As['M3'] * A['proof_MPa'], strip_al(3, 6), 'O링 P6 압축률 26 % (규격집 36항 홈)')

mass = chk['mass']
m_tool = mass['tool03_detachable (incl. load cell, adapter, changer tool plate, module)']['mass_kg']
z_tool = mass['tool03_detachable (incl. load cell, adapter, changer tool plate, module)']['cog_mm'][2]
m_rot = m_tool + 0.9 + 0.12
z_rot = (m_tool * z_tool + 0.9 * 214 + 0.12 * 206.5) / m_rot
d_axis = 264 - z_rot
moments = {
    '이상 흡착력 합계 (60 kPa × 외곽 면적, 2컵)': f'{F_suction_ideal:.1f} N',
    '한쪽 컵에만 흡착력이 걸릴 때 로드셀 굽힘 모멘트': f'{F_suction_ideal * 0.040:.2f} N·m',
    f'검토 하중 {A["F_check_N"]:.0f} N을 한쪽 컵에 걸 때 (로드셀/교환기 굽힘)': f'{M_check / 1000:.1f} N·m',
    f'횡하중 {A["F_lat_N"]:.0f} N(가정)을 셀 상면 Z=0에 걸 때 — 로드셀 중심 Z146.5': f'{A["F_lat_N"] * 0.1465:.1f} N·m',
    '  — 교환기 접속면 Z169': f'{A["F_lat_N"] * 0.169:.1f} N·m',
    '  — 기울임축 중심 Z264': f'{A["F_lat_N"] * 0.264:.1f} N·m',
    '기울임축 아래 회전 질량 (03 + 마스터 + 모듈, 가정 포함)': f'{m_rot:.2f} kg, 무게중심 Z{z_rot:.0f} (축 아래 {d_axis:.0f} mm)',
    '자중에 의한 기울임 모멘트 3° / 15°': f'{m_rot * 9.81 * d_axis / 1000 * math.sin(math.radians(3)):.2f} / {m_rot * 9.81 * d_axis / 1000 * math.sin(math.radians(15)):.2f} N·m',
    '로드셀이 받는 공구 자중 (로드셀 아래)': f'{mass["below_load_cell (what the load cell carries as tare)"]["mass_kg"] * 9.81:.1f} N',
    '흡착력 상한 대비 로드셀 범위 500 N': f'{F_suction_ideal / 500 * 100:.0f} % — 분해능·과부하 보호를 함께 검토',
}
pad = {'가정 패드 압력 (예시)': '0.05 MPa', '가정 마찰계수': 0.3, '양면 패드 면적 148×91×2': '26,936 mm²',
       '예시 마찰력': f'{0.05 * 26936 * 0.3:.0f} N', '해석': '예시 값만으로도 이상 흡착력(약 57 N)의 수 배 — 패드 압축 해제 없이 필링 불가 가능성 (가설, 미검증)'}
torque = {'M4 PEEK 플랜지 누름판 예압 제안 (가정)': '1.5~2.0 kN → 약 1.2~1.6 N·m (K=0.2 가정), 접시스프링 와셔 검토',
          'M3 클램프·브래킷': '센서/인서트 공급사 허용 토크 우선'}
res = dict(assumptions=A, joints=rows, moments=moments, pad_friction_example=pad, torque_proposal=torque)
(OUT / 'R03_strength_review.json').write_text(json.dumps(res, ensure_ascii=False, indent=1))
with open(OUT / 'R03_strength_review.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
print(json.dumps(res, ensure_ascii=False, indent=1))
