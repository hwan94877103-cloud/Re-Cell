"""D-01 전체 구조·공정 배치도 (R03) from scene_r03 (layout solids are assumed envelopes).
1:50 (KS 권장 척도 계열) - 평면도, 정면도(펜스 생략), 단면 B-B (X 2610, -X 방향)."""
import numpy as np
import cadquery as cq

from common import T, load, DATE, WORK, STATUS, TEAM, HERE
import scene_r03 as S
import draw_lib as DL
from draw_lib import Sheet, View, project, dedupe

n_pic = np.array([-0.9, -1.6, 1.25]) / np.linalg.norm([-0.9, -1.6, 1.25])
DL.VIEWDIR['pic01'] = (tuple(n_pic), tuple(np.array([-n_pic[1], n_pic[0], 0.0]) / np.linalg.norm(n_pic[:2])))

OUT = HERE / 'out'
parts, QTY, ITEM = load()
TB = dict(work=WORK, dwg_no='D-01', date=DATE, rev='R03', status=STATUS, team=TEAM)
BX, BY = S.local_offset()
GX, GY = BX, BY                       # gantry over the target cell (tool axis = local X0, Y0)
ZT = S.ZC + S.TILT_TO_CUP             # tilt axis at the working height
XB = 2610.0                           # section B-B plane (gap between bench end 2600 and rack 2620)


def world_tool03():
    return [S.W(p['solid'], BX, BY, S.ZC) for p in parts]


