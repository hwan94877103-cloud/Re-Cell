"""KS-style 2D drawing helpers for CTP TOOL03 R03 (DXF R2013 via ezdxf, PDF/PNG via PyMuPDF backend).

Conventions
- Modelspace = A3 sheet in paper mm (420 x 297). Each View maps model (u, v) -> paper with one uniform scale.
- DIMENSION entities use DIMLFAC = 1/scale, so the displayed values are model sizes.
- Views come from OCC exact HLR of the R03 solids (tool03_r03.build()); sections are real boolean cuts.
- Text style 'KS' points to malgun.ttf for the CAD file; the PDF render swaps it to NanumGothic in memory only.
"""
import math
from pathlib import Path

import numpy as np
import ezdxf
from ezdxf.enums import TextEntityAlignment
from ezdxf.math import BoundingBox2d
import cadquery as cq
import shapely.geometry as sg
import shapely.ops as so
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_EDGE, TopAbs_REVERSED
from OCP.BRepLib import BRepLib
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.BRepTools import BRepTools_WireExplorer
from OCP.GeomAbs import GeomAbs_Line, GeomAbs_Circle
from OCP.GCPnts import GCPnts_QuasiUniformDeflection
from OCP.TopoDS import TopoDS

FONT_CAD = 'malgun.ttf'
FONT_PDF = 'NanumGothic.ttf'
SHEET_W, SHEET_H = 420.0, 297.0
BORDER = (20.0, 10.0, 410.0, 287.0)          # left binding margin 20, others 10

VIEWDIR = {                                   # (view normal towards the viewer, u direction)
    'front': ((0, -1, 0), (1, 0, 0)),         # u = X,  v = Z   viewer at -Y
    'back': ((0, 1, 0), (-1, 0, 0)),          # u = -X, v = Z
    'right': ((1, 0, 0), (0, 1, 0)),          # u = Y,  v = Z   viewer at +X
    'left': ((-1, 0, 0), (0, -1, 0)),         # u = -Y, v = Z
    'top': ((0, 0, 1), (1, 0, 0)),            # u = X,  v = Y
    'bottom': ((0, 0, -1), (1, 0, 0)),        # u = X,  v = -Y
}

LAYERS = {   # name: (ACI colour, lineweight 1/100 mm, linetype)
    'OUTLINE': (7, 50, 'Continuous'), 'HIDDEN': (2, 25, 'KS_HIDDEN'), 'CENTER': (1, 18, 'KS_CENTER'),
    'PHANTOM': (6, 18, 'KS_PHANTOM'), 'DIM': (3, 18, 'Continuous'), 'TEXT': (7, 25, 'Continuous'),
    'HATCH': (8, 13, 'Continuous'), 'CUT': (1, 18, 'KS_CENTER'), 'CUT_THK': (1, 50, 'Continuous'),
    'SYMBOL': (7, 25, 'Continuous'), 'FRAME': (7, 70, 'Continuous'), 'TABLE': (7, 25, 'Continuous'),
    'TABLE_THK': (7, 50, 'Continuous'), 'BREAK': (7, 18, 'Continuous'), 'BALLOON': (7, 25, 'Continuous'),
    'THREAD': (7, 18, 'Continuous'),
}


def fmt(v, nd=2):
    t = f'{v:.{nd}f}'.rstrip('0').rstrip('.')
    return '0' if t in ('-0', '') else t


def frame_of(direction):
    n, xd = (np.array(a, float) for a in VIEWDIR[direction])
    return n, xd, np.cross(n, xd)


# ============================================================================ projection
def _edge_prims(comp, defl=0.01):
    prims = []
    if comp is None or comp.IsNull():
        return prims
    ex = TopExp_Explorer(comp, TopAbs_EDGE)
    while ex.More():
        e = TopoDS.Edge_s(ex.Current())
        BRepLib.BuildCurves3d_s(e, 1e-7)
        c = BRepAdaptor_Curve(e)
        f, l = c.FirstParameter(), c.LastParameter()

        def P(par):
            p = c.Value(par)
            return (p.X(), p.Y())
        t = c.GetType()
        if t == GeomAbs_Line:
            a, b = P(f), P(l)
            if math.dist(a, b) > 1e-6:
                prims.append(('L', a, b))
        elif t == GeomAbs_Circle:
            ci = c.Circle()
            cc = (ci.Location().X(), ci.Location().Y())
            if abs((l - f) - 2 * math.pi) < 1e-7:
                prims.append(('C', cc, ci.Radius()))
            elif ci.Radius() * abs(l - f) > 1e-5:
                prims.append(('A', cc, ci.Radius(), P(f), P(0.5 * (f + l)), P(l)))
        else:
            d = GCPnts_QuasiUniformDeflection(c, defl)
            if d.IsDone() and d.NbPoints() > 1:
                pts = [(d.Value(i).X(), d.Value(i).Y()) for i in range(1, d.NbPoints() + 1)]
                prims.append(('P', pts))
        ex.Next()
    return prims


def project(shapes, direction, hidden=False):
    """Exact HLR. Returns (visible prims, hidden prims) in model (u, v)."""
    n, xd = VIEWDIR[direction]
    algo = HLRBRep_Algo()
    for s in shapes:
        algo.Add(s.wrapped if hasattr(s, 'wrapped') else s)
    algo.Projector(HLRAlgo_Projector(gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*n), gp_Dir(*xd))))
    algo.Update()
    algo.Hide()
    h = HLRBRep_HLRToShape(algo)
    vis = _edge_prims(h.VCompound()) + _edge_prims(h.OutLineVCompound())
    hid = (_edge_prims(h.HCompound()) + _edge_prims(h.OutLineHCompound())) if hidden else []
    return vis, hid


def halfspace(p0, nkeep, big=4000.0):
    nk = np.array(nkeep, float)
    nk /= np.linalg.norm(nk)
    c = np.array(p0, float) + nk * big / 2
    return cq.Solid.makeBox(big, big, big, cq.Vector(*(c - big / 2)))


def clip_box(x0, x1, y0, y1, z0, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))


def cut_keep(solid, p0, nkeep, box=None):
    s = solid.intersect(halfspace(p0, nkeep))
    if box is not None:
        s = s.intersect(box)
    return s


def plane_faces(shape, p0, nkeep, tol=1e-4):
    nk = np.array(nkeep, float)
    p0 = np.array(p0, float)
    out = []
    for f in shape.Faces():
        if f.geomType() != 'PLANE':
            continue
        nn = f.normalAt()
        if abs(abs(nn.x * nk[0] + nn.y * nk[1] + nn.z * nk[2]) - 1) > 1e-6:
            continue
        c = f.Center()
        if abs((np.array([c.x, c.y, c.z]) - p0) @ nk) > tol:
            continue
        out.append(f)
    return out


