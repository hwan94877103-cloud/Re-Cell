/* CTP R03 process simulation (concept). Steps 4-10 with tools 01 / 02 / 03 on one gantry.
   Kinematics: trapezoidal axis profiles, travel height from the boxes under the path (tool and load footprints).
   Physics (step 9): assumed 4-node-per-cell heat network and assumed adhesive strength curve, heating/peel controller
   (v0.3: do not pull harder, keep heating). Steps 4-7 use assumed geometry (virtual cover, screws, electronics,
   coolant ports, busbar pieces) and assumed times. Every number is a design assumption. */
(() => {
  'use strict';
  const THREE_URLS = ['https://cdn.jsdelivr.net/npm/three@0.147.0/build/three.min.js',
    'https://unpkg.com/three@0.147.0/build/three.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js'];
  const SCENE_URL = 'sim/scene.json';
  const $ = (s) => document.querySelector(s);
  const el = (tag, cls, txt) => { const e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const lerp = (a, b, t) => a + (b - a) * t;
  const ease = (t) => { t = clamp(t, 0, 1); return t * t * (3 - 2 * t); };
  const fmt = (v, d = 0) => (Number.isFinite(v) ? v.toFixed(d) : '-');
  const mmss = (t) => { t = Math.max(0, t); const m = Math.floor(t / 60), s = Math.floor(t % 60); return `${m}:${String(s).padStart(2, '0')}`; };
  const D2R = Math.PI / 180;

  // ------------------------------------------------------------------ assumed parameters
  const SLIDERS = [
    { k: 'Q', n: '코일 출력 (냉각판에 들어가는 열)', u: 'W', min: 200, max: 1200, step: 50, d: 600 },
    { k: 'Tset', n: '냉각판 온도 상한', u: '°C', min: 80, max: 200, step: 5, d: 140, hint: '광섬유 센서 기준. 이 온도에 닿으면 코일을 끊었다 켰다 해요.' },
    { k: 'T50', n: '접착이 절반으로 약해지는 온도', u: '°C', min: 50, max: 160, step: 5, d: 85, hint: '시험 전이라 정해지지 않은 값. 결과를 가장 크게 바꿔요.' },
    { k: 'Flim', n: '당김 한계 (로드셀)', u: 'N', min: 10, max: 70, step: 1, d: 35, hint: '이상 흡착력 약 57 N보다 크면 컵이 먼저 떨어져요.' },
    { k: 'theta', n: '필링 각도', u: '°', min: 0.5, max: 4, step: 0.25, d: 2, hint: '가정 형상에서 3.15°에 블록 경계 부재와 닿아요.' },
    { k: 'Tir', n: '셀 윗면 온도 한계 (IR)', u: '°C', min: 35, max: 75, step: 1, d: 55, hint: '넘으면 가열을 멈춰요.' },
    { k: 'mCover', n: '커버 무게 (가정)', u: 'kg', min: 10, max: 40, step: 1, d: 25, hint: '02가 커버를 들 때 Z축 하중 계산에 써요. 같은 크기 3 mm 알루미늄 판이면 약 29 kg.' },
  ];
  const FIXED = {
    hyst: 5, Tem: 80, TbWarn: 80, w: 6, Fcold: 400, Framp: 8, kp: 0.15, rate: 0.5, Fpad: 404, mCell: 0.85, Fsuc: 56.5,
    tmax: 300, vxy: 400, axy: 800, vz: 200, az: 600, vapp: 20, app: 15, tLock: 1.0, tVac: 0.8, tRel: 0.5, tMeas: 5.0,
    clr: 50, Qanom: 1500, dTem: 0.5, tRate: 3, padRelease: true,
    tScrew: 6, tWire: 5, tElec: 10, tSuck: 60, tPurge: 30, vSeal: 20, vCutZ: 5, vCut: 10, vHop: 100, vRot: 90, vSlide: 100,
    m02: 10, mHead: 3.22, m03: 3.38, Zload: 40, cupD: 80, dpCover: 60,
  };
  const PRM = Object.assign({}, FIXED, Object.fromEntries(SLIDERS.map((s) => [s.k, s.d])));
  const TH = { Cp: 36, Ca: 9, Cb: 50, Cc: 800, Gpp: 3.0, Gpx: 0.11, Gpa: 12, Gab: 10, Gbc: 2.5, Gcc: 1.2, Gpamb: 0.3,
    Gaamb: 0.05, Gcamb: 0.05, Gair: 0.6, Tamb: 25 };
  const DT = 0.05;
  const N = 24;
  const STEPS = [
    { k: 's4', n: '4', t: '커버 열기', tool: '01→02' }, { k: 's5', n: '5', t: '배선·버스바', tool: '01/02' },
    { k: 's6', n: '6', t: '전장품', tool: '01' }, { k: 's7', n: '7', t: '냉각수', tool: '02' },
    { k: 's9', n: '9', t: '셀 분리', tool: '03' }, { k: 's10', n: '10', t: '측정·분류', tool: '03' },
  ];
  const TOOLNAME = { 0: '없음', 1: '01 나사 해체 헤드 (외형)', 2: '02 절단·흡착', 3: '03 셀 분리' };

  let THREE = null, C = null, OBS = [], st = null, V = null, H = null;
  const label = (i) => (i >= 12 ? 'B' : 'A') + ((i % 12) + 1);
  const rowOf = (i) => (i >= 12 ? 1 : 0);
  const jOf = (i) => (i % 12) - 6;
  const keyOf = (i) => (i >= 12 ? 'B' : 'A') + (jOf(i) >= 0 ? '+' : '') + jOf(i);
  const cellXY = (i) => [C.BX + C.ROW_X[rowOf(i)], C.BY + C.PITCH * jOf(i)];
  const rotXY = (v, deg) => { const c = Math.cos(deg * D2R), s = Math.sin(deg * D2R); return [v[0] * c - v[1] * s, v[0] * s + v[1] * c]; };
  const M4 = () => new THREE.Matrix4();

  // ------------------------------------------------------------------ motion profiles
  function trap(D, v, a) {
    const ta = v / a, da = 0.5 * a * ta * ta;
    if (D <= 1e-9) return { T: 0, s: () => 0 };
    if (2 * da >= D) {
      const tp = Math.sqrt(D / a);
      return { T: 2 * tp, s: (t) => (t < tp ? 0.5 * a * t * t : D - 0.5 * a * (2 * tp - t) ** 2) };
    }
    const tc = (D - 2 * da) / v;
    return { T: 2 * ta + tc, s: (t) => (t < ta ? 0.5 * a * t * t : t < ta + tc ? da + v * (t - ta) : D - 0.5 * a * (2 * ta + tc - t) ** 2) };
  }

  // ------------------------------------------------------------------ state
  function freshState() {
    const s = {
      t: 0, running: false, speed: 5, auto: true,
      Tp: new Float64Array(N).fill(TH.Tamb), Ta: new Float64Array(N).fill(TH.Tamb),
      Tb: new Float64Array(N).fill(TH.Tamb), Tc: new Float64Array(N).fill(TH.Tamb),
      present: new Uint8Array(N).fill(1), status: new Array(N).fill('in'),
      cellM: [], rel: new Array(N).fill(null), falls: [],
      coilOn: false, coilZone: -1, air: false, anomaly: -1, chip: false, suck: false,
      queue: [], act: null, phase: '대기', step: '', sub: '',
      desc: '▶ 시작을 누르면 커버 나사 해체(01)부터 전체 공정을 돌려요. 위 단계 버튼을 누르면 그 단계로 바로 가요.',
      target: -1, next: 6, sep: null, cycle: null, records: [], events: [], series: null, lastSeries: null,
      rateT: new Float64Array(N), dTcNow: new Float64Array(N),
      binCount: 0, tankCount: 0, drops: [], travelMax: 0, emergency: null, emLast: null, emCells: new Set(), banner: null,
      stepDone: new Set(), stepT: {}, stepNow: null,
      screw: new Uint8Array(C.SCREWS.length).fill(1), bar: new Uint8Array(C.BARS.length).fill(1),
      cover: { state: 'on', M: M4(), rel: null }, elec: { state: 'on', M: M4(), rel: null, fall: null },
      seal: { cut: 0, total: 0, skip: 0, segs: [] }, toolChanges: 0, toolChangeT: 0, cnt: { screw: 0, bar: 0 },
      warnOnce: new Set(), prepDone: false,
    };
    for (let i = 0; i < N; i++) s.cellM.push(M4());
    return s;
  }
  function freshHead() { return { x: C.HOME[0], y: C.HOME[1], z: C.HOME[2], rot: 0, tilt: 0, tool: 0, slide: 80, cell: -1, carry: null, vac: 0 }; }
  function log(m, alert) { st.events.push({ t: st.t, m, alert: !!alert }); if (st.events.length > 120) st.events.shift(); }

  function headMatrix(out) {
    const R = M4().makeRotationZ(H.rot * D2R).multiply(M4().makeRotationY(H.tilt * D2R));
    return (out || M4()).makeTranslation(H.x, H.y, H.z).multiply(R);
  }
  function parkMatrix(n, out) { const p = C.PARK[n]; return (out || M4()).makeTranslation(p[0], p[1], p[2] + C.DOCK[n]); }
  function toolMatrix(n, out) { return H.tool === n ? headMatrix(out) : parkMatrix(n, out); }
  const tm = () => headMatrix();

  // ------------------------------------------------------------------ obstacles and travel height
  function dynObstacles() {
    const o = OBS.slice();
    for (const n of [1, 2, 3]) {
      if (H.tool === n) continue;
      const b = C.TOOLBB[n], p = C.PARK[n], dz = p[2] + C.DOCK[n];
      o.push({ n: `${n === 1 ? '01' : n === 2 ? '02' : '03'} 공구 거치`, b: [b[0] + p[0], b[1] + p[0], b[2] + p[1], b[3] + p[1], b[4] + dz, b[5] + dz] });
    }
    const cb = C.COVER.body;
    if (st.cover.state === 'on') o.push({ n: '커버', b: cb });
    if (st.cover.state === 'table') {
      const p = new THREE.Vector3().setFromMatrixPosition(st.cover.M), hx = (cb[3] - cb[2]) / 2, hy = (cb[1] - cb[0]) / 2;
      const cx = (cb[0] + cb[1]) / 2 + p.x, cy = (cb[2] + cb[3]) / 2 + p.y;
      o.push({ n: '커버 (거치대)', b: [cx - hx, cx + hx, cy - hy, cy + hy, cb[4] + p.z, cb[5] + p.z] });
    }
    if (st.elec.state === 'on') { const e = C.ELEC; o.push({ n: '전장품', b: e }); }
    return o;
  }
  function footprints() {
    // rectangles around the head (half sizes in world XY) with the distance from the tilt centre down to their bottom
    const r = Math.abs(H.rot % 180) > 45 && Math.abs(H.rot % 180) < 135;
    const out = [];
    if (H.tool === 0) out.push({ hx: 60, hy: 60, drop: 70 });
    if (H.tool === 1) {
      out.push({ hx: 92, hy: 92, drop: -C.TOOLBB[1][4] });
      if (H.carry === 'elec') { const e = C.ELEC; out.push({ hx: (e[1] - e[0]) / 2, hy: (e[3] - e[2]) / 2, drop: -C.TOOLBB[1][4] + (e[5] - e[4]) }); }
    }
    if (H.tool === 2) {
      const c = Math.abs(Math.cos(H.rot * D2R)), s = Math.abs(Math.sin(H.rot * D2R));
      out.push({ hx: c * 341 + s * 240, hy: s * 341 + c * 240, drop: Math.max(C.DOCK[2], -(C.T2.tip_z - C.DOCK[2]) - H.slide) });
      if (H.carry === 'cover') { const cb = C.COVER.body, a = (cb[1] - cb[0]) / 2, b = (cb[3] - cb[2]) / 2; out.push({ hx: c * a + s * b, hy: s * a + c * b, drop: C.DOCK[2] + C.COVER.h }); }
    }
    if (H.tool === 3) out.push({ hx: 92, hy: 75, drop: C.TILT + (H.cell >= 0 ? C.CELL.H : 0) });
    return out;
  }
  function safeZ(x0, y0, x1, y1) {
    const fps = footprints(), obs = dynObstacles(), m = 30;
    let need = 0, who = '', top = 0;
    const n = Math.max(2, Math.ceil(Math.hypot(x1 - x0, y1 - y0) / 25));
    for (let k = 0; k <= n; k++) {
      const x = lerp(x0, x1, k / n), y = lerp(y0, y1, k / n);
      for (const f of fps) for (const o of obs) {
        const b = o.b;
        if (x + f.hx + m > b[0] && x - f.hx - m < b[1] && y + f.hy + m > b[2] && y - f.hy - m < b[3]) {
          const z = b[5] + PRM.clr + f.drop;
          if (z > need) { need = z; who = o.n; top = b[5]; }
        }
      }
    }
    return { z: need, top, who };
  }
  function inReach(x, y) { return x >= C.X[0] - 0.5 && x <= C.X[1] + 0.5 && y >= C.Y[0] - 0.5 && y <= C.Y[1] + 0.5; }
  function warnOnce(key, msg) { if (!st.warnOnce.has(key)) { st.warnOnce.add(key); log(msg, true); } }

  // ------------------------------------------------------------------ actions
  function startAct(a) {
    if (a.stp && a.stp !== st.step) {
      if (st.step) { st.stepDone.add(st.step); if (st.stepNow) st.stepT[st.step] = (st.stepT[st.step] || 0) + st.t - st.stepNow; }
      st.step = a.stp; st.stepNow = st.t;
    }
    if (a.ph) { st.phase = a.ph; st.sub = a.ph; }
    if (a.desc) st.desc = typeof a.desc === 'function' ? a.desc() : a.desc;
    if (a.begin) a.begin();
  }
  function Seq(list) {
    let i = -1, cur = null;
    return {
      step(dt) {
        for (let g = 0; g < 40; g++) {
          if (!cur) { i++; if (i >= list.length) return true; cur = list[i]; startAct(cur); }
          if (cur.step(dt)) { cur = null; dt = 0; continue; }
          return false;
        }
        return false;
      },
    };
  }
  const tag = (a, o) => { if (o) { if (o.ph) a.ph = o.ph; if (o.desc) a.desc = o.desc; if (o.stp) a.stp = o.stp; } return a; };
  function A_move(to, v, a, o) {
    let p0, d, prof, D, t = 0;
    return tag({
      begin() {
        p0 = [H.x, H.y, H.z];
        const p1 = [to.x ?? p0[0], to.y ?? p0[1], to.z ?? p0[2]];
        if (!inReach(p1[0], p1[1])) warnOnce(`reach${Math.round(p1[0])},${Math.round(p1[1])}`, `갠트리 행정 밖 위치 요청: X ${fmt(p1[0])}, Y ${fmt(p1[1])}`);
        p1[0] = clamp(p1[0], C.X[0], C.X[1]); p1[1] = clamp(p1[1], C.Y[0], C.Y[1]);
        p1[2] = clamp(p1[2], C.ZT[0], C.ZT[1]);
        d = [p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]];
        D = Math.hypot(d[0], d[1], d[2]); prof = trap(D, v, a); t = 0;
      },
      step(dt) {
        t += dt;
        const s = D > 1e-9 ? prof.s(Math.min(t, prof.T)) / D : 1;
        H.x = p0[0] + d[0] * s; H.y = p0[1] + d[1] * s; H.z = p0[2] + d[2] * s;
        return t >= prof.T;
      },
    }, o);
  }
  function A_travel(x, y, zEnd, o = {}) {
    let seq;
    return tag({
      begin() {
        const need = safeZ(H.x, H.y, x, y);
        let zs = Math.max(H.z, need.z, zEnd + (o.slow ? PRM.app : 0));
        if (zs > C.ZT[1] + 0.5) { warnOnce('ztop' + need.who, `이동 높이 부족: ${need.who} 위를 지나려면 기울임축 Z ${fmt(need.z)} 필요 (한계 ${C.ZT[1]})`); zs = C.ZT[1]; }
        st.travelMax = Math.max(st.travelMax, zs);
        const list = [];
        if (zs - H.z > 0.5) list.push(A_move({ z: zs }, PRM.vz, PRM.az));
        list.push(A_move({ x, y }, PRM.vxy, PRM.axy));
        if (o.slow) { list.push(A_move({ z: zEnd + PRM.app }, PRM.vz, PRM.az)); list.push(A_move({ z: zEnd }, PRM.vapp, 200)); }
        else list.push(A_move({ z: zEnd }, PRM.vz, PRM.az));
        seq = Seq(list);
      },
      step(dt) { return seq.step(dt); },
    }, o);
  }
  function A_wait(T, o = {}) { let t = 0; return tag({ begin() { t = 0; }, step(dt) { t += dt; return t >= T; } }, o); }
  function A_do(fn, o = {}) { return tag({ step() { fn(); return true; } }, o); }
  function A_rot(deg, o = {}) {
    let r0, t = 0, T = 0;
    return tag({ begin() { r0 = H.rot; T = Math.abs(deg - r0) / PRM.vRot; t = 0; },
      step(dt) { t += dt; H.rot = T > 0 ? lerp(r0, deg, ease(t / T)) : deg; return t >= T; } }, o);
  }
  function A_slide(target, o = {}) {
    let s0, t = 0, T = 0;
    return tag({ begin() { s0 = H.slide; T = Math.abs(target - s0) / PRM.vSlide; t = 0; },
      step(dt) { t += dt; H.slide = T > 0 ? lerp(s0, target, ease(t / T)) : target; return t >= T; } }, o);
  }
  function A_lock(n, o = {}) {
    let t = 0;
    return tag({ begin() { t = 0; }, step(dt) { t += dt; if (t >= PRM.tLock) { H.tool = n; H.slide = 80; log(`${n === 1 ? '01' : n === 2 ? '02' : '03'} 공구 결합`); return true; } return false; } }, o);
  }
  function A_unlock(o = {}) {
    let t = 0;
    return tag({ begin() { t = 0; }, step(dt) { t += dt; if (t >= PRM.tLock) { H.tool = 0; return true; } return false; } }, o);
  }
  function toolChange(n, stp) {
    if (H.tool === n) return [];
    const name = (k) => (k === 1 ? '01' : k === 2 ? '02' : '03');
    const list = [];
    let t0 = 0;
    list.push(A_do(() => { t0 = st.t; }, { stp, ph: '공구 교환' }));
    const cur = () => H.tool;
    // return the current tool (decided at run time)
    list.push({ ph: '공구 교환', stp, begin() {
      const c = cur(); const q = [];
      if (c) {
        const p = C.PARK[c];
        if (c === 2) q.push(A_slide(80));
        q.push(A_rot(0), A_travel(p[0], p[1], p[2] + C.DOCK[c], { slow: true }), A_unlock(), A_move({ z: p[2] + C.DOCK[c] + 150 }, PRM.vz, PRM.az));
        st.desc = `${name(c)} 공구를 거치대에 돌려놓고 ${name(n)} 공구로 바꿔요.`;
      }
      this.seq = Seq(q);
    }, step(dt) { return this.seq.step(dt); } });
    const p = C.PARK[n];
    list.push(A_travel(p[0], p[1], p[2] + C.DOCK[n], { slow: true, ph: '공구 교환', stp, desc: `거치대의 ${name(n)} 공구 위로 가서 내려가요.` }));
    list.push(A_lock(n, { ph: '공구 교환', stp, desc: `교환기를 잠가 ${name(n)} 공구를 결합해요 (1초 가정).` }));
    list.push(A_move({ z: p[2] + C.DOCK[n] + 150 }, PRM.vz, PRM.az, { ph: '공구 교환', stp }));
    list.push(A_do(() => { st.toolChanges++; st.toolChangeT += st.t - t0; }, { stp }));
    return list;
  }

  // ------------------------------------------------------------------ cells (tool 03)
  function cellUnderCups() {
    const cup = new THREE.Vector3(0, 0, -C.TILT).applyMatrix4(tm());
    for (let i = 0; i < N; i++) {
      if (!['in', 'jig'].includes(st.status[i])) continue;
      const b = C.cells[keyOf(i)];
      const top = new THREE.Vector3((b[0] + b[1]) / 2, (b[2] + b[3]) / 2, b[5]).applyMatrix4(st.cellM[i]);
      if (Math.abs(top.x - cup.x) < 20 && Math.abs(top.y - cup.y) < 10 && Math.abs(top.z - cup.z) < 6) return i;
    }
    return -1;
  }
  function attach(i) {
    H.cell = i;
    st.rel[i] = tm().invert().multiply(st.cellM[i]);
    if (st.status[i] === 'jig') st.status[i] = 'carry';
    else if (st.status[i] === 'in') st.status[i] = 'held';
  }
  function A_vac(on, o = {}) {
    let t = 0, v0 = 0;
    return tag({
      begin() { t = 0; v0 = H.vac; if (!on && H.cell >= 0) st.cellM[H.cell].copy(tm().multiply(st.rel[H.cell])); },
      step(dt) {
        t += dt;
        const T = on ? PRM.tVac : PRM.tRel, u = Math.min(1, t / T);
        H.vac = lerp(v0, on ? 1 : 0, u);
        if (u < 1) return false;
        if (on) { const i = cellUnderCups(); if (i >= 0) attach(i); }
        else if (H.cell >= 0) releaseCell(o.drop, o.abort);
        return true;
      },
    }, o);
  }
  function releaseCell(drop, abort) {
    const i = H.cell; H.cell = -1;
    st.cellM[i].copy(tm().multiply(st.rel[i]));
    st.rel[i] = null;
    if (st.status[i] === 'held') { st.status[i] = abort ? 'in' : 'fail'; st.cellM[i].identity(); return; }   // back onto its adhesive
    if (!drop) { st.status[i] = 'jig'; return; }
    const b = C.cells[keyOf(i)];
    const pos = new THREE.Vector3().setFromMatrixPosition(st.cellM[i]);
    const zb = b[4] + pos.z;                                   // current bottom (no rotation at release)
    let tx, ty, zr;
    if (drop === 'bin') {
      const k = st.binCount++, layer = Math.floor(k / 14), r = k % 14;
      tx = C.BIN.x; ty = C.BIN.inner[2] + 14 + 13.25 + 28.5 * r; zr = C.BIN.floor + C.CELL.H * layer;
    } else {
      const k = st.tankCount++;
      tx = C.TANK.inner[0] + 90 + 30 * k; ty = C.TANK.y; zr = C.TANK.floor;
      if (st.anomaly === i) st.anomaly = -1;
    }
    const cx = (b[0] + b[1]) / 2, cy = (b[2] + b[3]) / 2;
    st.falls.push({ i, x0: pos.x, y0: pos.y, x1: tx - cx, y1: ty - cy, zb0: zb, zr, z0: pos.z, v: 0, dz: 0, to: drop });
    st.status[i] = 'fall';
    st.drops.push({ i, to: drop, h: zb - zr });
    log(`${label(i)} ${drop === 'bin' ? '회수함' : '침수조'}에 놓음: 셀 바닥 ${fmt(zb)} mm에서 ${fmt((zb - zr) / 1000, 2)} m 낙하`, drop === 'tank');
  }
  function stepFalls(dt) {
    for (const f of st.falls) {
      if (f.done) continue;
      f.v += 9810 * dt; f.dz += f.v * dt;
      const H0 = f.zb0 - f.zr, u = H0 > 0 ? Math.min(1, f.dz / H0) : 1;
      st.cellM[f.i].makeTranslation(lerp(f.x0, f.x1, u), lerp(f.y0, f.y1, u), f.z0 - Math.min(f.dz, H0));
      if (u >= 1) { f.done = true; st.status[f.i] = f.to; }
    }
    st.falls = st.falls.filter((f) => !f.done);
    const e = st.elec.fall;
    if (e && !e.done) {
      e.v += 9810 * dt; e.dz += e.v * dt;
      const u = e.h > 0 ? Math.min(1, e.dz / e.h) : 1;
      st.elec.M.makeTranslation(e.x, e.y, e.z0 - Math.min(e.dz, e.h));
      if (u >= 1) { e.done = true; st.elec.state = 'bin'; }
    }
  }
  function setTiltPose(s, thDeg) {
    const phi = s.sgn * thDeg * D2R;
    const vx = s.cx - s.pivotX, vz = C.ZC + C.TILT - s.pivotZ;
    H.x = s.pivotX + vx * Math.cos(phi) + vz * Math.sin(phi);
    H.z = s.pivotZ - vx * Math.sin(phi) + vz * Math.cos(phi);
    H.tilt = phi / D2R;
  }
  function A_relevel(i, dz, T, o = {}) {
    let x0, z0, t0, t = 0; const [cx] = cellXY(i);
    return tag({ begin() { x0 = H.x; z0 = H.z; t0 = H.tilt; t = 0; },
      step(dt) { t += dt; const u = ease(t / T); H.x = lerp(x0, cx, u); H.z = lerp(z0, C.ZC + C.TILT + dz, u); H.tilt = lerp(t0, 0, u); return t >= T; } }, o);
  }

  // ------------------------------------------------------------------ heat network
  const dTp = new Float64Array(N), dTa = new Float64Array(N), dTb = new Float64Array(N), dTc = new Float64Array(N);
  function thermal(dt) {
    const { Tp, Ta, Tb, Tc } = st;
    const si = st.sep ? st.sep.i : -1;
    for (let i = 0; i < N; i++) {
      const r = rowOf(i), j = i % 12;
      let q = TH.Gpa * (Ta[i] - Tp[i]) + TH.Gpamb * (TH.Tamb - Tp[i]) + TH.Gpx * (Tp[r ? i - 12 : i + 12] - Tp[i]);
      if (j > 0) q += TH.Gpp * (Tp[i - 1] - Tp[i]);
      if (j < 11) q += TH.Gpp * (Tp[i + 1] - Tp[i]);
      if (st.coilOn && st.coilZone === i) q += PRM.Q;
      dTp[i] = q / TH.Cp;
      const pres = st.present[i];
      dTa[i] = (TH.Gpa * (Tp[i] - Ta[i]) + (pres ? TH.Gab * (Tb[i] - Ta[i]) : TH.Gaamb * (TH.Tamb - Ta[i]))) / TH.Ca;
      if (pres) {
        dTb[i] = (TH.Gab * (Ta[i] - Tb[i]) + TH.Gbc * (Tc[i] - Tb[i])) / TH.Cb;
        let qc = TH.Gbc * (Tb[i] - Tc[i]) + TH.Gcamb * (TH.Tamb - Tc[i]);
        if (j > 0 && st.present[i - 1]) qc += TH.Gcc * (Tc[i - 1] - Tc[i]);
        if (j < 11 && st.present[i + 1]) qc += TH.Gcc * (Tc[i + 1] - Tc[i]);
        if (st.air && si >= 0 && rowOf(si) === r && Math.abs(i - si) === 1) qc += TH.Gair * (TH.Tamb - Tc[i]);
        if (st.anomaly === i) qc += PRM.Qanom;
        dTc[i] = qc / TH.Cc;
      } else {
        const g = st.status[i] === 'tank' ? 5 : 0.15;
        dTb[i] = (TH.Gbc * (Tc[i] - Tb[i]) + g * 0.3 * (TH.Tamb - Tb[i])) / TH.Cb;
        let qc = TH.Gbc * (Tb[i] - Tc[i]) + g * (TH.Tamb - Tc[i]);
        if (st.anomaly === i) qc += PRM.Qanom;
        dTc[i] = qc / TH.Cc;
      }
    }
    for (let i = 0; i < N; i++) {
      Tp[i] += dTp[i] * dt; Ta[i] += dTa[i] * dt; Tb[i] += dTb[i] * dt; Tc[i] += dTc[i] * dt;
      st.dTcNow[i] = dTc[i]; st.rateT[i] = dTc[i] > PRM.dTem ? st.rateT[i] + dt : 0;
    }
  }

  // ------------------------------------------------------------------ separation controller (step 9)
  function A_separate(i) {
    const r = rowOf(i), [cx] = cellXY(i);
    const s0 = { i, p: 0, Fcmd: 0, F: 0, Fneed: 0, hold: false, cx, sgn: r ? 1 : -1,
      pivotX: r ? cx + C.CELL.L / 2 : cx - C.CELL.L / 2, pivotZ: C.ZC - C.CELL.H };
    let lastSample = -1;
    return {
      ph: '가열·필링', stp: 's9', desc: () => sepDesc(),
      begin() {
        if (H.cell !== i) { log(`${label(i)} 흡착 확인 실패`, true); st.queue.unshift(A_do(() => cycleDone(false, '흡착 실패'))); st.sep = null; return; }
        st.sep = Object.assign({}, s0, { t0: st.t });
        st.coilZone = i; st.coilOn = true; st.air = true;
        st.series = { i, rows: [] }; lastSample = -1;
        log(`${label(i)} 구역 가열 시작, 이웃 셀 냉각 공기 켬`);
      },
      step(dt) {
        const s = st.sep;
        if (!s) return true;
        const T = st.t - s.t0;
        if (st.Tp[i] >= PRM.Tset || st.Tc[i] >= PRM.Tir) st.coilOn = false;
        else if (st.Tp[i] < PRM.Tset - PRM.hyst && st.Tc[i] < PRM.Tir - 1) st.coilOn = true;
        const Fb = PRM.Fcold / (1 + Math.exp((st.Ta[i] - PRM.T50) / PRM.w));
        s.Fneed = Fb * (1 - s.p) + (PRM.padRelease ? 0 : PRM.Fpad) + PRM.mCell * 9.81;
        s.Fcmd = Math.min(PRM.Flim, s.Fcmd + PRM.Framp * dt);
        s.F = Math.min(s.Fcmd, s.Fneed);
        const wasHold = s.hold;
        s.hold = s.Fcmd >= PRM.Flim - 1e-6 && s.Fneed > s.Fcmd;
        if (s.hold && !wasHold && !s.holdLogged) { s.holdLogged = true; log(`당김 한계 ${PRM.Flim} N 도달: 더 당기지 않고 가열 유지`); }
        if (s.F > PRM.Fsuc * H.vac + 1e-6) return endSep(false, `흡착 풀림 (당김 ${fmt(s.F, 1)} N > 이상 흡착력 ${fmt(PRM.Fsuc, 1)} N)`);
        const dp = Math.min(PRM.kp * Math.max(0, s.Fcmd - s.Fneed) / PRM.Flim, PRM.rate / Math.max(PRM.theta, 0.1));
        if (dp > 0 && s.p === 0) log('접착이 약해져 필링 시작 (바깥쪽 아래 모서리 기준 회전)');
        s.p = Math.min(1, s.p + dp * dt);
        setTiltPose(s, PRM.theta * s.p);
        const c = st.cycle;
        if (c) {
          c.maxTb = Math.max(c.maxTb, st.Tb[i]); c.maxTc = Math.max(c.maxTc, st.Tc[i]);
          for (const k of [i - 1, i + 1]) if (k >= 0 && k < N && rowOf(k) === r && st.present[k]) c.maxTaN = Math.max(c.maxTaN, st.Ta[k]);
        }
        if (Math.floor(T / 0.5) !== lastSample) {
          lastSample = Math.floor(T / 0.5);
          st.series.rows.push([T, st.Tp[i], st.Ta[i], st.Tb[i], st.Tc[i], s.F, s.Fneed]);
        }
        if (s.p >= 1) return endSep(true);
        if (T > PRM.tmax) return endSep(false, `시간 초과 (${PRM.tmax}초 안에 안 떨어짐)`);
        return false;
      },
    };
  }
  function carryPlan() {
    const bz = C.BINS['13'];
    return [
      A_travel(C.MEAS.x, C.MEAS.y, C.MEAS.top + C.CELL.H + C.TILT, { slow: true, ph: '측정대', stp: 's10', desc: '측정대로 옮겨요.' }),
      A_vac(false, { ph: '측정대', stp: 's10', desc: '측정대 스프링 핀 위에 내려놓아요.' }),
      A_wait(PRM.tMeas, { ph: '측정대', stp: 's10', desc: '전압·절연 측정 (가상, 5초 가정). 값은 만들지 않았어요.' }),
      A_vac(true, { ph: '측정대', stp: 's10', desc: '다시 흡착해요.' }),
      A_travel(bz.x, bz.y, C.ZT[0], { ph: '회수함', stp: 's10', desc: '셀 회수함 위로 가서 Z축을 가장 낮게 내려요.' }),
      A_vac(false, { drop: 'bin', ph: '회수함', stp: 's10', desc: '흡착을 풀어 회수함에 놓아요.' }),
      A_move({ z: C.ZT[0] + 200 }, PRM.vz, PRM.az, { stp: 's10' }),
      A_do(() => cycleDone(true), { stp: 's10' }),
    ];
  }
  function endSep(ok, why) {
    const s = st.sep, i = s.i;
    st.coilOn = false; st.air = false; st.coilZone = -1;
    const T = st.t - s.t0;
    if (st.cycle) st.cycle.tSep = T;
    st.series.rows.push([T, st.Tp[i], st.Ta[i], st.Tb[i], st.Tc[i], s.F, s.Fneed]);
    st.lastSeries = st.series;
    st.sep = null;
    if (ok) {
      st.present[i] = 0; st.status[i] = 'carry';
      log(`${label(i)} 분리 (${fmt(T, 1)}초, 접착층 ${fmt(st.Ta[i])} °C)`);
      st.queue.push(A_relevel(i, 30, 1.5, { ph: '들어 올림', stp: 's9', desc: '떨어진 셀을 수평으로 되돌리며 들어 올려요.' }), ...carryPlan());
    } else {
      log(`${label(i)} 분리 실패: ${why}`, true);
      st.queue.push(
        A_relevel(i, 0, 1.0, { ph: '가열·필링', stp: 's9', desc: `분리 실패: ${why}. 셀을 제자리에 내려놓아요.` }),
        A_vac(false, { ph: '가열·필링', stp: 's9' }),
        A_move({ z: C.ZC + C.TILT + 150 }, PRM.vz, PRM.az, { stp: 's9' }),
        A_do(() => cycleDone(false, why), { stp: 's9' }),
      );
    }
    return true;
  }
  function sepDesc() {
    const s = st.sep; if (!s) return st.desc;
    const heat = st.coilOn ? '코일 켬' : (st.Tp[s.i] >= PRM.Tset - PRM.hyst ? '냉각판 상한이라 잠시 끔' : st.Tc[s.i] >= PRM.Tir - 1 ? '셀 윗면 한계라 잠시 끔' : '코일 끔');
    if (s.p > 0) return `${label(s.i)} 접착이 약해져 바깥쪽 아래 모서리를 축으로 기울여 떼는 중 (${fmt(s.p * 100)}%). ${heat}.`;
    if (s.hold) return `당김 한계 ${PRM.Flim} N에 닿아 더 당기지 않고 가열을 기다려요. 필요한 힘 ${fmt(s.Fneed)} N. ${heat}.`;
    return `${label(s.i)} 아래 코일만 켜고(${heat}) 당기는 힘을 천천히 올려요.`;
  }

  // ------------------------------------------------------------------ steps 4-7 (tools 01 / 02, assumed geometry)
  const hatTop = () => C.COVER.z0 + C.COVER.h;
  const tipLocal = () => C.T2.tip_z - C.DOCK[2];                 // end-mill tip below the tilt centre, slide extended
  const nozLocal = () => C.T2.nozzle_tip_z - C.DOCK[2];
  function A_grab(kind, on, o = {}) {
    let t = 0;
    return tag({ begin() { t = 0; }, step(dt) {
      t += dt; const T = kind === 'cover' ? PRM.tVac : 1.0;
      if (kind === 'cover') H.vac = on ? Math.min(1, t / T) : Math.max(0, 1 - t / T);
      if (t < T) return false;
      const obj = kind === 'cover' ? st.cover : st.elec;
      if (on) { obj.rel = tm().invert().multiply(obj.M); obj.state = 'carry'; H.carry = kind; }
      else {
        obj.M.copy(tm().multiply(obj.rel)); obj.rel = null; H.carry = null;
        if (kind === 'cover') {
          obj.state = 'table';
          const hit = coverTableClash();
          if (hit.length) warnOnce('coverclash', `거치대에 놓은 커버가 ${[...new Set(hit.map((q) => q.n))].join(', ')} ${hit.length}곳과 겹쳐요 (가정 배치, 정지 상태).`);
        }
        else {
          const p = new THREE.Vector3().setFromMatrixPosition(obj.M), e = C.ELEC, b = C.BINS['12'];
          const zb = e[4] + p.z, hgt = zb - b.floor;
          obj.state = 'fall'; obj.fall = { x: p.x, y: p.y, z0: p.z, h: hgt, v: 0, dz: 0 };
          st.drops.push({ i: -1, to: 'elec', h: hgt });
          log(`전장품을 회수함(12)에 놓음: 바닥 ${fmt(zb)} mm에서 ${fmt(hgt / 1000, 2)} m 낙하`);
        }
      }
      return true;
    } }, o);
  }
  function screwOrder() {
    const cx = (C.COVER.pack[0] + C.COVER.pack[1]) / 2, cy = (C.COVER.pack[2] + C.COVER.pack[3]) / 2;
    return C.SCREWS.map((p, k) => ({ k, a: Math.atan2(p[1] - cy, p[0] - cx) })).sort((a, b) => a.a - b.a).map((q) => q.k);
  }
  function sealPlan() {
    return C.SEAL.map((sd) => {
      const [x0, y0] = sd.p0, [x1, y1] = sd.p1, L = Math.hypot(x1 - x0, y1 - y0);
      const off = rotXY(C.T2.spindle, sd.rot);
      let ua = 0, ub = 1;
      const lim = (p0, p1, lo, hi) => {                        // u range where p0 + (p1 - p0) u stays in [lo, hi]
        const d = p1 - p0;
        if (Math.abs(d) < 1e-9) { if (p0 < lo - 1e-6 || p0 > hi + 1e-6) { ua = 1; ub = 0; } return; }
        let a = (lo - p0) / d, b = (hi - p0) / d; if (a > b) [a, b] = [b, a];
        ua = Math.max(ua, a); ub = Math.min(ub, b);
      };
      lim(x0 - off[0], x1 - off[0], C.X[0], C.X[1]); lim(y0 - off[1], y1 - off[1], C.Y[0], C.Y[1]);
      return { ...sd, L, off, ua: clamp(ua, 0, 1), ub: clamp(ub, 0, 1) };
    });
  }
  function coverPlacedBox() {
    const cb = C.COVER.body, cw = cb[3] - cb[2], cl = cb[1] - cb[0];
    const px = Math.min((C.TABLE[0] + C.TABLE[1]) / 2, C.X[1]), py = (C.TABLE[2] + C.TABLE[3]) / 2;
    return [px - cw / 2, px + cw / 2, py - cl / 2, py + cl / 2, C.TABLE[4], C.TABLE[4] + C.COVER.h];
  }
  function coverTableClash() {
    // the cover as placed on the cover table vs the static boxes and the parked tools (bounding boxes)
    const c = coverPlacedBox(), boxes = OBS.slice();
    for (const n of [1, 2, 3]) {
      const b = C.TOOLBB[n], p = C.PARK[n], dz = p[2] + C.DOCK[n];
      boxes.push({ n: `${n === 1 ? '01' : n === 2 ? '02' : '03'} 공구(거치 중)`, b: [b[0] + p[0], b[1] + p[0], b[2] + p[1], b[3] + p[1], b[4] + dz, b[5] + dz] });
    }
    return boxes.filter((o) => { const b = o.b; return b[0] < c[1] && b[1] > c[0] && b[2] < c[3] && b[3] > c[2] && b[5] > c[4] + 0.5 && b[4] < c[5] - 0.5; })
      .map((o) => ({ n: o.n === '거치대 다리' && o.b[1] < C.TABLE[0] ? '공구 거치대 다리' : o.n, b: o.b }));
  }
  function A_cut(sd, o = {}) {
    let t = 0, T = 0, p0, p1;
    return tag({ begin() {
      p0 = [lerp(sd.p0[0], sd.p1[0], sd.ua) - sd.off[0], lerp(sd.p0[1], sd.p1[1], sd.ua) - sd.off[1]];
      p1 = [lerp(sd.p0[0], sd.p1[0], sd.ub) - sd.off[0], lerp(sd.p0[1], sd.p1[1], sd.ub) - sd.off[1]];
      T = Math.hypot(p1[0] - p0[0], p1[1] - p0[1]) / PRM.vSeal; t = 0; st.chip = true; sd.cut = 0;
    }, step(dt) {
      t += dt; const u = T > 0 ? Math.min(1, t / T) : 1;
      H.x = lerp(p0[0], p1[0], u); H.y = lerp(p0[1], p1[1], u); sd.cut = u;
      st.seal.cut = st.seal.segs.reduce((a, s) => a + (s.cut || 0) * s.L * (s.ub - s.ua), 0);
      if (u >= 1) { st.chip = false; return true; }
      return false;
    } }, o);
  }
  function planProcess() {
    const q = [];
    const ph = (p, s, d) => ({ ph: p, stp: s, desc: d });
    // 4-1 screws (01)
    q.push(...toolChange(1, 's4'));
    const zHover = hatTop() + 10 - C.TOOLBB[1][4];
    const order = screwOrder();
    order.forEach((k, n) => {
      const [x, y] = C.SCREWS[k];
      q.push(A_travel(x, y, zHover, ph('나사 해체', 's4', `커버 나사 ${n + 1}/${order.length}: 01이 나사 위로 가요 (01 실제 형상은 팀원 설계, 여기선 외형 원기둥만).`)));
      q.push(A_wait(PRM.tScrew, ph('나사 해체', 's4', `나사 ${n + 1}/${order.length} 푸는 중 (${PRM.tScrew}초 가정).`)));
      q.push(A_do(() => { st.screw[k] = 0; st.cnt.screw++; }, { stp: 's4' }));
    });
    const b11 = C.BINS['11'], b12 = C.BINS['12'];
    q.push(A_travel(b11.x, b11.y, C.ZT[0] + 150, ph('나사 해체', 's4', '푼 나사를 나사·칩 회수함(11)에 넣어요.')), A_wait(1.0, { stp: 's4' }));
    // 4-2 seal cut (02)
    q.push(...toolChange(2, 's4'));
    const zCut = C.COVER.z0 - 0.5 - tipLocal();
    st.seal.segs = sealPlan(); st.seal.total = st.seal.segs.reduce((a, s) => a + s.L, 0);
    st.seal.skip = st.seal.segs.reduce((a, s) => a + s.L * (1 - Math.max(0, s.ub - s.ua)), 0);
    st.seal.segs.forEach((sd, k) => {
      if (sd.ub - sd.ua < 1e-6) return;
      const sx = lerp(sd.p0[0], sd.p1[0], sd.ua) - sd.off[0], sy = lerp(sd.p0[1], sd.p1[1], sd.ua) - sd.off[1];
      const d = `실링 절개 ${k + 1}/4변: 02 엔드밀로 커버 가장자리 안쪽(${C.COVER.cut_inset} mm)을 따라 플랜지를 잘라요 (${PRM.vSeal} mm/s 가정). 공구 세부는 미정.`;
      q.push(A_slide(80, ph('실링 절개', 's4', d)), A_rot(sd.rot, ph('실링 절개', 's4', d)));
      q.push(A_travel(sx, sy, zCut + 30, ph('실링 절개', 's4', d)), A_slide(0, ph('실링 절개', 's4', d)));
      q.push(A_move({ z: zCut }, PRM.vCutZ * 4, 200, ph('실링 절개', 's4', d)), A_cut(sd, ph('실링 절개', 's4', d)));
      q.push(A_move({ z: zCut + 30 }, PRM.vz, PRM.az, ph('실링 절개', 's4', d)));
      if (sd.ua > 1e-6 || sd.ub < 1 - 1e-6) q.push(A_do(() => log(`실링 절개 ${k + 1}변: ${fmt(sd.L * (1 - (sd.ub - sd.ua)))} mm는 갠트리 행정 밖이라 못 자름`, true), { stp: 's4' }));
    });
    // 4-3 cover lift (02)
    const cb = C.COVER.body, ccx = (cb[0] + cb[1]) / 2, ccy = (cb[2] + cb[3]) / 2;
    const zCup = hatTop() + C.DOCK[2];
    const tx = Math.min((C.TABLE[0] + C.TABLE[1]) / 2, C.X[1]), ty = (C.TABLE[2] + C.TABLE[3]) / 2;
    const zPlace = C.TABLE[4] + C.COVER.h + C.DOCK[2];
    q.push(A_slide(80, ph('커버 인양', 's4', '엔드밀을 올리고 커버 가운데로 가요.')), A_rot(0, ph('커버 인양', 's4')));
    q.push(A_travel(ccx, ccy, zCup, { slow: true, ...ph('커버 인양', 's4', 'Ø80 흡착컵 4개를 커버 윗면에 대요.') }));
    q.push(A_grab('cover', true, ph('커버 인양', 's4', '흡착 (−60 kPa 가정)으로 커버를 잡아요.')));
    q.push(A_move({ z: zCup + 60 }, PRM.vapp * 2, 200, ph('커버 인양', 's4', '커버를 천천히 들어 올려요.')));
    q.push(A_rot(90, ph('커버 인양', 's4', '거치대에 맞게 커버를 90° 돌려요.')));
    q.push(A_travel(tx, ty, zPlace, { slow: true, ...ph('커버 인양', 's4', '커버 거치대로 옮겨요.') }));
    q.push(A_grab('cover', false, ph('커버 인양', 's4', '커버를 거치대에 내려놓아요.')));
    q.push(A_move({ z: zPlace + 200 }, PRM.vz, PRM.az, { stp: 's4' }), A_rot(0, { stp: 's4' }));
    // 5-1 wiring (01)
    q.push(...toolChange(1, 's5'));
    const zWire = C.ZC + 25 - C.TOOLBB[1][4];
    const wp = [];
    for (const r of [0, 1]) for (const s of [-1, 1]) wp.push([C.BX + C.ROW_X[r] + s * 64, C.BY + 6 * C.PITCH]);
    wp.forEach(([x, y], n) => {
      q.push(A_travel(x, y, zWire, ph('배선 제거', 's5', `감지 배선·커넥터 ${n + 1}/${wp.length} (위치 가정): 01이 떼어내요.`)));
      q.push(A_wait(PRM.tWire, ph('배선 제거', 's5', `배선·커넥터 ${n + 1}/${wp.length} 떼는 중 (${PRM.tWire}초 가정).`)));
    });
    q.push(A_travel(b12.x, b12.y, C.ZT[0] + 150, ph('배선 제거', 's5', '뗀 배선을 전장품 회수함(12)에 넣어요 (가정).')), A_wait(1.0, { stp: 's5' }));
    // 5-2 busbar cuts (02)
    q.push(...toolChange(2, 's5'));
    const zTipUp = C.ZC + 12, zTipCut = C.ZC + 2.5;
    const bars = C.BARS.map((b, k) => ({ ...b, k })).sort((a, b) => (a.x - b.x) || (a.y - b.y));
    let lastX = null;
    const bseq = []; let dir = 1, cur = [];
    for (const b of bars) { if (lastX !== null && Math.abs(b.x - lastX) > 1) { bseq.push(...(dir > 0 ? cur : cur.reverse())); dir = -dir; cur = []; } cur.push(b); lastX = b.x; }
    bseq.push(...(dir > 0 ? cur : cur.reverse()));
    bseq.forEach((b, n) => {
      const cx = b.x - C.T2.spindle[0], cy = b.y - C.T2.spindle[1];
      const d = `버스바 연결부 ${n + 1}/${bseq.length}: Ø6 엔드밀로 셀 사이를 끊고 칩은 후드로 바로 빨아들여요 (대상 블록 44곳, 가정).`;
      if (n === 0) q.push(A_rot(0, ph('버스바 절단', 's5', d)), A_travel(cx, cy, zTipUp - tipLocal(), ph('버스바 절단', 's5', d)), A_slide(0, ph('버스바 절단', 's5', d)));
      else q.push(A_move({ x: cx - 8, y: cy }, PRM.vHop, 400, ph('버스바 절단', 's5', d)));
      if (n === 0) q.push(A_move({ x: cx - 8 }, PRM.vHop, 400, ph('버스바 절단', 's5', d)));
      q.push(A_do(() => { st.chip = true; }, { stp: 's5' }));
      q.push(A_move({ z: zTipCut - tipLocal() }, PRM.vCutZ, 100, ph('버스바 절단', 's5', d)));
      q.push(A_move({ x: cx + 8 }, PRM.vCut, 100, ph('버스바 절단', 's5', d)));
      q.push(A_do(() => { st.bar[b.k] = 0; st.cnt.bar++; }, { stp: 's5' }));
      q.push(A_move({ z: zTipUp - tipLocal() }, PRM.vCutZ * 2, 100, ph('버스바 절단', 's5', d)));
      q.push(A_do(() => { st.chip = false; }, { stp: 's5' }));
    });
    q.push(A_slide(80, { stp: 's5' }));
    // 6 electronics (01)
    q.push(...toolChange(1, 's6'));
    const e = C.ELEC, ex = (e[0] + e[1]) / 2, ey = (e[2] + e[3]) / 2;
    q.push(A_travel(ex, ey, e[5] - C.TOOLBB[1][4], { slow: true, ...ph('전장품 분리', 's6', '01이 전장품(BMS·BDU, 가상) 위로 내려가요.') }));
    q.push(A_wait(PRM.tElec, ph('전장품 분리', 's6', `고정 나사·커넥터를 풀어요 (${PRM.tElec}초 가정).`)));
    q.push(A_grab('elec', true, ph('전장품 분리', 's6', '전장품을 잡아요.')));
    q.push(A_move({ z: e[5] - C.TOOLBB[1][4] + 60 }, PRM.vapp * 2, 200, ph('전장품 분리', 's6', '들어 올려요.')));
    q.push(A_travel(b12.x, b12.y, C.ZT[0], ph('전장품 분리', 's6', '전장품 회수함(12)으로 옮기고 Z축을 가장 낮게 내려요.')));
    q.push(A_grab('elec', false, ph('전장품 분리', 's6', '회수함에 놓아요.')));
    q.push(A_move({ z: C.ZT[0] + 200 }, PRM.vz, PRM.az, { stp: 's6' }));
    // 7 coolant (02)
    q.push(...toolChange(2, 's7'));
    const pt = C.PORTS[0], ncx = pt[0] - C.T2.nozzle[0], ncy = pt[1] - C.T2.nozzle[1];
    const zNoz = C.PORT_TOP - 5 - nozLocal();
    q.push(A_rot(0, ph('냉각수 흡입', 's7')), A_travel(ncx, ncy, zNoz + 40, ph('냉각수 흡입', 's7', '냉각수 포트(가상) 위로 가요.')));
    q.push(A_slide(0, ph('냉각수 흡입', 's7', '흡입 노즐을 내려요.')), A_move({ z: zNoz }, PRM.vapp, 200, ph('냉각수 흡입', 's7', '노즐을 포트에 꽂아요.')));
    q.push(A_do(() => { st.suck = true; }, { stp: 's7' }));
    q.push(A_wait(PRM.tSuck, ph('냉각수 흡입', 's7', `냉각수를 빨아내요 (${PRM.tSuck}초 가정) → 냉각수 회수 탱크로.`)));
    q.push(A_wait(PRM.tPurge, ph('냉각수 흡입', 's7', `압축 공기로 남은 냉각수를 밀어내요 (${PRM.tPurge}초 가정, 공기 공급 방식 미정).`)));
    q.push(A_do(() => { st.suck = false; }, { stp: 's7' }));
    q.push(A_move({ z: zNoz + 60 }, PRM.vz, PRM.az, { stp: 's7' }), A_slide(80, { stp: 's7' }));
    // 9 -> cells
    q.push(A_do(() => { st.prepDone = true; log('4~7단계 끝: 03으로 셀 분리 시작'); const i = st.next >= 0 && st.status[st.next] === 'in' ? st.next : pickNext(-1); if (i >= 0) planCycle(i, true); }, { stp: 's9' }));
    st.queue = q;
  }

  // ------------------------------------------------------------------ cycles (steps 9-10)
  function planCycle(i, keep) {
    st.target = i; st.next = -1;
    st.cycle = { i, t0: st.t, tSep: null, maxTb: st.Tb[i], maxTc: st.Tc[i], maxTaN: 0, result: null };
    const [cx, cy] = cellXY(i);
    const q = [];
    q.push(...toolChange(3, 's9'));
    q.push(A_travel(cx, cy, C.ZC + C.TILT, { slow: true, ph: '셀 위로 이동', stp: 's9', desc: () => `${label(i)} 위로 가요. 지나는 길의 가장 높은 장비보다 ${PRM.clr} mm 위로 지나가요.` }));
    q.push(A_vac(true, { ph: '흡착', stp: 's9', desc: '마지막 15 mm는 천천히 내려가 컵 2개로 흡착해요 (−60 kPa 가정).' }));
    q.push(A_separate(i));
    if (keep) st.queue.push(...q); else st.queue = q;
    log(`${label(i)} 사이클 시작`);
  }
  function cycleDone(ok, why) {
    const c = st.cycle;
    if (c) { c.tCycle = st.t - c.t0; c.result = ok ? '회수함' : why; st.records.push(c); }
    st.cycle = null; st.target = -1;
    if (!ok) { pause(); return; }
    if (!st.auto) { pause(); st.desc = '한 셀 끝. ▶를 누르면 다음 셀을 떼어내요.'; return; }
    const nx = pickNext(c ? c.i : -1);
    if (nx < 0) { pause(); st.phase = '완료'; st.desc = '블록의 셀을 모두 떼어냈어요.'; log('모든 셀 처리 완료'); return; }
    planCycle(nx);
  }
  function pickNext(after) {
    if (st.next >= 0 && st.status[st.next] === 'in') return st.next;
    for (let k = 1; k <= N; k++) { const i = (Math.max(after, 0) + k) % N; if (st.status[i] === 'in') return i; }
    return -1;
  }
  function pause() { st.running = false; }

  // ------------------------------------------------------------------ emergency
  function checkEmergency() {
    if (st.emergency) return;
    for (let i = 0; i < N; i++) {
      if (['gone', 'tank', 'fall'].includes(st.status[i]) || st.emCells.has(i)) continue;
      if (st.Tc[i] >= PRM.Tem) { emergency(i, `셀 온도 ${fmt(st.Tc[i])} °C ≥ ${PRM.Tem} °C`); return; }
      if (st.rateT[i] >= PRM.tRate) { emergency(i, `온도 상승 ${fmt(st.dTcNow[i], 1)} °C/s가 ${PRM.tRate}초 이어짐 (기준 ${PRM.dTem} °C/s)`); return; }
    }
  }
  const PLACE = { in: '블록 안', fail: '블록 안', bin: '회수함 안', jig: '측정대 위' };
  function emergency(i, why) {
    const held = H.cell;
    const where = held === i ? (st.status[i] === 'carry' ? 'carry' : 'held') : 'other';
    st.emergency = { i, t0: st.t, where, tDone: null }; st.emCells.add(i); st.emLast = st.emergency;
    st.coilOn = false; st.air = false; st.coilZone = -1;
    if (st.sep) { st.lastSeries = st.series; st.sep = null; }
    st.queue = []; st.act = null; st.phase = '비상';
    log(`이상 감지: ${label(i)} ${why} → 가열 정지`, true);
    const closeCycle = (res) => { if (st.cycle) { st.cycle.result = res; st.cycle.tCycle = st.t - st.cycle.t0; st.records.push(st.cycle); st.cycle = null; } st.target = -1; };
    if (where === 'carry') {
      closeCycle('비상: 침수조');
      st.queue.push(
        A_travel(C.TANK.x, C.TANK.y, C.ZT[0], { ph: '비상', desc: `${label(i)}을 비상 침수조로 옮겨요.` }),
        A_vac(false, { drop: 'tank', ph: '비상' }),
        A_do(() => { st.emergency.tDone = st.t; log(`감지 → 침수조 투입 ${fmt(st.t - st.emergency.t0, 1)}초`, true); }),
        A_move({ z: C.ZT[0] + 250 }, PRM.vz, PRM.az),
        A_do(() => { finishEmergency(`${label(i)}을 비상 침수조에 넣었어요. 감지부터 ${fmt(st.emergency.tDone - st.emergency.t0, 1)}초 걸렸어요 (이동 계산값). ▶를 누르면 다음 셀로 계속해요.`); }),
      );
    } else if (where === 'held') {
      closeCycle('비상: 중단');
      st.queue.push(
        A_relevel(i, 0, 1.0, { ph: '비상', desc: '가열을 끄고 셀을 제자리에 내려놓아요.' }),
        A_vac(false, { ph: '비상' }),
        A_move({ z: C.ZC + C.TILT + 150 }, PRM.vz, PRM.az),
        A_do(() => { st.status[i] = 'fail'; finishEmergency(`${label(i)}이 아직 접착층에 붙어 있어서 침수조로 옮길 수 없어요. 이 경우의 대응은 아직 정하지 않았어요.`); }),
      );
    } else {
      const place = PLACE[st.status[i]] || '';
      if (st.status[i] === 'in') st.status[i] = 'fail';
      if (held >= 0 && st.status[held] === 'held') {
        closeCycle('비상: 중단');
        st.queue.push(
          A_relevel(held, 0, 1.0, { ph: '비상', desc: `가열을 끄고 잡고 있던 ${label(held)}을 제자리에 내려놓아요.` }),
          A_vac(false, { ph: '비상', abort: true }),
          A_move({ z: C.ZC + C.TILT + 150 }, PRM.vz, PRM.az),
        );
      }
      st.queue.push(A_do(() => finishEmergency(`${place} ${label(i)}이 이상 온도에 닿았지만 공구에 잡혀 있지 않아 옮길 수 없어요. 이 경우의 대응은 아직 정하지 않았어요.${held >= 0 && st.status[held] === 'carry' ? ` 들고 있던 ${label(held)}은 ▶를 누르면 계속 옮겨요.` : ''}`)));
    }
  }
  function finishEmergency(msg) {
    if (st.anomaly >= 0) { log('가상 발열은 여기서 멈춤 (시뮬레이션 단순화)'); st.anomaly = -1; }
    st.banner = msg; st.phase = '비상'; st.desc = msg; pause();
  }

  // ------------------------------------------------------------------ main step
  function stepSim(dt) {
    st.t += dt;
    thermal(dt);
    stepFalls(dt);
    for (let g = 0; g < 40; g++) {
      if (!st.act) {
        const nx = st.queue.shift();
        if (!nx) break;
        st.act = nx; startAct(nx);
      }
      if (st.act.step(dt)) { st.act = null; dt = 0; continue; }
      break;
    }
    if (st.act && st.act.desc && typeof st.act.desc === 'function') st.desc = st.act.desc();
    if (H.cell >= 0 && st.rel[H.cell]) st.cellM[H.cell].copy(tm().multiply(st.rel[H.cell]));
    if (H.carry === 'cover') st.cover.M.copy(tm().multiply(st.cover.rel));
    if (H.carry === 'elec') st.elec.M.copy(tm().multiply(st.elec.rel));
    checkEmergency();
  }
  function idle() { return !st.act && !st.queue.length; }
  function fastForward(pred, maxSteps = 400000) {
    let k = 0;
    for (; k < maxSteps; k++) { if (pred()) break; if (idle() && !st.falls.length) break; stepSim(DT); }
    return k;
  }

  // ------------------------------------------------------------------ heat colours (one hue, light -> dark)
  const HSTOPS = [[25, [238, 233, 226]], [55, [246, 205, 173]], [85, [238, 141, 85]], [115, [210, 84, 32]], [150, [128, 40, 10]]];
  function heatRGB(T) {
    if (T <= HSTOPS[0][0]) return HSTOPS[0][1];
    for (let k = 1; k < HSTOPS.length; k++) {
      if (T <= HSTOPS[k][0]) { const [t0, c0] = HSTOPS[k - 1], [t1, c1] = HSTOPS[k]; const u = (T - t0) / (t1 - t0); return c0.map((v, m) => Math.round(lerp(v, c1[m], u))); }
    }
    return HSTOPS[HSTOPS.length - 1][1];
  }
  const rgbCss = (c) => `rgb(${c[0]},${c[1]},${c[2]})`;
  const lum = (c) => (0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]) / 255;

  // ================================================================== three.js view
  function cssVar(n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); }
  function b64(buf) { const s = atob(buf); const a = new Uint8Array(s.length); for (let i = 0; i < s.length; i++) a[i] = s.charCodeAt(i); return a.buffer; }
  const MATRIX_GROUPS = ['tool1', 'tool2', 'tool2s', 'tool3', 'headout', 'rot', 'coverBody', 'elec'];
  function buildView(scene) {
    const canvas = $('#simgl'), box = $('#simcanvas');
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    const sc = new THREE.Scene();
    const cam = new THREE.PerspectiveCamera(35, 1.5, 20, 60000);
    cam.up.set(0, 0, 1);
    const hemi = new THREE.HemisphereLight(0xffffff, 0x7d878c, 0.58); hemi.position.set(0, 0, 1); sc.add(hemi);
    const dir = new THREE.DirectionalLight(0xffffff, 0.48); dir.position.set(-3000, -4500, 7000); sc.add(dir);
    const dir2 = new THREE.DirectionalLight(0xffffff, 0.14); dir2.position.set(4000, 3000, 2000); sc.add(dir2);
    const grid = new THREE.GridHelper(8000, 16); grid.rotation.x = Math.PI / 2; grid.position.set(2250, 0, 0); sc.add(grid);
    const groups = {};
    const G = (k) => (groups[k] = groups[k] || (() => { const g = new THREE.Group(); if (MATRIX_GROUPS.includes(k)) g.matrixAutoUpdate = false; sc.add(g); return g; })());
    const clipMats = [];
    const W = (m) => { clipMats.push(m); return m; };
    const edgeW = W(new THREE.LineBasicMaterial({ color: 0x1d2226, transparent: true, opacity: 0.55 }));
    const edgeM = new THREE.LineBasicMaterial({ color: 0x1d2226, transparent: true, opacity: 0.55 });
    const edgeFence = W(new THREE.LineBasicMaterial({ color: 0x8e9aa3, transparent: true, opacity: 0.55 }));
    const matsW = {}, matsM = {};
    const mat = (col, key, world) => {
      const c = world ? matsW : matsM, k = key || col;
      if (!c[k]) { c[k] = new THREE.MeshLambertMaterial({ color: new THREE.Color(col) }); if (world) W(c[k]); }
      return c[k];
    };
    const cells = {}, adh = {}, coil = {}, plates = [], bodies = [], pads = [], screws = [], bars = [];
    const padMat = W(new THREE.MeshLambertMaterial({ color: new THREE.Color('#e6c26b'), transparent: true, opacity: 1 }));
    const cellBodyMat = W(new THREE.MeshLambertMaterial({ color: new THREE.Color('#8fb0c4'), transparent: true, opacity: 1 }));
    const coverMat = new THREE.MeshLambertMaterial({ color: new THREE.Color('#c7cfd4'), transparent: true, opacity: 1 });
    const coverRimMat = W(new THREE.MeshLambertMaterial({ color: new THREE.Color('#c7cfd4'), transparent: true, opacity: 1 }));
    for (const m of scene.meshes) {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(b64(m.pos)), 3));
      g.setIndex(new THREE.BufferAttribute(m.it === 16 ? new Uint16Array(b64(m.idx)) : new Uint32Array(b64(m.idx)), 1));
      g.computeVertexNormals();
      let material, parent, edges = true;
      const world = ['static', 'cell', 'adh', 'coil', 'pad'].includes(m.group);
      if (m.kind === 'fence') {
        material = W(new THREE.MeshBasicMaterial({ color: new THREE.Color(m.color), transparent: true, opacity: 0.05, depthWrite: false }));
        parent = G('static');
        parent.add(new THREE.LineSegments(new THREE.EdgesGeometry(g, 30), edgeFence));
        edges = false;
      } else if (m.group === 'cell') {
        const k = m.key;
        cells[k] = cells[k] || (() => { const gr = new THREE.Group(); gr.matrixAutoUpdate = false; sc.add(gr); return gr; })();
        parent = cells[k];
        material = m.kind === 'body' ? cellBodyMat : mat(m.color, 'terms', true);
      } else if (m.group === 'adh') {
        material = W(new THREE.MeshLambertMaterial({ color: new THREE.Color(m.color) })); adh[m.key] = material; parent = G('static'); edges = false;
      } else if (m.group === 'coil') {
        material = W(new THREE.MeshLambertMaterial({ color: new THREE.Color(m.color), emissive: new THREE.Color(0x000000) })); coil[m.key] = material; parent = G('static');
      } else if (m.group === 'pad') {
        material = padMat; parent = G('static'); edges = false;
      } else if (m.kind === 'plate') {
        material = W(new THREE.MeshLambertMaterial({ color: new THREE.Color(m.color), transparent: true, opacity: 1 })); plates.push(material); parent = G('static');
      } else if (m.group === 'coverBody') {
        material = coverMat; parent = G('coverBody');
      } else if (m.group === 'screw' || m.group === 'bar') {
        material = mat(m.color, m.group, false); parent = G(m.group);
      } else {
        material = (m.color === '#c7cfd4' && m.group === 'static') ? coverRimMat : mat(m.color, null, world);
        parent = G(m.group === 'static' ? 'static' : m.group);
      }
      const mesh = new THREE.Mesh(g, material);
      if (m.group === 'cell' && m.kind === 'body') { mesh.userData.key = m.key; bodies.push(mesh); }
      if (m.group === 'pad') { g.computeBoundingBox(); mesh.userData.yc = (g.boundingBox.min.y + g.boundingBox.max.y) / 2; pads.push(mesh); }
      if (m.group === 'screw') screws[m.key] = mesh;
      if (m.group === 'bar') bars[m.key] = mesh;
      parent.add(mesh);
      if (edges) mesh.add(new THREE.LineSegments(new THREE.EdgesGeometry(g, 32), world ? edgeW : edgeM));
    }
    // seal-cut line (progress) and the parts of the line out of the gantry reach
    const cutMat = new THREE.MeshBasicMaterial({ color: 0xd2302a, side: THREE.DoubleSide });
    const cutGeo = new THREE.BufferGeometry(); cutGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(3 * 6 * 8), 3));
    const cutLine = new THREE.Mesh(cutGeo, cutMat); cutLine.frustumCulled = false; sc.add(cutLine);
    renderer.localClippingEnabled = true;
    const view = { renderer, sc, cam, grid, groups, cells, adh, coil, plates, bodies, pads, padMat, cellBodyMat, coverMat, coverRimMat, screws, bars,
      canvas, box, xray: false, dirty: true, cutGeo, cutLine,
      clipMats, plane: new THREE.Plane(new THREE.Vector3(0, 1, 0), 0), section: true, clipOn: false };
    applyTheme(view);
    return view;
  }
  function applyTheme(v) {
    const bg = new THREE.Color(cssVar('--scene') || '#e3e8e9');
    v.renderer.setClearColor(bg, 1);
    const gc = new THREE.Color(cssVar('--grid3') || '#c3cbce');
    const mats = Array.isArray(v.grid.material) ? v.grid.material : [v.grid.material];
    mats.forEach((m) => { m.color = gc; m.vertexColors = false; m.needsUpdate = true; });
    v.dirty = true;
  }
  function setM(g, M) { g.matrix.copy(M); g.matrixWorldNeedsUpdate = true; }
  function syncView() {
    const v = V, gr = v.groups;
    gr.bridge.position.set(H.x, 0, 0);
    gr.carriage.position.set(H.x, H.y, 0);
    gr.ram.position.set(H.x, H.y, H.z);
    setM(gr.rot, M4().makeTranslation(H.x, H.y, H.z).multiply(M4().makeRotationZ(H.rot * D2R)));
    setM(gr.headout, headMatrix());
    for (const n of [1, 2, 3]) setM(gr['tool' + n], toolMatrix(n));
    setM(gr.tool2s, toolMatrix(2).multiply(M4().makeTranslation(0, 0, H.tool === 2 ? H.slide : 80)));
    setM(gr.coverBody, st.cover.M);
    setM(gr.elec, st.elec.M);
    for (let k = 0; k < v.screws.length; k++) if (v.screws[k]) v.screws[k].visible = !!st.screw[k];
    for (let k = 0; k < v.bars.length; k++) if (v.bars[k]) v.bars[k].visible = !!st.bar[k];
    for (let i = 0; i < N; i++) { const g = v.cells[keyOf(i)]; if (g) setM(g, st.cellM[i]); }
    // seal-cut progress on the flange: a red strip 8 mm wide (display only)
    const pos = v.cutGeo.attributes.position.array; let n = 0;
    const z = C.COVER.z0 + C.COVER.t + 0.6, w = 4;
    if (st.cover.state === 'on' && st.seal.segs.length) {
      for (const s of st.seal.segs) {
        const c = s.cut || 0;
        if (c <= 0 || n >= 48) continue;
        const u1 = s.ua + c * (s.ub - s.ua);
        const ax = lerp(s.p0[0], s.p1[0], s.ua), ay = lerp(s.p0[1], s.p1[1], s.ua), bx = lerp(s.p0[0], s.p1[0], u1), by = lerp(s.p0[1], s.p1[1], u1);
        const L = Math.hypot(bx - ax, by - ay) || 1, nx = -(by - ay) / L * w, ny = (bx - ax) / L * w;
        pos.set([ax + nx, ay + ny, z, bx + nx, by + ny, z, bx - nx, by - ny, z, ax + nx, ay + ny, z, bx - nx, by - ny, z, ax - nx, ay - ny, z], n * 3); n += 6;
      }
    }
    v.cutGeo.setDrawRange(0, n); v.cutGeo.attributes.position.needsUpdate = true;
    updateSection();
    for (let i = 0; i < N; i++) {
      const a = v.adh[keyOf(i)]; if (a) { const c = heatRGB(st.Ta[i]); a.color.setRGB(c[0] / 255, c[1] / 255, c[2] / 255); }
      const cm = v.coil[keyOf(i)];
      if (cm) { const on = st.coilOn && st.coilZone === i; cm.emissive.setRGB(on ? 0.95 : 0, on ? 0.38 : 0, on ? 0.05 : 0); }
    }
    v.dirty = true;
  }
  function sectionWanted() {
    if (!V.section) return null;
    const i = H.cell >= 0 && ['held', 'carry'].includes(st.status[H.cell]) ? H.cell : st.target;
    if (i < 0 || H.tool !== 3) return null;
    const near = ['흡착', '가열·필링', '들어 올림'].includes(st.phase) || (st.phase === '셀 위로 이동' && Math.hypot(H.x - cellXY(i)[0], H.y - cellXY(i)[1]) < 30 && H.z < C.ZC + C.TILT + 60);
    return near ? cellXY(i)[1] - C.CELL.T / 2 - 0.8 : null;
  }
  function updateSection() {
    const y = sectionWanted(), on = y != null;
    if (on) V.plane.constant = -y;
    for (const p of V.pads) p.visible = !(on && p.userData.yc < y + 2);
    if (on !== V.clipOn) {
      V.clipOn = on;
      for (const m of V.clipMats) { m.clippingPlanes = on ? [V.plane] : null; m.side = on ? THREE.DoubleSide : THREE.FrontSide; m.needsUpdate = true; }
    }
  }
  function setSection(on) { V.section = on; $('#sect').setAttribute('aria-pressed', String(on)); syncView(); }
  function setXray(on) {
    V.xray = on;
    const tr = (m, a) => { m.opacity = on ? a : 1; m.depthWrite = !on; m.needsUpdate = true; };
    tr(V.cellBodyMat, 0.16); V.plates.forEach((m) => tr(m, 0.2)); tr(V.padMat, 0.12); tr(V.coverMat, 0.25); tr(V.coverRimMat, 0.25);
    $('#xray').setAttribute('aria-pressed', String(on));
    V.dirty = true;
  }

  // ------------------------------------------------------------------ camera (Z up orbit)
  const CAM = { tgt: [2300, 0, 900], dist: 8200, az: -2.09, el: 0.62, goal: null, mode: 'follow', user: 0, fixed: null };
  function camPreset(mode, instant) {
    CAM.mode = mode; CAM.fixed = null;
    if (mode === 'free') { document.querySelectorAll('[data-cam]').forEach((b) => b.setAttribute('aria-pressed', 'false')); CAM.goal = null; return; }
    document.querySelectorAll('[data-cam]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.cam === mode)));
    const g = camGoal();
    if (instant || matchMedia('(prefers-reduced-motion: reduce)').matches) { Object.assign(CAM, g); CAM.goal = null; }
    else CAM.goal = Object.assign({ t: 0 }, g, { from: { tgt: CAM.tgt.slice(), dist: CAM.dist, az: CAM.az, el: CAM.el } });
    CAM.user = 0;
    if (V) V.dirty = true;
  }
  function headPoint(dz) { return [H.x, H.y, H.z + dz]; }
  function camGoal() {
    if (CAM.fixed) return CAM.fixed;
    if (CAM.mode === 'all') return { tgt: [2350, 0, 850], dist: 8600, az: -2.09, el: 0.6 };
    if (CAM.mode === 'bench') return { tgt: [C.BX + 75, C.BY, 880], dist: 1700, az: -1.95, el: 0.6 };
    const ph = st.phase;
    if (st.sep && st.sep.p > 0) { const s = st.sep, [, cy] = cellXY(s.i); return { tgt: [s.cx - s.sgn * C.CELL.L / 2, cy, C.ZC - C.CELL.H + 25], dist: 400, az: -1.5708, el: 0.07 }; }
    if (H.tool === 3 && (ph === '가열·필링' || ph === '흡착')) { const c = cupPoint(); return { tgt: [c[0], c[1], C.ZC - 30], dist: 620, az: -1.5708, el: 0.16 }; }
    if (ph === '커버 인양' && H.carry === 'cover') return { tgt: headPoint(-400), dist: 6200, az: -2.0, el: 0.55 };
    if (ph === '실링 절개') return { tgt: headPoint(-300), dist: 1500, az: -2.1, el: 0.5 };
    if (ph === '버스바 절단') return { tgt: [H.x + C.T2.spindle[0], H.y, C.ZC + 10], dist: 700, az: -2.0, el: 0.45 };
    if (ph === '냉각수 흡입') return { tgt: [C.PORTS[0][0], C.PORTS[0][1], C.PORT_TOP], dist: 1100, az: -0.8, el: 0.35 };
    if (ph === '나사 해체' || ph === '배선 제거' || ph === '전장품 분리') return { tgt: headPoint(-380), dist: 1900, az: -2.0, el: 0.5 };
    if (ph === '공구 교환') return { tgt: headPoint(-250), dist: 2600, az: -2.2, el: 0.42 };
    return { tgt: cupPoint(), dist: 2300, az: -1.95, el: 0.42 };
  }
  function cupPoint() {
    if (!H.tool) return [H.x, H.y, H.z - 70];
    const p = new THREE.Vector3(0, 0, -C.DOCK[H.tool]).applyMatrix4(tm()); return [p.x, p.y, p.z];
  }
  function camUpdate(rdt) {
    if (CAM.mode === 'follow' && !CAM.fixed) {
      const g = camGoal();
      const k = 1 - Math.exp(-rdt * 3.5);
      for (let i = 0; i < 3; i++) CAM.tgt[i] = lerp(CAM.tgt[i], g.tgt[i], k);
      if (CAM.user <= 0) { CAM.dist = lerp(CAM.dist, g.dist, k * 0.7); CAM.az = lerp(CAM.az, g.az, k * 0.7); CAM.el = lerp(CAM.el, g.el, k * 0.7); }
      else CAM.user -= rdt;
    } else if (CAM.goal) {
      const g = CAM.goal; g.t += rdt / 0.7; const u = ease(g.t);
      for (let i = 0; i < 3; i++) CAM.tgt[i] = lerp(g.from.tgt[i], g.tgt[i], u);
      CAM.dist = lerp(g.from.dist, g.dist, u); CAM.az = lerp(g.from.az, g.az, u); CAM.el = lerp(g.from.el, g.el, u);
      if (g.t >= 1) CAM.goal = null;
    }
    const c = V.cam, ce = Math.cos(CAM.el);
    c.position.set(CAM.tgt[0] + CAM.dist * ce * Math.cos(CAM.az), CAM.tgt[1] + CAM.dist * ce * Math.sin(CAM.az), CAM.tgt[2] + CAM.dist * Math.sin(CAM.el));
    c.lookAt(CAM.tgt[0], CAM.tgt[1], CAM.tgt[2]);
    c.near = Math.max(5, CAM.dist / 200); c.far = CAM.dist * 20 + 20000; c.updateProjectionMatrix();
  }
  function bindCamera() {
    const cv = V.canvas, pts = new Map();
    let pinch = null, moved = 0;
    cv.addEventListener('contextmenu', (e) => e.preventDefault());
    cv.addEventListener('pointerdown', (e) => { cv.setPointerCapture(e.pointerId); pts.set(e.pointerId, { x: e.clientX, y: e.clientY, b: e.button, sh: e.shiftKey }); moved = 0;
      if (pts.size === 2) { const [a, b] = [...pts.values()]; pinch = { d: Math.hypot(a.x - b.x, a.y - b.y), cx: (a.x + b.x) / 2, cy: (a.y + b.y) / 2 }; } });
    cv.addEventListener('pointermove', (e) => {
      const p = pts.get(e.pointerId); if (!p) return;
      const dx = e.clientX - p.x, dy = e.clientY - p.y; p.x = e.clientX; p.y = e.clientY; moved += Math.abs(dx) + Math.abs(dy);
      if (pts.size === 1) {
        if (p.b === 2 || p.sh) pan(dx, dy); else { CAM.az -= dx * 0.006; CAM.el = clamp(CAM.el + dy * 0.005, 0.03, 1.5); }
      } else if (pts.size === 2 && pinch) {
        const [a, b] = [...pts.values()], d = Math.hypot(a.x - b.x, a.y - b.y), cx = (a.x + b.x) / 2, cy = (a.y + b.y) / 2;
        CAM.dist = clamp(CAM.dist * pinch.d / Math.max(d, 1), 150, 30000); pan(cx - pinch.cx, cy - pinch.cy); pinch = { d, cx, cy };
      }
      CAM.goal = null; CAM.user = 6; V.dirty = true;
    });
    const up = (e) => {
      const p = pts.get(e.pointerId); pts.delete(e.pointerId); if (pts.size < 2) pinch = null;
      if (p && moved < 6 && pts.size === 0) pick(e);
    };
    cv.addEventListener('pointerup', up); cv.addEventListener('pointercancel', (e) => { pts.delete(e.pointerId); pinch = null; });
    cv.addEventListener('wheel', (e) => { e.preventDefault(); CAM.dist = clamp(CAM.dist * Math.exp(e.deltaY * 0.0012), 150, 30000); CAM.goal = null; CAM.user = 6; V.dirty = true; }, { passive: false });
    cv.addEventListener('keydown', (e) => { if (e.code === 'Space') { e.preventDefault(); togglePlay(); } });
  }
  function pan(dx, dy) {
    const k = CAM.dist * 0.0012, sa = Math.sin(CAM.az), ca = Math.cos(CAM.az);
    const rx = -sa, ry = ca;
    CAM.tgt[0] -= (rx * dx) * k; CAM.tgt[1] -= (ry * dx) * k; CAM.tgt[2] += dy * k;
    if (CAM.mode === 'follow') camPreset('free');
  }
  function pick(e) {
    const r = V.canvas.getBoundingClientRect();
    const ndc = new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    const rc = new THREE.Raycaster(); rc.setFromCamera(ndc, V.cam);
    const hit = rc.intersectObjects(V.bodies, false)[0];
    if (!hit) return;
    const key = hit.object.userData.key;
    for (let i = 0; i < N; i++) if (keyOf(i) === key) { chooseCell(i); break; }
  }

  // ================================================================== UI
  function chooseCell(i) {
    if (st.status[i] !== 'in') return;
    st.next = i;
    if (!st.running && idle()) st.desc = `${label(i)}을 다음 대상으로 정했어요. ▶ 시작을 누르세요.`;
    else log(`다음 대상: ${label(i)}`);
    refreshUI(true);
  }
  function togglePlay() {
    if (st.emergency && !st.running && st.banner) { st.banner = null; st.emergency = null; st.phase = '대기'; }
    if (!st.running && idle()) {
      if (H.cell >= 0 && st.status[H.cell] === 'carry') st.queue.push(...carryPlan());
      else if (!st.prepDone) planProcess();
      else {
        const i = st.next >= 0 && st.status[st.next] === 'in' ? st.next : pickNext(-1);
        if (i < 0) { st.desc = '남은 셀이 없어요. 처음부터를 누르세요.'; refreshUI(true); return; }
        planCycle(i);
      }
    }
    st.running = !st.running;
    if (st.running && CAM.auto) { CAM.auto = false; camPreset('follow'); }
    refreshUI(true);
  }
  function resetAll(keepNext) {
    const nx = keepNext && st && st.next >= 0 ? st.next : 6;
    st = freshState(); H = freshHead(); st.speed = currentSpeed(); st.auto = $('#auto').checked; st.next = nx;
    syncView(); camPreset(CAM.mode === 'free' ? 'follow' : CAM.mode, true); refreshUI(true);
  }
  function jumpTo(stepKey, run) {
    const wasRunning = run ?? st.running;
    resetAll(true);
    planProcess();
    fastForward(() => st.act && st.step === stepKey);
    st.running = !!wasRunning;
    if (CAM.auto) { CAM.auto = false; }
    camPreset('follow', true);
    syncView(); refreshUI(true);
  }
  function currentSpeed() { const b = document.querySelector('#speed [aria-pressed="true"]'); return b ? +b.dataset.s : 5; }

  function buildUI() {
    const cm = $('#cmap'); cm.replaceChildren();
    for (const r of [1, 0]) {
      cm.append(el('span', 'rl', r ? 'B' : 'A'));
      for (let j = 0; j < 12; j++) {
        const i = r * 12 + j, b = el('button', 'cbtn', String(j + 1)); b.type = 'button'; b.dataset.i = i;
        b.setAttribute('aria-label', `${label(i)} 셀`);
        b.addEventListener('click', () => chooseCell(i)); cm.append(b);
      }
    }
    const bar = $('#cbar'); bar.style.background = `linear-gradient(90deg, ${HSTOPS.map(([t, c]) => `${rgbCss(c)} ${((t - 25) / 125 * 100).toFixed(0)}%`).join(', ')})`;
    const pr = $('#prm'); pr.replaceChildren();
    for (const s of SLIDERS) {
      const lab = el('label'); const id = 'prm-' + s.k;
      const name = el('span', '', s.n), val = el('span', 'v'); val.id = id + '-v';
      const inp = el('input'); inp.type = 'range'; inp.id = id; inp.min = s.min; inp.max = s.max; inp.step = s.step; inp.value = PRM[s.k];
      inp.addEventListener('input', () => { PRM[s.k] = +inp.value; val.textContent = `${inp.value} ${s.u}`; refreshUI(true); });
      val.textContent = `${PRM[s.k]} ${s.u}`;
      lab.append(name, val, inp); if (s.hint) lab.append(el('span', 'hint', s.hint)); pr.append(lab);
    }
    const pad = el('label', 'chk'); const pc = el('input'); pc.type = 'checkbox'; pc.id = 'prm-pad'; pc.checked = PRM.padRelease;
    pc.addEventListener('change', () => { PRM.padRelease = pc.checked; refreshUI(true); });
    pad.append(pc, document.createTextNode(' 셀 사이 패드 압축을 풀고 시작 (가설)')); pr.append(pad);
    $('#prmreset').addEventListener('click', () => {
      Object.assign(PRM, FIXED, Object.fromEntries(SLIDERS.map((s) => [s.k, s.d])));
      SLIDERS.forEach((s) => { $('#prm-' + s.k).value = s.d; $('#prm-' + s.k + '-v').textContent = `${s.d} ${s.u}`; });
      $('#prm-pad').checked = PRM.padRelease; refreshUI(true);
    });
    $('#anom').addEventListener('click', () => {
      const i = H.cell >= 0 ? H.cell : st.target;
      if (i < 0 || st.anomaly >= 0) return;
      st.anomaly = i; log(`가상 이상 발열 시작: ${label(i)} (내부 ${PRM.Qanom} W 가정)`, true);
      if (!st.running && !idle()) st.running = true;
      refreshUI(true);
    });
    $('#play').addEventListener('click', togglePlay);
    $('#reset').addEventListener('click', () => resetAll(true));
    $('#speed').addEventListener('click', (e) => { const b = e.target.closest('button'); if (!b) return;
      document.querySelectorAll('#speed button').forEach((x) => x.setAttribute('aria-pressed', String(x === b))); st.speed = +b.dataset.s; });
    $('#auto').addEventListener('change', (e) => { st.auto = e.target.checked; });
    document.querySelectorAll('[data-cam]').forEach((b) => b.addEventListener('click', () => { CAM.auto = false; camPreset(b.dataset.cam); }));
    $('#xray').addEventListener('click', () => setXray(!V.xray));
    $('#sect').addEventListener('click', () => setSection(!V.section));
    $('#tbtn').addEventListener('click', () => { const t = $('#tview'); t.hidden = !t.hidden; $('#tbtn').textContent = t.hidden ? '표로 보기' : '표 닫기'; refreshUI(true); });
    const ph = $('#phases'); ph.replaceChildren();
    STEPS.forEach((s, k) => {
      if (k) ph.append(el('span', 'ar', '→'));
      const b = el('button', 'ph'); b.type = 'button'; b.dataset.p = s.k;
      b.append(el('span', 'pn', s.n), document.createTextNode(' ' + s.t), el('span', 'pt', ' ' + s.tool));
      b.title = `${s.n}단계로 바로 가기`;
      b.addEventListener('click', () => jumpTo(s.k));
      ph.append(b);
    });
    $('#modelnote').replaceChildren(...[
      `축 이동: X·Y 최고 ${PRM.vxy} mm/s(가속 ${PRM.axy}), Z 최고 ${PRM.vz} mm/s, θ ${PRM.vRot}°/s, 마지막 ${PRM.app} mm는 ${PRM.vapp} mm/s. 이동 높이 = 지나는 길에서 가장 높은 장비 + ${PRM.clr} mm + 매달린 것 길이(공구·커버·전장품·셀). 갠트리 범위 X ${C.X[0]}~${C.X[1]}, Y ±${C.Y[1]}, Z ${C.ZT[0]}~${C.ZT[1]} (기울임축 중심).`,
      `공구 교환: 거치대 위치까지 가서 천천히 내려가 잠금 ${PRM.tLock}초. 순서는 D-01 공정표 그대로 01 → 02 → 01 → 02 → 01 → 02 → 03.`,
      `4단계 (가상 커버 2200×1600, 높이 ${C.COVER.h}, 플랜지 ${C.COVER.flange}, 나사 ${C.SCREWS.length}개): 나사 1개 ${PRM.tScrew}초(01은 외형 원기둥, 실제 형상·비트는 팀원 설계). 실링 절개는 02 엔드밀로 가장자리 ${C.COVER.cut_inset} mm 안쪽 플랜지를 ${PRM.vSeal} mm/s로 자른다고 가정(공구 세부 미정). 커버는 흡착컵 4개로 들어 90° 돌려 거치대에.`,
      `5단계: 배선·커넥터 4곳 각 ${PRM.tWire}초(위치 가정). 버스바는 대상 블록의 셀 사이 연결부 44곳을 Ø6 엔드밀로 끊음(내려가기 ${PRM.vCutZ} mm/s, 가로 16 mm를 ${PRM.vCut} mm/s).`,
      `6·7단계: 전장품(BMS·BDU 가상 240×400×50)을 01이 풀고(${PRM.tElec}초) 회수함 12로. 냉각수는 02 노즐을 포트(가상)에 꽂아 흡입 ${PRM.tSuck}초 + 공기 퍼지 ${PRM.tPurge}초.`,
      '열: 셀마다 냉각판·접착층·셀 바닥·셀 몸통 4점 열회로. 냉각판 옆 구역끼리 3 W/K, 냉각판→접착층 12, 접착층→셀 바닥 10, 셀 바닥→몸통 2.5, 셀끼리(패드) 1.2 W/K. 열용량 냉각판 36, 접착층 9, 셀 바닥 50, 셀 몸통 800 J/K. 코일 출력은 냉각판 구역에 바로 들어간다고 봄. 냉각수는 7단계에서 빼 둔 상태.',
      `접착: 강도 = ${PRM.Fcold} N ÷ (1 + e^((접착층 온도 − 연화 온도) ÷ ${PRM.w})). 필요한 힘 = 접착 강도 × 아직 붙은 비율 + 패드 마찰(풀지 않으면 예시 ${PRM.Fpad} N) + 셀 무게(${PRM.mCell} kg).`,
      `제어: 냉각판 상한(−${PRM.hyst} °C에서 다시 켬)과 셀 윗면(IR) 한계에서 코일을 끊어요. 당김 힘은 초당 ${PRM.Framp} N씩 올리다 한계에서 멈추고 가열을 기다려요(v0.3 원칙). 필요한 힘이 한계보다 작아지면 그 차이만큼 필링이 진행되고, 기울기는 초당 ${PRM.rate}° 이하.`,
      `비상: 셀 온도 ${PRM.Tem} °C 이상이거나 초당 ${PRM.dTem} °C 넘게 ${PRM.tRate}초 오르면(가정) 가열을 끄고, 떨어져서 공구에 잡힌 셀이면 비상 침수조로 옮겨요. '이상 발열 넣기'는 셀 안에 ${PRM.Qanom} W 발열을 넣는 가상 고장이에요. 측정은 5초 대기로만 표현했고 측정값은 만들지 않았어요.`,
      '확인하지 않은 것: 실제 열전달, 접착 분리 온도, 흡착 유지, 강도, 전기 절연, 비상 대응, 실제 커버·나사·전장품·냉각수 포트 형상. 이 화면은 개념 검토용이에요.',
    ].map((t) => el('li', '', t)));
  }

  let lastUI = 0, lastHeavy = 0;
  function payload() {
    if (H.tool === 2) return PRM.m02 + PRM.mHead + (H.carry === 'cover' ? PRM.mCover : 0);
    if (H.tool === 3) return PRM.m03 + PRM.mHead + (H.cell >= 0 && st.status[H.cell] !== 'held' ? PRM.mCell : 0);
    return null;
  }
  function refreshUI(force) {
    const now = performance.now();
    if (!force && now - lastUI < 120) return;
    lastUI = now;
    $('#play').textContent = st.running ? '❚❚ 일시정지' : '▶ ' + (st.t > 0 ? '계속' : '시작');
    $('#clock').textContent = `시뮬레이션 시간 ${mmss(st.t)}`;
    const hud = $('#hud'); hud.replaceChildren();
    const ci = H.cell >= 0 ? H.cell : st.target;
    const stp = STEPS.find((s) => s.k === st.step);
    const c1 = el('span', 'hchip' + (st.phase === '비상' ? ' alert' : ''));
    c1.append(el('b', '', stp && st.phase !== '비상' ? `${stp.n} ${st.phase}` : st.phase));
    if (H.tool === 3 && ci >= 0) c1.append(document.createTextNode(' · ' + label(ci)));
    if (st.phase === '나사 해체') c1.append(document.createTextNode(` · ${st.cnt.screw}/${C.SCREWS.length}`));
    if (st.phase === '버스바 절단') c1.append(document.createTextNode(` · ${st.cnt.bar}/${C.BARS.length}`));
    if (st.phase === '실링 절개') c1.append(document.createTextNode(` · ${fmt(st.seal.cut / 1000, 2)}/${fmt((st.seal.total - st.seal.skip) / 1000, 2)} m`));
    hud.append(c1);
    if (H.tool) { const c0 = el('span', 'hchip'); c0.textContent = '공구 ' + TOOLNAME[H.tool]; hud.append(c0); }
    if (st.sep) {
      const c2 = el('span', 'hchip'); c2.innerHTML = `<span class="mono">${fmt(st.t - st.sep.t0)} s</span> · 접착층 <span class="mono">${fmt(st.Ta[st.sep.i])} °C</span>`; hud.append(c2);
      if (st.sep.p > 0) { const c3 = el('span', 'hchip'); c3.innerHTML = `기울기 <span class="mono">${fmt(Math.abs(H.tilt), 2)}°</span> · 끝 틈 <span class="mono">${fmt(C.CELL.L * Math.sin(Math.abs(H.tilt) * D2R), 1)} mm</span>`; hud.append(c3); }
    }
    if (H.carry === 'cover') { const p = payload(); const c4 = el('span', 'hchip' + (p > PRM.Zload * 0.9 ? ' alert' : '')); c4.innerHTML = `Z축 하중 <span class="mono">${fmt(p, 1)} / ${PRM.Zload} kg</span>`; hud.append(c4); }
    const idx = STEPS.findIndex((s) => s.k === st.step);
    document.querySelectorAll('#phases .ph').forEach((b, k) => { b.classList.toggle('on', b.dataset.p === st.step); b.classList.toggle('done', idx >= 0 && k < idx); b.setAttribute('aria-current', String(b.dataset.p === st.step)); });
    $('#desc').textContent = st.desc;
    const bn = $('#banner');
    if (st.banner) { bn.hidden = false; bn.replaceChildren(el('p', '', st.banner)); } else bn.hidden = true;
    let gone = 0, left = 0, fail = 0;
    document.querySelectorAll('#cmap .cbtn').forEach((b) => {
      const i = +b.dataset.i, s = st.status[i];
      const out = !['in', 'held'].includes(s);
      b.classList.toggle('gone', out && s !== 'fail'); b.classList.toggle('fail', s === 'fail');
      b.classList.toggle('tgt', i === st.target || (i === H.cell && s === 'held'));
      b.classList.toggle('nxt', i === st.next);
      if (!out || s === 'fail') { const c = heatRGB(st.Ta[i]); b.style.background = rgbCss(c); b.style.color = lum(c) < 0.5 ? '#fff' : '#1b2023'; }
      b.title = `${label(i)} · 접착층 ${fmt(st.Ta[i])} °C · 셀 ${fmt(st.Tc[i])} °C`;
      if (s === 'in' || s === 'held') left++; else if (s === 'fail') fail++; else gone++;
    });
    $('#cmapsum').textContent = `떼어냄 ${gone} · 남음 ${left}${fail ? ` · 실패 ${fail}` : ''}`;
    const s = st.sep, i = s ? s.i : (ci >= 0 ? ci : 6);
    const pills = $('#pills'); pills.replaceChildren();
    const pill = (txt, on, cls) => { const p = el('span', 'pill ' + cls + (on ? ' on' : '')); p.append(el('span', 'd'), document.createTextNode(txt)); pills.append(p); };
    if (st.prepDone || H.tool === 3) {
      pill(st.coilOn ? '코일 켬' : '코일 끔', st.coilOn, 'heat');
      pill(st.air ? '냉각 공기 켬' : '냉각 공기 끔', st.air, 'air');
    }
    pill(`진공 −${fmt(H.vac * 60)} kPa`, H.vac > 0.05, 'vac');
    if (H.tool === 2) { pill(st.chip ? '절삭·칩 흡입' : '스핀들 정지', st.chip, 'heat'); pill(H.slide < 1 ? '슬라이드 내림' : H.slide > 79 ? '슬라이드 올림' : '슬라이드 이동', H.slide < 1, 'air'); }
    if (st.suck) pill('냉각수 흡입·퍼지', true, 'air');
    if (s) pill(s.hold ? '당김 한계에서 대기' : s.p > 0 ? '필링 중' : '당기는 중', true, 'hold');
    const nb = [i - 1, i + 1].filter((k) => k >= 0 && k < N && rowOf(k) === rowOf(i) && st.present[k]);
    const avg = (() => { let a = 0, n = 0; for (let k = 0; k < N; k++) if (st.present[k]) { a += st.Tc[k]; n++; } return n ? a / n : TH.Tamb; })();
    const pl = payload();
    const ro = [
      ['기울임축 중심 X', `${fmt(H.x)} mm`], ['Y', `${fmt(H.y)} mm`], ['Z', `${fmt(H.z)} mm`], ['θ 회전 · 기울기', `${fmt(H.rot)}° · ${fmt(Math.abs(H.tilt), 2)}°`],
      ['Z축 하중 (가정)', pl != null ? `${fmt(pl, 1)} kg` : '-', pl != null && pl > PRM.Zload * 0.9],
      ['공구 교환', `${st.toolChanges}번 · ${fmt(st.toolChangeT)} s`],
      ['당김 힘', s ? `${fmt(s.F, 1)} N` : '-'], ['필요한 힘', s ? `${fmt(s.Fneed, 1)} N` : '-'],
      [`냉각판 (${label(i)})`, `${fmt(st.Tp[i])} °C`, st.Tp[i] > PRM.Tset], [`접착층 (${label(i)})`, `${fmt(st.Ta[i])} °C`],
      ['셀 바닥 (모델 추정)', `${fmt(st.Tb[i])} °C`, st.Tb[i] > PRM.TbWarn], ['셀 윗면 (IR)', `${fmt(st.Tc[i])} °C`, st.Tc[i] > PRM.Tir],
      ['이웃 접착층 최고', nb.length ? `${fmt(Math.max(...nb.map((k) => st.Ta[k])))} °C` : '-'], ['블록 셀 평균', `${fmt(avg, 1)} °C`],
    ];
    const dl = $('#ro'); dl.replaceChildren();
    for (const [k, v, hot] of ro) { const d = el('div'); d.append(el('dt', '', k), el('dd', hot ? 'hot' : '', v)); dl.append(d); }
    const ai = H.cell >= 0 ? H.cell : st.target;
    $('#anom').disabled = ai < 0 || st.anomaly >= 0 || !!st.emergency;
    drawCharts();
    if (!force && now - lastHeavy < 500) return;
    lastHeavy = now;
    drawFindings();
    drawRecords();
    const ev = $('#ev'); ev.replaceChildren();
    st.events.slice(-40).reverse().forEach((e) => { const li = el('li', e.alert ? 'alert' : ''); li.append(el('span', 't', mmss(e.t)), el('span', 'm', e.m)); ev.append(li); });
    if (!st.events.length) ev.append(el('li', '', '아직 없음'));
  }

  // ------------------------------------------------------------------ charts (SVG, one axis each)
  const NS = 'http://www.w3.org/2000/svg';
  const sv = (tag, at) => { const e = document.createElementNS(NS, tag); for (const k in at) e.setAttribute(k, at[k]); return e; };
  const SER1 = [{ n: '냉각판', c: '--s1', k: 1 }, { n: '접착층', c: '--s2', k: 2 }, { n: '셀 바닥(추정)', c: '--s3', k: 3 }, { n: '셀 윗면(IR)', c: '--s4', k: 4 }];
  const SER2 = [{ n: '필요한 힘', c: '--s1', k: 6 }, { n: '당김 힘', c: '--s2', k: 5 }];
  function legend(id, ser) {
    const L = $(id); if (L.childElementCount) return;
    ser.forEach((s) => { const x = el('span'); const i = el('i'); i.style.background = `var(${s.c})`; x.append(i, document.createTextNode(s.n)); L.append(x); });
  }
  function niceMax(v, step) { return Math.ceil(v / step) * step; }
  function drawChart(svgId, wrapId, rows, ser, yMax, yStep, refs, unit, h) {
    const svg = $(svgId), wrap = $(wrapId), W = Math.max(260, wrap.clientWidth), M = { l: 34, r: 78, t: 8, b: 22 };
    svg.setAttribute('viewBox', `0 0 ${W} ${h}`); svg.setAttribute('height', h); svg.replaceChildren();
    const tMax = Math.max(60, niceMax(rows.length ? rows[rows.length - 1][0] : 0, 30));
    const X = (t) => M.l + (W - M.l - M.r) * t / tMax, Y = (v) => M.t + (h - M.t - M.b) * (1 - clamp(v, 0, yMax) / yMax);
    for (let v = 0; v <= yMax + 1e-6; v += yStep) {
      svg.append(sv('line', { class: 'grid', x1: M.l, x2: W - M.r, y1: Y(v), y2: Y(v) }));
      const tx = sv('text', { class: 'tick', x: M.l - 6, y: Y(v) + 3.5, 'text-anchor': 'end' }); tx.textContent = v; svg.append(tx);
    }
    const xs = tMax <= 120 ? 30 : tMax <= 300 ? 60 : 120;
    for (let t = 0; t <= tMax + 1e-6; t += xs) {
      const tx = sv('text', { class: 'tick', x: X(t), y: h - 6, 'text-anchor': 'middle' }); tx.textContent = t === 0 ? '0 s' : t; svg.append(tx);
    }
    let prevY = null;
    for (const r of refs) {
      if (r.v > yMax) continue;
      const y = Y(r.v);
      svg.append(sv('line', { class: 'ref', x1: M.l, x2: W - M.r, y1: y, y2: y }));
      const right = prevY != null && Math.abs(prevY - y) < 13;
      const tx = sv('text', right ? { x: W - M.r - 4, y: y + 11, 'text-anchor': 'end' } : { x: M.l + 4, y: y - 3 });
      tx.textContent = r.n; svg.append(tx); prevY = y;
    }
    if (!rows.length) { const tx = sv('text', { x: M.l + 8, y: h - M.b - 8 }); tx.textContent = '셀을 하나 떼어 보면 그래프가 그려져요.'; svg.append(tx); return null; }
    if (rows.some((r) => ser.some((q) => r[q.k] > yMax))) {
      const tx = sv('text', { x: W - M.r - 4, y: M.t + 10, 'text-anchor': 'end' }); tx.textContent = `맨 위에 붙은 구간 = ${yMax} ${unit} 이상`; svg.append(tx);
    }
    const step = Math.max(1, Math.floor(rows.length / 500));
    const ends = [];
    for (const s of ser) {
      let d = '';
      for (let k = 0; k < rows.length; k += step) d += (d ? 'L' : 'M') + X(rows[k][0]).toFixed(1) + ',' + Y(rows[k][s.k]).toFixed(1);
      const last = rows[rows.length - 1];
      d += 'L' + X(last[0]).toFixed(1) + ',' + Y(last[s.k]).toFixed(1);
      svg.append(sv('path', { class: 'ln', d, style: `stroke:var(${s.c})` }));
      ends.push({ s, x: X(last[0]), y: Y(last[s.k]), v: last[s.k] });
    }
    const lab = ends.map((e) => ({ ...e, ly: e.y })).sort((a, b) => a.ly - b.ly);
    for (let k = 1; k < lab.length; k++) if (lab[k].ly - lab[k - 1].ly < 13) lab[k].ly = lab[k - 1].ly + 13;
    const over = lab.length ? lab[lab.length - 1].ly - (h - M.b) : 0;
    if (over > 0) lab.forEach((l) => { l.ly -= over; });
    for (const l of lab) {
      svg.append(sv('circle', { class: 'dot', cx: l.x, cy: l.y, r: 4, style: `fill:var(${l.s.c})` }));
      if (Math.abs(l.ly - l.y) > 3) svg.append(sv('line', { class: 'xh', x1: l.x + 5, y1: l.y, x2: l.x + 12, y2: l.ly }));
      const tx = sv('text', { class: 'lab', x: l.x + 14, y: l.ly + 4 }); tx.textContent = `${l.s.n.replace('(추정)', '').replace('(IR)', '')} ${fmt(l.v)}`; svg.append(tx);
    }
    const hit = sv('rect', { x: M.l, y: M.t, width: W - M.l - M.r, height: h - M.t - M.b, fill: 'transparent' });
    const xh = sv('line', { class: 'xh', y1: M.t, y2: h - M.b, x1: -10, x2: -10 }); svg.append(xh, hit);
    let tip = wrap.querySelector('.tip'); if (!tip) { tip = el('div', 'tip'); tip.hidden = true; wrap.append(tip); }
    const show = (ev) => {
      const r = svg.getBoundingClientRect(), px = (ev.clientX - r.left) * W / r.width, t = (px - M.l) / (W - M.l - M.r) * tMax;
      let best = 0; for (let k = 0; k < rows.length; k++) if (Math.abs(rows[k][0] - t) < Math.abs(rows[best][0] - t)) best = k;
      const row = rows[best]; xh.setAttribute('x1', X(row[0])); xh.setAttribute('x2', X(row[0]));
      tip.replaceChildren(el('div', '', `${fmt(row[0], 1)} s`));
      ser.forEach((s) => { const d = el('div', 'row2'); const a = el('span'); const i = el('i'); i.style.background = `var(${s.c})`; a.append(i, document.createTextNode(' ' + s.n)); d.append(a, el('b', '', `${fmt(row[s.k], s.k >= 5 ? 1 : 0)} ${unit}${row[s.k] > yMax ? ' ↑' : ''}`)); tip.append(d); });
      tip.hidden = false;
      const x = (ev.clientX - wrap.getBoundingClientRect().left); tip.style.left = Math.min(x + 12, wrap.clientWidth - 170) + 'px'; tip.style.top = '4px';
    };
    hit.addEventListener('pointermove', show); hit.addEventListener('pointerdown', show);
    hit.addEventListener('pointerleave', () => { tip.hidden = true; xh.setAttribute('x1', -10); xh.setAttribute('x2', -10); });
    return tMax;
  }
  let chartSig = '';
  function drawCharts() {
    legend('#leg1', SER1); legend('#leg2', SER2);
    const S = st.series && st.sep ? st.series : st.lastSeries;
    const rows = S ? S.rows : [];
    const sig = `${S ? S.i : -1}|${rows.length}|${PRM.T50}|${PRM.Flim}|${PRM.Tir}|${$('#cw1').clientWidth}|${$('#tview').hidden}`;
    if (sig === chartSig) return; chartSig = sig;
    $('#chartcell').textContent = S ? `${label(S.i)} · 가열 시작부터` : '';
    const tMaxT = Math.max(160, niceMax(Math.max(PRM.Tset, ...rows.map((r) => Math.max(r[1], r[2]))), 50));
    drawChart('#ch1', '#cw1', rows, SER1, tMaxT, 50, [{ v: PRM.T50, n: `접착 절반 강도 ${PRM.T50} °C (가정)` }, { v: PRM.TbWarn, n: `셀 바닥 주의 ${PRM.TbWarn} °C (가정)` }], '°C', 170);
    const fMax = Math.max(70, niceMax(Math.max(PRM.Flim, PRM.Fsuc) * 1.25, 10));
    drawChart('#ch2', '#cw2', rows, SER2, fMax, fMax > 100 ? 40 : 20, [{ v: PRM.Flim, n: `당김 한계 ${PRM.Flim} N` }, { v: PRM.Fsuc, n: `이상 흡착력 ${fmt(PRM.Fsuc)} N` }], 'N', 130);
    const tv = $('#tview');
    if (!tv.hidden) {
      const tb = el('table'); const hr = el('tr'); ['시간 s', '냉각판', '접착층', '셀 바닥', '셀 윗면', '당김 N', '필요 N'].forEach((h) => hr.append(el('th', '', h))); tb.append(hr);
      rows.filter((r, k) => k % 10 === 0 || k === rows.length - 1).forEach((r) => { const tr = el('tr'); [r[0], r[1], r[2], r[3], r[4], r[5], r[6]].forEach((v, k) => tr.append(el('td', '', fmt(v, k === 0 || k >= 5 ? 1 : 0)))); tb.append(tr); });
      tv.replaceChildren(rows.length ? tb : el('p', 'empty', '아직 데이터가 없어요.'));
    }
  }

  // ------------------------------------------------------------------ findings (computed from the run + geometry)
  function geomFindings(F) {
    // seal-cut reach and cup clearance (from the D-09 tool geometry and the assumed cover)
    const segs = sealPlan(), total = segs.reduce((a, s) => a + s.L, 0), skip = segs.reduce((a, s) => a + s.L * (1 - Math.max(0, s.ub - s.ua)), 0);
    if (skip > 1) F.push(['warn', `<b>실링 절개: 커버 둘레 ${fmt(total / 1000, 1)} m 중 ${fmt(skip)} mm를 못 잘라요.</b> 엔드밀이 공구 중심에서 ${C.T2.spindle[0]} mm 떨어져 있어서, 노즐·호스가 커버에 안 닿는 방향으로 돌리면 모서리 근처에서 공구 중심이 갠트리 행정(X ${C.X[0]}~, Y ±${C.Y[1]}) 밖으로 나가요 (가정 커버·절단선 기준).`]);
    const clear = -C.T2.tip_z - 0.5 - C.COVER.h;
    F.push(['info', `실링 절개 때 흡착컵과 커버 윗면 사이 ${fmt(clear, 1)} mm (엔드밀은 컵 면보다 ${-C.T2.tip_z} mm 아래까지 나옴, 가정 커버 높이 ${C.COVER.h} mm). 커버가 약 ${fmt(-C.T2.tip_z - 0.5 - 5)} mm보다 높으면 컵이 커버에 닿아요.`]);
    const pl = PRM.m02 + PRM.mHead + PRM.mCover;
    F.push(pl > PRM.Zload * 0.9 ? ['warn', `<b>커버를 들 때 Z축 하중 약 ${fmt(pl, 1)} kg</b> (02 ${PRM.m02} + 교환기 마스터·기울임축 ${PRM.mHead} + 커버 ${PRM.mCover}, 모두 가정) — 40 kg급의 ${fmt(pl / PRM.Zload * 100)}%로 여유가 거의 없어요.`]
      : ['ok', `커버를 들 때 Z축 하중 약 ${fmt(pl, 1)} kg / 40 kg급 (가정).`]);
    const fs = 4 * PRM.dpCover * 1e-3 * Math.PI * (PRM.cupD / 2) ** 2;
    F.push(['info', `커버 흡착: Ø${PRM.cupD} 컵 4개 이상 흡착력 약 ${fmt(fs)} N, 커버 무게 ${fmt(PRM.mCover * 9.81)} N → 이상값 기준 ${fmt(fs / (PRM.mCover * 9.81), 1)}배. 실링이 덜 잘리면 더 큰 힘이 필요해요.`]);
    const cb = C.COVER.body, cw = cb[3] - cb[2], cl = cb[1] - cb[0], tcx = (C.TABLE[0] + C.TABLE[1]) / 2, px = Math.min(tcx, C.X[1]);
    const ox0 = (C.TABLE[0]) - (px - cw / 2), ox1 = (px + cw / 2) - C.TABLE[1], oy = cl / 2 - (C.TABLE[3] - C.TABLE[2]) / 2;
    F.push(['warn', `<b>커버 거치대가 커버보다 작아요.</b> 커버(${fmt(cl)}×${fmt(cw)}, 실링 안쪽)를 90° 돌려 놓아도 거치대(${C.TABLE[1] - C.TABLE[0]}×${C.TABLE[3] - C.TABLE[2]}) 밖으로 X ${fmt(ox0)}/${fmt(ox1)} mm, Y ${fmt(oy)} mm씩 튀어나와요. 거치대 중심(X ${tcx})이 갠트리 X 끝(${C.X[1]})보다 바깥이라 ${fmt(tcx - px)} mm 치우쳐 놓여요.`]);
    const hit = coverTableClash();
    if (hit.length) {
      const c = coverPlacedBox(), x0 = Math.min(...hit.map((q) => q.b[0])), x1 = Math.max(...hit.map((q) => q.b[1])), top = Math.max(...hit.map((q) => q.b[5]));
      F.push(['warn', `<b>거치대에 놓은 커버가 ${[...new Set(hit.map((q) => q.n))].join(', ')}와 겹쳐요.</b> 커버를 X ${fmt((c[0] + c[1]) / 2)} 중심에 놓으면 X ${fmt(c[0])}부터 차지하는데, X ${fmt(Math.max(c[0], x0))}~${fmt(Math.min(c[1], x1))} 구간에서 이 물체들이 커버 높이(Z ${fmt(c[4])}~${fmt(c[5])}) 안까지 올라와요. 커버 거치대·공구 거치대 배치나 갠트리 X 행정을 다시 정해야 해요 (가정 배치, 정지 상태 겹침).`]);
    }
    const lowE = C.ZT[0] + C.TOOLBB[1][4] - (C.ELEC[5] - C.ELEC[4]);
    F.push(['warn', `<b>전장품도 회수함(12)에 약 ${fmt((lowE - C.BINS['12'].floor) / 1000, 2)} m 떨어뜨려야 해요.</b> 01이 가장 낮게 내려가도 전장품 바닥이 ${fmt(lowE)} mm예요 (01 외형 기준).`]);
  }
  function drawFindings() {
    const F = [];
    const lowBottom = C.ZT[0] - C.TILT - C.CELL.H;
    const binDrops = st.drops.filter((d) => d.to === 'bin');
    const binMax = binDrops.length ? Math.max(...binDrops.map((d) => d.h)) : lowBottom - C.BIN.floor;
    F.push(['warn', `<b>셀 회수함에 약 ${fmt(binMax / 1000, 2)} m 떨어뜨려야 해요.</b> Z축이 가장 낮게 내려가도(기울임축 Z ${C.ZT[0]}) 셀 바닥이 ${fmt(lowBottom)} mm라서 회수함 바닥(${C.BIN.floor} mm)까지 못 내려가요. 회수함 받침을 올리거나 회수 방식을 바꿔야 해요.`]);
    geomFindings(F);
    const recs = st.records.filter((r) => r.tSep != null);
    const all = st.cycle && st.sep ? recs.concat([st.cycle]) : recs;
    if (all.length) {
      const tb = Math.max(...all.map((r) => r.maxTb)), tc = Math.max(...all.map((r) => r.maxTc));
      const nb = all.filter((r) => r.maxTaN > 0), taN = nb.length ? Math.max(...nb.map((r) => r.maxTaN)) : null;
      F.push(tb > PRM.TbWarn
        ? ['warn', `<b>셀 바닥 추정 최고 ${fmt(tb)} °C</b> — 가정 주의 온도 ${PRM.TbWarn} °C보다 높아요. 접착층이 셀 바로 밑이라 셀 바닥도 거의 같이 뜨거워져요. 접착이 몇 °C에서 떨어지는지가 이 방식의 핵심 확인 사항이에요.`]
        : ['ok', `셀 바닥 추정 최고 ${fmt(tb)} °C — 가정 주의 온도 ${PRM.TbWarn} °C 이하예요.`]);
      F.push(['info', `셀 윗면(IR)은 최고 ${fmt(tc)} °C예요. 윗면은 늦게 데워져서 IR만으로는 바닥 온도를 알 수 없어요 — 냉각판 센서와 모델 추정을 같이 써야 해요.`]);
      if (taN != null) F.push(taN > PRM.T50 - 15
        ? ['warn', `<b>이웃 셀 접착층 최고 ${fmt(taN)} °C</b> — 연화 온도(${PRM.T50} °C)에 가까워 이웃 셀도 약해질 수 있어요.`]
        : ['ok', `이웃 셀 접착층 최고 ${fmt(taN)} °C — 연화 온도보다 충분히 낮아 같이 떨어지지 않아요.`]);
    }
    F.push(PRM.Flim >= PRM.Fsuc
      ? ['warn', `<b>당김 한계 ${PRM.Flim} N이 이상 흡착력 ${fmt(PRM.Fsuc)} N 이상</b> — 컵이 셀보다 먼저 떨어질 수 있어요.`]
      : ['ok', `당김 한계 ${PRM.Flim} N < 이상 흡착력 ${fmt(PRM.Fsuc)} N (여유 ${fmt(PRM.Fsuc - PRM.Flim)} N).`]);
    F.push(PRM.theta > C.PEEL_LIMIT_DEG
      ? ['warn', `<b>필링 각도 ${PRM.theta}°</b>가 블록 경계 부재 접촉 각도 ${C.PEEL_LIMIT_DEG}°보다 커요.`]
      : ['ok', `필링 각도 ${PRM.theta}° < 경계 부재 접촉 ${C.PEEL_LIMIT_DEG}° (가정 형상, 틈 ${C.END_GAP} mm).`]);
    F.push(PRM.padRelease
      ? ['info', '셀 사이 패드 압축을 풀었다고 가정했어요(가설). 풀지 않으면 마찰(예시 약 400 N)이 흡착력보다 훨씬 커요 — 체크를 끄고 돌려 보세요.']
      : ['warn', `<b>패드 압축을 풀지 않음</b> — 패드 마찰(예시 ${PRM.Fpad} N)이 당김 한계보다 커서 떼어낼 수 없어요 (가설).`]);
    // time summary (from this run)
    const T = Object.assign({}, st.stepT); if (st.step && st.stepNow != null) T[st.step] = (T[st.step] || 0) + st.t - st.stepNow;
    if (T.s4 || T.s5) {
      const prep = (T.s4 || 0) + (T.s5 || 0) + (T.s6 || 0) + (T.s7 || 0);
      const parts = STEPS.filter((s) => T[s.k] && ['s4', 's5', 's6', 's7'].includes(s.k)).map((s) => `${s.n}단계 ${fmt(T[s.k] / 60, 1)}분`).join(', ');
      F.push(['info', `이번 실행 시간: ${parts} (합계 ${fmt(prep / 60, 1)}분, 공구 교환 ${st.toolChanges}번 ${fmt(st.toolChangeT)}초 포함). 버스바 절단은 대상 블록 1개(44곳)만 계산 — 팩 블록 24개면 약 ${fmt((T.s5 || 0) * 24 / 60)}분으로 늘어요.`]);
      if (st.toolChanges >= 5) F.push(['info', `공정표 순서대로면 공구 교환이 7번이에요(01→02→01→02→01→02→03). 배선 제거와 전장품 분리를 한 번에(01), 버스바 절단과 냉각수 흡입을 한 번에(02) 하면 5번으로 줄어요 — 순서를 바꿔도 되는지 확인이 필요해요.`]);
    }
    const okr = st.records.filter((r) => r.result === '회수함');
    if (okr.length) {
      const a = okr.reduce((s, r) => s + r.tCycle, 0) / okr.length, b = okr.reduce((s, r) => s + r.tSep, 0) / okr.length;
      F.push(['info', `셀 1개 평균 ${fmt(a)}초(가열·필링 ${fmt(b)}초). 같은 속도면 블록 하나(셀 24개)에 약 ${fmt(a * 24 / 60)}분 — 가열이 대부분이에요. 바로 옆 셀은 미리 데워져 있어 더 빨리 떨어져요.`]);
    }
    let avg = 0, n = 0; for (let k = 0; k < N; k++) if (st.present[k]) { avg += st.Tc[k]; n++; }
    if (n && avg / n > TH.Tamb + 3) F.push(['info', `블록 셀 평균 ${fmt(avg / n, 1)} °C — 냉각수를 빼 둔 상태라 연속 작업할수록 블록이 데워져요.`]);
    if (st.travelMax) F.push(st.travelMax >= C.ZT[1] - 0.5 ? ['warn', '<b>이동 높이가 Z 한계에 닿았어요.</b> 경로 중 높은 장비를 넘지 못할 수 있어요.'] : ['ok', `이동할 때 가장 높이 올라간 기울임축 Z ${fmt(st.travelMax)} (한계 ${C.ZT[1]}).`]);
    F.push(['info', `비상 침수조: 가장 낮게 내려가면 셀 바닥이 테두리(${C.TANK.rim} mm)보다 ${fmt(lowBottom - C.TANK.rim)} mm 위 — 넣을 수는 있어요. 물 높이는 아직 정하지 않았어요.`]);
    const em = st.emLast;
    if (em && em.tDone != null) F.push(['info', `이상 감지부터 침수조 투입까지 ${fmt(em.tDone - em.t0, 1)}초 (이동 계산값). 감지 전 발열 시간은 포함 안 됨.`]);
    else if (em && em.where !== 'carry') F.push(['warn', '<b>셀이 붙어 있거나 공구에 잡혀 있지 않을 때의 이상</b>은 침수조로 옮길 방법이 아직 없어요.']);
    const order = { warn: 0, ok: 1, info: 2 };
    F.sort((a, b) => order[a[0]] - order[b[0]]);
    const ul = $('#fnd'); ul.replaceChildren();
    for (const [k, html] of F) { const li = el('li'); li.append(el('span', 'st ' + k, k === 'warn' ? '주의' : k === 'ok' ? '확인' : '참고')); const p = el('p'); p.innerHTML = html; li.append(p); ul.append(li); }
  }
  function drawRecords() {
    const t = $('#rec'); t.replaceChildren();
    const hr = el('tr'); ['셀', '가열·필링', '사이클', '셀 바닥 최고', '결과'].forEach((h) => hr.append(el('th', '', h))); t.append(hr);
    if (!st.records.length) { const tr = el('tr'); const td = el('td', 'empty', '아직 없음'); td.colSpan = 5; tr.append(td); t.append(tr); return; }
    st.records.slice().reverse().forEach((r) => {
      const tr = el('tr');
      [label(r.i), r.tSep != null ? `${fmt(r.tSep, 1)} s` : '-', r.tCycle != null ? `${fmt(r.tCycle, 1)} s` : '-', `${fmt(r.maxTb)} °C`, r.result || '-'].forEach((v) => tr.append(el('td', '', v)));
      t.append(tr);
    });
  }

  // ================================================================== loop
  let raf = 0, lastT = 0, active = false;
  function frame(ts) {
    raf = requestAnimationFrame(frame);
    const rdt = Math.min(0.1, (ts - (lastT || ts)) / 1000); lastT = ts;
    let changed = false;
    if (st.running) {
      const simDt = rdt * st.speed, n = Math.min(1200, Math.max(1, Math.ceil(simDt / DT)));
      for (let k = 0; k < n && st.running; k++) stepSim(simDt / n);
      changed = true;
    }
    if ((st.falls.length || (st.elec.fall && !st.elec.fall.done)) && !st.running) { stepFalls(rdt); changed = true; }
    if (changed) syncView();
    const box = V.box, w = box.clientWidth, h = box.clientHeight;
    if (V.w !== w || V.h !== h) { V.w = w; V.h = h; V.renderer.setSize(w, h, false); V.cam.aspect = w / Math.max(h, 1); V.dirty = true; }
    camUpdate(rdt);
    const sig = V.cam.position.toArray().map((v) => v.toFixed(1)).join(',') + CAM.tgt.map((v) => v.toFixed(1)).join(',');
    if (V.dirty || sig !== V.sig) { V.renderer.render(V.sc, V.cam); V.dirty = false; V.sig = sig; }
    refreshUI(false);
  }

  // ================================================================== figure scenes (process-sequence figures)
  function figTarget(cam) {
    // same rules as the figure capture: fixed point, or the head / end-mill tip / cup plane / peel pivot (+ offset)
    let t;
    if (Array.isArray(cam.tgt)) t = cam.tgt.slice();
    else if (cam.tgt === 'head') t = [H.x, H.y, H.z];
    else if (cam.tgt === 'tip') { const r = H.rot * D2R, sp = C.T2.spindle; t = [H.x + sp[0] * Math.cos(r) - sp[1] * Math.sin(r), H.y + sp[0] * Math.sin(r) + sp[1] * Math.cos(r), H.z + C.T2.tip_z - C.DOCK['2'] + H.slide]; }
    else if (cam.tgt === 'cup') t = [H.x, H.y, H.z - (H.tool ? C.DOCK[String(H.tool)] : 70)];
    else if (cam.tgt === 'peel' && st.sep) { const p = st.sep; t = [p.cx - p.sgn * C.CELL.L / 2, cellXY(p.i)[1], C.ZC - C.CELL.H + 25]; }
    else t = [H.x, H.y, H.z - 200];
    const o = cam.off || [0, 0, 0];
    return [t[0] + o[0], t[1] + o[1], t[2] + o[2]];
  }
  function showScene(f) {
    jumpTo(f.step, false);
    if (f.anomaly) { const i = H.cell >= 0 ? H.cell : st.target; if (i >= 0 && st.anomaly < 0) { st.anomaly = i; log(`가상 이상 발열 시작: ${label(i)} (내부 ${PRM.Qanom} W 가정)`, true); } }
    const fn = new Function('s', 'h', 'return ' + f.until);
    fastForward(() => { try { return !!fn(st, H); } catch (e) { return true; } });
    st.running = false;
    camPreset('free');
    Object.assign(CAM, { tgt: figTarget(f.cam), dist: f.cam.dist, az: f.cam.az, el: f.cam.el, goal: null, fixed: null, user: 0 });
    CAM.auto = false;
    if (!st.banner) st.desc = `공정 순서 그림 '${f.no} ${f.title}' 장면이에요. ▶를 누르면 여기서부터 이어서 돌아가요. 시점은 '따라가기'로 바꿀 수 있어요.`;
    syncView(); refreshUI(true);
  }

  // ================================================================== pose export (per-step STEP) and figure helpers
  function poseJSON() {
    const m16 = (M) => { const e = M.elements; return [e[0], e[4], e[8], e[12], e[1], e[5], e[9], e[13], e[2], e[6], e[10], e[14], e[3], e[7], e[11], e[15]]; };
    return { t: st.t, step: st.step, phase: st.phase, head: { x: H.x, y: H.y, z: H.z, rot: H.rot, tilt: H.tilt }, tool: H.tool, slide: H.slide,
      cover: { state: st.cover.state, M: m16(st.cover.M) }, elec: { state: st.elec.state, M: m16(st.elec.M) },
      screws: Array.from(st.screw), bars: Array.from(st.bar),
      cells: Array.from({ length: N }, (_, i) => ({ key: keyOf(i), status: st.status[i], M: m16(st.cellM[i]) })),
      seal: st.seal.segs.map((s) => ({ ua: s.ua, ub: s.ub, cut: s.cut || 0 })) };
  }

  // ================================================================== boot
  let booting = null;
  function loadScript(src) { return new Promise((res, rej) => { const s = document.createElement('script'); s.src = src; s.onload = res; s.onerror = () => rej(new Error('three.js를 불러오지 못했어요.')); document.head.append(s); }); }
  async function boot() {
    for (const u of THREE_URLS) { if (window.THREE) break; try { await loadScript(u); } catch (e) { /* try the next CDN */ } }
    if (!window.THREE) throw new Error('3D 라이브러리(three.js)를 불러오지 못했어요.');
    THREE = window.THREE;
    // the standalone HTML carries the scene inline (file:// cannot fetch); the hosted page loads sim/scene.json
    const inl = document.getElementById('sim-scene');
    let scene;
    if (inl) scene = JSON.parse(inl.textContent);
    else {
      const res = await fetch(SCENE_URL);
      if (!res.ok) throw new Error('3D 모델 파일을 불러오지 못했어요.');
      scene = await res.json();
    }
    C = scene.const; OBS = scene.obstacles;
    st = freshState(); H = freshHead();
    st.seal.segs = sealPlan();
    V = buildView(scene);
    buildUI(); bindCamera(); syncView(); camPreset('all', true); CAM.auto = true;
    $('#simload').hidden = true;
    const mq = matchMedia('(prefers-color-scheme: dark)');
    const re = () => { if (V) applyTheme(V); chartSig = ''; };
    mq.addEventListener && mq.addEventListener('change', re);
    new MutationObserver(re).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    window.ctpSim = { get state() { return st; }, get head() { return H; }, get C() { return C; }, PRM, setSpeed: (s) => { st.speed = s; }, play: togglePlay,
      choose: chooseCell, cam: camPreset, xray: setXray, section: setSection, anomaly: () => $('#anom').click(), jump: jumpTo,
      step(n = 1) { for (let k = 0; k < n; k++) stepSim(DT); syncView(); refreshUI(true); },
      ff(src, max) { const f = new Function('s', 'h', 'return ' + src); const k = fastForward(() => f(st, H), max); syncView(); refreshUI(true); return k; },
      start() { if (idle() && !st.prepDone) planProcess(); },
      setCam(c) { CAM.fixed = c ? { tgt: c.tgt, dist: c.dist, az: c.az, el: c.el } : null; if (c) { Object.assign(CAM, CAM.fixed); CAM.goal = null; } V.dirty = true; },
      snap() { const g = camGoal(); Object.assign(CAM, g); CAM.goal = null; CAM.user = 0; V.dirty = true; },
      figCam(cam) { const t = figTarget(cam); CAM.fixed = { tgt: t, dist: cam.dist, az: cam.az, el: cam.el }; Object.assign(CAM, CAM.fixed); CAM.goal = null; syncView(); camUpdate(0); V.renderer.render(V.sc, V.cam); return t; },
      scene: showScene,
      render() { syncView(); camUpdate(0); V.renderer.render(V.sc, V.cam); },
      pose: poseJSON };
  }
  function open() {
    active = true;
    if (!booting) booting = boot().catch((e) => { $('#simload').textContent = e.message + ' 새로고침해 보세요.'; throw e; });
    booting.then(() => { if (active && !raf) { lastT = 0; raf = requestAnimationFrame(frame); } }).catch(() => {});
  }
  function close() { active = false; if (raf) cancelAnimationFrame(raf); raf = 0; if (st) st.running = false; }
  window.CTPSim = { open, close, jump: (k) => { open(); booting && booting.then(() => jumpTo(k, false)); },
    scene: (f) => { open(); booting && booting.then(() => showScene(f)); } };
})();