def sheet():
    sh = Sheet()
    sh.frame()
    sh.title_block(dict(TB, title='전체 구조 및 공정 배치도', scale='1:50', sheet='1/1'))
    L = S.layout(gantry_x=GX, gantry_y=GY, z_tilt=ZT)
    R = S.rack_tools(parts)
    tool = world_tool03()
    g = lambda *gs: [d['solid'] for d in L if d['group'] in gs]
    sc = 1 / 50
    X0 = 45.0
    # ---------------- plan view (top)
    vp = View(sh, 'top', sc, (X0, 197))
    vp.outline(g('fence', 'conveyor', 'bench', 'pack', 'gantry', 'rack', 'station') + [d['solid'] for d in R])
    pv, _ = project(g('moving') + tool, 'top')
    vp.draw_prims(dedupe(pv), 'PHANTOM')
    tv, _ = project([d['solid'] for d in L if d['group'] == 'top' and d['name'] != '가스 감지기'], 'top')
    vp.draw_prims(dedupe(tv), 'HIDDEN')
    vp.outline([d['solid'] for d in L if d['name'] == '가스 감지기'])
    sh.text('평면도', (24, 262), 3.5)
    # ---------------- front view (from -Y), fence omitted (phantom outline)
    vf = View(sh, 'front', sc, (X0, 67))
    vf.outline(g('conveyor', 'bench', 'pack', 'gantry', 'rack', 'station', 'top', 'moving') + [d['solid'] for d in R] + tool)
    vf.phantom_poly([(0, 0), (0, 2000), (5400, 2000), (5400, 0)])
    sh.line(vf.P(-950, 0), vf.P(5500, 0), 'OUTLINE')
    sh.text('정면도 (펜스 생략)', (24, 140), 3.5)
    # ---------------- section B-B (X = 2610, looking -X), fence omitted
    vs = View(sh, 'right', sc, (196, 67))
    rails = [d['solid'] for d in L if d['name'] == 'X 레일 빔']
    whole = [d['solid'] for d in L if d['group'] not in ('fence',) and d['name'] != 'X 레일 빔'] + \
            [d['solid'] for d in R] + tool
    vs.section([], (XB, 0, 0), rails, whole, hatch_specs={0: dict(angle=45, spacing=1.0), 1: dict(angle=45, spacing=1.0)})
    sh.line(vs.P(-1550, 0), vs.P(1550, 0), 'OUTLINE')
    sh.view_label('단면 B-B (펜스 생략)', (196, 152))
    sh.cutline(vp.P(XB, -1500), vp.P(XB, 1500), 'B', (-1, 0), ext=3.0, thick=4.0)
    # ---------------- dimensions
    vp.dim((0, 1500), (5400, 1500), at=vp.P(0, 1500)[1] + 6)
    vp.dim((5400, -1500), (5400, 1500), at=vp.P(5400, 0)[0] + 6, orient='v')
    x_r = vs.P(1500, 0)[0]
    vs.dim((1080, 0), (771, S.ZC), at=vs.P(1080, 0)[0], orient='v')
    vs.dim((1425, 0), (1425, S.RAIL_Z[1]), at=x_r + 4, orient='v')
    top_eq = [d['solid'] for d in L if d['group'] == 'top' and d['name'] != '가스 감지기']
    z_bot = min(s.BoundingBox().zmin for s in top_eq)
    z_top = max(s.BoundingBox().zmax for s in top_eq)
    y_hood = max(s.BoundingBox().ymax for s in top_eq if abs(s.BoundingBox().zmin - z_bot) < 1e-6)
    y_duct = max(s.BoundingBox().ymax for s in top_eq if abs(s.BoundingBox().zmax - z_top) < 1e-6)
    vs.dim((1425, 0), (y_hood, z_bot), at=x_r + 10, orient='v')
    vs.dim((1425, 0), (y_duct, z_top), at=x_r + 16, orient='v')
    vs.dim((-S.RAIL_Y, S.RAIL_Z[1]), (S.RAIL_Y, S.RAIL_Z[1]), at=vs.P(0, 2450)[1] + 9, text='<> 레일 간격')
    # ---------------- pictorial (reference, fence omitted, no scale)
    pic = [d['solid'] for d in L if d['group'] != 'fence'] + [d['solid'] for d in R] + \
          [S.W(p['solid'], BX, BY, S.ZC) for p in parts if p['kind'] in ('가공', '구매', '공통') and not p['no'].startswith('03-2')]
    vis, _ = project(pic, 'pic01')
    vtmp = View(sh, 'pic01', 1.0, (0, 0))
    us, vs_ = [], []
    for pr in vis:
        from draw_lib import prim_points
        for q in prim_points(pr, 0.002):
            us.append(q[0]); vs_.append(q[1])
    u0, u1, v0, v1 = min(us), max(us), min(vs_), max(vs_)
    k = min(150.0 / (u1 - u0), 86.0 / (v1 - v0))
    vI = View(sh, 'pic01', k, (322.0, 66.0 + 0.5 * (v1 - v0) * k), ref=((u0 + u1) / 2, (v0 + v1) / 2))
    vI.draw_prims(dedupe(vis), 'OUTLINE')
    sh.view_label('참고 입체도 (펜스 생략, 척도 없음)', (322, 66.0 + (v1 - v0) * k + 4.0))
    sh.lines_of_text(['갠트리 이동 범위 (가정): X 4050 (350~4400), Y 1800 (±900), Z 800',
                      'Z축 가반하중 40 kg급, Z축 끝 회전축(θ) + 기울임축 (셀 두께 방향과 평행)'], (24, 27), h=2.3, gap=1.6)
    # ---------------- balloons
    items = [
        (2, vp, (-400, 600), (30, 244)), (3, vp, (330, 860), (42, 244)),
        (8, vp, (2650, 330), (78, 244)), (19, vp, (2720, 600), (88, 244)), (17, vp, (2900, 600), (98, 244)),
        (16, vp, (2900, 1200), (108, 244)), (18, vp, (3350, 750), (118, 244)), (14, vp, (4300, 300), (140, 244)),
        (1, vp, (600, -1490), (30, 156)), (4, vp, (600, -700), (42, 156)),
        (20, vp, (2700, -1420), (90, 156)), (9, vp, (2830, -100), (100, 156)), (10, vp, (3250, -100), (110, 156)),
        (11, vp, (2800, -700), (120, 156)), (12, vp, (3150, -700), (130, 156)), (13, vp, (3480, -700), (140, 156)),
        (15, vs, (0, 3305), (172, 143)), (6, vs, (-1000, 2375), (182, 143)), (7, vs, (GY, 1800), (192, 143)),
        (5, vs, (1350, 2225), (222, 143)),
    ]
    for n, v_, uv, bp in items:
        sh.balloon(n, bp, v_.P(*uv))
    legend = [['1', '안전 펜스'], ['2', '팩 입고 컨베이어'], ['3', '가열 작업대 (비금속 상판·구역 코일)'],
              ['4', '가상 CTP 팩 2200×1600 (커버 제거 후)'], ['5', 'X 레일 (갠트리)'], ['6', 'Y 브리지'],
              ['7', 'Z축·회전축·기울임축 + 03 (작업 위치)'], ['8', '공구 거치대'], ['9', '셀 측정대 (전압·절연)'],
              ['10', '비상 침수조 400×300×300'], ['11', '회수함: 나사·칩'], ['12', '회수함: 전장품'],
              ['13', '셀 회수함 (재사용/재활용)'], ['14', '커버 거치대'], ['15', '상부 고정 프레임 (카메라·열화상·배기)'],
              ['16', '냉각수 회수 탱크'], ['17', '03 셀 분리 공구'], ['18', '02 절단·흡착 공구'],
              ['19', '01 나사 해체 헤드 (팀원 설계)'], ['20', '가스 감지기']]
    sh.text('구성 (모두 가정 배치)', (250, 279), 2.6)
    sh.table(248, 276, [8, 70], ['번', '이름'], legend, rh=4.6, hh=5.5, h=2.1, align=['C', 'L'])
    proc = [['입고', 'HV 차단·진단, 하부 보호판 제거', '범위 밖', '2'],
            ['4', '나사 해체 → 실링 절단 → 커버 인양', '01→02', '14'],
            ['5', '배선 제거, 버스바 절단·칩 흡입', '01/02', '11'],
            ['6', '전장품 분리', '01', '12'],
            ['7', '냉각수 흡입 → 압축 공기 퍼지', '02', '16'],
            ['9', '흡착 → 구역 가열 → 필링 → 이송', '03', '3'],
            ['10', '셀 전압·절연 측정 → 분류', '측정대', '9→13'],
            ['비상', '온도·가스 이상 → 가열 off → 침수조', '03', '10']]
    sh.text('공정 (v0.3 + R03, 8단계 모듈 인출 없음)', (330, 279), 2.6)
    yp = sh.table(330, 276, [9, 45, 12, 10], ['단계', '작업', '공구', '위치'], proc, rh=6.2, hh=5.5, h=2.0,
                  align=['C', 'L', 'C', 'C'])
    sh.lines_of_text([
        '주기',
        '1. 배치·치수·이동 범위는 모두 가정 (개념 배치도).',
        '2. 갠트리 브리지·Z축·03은 작업 위치. 평면도는 가상선.',
        '3. 평면도의 상부 장비(카메라·열화상·배기 후드)는 숨은선.',
        f'4. 상부 장비 아랫면 {z_bot:.0f} > Z 램 최고 위치 약 3094.',
        '   상부 장비 지지 구조(천장 고정 등)는 미표시.',
        f'5. 작업면(셀 윗면) 높이 {S.ZC:.0f} = 커버 거치대 윗면.',
        '6. 01은 팀원 설계 - 외형 박스만 표시.',
        '7. 셀 전압 측정은 03에서 분리된 별도 측정대.',
        '8. 비상 대응·배기량·감지 임계값은 미검증.',
        '9. 02 공구 약 10 kg(가정) + 커버 25 kg + 마스터·',
        '   기울임축 → Z축 40 kg급은 여유가 거의 없음 (검토).',
    ], (330, yp - 6), h=2.2, gap=1.55)
    return sh


if __name__ == '__main__':
    sh = sheet()
    sh.save(OUT / 'D-01_R03_1of1.dxf')
    sh.render(OUT / 'D-01_R03_1of1.pdf', OUT / 'D-01_R03_1of1.png', dpi=150)
    print('ok')