def face_polygon(face, direction, defl=0.01):
    _, xd, yd = frame_of(direction)

    def wire_uv(w):
        ex = BRepTools_WireExplorer(w.wrapped, face.wrapped)
        pts = []
        while ex.More():
            e = ex.Current()
            c = BRepAdaptor_Curve(e)
            f, l = c.FirstParameter(), c.LastParameter()
            if c.GetType() == GeomAbs_Line:
                ps = [c.Value(f), c.Value(l)]
            else:
                d = GCPnts_QuasiUniformDeflection(c, defl)
                ps = [d.Value(i) for i in range(1, d.NbPoints() + 1)]
            if e.Orientation() == TopAbs_REVERSED:
                ps = ps[::-1]
            for p in ps:
                q = (p.X() * xd[0] + p.Y() * xd[1] + p.Z() * xd[2], p.X() * yd[0] + p.Y() * yd[1] + p.Z() * yd[2])
                if not pts or math.dist(pts[-1], q) > 1e-7:
                    pts.append(q)
            ex.Next()
        return pts
    outer = wire_uv(face.outerWire())
    holes = [h for h in (wire_uv(w) for w in face.innerWires()) if len(h) >= 3]
    poly = sg.Polygon(outer, holes)
    if not poly.is_valid:
        poly = poly.buffer(0)
    return poly


def _arc_angles(c, p0, pm, p1):
    a0 = math.degrees(math.atan2(p0[1] - c[1], p0[0] - c[0])) % 360
    a1 = math.degrees(math.atan2(p1[1] - c[1], p1[0] - c[0])) % 360
    am = math.degrees(math.atan2(pm[1] - c[1], pm[0] - c[0])) % 360
    sweep = (a1 - a0) % 360
    if (am - a0) % 360 <= sweep + 1e-9:
        return a0, a1
    return a1, a0


