import * as THREE from 'three';

// ---------------- helpers ----------------
const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const P = (t, a, b) => clamp((t - a) / (b - a));
const eo = x => 1 - Math.pow(1 - x, 3);
const eio = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
const back = x => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
const lerp = (a, b, x) => a + (b - a) * x;
const $ = id => document.getElementById(id);
function rng(seed) { let s = seed; return () => (s = (s * 16807) % 2147483647) / 2147483647; }

// ---------------- renderer / scene ----------------
const W = 1080, H = 1920;
const renderer = new THREE.WebGLRenderer({ canvas: $('gl'), antialias: true, preserveDrawingBuffer: true });
renderer.setPixelRatio(1); renderer.setSize(W, H, false);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
const scene = new THREE.Scene();
const BG = new THREE.Color(0x0b1530);
scene.background = BG; scene.fog = new THREE.Fog(0x0b1530, 18, 60);
const camera = new THREE.PerspectiveCamera(42, W / H, 0.1, 200);
scene.add(new THREE.HemisphereLight(0xbcd4ff, 0x1a2140, 1.1));
const sun = new THREE.DirectionalLight(0xffffff, 2.2);
sun.position.set(6, 12, 8); sun.castShadow = true; sun.shadow.mapSize.set(1024, 1024);
Object.assign(sun.shadow.camera, { left: -12, right: 12, top: 12, bottom: -12, near: 1, far: 40 });
scene.add(sun);
const rim = new THREE.DirectionalLight(0x6fb8ff, 1.2); rim.position.set(-8, 5, -8); scene.add(rim);

const std = (c, o = {}) => new THREE.MeshStandardMaterial({ color: c, roughness: .45, metalness: .15, ...o });
function mesh(geo, mat, x = 0, y = 0, z = 0, shadow = true) { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.castShadow = shadow; m.receiveShadow = true; return m; }
function canvasTex(w, h, draw) { const c = document.createElement('canvas'); c.width = w; c.height = h; const g = c.getContext('2d'); draw(g, w, h); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return { tex: t, ctx: g, canvas: c }; }
function rr(g, x, y, w, h, r) { g.beginPath(); g.roundRect(x, y, w, h, r); }

const groups = {};
function grp(name) { const g = new THREE.Group(); g.name = name; scene.add(g); groups[name] = g; return g; }

// ---------------- assets ----------------
function makeCar(body = 0xffc400, taxi = true) {
  const car = new THREE.Group();
  const paint = std(body, { roughness: .3, metalness: .35 });
  car.add(mesh(new THREE.BoxGeometry(2.0, 0.6, 4.2), paint, 0, 0.62, 0));
  car.add(mesh(new THREE.BoxGeometry(2.04, 0.22, 4.3), std(0x1b2133), 0, 0.36, 0));
  car.add(mesh(new THREE.BoxGeometry(1.72, 0.58, 2.2), paint, 0, 1.2, -0.25));
  car.add(mesh(new THREE.BoxGeometry(1.76, 0.4, 2.26), std(0x16233f, { roughness: .08, metalness: .7 }), 0, 1.18, -0.25));
  if (taxi) {
    const chk = canvasTex(512, 32, (g, w, h) => { for (let i = 0; i < 32; i++) for (let j = 0; j < 2; j++) { g.fillStyle = (i + j) % 2 ? '#111' : '#ffc400'; g.fillRect(i * 16, j * 16, 16, 16); } });
    car.add(mesh(new THREE.BoxGeometry(2.03, 0.14, 3.6), new THREE.MeshStandardMaterial({ map: chk.tex, roughness: .5 }), 0, 0.72, 0.1));
    const sign = canvasTex(256, 96, (g, w, h) => { g.fillStyle = '#0b1530'; g.fillRect(0, 0, w, h); g.fillStyle = '#ffc400'; g.font = '900 64px Inter'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('TAXI', w / 2, h / 2 + 4); });
    car.add(mesh(new THREE.BoxGeometry(0.8, 0.26, 0.36), new THREE.MeshStandardMaterial({ map: sign.tex, emissive: 0xffffff, emissiveMap: sign.tex, emissiveIntensity: .6 }), 0, 1.62, -0.25));
  }
  const hl = new THREE.MeshStandardMaterial({ color: 0xfff6d0, emissive: 0xfff2b0, emissiveIntensity: 2 });
  car.add(mesh(new THREE.BoxGeometry(0.45, 0.16, 0.06), hl, -0.62, 0.7, 2.11, false), mesh(new THREE.BoxGeometry(0.45, 0.16, 0.06), hl, 0.62, 0.7, 2.11, false));
  const tl = new THREE.MeshStandardMaterial({ color: 0xff3344, emissive: 0xff2233, emissiveIntensity: 1.5 });
  car.add(mesh(new THREE.BoxGeometry(0.45, 0.14, 0.06), tl, -0.62, 0.72, -2.11, false), mesh(new THREE.BoxGeometry(0.45, 0.14, 0.06), tl, 0.62, 0.72, -2.11, false));
  car.wheels = [];
  for (const [x, z] of [[-1, 1.35], [1, 1.35], [-1, -1.35], [1, -1.35]]) {
    const piv = new THREE.Group(); piv.position.set(x, 0.4, z);
    const w = mesh(new THREE.CylinderGeometry(0.4, 0.4, 0.32, 28), std(0x10131c, { roughness: .8 })); w.rotation.z = Math.PI / 2;
    const hub = mesh(new THREE.CylinderGeometry(0.2, 0.2, 0.34, 6), std(0xc9d1e6, { metalness: .8, roughness: .3 })); hub.rotation.z = Math.PI / 2;
    piv.add(w, hub); car.add(piv); car.wheels.push(piv);
  }
  car.spin = a => car.wheels.forEach(w => w.rotation.x = a);
  return car;
}
function makePerson(color = 0x2aabee) {
  const p = new THREE.Group();
  p.add(mesh(new THREE.CylinderGeometry(0.26, 0.32, 0.8, 20), std(color), 0, 0.4, 0));
  p.add(mesh(new THREE.SphereGeometry(0.24, 24, 16), std(0xf2c7a0), 0, 1.02, 0));
  p.add(mesh(new THREE.SphereGeometry(0.25, 24, 16, 0, Math.PI * 2, 0, Math.PI / 2.2), std(0x2b1d14), 0, 1.06, 0));
  return p;
}
function makePin(color) {
  const p = new THREE.Group(); const m = std(color, { emissive: color, emissiveIntensity: .35 });
  const cone = mesh(new THREE.ConeGeometry(0.34, 0.95, 24), m, 0, 0.48, 0); cone.rotation.x = Math.PI; p.add(cone);
  p.add(mesh(new THREE.SphereGeometry(0.44, 28, 20), m, 0, 1.08, 0));
  p.add(mesh(new THREE.SphereGeometry(0.17, 20, 14), std(0xffffff), 0, 1.12, 0.33));
  return p;
}
function makeX() {
  const g = new THREE.Group(); const m = std(0xef4444, { emissive: 0xef4444, emissiveIntensity: .5 });
  const a = mesh(new THREE.BoxGeometry(1.4, 0.32, 0.32), m); a.rotation.z = Math.PI / 4;
  const b = mesh(new THREE.BoxGeometry(1.4, 0.32, 0.32), m); b.rotation.z = -Math.PI / 4; g.add(a, b); return g;
}

