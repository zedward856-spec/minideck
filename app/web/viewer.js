// Minideck app viewer: the deck on its own. Drag to orbit, pinch to zoom, two fingers to pan.
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { toCreasedNormals } from "three/addons/utils/BufferGeometryUtils.js";

// "Cyber yellow" palette + fixed electronics colours (same as the site's main.js)
const PAL = { body: "#2d2d2d", kbplate: "#3d3d3d", accent: "#f7d116", accent2: "#f7d116", keys: "#161616",
  fill: "#f7d116", fill_dark: "#2d2d2d" };
const FIXED = {
  pcb_green: ["#1f7a45", 0.5, 0.1], pcb_red: ["#a3232a", 0.5, 0.1], pcb_purple: ["#4b2a8a", 0.5, 0.1],
  pcb_blue: ["#1e4fc0", 0.5, 0.1], metal: ["#c9cacc", 0.32, 0.9], brass: ["#c8a03c", 0.35, 0.9],
  cell: ["#2f5fd0", 0.35, 0.2], flex: ["#d39a1c", 0.45, 0.1], dark: ["#1d1d1f", 0.45, 0.2],
  glass: ["#04060a", 0.08, 0.3], ceramic: ["#e6e6dc", 0.7, 0.0], sdcard: ["#0d0d0f", 0.28, 0.25],
};
const LID_DEG = 110;

const canvas = document.getElementById("stage");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance" });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
renderer.toneMapping = THREE.NeutralToneMapping;   // keeps the paint yellow true (ACES washed it toward cream)
renderer.toneMappingExposure = 1.0;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.setClearColor(0x0a0a0c, 1);

const scene = new THREE.Scene();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
scene.environmentIntensity = 0.55;

const camera = new THREE.PerspectiveCamera(32, innerWidth / innerHeight, 1, 3000);
const key = new THREE.DirectionalLight(0xffffff, 2.4); key.position.set(-120, 220, 160); scene.add(key);
// neutral rims (the site's yellow/cyan rims tinted the case)
const rimL = new THREE.PointLight(0xfff6e8, 5000, 600, 1.6); rimL.position.set(-160, 60, -140); scene.add(rimL);
const rimR = new THREE.PointLight(0xe8f0ff, 4000, 600, 1.6); rimR.position.set(170, 40, -120); scene.add(rimR);
scene.add(new THREE.HemisphereLight(0xbfc6d0, 0x0a0a0c, 0.6));

const controls = new OrbitControls(camera, canvas);
Object.assign(controls, { enableDamping: true, dampingFactor: 0.08, rotateSpeed: 0.8, zoomSpeed: 1.1, panSpeed: 0.8,
  screenSpacePanning: true });
controls.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN };

// case mm frame (Z up) -> three (Y up)
const caseFrame = new THREE.Group(); caseFrame.rotation.x = -Math.PI / 2; scene.add(caseFrame);

const mats = {};
function mat(role) {
  if (mats[role]) return mats[role];
  let m;
  if (FIXED[role]) {
    const [c, r, mt] = FIXED[role];
    m = new THREE.MeshStandardMaterial({ color: c, roughness: r, metalness: mt });
  } else m = new THREE.MeshStandardMaterial({ color: PAL[role] || PAL.body, roughness: role === "keys" ? 0.85 : 0.62, metalness: 0 });
  if (role === "fill" || role === "fill_dark") Object.assign(m, { polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 });
  return (mats[role] = m);
}

// lid: rotates about the hinge axis (the "lid" node's pivot sits on it)
let lidNode = null;
const lidIn = document.getElementById("lid"), lidOut = document.getElementById("lidDeg");
function setLid(deg) {
  if (lidNode) lidNode.rotation.x = -THREE.MathUtils.degToRad(deg);
  lidIn.value = deg; lidOut.textContent = deg + "°";
  lidIn.style.setProperty("--p", (deg / 180) * 100 + "%");
}
lidIn.addEventListener("input", () => setLid(+lidIn.value));

let screenVideo = null;
// coming back from the background / screen off: kick the screen animation again
document.addEventListener("visibilitychange", () => {
  if (!document.hidden && screenVideo) screenVideo.play().catch(() => {});
});
addEventListener("pointerdown", () => { if (screenVideo && screenVideo.paused) screenVideo.play().catch(() => {}); });

let home = null;     // the framed view "reset" returns to
function frameDeck(root) {
  scene.updateMatrixWorld(true);                   // caseFrame rotation must be in the world matrices
  const sphere = new THREE.Box3().setFromObject(root).getBoundingSphere(new THREE.Sphere());
  const vf = THREE.MathUtils.degToRad(camera.fov) / 2, hf = Math.atan(Math.tan(vf) * camera.aspect);
  const dist = (sphere.radius / Math.sin(Math.min(vf, hf))) * 0.9;
  const dir = new THREE.Vector3(-0.55, 0.5, 1).normalize();
  home = { target: sphere.center.clone(), pos: sphere.center.clone().addScaledVector(dir, dist) };
  controls.minDistance = sphere.radius * 0.15;
  controls.maxDistance = dist * 4;
}
function resetView() {
  controls.target.copy(home.target); camera.position.copy(home.pos); controls.update();
}

