import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { toCreasedNormals } from "three/addons/utils/BufferGeometryUtils.js";

// ------------------------------------------------------------------ data
const PALETTES = [
  { name: "Cyber yellow", body: "#2d2d2d", kbplate: "#3d3d3d", accent: "#f7d116", accent2: "#f7d116", keys: "#161616", glow: 0.0 },
  { name: "Neon night", body: "#0d0d12", kbplate: "#22232c", accent: "#ff2a6d", accent2: "#05d9e8", keys: "#161618", glow: 0.6 },
  { name: "Arasaka", body: "#111214", kbplate: "#3b3d42", accent: "#e0102a", accent2: "#e0102a", keys: "#161618", glow: 0.2 },
  { name: "Snow", body: "#e7e6e1", kbplate: "#f6f6f3", accent: "#ff5a10", accent2: "#ff5a10", keys: "#f2f2f0", glow: 0.0 },
  { name: "Retro beige", body: "#d6c9a8", kbplate: "#bfb08c", accent: "#7a1f2b", accent2: "#7a1f2b", keys: "#8e9093", glow: 0.0 },
  { name: "Field olive", body: "#4b5320", kbplate: "#b8a77c", accent: "#1a1a1a", accent2: "#1a1a1a", keys: "#161618", glow: 0.0 },
];
const FIXED = {          // electronics: colour, roughness, metalness
  pcb_green: ["#1f7a45", 0.5, 0.1], pcb_red: ["#a3232a", 0.5, 0.1], pcb_purple: ["#4b2a8a", 0.5, 0.1],
  pcb_blue: ["#1e4fc0", 0.5, 0.1], metal: ["#c9cacc", 0.32, 0.9], brass: ["#c8a03c", 0.35, 0.9],
  cell: ["#2f5fd0", 0.35, 0.2], flex: ["#d39a1c", 0.45, 0.1], dark: ["#1d1d1f", 0.45, 0.2],
  glass: ["#04060a", 0.08, 0.3], ceramic: ["#e6e6dc", 0.7, 0.0],
};
const TAGGED = ["radxa", "18650", "lora", "pn532", "dac", "keyboard", "driver_board", "battery_door", "hinge_axle",
  "gps_module", "sdr_dongle", "mt3608", "tp4056", "screen_panel", "torque_hinge"];
const BOM = {
  printed: [["Case bottom", "body"], ["Keyboard plate", "kbplate"], ["Lid shell", "body"], ["Screen bezel", "kbplate"],
    ["Hinge-box hatch", "body"], ["Battery door", "accent"], ["C-clip lock", "accent2"], ["Torque hinge cap", "accent2"],
    ["Hollow hinge axle", "accent2"]],
  elec: [["Radxa ZERO 3W", "computer"], ["EP28060S 2.8″ IPS", "display"], ["EHD-40P-V3", "HDMI driver"],
    ["M5Stack CardKB", "keyboard · I²C"], ["PN532", "NFC · I²C"], ["PCM5102", "I²S DAC"], ["Ebyte E22-900T22S", "LoRa · UART"],
    ["ATGM336H + patch", "GPS · UART"], ["NESDR Nano 2+", "SDR · USB pins"], ["3 × Molex FPC", "antennas"],
    ["TP4056 USB-C", "charger"], ["MT3608", "5.1 V boost"], ["18650", "battery"]],
  hw: [["M2 × 4 screws", "12"], ["M2 heat-set inserts", "12"], ["Friction torque hinge", "1"], ["Silicone keycaps", "1 set"],
    ["Silicone wire + u.FL", "—"]],
};

// ------------------------------------------------------------------ helpers
const $ = (s) => document.querySelector(s);
const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const lerp = (a, b, t) => a + (b - a) * t;
const damp = (a, b, k, dt) => lerp(a, b, 1 - Math.exp(-k * dt));
const mobile = () => innerWidth < 860;

// email, assembled at runtime so scrapers don't get it for free
const MAIL = ["zedward856", "gmail.com"].join("@");
for (const id of ["mail", "mail2"]) {
  const a = document.getElementById(id);
  a.href = "mailto:" + MAIL + "?subject=" + encodeURIComponent("Minideck");
  if (id === "mail") a.textContent = MAIL;
}

// ------------------------------------------------------------------ loader boot log
document.body.classList.add("loading");
const BOOT = ["mounting /dev/minideck", "radxa zero 3w: rk3566 online", "i2c5: cardkb@0x5f pn532@0x24", "uart4: e22 lora 868 MHz",
  "uart3: gps fix pending…", "usb2 host2: rtl2832u found", "i2s3: pcm5102 ready", "hdmi: 2.8\" panel ok", "loading chassis mesh"];
