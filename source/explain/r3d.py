"""Offscreen technical renders of CAD solids (pyvista/VTK) with CAD edges, transparent background,
and projection of 3D anchor points to image percentages (for clickable markers on the explainer page)."""
import numpy as np
import pyvista as pv
import vtk
import cadquery as cq
from PIL import Image

vtk.vtkMapper.SetResolveCoincidentTopologyToPolygonOffset()
EDGE = '#1d2226'
SECTION = '#f2c9b8'          # cut faces (like hatching on the drawings)


def tess(shape, tol=0.15, ang=0.25):
    v, t = shape.tessellate(tol, ang)
    if not t:
        return None
    pts = np.array([(p.x, p.y, p.z) for p in v], float)
    faces = np.hstack([[3, *tri] for tri in t]).astype(np.int64)
    return pv.PolyData(pts, faces)


def edge_lines(shape, seg=3.0):
    pts, lines = [], []
    for e in shape.Edges():
        try:
            if e.geomType() == 'LINE':
                P = [e.startPoint(), e.endPoint()]
            else:
                n = int(max(10, min(120, e.Length() / seg + 1)))
                P = e.positions(np.linspace(0, 1, n))
        except Exception:
            continue
        i0 = len(pts)
        pts.extend([(p.x, p.y, p.z) for p in P])
        lines.append([len(P), *range(i0, i0 + len(P))])
    if not pts:
        return None
    pd = pv.PolyData(np.array(pts, float))
    pd.lines = np.hstack(lines).astype(np.int64)
    return pd


def halfspace(shape, axis='y', keep_ge=0.0, big=5000.0):
    """Keep the part of shape with coordinate >= keep_ge along axis. Returns (solid or None, cut faces list)."""
    bb = shape.BoundingBox()
    lo = dict(x=bb.xmin, y=bb.ymin, z=bb.zmin)[axis]
    hi = dict(x=bb.xmax, y=bb.ymax, z=bb.zmax)[axis]
    if lo >= keep_ge - 1e-6:
        return shape, []
    if hi <= keep_ge + 1e-6:
        return None, []
    c = [0.0, 0.0, 0.0]
    i = 'xyz'.index(axis)
    c[i] = keep_ge + big / 2
    box = cq.Solid.makeBox(big, big, big, cq.Vector(*[(-big / 2 if k != i else keep_ge) for k in range(3)]))
    try:
        half = shape.intersect(box)
    except Exception:
        return shape, []
    faces = []
    for f in half.Faces():
        try:
            cc = f.Center()
            nrm = f.normalAt()
            if abs([cc.x, cc.y, cc.z][i] - keep_ge) < 1e-4 and abs(abs([nrm.x, nrm.y, nrm.z][i]) - 1) < 1e-6:
                faces.append(f)
        except Exception:
            pass
    return half, faces


class Scene:
    def __init__(self):
        self.items = []          # (mesh, color, opacity, edges)

    def add(self, shape, color, opacity=1.0, edges=True, tol=0.15):
        m = tess(shape, tol)
        if m is None:
            return
        self.items.append((m, color, opacity, edge_lines(shape) if edges else None))

    def add_wire(self, shape, color='#7d8a93'):
        self.items.append((None, color, 1.0, edge_lines(shape, seg=20.0)))

    def add_cut(self, shape, color, axis='y', keep_ge=0.0, opacity=1.0, tol=0.15):
        half, cut = halfspace(shape, axis, keep_ge)
        if half is None:
            return
        if not cut:
            self.add(half, color, opacity, True, tol)
            return
        keep = [f for f in half.Faces() if not any(f.isSame(c) for c in cut)]
        m = merge([tess(f, tol) for f in keep])
        if m is not None:
            self.items.append((m, color, opacity, edge_lines(half)))
        m = merge([tess(f, tol) for f in cut])
        if m is not None:
            self.items.append((m, tint(color), 1.0, None))


def tint(hex_col, k=0.5):
    h = hex_col.lstrip('#')
    rgb = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    rgb = [round(c + (255 - c) * k) for c in rgb]
    # warm the cut faces slightly so they read as "cut" like hatching
    rgb = [min(255, rgb[0] + 14), rgb[1], max(0, rgb[2] - 10)]
    return '#%02x%02x%02x' % tuple(rgb)


def merge(meshes):
    ms = [m for m in meshes if m is not None and m.n_points]
    if not ms:
        return None
    out = ms[0].copy()
    for m in ms[1:]:
        out = out.merge(m, merge_points=False)
    return out


