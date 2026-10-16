"""Build the drawing explainer: drawing images, 3D pictures with anchors, data.json, debug overlays.
usage: python3 build.py SITE_DIR DEBUG_DIR [--no3d]"""
import json
import sys
from pathlib import Path

import numpy as np
import pymupdf
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import content as C

SITE, DEBUG = Path(sys.argv[1]), Path(sys.argv[2])
NO3D = '--no3d' in sys.argv
IMG = SITE / 'img'
IMG.mkdir(parents=True, exist_ok=True)
DEBUG.mkdir(parents=True, exist_ok=True)
DWG = Path('/home/claude/ctp/R03/drawings/out')
MARKS = json.loads((HERE / 'marks.json').read_text(encoding='utf-8'))
W_MM, H_MM = 420.0, 297.0
FONT = ImageFont.truetype('/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf', 15)


def pct(xy):
    return [round(xy[0] / W_MM * 100, 3), round((1 - xy[1] / H_MM) * 100, 3)]


# ----------------------------------------------------------------- drawings
for sh in C.SHEETS:
    out = IMG / f"{sh['stem']}.webp"
    if not out.exists():
        pix = pymupdf.open(DWG / f"{sh['stem']}.pdf")[0].get_pixmap(dpi=240, colorspace=pymupdf.csGRAY)
        Image.frombytes('L', (pix.width, pix.height), pix.samples).save(out, 'WEBP', lossless=True, quality=100, method=6)

# ----------------------------------------------------------------- 3D pictures
S3 = HERE / 'scenes.json'
scene_pct = json.loads(S3.read_text(encoding='utf-8')) if S3.exists() else {}
if not NO3D:
    import scenes
    for name, fn in scenes.ALL.items():
        im, p = fn()
        im.save(IMG / f'3d_{name}.webp', 'WEBP', quality=90, method=6)
        scene_pct[name] = dict(size=list(im.size), anchors={k: [round(v[0], 3), round(v[1], 3)] for k, v in p.items()})
        print('3d', name, im.size, len(p))
    S3.write_text(json.dumps(scene_pct, ensure_ascii=False, indent=1), encoding='utf-8')


# ----------------------------------------------------------------- marks
def view_point(stem, vi, p, off):
    v = MARKS[stem]['views'][vi]
    p3 = np.array(list(p) + [0.0] * (3 - len(p)), float)
    uv = np.array([p3 @ np.array(v['xd']), p3 @ np.array(v['yd'])])
    q = np.array(v['origin']) + v['scale'] * (uv - np.array(v['ref']))
    m = q + np.array(off, float)
    return m, (q if np.linalg.norm(off) > 0.01 else None)


def marks2d(sh, spec):
    out = []
    stem = sh['stem']
    if spec[0] == 'b':
        hits = [b for b in MARKS[stem].get('balloons', []) if b['num'] == spec[1]]
        if not hits:
            raise SystemExit(f'{stem}: balloon {spec[1]} not found')
        for b in hits:
            out.append(dict(l=spec[1], p=pct(b['c'])))
    elif spec[0] == 'v':
        _, lab, vi, p, off = spec
        m, lead = view_point(stem, vi, p, off)
        d = dict(l=lab, p=pct(m))
        if lead is not None:
            d['lead'] = pct(lead)
        out.append(d)
    elif spec[0] == 'p':
        lab, xy, lead = spec[1], spec[2], spec[3]
        d = dict(l=lab, p=pct(xy))
        if lead:
            d['lead'] = pct(lead)
        if len(spec) > 4:
            x, y0, y1 = spec[4]
            d['span'] = [*pct((x, y1)), *pct((x, y0))]
        out.append(d)
    return out


def marks3d(sh, item, labels):
    anchors = scene_pct.get(sh['scene'], {}).get('anchors', {})
    keys = item.get('k3')
    if keys is None:
        keys = [k for k in anchors if any(k == l or k.startswith(l + '#') for l in labels)]
    return [dict(l=k.split('#')[0], p=anchors[k]) for k in keys if k in anchors]


data = dict(hint=C.HINT, groups=C.GROUPS, sheets=[])
for sh in C.SHEETS:
    items = []
    for it in sh['items']:
        m2 = [m for spec in it['m'] for m in marks2d(sh, spec)]
        labels = sorted({m['l'] for m in m2})
        items.append(dict(L=it['L'], t=it['t'], d=it['d'], m2=m2, m3=marks3d(sh, it, labels)))
    d = dict(id=sh['id'], short=sh['short'], dwg=sh['dwg'], no=sh['no'], title=sh['title'], scale=sh['scale'], intro=sh['intro'],
             img=f"img/{sh['stem']}.webp", img3d=f"img/3d_{sh['scene']}.webp", cap3d=sh['cap3d'],
             size3d=scene_pct.get(sh['scene'], {}).get('size'),
             views=[dict(n=n, d=dd, box=[*pct((b[0], b[3])), *pct((b[2], b[1]))]) for n, dd, b in sh['views']],
             items=items)
    if sh.get('steps'):
        d['steps'] = [dict(n=n, t=tt, d=dd, marks=mk) for n, tt, dd, mk in sh['steps']]
        d['stepNote'] = sh.get('step_note', '')
    data['sheets'].append(d)
(SITE / 'data.json').write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')


# ----------------------------------------------------------------- debug overlays
def dot(draw, x, y, lab, r=13):
    draw.ellipse((x - r, y - r, x + r, y + r), fill=(214, 49, 43, 235))
    tw = draw.textlength(lab, font=FONT)
    draw.text((x - tw / 2, y - 9), lab, font=FONT, fill='white')


for sh, d in zip(C.SHEETS, data['sheets']):
    im = Image.open(IMG / f"{sh['stem']}.webp").convert('RGB')
    im = im.resize((im.width // 2, im.height // 2), Image.LANCZOS)
    dr = ImageDraw.Draw(im)
    W, H = im.size
    for v in d['views']:
        b = v['box']
        dr.rectangle((b[0] / 100 * W, b[1] / 100 * H, b[2] / 100 * W, b[3] / 100 * H), outline=(40, 120, 220), width=2)
        dr.text((b[0] / 100 * W + 4, b[1] / 100 * H + 2), v['n'], font=FONT, fill=(40, 120, 220))
    for it in d['items']:
        for m in it['m2']:
            x, y = m['p'][0] / 100 * W, m['p'][1] / 100 * H
            if 'lead' in m:
                dr.line((x, y, m['lead'][0] / 100 * W, m['lead'][1] / 100 * H), fill=(214, 49, 43), width=2)
            if 'span' in m:
                sp = m['span']
                dr.line((sp[0] / 100 * W, sp[1] / 100 * H, sp[2] / 100 * W, sp[3] / 100 * H), fill=(214, 49, 43), width=4)
            dot(dr, x, y, m['l'])
    im.save(DEBUG / f"{sh['id']}_2d.png")
    p3 = IMG / f"3d_{sh['scene']}.webp"
    if p3.exists():
        im = Image.open(p3).convert('RGBA')
        bg = Image.new('RGBA', im.size, (236, 239, 241, 255))
        bg.alpha_composite(im)
        dr = ImageDraw.Draw(bg)
        for it in d['items']:
            for m in it['m3']:
                dot(dr, m['p'][0] / 100 * im.width, m['p'][1] / 100 * im.height, m['l'])
        bg.convert('RGB').save(DEBUG / f"{sh['id']}_3d.png")
print('sheets', len(data['sheets']), 'items', sum(len(s['items']) for s in data['sheets']))
