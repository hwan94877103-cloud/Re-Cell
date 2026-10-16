"""D-09 02 공구 외형도 (R03, outline level): Ø80 cups x4 (600x400), cutting spindle on a pneumatic slide,
chip suction hood, coolant suction nozzle, changer tool plate (same interface as 03). All assumed."""
import cadquery as cq
from common import DATE, WORK, STATUS, TEAM, HERE
import scene_r03 as S
from draw_lib import Sheet, View, project, dedupe

OUT = HERE / 'out'
TB = dict(work=WORK, dwg_no='D-09', date=DATE, rev='R03', status=STATUS, team=TEAM)
SPINDLE = ('공압 슬라이드 (스트로크 80)', '절단 스핀들 Ø40', '엔드밀 Ø6', '칩 흡입 후드 Ø40', '칩 흡입 호스 Ø25', '냉각수 흡입 노즐 Ø10')


def sheet():
    sh = Sheet()
    sh.frame()
    sh.title_block(dict(TB, title='02 절단·흡착 공구 외형도', scale='1:5', sheet='1/1'))
    T2 = S.tool02()
    sol = [s for n, s, g in T2]
    moving = [s.translate(cq.Vector(0, 0, 80)) for n, s, g in T2 if n in SPINDLE and n != '공압 슬라이드 (스트로크 80)']
    sc = 0.2
    vt = View(sh, 'top', sc, (115, 222))
    vf = View(sh, 'front', sc, (115, 110))
    vr = View(sh, 'right', sc, (265, 110))
    vt.outline(sol)
    vf.outline(sol)
    vr.outline(sol)
    pv, _ = project(moving, 'front')
    vf.draw_prims(dedupe(pv), 'PHANTOM')
    for v_ in (vf, vr):
        v_.phantom_poly([(-380 if v_ is vf else -280, 0), (380 if v_ is vf else 280, 0)])
    sh.text('커버 윗면 (가상선)', vf.P(-380, -16), 2.3)
    sh.leader(vf.P(170, 140), (205, 141), '스핀들 후퇴 위치 (가상선)', h=2.3, end='dot', side=1)
    for x in (-300, 300):
        for y in (-200, 200):
            vt.cmark((x, y), 40, ext=2.0)
    vt.axis((-370, 0), (370, 0), ext=0)
    vt.axis((0, -260), (0, 260), ext=0)
    vf.axis((0, -70), (0, 200), ext=0)
    vr.axis((0, -70), (0, 200), ext=0)
    # dimensions
    vt.dim((-300, 200), (300, 200), at=vt.P(0, 240)[1] + 6)
    vt.dim((-340, 240), (340, 240), at=vt.P(0, 240)[1] + 13)
    vt.dim((-300, -200), (-300, 200), at=vt.P(-340, 0)[0] - 6, orient='v')
    vt.dim((0, 0), (150, 0), at=vt.P(0, -240)[1] - 6, text='<> (스핀들)')
    vf.dim((340, 0), (340, 185), at=vf.P(340, 0)[0] + 7, orient='v', text='<> (교환기 면)')
    vf.dim((150, -60), (150, 0), at=vf.P(340, 0)[0] + 7, orient='v')
    vr.dim((-240, 0), (240, 0), at=vr.P(0, -60)[1] - 6, text='<> (컵 외곽)')
    sh.view_label('평면도', (35, 266))
    sh.view_label('정면도', (35, 152))
    sh.view_label('우측면도', (230, 152))
    items = [(1, vt, (300, 200), (190, 262)), (2, vt, (-300, 200), (40, 252)), (3, vf, (0, 140), (60, 150)),
             (4, vf, (0, 172), (100, 150)), (5, vf, (150, 80), (178, 150)), (6, vf, (150, -30), (190, 76)),
             (7, vt, (192, 37), (200, 206)), (8, vt, (60, 0), (190, 236)), (9, vr, (0, 172), (300, 150)),
             (10, vf, (118, 40), (160, 76))]
    for n, v_, uv, bp in items:
        sh.balloon(n, bp, v_.P(*uv))
    legend = [['1', 'Ø80 흡착컵 ×4 (주름형, 가정)'], ['2', '컵 스프링 홀더 ×4'], ['3', '알루미늄 프레임 40×40'],
              ['4', '중앙 허브판·어댑터판'], ['5', '공압 슬라이드 (스트로크 80)'], ['6', '절단 스핀들 + 엔드밀 Ø6'],
              ['7', '냉각수 흡입 노즐 Ø10 (슬라이드 장착)'], ['8', '통과 모듈 툴측 (03과 동일)'], ['9', '교환기 툴 플레이트 Ø100'],
              ['10', '칩 흡입 후드 Ø40 + 호스 Ø25']]
    sh.text('구성 (외형 가정, 선정 필요)', (316, 279), 2.6)
    yl = sh.table(314, 276, [8, 84], ['번', '이름'], legend, rh=5.0, hh=5.5, h=2.2, align=['C', 'L'])
    sh.lines_of_text([
        '주기',
        '1. 외형도 수준: 내부 구조·공압 배관·배선은 표시하지 않음.',
        '2. 교환기 접속은 03과 같은 가정 규격 (Ø100, 4×M5 PCD90).',
        '3. 스핀들·후드·흡입 노즐은 한 슬라이드에 장착: 커버 흡착 시 후퇴,',
        '   버스바 절단·냉각수 흡입 시 하강 (엔드밀 끝이 컵보다 60 아래).',
        '4. 커버 약 15~25 kg (가정): Ø80 컵 4개 이상 흡착력 약 1,200 N',
        '   (v0.3 계산, 진공 -60 kPa 가정). 커버 휨·밀봉·편심은 미검토.',
        '5. 공구 질량 약 10 kg (부피 × 가정 밀도). Z축 40 kg급에',
        '   커버 25 kg를 더하면 여유가 거의 없음 → Z축 선정 시 재검토.',
        '6. 칩 낙하 시 단락 위험 → 절단 중 흡입 유지, 절연 커버 검토.',
        '7. 모든 치수 가정. 구매품(컵·스핀들·슬라이드) 선정 후 확정.',
    ], (314, yl - 7), h=2.2, gap=1.55)
    return sh


if __name__ == '__main__':
    sh = sheet()
    sh.save(OUT / 'D-09_R03_1of1.dxf')
    sh.render(OUT / 'D-09_R03_1of1.pdf', OUT / 'D-09_R03_1of1.png', dpi=150)
    print('ok')
