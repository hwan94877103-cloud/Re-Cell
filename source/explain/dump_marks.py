"""Re-run the drawing scripts without writing files and record where balloons, view labels, part heads,
leaders and views land on each sheet (paper mm, origin bottom-left, A3 420 x 297)."""
import json
import sys
from pathlib import Path

R03 = Path('/home/claude/ctp/R03')
sys.path[:0] = [str(R03 / 'drawings'), str(R03)]
import draw_lib as DL

REC = {}


def rec(sh):
    return REC.setdefault(id(sh), dict(balloons=[], view_labels=[], part_heads=[], leaders=[], views=[]))


_b, _vl, _ph, _ld, _vi = DL.Sheet.balloon, DL.Sheet.view_label, DL.Sheet.part_head, DL.Sheet.leader, DL.View.__init__


def balloon(self, num, c, target, *a, **k):
    rec(self)['balloons'].append(dict(num=str(num), c=[float(x) for x in c], target=[float(x) for x in target]))
    return _b(self, num, c, target, *a, **k)


def view_label(self, text, p, *a, **k):
    rec(self)['view_labels'].append(dict(text=text, p=[float(x) for x in p], sub=k.get('sub')))
    return _vl(self, text, p, *a, **k)


def part_head(self, p, item, base, *a, **k):
    rec(self)['part_heads'].append(dict(item=str(item), p=[float(x) for x in p], label=k.get('label')))
    return _ph(self, p, item, base, *a, **k)


def leader(self, tip, knee, text, *a, **k):
    rec(self)['leaders'].append(dict(text=str(text), tip=[float(x) for x in tip], knee=[float(x) for x in knee]))
    return _ld(self, tip, knee, text, *a, **k)


def view_init(self, sheet, direction, scale, origin, ref=(0.0, 0.0), clip=None, name=''):
    _vi(self, sheet, direction, scale, origin, ref, clip, name)
    rec(sheet)['views'].append(dict(name=name, dir=[float(x) for x in direction] if not isinstance(direction, str) else direction,
                                    scale=float(scale), origin=[float(x) for x in origin], ref=[float(x) for x in ref],
                                    xd=[float(x) for x in self.xd], yd=[float(x) for x in self.yd]))


DL.Sheet.balloon, DL.Sheet.view_label, DL.Sheet.part_head, DL.Sheet.leader = balloon, view_label, part_head, leader
DL.View.__init__ = view_init

import d01, d02, d03, d04ks, d09

jobs = [('D-01_R03_1of1', d01.sheet), ('D-02_R03_1of3', d02.sheet1), ('D-02_R03_2of3', d02.sheet2),
        ('D-02_R03_3of3', d02.sheet3), ('D-03_R03_1of2', d03.sheet1), ('D-03_R03_2of2', d03.sheet2),
        ('D-04_R03_1of5', d04ks.sheet1), ('D-04_R03_2of5', d04ks.sheet2), ('D-04_R03_3of5', d04ks.sheet3),
        ('D-04_R03_4of5', d04ks.sheet4), ('D-04_R03_5of5', d04ks.sheet5), ('D-09_R03_1of1', d09.sheet)]
out = {}
for stem, fn in jobs:
    sh = fn()
    out[stem] = REC.get(id(sh), {})
Path(sys.argv[1]).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
for k, v in out.items():
    print(k, {kk: len(vv) for kk, vv in v.items()})