// ---------- phone (screen = canvas texture redrawn per frame) ----------
const SCR = canvasTex(560, 1160, () => {});
function makePhone() {
  const ph = new THREE.Group();
  ph.add(mesh(new THREE.BoxGeometry(1.7, 3.4, 0.18), std(0x0d1326, { metalness: .6, roughness: .25 })));
  const frame = mesh(new THREE.BoxGeometry(1.74, 3.44, 0.14), std(0xc9d1e6, { metalness: .9, roughness: .2 })); ph.add(frame);
  const scr = new THREE.Mesh(new THREE.PlaneGeometry(1.56, 3.24), new THREE.MeshBasicMaterial({ map: SCR.tex, toneMapped: false }));
  scr.position.z = 0.096; ph.add(scr); return ph;
}
const font = (w, s) => `${w} ${s}px Inter`;
function txt(g, s, x, y, f, c, al = 'left') { g.font = f; g.fillStyle = c; g.textAlign = al; g.textBaseline = 'middle'; g.fillText(s, x, y); }
function bubble(g, s, x, y, me, a) {
  if (a <= 0) return; g.save(); g.globalAlpha = clamp(a); g.font = font(700, 40); const w = g.measureText(s).width + 52;
  const bx = me ? 560 - 24 - w : 24; const dy = (1 - eo(clamp(a))) * 30;
  g.fillStyle = me ? '#ffc400' : '#22345e'; rr(g, bx, y + dy, w, 86, 30); g.fill();
  txt(g, s, bx + 26, y + 43 + dy, font(700, 40), me ? '#0b1530' : '#fff'); g.restore();
}
function drawScreen(mode, p) {
  const g = SCR.ctx, w = 560, h = 1160; g.clearRect(0, 0, w, h);
  g.fillStyle = '#0e1730'; g.fillRect(0, 0, w, h);
  txt(g, '9:41', 34, 34, font(700, 24), '#fff'); txt(g, '▮▮▮ 100%', w - 30, 34, font(700, 22), '#fff', 'right');
  if (mode === 'call') {
    const grd = g.createLinearGradient(0, 0, 0, h); grd.addColorStop(0, '#1b2a55'); grd.addColorStop(1, '#0b1226'); g.fillStyle = grd; g.fillRect(0, 60, w, h);
    for (let k = 0; k < 3; k++) { const r = 110 + ((p * 3 + k / 3) % 1) * 140; g.strokeStyle = `rgba(255,255,255,${.35 * (1 - ((p * 3 + k / 3) % 1))})`; g.lineWidth = 4; g.beginPath(); g.arc(w / 2, 330, r, 0, 7); g.stroke(); }
    g.fillStyle = '#ffc400'; g.beginPath(); g.arc(w / 2, 330, 105, 0, 7); g.fill(); txt(g, 'TAXI', w / 2, 334, font(900, 52), '#0b1530', 'center');
    txt(g, 'Taksi', w / 2, 520, font(800, 50), '#fff', 'center');
    const busy = p > .45;
    txt(g, busy ? 'BAND...' : 'Qoʻngʻiroq qilinmoqda...', w / 2, 590, font(700, busy ? 46 : 32), busy ? '#ff5a5a' : '#b8c4e6', 'center');
    if (busy) txt(g, 'Javob yoʻq', w / 2, 650, font(700, 32), '#b8c4e6', 'center');
    g.fillStyle = '#ef4444'; g.beginPath(); g.arc(w / 2, 950, 70, 0, 7); g.fill(); txt(g, '✕', w / 2, 954, font(900, 64), '#fff', 'center');
  } else if (mode === 'bot') {
    g.fillStyle = '#2aabee'; g.fillRect(0, 60, w, 120); g.fillStyle = '#ffc400'; g.beginPath(); g.arc(70, 120, 38, 0, 7); g.fill();
    txt(g, 'Y', 70, 122, font(900, 40), '#0b1530', 'center'); txt(g, 'Yoʻldamiz bot', 126, 106, font(800, 34), '#fff'); txt(g, 'online', 126, 144, font(600, 24), '#dff3ff');
    bubble(g, 'Qayerdan?', 0, 215, false, P(p, 0, .12));
    bubble(g, 'Fargʻona, Margʻilon', 0, 320, true, P(p, .1, .22));
    bubble(g, 'Qayerga?', 0, 425, false, P(p, .2, .32));
    bubble(g, 'Toshkent', 0, 530, true, P(p, .3, .42));
    bubble(g, 'Lokatsiya yuborildi ✓', 0, 635, true, P(p, .4, .52));
    const pr = p > .72, a = P(p, .5, .6); g.globalAlpha = a;
    g.fillStyle = pr ? '#15803d' : '#22c55e'; rr(g, 40, 900 + (pr ? 6 : 0), w - 80, 120, 30); g.fill();
    txt(g, pr ? 'Yuborildi ✓' : 'Soʻrov qoldirish', w / 2, 962 + (pr ? 6 : 0), font(900, 42), '#fff', 'center');
    if (pr) { const q = P(p, .72, 1); g.strokeStyle = `rgba(255,255,255,${.7 * (1 - q)})`; g.lineWidth = 8; g.beginPath(); g.arc(w / 2, 962, 40 + q * 260, 0, 7); g.stroke(); }
    g.globalAlpha = 1;
  } else if (mode === 'notify') {
    const grd = g.createLinearGradient(0, 0, 0, h); grd.addColorStop(0, '#13204a'); grd.addColorStop(1, '#0b1226'); g.fillStyle = grd; g.fillRect(0, 60, w, h);
    const a = back(P(p, .05, .3)); g.save(); g.translate(w / 2, 420); g.scale(a, a); g.translate(-w / 2, -420);
    g.fillStyle = '#fff'; rr(g, 30, 180, w - 60, 560, 36); g.fill();
    g.fillStyle = '#ffc400'; rr(g, 30, 180, w - 60, 100, [36, 36, 0, 0]); g.fill();
    txt(g, 'Yangi yoʻlovchi!', w / 2, 232, font(900, 44), '#0b1530', 'center');
    txt(g, 'Fargʻona → Toshkent', 56, 345, font(800, 42), '#0b1530');
    txt(g, '1 kishi · 1,2 km', 56, 405, font(700, 36), '#5b6680');
    const acc = p > .62;
    g.fillStyle = acc ? '#15803d' : '#22c55e'; rr(g, 60, 470, 210, 100, 24); g.fill(); txt(g, 'Olaman', 165, 521, font(900, 36), '#fff', 'center');
    g.fillStyle = '#e5e7eb'; rr(g, 290, 470, 210, 100, 24); g.fill(); txt(g, 'Rad etish', 395, 521, font(800, 32), '#374151', 'center');
    if (acc) { txt(g, 'Qabul qilindi ✓', w / 2, 660, font(900, 44), '#15803d', 'center'); }
    g.restore();
  }
  SCR.tex.needsUpdate = true;
}