def render(scene, direction, anchors, size=(1200, 860), ss=2, zoom=1.0, up=(0, 0, 1), edge_w=1.25, focus=None,
           pad=24, depth_peel=False, out_scale=1.5):
    """Returns (PIL RGBA image cropped to content, {key: (x%, y%)}) for anchors {key: (x, y, z)}."""
    W, H = size[0] * ss, size[1] * ss
    pl = pv.Plotter(off_screen=True, window_size=(W, H))
    if depth_peel:
        pl.enable_depth_peeling(8)
    for m, col, op, ed in scene.items:
        if m is None:
            pl.add_mesh(ed, color=col, line_width=edge_w * ss * 1.3)
            continue
        pl.add_mesh(m, color=col, opacity=op, smooth_shading=False, ambient=0.28, diffuse=0.78, specular=0.08,
                    show_edges=False)
        if ed is not None:
            pl.add_mesh(ed, color=EDGE, line_width=edge_w * ss, opacity=1.0 if op > 0.5 else 0.35)
    pl.enable_parallel_projection()
    b = np.array(pl.bounds).reshape(3, 2)
    c = np.array(focus, float) if focus is not None else b.mean(axis=1)
    d = np.array(direction, float)
    d /= np.linalg.norm(d)
    r = np.linalg.norm(b[:, 1] - b[:, 0])
    pl.camera_position = [tuple(c + d * r * 2), tuple(c), up]
    pl.reset_camera()
    pl.camera.focal_point = tuple(c)
    pl.camera.position = tuple(c + d * r * 2)
    pl.camera.zoom(zoom)
    img = pl.screenshot(transparent_background=True, return_img=True)
    ren = pl.renderer
    proj = {}
    for k, p in anchors.items():
        ren.SetWorldPoint(float(p[0]), float(p[1]), float(p[2]), 1.0)
        ren.WorldToDisplay()
        x, y, _ = ren.GetDisplayPoint()
        proj[k] = (x, H - y)
    pl.close()
    im = Image.fromarray(img)
    if im.mode != 'RGBA':
        im = im.convert('RGBA')
    a = np.array(im)[:, :, 3]
    ys, xs = np.nonzero(a > 8)
    x0, x1 = max(0, xs.min() - pad * ss), min(W, xs.max() + pad * ss)
    y0, y1 = max(0, ys.min() - pad * ss), min(H, ys.max() + pad * ss)
    # keep anchors inside the crop
    for k, (x, y) in proj.items():
        x0, x1 = min(x0, int(x) - 30 * ss), max(x1, int(x) + 30 * ss)
        y0, y1 = min(y0, int(y) - 30 * ss), max(y1, int(y) + 30 * ss)
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    im = im.crop((x0, y0, x1, y1))
    w, h = im.size
    k = out_scale / ss
    im = im.resize((round(w * k), round(h * k)), Image.LANCZOS)
    pct = {k: ((x - x0) / w * 100, (y - y0) / h * 100) for k, (x, y) in proj.items()}
    return im, pct


def side_by_side(parts, gap=40):
    """parts: [(image, pct dict)] -> combined image and pct dict (keys must be unique)."""
    hs = max(im.size[1] for im, _ in parts)
    wsum = sum(im.size[0] for im, _ in parts) + gap * (len(parts) - 1)
    out = Image.new('RGBA', (wsum, hs), (0, 0, 0, 0))
    pct = {}
    x = 0
    for im, p in parts:
        y = (hs - im.size[1]) // 2
        out.paste(im, (x, y), im)
        for k, (px, py) in p.items():
            pct[k] = ((x + px / 100 * im.size[0]) / wsum * 100, (y + py / 100 * im.size[1]) / hs * 100)
        x += im.size[0] + gap
    return out, pct


def stacked(parts, gap=30):
    """Vertical version of side_by_side."""
    ws = max(im.size[0] for im, _ in parts)
    hsum = sum(im.size[1] for im, _ in parts) + gap * (len(parts) - 1)
    out = Image.new('RGBA', (ws, hsum), (0, 0, 0, 0))
    pct = {}
    y = 0
    for im, p in parts:
        x = (ws - im.size[0]) // 2
        out.paste(im, (x, y), im)
        for k, (px, py) in p.items():
            pct[k] = ((x + px / 100 * im.size[0]) / ws * 100, (y + py / 100 * im.size[1]) / hsum * 100)
        y += im.size[1] + gap
    return out, pct