let bootI = 0;
const bootTimer = setInterval(() => {
  if (bootI >= BOOT.length) return;
  const d = document.createElement("div"); d.textContent = BOOT[bootI++]; $("#bootlog").appendChild(d);
}, 170);

// ------------------------------------------------------------------ renderer / scene
const canvas = $("#stage");
const SHOTMODE = new URLSearchParams(location.search).has("y");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance", preserveDrawingBuffer: SHOTMODE });
renderer.setPixelRatio(Math.min(devicePixelRatio, mobile() ? 1.5 : 2));
renderer.setSize(innerWidth, innerHeight);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.setClearColor(new THREE.Color("#0a0a0c"), 1);

const scene = new THREE.Scene();
scene.fog = new THREE.Fog(0x0a0a0c, 380, 900);
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.55;

const camera = new THREE.PerspectiveCamera(32, innerWidth / innerHeight, 1, 2000);
camera.position.set(0, 80, 430);

const key = new THREE.DirectionalLight(0xffffff, 2.4); key.position.set(-120, 220, 160); scene.add(key);
const rimY = new THREE.PointLight(0xf7d116, 9000, 600, 1.6); rimY.position.set(-160, 60, -140); scene.add(rimY);
const rimC = new THREE.PointLight(0x05d9e8, 6000, 600, 1.6); rimC.position.set(170, 40, -120); scene.add(rimC);
scene.add(new THREE.HemisphereLight(0xbfc6d0, 0x0a0a0c, 0.6));

