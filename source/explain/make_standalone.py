"""Standalone explainer: one HTML file that opens offline from disk (file://).
- drawing, 3D and process images are embedded as data URIs; three.js r147 and the simulation scene are inline
- download links point into the package folders, so they work when the four ZIPs are extracted into one folder and
  this file is opened from the CTP_R03_package root

usage: python3 make_standalone.py SITE OUT_HTML [THREE_MIN_JS]"""
import base64
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = HERE.parent / 'sim'
SITE = Path(sys.argv[1])
OUT = Path(sys.argv[2])
THREE = Path(sys.argv[3]) if len(sys.argv) > 3 else Path(
    '/tmp/claude-0/-home-claude/df011815-cf4a-566b-ba83-c5996066a900/scratchpad/three/package/build/three.min.js')
FOLD = {'D-01': 'D-01_Layout', 'D-02': 'D-02_Tool03_Assembly', 'D-03': 'D-03_Bench_Section', 'D-04': 'D-04_Tool03_Parts',
        'D-09': 'D-09_Tool02_Outline'}


def uri(p):
    mt = {'.webp': 'image/webp', '.png': 'image/png'}[p.suffix]
    return f'data:{mt};base64,' + base64.b64encode(p.read_bytes()).decode()


d = json.loads((SITE / 'data.json').read_text(encoding='utf-8'))
proc = json.loads((SITE / 'process.json').read_text(encoding='utf-8'))
for sh in d['sheets']:
    sh['img'] = uri(SITE / sh['img'])
    sh['img3d'] = uri(SITE / sh['img3d'])
for f in proc['figs']:
    f['img'] = uri(SITE / f['img'])
    f['big'] = f['img']                                                   # lightbox shows the embedded picture
    f['png'] = f"Process_Sequence/figures/CTP_R03_process_{f['id']}.png"  # download = original PNG in the package
proc['boards'] = dict(png='Process_Sequence/storyboard/CTP_R03_process_storyboard_4x3.png',
                      pdf='Process_Sequence/storyboard/CTP_R03_process_storyboard_4x3.pdf',
                      png_portrait='Process_Sequence/storyboard/CTP_R03_process_storyboard_3x4.png')
d['process'] = proc
d['downloads'] = dict(all='00_ALL/CTP_R03_drawings_all_12_sheets.pdf', video='00_ALL/CTP_R03_process_concept_video.mp4',
                      ks='00_ALL/D-04_KS_rationale_R03.pdf', dwg={k: f'{v}/drawings/{k}_R03.pdf' for k, v in FOLD.items()},
                      note='내려받기 링크와 원본 PNG는 ZIP 4개를 한 폴더에 풀고 CTP_R03_package 폴더 안의 이 파일을 열었을 때 열려요. '
                           '그림·3D·시뮬레이션은 이 파일만으로 인터넷 없이 볼 수 있어요.')
data = json.dumps(d, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')

page = (HERE / 'page.html').read_text(encoding='utf-8')
page = page.replace('/*DATA*/', data)
page = page.replace('/*SIMCSS*/', (SIM / 'sim.css').read_text(encoding='utf-8'))
page = page.replace('<!--SIMHTML-->', (SIM / 'sim.html').read_text(encoding='utf-8'))
page = page.replace('/*SIMJS*/', (SIM / 'sim.js').read_text(encoding='utf-8'))
assert '/*SIM' not in page and '<!--SIMHTML-->' not in page

i = page.index('<div class="wrap">')
head, body = page[:i], page[i:]
three = THREE.read_text(encoding='utf-8')
assert '</script' not in three.lower()
scene = (SITE / 'sim' / 'scene.json').read_text(encoding='utf-8').replace('</', '<\\/')
j = body.index('id="dwg-data">')
k = body.index('</script>', j) + len('</script>')
body = (body[:k] + '\n<script type="application/json" id="sim-scene">' + scene + '</script>\n'
        + '<script>/* three.js r147 (MIT License, Copyright 2010-2022 Three.js Authors) */\n' + three + '\n</script>' + body[k:])
html = ('<!doctype html>\n<html lang="ko">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<style>body{margin:0}</style>\n' + head + '</head>\n<body>\n' + body + '\n</body>\n</html>\n')
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(html, encoding='utf-8')
print(OUT.name, round(OUT.stat().st_size / 2**20, 2), 'MiB')