// ---------------- world groups ----------------
// ground + grid (shared)
const ground = mesh(new THREE.PlaneGeometry(400, 400), std(0x111c3c, { roughness: .95 }), 0, 0, 0, false); ground.rotation.x = -Math.PI / 2; scene.add(ground);
const grid = new THREE.GridHelper(400, 200, 0x2a3f75, 0x1a2a55); grid.position.y = 0.01; scene.add(grid);

// G1 road (intro)
const gRoad = grp('road');
const road = mesh(new THREE.PlaneGeometry(9, 300), std(0x262c3d, { roughness: .9 }), 0, 0.02, 0, false); road.rotation.x = -Math.PI / 2; gRoad.add(road);
const dashGeo = new THREE.BoxGeometry(0.22, 0.02, 2.2), dashMat = std(0xffc400, { emissive: 0xffc400, emissiveIntensity: .5 });
const dashes = new THREE.InstancedMesh(dashGeo, dashMat, 40); gRoad.add(dashes);
const poleMat = std(0x8a93ad); const lampMat = new THREE.MeshStandardMaterial({ color: 0xfff1c0, emissive: 0xffe08a, emissiveIntensity: 2 });
const poles = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.08, 0.1, 4, 8), poleMat, 24); const lamps = new THREE.InstancedMesh(new THREE.SphereGeometry(0.22, 12, 8), lampMat, 24); gRoad.add(poles, lamps);
const mts = new THREE.Group(); { const r = rng(5); for (let i = 0; i < 14; i++) { const h = 6 + r() * 10; const m = mesh(new THREE.ConeGeometry(4 + r() * 5, h, 5), std(0x1a2a55, { roughness: 1, flatShading: true }), (r() - .5) * 120, h / 2, -60 - r() * 40, false); mts.add(m); } } gRoad.add(mts);
const carRoad = makeCar(); gRoad.add(carRoad);

