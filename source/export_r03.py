"""Export R03: STEP assembly, machined-part STEPs, parts list, preview images (model-based)."""
import json, csv, re
from pathlib import Path
import numpy as np
import cadquery as cq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import tool03_r03 as T

OUT = Path(__file__).resolve().parent
matplotlib.font_manager.fontManager.addfont('/usr/share/fonts/truetype/nanum/NanumGothic.ttf')
plt.rcParams['font.family'] = 'NanumGothic'
plt.rcParams['axes.unicode_minus'] = False
parts = T.build()
refs = T.reference()

# ascii names for STEP
seen = {}
for p in parts:
    tag = re.sub(r'[^A-Za-z0-9+\-]', '', p['name'].split(' ')[-1]) if not p['name'].isascii() else p['name']
    base = p['no'] if not tag or tag == p['no'] else f"{p['no']}_{tag}"
    seen[base] = seen.get(base, 0) + 1
    p['ascii'] = base if seen[base] == 1 else f"{base}_{seen[base]}"
asm = cq.Assembly(name='TOOL03_R03_20261014')
for p in parts:
    rgb = tuple(int(p['color'][i:i + 2], 16) / 255 for i in (1, 3, 5))
    asm.add(p['solid'], name=p['ascii'], color=cq.Color(*rgb))
asm.export(str(OUT / 'TOOL03_R03_assembly.step'))
ref_asm = cq.Assembly(name='REF_CELLS_R03_ASSUMED')
for i, r in enumerate(refs):
    rgb = tuple(int(r['color'][k:k + 2], 16) / 255 for k in (1, 3, 5))
    ref_asm.add(r['solid'], name=f'REF_{i:02d}', color=cq.Color(*rgb))
ref_asm.export(str(OUT / 'REF_cells_R03_assumed.step'))
(OUT / 'parts').mkdir(exist_ok=True)
done = set()
for p in parts:
    if p['kind'] == '가공' and p['no'] not in done:
        cq.exporters.export(p['solid'], str(OUT / 'parts' / f"{p['no']}.step"))
        done.add(p['no'])
# re-read check
rb = cq.importers.importStep(str(OUT / 'TOOL03_R03_assembly.step'))
solids = rb.solids().vals()
readback = {'solids': len(solids), 'all_valid': all(s.isValid() for s in solids)}
with open(OUT / 'R03_parts_list.csv', 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['step_name', 'part_no', 'name', 'kind', 'material', 'group', 'volume_mm3', 'note'])
    for p in parts:
        w.writerow([p['ascii'], p['no'], p['name'], p['kind'], p['mat'], p['group'], round(p['solid'].Volume(), 1), p['note']])
(OUT / 'R03_step_readback.json').write_text(json.dumps(readback, indent=1))
print('readback', readback)

# ------------------------------------------------------------------ previews
def mesh(s):
    v, t = s.tessellate(0.6, 0.2)
    return np.array([x.toTuple() for x in v]), np.array(t)


M = {p['name']: mesh(p['solid']) for p in parts}
R = {r['name']: mesh(r['solid']) for r in refs}
LIGHT = np.array([.3, -.6, 1.]) / np.linalg.norm([.3, -.6, 1.])


