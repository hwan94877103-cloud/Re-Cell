"""Inject data.json and the simulation (sim.css / sim.html / sim.js) into page.html ->
SITE/index.html (artifact fragment) and SITE/_local_test.html (full skeleton for local checks)."""
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = HERE.parent / 'sim'
SITE = Path(sys.argv[1])
import json
_d = json.loads((SITE / 'data.json').read_text(encoding='utf-8'))
if (SITE / 'process.json').exists():                       # process-sequence figures (process_assets.py)
    _d['process'] = json.loads((SITE / 'process.json').read_text(encoding='utf-8'))
PKG = Path(sys.argv[2]) if len(sys.argv) > 2 else None   # built package folder (CTP_R03_package) for the downloads
if PKG and PKG.exists():
    dl = SITE / 'dl'
    dl.mkdir(exist_ok=True)
    pairs = {'CTP_R03_drawings_all_12_sheets.pdf': PKG / '00_ALL' / 'CTP_R03_drawings_all_12_sheets.pdf',
             'CTP_R03_process_concept_video.mp4': PKG / '00_ALL' / 'CTP_R03_process_concept_video.mp4',
             'D-04_KS_rationale_R03.pdf': PKG / '00_ALL' / 'D-04_KS_rationale_R03.pdf'}
    folders = {'D-01': 'D-01_Layout', 'D-02': 'D-02_Tool03_Assembly', 'D-03': 'D-03_Bench_Section', 'D-04': 'D-04_Tool03_Parts',
               'D-09': 'D-09_Tool02_Outline'}
    for k, f in folders.items():
        pairs[f'{k}_R03.pdf'] = PKG / f / 'drawings' / f'{k}_R03.pdf'
    for n, src in pairs.items():
        shutil.copy(src, dl / n)
    _d['downloads'] = dict(all='dl/CTP_R03_drawings_all_12_sheets.pdf', video='dl/CTP_R03_process_concept_video.mp4',
                           ks='dl/D-04_KS_rationale_R03.pdf', dwg={k: f'dl/{k}_R03.pdf' for k in folders})
data = json.dumps(_d, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
page = (HERE / 'page.html').read_text(encoding='utf-8')
page = page.replace('/*DATA*/', data)
page = page.replace('/*SIMCSS*/', (SIM / 'sim.css').read_text(encoding='utf-8'))
page = page.replace('<!--SIMHTML-->', (SIM / 'sim.html').read_text(encoding='utf-8'))
page = page.replace('/*SIMJS*/', (SIM / 'sim.js').read_text(encoding='utf-8'))
assert '/*SIM' not in page and '<!--SIMHTML-->' not in page
(SITE / 'index.html').write_text(page, encoding='utf-8')
(SITE / 'sim').mkdir(exist_ok=True)
shutil.copy(SIM / 'scene.json', SITE / 'sim' / 'scene.json')
skel = ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
        '<style>:root{color-scheme:light}body{margin:0;font:14px system-ui}img{max-width:100%}[hidden]{display:none!important}</style>'
        '</head><body>' + page + '</body></html>')
(SITE / '_local_test.html').write_text(skel, encoding='utf-8')
print('index.html', len(page.encode('utf-8')) // 1024, 'KB; scene.json', (SITE / 'sim' / 'scene.json').stat().st_size // 1024, 'KB')