// G2 map
const gMap = grp('map');
const mapTex = canvasTex(2048, 2048, (g, w, h) => {
  g.fillStyle = '#13244e'; g.fillRect(0, 0, w, h); const r = rng(11);
  g.strokeStyle = '#1f3570'; g.lineWidth = 3; for (let i = 0; i < 60; i++) { g.beginPath(); const x = r() * w, y = r() * h; g.moveTo(x, y); g.lineTo(x + (r() - .5) * 900, y + (r() - .5) * 900); g.stroke(); }
  g.strokeStyle = '#1d5aa8'; g.lineWidth = 26; g.beginPath(); g.moveTo(0, 900); g.bezierCurveTo(600, 700, 1000, 1300, 2048, 1000); g.stroke();
  g.fillStyle = '#183a2f'; for (let i = 0; i < 30; i++) { g.beginPath(); g.arc(r() * w, r() * h, 30 + r() * 90, 0, 7); g.fill(); }
  g.strokeStyle = '#2b4585'; g.lineWidth = 2; for (let i = 0; i <= 2048; i += 128) { g.beginPath(); g.moveTo(i, 0); g.lineTo(i, h); g.moveTo(0, i); g.lineTo(w, i); g.stroke(); }
});
const mapPlane = mesh(new THREE.PlaneGeometry(26, 26), new THREE.MeshStandardMaterial({ map: mapTex.tex, roughness: .9 }), 0, 0.03, 0, false); mapPlane.rotation.x = -Math.PI / 2; gMap.add(mapPlane);
const F = new THREE.Vector3(-5, 0.1, 6), T = new THREE.Vector3(5, 0.1, -6);
const route = new THREE.CatmullRomCurve3([F, new THREE.Vector3(-3, .1, 2.5), new THREE.Vector3(1, .1, 3), new THREE.Vector3(3, .1, -1.5), T]);
const tubeGeo = new THREE.TubeGeometry(route, 200, 0.16, 10, false);
const tube = mesh(tubeGeo, new THREE.MeshStandardMaterial({ color: 0xffc400, emissive: 0xffc400, emissiveIntensity: .9 }), 0, 0, 0, false); gMap.add(tube);
const pinF = makePin(0xffc400); pinF.position.copy(F); const pinT = makePin(0x2aabee); pinT.position.copy(T); gMap.add(pinF, pinT);
const carMap = makeCar(); carMap.scale.setScalar(.45); gMap.add(carMap);

// G3 phone stage
const gPhone = grp('phone');
const phone = makePhone(); gPhone.add(phone);
const xs = [makeX(), makeX(), makeX()]; xs.forEach(x => gPhone.add(x));
const clockG = new THREE.Group(); { const face = mesh(new THREE.CylinderGeometry(0.9, 0.9, 0.2, 40), std(0xffffff)); face.rotation.x = Math.PI / 2; clockG.add(face);
  const rimm = mesh(new THREE.TorusGeometry(0.9, 0.1, 12, 40), std(0xef4444)); clockG.add(rimm);
  clockG.hand1 = mesh(new THREE.BoxGeometry(0.08, 0.6, 0.05), std(0x0b1530)); clockG.hand1.geometry.translate(0, .28, 0); clockG.hand1.position.z = .14; clockG.add(clockG.hand1);
  clockG.hand2 = mesh(new THREE.BoxGeometry(0.08, 0.42, 0.05), std(0x0b1530)); clockG.hand2.geometry.translate(0, .19, 0); clockG.hand2.position.z = .14; clockG.add(clockG.hand2); }
gPhone.add(clockG);

// G4 nearest driver (map-ish, reuse map plane via separate group)
const gNear = grp('near');
const homePin = makePin(0x22c55e); gNear.add(homePin);
const ring = new THREE.Mesh(new THREE.RingGeometry(0.9, 1.1, 64), new THREE.MeshBasicMaterial({ color: 0x22c55e, transparent: true, side: THREE.DoubleSide })); ring.rotation.x = -Math.PI / 2; ring.position.y = .08; gNear.add(ring);
const nearCars = [[-4.5, -3.5, 0.6], [4.2, -2.5, 2.2], [-3.8, 4.2, 4], [2.2, 2.6, 3.9]].map(([x, z, r], i) => { const c = makeCar(i === 3 ? 0xffc400 : 0x9aa3bd, i === 3); c.scale.setScalar(.5); c.position.set(x, 0, z); c.rotation.y = r; gNear.add(c); return c; });
const card3d = canvasTex(800, 480, (g, w, h) => {
  g.fillStyle = '#ffffff'; rr(g, 0, 0, w, h, 50); g.fill(); g.fillStyle = '#ffc400'; rr(g, 0, 0, w, 110, [50, 50, 0, 0]); g.fill();
  txt(g, 'Haydovchi topildi ✓', w / 2, 58, font(900, 46), '#0b1530', 'center');
  g.fillStyle = '#2aabee'; g.beginPath(); g.arc(120, 270, 80, 0, 7); g.fill(); txt(g, 'A', 120, 274, font(900, 80), '#fff', 'center');
  txt(g, 'Alisher', 240, 190, font(900, 50), '#0b1530'); txt(g, '+998 90 123 45 67', 240, 260, font(700, 38), '#334155');
  txt(g, 'Cobalt · oq', 240, 325, font(700, 38), '#334155'); txt(g, '40 A 123 BC', 240, 390, font(800, 38), '#0b1530');
});
const cardMesh = mesh(new THREE.BoxGeometry(4, 2.4, 0.08), [std(0xffffff), std(0xffffff), std(0xffffff), std(0xffffff), new THREE.MeshBasicMaterial({ map: card3d.tex, toneMapped: false }), std(0xffc400)]);
const gCard = grp('card'); gCard.add(cardMesh);

