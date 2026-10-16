"""Capture the process-sequence figures from the browser simulation (headless Chromium, SwiftShader).
For each entry of process_figs.FIGS: jump to the step, fast-forward to the state, set the camera, render the WebGL
canvas (no HUD) and save it as PNG, plus the pose JSON used by the per-step STEP builder.

usage: python3 capture_process.py SITE OUT [preview|final] [P01,P02,...]"""
import base64
import json
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from process_figs import FIGS  # noqa: E402

SITE = Path(sys.argv[1])
OUT = Path(sys.argv[2])
MODE = sys.argv[3] if len(sys.argv) > 3 else 'final'
ONLY = set(sys.argv[4].split(',')) if len(sys.argv) > 4 else None
THREE = Path('/tmp/claude-0/-home-claude/df011815-cf4a-566b-ba83-c5996066a900/scratchpad/three/package/build/three.min.js')
VW, VH, DSF = (960, 600, 1) if MODE == 'preview' else (1600, 1000, 1.5)
(OUT / 'figs').mkdir(parents=True, exist_ok=True)
(OUT / 'poses').mkdir(parents=True, exist_ok=True)

FULL = ('#simcanvas{position:fixed!important;inset:0!important;width:100vw!important;height:100vh!important;'
        'max-height:none!important;aspect-ratio:auto!important;border-radius:0!important;z-index:99999!important}'
        '#hud,.camctl,#banner{display:none!important}')

CAMJS = '(cam) => window.ctpSim.figCam(cam)'

srv = subprocess.Popen([sys.executable, '-m', 'http.server', '8768', '--bind', '127.0.0.1'], cwd=SITE,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.0)
errs, meta = [], []
try:
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
        ctx = b.new_context(viewport={'width': VW, 'height': VH}, device_scale_factor=DSF, color_scheme='light')
        ctx.route('https://cdn.jsdelivr.net/npm/three@0.147.0/build/three.min.js',
                  lambda r: r.fulfill(path=str(THREE), content_type='application/javascript'))
        ctx.route('https://fonts.googleapis.com/**', lambda r: r.abort())
        pg = ctx.new_page()
        pg.on('console', lambda m: errs.append(f'{m.type}: {m.text}') if m.type in ('error', 'warning') else None)
        pg.on('pageerror', lambda e: errs.append(f'pageerror: {e}'))
        pg.goto('http://127.0.0.1:8768/_local_test.html#sim')
        pg.wait_for_function('window.ctpSim !== undefined', timeout=90000)
        pg.add_style_tag(content=FULL)
        pg.wait_for_timeout(1500)
        for f in FIGS:
            if ONLY and f['id'] not in ONLY:
                continue
            t0 = time.time()
            pg.evaluate('(k) => window.ctpSim.jump(k, false)', f['step'])
            if f.get('anomaly'):
                pg.evaluate('() => { window.ctpSim.anomaly(); window.ctpSim.state.running = false; }')
            k = pg.evaluate('([c]) => window.ctpSim.ff(c, 400000)', [f['until']])
            ok = pg.evaluate('(c) => { const S = window.ctpSim; return !!(new Function("s", "h", "return " + c))(S.state, S.head); }', f['until'])
            pg.evaluate('() => { window.ctpSim.state.running = false; }')
            pg.wait_for_timeout(250)
            tgt = pg.evaluate(CAMJS, f['cam'])
            pg.wait_for_timeout(250)
            url = pg.evaluate('() => { window.ctpSim.render(); return document.querySelector("#simgl").toDataURL("image/png"); }')
            png = base64.b64decode(url.split(',', 1)[1])
            (OUT / 'figs' / f"{f['id']}.png").write_bytes(png)
            pose = pg.evaluate('() => window.ctpSim.pose()')
            pose.update(id=f['id'], no=f['no'], title=f['title'])
            (OUT / 'poses' / f"{f['id']}.json").write_text(json.dumps(pose, ensure_ascii=False), encoding='utf-8')
            info = pg.evaluate('''() => { const s = window.ctpSim.state, h = window.ctpSim.head;
                return { t: +s.t.toFixed(1), step: s.step, phase: s.phase, tool: h.tool, x: +h.x.toFixed(1), y: +h.y.toFixed(1),
                         z: +h.z.toFixed(1), rot: +h.rot.toFixed(1), tilt: +h.tilt.toFixed(2), slide: +h.slide.toFixed(1) }; }''')
            size = pg.evaluate('() => [document.querySelector("#simgl").width, document.querySelector("#simgl").height]')
            meta.append(dict(id=f['id'], no=f['no'], title=f['title'], tool=f['tool'], note=f['note'], ok=ok, ff_steps=k,
                             sim=info, cam_target=[round(v, 1) for v in tgt], px=size))
            print(f"{f['id']} {'OK ' if ok else 'NOT REACHED'} {time.time() - t0:5.1f}s {json.dumps(info, ensure_ascii=False)} px={size}")
        b.close()
finally:
    srv.terminate()
mp = OUT / 'figs' / 'meta.json'
if ONLY and mp.exists():                                   # partial re-capture: merge into the existing list
    old = {m['id']: m for m in json.loads(mp.read_text(encoding='utf-8'))}
    old.update({m['id']: m for m in meta})
    meta = [old[k] for k in sorted(old)]
mp.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding='utf-8')
print('console:', errs[:10])
