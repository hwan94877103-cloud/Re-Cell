"""Assembly -> GLB (colours, parts, Y-up, metres) and STL (one mesh, mm, Z-up) for plain 3D viewers."""
import json
import struct

import cadquery as cq
from cadquery.occ_impl.assembly import toCAF
from OCP.RWGltf import RWGltf_CafWriter
from OCP.RWMesh import RWMesh_CoordinateSystem
from OCP.TCollection import TCollection_AsciiString
from OCP.TColStd import TColStd_IndexedDataMapOfStringString
from OCP.Message import Message_ProgressRange


def hex2color(h):
    """'#rrggbb' or '#rrggbbaa' (alpha < 1 -> transparent material in GLB)."""
    h = h.lstrip('#')
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
    return cq.Color(*rgb, a)


def build_assembly(items, name):
    """items: (key, solid, hex colour or None[, ASCII label]). The label (or key) becomes the part name in STEP/GLB."""
    a = cq.Assembly(name=name)
    for i, it in enumerate(items):
        s = it[1]
        col = it[2] if len(it) > 2 and it[2] else '#a7b0b6'
        lab = it[3] if len(it) > 3 and it[3] else it[0]
        a.add(s, name=f'{i:03d}_{lab}'[:60], color=hex2color(col))
    return a


def export_glb(assy, path, tol=0.2, ang=0.3):
    _, doc = toCAF(assy, True, True, tol, ang)
    w = RWGltf_CafWriter(TCollection_AsciiString(str(path)), True)
    cs = w.ChangeCoordinateSystemConverter()
    cs.SetInputLengthUnit(0.001)                                  # model in mm
    cs.SetInputCoordinateSystem(RWMesh_CoordinateSystem.RWMesh_CoordinateSystem_Zup)
    cs.SetOutputLengthUnit(1.0)                                   # glTF: metres
    cs.SetOutputCoordinateSystem(RWMesh_CoordinateSystem.RWMesh_CoordinateSystem_glTF)   # Y-up
    w.SetMergeFaces(True)                                         # one primitive per part -> fewer draw calls
    ok = w.Perform(doc, TColStd_IndexedDataMapOfStringString(), Message_ProgressRange())
    if ok:
        set_pbr(path)
    return ok


def set_pbr(path, metallic=0.0, roughness=0.6):
    """OCCT writes only baseColorFactor; glTF then defaults to metallic 1 / rough 1, which looks dark and
    grey in most viewers. Write plain (non-metal) factors so the part colours show as intended."""
    b = open(path, 'rb').read()
    clen, ctype = struct.unpack('<II', b[12:20])
    assert b[:4] == b'glTF' and ctype == 0x4E4F534A
    js = json.loads(b[20:20 + clen])
    for m in js.get('materials', []):
        pbr = m.setdefault('pbrMetallicRoughness', {})
        pbr.setdefault('metallicFactor', metallic)
        pbr.setdefault('roughnessFactor', roughness)
    jb = json.dumps(js, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    jb += b' ' * (-len(jb) % 4)
    rest = b[20 + clen:]                                          # BIN chunk unchanged
    out = struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(jb) + len(rest)) + struct.pack('<II', len(jb), 0x4E4F534A) + jb + rest
    open(path, 'wb').write(out)


def export_stl(solids, path, tol=0.2, ang=0.3):
    comp = cq.Compound.makeCompound(list(solids))
    cq.exporters.export(comp, str(path), tolerance=tol, angularTolerance=ang)


def glb_info(path):
    """Read back a GLB: node/mesh/material counts, triangle count, world bounds (metres, Y-up)."""
    b = open(path, 'rb').read()
    magic, ver, length = struct.unpack('<4sII', b[:12])
    jlen, jtype = struct.unpack('<II', b[12:20])
    js = json.loads(b[20:20 + jlen])
    tri = 0
    for m in js.get('meshes', []):
        for pr in m['primitives']:
            if 'indices' in pr:
                tri += js['accessors'][pr['indices']]['count'] // 3
    mins, maxs = [1e9] * 3, [-1e9] * 3
    for acc in js['accessors']:
        if acc.get('type') == 'VEC3' and 'min' in acc and acc.get('componentType') == 5126:
            pass
    # positions are written in world coordinates by RWGltf (node transforms may also exist)
    import numpy as np
    def node_mats():
        out = {}
        def walk(i, M):
            nd = js['nodes'][i]
            T = np.eye(4)
            if 'matrix' in nd:
                T = np.array(nd['matrix']).reshape(4, 4).T
            else:
                t = nd.get('translation', [0, 0, 0]); r = nd.get('rotation', [0, 0, 0, 1]); s = nd.get('scale', [1, 1, 1])
                x, y, z, w_ = r
                R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w_), 2 * (x * z + y * w_)],
                              [2 * (x * y + z * w_), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w_)],
                              [2 * (x * z - y * w_), 2 * (y * z + x * w_), 1 - 2 * (x * x + y * y)]])
                T[:3, :3] = R * np.array(s)
                T[:3, 3] = t
            M2 = M @ T
            if 'mesh' in nd:
                out.setdefault(nd['mesh'], []).append(M2)
            for c in nd.get('children', []):
                walk(c, M2)
        for sc in js.get('scenes', []):
            for r in sc['nodes']:
                walk(r, np.eye(4))
        return out
    lo, hi = np.full(3, 1e9), np.full(3, -1e9)
    for mi, mats in node_mats().items():
        for pr in js['meshes'][mi]['primitives']:
            acc = js['accessors'][pr['attributes']['POSITION']]
            c = np.array([[x, y, z, 1] for x in (acc['min'][0], acc['max'][0]) for y in (acc['min'][1], acc['max'][1])
                          for z in (acc['min'][2], acc['max'][2])])
            for M in mats:
                w_ = (M @ c.T).T[:, :3]
                lo = np.minimum(lo, w_.min(0)); hi = np.maximum(hi, w_.max(0))
    return dict(bytes=len(b), nodes=len(js.get('nodes', [])), meshes=len(js.get('meshes', [])),
                materials=len(js.get('materials', [])), triangles=tri, bounds_m=[lo.round(3).tolist(), hi.round(3).tolist()])