// G5 seats (top-down car interior)
const gSeats = grp('seats');
{ const base = mesh(new THREE.BoxGeometry(2.6, 0.5, 5), std(0xffc400, { roughness: .3, metalness: .35 }), 0, 0.25, 0); gSeats.add(base);
  const floor = mesh(new THREE.BoxGeometry(2.3, 0.1, 4.6), std(0x1b2133), 0, 0.52, 0); gSeats.add(floor);
  const wsh = mesh(new THREE.BoxGeometry(2.3, 0.08, 0.9), std(0x16233f, { roughness: .1, metalness: .7 }), 0, 0.9, 2.0); wsh.rotation.x = -0.6; gSeats.add(wsh); }
const seatPos = [[-0.6, 0.9], [0.6, 0.9], [-0.7, -1.0], [0, -1.0], [0.7, -1.0]];
const seatMat = std(0x334155), seatOn = std(0x22c55e);
const seats = seatPos.map(([x, z], i) => { const s = new THREE.Group(); s.add(mesh(new THREE.BoxGeometry(i < 2 ? 0.75 : 0.62, 0.25, 0.7), seatMat), mesh(new THREE.BoxGeometry(i < 2 ? 0.75 : 0.62, 0.7, 0.16), seatMat, 0, 0.35, -0.35)); s.position.set(x, 0.62, z); gSeats.add(s); return s; });
const sw = mesh(new THREE.TorusGeometry(0.22, 0.05, 10, 24), std(0x111111), -0.6, 1.2, 1.45); sw.rotation.x = -0.9; gSeats.add(sw);
const driver = makePerson(0xffc400); driver.scale.setScalar(.8); driver.position.set(-0.6, 0.7, 0.85); gSeats.add(driver);
const pax = [1, 2, 3, 4].map(i => { const p = makePerson([0x2aabee, 0xef4444, 0x22c55e, 0xa855f7][i - 1]); p.scale.setScalar(.75); p.position.set(seatPos[i][0], 0.7, seatPos[i][1] - 0.05); gSeats.add(p); return p; });
const carSide = makeCar(); const gDrive = grp('drive'); gDrive.add(carSide); const phone2 = makePhone(); gDrive.add(phone2);

// G6 coins / gift
const gCoins = grp('coins');
const coinGeo = new THREE.CylinderGeometry(0.42, 0.42, 0.1, 36);
const coinTex = canvasTex(256, 256, (g, w, h) => { g.fillStyle = '#ffcc33'; g.fillRect(0, 0, w, h); g.strokeStyle = '#c98a00'; g.lineWidth = 14; g.beginPath(); g.arc(128, 128, 104, 0, 7); g.stroke(); txt(g, 'S', 128, 136, font(900, 140), '#c98a00', 'center'); });
const coinMat = [std(0xe0a400, { metalness: .9, roughness: .25 }), new THREE.MeshStandardMaterial({ map: coinTex.tex, metalness: .7, roughness: .3 }), new THREE.MeshStandardMaterial({ map: coinTex.tex, metalness: .7, roughness: .3 })];
const NC = 70; const coins = []; { const r = rng(21); for (let i = 0; i < NC; i++) { const c = mesh(coinGeo, coinMat); c.userData = { x: (r() - .5) * 9, z: (r() - .5) * 4 - 1, d: r() * 1.4, sp: 5 + r() * 4, rx: r() * 6, ry: r() * 6, vx: (r() - .5) * 6, vz: (r() - .5) * 3, vy: 6 + r() * 5 }; gCoins.add(c); coins.push(c); } }
const gift = new THREE.Group(); { const red = std(0xef4444, { roughness: .4 }), gold = std(0xffc400, { metalness: .5, roughness: .3 });
  gift.add(mesh(new THREE.BoxGeometry(2, 1.6, 2), red, 0, 0.8, 0), mesh(new THREE.BoxGeometry(0.34, 1.62, 2.02), gold, 0, 0.8, 0), mesh(new THREE.BoxGeometry(2.02, 1.62, 0.34), gold, 0, 0.8, 0));
  gift.lid = new THREE.Group(); gift.lid.position.set(0, 1.6, -1.05);
  const l = mesh(new THREE.BoxGeometry(2.2, 0.4, 2.2), red, 0, 0.2, 1.05); const l2 = mesh(new THREE.BoxGeometry(0.36, 0.42, 2.22), gold, 0, 0.2, 1.05);
  const bow1 = mesh(new THREE.TorusGeometry(0.32, 0.1, 10, 24), gold, -0.3, 0.6, 1.05); bow1.rotation.y = .4; const bow2 = mesh(new THREE.TorusGeometry(0.32, 0.1, 10, 24), gold, 0.3, 0.6, 1.05); bow2.rotation.y = -.4;
  gift.lid.add(l, l2, bow1, bow2); gift.add(gift.lid); }
gCoins.add(gift);

// G7 CTA turntable
const gCta = grp('cta');
const plat = mesh(new THREE.CylinderGeometry(3.2, 3.4, 0.3, 64), std(0x1e2f60, { metalness: .5, roughness: .3 }), 0, 0.15, 0); gCta.add(plat);
const platRing = mesh(new THREE.TorusGeometry(3.3, 0.06, 10, 80), new THREE.MeshStandardMaterial({ color: 0xffc400, emissive: 0xffc400, emissiveIntensity: 1.5 }), 0, 0.3, 0); platRing.rotation.x = Math.PI / 2; gCta.add(platRing);
const carCta = makeCar(); carCta.position.y = 0.3; gCta.add(carCta);

