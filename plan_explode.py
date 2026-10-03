"""Collision-free teardown for the promo site's exploded view.

Reads ../minideck-site/assets/minideck.glb + parts.json, voxelises every part (0.5 mm), then:
  1. finds a removal order: each step takes a part that can slide straight out along one of a
     few directions without touching anything still assembled (screws first, keycaps, plate ...)
  2. places every part's resting spot so no two overlap (parts removed later rest nearer)
  3. replays the exact timeline the website plays and checks every frame for overlaps
and writes per-part {dir, clear, dist, t0, t1, tumble} back into parts.json.

    python3 plan_explode.py
"""
import json, os, numpy as np, trimesh
from scipy import ndimage

SITE = os.path.expanduser("~/minideck-site/assets")
PITCH = 0.5
LID_DEG = 110.0                                   # the lid angle the teardown is played at
FIXED = "bottom"                                  # the case stays put; everything leaves it
FOLLOW = {"m2_hardware": "bottom", "lid_inserts": "screen_back", "keycaps": "keyboard"}   # inserts melted in; the silicone sheet rides on the CardKB   # heat-set inserts stay melted in
DIRS = [(0, 0, 1), (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, -1),
        (1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1)]
GAP = 6.0                                         # mm between resting parts
SPAN = 0.80                                       # the teardown uses E 0..SPAN for starts; each part moves for DUR
DUR_K = 1.5                                       # each part's move lasts DUR_K / N of the timeline

meta = json.load(open(f"{SITE}/parts.json"))
H = meta["_hinge"]
scene = trimesh.load(f"{SITE}/minideck.glb")

def lid_matrix(deg):
    """lid frame -> case frame at a given opening (rotation about the hinge axis, X)."""
    a = np.radians(-deg)
    R = trimesh.transformations.rotation_matrix(a, (1, 0, 0), point=(0, H["y"], H["z"]))
    T = np.eye(4); T[:3, 3] = (0, H["y"], H["z"])
    return R @ T

LIDM = lid_matrix(LID_DEG)
LID_DIRS = [tuple(LIDM[:3, :3] @ np.array(d, float)) for d in [(0, 0, 1), (0, 0, -1), (0, 1, 0), (0, -1, 0)]]
bodies = {}
for name, m in meta.items():
    if name.startswith("_") or "explode" not in m or name in FOLLOW:
        continue
    g = scene.geometry.get(name)
    if g is None:
        continue
    tm = g.copy()
    if m["lid"]:
        tm.apply_transform(LIDM)
    bodies[name] = tm

# ---------------------------------------------------------------- voxels
allb = np.array([b.bounds for b in bodies.values()])
ORIGIN = allb[:, 0].min(0) - 2
SHAPE = np.ceil((allb[:, 1].max(0) + 2 - ORIGIN) / PITCH).astype(int)

def voxels(tm):
    v = tm.voxelized(PITCH)
    try:
        v = v.fill()
    except Exception:
        pass
    pts = v.points
    ijk = np.round((pts - ORIGIN) / PITCH).astype(int)
    lo = ijk.min(0); dense = np.zeros(ijk.max(0) - lo + 1, bool); dense[tuple((ijk - lo).T)] = True
    er = ndimage.binary_erosion(dense)             # parts that touch get a 1-voxel gap each
    use = er if er.sum() > 0.15 * dense.sum() else dense
    return np.argwhere(use) + lo

V = {n: voxels(b) for n, b in bodies.items()}
names = list(V)
idx = {n: i for i, n in enumerate(names)}
print(len(names), "bodies voxelised, grid", SHAPE)

M = 4096
def keys(c):
    c = c.astype(np.int64) + M // 2
    return (c[:, 0] * M + c[:, 1]) * M + c[:, 2]