def prim_points(pr, n_per_mm=2.0):
    """Discretise a prim to a list of (u, v) points (model units)."""
    k = pr[0]
    if k == 'L':
        return [pr[1], pr[2]]
    if k == 'P':
        return list(pr[1])
    if k == 'C':
        c, r = pr[1], pr[2]
        n = max(24, int(2 * math.pi * r * n_per_mm))
        return [(c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]
    c, r = pr[1], pr[2]
    a0, a1 = _arc_angles(c, pr[3], pr[4], pr[5])
    sw = (a1 - a0) % 360
    n = max(6, int(math.radians(sw) * r * n_per_mm))
    return [(c[0] + r * math.cos(math.radians(a0 + sw * i / n)), c[1] + r * math.sin(math.radians(a0 + sw * i / n)))
            for i in range(n + 1)]


def prim_bounds(pr):
    if pr[0] in ('C', 'A'):
        c, r = pr[1], pr[2]
        return (c[0] - r, c[1] - r, c[0] + r, c[1] + r)
    pts = np.array(prim_points(pr))
    return (pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max())


def dedupe(prims, nd=4):
    seen, out = set(), []
    for pr in prims:
        if pr[0] == 'L':
            a = tuple(round(x, nd) for x in pr[1])
            b = tuple(round(x, nd) for x in pr[2])
            key = ('L',) + tuple(sorted([a, b]))
        elif pr[0] == 'C':
            key = ('C', round(pr[1][0], nd), round(pr[1][1], nd), round(pr[2], nd))
        elif pr[0] == 'A':
            a0, a1 = _arc_angles(pr[1], pr[3], pr[4], pr[5])
            key = ('A', round(pr[1][0], nd), round(pr[1][1], nd), round(pr[2], nd), round(a0, 2), round(a1, 2))
        else:
            key = ('P',) + tuple(tuple(round(x, 3) for x in p) for p in (pr[1][0], pr[1][len(pr[1]) // 2], pr[1][-1]))
        if key in seen:
            continue
        seen.add(key)
        out.append(pr)
    return out


# ============================================================================ view
class View:
    def __init__(self, sheet, direction, scale, origin, ref=(0.0, 0.0), clip=None, name=''):
        """origin: paper point where model (u, v) = ref lands. clip: shapely geometry in model (u, v)."""
        self.sh, self.dir, self.scale = sheet, direction, float(scale)
        self.O, self.ref = np.array(origin, float), np.array(ref, float)
        self.clip, self.name = clip, name
        self.n, self.xd, self.yd = frame_of(direction)

    def P(self, u, v=None):
        if v is None:
            u, v = u
        q = self.O + self.scale * (np.array([u, v], float) - self.ref)
        return (float(q[0]), float(q[1]))

    def uv(self, p3):
        p = np.array(p3, float)
        return (float(p @ self.xd), float(p @ self.yd))

    def P3(self, p3):
        return self.P(*self.uv(p3))

    # ---------------------------------------------------------------- geometry output
    def draw_prims(self, prims, layer):
        msp = self.sh.msp
        for pr in prims:
            if self.clip is not None:
                bx = sg.box(*prim_bounds(pr))
                if not self.clip.intersects(bx):
                    continue
                if not self.clip.contains(bx):
                    ls = sg.LineString(prim_points(pr, 8.0))
                    cut = ls.intersection(self.clip)
                    geoms = getattr(cut, 'geoms', [cut])
                    for g in geoms:
                        if g.is_empty or g.geom_type != 'LineString':
                            continue
                        msp.add_lwpolyline([self.P(*p) for p in g.coords], dxfattribs={'layer': layer})
                    continue
            k = pr[0]
            if k == 'L':
                msp.add_line(self.P(*pr[1]), self.P(*pr[2]), dxfattribs={'layer': layer})
            elif k == 'C':
                msp.add_circle(self.P(*pr[1]), pr[2] * self.scale, dxfattribs={'layer': layer})
            elif k == 'A':
                a0, a1 = _arc_angles(pr[1], pr[3], pr[4], pr[5])
                msp.add_arc(self.P(*pr[1]), pr[2] * self.scale, a0, a1, dxfattribs={'layer': layer})
            else:
                msp.add_lwpolyline([self.P(*p) for p in pr[1]], dxfattribs={'layer': layer})

    def hatch_poly(self, poly, angle=45.0, spacing=2.0, layer='HATCH'):
        if self.clip is not None:
            poly = poly.intersection(self.clip)
        polys = [poly] if poly.geom_type == 'Polygon' else [g for g in getattr(poly, 'geoms', []) if g.geom_type == 'Polygon']
        for pg in polys:
            if pg.is_empty or pg.area * self.scale ** 2 < 0.05:
                continue
            h = self.sh.msp.add_hatch(dxfattribs={'layer': layer, 'hatch_style': 0})
            h.set_pattern_fill('ANSI31', scale=spacing / 3.175, angle=angle - 45.0, style=0)
            h.paths.add_polyline_path([self.P(*p) for p in pg.exterior.coords[:-1]], is_closed=True,
                                      flags=ezdxf.const.BOUNDARY_PATH_EXTERNAL)
            for ring in pg.interiors:
                h.paths.add_polyline_path([self.P(*p) for p in ring.coords[:-1]], is_closed=True,
                                          flags=ezdxf.const.BOUNDARY_PATH_DEFAULT)

    def solid_fill(self, poly, layer='HATCH'):
        if self.clip is not None:
            poly = poly.intersection(self.clip)
        polys = [poly] if poly.geom_type == 'Polygon' else [g for g in getattr(poly, 'geoms', []) if g.geom_type == 'Polygon']
        for pg in polys:
            if pg.is_empty or pg.area * self.scale ** 2 < 0.02:
                continue
            h = self.sh.msp.add_hatch(dxfattribs={'layer': layer})
            h.set_solid_fill(color=7)
            h.paths.add_polyline_path([self.P(*p) for p in pg.exterior.coords[:-1]], is_closed=True,
                                      flags=ezdxf.const.BOUNDARY_PATH_EXTERNAL)

    def outline(self, shapes, hidden=False, layer='OUTLINE', hidden_layer='HIDDEN'):
        vis, hid = project(shapes, self.dir, hidden)
        self.draw_prims(dedupe(vis), layer)
        if hidden:
            self.draw_prims(dedupe(hid), hidden_layer)
        return vis, hid

    def section(self, parts, p0, cut_parts, whole_parts=(), phantom=(), box=None, hatch_specs=None, hidden=False,
                whole_box=None, onplane_tol=0.6):
        """Full section: cut_parts are boolean-cut at the plane (kept side away from the viewer) and hatched;
        whole_parts are shown uncut if any part of them lies on the kept side (fasteners, purchased items)."""
        nkeep = -self.n
        kept, polys = [], []
        for i, s in enumerate(cut_parts):
            k = cut_keep(s, p0, nkeep, box)
            if k is None or not k.Solids():
                continue
            kept.append(k)
            for f in plane_faces(k, p0, nkeep):
                polys.append((i, face_polygon(f, self.dir)))
        shows = []
        hs = halfspace(p0, nkeep)
        p0a = np.array(p0, float)
        for s in whole_parts:
            bb = s.BoundingBox()
            ds = [(np.array([x, y, z]) - p0a) @ nkeep for x in (bb.xmin, bb.xmax) for y in (bb.ymin, bb.ymax)
                  for z in (bb.zmin, bb.zmax)]
            if max(ds) <= 1e-6:
                continue                                    # entirely in front of the plane: removed
            if min(ds) >= -1e-6 or abs(0.5 * (max(ds) + min(ds))) <= onplane_tol:
                k = s                                       # behind the plane, or the plane holds its axis
            else:
                k = s.intersect(hs)                         # crosses the plane off-axis: keep the far side only
                if not k.Solids():
                    continue
            shows.append(k if whole_box is None else k.intersect(whole_box))
        vis, hid = project(kept + shows, self.dir, hidden)
        self.draw_prims(dedupe(vis), 'OUTLINE')
        if hidden:
            self.draw_prims(dedupe(hid), 'HIDDEN')
        for i, pg in polys:
            spec = (hatch_specs or {}).get(i, {})
            if spec.get('solid'):
                self.solid_fill(pg)
            elif spec.get('none'):
                continue
            else:
                self.hatch_poly(pg, angle=spec.get('angle', 45.0), spacing=spec.get('spacing', 2.0))
        if phantom:
            pv, _ = project(list(phantom), self.dir, False)
            self.draw_prims(dedupe(pv), 'PHANTOM')
        return polys

    # ---------------------------------------------------------------- annotations in model coordinates
    def cmark(self, c, r, ext=2.0, both=True, layer='CENTER'):
        """Centre mark of a circle (model centre c, model radius r), lines extend ext paper-mm beyond."""
        x, y = self.P(*c)
        R = r * self.scale + ext
        self.sh.msp.add_line((x - R, y), (x + R, y), dxfattribs={'layer': layer})
        if both:
            self.sh.msp.add_line((x, y - R), (x, y + R), dxfattribs={'layer': layer})

    def axis(self, a, b, ext=2.0, layer='CENTER'):
        pa, pb = np.array(self.P(*a)), np.array(self.P(*b))
        d = pb - pa
        L = np.linalg.norm(d)
        if L < 1e-9:
            return
        d /= L
        self.sh.msp.add_line(tuple(pa - d * ext), tuple(pb + d * ext), dxfattribs={'layer': layer})

    def pcd(self, c, r, a0=0, a1=360, layer='CENTER'):
        if a1 - a0 >= 360:
            self.sh.msp.add_circle(self.P(*c), r * self.scale, dxfattribs={'layer': layer})
        else:
            self.sh.msp.add_arc(self.P(*c), r * self.scale, a0, a1, dxfattribs={'layer': layer})

    def phantom_poly(self, pts, closed=False):
        pts = list(pts) + ([pts[0]] if closed else [])
        self.draw_prims([('P', pts)], 'PHANTOM')

    def dim(self, a, b, at=None, off=None, orient='h', text='<>', tol=None, style_over=None, basic=False):
        """Linear dimension between model points a, b. orient 'h' (horizontal) / 'v' (vertical) / 'a' (aligned).
        at = absolute paper coordinate of the dim line (y for 'h', x for 'v'); off = paper offset from the
        outermost of a/b instead."""
        pa, pb = self.P(*a), self.P(*b)
        return self.sh.dim_paper(pa, pb, self.scale, at=at, off=off, orient=orient, text=text, tol=tol,
                                 style_over=style_over, basic=basic)

    def dia(self, c, r, ang=45.0, text='<>', style_over=None):
        return self.sh.dia_paper(self.P(*c), r * self.scale, self.scale, ang, text, style_over)


# ============================================================================ sheet
class Sheet:
    def __init__(self):
        doc = ezdxf.new('R2013', setup=False, units=4)
        doc.header['$MEASUREMENT'] = 1
        doc.header['$LTSCALE'] = 1.0
        doc.header['$PSLTSCALE'] = 0
        doc.header['$LWDISPLAY'] = 1
        doc.header['$TEXTSTYLE'] = 'KS'
        doc.linetypes.add('KS_HIDDEN', pattern=[4.0, 3.0, -1.0], description='KS hidden ---- ----')
        doc.linetypes.add('KS_CENTER', pattern=[17.0, 12.0, -2.0, 1.0, -2.0], description='KS centre ____ . ____')
        doc.linetypes.add('KS_PHANTOM', pattern=[20.0, 12.0, -2.0, 1.0, -2.0, 1.0, -2.0],
                          description='KS phantom ____ . . ____')
        for name, (col, lw, lt) in LAYERS.items():
            doc.layers.add(name, color=col, lineweight=lw, linetype=lt)
        doc.styles.add('KS', font=FONT_CAD)
        self.doc, self.msp = doc, doc.modelspace()
        self._dimstyles = {}

    # ---------------------------------------------------------------- primitives (paper)
    def line(self, a, b, layer='OUTLINE'):
        return self.msp.add_line(a, b, dxfattribs={'layer': layer})

    def pline(self, pts, layer='OUTLINE', closed=False):
        return self.msp.add_lwpolyline(pts, close=closed, dxfattribs={'layer': layer})

    def rect(self, x0, y0, x1, y1, layer='TABLE'):
        return self.pline([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer, closed=True)

    def circle(self, c, r, layer='OUTLINE'):
        return self.msp.add_circle(c, r, dxfattribs={'layer': layer})

    SYM_CHARS = '⌴↧'

    def text(self, s, p, h=2.5, align='BOTTOM_LEFT', rot=0.0, layer='TEXT', width=1.0):
        if rot == 0.0 and any(c in s for c in self.SYM_CHARS):
            return self._text_sym(s, p, h, align, layer)
        t = self.msp.add_text(s, height=h, rotation=rot, dxfattribs={'layer': layer, 'style': 'KS', 'width': width})
        t.set_placement(p, align=TextEntityAlignment[align])
        return t

    def _sym_w(self, h):
        return 1.15 * h

    def _text_sym(self, s, p, h, align, layer):
        """Text with drawn counterbore (⌴) and depth (↧) symbols (fonts have no such glyphs)."""
        runs, cur = [], ''
        for ch in s:
            if ch in self.SYM_CHARS:
                if cur:
                    runs.append(('t', cur))
                runs.append(('s', ch))
                cur = ''
            else:
                cur += ch
        if cur:
            runs.append(('t', cur))
        W = sum(self.text_width(r, h) if k == 't' else self._sym_w(h) for k, r in runs)
        va, ha = align.split('_')
        x = p[0] - {'LEFT': 0.0, 'CENTER': W / 2, 'RIGHT': W}.get(ha, 0.0)
        yb = p[1] - {'BOTTOM': 0.0, 'MIDDLE': h / 2, 'TOP': h}.get(va, 0.0)
        for k, r in runs:
            if k == 't':
                t = self.msp.add_text(r, height=h, dxfattribs={'layer': layer, 'style': 'KS'})
                t.set_placement((x, yb), align=TextEntityAlignment['BOTTOM_LEFT'])
                x += self.text_width(r, h)
            else:
                u = h
                if r == '⌴':
                    self.pline([(x + 0.05 * u, yb + 0.8 * u), (x + 0.25 * u, yb + 0.8 * u), (x + 0.25 * u, yb + 0.1 * u),
                                (x + 0.85 * u, yb + 0.1 * u), (x + 0.85 * u, yb + 0.8 * u), (x + 1.05 * u, yb + 0.8 * u)], layer)
                else:
                    xc = x + 0.5 * u
                    self.line((xc, yb + 0.9 * u), (xc, yb + 0.05 * u), layer)
                    self.pline([(xc - 0.25 * u, yb + 0.35 * u), (xc, yb + 0.05 * u), (xc + 0.25 * u, yb + 0.35 * u)], layer)
                    self.line((xc - 0.35 * u, yb + 0.05 * u), (xc + 0.35 * u, yb + 0.05 * u), layer)
                x += self._sym_w(h)
        return None

    def lines_of_text(self, lines, p, h=2.5, gap=1.6, layer='TEXT'):
        x, y = p
        for s in lines:
            self.text(s, (x, y), h, 'BOTTOM_LEFT', layer=layer)
            y -= h * gap
        return y

    def arrow(self, tip, frm, L=2.5, W=0.85, layer='DIM'):
        tip, frm = np.array(tip, float), np.array(frm, float)
        d = frm - tip
        d /= np.linalg.norm(d)
        nrm = np.array([-d[1], d[0]])
        b = tip + d * L
        p1, p2 = b + nrm * W / 2, b - nrm * W / 2
        self.msp.add_solid([tuple(tip), tuple(p1), tuple(p2)], dxfattribs={'layer': layer})

    def dot(self, p, r=0.45, layer='DIM'):
        h = self.msp.add_hatch(dxfattribs={'layer': layer})
        h.set_solid_fill(color=256)
        h.paths.add_edge_path().add_arc(p, r, 0, 360)

    def leader(self, tip, knee, text, h=2.5, end='arrow', side=None, lines=None):
        """Leader from tip (paper) to knee, then a horizontal shoulder carrying the text above it."""
        tip, knee = np.array(tip, float), np.array(knee, float)
        texts = [text] if lines is None else lines
        w = max(self.text_width(s, h) for s in texts) + 1.0
        sgn = side if side is not None else (1 if knee[0] >= tip[0] else -1)
        end_pt = knee + np.array([sgn * w, 0])
        self.pline([tuple(tip), tuple(knee), tuple(end_pt)], 'DIM')
        if end == 'arrow':
            self.arrow(tip, knee)
        elif end == 'dot':
            self.dot(tuple(tip))
        x0 = min(knee[0], end_pt[0]) + 0.5
        y = knee[1] + 0.8
        for s in reversed(texts):
            self.text(s, (x0, y), h, 'BOTTOM_LEFT')
            y += h * 1.5
        return end_pt

    def callout(self, tip, knee, lines, fcfs=(), h=2.5, end='arrow', side=None, datum=None):
        """Hole/feature callout: leader with text above the shoulder and feature control frames below it.
        fcfs: list of (kind, value, datums, diameter). datum: letter of a datum feature symbol hung under the frames."""
        tip, knee = np.array(tip, float), np.array(knee, float)
        sgn = side if side is not None else (1 if knee[0] >= tip[0] else -1)
        ws = [self.text_width(t, h) + 1.0 for t in lines]
        fw = []
        for kind, val, dts, dia in fcfs:
            fw.append(2.4 * h + self.text_width(('Ø' if dia else '') + val, h) + 2.4 + 2.4 * h * len(dts))
        W = max(ws + fw + [8.0])
        x_end = knee[0] + sgn * W
        self.pline([tuple(tip), tuple(knee), (x_end, knee[1])], 'DIM')
        if end == 'arrow':
            self.arrow(tuple(tip), tuple(knee))
        elif end == 'dot':
            self.dot(tuple(tip))
        x0 = min(knee[0], x_end)
        y = knee[1] + 0.8
        for t in reversed(lines):
            self.text(t, (x0 + 0.5, y), h, 'BOTTOM_LEFT')
            y += h * 1.5
        yb = knee[1]
        frames = []
        for (kind, val, dts, dia), w in zip(fcfs, fw):
            H = 2.4 * h
            fr = self.fcf((x0, yb - H), kind, val, dts, h, dia)
            frames.append(fr)
            yb -= H
        if datum and frames:
            fx0, fy0, fx1, fy1 = frames[-1]
            S = 2.4 * h
            bx = fx0 + S / 2
            self.datum(datum, (bx, fy0), (bx, fy0 - 2.2 - 3.0 - S / 2), h)
        return x0, x_end

    _ADV = None
    EM = 1.333          # rendered em / text height (calibrated on the PDF output: cap height = 0.75 em)

    @staticmethod
    def text_width(s, h):
        """Advance width of s in paper mm for text height h (NanumGothic advances x EM)."""
        if Sheet._ADV is None:
            try:
                from fontTools.ttLib import TTFont
                import glob
                fp = (glob.glob('/usr/share/fonts/**/NanumGothic.ttf', recursive=True) or [None])[0]
                t = TTFont(fp)
                cm, hm, upm = t.getBestCmap(), t['hmtx'], t['head'].unitsPerEm
                Sheet._ADV = (cm, hm, upm)
            except Exception:
                Sheet._ADV = False
        w = 0.0
        for ch in s:
            o = ord(ch)
            if ch in '⌴↧':
                w += 1.15 * h
            elif Sheet._ADV and o in Sheet._ADV[0]:
                cm, hm, upm = Sheet._ADV
                w += hm[cm[o]][0] / upm * h * Sheet.EM
            elif 0xAC00 <= o <= 0xD7A3 or 0x3130 <= o <= 0x318F:
                w += 0.94 * h * Sheet.EM
            else:
                w += 0.62 * h * Sheet.EM
        return w

    # ---------------------------------------------------------------- dimensions
    def dimstyle(self, scale, **extra):
        key = (round(scale, 6), tuple(sorted(extra.items())))
        if key in self._dimstyles:
            return self._dimstyles[key]
        name = f'KS_{len(self._dimstyles):02d}'
        ds = self.doc.dimstyles.new(name)
        a = dict(dimtxsty='KS', dimtxt=2.5, dimasz=2.5, dimexe=1.5, dimexo=0.8, dimgap=0.8, dimtad=1, dimtih=0,
                 dimtoh=0, dimdec=2, dimzin=8, dimlfac=1.0 / scale, dimclrd=3, dimclre=3, dimclrt=7, dimlwd=18,
                 dimlwe=18, dimdsep=ord('.'), dimatfit=3, dimtmove=0, dimcen=0.0, dimtdec=2, dimtzin=8, dimtfac=0.7)
        a.update(extra)
        for k, v in a.items():
            ds.dxf.set(k, v)
        self._dimstyles[key] = name
        return name

    def dim_paper(self, pa, pb, scale, at=None, off=None, orient='h', text='<>', tol=None, style_over=None,
                  basic=False):
        pa, pb = np.array(pa, float), np.array(pb, float)
        extra = dict(style_over or {})
        if tol is not None:            # (upper, lower) deviations in model mm
            extra.update(dimtol=1, dimtp=float(tol[0]), dimtm=float(-tol[1]))
        st = self.dimstyle(scale, **extra)
        if orient == 'h':
            if at is None:
                at = (max(pa[1], pb[1]) + off) if off >= 0 else (min(pa[1], pb[1]) + off)
            base, ang = (0.5 * (pa[0] + pb[0]), at), 0
        elif orient == 'v':
            if at is None:
                at = (max(pa[0], pb[0]) + off) if off >= 0 else (min(pa[0], pb[0]) + off)
            base, ang = (at, 0.5 * (pa[1] + pb[1])), 90
        else:
            d = pb - pa
            nrm = np.array([-d[1], d[0]]) / np.linalg.norm(d)
            base, ang = tuple(pa + nrm * off), math.degrees(math.atan2(d[1], d[0]))
        dim = self.msp.add_linear_dim(base=base, p1=tuple(pa), p2=tuple(pb), angle=ang, dimstyle=st, text=text,
                                      dxfattribs={'layer': 'DIM'})
        dim.render()
        if basic:                                   # theoretically exact dimension: box around the value
            val = dim.dimension.get_measurement() / scale
            txt = text.replace('<>', fmt(val))
            c = dim.dimension.dxf.text_midpoint
            w, hh = self.text_width(txt, 2.5) + 1.4, 2.5 + 1.4
            if orient == 'v':
                w, hh = hh, w
            self.rect(c[0] - w / 2, c[1] - hh / 2, c[0] + w / 2, c[1] + hh / 2, 'DIM')
        return dim

    def dia_paper(self, c, r_paper, scale, ang=45.0, text='<>', style_over=None):
        st = self.dimstyle(scale, **(style_over or {}))
        d = self.msp.add_diameter_dim(center=c, radius=r_paper, angle=ang, dimstyle=st, text=text,
                                      dxfattribs={'layer': 'DIM'})
        d.render()
        return d

    # ---------------------------------------------------------------- KS symbols
    def balloon(self, num, c, target, r=4.0, end='dot'):
        c, target = np.array(c, float), np.array(target, float)
        self.circle(tuple(c), r, 'BALLOON')
        self.text(str(num), tuple(c), 3.5 if len(str(num)) < 3 else 2.8, 'MIDDLE_CENTER')
        d = target - c
        L = np.linalg.norm(d)
        if L > r + 0.5:
            p0 = c + d / L * r
            self.line(tuple(p0), tuple(target), 'BALLOON')
            if end == 'dot':
                self.dot(tuple(target), 0.5, 'BALLOON')
            elif end == 'arrow':
                self.arrow(tuple(target), tuple(p0), layer='BALLOON')

    def gdt_symbol(self, kind, c, s=2.6):
        """Draw a geometric characteristic symbol centred at c (paper), size s."""
        x, y = c
        L = lambda a, b: self.line(a, b, 'SYMBOL')
        if kind == 'flat':
            w, hh, sk = s * 0.9, s * 0.45, s * 0.35
            self.pline([(x - w / 2, y - hh / 2), (x + w / 2 - sk, y - hh / 2), (x + w / 2, y + hh / 2),
                        (x - w / 2 + sk, y + hh / 2)], 'SYMBOL', True)
        elif kind == 'par':
            for dx in (-0.45 * s, 0.05 * s):
                L((x + dx - 0.15 * s, y - 0.45 * s), (x + dx + 0.35 * s, y + 0.45 * s))
        elif kind == 'perp':
            L((x - 0.45 * s, y - 0.45 * s), (x + 0.45 * s, y - 0.45 * s))
            L((x, y - 0.45 * s), (x, y + 0.5 * s))
        elif kind == 'pos':
            self.circle((x, y), 0.32 * s, 'SYMBOL')
            L((x - 0.5 * s, y), (x + 0.5 * s, y))
            L((x, y - 0.5 * s), (x, y + 0.5 * s))
        elif kind == 'circ':
            self.circle((x, y), 0.42 * s, 'SYMBOL')

    def fcf(self, p, kind, value, datums=(), h=2.5, diameter=False):
        """Feature control frame; p = left-bottom corner (paper). Returns (x0, y0, x1, y1)."""
        H = 2.4 * h
        x, y = p
        cells = [H]
        val = ('Ø' if diameter else '') + value
        cells.append(self.text_width(val, h) + 2.4)
        cells += [H] * len(datums)
        x1 = x + sum(cells)
        self.rect(x, y, x1, y + H, 'SYMBOL')
        xx = x
        for i, w in enumerate(cells[:-1]):
            xx += w
            self.line((xx, y), (xx, y + H), 'SYMBOL')
        self.gdt_symbol(kind, (x + H / 2, y + H / 2))
        self.text(val, (x + H + cells[1] / 2, y + H / 2), h, 'MIDDLE_CENTER')
        xx = x + H + cells[1]
        for dlt in datums:
            self.text(dlt, (xx + H / 2, y + H / 2), h, 'MIDDLE_CENTER')
            xx += H
        return (x, y, x1, y + H)

    def datum(self, letter, foot, box_c, h=2.5):
        """Datum feature symbol: filled triangle on the feature at foot, line to a square box centred at box_c."""
        foot, box_c = np.array(foot, float), np.array(box_c, float)
        d = box_c - foot
        d /= np.linalg.norm(d)
        nrm = np.array([-d[1], d[0]])
        tri_h, tri_w = 2.2, 2.6
        b = foot + d * tri_h
        h_ = self.msp.add_hatch(dxfattribs={'layer': 'SYMBOL'})
        h_.set_solid_fill(color=256)
        h_.paths.add_polyline_path([tuple(foot + nrm * tri_w / 2), tuple(foot - nrm * tri_w / 2), tuple(b)], is_closed=True)
        self.pline([tuple(foot + nrm * tri_w / 2), tuple(foot - nrm * tri_w / 2), tuple(b)], 'SYMBOL', True)
        S = 2.4 * h
        edge = box_c - d * S / 2
        self.line(tuple(b), tuple(edge), 'SYMBOL')
        self.rect(box_c[0] - S / 2, box_c[1] - S / 2, box_c[0] + S / 2, box_c[1] + S / 2, 'SYMBOL')
        self.text(letter, tuple(box_c), h, 'MIDDLE_CENTER')

    def rough(self, p, ra=None, rot=0.0, removal=True, h=2.5):
        """ISO 1302 style surface texture symbol; p = vertex on the surface (paper), rot = surface direction deg.
        The symbol stands on the left side of the surface direction vector (rot=0: surface horizontal, symbol above)."""
        H1, H2 = 1.4 * h, 3.0 * h
        c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        T = lambda x, y: (p[0] + x * c - y * s, p[1] + x * s + y * c)
        k = 1 / math.tan(math.radians(60))
        a = T(-H1 * k, H1)
        b = T(H2 * k, H2)
        self.line(T(0, 0), a, 'SYMBOL')
        self.line(T(0, 0), b, 'SYMBOL')
        if removal:
            self.line(a, T(H1 * k, H1), 'SYMBOL')
        if ra is not None:
            w = self.text_width(ra, h) + 1.2
            self.line(b, T(H2 * k + w, H2), 'SYMBOL')
            self.text(ra, T(H2 * k + 0.6, H2 - h - 0.6), h, 'BOTTOM_LEFT', rot=rot)

    def rough_leader(self, tip, knee, ra, h=2.5):
        """Surface texture symbol on a leader (for faces that point down or are hard to reach)."""
        tip, knee = np.array(tip, float), np.array(knee, float)
        self.line(tuple(tip), tuple(knee), 'SYMBOL')
        self.arrow(tuple(tip), tuple(knee), layer='SYMBOL')
        k = 1 / math.tan(math.radians(60))
        H1 = 1.4 * h
        L = H1 * k + 1.0
        self.line(tuple(knee), (knee[0] + L, knee[1]), 'SYMBOL')
        self.rough((knee[0] + L, knee[1]), ra, 0.0, True, h)

    def cutline(self, a, b, label, look, ext=4.0, thick=6.0, h=3.5):
        """Cutting plane line between paper points a, b; look = viewing direction (paper unit vector)."""
        a, b = np.array(a, float), np.array(b, float)
        d = (b - a) / np.linalg.norm(b - a)
        A, B = a - d * ext, b + d * ext
        self.line(tuple(A + d * thick), tuple(B - d * thick), 'CUT')
        self.line(tuple(A), tuple(A + d * thick), 'CUT_THK')
        self.line(tuple(B - d * thick), tuple(B), 'CUT_THK')
        lk = np.array(look, float) / np.linalg.norm(look)
        for P_ in (A, B):
            q = P_ + d * 0.0
            tail = q
            tip = q + lk * 6.0
            self.line(tuple(tail), tuple(tip - lk * 2.5), 'DIM')
            self.arrow(tuple(tip), tuple(tail), L=3.0, W=1.0)
            self.text(label, tuple(tip + lk * 3.0), h, 'MIDDLE_CENTER')

    def detail_circle(self, c, r, label, lab_pos, h=3.5):
        self.circle(c, r, 'DIM')
        self.text(label, lab_pos, h, 'MIDDLE_CENTER')

    def view_label(self, text, p, h=3.5, sub=None):
        self.text(text, p, h, 'BOTTOM_CENTER')
        if sub:
            self.text(sub, (p[0], p[1] - 4.2), 2.5, 'BOTTOM_CENTER')

    # ---------------------------------------------------------------- sheet furniture
    def frame(self):
        x0, y0, x1, y1 = BORDER
        self.rect(x0, y0, x1, y1, 'FRAME')
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        for a, b in [((cx, y1), (cx, y1 + 5)), ((cx, y0), (cx, y0 - 5)), ((x0, cy), (x0 - 10, cy)), ((x1, cy), (x1 + 5, cy))]:
            self.line(a, b, 'FRAME')
        # trimming-corner marks (thin) at the sheet edge, helps exact plotting
        for (x, y, sx, sy) in [(0, 0, 1, 1), (SHEET_W, 0, -1, 1), (0, SHEET_H, 1, -1), (SHEET_W, SHEET_H, -1, -1)]:
            self.line((x, y), (x + sx * 4, y), 'TABLE')
            self.line((x, y), (x, y + sy * 4), 'TABLE')

    def proj_symbol(self, c, s=1.0):
        """Third-angle projection symbol (truncated cone: small end towards the end view)."""
        x, y = c
        H1, H2, L = 7.0 * s, 4.0 * s, 9.0 * s
        x0 = x - 13 * s
        self.pline([(x0, y - H1 / 2), (x0 + L, y - H2 / 2), (x0 + L, y + H2 / 2), (x0, y + H1 / 2)], 'SYMBOL', True)
        xc = x + 7 * s
        self.circle((xc, y), H1 / 2, 'SYMBOL')
        self.circle((xc, y), H2 / 2, 'SYMBOL')
        self.line((x0 - 1.5 * s, y), (xc + H1 / 2 + 1.5 * s, y), 'CENTER')

    def title_block(self, info):
        """KS-style title block at the bottom-right corner, width 180."""
        x1, y0 = BORDER[2], BORDER[1]
        W = 180.0
        x0 = x1 - W
        rows = [9.0, 9.0, 8.0, 8.0]          # from bottom
        Ht = sum(rows)
        self.rect(x0, y0, x1, y0 + Ht, 'TABLE_THK')
        ys = [y0]
        for r in rows:
            ys.append(ys[-1] + r)
        for y in ys[1:-1]:
            self.line((x0, y), (x1, y), 'TABLE')
        # row 4 (top): 작품명 | value | 팀명 | value
        yA, yB = ys[3], ys[4]
        cols = [x0, x0 + 18, x0 + 120, x0 + 136, x1]
        for x in cols[1:-1]:
            self.line((x, yA), (x, yB), 'TABLE')
        self.text('작품명', ((cols[0] + cols[1]) / 2, (yA + yB) / 2), 2.5, 'MIDDLE_CENTER')
        self.text(info['work'], (cols[1] + 2, (yA + yB) / 2), 3.0, 'MIDDLE_LEFT')
        self.text('팀명', ((cols[2] + cols[3]) / 2, (yA + yB) / 2), 2.5, 'MIDDLE_CENTER')
        self.text(info.get('team', ''), (cols[3] + 2, (yA + yB) / 2), 2.5, 'MIDDLE_LEFT')
        # row 3: 도면명
        yA, yB = ys[2], ys[3]
        self.line((cols[1], yA), (cols[1], yB), 'TABLE')
        self.text('도면명', ((cols[0] + cols[1]) / 2, (yA + yB) / 2), 2.5, 'MIDDLE_CENTER')
        self.text(info['title'], (cols[1] + 2, (yA + yB) / 2), 3.5, 'MIDDLE_LEFT')
        # row 2: 도번 | 척도 | 단위 | 투상 | 작성일 | 개정
        yA, yB = ys[1], ys[2]
        c2 = [x0, x0 + 18, x0 + 46, x0 + 58, x0 + 76, x0 + 86, x0 + 98, x0 + 110, x0 + 136, x0 + 150, x0 + 162, x1]
        for x in c2[1:-1]:
            self.line((x, yA), (x, yB), 'TABLE')
        cells = [('도번', 2.5), (info['dwg_no'], 3.5), ('척도', 2.5), (info['scale'], 2.5), ('단위', 2.5), ('mm', 2.5),
                 ('작성일', 2.5), (info['date'], 2.5), ('개정', 2.5), (info['rev'], 2.5), ('', 2.5)]
        for i, (s, h) in enumerate(cells):
            self.text(s, ((c2[i] + c2[i + 1]) / 2, (yA + yB) / 2), h, 'MIDDLE_CENTER')
        self.proj_symbol(((c2[-2] + c2[-1]) / 2 + 1.0, (yA + yB) / 2), s=0.5)
        # row 1 (bottom): status
        yA, yB = ys[0], ys[1]
        self.line((cols[1], yA), (cols[1], yB), 'TABLE')
        self.text('상태', ((cols[0] + cols[1]) / 2, (yA + yB) / 2), 2.5, 'MIDDLE_CENTER')
        self.text(info['status'], (cols[1] + 2, (yA + yB) / 2), 2.5, 'MIDDLE_LEFT')
        self.text(info.get('sheet', ''), (x1 - 2, (yA + yB) / 2), 2.5, 'MIDDLE_RIGHT')
        return (x0, y0, x1, y0 + Ht)

    def table(self, x0, y_top, cols, header, rows, rh=5.0, hh=7.0, h=2.3, align=None):
        """Generic table growing downwards from y_top. cols = widths. Returns bottom y."""
        x1 = x0 + sum(cols)
        y = y_top
        self.rect(x0, y - hh - rh * len(rows), x1, y, 'TABLE_THK')
        xs = [x0]
        for w in cols:
            xs.append(xs[-1] + w)
        self.line((x0, y - hh), (x1, y - hh), 'TABLE_THK')
        for i, s in enumerate(header):
            self.text(s, ((xs[i] + xs[i + 1]) / 2, y - hh / 2), h, 'MIDDLE_CENTER')
        y -= hh
        for r in rows:
            for i, s in enumerate(r):
                al = (align or ['C'] * len(cols))[i]
                if al == 'C':
                    self.text(str(s), ((xs[i] + xs[i + 1]) / 2, y - rh / 2), h, 'MIDDLE_CENTER')
                else:
                    self.text(str(s), (xs[i] + 1.2, y - rh / 2), h, 'MIDDLE_LEFT')
            y -= rh
            self.line((x0, y), (x1, y), 'TABLE')
        for x in xs[1:-1]:
            self.line((x, y_top), (x, y), 'TABLE')
        return y

    # ---------------------------------------------------------------- KS exam-style helpers (R03 KS revision)
    def rough_group(self, p, base, others=(), h=2.5):
        """Part roughness group: base symbol + (other symbols), e.g. w(x, y). p = left vertex point. Returns end x."""
        k = 1 / math.tan(math.radians(60))
        step = 3.0 * h * k + self.text_width('w', h) + 2.6
        x, y = p
        self.rough((x + 1.4 * h * k, y), base, 0.0, True, h)
        x += step + 1.0
        if others:
            self.text('(', (x, y - 0.4), 1.8 * h, 'BOTTOM_LEFT')
            x += 1.6 * h
            for i, o in enumerate(others):
                self.rough((x + 1.4 * h * k, y), o, 0.0, True, h)
                x += step
                if i < len(others) - 1:
                    self.text(',', (x - 1.2, y - 0.2), h, 'BOTTOM_LEFT')
                    x += 1.4
            self.text(')', (x - 0.6, y - 0.4), 1.8 * h, 'BOTTOM_LEFT')
            x += 1.2 * h
        return x

    def part_head(self, p, item, base, others=(), label=None, h=2.5):
        """Circled item number followed by the roughness group (and an optional label)."""
        x, y = p
        r = 4.2
        self.circle((x + r, y + r - 1.0), r, 'BALLOON')
        self.text(str(item), (x + r, y + r - 1.0), 3.5, 'MIDDLE_CENTER')
        xe = self.rough_group((x + 2 * r + 3.0, y - 0.5), base, others, h)
        if label:
            self.text(label, (xe + 2.0, y), 2.5, 'BOTTOM_LEFT')
        return xe

    def parts_list(self, rows, x1=None, y0=None):
        """KS exam-style 부품란 directly above the title block: header row at the bottom, items above it.
        rows: [번호, 품번, 품명, 재질, 수량, 비고] in ascending item order."""
        x1 = BORDER[2] if x1 is None else x1
        y0 = BORDER[1] + 34.0 if y0 is None else y0
        cols = [11, 21, 50, 40, 12, 46]
        x0 = x1 - sum(cols)
        rh = 6.0
        allrows = [['번호', '품번', '품명', '재질', '수량', '비고']] + [[str(c) for c in r] for r in rows]
        ytop = y0 + rh * len(allrows)
        self.rect(x0, y0, x1, ytop, 'TABLE_THK')
        xs = [x0]
        for w in cols:
            xs.append(xs[-1] + w)
        for x in xs[1:-1]:
            self.line((x, y0), (x, ytop), 'TABLE')
        for i, r in enumerate(allrows):
            yb = y0 + rh * i
            if i:
                self.line((x0, yb), (x1, yb), 'TABLE_THK' if i == 1 else 'TABLE')
            for j, s in enumerate(r):
                if j in (2, 3, 5) and i:
                    self.text(s, (xs[j] + 1.2, yb + rh / 2), 2.4, 'MIDDLE_LEFT')
                else:
                    self.text(s, ((xs[j] + xs[j + 1]) / 2, yb + rh / 2), 2.4, 'MIDDLE_CENTER')
        return (x0, y0, x1, ytop)

    def notes_ks(self, p, lines, letters=('w', 'x', 'y'), h=2.4, gap=1.7, rough_vals=None, extra=()):
        """주서 block in the format of 규격집 46항: numbered lines, then the roughness legend with drawn symbols."""
        x, y = p
        self.text('주 서', (x, y), 3.5, 'BOTTOM_LEFT')
        y -= 3.5 * 1.7
        for s in lines:
            self.text(s, (x, y), h, 'BOTTOM_LEFT')
            y -= h * gap
        k = 1 / math.tan(math.radians(60))
        y -= 4.2                                   # symbol stands 3h above its vertex
        for lt in letters:
            self.rough((x + 8.0 + 1.4 * h * k, y), lt, 0.0, True, h)
            self.text('=', (x + 22.0, y + 0.6), h, 'BOTTOM_LEFT')
            self.rough((x + 28.0 + 1.4 * h * k, y), (rough_vals or {}).get(lt, lt), 0.0, True, h)
            y -= 3.0 * h + 1.8
        y += 2.0
        for s in extra:
            self.text(s, (x, y), h, 'BOTTOM_LEFT')
            y -= h * gap
        return y

    def zone_line(self, a, b, off=1.2, layer='CUT_THK'):
        """Thick chain line parallel to a surface, marking the extent of a special requirement (특수 지정선)."""
        a, b = np.array(a, float), np.array(b, float)
        d = (b - a) / np.linalg.norm(b - a)
        nrm = np.array([-d[1], d[0]]) * off
        L = np.linalg.norm(b - a)
        t, dash, gapl = 0.0, 4.0, 1.2
        while t < L:
            t1 = min(t + dash, L)
            self.line(tuple(a + nrm + d * t), tuple(a + nrm + d * t1), 'CUT_THK')
            t = t1 + gapl
            if t < L:
                self.line(tuple(a + nrm + d * t), tuple(a + nrm + d * min(t + 0.4, L)), 'CUT_THK')
                t += 0.4 + gapl

    # ---------------------------------------------------------------- output
    def save(self, path):
        self.doc.saveas(path)

    def render(self, pdf_path=None, png_path=None, dpi=110):
        from ezdxf.addons.drawing import RenderContext, Frontend, layout, pymupdf, config
        st = self.doc.styles.get('KS')
        old = st.dxf.font
        st.dxf.font = FONT_PDF
        try:
            ctx = RenderContext(self.doc)
            be = pymupdf.PyMuPdfBackend()
            cfg = config.Configuration(background_policy=config.BackgroundPolicy.WHITE,
                                       color_policy=config.ColorPolicy.BLACK,
                                       lineweight_policy=config.LineweightPolicy.ABSOLUTE,
                                       line_policy=config.LinePolicy.ACCURATE, lineweight_scaling=1.0,
                                       min_lineweight=0.05, hatch_policy=config.HatchPolicy.NORMAL)
            Frontend(ctx, be, config=cfg).draw_layout(self.msp, finalize=True)
            page = layout.Page(SHEET_W, SHEET_H, layout.Units.mm, margins=layout.Margins.all(0))
            stg = layout.Settings(fit_page=True)
            box = BoundingBox2d([(0, 0), (SHEET_W, SHEET_H)])
            pdf = be.get_pdf_bytes(page, settings=stg, render_box=box)   # backend is single-use: one call only
            if pdf_path:
                Path(pdf_path).write_bytes(pdf)
            if png_path:
                import pymupdf
                d = pymupdf.open(stream=pdf, filetype='pdf')
                d[0].get_pixmap(dpi=dpi).save(str(png_path))
            return pdf
        finally:
            st.dxf.font = old