// ---------------- labels (projected HTML) ----------------
const labelLayer = $('labels'); const LBL = {};
function label(key, html, v3, show, color) {
  let el = LBL[key]; if (!el) { el = document.createElement('div'); el.className = 'ov lbl'; labelLayer.appendChild(el); LBL[key] = el; el.innerHTML = html; }
  if (!show) { el.style.opacity = 0; return; }
  const p = v3.clone().project(camera); el.style.left = ((p.x + 1) / 2 * W) + 'px'; el.style.top = ((1 - p.y) / 2 * H) + 'px'; el.style.opacity = show; if (color) el.style.borderColor = color;
}

// ---------------- shots ----------------
const TL = window.TIMELINE;
const seg = id => TL.segments.find(s => s.id === id);
function cam(px, py, pz, tx, ty, tz, fov = 42) { camera.position.set(px, py, pz); camera.fov = fov; camera.updateProjectionMatrix(); camera.lookAt(tx, ty, tz); }
const H1 = { intro: '<span class="y">FARGʻONA</span><br>⇄ <span class="b">TOSHKENT</span>' };
const SHOTS = [
  // ---- seg 1: intro
  { seg: 1, a: 0, b: .5, head: H1.intro, show: ['road'], run(lt, p, t) {
    const sp = t * 26; dashes.count = 40; const m = new THREE.Matrix4();
    for (let i = 0; i < 40; i++) { m.makeTranslation(0, 0.03, ((i * 5 + sp) % 200) - 150); dashes.setMatrixAt(i, m); } dashes.instanceMatrix.needsUpdate = true;
    for (let i = 0; i < 24; i++) { const z = ((i * 10 + sp) % 240) - 200; const x = i % 2 ? 6 : -6; m.makeTranslation(x, 2, z); poles.setMatrixAt(i, m); m.makeTranslation(x * .85, 4, z); lamps.setMatrixAt(i, m); }
    poles.instanceMatrix.needsUpdate = true; lamps.instanceMatrix.needsUpdate = true;
    carRoad.position.set(0, Math.sin(t * 30) * .02, 0); carRoad.spin(t * 20);
    const a = lerp(.8, .3, eio(p)); cam(Math.sin(a) * 11, lerp(2.2, 3.2, p), Math.cos(a) * 11, 0, 1.6, 0, 40);
  } },
  { seg: 1, a: .5, b: 1, head: H1.intro, show: ['map'], run(lt, p, t) {
    const k = eio(clamp(p * 1.25)); tube.geometry.setDrawRange(0, Math.floor(tubeGeo.index.count * k / 6) * 6);
    const pt = route.getPointAt(k), pt2 = route.getPointAt(Math.min(1, k + .01)); carMap.position.copy(pt); carMap.lookAt(pt2.x, pt.y, pt2.z); carMap.spin(t * 20);
    [pinF, pinT].forEach((pn, i) => { const s = back(P(p, i * .15, i * .15 + .3)); pn.scale.setScalar(Math.max(.001, s)); pn.position.y = .1 + Math.sin(t * 4 + i) * .08; });
    const a = lerp(-.5, .1, p); cam(Math.sin(a) * 15, lerp(17, 15, p), Math.cos(a) * 15 + 3, 0, 0, 0.5, 45);
    label('F', 'Fargʻona', F.clone().add(new THREE.Vector3(0, 1.8, 0)), P(p, .1, .25), '#ffc400');
    label('T', 'Toshkent', T.clone().add(new THREE.Vector3(0, 1.8, 0)), P(p, .25, .4), '#2aabee');
  } },
  // ---- seg 2: problem
  { seg: 2, a: 0, b: .55, head: 'Taksi qidirib<br><span class="r">charchadingizmi?</span>', chips: [['no', '✕', 'Qoʻngʻiroqlar']], show: ['phone'], run(lt, p, t) {
    drawScreen('call', p); phone.position.set(Math.sin(t * 60) * .04 * (p > .1), .45, 0); phone.rotation.set(-.05, lerp(.4, .2, p), Math.sin(t * 50) * .03);
    xs.forEach(x => x.visible = false); clockG.visible = false;
    cam(0, 0.2, lerp(11.2, 10.2, eio(p)), 0, 0, 0, 42);
  } },
  { seg: 2, a: .55, b: 1, head: 'Taksi qidirib<br><span class="r">charchadingizmi?</span>', chips: [['no', '✕', 'Qoʻngʻiroqlar'], ['no', '✕', 'Kutish']], show: ['phone'], run(lt, p, t) {
    drawScreen('call', .8); phone.position.set(0, .45, 0); phone.rotation.set(-.1, -.3 + p * .3, 0);
    xs.forEach((x, i) => { x.visible = true; const s = back(P(p, i * .15, i * .15 + .3)); x.scale.setScalar(Math.max(.001, s * .8)); x.position.set([-2.1, 2.1, -1.9][i], [1.9, 0.9, -0.9][i], .6); x.rotation.y = t * 2 + i; });
    clockG.visible = true; clockG.position.set(1.9, -0.9, .8); clockG.scale.setScalar(Math.max(.001, back(P(p, .35, .7)) * .9)); clockG.hand1.rotation.z = -t * 8; clockG.hand2.rotation.z = -t * .7; clockG.rotation.y = -.4;
    cam(lerp(1.5, -1, p), 0.5, 11.5, 0, 0, 0, 42);
  } },
  // ---- seg 3: passenger
  { seg: 3, a: 0, b: .36, head: '<span class="b">YOʻLOVCHI</span>misiz?<span class="sm">1 daqiqada soʻrov qoldiring</span>', chips: [['ok', '✓', '1 daqiqada soʻrov']], show: ['phone'], run(lt, p, t) {
    drawScreen('bot', p); xs.forEach(x => x.visible = false); clockG.visible = false;
    phone.position.set(0, .45, 0); phone.rotation.set(-.03, lerp(-1.2, .1, eo(P(p, 0, .3))), 0);
    cam(0, 0.2, lerp(10.8, 10.0, p), 0, 0, 0, 42);
  } },
  { seg: 3, a: .36, b: .72, head: 'Eng <span class="g">yaqin</span><br>haydovchi', chips: [['ok', '✓', 'Bot oʻzi topadi']], show: ['map', 'near'], run(lt, p, t) {
    tube.visible = false; pinF.visible = pinT.visible = carMap.visible = false;
    homePin.position.set(0, .1 + (1 - eo(P(p, 0, .2))) * 4, 0); homePin.scale.setScalar(1.1);
    const rp = (p * 2.2) % 1; ring.scale.setScalar(.5 + rp * 7); ring.material.opacity = (1 - rp) * .8;
    const hi = P(p, .35, .5);
    nearCars.forEach((c, i) => { c.spin(t * 10); if (i === 3) { const k = eio(P(p, .5, 1)); c.position.set(lerp(2.2, 1.2, k), 0, lerp(2.6, 1.3, k)); c.scale.setScalar(.5 + hi * .15 + Math.sin(t * 12) * .02 * hi); } });
    const a = lerp(.3, -.2, p); cam(Math.sin(a) * 11, lerp(12, 10, p), Math.cos(a) * 11, 0, 0, 0.5, 45);
    label('H', 'Siz', homePin.position.clone().add(new THREE.Vector3(0, 2.0, 0)), P(p, .15, .25), '#22c55e');
    label('D', '1,2 km', nearCars[3].position.clone().add(new THREE.Vector3(0, 1.6, 0)), P(p, .4, .5), '#ffc400');
  } },
  { seg: 3, a: .72, b: 1, head: 'Haydovchi <span class="y">maʼlumotlari</span><br>darhol keladi', chips: [], show: ['card'], run(lt, p, t) {
    cardMesh.rotation.set(-.1 + Math.sin(t * 2) * .03, lerp(Math.PI, 0.18, eo(P(p, 0, .45))) + Math.sin(t * 1.5) * .05, 0); cardMesh.position.set(0, .3, 0);
    cam(0, 0.2, lerp(11.5, 10.5, p), 0, 0, 0, 42);
  } },
  // ---- seg 4: driver
  { seg: 4, a: 0, b: .45, head: '<span class="y">HAYDOVCHI</span>misiz?', chips: [['ok', '✓', 'Yaqin yoʻlovchilar']], show: ['drive'], run(lt, p, t) {
    drawScreen('notify', p); carSide.position.set(-1.6, 0, -1.5); carSide.rotation.y = -.5; carSide.spin(t * 6);
    phone2.position.set(2.3, 3.1 + Math.sin(t * 3) * .08, 2.0); phone2.rotation.set(0, -.45, .06); phone2.scale.setScalar(Math.max(.001, back(P(p, 0, .25)) * .85));
    cam(lerp(4.5, 3.5, p), 3.4, lerp(12.5, 11.5, p), 0.4, 2.6, 0, 42);
  } },
  { seg: 4, a: .45, b: 1, head: 'Boʻsh joy<br>bilan <span class="r">yurmaysiz!</span>', chips: [], show: ['seats'], run(lt, p, t) {
    pax.forEach((m, i) => { const s = back(P(p, .1 + i * .17, .25 + i * .17)); m.scale.setScalar(Math.max(.001, s * .75)); seats[i + 1].children.forEach(c => c.material = s > .5 ? seatOn : seatMat); });
    const a = lerp(-.25, .25, p); cam(Math.sin(a) * 5, lerp(8.5, 7.5, p), Math.cos(a) * 5 - .5, 0, 0.5, -0.2, 45);
    const left = 4 - Math.floor(clamp((p - .1) / .17 + .5, 0, 4));
    $('chips').innerHTML = `<div class="chip ${left ? 'coin' : 'ok'}"><i>${left || '✓'}</i>${left ? 'Boʻsh joy: ' + left : 'Mashina toʻldi!'}</div>`;
  } },
  // ---- seg 5: bonus
  { seg: 5, a: 0, b: .5, head: '<span class="y">BONUS</span> — pul ishlang!', counter: [10000, 'Yoʻlovchi uzatish'], show: ['coins'], run(lt, p, t) {
    gift.visible = false;
    coins.forEach((c, i) => { const u = c.userData; const tt = Math.max(0, lt - u.d * .5); const y = 9 - ((tt * u.sp) % 13); c.visible = true; c.position.set(u.x, y, u.z); c.rotation.set(u.rx + t * 4, u.ry + t * 3, 0); });
    cam(0, 3, 10, 0, 2.6, 0, 45);
  } },
  { seg: 5, a: .5, b: 1, head: '<span class="y">BONUS</span> — pul ishlang!', counter: [5000, 'Doʻst taklif qilish'], show: ['coins'], run(lt, p, t) {
    gift.visible = true; gift.position.set(0, 0, 0); gift.rotation.y = .5 + Math.sin(t) * .1; const open = eo(P(p, .1, .3)); gift.lid.rotation.x = -open * 1.9;
    coins.forEach((c, i) => { const u = c.userData; const tt = Math.max(0, lt - .12 * (lt > 0) - u.d * .15); const on = p > .12 && i < 45; c.visible = on;
      if (on) { c.position.set(u.vx * tt * .55, 1.6 + u.vy * tt - 4.9 * tt * tt * .9, u.vz * tt * .55); c.rotation.set(u.rx + t * 6, u.ry + t * 5, 0); } });
    const a = lerp(-.3, .3, p); cam(Math.sin(a) * 9, 4.2, Math.cos(a) * 9, 0, 2.4, 0, 45);
  } },
  // ---- seg 6: CTA
  { seg: 6, a: 0, b: 1, head: 'Botga kiring —<br><span class="y">boshladik!</span>', cta: true, show: ['cta'], run(lt, p, t) {
    carCta.rotation.y = t * 1.1; carCta.spin(0); platRing.material.emissiveIntensity = 1.2 + Math.sin(t * 6) * .5;
    cam(0, 3.6, 12.5, 0, 3.4, 0, 42);
  } },
];
// absolute times
SHOTS.forEach(s => { const sg = seg(s.seg); s.t0 = lerp(sg.start, sg.end, s.a); s.t1 = lerp(sg.start, sg.end, s.b); });

