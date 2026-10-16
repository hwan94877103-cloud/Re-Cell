"""Concept animation of the 03 cell separation sequence (R03 geometry, assumed layout). Not a simulation.
Renders with pyvista (VTK offscreen), captions with PIL (NanumGothic), encodes H.264 MP4 with ffmpeg."""
import math
import sys
from pathlib import Path

import numpy as np
import pyvista as pv
import cadquery as cq
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tool03_r03 as T
import bench_r03 as BM
import scene_r03 as S

FPS = 20
W_, H_ = 1280, 720
FONT = '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'
FONT_B = '/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf'
OUT = HERE / 'video'
OUT.mkdir(exist_ok=True)

BX, BY = S.local_offset()
RACK3 = (S.RACK['st']['03'][0], S.RACK['st']['03'][1], S.RACK['z_top'] - 58.0)   # tool local origin when parked
ZT_WORK = S.ZC + S.TILT_TO_CUP
ZT_RACK = RACK3[2] + S.TILT_TO_CUP
ZT_TRAVEL = 1720.0
MEAS = (2825.0, -100.0)
ZT_MEAS = 905.0 + 91.0 + S.TILT_TO_CUP
PIVOT = np.array([-BM.CELL_L / 2, 0.0, -BM.CELL_H])
TILT_C = np.array([0.0, 0.0, S.TILT_TO_CUP])


def mesh(solid, tol=0.4, ang=0.35):
    v, t = solid.tessellate(tol, ang)
    pts = np.array([[p.x, p.y, p.z] for p in v], float)
    faces = np.hstack([np.r_[3, tri] for tri in t]).astype(np.int64)
    return pv.PolyData(pts, faces)


def merge(meshes):
    m = meshes[0].copy()
    for x in meshes[1:]:
        m = m.merge(x)
    return m


def Mtrans(d):
    M = np.eye(4)
    M[:3, 3] = d
    return M


def Mrot_y_neg(deg, about):
    """Rotation about an axis parallel to -Y through 'about' (positive lifts the +X end)."""
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    R = np.array([[c, 0, -s], [0, 1, 0], [s, 0, c]])      # rotation about -Y
    M = np.eye(4)
    M[:3, :3] = R
    M[:3, 3] = about - R @ about
    return M


def ease(t):
    t = min(max(t, 0.0), 1.0)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return np.asarray(a, float) + (np.asarray(b, float) - np.asarray(a, float)) * t


# ============================================================================ build scene
def build():
    tool = T.build()
    lay = S.layout(gantry_x=0.0, gantry_y=0.0, z_tilt=S.TILT_TO_CUP, with_cells=True)
    rack = S.rack_tools(tool)
    actors = {}
    statics = {}

    def st(key, solid, tol=2.0):
        statics.setdefault(key, []).append(mesh(solid, tol, 0.5))

    for d in lay:
        g = d['group']
        if g == 'moving':
            continue
        if g == 'fence':
            st('fence', d['solid'])
        elif g == 'pack':
            st('block' if d['name'].startswith('셀 블록') else 'pack', d['solid'])
        elif g in ('bench', 'conveyor'):
            st('bench', d['solid'])
        elif g == 'gantry':
            st('gantry', d['solid'])
        elif g == 'top':
            st('top', d['solid'])
        else:
            st('station', d['solid'])
    for d in rack:
        if d['group'] == 'tool02':
            st('tool02', d['solid'], 1.0)
        elif d['group'] == 'tool01':
            st('tool01', d['solid'], 1.0)
    # moving gantry pieces at reference position (gx = gy = 0, tilt centre at local Z 264)
    mv = {d['name']: d['solid'] for d in lay if d['group'] == 'moving'}
    bridge = mesh(mv['Y 브리지'], 2.0)
    carriage = mesh(mv['Z 캐리지'], 2.0)
    upper = merge([mesh(mv[n], 1.0) for n in ('Z 램', '회전축 (θ)', '근접 카메라 + 링 조명')])
    tilt = mesh(mv['기울임축 유닛'], 0.5)
    cm = merge([mesh(p['solid'], 0.5) for p in tool if p['no'] in ('CM-01', 'CM-02')])
    # tool 03 (local), grouped by colour
    tcol = {}
    for p in tool:
        if p['no'].startswith('CM'):
            continue
        tcol.setdefault(p['color'], []).append(mesh(p['solid'], 0.3, 0.3))
    tool_meshes = {c: merge(ms) for c, ms in tcol.items()}
    # target block cells (world): individual cells in the target block, target cell separate
    bl = BM.bench(rows=(0, 1), cells=BM.CELL_J)
    cells, terms, target, neigh = [], [], [], []
    for b in bl:
        n = b['name']
        s = b['solid'].translate(cq.Vector(BX, BY, S.ZC))
        if n.endswith(' A+0') and (n.startswith('셀') or n.startswith('단자') or n.startswith('잔여')):
            target.append((n, mesh(s, 0.5)))
        elif n.startswith('셀 A+1') or n.startswith('셀 A-1'):
            neigh.append(mesh(s, 0.5))
        elif n.startswith('셀 '):
            cells.append(mesh(s, 1.0))
        elif n.startswith('단자') or n.startswith('잔여'):
            terms.append(mesh(s, 1.0))
        elif n.startswith('압축 패드'):
            terms.append(mesh(s, 1.0))
    statics['cells'] = cells
    statics['terms'] = terms
    return dict(statics={k: merge(v) for k, v in statics.items()}, bridge=bridge, carriage=carriage, upper=upper,
                tilt=tilt, cm=cm, tool=tool_meshes, target=target, neigh=merge(neigh))