class Grid:
    """sparse occupancy: which body owns each voxel (hashed voxel keys)."""
    def __init__(self):
        self.parts = {}; self._k = None
    def put(self, n, shift=(0, 0, 0)):
        self.parts[n] = keys(V[n] + np.round(np.asarray(shift)).astype(int)); self._k = None
    def clear(self, n, shift=None):
        self.parts.pop(n, None); self._k = None
    def _build(self):
        if self._k is None:
            ks = [k for k in self.parts.values()]
            lab = [np.full(len(k), idx[n], np.int16) for n, k in self.parts.items()]
            k = np.concatenate(ks) if ks else np.zeros(0, np.int64)
            l = np.concatenate(lab) if lab else np.zeros(0, np.int16)
            o = np.argsort(k); self._k, self._l = k[o], l[o]
    def hits(self, n, shift, ignore=()):
        self._build()
        if not len(self._k):
            return np.zeros(0, int)
        q = keys(V[n] + np.round(np.asarray(shift)).astype(int))
        p = np.searchsorted(self._k, q); p[p >= len(self._k)] = 0
        lab = self._l[p[self._k[p] == q]]
        lab = lab[lab != idx[n]]
        for i in ignore:
            lab = lab[lab != i]
        return np.unique(lab)
    def counts(self, n, shift):
        """{other body: overlapping voxels} for body n moved by shift (voxels shared by several bodies
        count for each of them)"""
        self._build()
        if not len(self._k):
            return {}
        q = keys(V[n] + np.round(np.asarray(shift)).astype(int))
        lo = np.searchsorted(self._k, q, "left"); hi = np.searchsorted(self._k, q, "right")
        m = hi > lo
        lo, hi = lo[m], hi[m]
        if not len(lo):
            return {}
        cnt = hi - lo
        pos = np.repeat(lo - np.cumsum(np.r_[0, cnt[:-1]]), cnt) + np.arange(cnt.sum())
        lab = self._l[pos]
        lab = lab[lab != idx[n]]
        u, c = np.unique(lab, return_counts=True)
        return dict(zip(u.tolist(), c.tolist()))

def bbox(ns):
    a = np.vstack([V[n] for n in ns]); return a.min(0), a.max(0)

# ---------------------------------------------------------------- 1. removal order
grid = Grid()
for n in names:
    grid.put(n)
remaining = set(names)
order, plan = [], {}
TOL = 4                                            # voxels of slack
INIT = {n: grid.counts(n, (0, 0, 0)) for n in names}   # modelled interference (pins in holes, keys in the CardKB)
for n, d in INIT.items():
    big = {names[j]: c for j, c in d.items() if c > TOL}
    if big:
        print("  starts overlapping:", n, big)

def blocked(g, n, shift, prev):
    """a move is fine if it only shrinks the overlaps the part started with"""
    c = g.counts(n, shift)
    for j, v in c.items():
        if v > min(prev.get(j, 0), INIT[n].get(j, 0)) + TOL:
            return True, c
    return False, c
while len(remaining) > 1:
    rlo, rhi = bbox(remaining)
    best = None
    for n in sorted(remaining - {FIXED}, key=lambda n: (not (n.startswith("screws") or n == "sdcard"), -V[n][:, 2].max())):
        lo, hi = V[n].min(0), V[n].max(0)
        for d in (DIRS + LID_DIRS if meta[n]["lid"] else DIRS):
            d = np.array(d, float)
            free, k, prev = True, 0, dict(INIT[n])
            while True:
                k += 1
                hit, prev = blocked(grid, n, d * k, prev)
                if hit:
                    free = False; break
                slo, shi = lo + d * k, hi + d * k
                if k > 600:
                    break
                if ((shi < rlo) | (slo > rhi)).any():       # out of the remaining assembly's box
                    break
            if free:
                clear = k * np.linalg.norm(d) * PITCH
                score = clear + (0 if d[2] > 0.3 else 6) - (30 if n.startswith("screws") or n == "sdcard" else 0)   # screws first, short pulls, upwards
                if best is None or score < best[0]:
                    best = (score, n, d, clear)
        if best and best[0] < 12:                            # good enough: take it now
            break
    if best is None:
        # nothing slides out cleanly: the (part, direction) that pushes into the least material
        cands = []
        for n in remaining - {FIXED}:
            lo, hi = V[n].min(0), V[n].max(0)
            for d in (DIRS + LID_DIRS if meta[n]["lid"] else DIRS):
                d = np.array(d, float); worst, k, who = 0, 0, {}
                while True:
                    k += 1
                    c = grid.counts(n, d * k)
                    new = {j: v - INIT[n].get(j, 0) for j, v in c.items() if v > INIT[n].get(j, 0) + TOL}
                    if new:
                        worst = max(worst, sum(new.values())); who.update({names[j]: v for j, v in new.items()})
                    slo, shi = lo + d * k, hi + d * k
                    if ((shi < rlo) | (slo > rhi)).any() or k > 600:
                        break
                cands.append((worst, n, d, k * np.linalg.norm(d) * PITCH, who))
        worst, n, d, clear, who = min(cands, key=lambda c: c[0])
        print(f"  forced: {n} dir {np.round(d, 2)} pushes into {who}")
        best = (0, n, d, clear)
    _, n, d, clear = best
    order.append(n); remaining.discard(n); grid.clear(n)
    plan[n] = dict(dir=(d / np.linalg.norm(d)).tolist(), clear=float(clear))
    print(f"  {len(order):2d} {n:22s} dir {np.round(d, 2).tolist()} clear {clear:5.1f} mm")

