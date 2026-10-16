"""Process-sequence assets for the explainer page: card images (webp), original PNGs and the storyboard
(downloads), and SITE/process.json (figure list + D-01 step mapping) that make_page.py merges into the page data.

usage: python3 process_assets.py SITE [PROCESS_DIR]"""
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from process_figs import FIGS, D01_STEPS  # noqa: E402

SITE = Path(sys.argv[1])
PROC = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE.parent / 'process'
(SITE / 'img').mkdir(parents=True, exist_ok=True)
(SITE / 'figs').mkdir(parents=True, exist_ok=True)
meta = {m['id']: m for m in json.loads((PROC / 'figs' / 'meta.json').read_text(encoding='utf-8'))}
TOOL = {'01': '01 (외형)', '02': '02', '03': '03', '-': ''}
out = []
for f in FIGS:
    src = PROC / 'figs' / f"{f['id']}.png"
    im = Image.open(src).convert('RGB')
    w = im.resize((1200, 750), Image.LANCZOS)
    w.save(SITE / 'img' / f"proc_{f['id']}.webp", 'WEBP', quality=84, method=6)
    shutil.copy(src, SITE / 'figs' / f"CTP_R03_process_{f['id']}.png")
    out.append(dict(id=f['id'], no=f['no'], title=f['title'], tool=TOOL[f['tool']], note=f['note'], step=f['step'],
                    until=f['until'], anomaly=bool(f.get('anomaly')), cam=f['cam'],
                    img=f"img/proc_{f['id']}.webp", png=f"figs/CTP_R03_process_{f['id']}.png",
                    t=meta[f['id']]['sim']['t']))
sb = PROC / 'storyboard'
for n in ['CTP_R03_process_storyboard_4x3.png', 'CTP_R03_process_storyboard_4x3.pdf', 'CTP_R03_process_storyboard_3x4.png']:
    shutil.copy(sb / n, SITE / 'figs' / n)
data = dict(figs=out, d01=D01_STEPS,
            boards=dict(png='figs/CTP_R03_process_storyboard_4x3.png', pdf='figs/CTP_R03_process_storyboard_4x3.pdf',
                        png_portrait='figs/CTP_R03_process_storyboard_3x4.png'))
(SITE / 'process.json').write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
tot = sum(p.stat().st_size for p in (SITE / 'img').glob('proc_*.webp'))
print('figs', len(out), 'webp total', tot // 1024, 'KB; downloads', sum(p.stat().st_size for p in (SITE / 'figs').iterdir()) // 1024, 'KB')