COL = dict(fence='#c9d3da', block='#4d5961', pack='#7c8790', bench='#9aa5ad', gantry='#d9822b', top='#8a96a0',
           station='#a7b4bd', tool02='#6f8fa6', tool01='#b0a16f', cells='#7fa3b8', terms='#c49a62')


# ============================================================================ timeline
KEY = []          # (t, dict) keyframes for head state


def timeline():
    """Head state vs time: gx, gy, zt, angle, attach tool, carry cell, heat 0..1, air 0..1, caption."""
    seg = []

    def add(t0, t1, a, b, cap):
        seg.append((t0, t1, a, b, cap))
    rx, ry = RACK3[0], RACK3[1]
    p0 = dict(gx=rx, gy=ry, zt=ZT_RACK + 320, ang=0.0, tool=0, cell=0, heat=0.0, air=0.0)
    p1 = dict(p0, zt=ZT_RACK)
    p2 = dict(p1, tool=1)
    p3 = dict(p2, zt=ZT_TRAVEL)
    p4 = dict(p3, gx=BX, gy=BY)
    p5 = dict(p4, zt=ZT_WORK)
    p6 = dict(p5, heat=1.0, air=1.0)
    p7 = dict(p6, ang=3.0, cell=1)
    p8 = dict(p7, zt=ZT_WORK + 150, ang=0.0, heat=0.0, air=0.0)
    p9 = dict(p8, zt=ZT_TRAVEL)
    p10 = dict(p9, gx=MEAS[0], gy=MEAS[1])
    p11 = dict(p10, zt=ZT_MEAS)
    p12 = dict(p11, cell=2)
    p13 = dict(p12, zt=ZT_MEAS + 300)
    add(0.0, 4.0, p0, p0, '')
    add(4.0, 6.0, p0, p1, '공구 자동 교환: 공구 거치대에서 03 셀 분리 공구 결합')
    add(6.0, 6.5, p1, p2, '공구 자동 교환: 공구 거치대에서 03 셀 분리 공구 결합')
    add(6.5, 8.0, p2, p3, '공구 자동 교환: 공구 거치대에서 03 셀 분리 공구 결합')
    add(8.0, 12.0, p3, p4, '대상 셀 위로 이동 (셀 전압 측정은 별도 측정대에서)')
    add(12.0, 14.5, p4, p5, '내려가서 타원 흡착컵 2개로 흡착 · 노즈 IR 센서로 셀 윗면 온도 측정')
    add(14.5, 20.0, p5, p6, '구역 가열: 대상 셀 아래 코일만 켬 → 냉각판 아랫벽 → 바닥 접착층 연화\n이웃 셀은 가열 끔 + 냉각 공기')
    add(20.0, 25.0, p6, p7, '짧은 변부터 필링: 기울임축 + X·Z 보정으로 셀 아래 모서리 기준 회전\n하중이 기준을 넘으면 더 당기지 않고 가열 유지')
    add(25.0, 27.5, p7, p8, '접착이 떨어지면 셀을 들어 올림')
    add(27.5, 29.0, p8, p9, '측정대로 이송')
    add(29.0, 33.0, p9, p10, '측정대로 이송')
    add(33.0, 35.0, p10, p11, '측정대에 내려놓음 → 전압·절연 측정 → 재사용/재활용 분류')
    add(35.0, 35.5, p11, p12, '측정대에 내려놓음 → 전압·절연 측정 → 재사용/재활용 분류')
    add(35.5, 37.5, p12, p13, '측정대에 내려놓음 → 전압·절연 측정 → 재사용/재활용 분류')
    add(37.5, 41.0, p13, p13, '')
    return seg