// ---------------- subtitles ----------------
let lastSub = -1;
function renderSubs(t) {
  const el = $('subs'); const idx = TL.subs.findIndex(s => t >= s.a - .05 && t <= s.b + .25);
  if (idx < 0) { el.style.opacity = 0; return; }
  const s = TL.subs[idx];
  if (idx !== lastSub) { el.innerHTML = '<span class="box">' + s.text.split(' ').map(w => `<span class="w">${w}</span>`).join(' ') + '</span>'; lastSub = idx; }
  const ws = el.querySelectorAll('.w'); const lens = [...ws].map(w => w.textContent.length + 2); const tot = lens.reduce((a, b) => a + b, 0);
  const prog = P(t, s.a, s.b) * tot; let acc = 0; ws.forEach((w, i) => { w.classList.toggle('on', prog > acc); acc += lens[i]; });
  el.style.opacity = clamp(Math.min(P(t, s.a - .05, s.a + .1), 1 - P(t, s.b + .1, s.b + .25)));
}

// ---------------- main render ----------------
let lastShot = -1, lastHead = '';
const fmt = n => n.toLocaleString('ru-RU').replace(/ /g, ' ');
window.render = function (t) {
  let i = SHOTS.findIndex(s => t >= s.t0 && t < s.t1); if (i < 0) i = SHOTS.length - 1;
  const s = SHOTS[i], lt = t - s.t0, p = clamp(lt / (s.t1 - s.t0));
  Object.values(groups).forEach(g => g.visible = s.show.includes(g.name));
  tube.visible = true; pinF.visible = pinT.visible = carMap.visible = true;
  ground.visible = grid.visible = !(s.show.includes('map') || s.show.includes('phone') || s.show.includes('card'));
  Object.values(LBL).forEach(e => e.style.opacity = 0);
  if (i !== lastShot) $('chips').innerHTML = (s.chips || []).map(([c, ic, tx]) => `<div class="chip ${c}"><i>${ic}</i>${tx}</div>`).join('');
  s.run(lt, p, t);

  // headline pop on change
  const hd = $('headline');
  if (s.head !== lastHead) { hd.innerHTML = s.head || ''; lastHead = s.head; }
  const segStart = SHOTS.find(x => x.head === s.head).t0; const hp = back(P(t, segStart, segStart + .35));
  hd.style.opacity = P(t, segStart, segStart + .12); hd.style.transform = `scale(${.6 + .4 * hp}) rotateX(${(1 - hp) * 30}deg)`;
  // chips
  [...$('chips').children].forEach((c, k) => { const q = back(P(lt, .1 + k * .2, .4 + k * .2)); c.style.opacity = P(lt, .1 + k * .2, .2 + k * .2); c.style.transform = `translateY(${(1 - q) * 40}px) scale(${.7 + .3 * q})`; });
  if (s.seg === 4 && s.a > 0) [...$('chips').children].forEach(c => { c.style.opacity = 1; c.style.transform = 'none'; });
  // counter
  const ct = $('counter');
  if (s.counter) { const v = Math.round(s.counter[0] * eo(P(lt, .1, .9)) / 100) * 100; ct.querySelector('.v').textContent = '+' + fmt(v) + ' soʻm'; ct.querySelector('.l').textContent = s.counter[1];
    const q = back(P(lt, 0, .3)); ct.style.opacity = P(lt, 0, .1); ct.style.transform = `scale(${.6 + .4 * q})`; } else ct.style.opacity = 0;
  // CTA cards
  const cta = $('cta');
  if (s.cta) { cta.style.opacity = 1;
    [['cardBot', .15], ['cardGrp', .45]].forEach(([id, d]) => { const q = eo(P(lt, d, d + .5)); $(id).style.transform = `rotateY(${(1 - q) * 80}deg) translateX(${(1 - q) * 300}px)`; $(id).style.opacity = P(lt, d, d + .15); });
    const bq = back(P(lt, .8, 1.15)); const pulse = lt > 1.15 ? 1 + Math.sin((lt - 1.15) * 8) * .05 : 1; $('startbtn').style.transform = `scale(${bq * pulse})`; $('startbtn').style.opacity = P(lt, .8, .9);
  } else cta.style.opacity = 0;
  // flash + punch-in on cuts
  const sinceCut = t - s.t0; $('flash').style.opacity = i > 0 ? Math.max(0, .45 - sinceCut * 4) : 0;
  if (sinceCut < .2) { camera.fov *= 1 + (.2 - sinceCut) * .4; camera.updateProjectionMatrix(); }
  $('brand').style.opacity = P(t, 0, .4);
  renderSubs(t);
  renderer.render(scene, camera);
  lastShot = i;
};
window.READY = true;