# ---------------------------------------------------------------- 2. resting spots (last removed placed first)
TUMBLE = {}
rng = np.random.default_rng(7)
placed = Grid(); placed.put(FIXED)
dil = {}
for n in reversed(order):
    size = np.ptp(V[n], 0).max() * PITCH
    ang = 0.0 if size > 40 else (0.25 if size > 20 else 0.7)
    TUMBLE[n] = dict(axis=(rng.normal(size=3) / 1.0).tolist(), ang=float(ang * rng.choice((-1, 1))))
    d = np.array(plan[n]["dir"]); dist = plan[n]["clear"] + GAP
    margin = int(np.ceil((2.0 + abs(ang) * size * 0.25) / PITCH))
    def busy(shift):
        return sum(placed.counts(n, shift).values()) > TOL
    while busy(d * dist / PITCH) or any(busy(d * dist / PITCH + np.array(o) * margin)
            for o in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))):
        dist += 3.0
    plan[n]["dist"] = float(dist)
    placed.put(n, np.round(d * dist / PITCH).astype(int))

# ---------------------------------------------------------------- 3. timeline (same formulas as main.js) + replay check
N = len(order)
dur = DUR_K / N
def clear_time(n):
    """when part n is out of the assembly (its smoothstep reaches clear/dist)"""
    p = plan[n]; target = min(1.0, p["clear"] / p["dist"])
    u = 0.5 - np.sin(np.arcsin(1 - 2 * target) / 3)           # inverse smoothstep
    return p["t0"] + u * (p["t1"] - p["t0"])
start = 0.0
for i, n in enumerate(order):
    t0 = max(i / max(N - 1, 1) * SPAN, start)
    for j in order[:i]:                    # wait for anything it touches to be clear first
        if INIT[n].get(idx[j], 0) > 0 or INIT[j].get(idx[n], 0) > 0:
            t0 = max(t0, clear_time(j) + 0.002)
    plan[n].update(t0=float(t0), t1=float(t0 + dur), order=i, tumble=TUMBLE[n])
    start = t0
end = max(p["t1"] for p in plan.values())
for n in order:                              # squeeze the whole teardown into E 0..1
    plan[n]["t0"] /= end; plan[n]["t1"] /= end

def offset(n, E):
    p = plan[n]; u = np.clip((E - p["t0"]) / (p["t1"] - p["t0"]), 0, 1)
    f = u * u * (3 - 2 * u)                                 # smoothstep
    return np.array(p["dir"]) * p["dist"] * f

bad = {}
for E in np.linspace(0, 1, 161):
    g = Grid()
    sh = {n: np.round(offset(n, E) / PITCH).astype(int) for n in order}
    g.put(FIXED)
    for n in order:
        g.put(n, sh[n])
    for n in order:
        # rotation only starts once a part is clear, so translation is what can collide
        for j, v in g.counts(n, sh[n]).items():
            if v > INIT[n].get(j, 0) + TOL:
                key = tuple(sorted((n, names[j])))
                bad[key] = bad.get(key, 0) + 1
print("replay: colliding pairs", len(bad))
for k, v in sorted(bad.items(), key=lambda kv: -kv[1])[:12]:
    print("   ", k, v, "frames")

# ---------------------------------------------------------------- write back (lid parts: directions in the lid frame)
Rinv = np.linalg.inv(LIDM[:3, :3])
for n, p in plan.items():
    m = meta[n]
    d = np.array(p["dir"])
    if m["lid"]:
        d = Rinv @ d
    m["plan"] = dict(dir=d.tolist(), clear=p["clear"], dist=p["dist"], t0=p["t0"], t1=p["t1"], order=p["order"],
                     tumble=p["tumble"])
meta[FIXED]["plan"] = None
for n, h in FOLLOW.items():
    if n in meta:
        meta[n].pop("explode", None); meta[n]["host"] = h
meta["_plan"] = dict(lid_deg=LID_DEG, n=N, pairs=len(bad))
json.dump(meta, open(f"{SITE}/parts.json", "w"), indent=1)
print("wrote plan for", N, "parts")

if os.environ.get("DEBUG_PAIR"):
    a, b2 = os.environ["DEBUG_PAIR"].split(",")
    print(a, plan[a]); print(b2, plan[b2])
    for E in np.linspace(0, 1, 41):
        g = Grid(); g.put(b2, np.round(offset(b2, E) / PITCH).astype(int))
        c = g.counts(a, np.round(offset(a, E) / PITCH).astype(int)).get(idx[b2], 0)
        if c > INIT[a].get(idx[b2], 0) + TOL:
            print(f"   E={E:.3f} overlap {c} (init {INIT[a].get(idx[b2], 0)})")