def state(seg, t):
    for (t0, t1, a, b, cap) in seg:
        if t0 <= t <= t1:
            u = ease((t - t0) / max(t1 - t0, 1e-6))
            s = {k: (a[k] + (b[k] - a[k]) * u if isinstance(a[k], float) else (b[k] if u >= 0.5 else a[k])) for k in a}
            s['cap'] = cap
            return s
    s = dict(seg[-1][3])
    s['cap'] = ''
    return s


CAM = [  # (t, position, focal point)
    (0.0, (6800, -5200, 4600), (2300, 0, 900)),
    (4.0, (5200, -2600, 2600), (2900, 500, 1100)),
    (8.0, (5200, -2600, 2600), (2900, 500, 1100)),
    (12.0, (BX + 900, BY - 1500, 1900), (BX, BY, 1050)),
    (14.5, (BX + 520, BY - 700, 1250), (BX, BY, 960)),
    (20.0, (BX + 120, BY - 760, 1010), (BX, BY, 905)),
    (25.0, (BX + 100, BY - 720, 990), (BX, BY, 910)),
    (27.5, (BX + 700, BY - 1300, 1500), (BX, BY, 1000)),
    (33.0, (MEAS[0] + 900, MEAS[1] - 1600, 1800), (MEAS[0], MEAS[1], 1050)),
    (37.5, (MEAS[0] + 800, MEAS[1] - 1400, 1500), (MEAS[0], MEAS[1], 980)),
    (41.0, (6800, -5200, 4600), (2300, 0, 900)),
]


def camera(t):
    for (ta, pa, fa), (tb, pb, fb) in zip(CAM[:-1], CAM[1:]):
        if ta <= t <= tb:
            u = ease((t - ta) / (tb - ta))
            return lerp(pa, pb, u), lerp(fa, fb, u)
    return np.array(CAM[-1][1], float), np.array(CAM[-1][2], float)