async function load() {
  const meta = await (await fetch("assets/parts.json")).json();
  const gltf = await new GLTFLoader().setMeshoptDecoder(MeshoptDecoder).loadAsync("assets/minideck.glb", (e) => {
    if (e.total) document.getElementById("loadpct").textContent = Math.round((e.loaded / e.total) * 100) + "%";
  });
  const root = gltf.scene;
  caseFrame.add(root);
  lidNode = root.getObjectByName("lid");
  setLid(LID_DEG);
  root.updateMatrixWorld(true);

  root.traverse((o) => {
    if (!o.isMesh) return;
    let n = o.name, m = meta[n];
    for (let p = o; !m && p; p = p.parent) { n = p.name; m = meta[n]; }
    if (m && m.role === "native") {                // real-colour component models
      const c = new THREE.Color((m.colours && m.colours[o.name]) || "#808080");
      const grey = Math.abs(c.r - c.g) < 0.04 && Math.abs(c.g - c.b) < 0.06 && c.r > 0.55;
      const gold = c.r > 0.7 && c.g > 0.45 && c.b < 0.45 && c.r - c.b > 0.3;
      o.material = new THREE.MeshStandardMaterial({ color: c, roughness: grey || gold ? 0.32 : 0.55, metalness: grey || gold ? 0.75 : 0.08 });
    } else o.material = mat(m ? m.role : "body");
    if (!meta._baked_normals) o.geometry = toCreasedNormals(o.geometry, THREE.MathUtils.degToRad(35));
  });

  // paint fills, inserts and keycaps ride inside their host, so hiding the host hides them too
  for (const n of Object.keys(meta)) {
    const h = meta[n].host && root.getObjectByName(meta[n].host), obj = root.getObjectByName(n);
    if (h && obj) h.attach(obj);
  }
  // keycap legends
  const L = meta.legends, kb = root.getObjectByName("keyboard");
  if (L && kb) {
    const tex = await new THREE.TextureLoader().loadAsync("assets/legends.png");
    tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
    const [x0, y0, x1, y1] = L.rect;
    const pl = new THREE.Mesh(new THREE.PlaneGeometry(x1 - x0, y1 - y0),
      new THREE.MeshStandardMaterial({ map: tex, alphaTest: 0.5, roughness: 0.85,
        polygonOffset: true, polygonOffsetFactor: -4, polygonOffsetUnits: -4 }));
    pl.position.set((x0 + x1) / 2, (y0 + y1) / 2, L.z + 0.12);
    kb.parent.add(pl); kb.attach(pl);
    var legendPlane = pl;
  }
  // the Optic animation on the screen
  const S = meta._screen, sp = root.getObjectByName("screen_panel");
  // held in memory as a blob: a streamed asset can't be resumed after Android suspends the WebView's media
  const clip = await (await fetch("assets/screen.mp4")).blob();
  const video = Object.assign(document.createElement("video"), { src: URL.createObjectURL(clip), muted: true, loop: true, playsInline: true, autoplay: true });
  video.play().catch(() => {});
  screenVideo = video;
  const vt = new THREE.VideoTexture(video); vt.colorSpace = THREE.SRGBColorSpace;
  const scr = new THREE.Mesh(new THREE.PlaneGeometry(S.w, S.h), new THREE.MeshBasicMaterial({ map: vt, toneMapped: false }));
  scr.rotation.x = Math.PI;
  scr.position.set(S.cx, S.cy, S.z - 0.05);
  lidNode.add(scr);
  if (sp) sp.attach(scr);

  // parts-panel.js hides byName[n].pivot
  const byName = {};
  for (const n of Object.keys(meta)) { const o = !n.startsWith("_") && root.getObjectByName(n); if (o) byName[n] = { pivot: o }; }
  window.__deck = { meta, byName, root, legendPlane };
  dispatchEvent(new Event("deck-ready"));

  frameDeck(root); resetView();
}

document.getElementById("resetBtn").onclick = () => home && resetView();

function frame() {
  requestAnimationFrame(frame);
  controls.update();
  // keep depth precision as you zoom right in
  const d = camera.position.distanceTo(controls.target);
  camera.near = Math.max(0.5, d * 0.05); camera.far = d * 10 + 500; camera.updateProjectionMatrix();
  renderer.render(scene, camera);
}
addEventListener("resize", () => {
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight);
});

// the Optic loading animation (a video, so it keeps playing while the model is parsed) always
// finishes its 4 s loop, lids pulled apart, before the deck shows
const optic = document.getElementById("optic");
let loaded = false;
const untilLoopEnd = () => new Promise((r) => {
  loaded = true;
  if (optic.ended || optic.error) return r();
  optic.addEventListener("ended", r, { once: true });
  setTimeout(r, 4500);                             // never hang on the loader if the video stalls
});
optic.addEventListener("ended", () => { if (!loaded) optic.play(); });
optic.play().catch(() => {});
load().then(untilLoopEnd).then(() => {
  document.body.classList.remove("loading"); requestAnimationFrame(frame);
  setTimeout(() => { optic.pause(); optic.removeAttribute("src"); optic.load(); }, 800);   // free its decoder once faded
})
  .catch((e) => { console.error(e); document.getElementById("loadpct").textContent = "load error"; });