// tron floor
const floorMat = new THREE.ShaderMaterial({
  transparent: true, depthWrite: false,
  uniforms: { uTime: { value: 0 }, uCol: { value: new THREE.Color("#f7d116") }, uScroll: { value: 0 } },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.); }`,
  fragmentShader: `varying vec2 vUv; uniform float uTime; uniform vec3 uCol; uniform float uScroll;
    void main(){
      vec2 p = (vUv - .5) * 60.; p.y += uTime*.6 + uScroll*8.;
      vec2 g = abs(fract(p) - .5) / fwidth(p);
      float line = 1. - min(min(g.x, g.y), 1.);
      float r = length(vUv - .5) * 2.;
      float fade = smoothstep(1., .05, r);
      float pulse = .5 + .5*sin(r*18. - uTime*2.);
      gl_FragColor = vec4(uCol, line * fade * (.22 + .18*pulse));
    }`,
});
const floor = new THREE.Mesh(new THREE.PlaneGeometry(1400, 1400), floorMat);
floor.rotation.x = -Math.PI / 2; floor.position.y = -110; scene.add(floor);
const glow = new THREE.Mesh(new THREE.CircleGeometry(160, 64), new THREE.MeshBasicMaterial({
  color: 0xf7d116, transparent: true, opacity: 0.06, depthWrite: false }));
glow.rotation.x = -Math.PI / 2; glow.position.y = -109; scene.add(glow);

// dust
const dustGeo = new THREE.BufferGeometry();
const N = mobile() ? 300 : 700, dp = new Float32Array(N * 3);
for (let i = 0; i < N; i++) { dp[i * 3] = (Math.random() - .5) * 900; dp[i * 3 + 1] = (Math.random() - .3) * 500; dp[i * 3 + 2] = (Math.random() - .5) * 700; }
dustGeo.setAttribute("position", new THREE.BufferAttribute(dp, 3));
const dust = new THREE.Points(dustGeo, new THREE.PointsMaterial({ color: 0xf7d116, size: 1.6, transparent: true, opacity: .5, depthWrite: false }));
scene.add(dust);

// ------------------------------------------------------------------ deck
const deck = new THREE.Group(); scene.add(deck);            // spins / moves
const caseFrame = new THREE.Group(); deck.add(caseFrame);   // case mm frame (Z up) -> three (Y up)
caseFrame.rotation.x = -Math.PI / 2;

const mats = {};
function mat(role) {
  if (mats[role]) return mats[role];
  let m;
  if (FIXED[role]) {
    const [c, r, mt] = FIXED[role];
    m = new THREE.MeshStandardMaterial({ color: c, roughness: r, metalness: mt });
  } else {
    m = new THREE.MeshStandardMaterial({ color: "#2d2d2d", roughness: role === "keys" ? 0.85 : 0.62, metalness: 0.0 });
    if (role.startsWith("accent") || role === "fill") m.emissive = new THREE.Color(0);
  }
  m.userData.role = role;
  return (mats[role] = m);
}
// palette roles: target colours, eased every frame
const palTarget = {}, palEmissive = { v: 0 };
function setPalette(i) {
  const P = PALETTES[i];
  Object.assign(palTarget, {
    body: P.body, kbplate: P.kbplate, accent: P.accent, accent2: P.accent2, keys: P.keys, fill: P.accent, fill_dark: P.body,
  });
  palEmissive.v = P.glow;
  document.querySelectorAll(".sw").forEach((b, k) => b.classList.toggle("on", k === i));
  $("#palName").textContent = `${i + 1} — ${P.name}`;
  document.querySelectorAll("[data-role-dot]").forEach((d) => (d.style.background = palTarget[d.dataset.roleDot]));
  palIndex = i;
}
let palIndex = 0, palAuto = true;

const parts = [];       // {name, pivot, centre, off, axis, ang, delay, lid}
let lidNode = null, lidBase = null, screenVideo = null, meta = null;
const tmpC = new THREE.Color();

function pivotize(obj, parent) {
  const box = new THREE.Box3().setFromObject(obj);
  // centre in the parent's frame
  parent.updateMatrixWorld(true);
  const c = box.getCenter(new THREE.Vector3());
  parent.worldToLocal(c);
  const pivot = new THREE.Group();
  pivot.position.copy(c);
  parent.add(pivot);
  obj.position.sub(c);
  pivot.add(obj);
  return { pivot, centre: c.clone() };
}

function rnd(seed) { let s = seed; return () => ((s = Math.sin(s * 9301 + 49297) * 233280) - Math.floor(s)); }

async function loadDeck() {
  meta = await (await fetch("assets/parts.json")).json();
  const gltf = await new GLTFLoader().loadAsync("assets/minideck.glb", (e) => {
    if (e.total) { const p = Math.round((e.loaded / e.total) * 100); $("#loadbar").style.width = p + "%"; $("#loadpct").textContent = p + "%"; }
  });
  const root = gltf.scene;
  caseFrame.add(root);
  // centre the deck (case frame point -> origin)
  const C = new THREE.Vector3(47, 42, 18);
  caseFrame.position.set(-C.x, -C.z, C.y);
  lidNode = root.getObjectByName("lid");
  lidBase = lidNode.position.clone();
  root.updateMatrixWorld(true);

  // materials
  root.traverse((o) => {
    if (!o.isMesh) return;
    let n = o.name, m = meta[n];
    for (let p = o; !m && p; p = p.parent) { n = p.name; m = meta[n]; }
    o.material = mat(m ? m.role : "body");
    o.geometry = toCreasedNormals(o.geometry, THREE.MathUtils.degToRad(35));
    o.castShadow = o.receiveShadow = false;
  });

  // pivots for every movable part
  const R = rnd(7);
  const byName = {};
  const names = Object.keys(meta).filter((n) => !n.startsWith("_") && meta[n].explode && n !== "legends");
  for (const n of names) {
    const obj = root.getObjectByName(n);
    if (!obj) continue;
    const { pivot, centre } = pivotize(obj, obj.parent);
    const pl = meta[n].plan;                       // collision-free teardown from plan_explode.py
    const e = { name: n, pivot, centre, lid: meta[n].lid, plan: pl, phase: R() * 20,
      dir: pl ? new THREE.Vector3(...pl.dir) : null,
      axis: pl ? new THREE.Vector3(...pl.tumble.axis).normalize() : new THREE.Vector3(0, 0, 1) };
    parts.push(e); byName[n] = e;
  }
  // fills ride inside their host
  for (const n of Object.keys(meta)) {
    if (!meta[n].host) continue;
    const obj = root.getObjectByName(n), host = byName[meta[n].host];
    if (!obj || !host) continue;
    obj.position.sub(host.centre); host.pivot.add(obj);
    obj.userData.stripes = meta[n].stripes;
  }
  // keycap legends: one textured plane over the keyboard
  const L = meta.legends, kc = byName["keycaps"] || byName[meta.keycaps.host];
  if (L && kc) {
    const tex = await new THREE.TextureLoader().loadAsync("assets/legends.png");
    tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
    const [x0, y0, x1, y1] = L.rect;
    const pl = new THREE.Mesh(new THREE.PlaneGeometry(x1 - x0, y1 - y0),
      new THREE.MeshStandardMaterial({ map: tex, transparent: true, alphaTest: 0.05, roughness: 0.85 }));
    pl.position.set((x0 + x1) / 2, (y0 + y1) / 2, L.z + 0.03).sub(kc.centre);
    kc.pivot.add(pl);
    legendPlane = pl;
  }
  // screen: your Optic loading animation on the panel
  const S = meta._screen, sp = byName["screen_panel"];
  screenVideo = document.createElement("video");
  Object.assign(screenVideo, { src: "assets/screen.mp4", muted: true, loop: true, playsInline: true, autoplay: true });
  screenVideo.setAttribute("playsinline", ""); screenVideo.play().catch(() => {});
  const vt = new THREE.VideoTexture(screenVideo); vt.colorSpace = THREE.SRGBColorSpace;
  const scr = new THREE.Mesh(new THREE.PlaneGeometry(S.w, S.h), new THREE.MeshBasicMaterial({ map: vt, toneMapped: false }));
  scr.rotation.x = Math.PI;                         // faces the keyboard when closed; image top = lid front edge
  scr.position.set(S.cx, S.cy, S.z - 0.05);
  if (sp) { scr.position.sub(sp.centre); sp.pivot.add(scr); } else lidNode.add(scr);

  // part tags
  for (const n of TAGGED) if (byName[n]) {
    const t = document.createElement("div"); t.className = "tag"; t.textContent = meta[n].label;
    $("#labels").appendChild(t); byName[n].tag = t;
  }
  setPalette(0);
  for (const r of Object.keys(palTarget)) if (mats[r]) mats[r].color.set(palTarget[r]);
}
let legendPlane = null;

// ------------------------------------------------------------------ UI: swatches + BOM
PALETTES.forEach((P, i) => {
  const b = document.createElement("button"); b.className = "sw";
  b.innerHTML = `<div class="chips"><i style="background:${P.body}"></i><i style="background:${P.kbplate}"></i><i style="background:${P.accent}"></i><i style="background:${P.accent2}"></i></div>${P.name}`;
  b.onclick = () => { palAuto = false; setPalette(i); burst(0.35); };
  $("#swatches").appendChild(b);
});
const row = (a, b, dot) => `<tr><td>${dot ? `<i class="dot" data-role-dot="${dot}"></i>` : ""}${a}</td><td>${b}</td></tr>`;
$("#bom-printed").innerHTML = BOM.printed.map(([n, r]) => row(n, r.replace("kbplate", "plate").replace("accent2", "accent"), r)).join("");
$("#bom-elec").innerHTML = BOM.elec.map(([n, r]) => row(n, r)).join("");
$("#bom-hw").innerHTML = BOM.hw.map(([n, q]) => row(n, q)).join("");

// reveal + counters
const io = new IntersectionObserver((es) => es.forEach((e) => {
  if (!e.isIntersecting) return;
  e.target.classList.add("in");
  e.target.querySelectorAll?.(".num").forEach(countUp);
  if (e.target.classList.contains("num")) countUp(e.target);
}), { threshold: 0.2 });
document.querySelectorAll(".reveal").forEach((el) => io.observe(el));
function countUp(el) {
  if (el.dataset.done) return; el.dataset.done = 1;
  const to = +el.dataset.to, dec = +el.dataset.dec, t0 = performance.now();
  const f = (t) => { const k = ease(clamp((t - t0) / 1400)); el.textContent = (to * k).toFixed(dec); if (k < 1) requestAnimationFrame(f); };
  requestAnimationFrame(f);
}

// ------------------------------------------------------------------ interaction: drag to spin, tap to blow it apart
let dragV = 0, dragSpin = 0, dragging = false, lastX = 0, downX = 0, downT = 0;
let pointer = { x: 0, y: 0 };
addEventListener("pointermove", (e) => {
  pointer.x = e.clientX / innerWidth - .5; pointer.y = e.clientY / innerHeight - .5;
  if (dragging) { const dx = e.clientX - lastX; lastX = e.clientX; dragV = dx * 0.01; dragSpin += dragV; }
});
canvas.addEventListener("pointerdown", (e) => { dragging = true; lastX = downX = e.clientX; downT = performance.now(); });
addEventListener("pointerup", (e) => {
  if (dragging && Math.abs(e.clientX - downX) < 6 && performance.now() - downT < 300) burst(1);
  dragging = false;
});
let burstT = -10, burstAmp = 1;
function burst(a) { if (performance.now() / 1000 - burstT > 3.2) { burstT = performance.now() / 1000; burstAmp = a; } }

// ------------------------------------------------------------------ scroll -> scene targets
const sections = [...document.querySelectorAll("[data-scene]")];
function sceneTargets(t) {
  const vh = innerHeight, m = mobile();
  let active = sections[0], p = 0;
  for (const s of sections) {
    const r = s.getBoundingClientRect();
    if (r.top <= vh * 0.5 && r.bottom > vh * 0.5) { active = s; p = clamp(-r.top / Math.max(1, r.height - vh)); break; }
  }
  const T = { explode: 0, lid: 110, spin: Math.sin(t * 0.25) * 0.8, tilt: 0.32, x: m ? 0 : 55, y: m ? 28 : 8, z: 0, scale: 1, tags: 0, floor: 0 };
  switch (active.dataset.scene) {
    case "hero":
      T.x = m ? 0 : 115; T.y = m ? 34 : 30; T.spin = -0.6 + Math.sin(t * 0.25) * 0.9; break;
    case "apart": {
      const e = p < 0.38 ? ease(p / 0.38) : p < 0.66 ? 1 : 1 - ease((p - 0.66) / 0.34);
      T.explode = e; T.spin = -0.5 + p * Math.PI * 0.9; T.tilt = 0.32 + Math.sin(p * Math.PI) * 0.25;
      T.x = m ? 0 : 70; T.scale = 1 - e * 0.18; T.tags = e > 0.95 ? 1 : 0;
      $("#apartPct").textContent = Math.round((1 - e) * 100) + "%";
      break;
    }
    case "hinge": {
      const d = ease(clamp(p / 0.85)) * 180;
      T.lid = d; T.spin = -Math.PI / 2 + 0.35 + Math.sin(p * Math.PI) * 0.5; T.tilt = 0.12; T.x = m ? 0 : -60; T.scale = 1.15;
      $("#lidDeg").textContent = Math.round(d) + "°";
      break;
    }
    case "specs":
      T.explode = 0.3; T.spin = 0.6 + Math.sin(t * 0.3) * 0.5; T.z = -200; T.y = m ? 120 : 96; T.x = m ? 0 : 175; T.scale = 0.9; break;
    case "palettes":
      T.spin = 0.5 + Math.sin(t * 0.4) * 0.6; T.x = m ? 0 : 60; T.scale = 1.1; break;
    case "parts":
      T.explode = 0.75; T.spin = 0.4 + Math.sin(t * 0.25) * 0.5; T.z = -220; T.x = 0; T.y = 50; break;
    case "contact":
      T.lid = 0; T.spin = t * 0.35; T.tilt = 0.45; T.x = 0; T.y = m ? 95 : 84; T.scale = 0.72; break;
  }
  if (m) T.scale *= 0.62;                          // phones: smaller deck, text gets the bottom half
  T.scene = active.dataset.scene;
  return T;
}

// ------------------------------------------------------------------ animate
const S = { explode: 1, lid: 0, spin: -1.2, tilt: 0.32, x: 115, y: 30, z: 0, scale: 1 };   // starts blown apart: flies together
let t0 = null, last = performance.now(), introDone = false, palTimer = 0;
const q = new THREE.Quaternion(), qI = new THREE.Quaternion(), v = new THREE.Vector3();

function frame(now) {
  requestAnimationFrame(frame);
  const dt = Math.min(0.05, (now - last) / 1000); last = now;
  const t = now / 1000;
  if (!meta || !lidNode) { renderer.render(scene, camera); return; }
  if (t0 === null) t0 = t;
  const it = t - t0;                              // intro clock
  const T = sceneTargets(t);

  // intro: parts fly in and lock together, then the lid swings open
  let introE = 0, introLid = null;
  if (it < 4.0) {
    introE = 1 - clamp(it / 2.6);                // the teardown played backwards: it builds itself
    introLid = 110 * ease(clamp((it - 2.6) / 1.4));
    if (T.scene !== "hero") introE = 0, introLid = null;
  }
  // tap burst: quick blow-apart and snap back
  const bt = t - burstT;
  const burstE = bt < 3.2 ? Math.sin(clamp(bt / 3.2) * Math.PI) * burstAmp : 0;

  const k = 4.5;
  const targetE = clamp(Math.max(T.explode, introE, burstE));
  S.explode = it < 2.6 ? targetE : damp(S.explode, targetE, burstE > 0 ? 10 : k, dt);
  S.lid = introLid !== null ? introLid : damp(S.lid, T.lid, 3.2, dt);
  dragSpin *= Math.exp(-dt * 0.6); dragV *= 0.92;
  // turn the short way round to the next section's angle (no unwinding whole turns)
  const dA = Math.atan2(Math.sin(T.spin - S.spin), Math.cos(T.spin - S.spin));
  S.spin += dA * (1 - Math.exp(-(it < 3 ? 1.8 : 2.4) * dt));
  for (const f of ["tilt", "x", "y", "z", "scale"]) S[f] = damp(S[f], T[f], 3, dt);

  deck.position.set(S.x, S.y, S.z);
  deck.rotation.set(S.tilt, S.spin + dragSpin, 0, "XYZ");
  deck.scale.setScalar(S.scale);

  // lid
  lidNode.rotation.x = -THREE.MathUtils.degToRad(S.lid);

  // parts: one at a time, each slides straight out along its free direction (nothing passes
  // through anything); it only starts to turn once it is clear, then eases into its resting spot
  for (const P of parts) {
    if (!P.plan) continue;
    const p = P.plan, u = clamp((S.explode - p.t0) / (p.t1 - p.t0));
    const f = u * u * (3 - 2 * u), d = f * p.dist;
    P.pivot.position.copy(P.centre).addScaledVector(P.dir, d);
    const out = clamp((d - p.clear) / Math.max(1, p.dist - p.clear));
    P.pivot.quaternion.copy(qI).multiply(q.setFromAxisAngle(P.axis, p.tumble.ang * out * out * (3 - 2 * out)));
    if (P.tag) {
      const show = T.tags && !mobile();
      P.tag.style.opacity = show ? 1 : 0;
      if (show) {
        P.pivot.getWorldPosition(v); v.project(camera);
        P.tag.style.transform = `translate(${(v.x * .5 + .5) * innerWidth + 14}px, ${(-v.y * .5 + .5) * innerHeight - 10}px)`;
      }
    }
  }

  // palette: auto-cycles while the colours section is on screen, eases colours
  if (T.scene === "palettes" && palAuto) { palTimer += dt; if (palTimer > 3.2) { palTimer = 0; setPalette((palIndex + 1) % PALETTES.length); burst(0.3); } }
  for (const r of Object.keys(palTarget)) if (mats[r]) {
    mats[r].color.lerp(tmpC.set(palTarget[r]), 1 - Math.exp(-dt * 6));
    if (r.startsWith("accent") || r === "fill") mats[r].emissive.copy(mats[r].color).multiplyScalar(palEmissive.v * 0.35);
  }
  floorMat.uniforms.uCol.value.lerp(tmpC.set(PALETTES[palIndex].accent2 === "#1a1a1a" ? "#b8a77c" : PALETTES[palIndex].accent2), 1 - Math.exp(-dt * 4));
  rimY.color.lerp(tmpC.set(PALETTES[palIndex].accent === "#1a1a1a" ? "#e9e2c8" : PALETTES[palIndex].accent), 1 - Math.exp(-dt * 4));

  floorMat.uniforms.uTime.value = t;
  floorMat.uniforms.uScroll.value = scrollY / innerHeight;
  dust.rotation.y = t * 0.02; dust.position.y = -scrollY * 0.05;
  camera.position.x = damp(camera.position.x, pointer.x * 40, 2, dt);
  camera.position.y = damp(camera.position.y, 80 - pointer.y * 24, 2, dt);
  camera.lookAt(0, 10, 0);

  renderer.render(scene, camera);
}

addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

requestAnimationFrame(frame);
window.__dbg = { deck, camera, parts, scene, renderer };
const minShow = new Promise((r) => setTimeout(r, 1900));
loadDeck().then(() => minShow).then(() => {
  clearInterval(bootTimer);
  $("#loadbar").style.width = "100%"; $("#loadpct").textContent = "100%";
  t0 = null;                                       // restart the intro clock as the curtain opens
  $("#loader").classList.add("done");
  document.body.classList.remove("loading");
  setTimeout(() => document.querySelectorAll(".hero .reveal").forEach((el) => el.classList.add("in")), 500);
  setTimeout(() => $("#loader").remove(), 1600);
  const qy = new URLSearchParams(location.search).get("y");          // ?y=3.5 jumps there (screenshots)
  if (qy) { document.documentElement.style.scrollBehavior = "auto"; scrollTo(0, +qy * innerHeight); }
}).catch((e) => { console.error(e); $("#loadpct").textContent = "load error"; });