# ============================================================================ render
def render(t_from=0.0, t_to=None, out_name='CTP_R03_process_concept.mp4', preview_times=None):
    sc = build()
    seg = timeline()
    T_END = seg[-1][1] if t_to is None else t_to
    pl = pv.Plotter(off_screen=True, window_size=(W_, H_))
    pl.set_background('#eef1f3', top='#ffffff')
    pl.enable_anti_aliasing('ssaa')
    for k, m in sc['statics'].items():
        op = 0.18 if k == 'fence' else 1.0
        pl.add_mesh(m, color=COL.get(k, '#aaaaaa'), opacity=op, smooth_shading=False, specular=0.15)
    a_bridge = pl.add_mesh(sc['bridge'], color='#e0913b')
    a_carr = pl.add_mesh(sc['carriage'], color='#c7792a')
    a_upper = pl.add_mesh(sc['upper'], color='#d6dde2', specular=0.3)
    a_tilt = pl.add_mesh(sc['tilt'], color='#618ba5')
    a_cm = pl.add_mesh(sc['cm'], color='#9aa3a8')
    a_tool = [pl.add_mesh(m, color=c, specular=0.2) for c, m in sc['tool'].items()]
    a_target = []
    for n, m in sc['target']:
        a_target.append((n, pl.add_mesh(m, color=COL['cells'] if n.startswith('셀') else COL['terms'])))
    a_neigh = pl.add_mesh(sc['neigh'], color=COL['cells'])
    # cooling air jets (cones from the nozzle orifices onto neighbour cells), tool-local
    jets = []
    for (x, y) in T.P['nozzle_xy'].values():
        cone = pv.Cone(center=(x, y, 22), direction=(0, 0, -1), height=44, radius=7, resolution=24)
        jets.append(cone)
    jet = merge(jets)
    a_jet = pl.add_mesh(jet, color='#4aa3df', opacity=0.0)
    font = ImageFont.truetype(FONT, 26)
    font_s = ImageFont.truetype(FONT, 18)
    font_t = ImageFont.truetype(FONT_B, 40)
    writer = None
    if preview_times is None:
        writer = imageio_ffmpeg.write_frames(str(OUT / out_name), (W_, H_), fps=FPS, codec='libx264',
                                             pix_fmt_out='yuv420p', quality=8, macro_block_size=8)
        writer.send(None)
        times = np.arange(t_from, T_END + 1e-9, 1.0 / FPS)
    else:
        times = preview_times
    held_cell_M = None
    placed_M = None
    pl.show(auto_close=False)
    for i, t in enumerate(times):
        s = state(seg, t)
        # head transforms
        base = np.array([s['gx'], s['gy'], s['zt'] - S.TILT_TO_CUP])
        R = Mrot_y_neg(s['ang'], PIVOT)
        lower = Mtrans(base) @ R
        tc_rot = (R @ np.r_[TILT_C, 1.0])[:3]
        upper = Mtrans(base + (tc_rot - TILT_C))
        a_bridge.user_matrix = Mtrans((s['gx'], 0, 0))
        a_carr.user_matrix = Mtrans((s['gx'], s['gy'], 0))
        a_upper.user_matrix = upper
        a_tilt.user_matrix = lower
        a_cm.user_matrix = lower
        tool_M = lower if s['tool'] else Mtrans(RACK3)
        for a in a_tool:
            a.user_matrix = tool_M
        # target cell: on the block, carried by the tool, or placed on the measuring jig
        if s['cell'] == 0:
            cm_ = np.eye(4)
            cell_world = np.eye(4)
        else:
            # cell local (tool frame) = world - (BX, BY, ZC) at pick-up; carried with 'lower'
            pick = Mtrans((-BX, -BY, -S.ZC))
            if s['cell'] == 1:
                cell_world = lower @ pick
            else:
                if placed_M is None:
                    placed_M = (Mtrans(np.array([MEAS[0], MEAS[1], ZT_MEAS - S.TILT_TO_CUP]))) @ pick
                cell_world = placed_M
        heat = s['heat']
        col_hot = np.array([0.95, 0.42, 0.18])
        col_cold = np.array(pv.Color(COL['cells']).float_rgb)
        for n, a in a_target:
            a.user_matrix = cell_world
            if n.startswith('셀'):
                a.prop.color = tuple(col_cold + (col_hot - col_cold) * (0.85 * heat))
        a_neigh.prop.color = tuple(col_cold + (np.array([0.45, 0.68, 0.9]) - col_cold) * 0.6 * s['air'])
        a_jet.user_matrix = lower
        a_jet.prop.opacity = 0.45 * s['air']
        pos, foc = camera(t)
        pl.camera_position = [tuple(pos), tuple(foc), (0, 0, 1)]
        pl.camera.view_angle = 35
        pl.camera.clipping_range = (50.0, 30000.0)
        pl.render()
        img = pl.screenshot(return_img=True)
        im = Image.fromarray(img)
        d = ImageDraw.Draw(im, 'RGBA')
        if t < 4.0:
            a_ = min(1.0, (4.0 - t) / 1.0)
            d.rectangle([0, 0, W_, H_], fill=(255, 255, 255, int(150 * a_)))
            d.text((70, 260), 'CTP 폐배터리 해체 로봇', font=font_t, fill=(20, 30, 40, int(255 * a_)))
            d.text((72, 320), '03 공구 셀 분리 공정 - 개념 영상 (R03)', font=font, fill=(40, 50, 60, int(255 * a_)))
        if t > 37.5:
            a_ = min(1.0, (t - 37.5) / 1.0)
            d.rectangle([0, 0, W_, H_], fill=(255, 255, 255, int(170 * a_)))
            d.text((70, 280), '개념 영상입니다. 시뮬레이션·시험 결과가 아닙니다.', font=font, fill=(20, 30, 40, int(255 * a_)))
            d.text((70, 322), '가상 CTP 팩 · 치수와 동작은 모두 설계 가정 (R03, 2026-10-14)', font=font_s,
                   fill=(40, 50, 60, int(255 * a_)))
        if 20.0 <= t <= 27.5:
            d.rectangle([W_ - 290, 60, W_ - 40, 108], fill=(20, 28, 36, 175))
            d.text((W_ - 272, 70), f'기울임 {s["ang"]:.1f}° (가정)', font=font, fill=(255, 255, 255, 255))
        if s['cap']:
            lines = s['cap'].split('\n')
            hb = 18 + 36 * len(lines)
            d.rectangle([40, H_ - 40 - hb, W_ - 40, H_ - 40], fill=(20, 28, 36, 175))
            for k, ln in enumerate(lines):
                d.text((60, H_ - 40 - hb + 12 + 36 * k), ln, font=font, fill=(255, 255, 255, 255))
        d.text((W_ - 330, 18), '개념 영상 · 시뮬레이션 아님', font=font_s, fill=(60, 70, 80, 220))
        if writer is not None:
            writer.send(np.asarray(im.convert('RGB')).tobytes())
        else:
            im.convert('RGB').save(OUT / f'preview_{t:05.1f}.png')
    if writer is not None:
        writer.close()
    pl.close()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'preview':
        render(preview_times=[float(x) for x in sys.argv[2:]])
    else:
        render()