def draw(ax, verts, tri, color, alpha, offset=np.zeros(3), rot=None):
    if len(tri) == 0:
        return
    vv = verts.copy()
    if rot is not None:
        vv = rot(vv)
    faces = (vv + offset)[tri]
    n = np.cross(faces[:, 1] - faces[:, 0], faces[:, 2] - faces[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-10)
    shade = .62 + .38 * np.maximum(n @ LIGHT, 0)
    fc = shade[:, None] * np.array(matplotlib.colors.to_rgb(color))[None, :]
    ax.add_collection3d(Poly3DCollection(faces, facecolors=np.clip(fc, 0, 1), alpha=alpha, edgecolor='none', linewidths=0))


def setlim(ax, lims, elev=22, azim=-58):
    for a, l in zip('xyz', lims):
        getattr(ax, 'set_' + a + 'lim')(l)
    ax.set_box_aspect([b - a for a, b in lims])
    ax.view_init(elev, azim)
    ax.set_axis_off()


def scene(ax, mode):
    for p in parts:
        n = p['name']
        a = 1.0
        off = np.zeros(3)
        if mode == 'internal' and (p['no'] in ('03-003', '03-208', '03-108', '03-209', '03-210', '03-211', '03-011', '03-109', '03-110') or p['group'] == 'common'):
            continue
        if mode == 'exploded':
            if p['group'] == 'common' and p['no'].startswith('CM'):
                continue
            off = np.array(p['explode'], float) * 1.0
        if mode in ('assembly', 'internal') and p['no'] == '03-002':
            a = .18
        if mode == 'assembly' and p['no'] == '03-003':
            a = .35
        if mode == 'internal' and p['no'] == '03-001':
            a = .30
        draw(ax, *M[n], p['color'], a, off)
    if mode in ('assembly',):
        for r in refs:
            if r['name'].startswith(('REF_셀', 'REF_단자', 'REF_버스바', 'REF_패드')) and 'X이웃' not in r['name']:
                draw(ax, *R[r['name']], r['color'], .25 if not r['name'].endswith('+0') else .55)


fig = plt.figure(figsize=(18, 10), facecolor='#f5f7fa')
titles = {'assembly': '01  전체 조립 (셀·단자 가정 포함)', 'internal': '02  내부 배치 (상판·로드셀 제외)', 'exploded': '03  분해 배치'}
lims = {'assembly': ((-110, 110), (-80, 80), (-95, 300)), 'internal': ((-85, 85), (-72, 72), (-2, 152)),
        'exploded': ((-120, 120), (-100, 100), (-130, 520))}
for i, mode in enumerate(('assembly', 'internal', 'exploded')):
    ax = fig.add_subplot(1, 3, i + 1, projection='3d')
    ax.set_facecolor('#f5f7fa')
    scene(ax, mode)
    setlim(ax, lims[mode], 20 if mode != 'internal' else 30, -58 if mode != 'internal' else -62)
    ax.set_title(titles[mode], fontsize=14, color='#25384a', pad=12)
fig.suptitle('03 셀 분리 공구 / R03 · 체결·배관 구체화 3D 조립안', fontsize=22, y=.95, color='#183548')
fig.text(.5, .085, '상판 구조화(M4×6) · 컵 직선 호스(R16) · IR 분할 클램프 볼트 · 노즐 블록 하우징 바닥 이전 · 진공 유닛 2 · 로드셀/어댑터/교환기 패턴(가정)', ha='center', fontsize=12, color='#334b5c')
fig.text(.5, .045, '실제 CAD 솔리드에서 생성한 미리보기 · 모든 치수는 설계 가정 · 정지 상태 겹침/접근 공간 검사만 수행 · 제작 승인 전', ha='center', fontsize=10, color='#6a7078')
plt.subplots_adjust(left=.01, right=.99, bottom=.12, top=.88, wspace=.02)
fig.savefig(OUT / 'TOOL03_R03_preview.png', dpi=130)
plt.close(fig)

# cell top layout (plan view, Z-projection) with cups, IR spot, terminals, vent
fig, ax = plt.subplots(figsize=(10, 4.6), facecolor='white')
from matplotlib.patches import Rectangle, Ellipse, Circle
L, Tt, H = T.P['cell']
for i in (-1, 0, 1):
    yc = i * T.P['pitch_y']
    ax.add_patch(Rectangle((-L / 2, yc - Tt / 2), L, Tt, fc='#dfe9ef' if i else '#c7dce8', ec='#476070', lw=1))
    for sx in (-1, 1):
        ax.add_patch(Rectangle((min(sx * 58, sx * 70), yc - 8), 12, 16, fc='#e8d2a6', ec='#8a6a2e', lw=.8))
    ax.add_patch(Circle((0, yc), 7, fc='white', ec='#888', lw=.8, ls='--'))
for x in (-40, 40):
    ax.add_patch(Ellipse((x, 0), 30, 20, fc='#3b4248', alpha=.35, ec='#222', lw=1))
    ax.add_patch(Rectangle((x - 20, -10), 40, 20, fc='none', ec='#5b6b75', lw=.8, ls=':'))
ax.add_patch(Circle((12, 0), 3, fc='#d9534f', alpha=.6, ec='#a33'))
ax.add_patch(Rectangle((-70, -12), 140, 24, fc='none', ec='#b08a4f', lw=1.2, ls='-.'))
for tag, (x, y) in T.P['nozzle_xy'].items():
    ax.add_patch(Circle((x, y), 1.25, fc='#4ca6b8'))
    ax.add_patch(Rectangle((x - 13, y - 8), 26, 16, fc='none', ec='#4ca6b8', lw=.8, ls='--'))
ax.annotate('단자 가정 |X|58~70, 높이3 + 버스바 잔여2', (64, 8), (80, 30), fontsize=9, arrowprops=dict(arrowstyle='-', lw=.6))
ax.annotate('벤트 가정 Ø14', (0, 7), (-30, 40), fontsize=9, arrowprops=dict(arrowstyle='-', lw=.6))
ax.annotate('IR 광점 가정 Ø6 (X=12)', (12, 3), (10, 22), fontsize=9, arrowprops=dict(arrowstyle='-', lw=.6))
ax.annotate('컵 30×20 (X=±40) / 브래킷 40×20 (점선)', (-40, -10), (-120, -36), fontsize=9, arrowprops=dict(arrowstyle='-', lw=.6))
ax.annotate('노즈 140×24 (일점쇄선)', (-60, -12), (-125, 20), fontsize=9, arrowprops=dict(arrowstyle='-', lw=.6))
ax.annotate('노즐 블록 토출 Ø2.5 → 이웃 셀', (-55, -31), (-130, -48), fontsize=9, arrowprops=dict(arrowstyle='-', lw=.6))
ax.set_xlim(-135, 135); ax.set_ylim(-50, 50); ax.set_aspect('equal'); ax.grid(alpha=.15)
ax.set_title('셀 상면 배치 가정 (Z 투영, mm) — 단자·벤트·광점 위치는 실제 셀 도면 확인 전 가정', fontsize=11)
fig.tight_layout(); fig.savefig(OUT / 'R03_cell_top_layout.png', dpi=150); plt.close(fig)
print('previews done')
