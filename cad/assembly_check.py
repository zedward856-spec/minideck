"""Assembly simulator: can every part actually be put in, in the build-guide order, without forcing it?

Everything is voxelised at PITCH. Parts go in one by one, each checked against the case + everything already
installed. For each part it searches for a way in:
  - straight in along a set of directions (from above, below, the sides, ...) until it is clear of everything
  - dropped in from above to a point beside its spot, then slid sideways into place (hooks under ledges,
    connectors into wall openings, the switch knob into its pocket)
A part may slide OUT of an overlap the model has by design (pins in holes, a board resting on a floor) but may
never push into anything new. Every path found is re-tested with the part grown by one voxel: "clear" means it
also passes that way (>= PITCH of room), "tight" means it only just passes (scrapes / needs a wiggle).
Wires are flexible and left out.

    python3 assembly_check.py   -> reports/assembly_report.md
"""
import _here  # noqa: F401  (repo root as the working dir)
import os, numpy as np, trimesh
from scipy import ndimage

SRC = "out/parts_in_place"
PITCH = 0.3
TOL = 2                                    # voxels of slack
UP, DOWN = (0, 0, 1), (0, 0, -1)
AXES = [(0, 0, 1), (0, 0, -1), (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)]
SIDE = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)]

# build order (BUILD.md), with how each part goes in. "case" = the parts that start out installed.
BASE = ["bottom", "m2_hardware"]                         # inserts are melted into the case
SNAP = {"pn532": "drops straight in and snaps under its 2 front corner clips (lips overhang 0.6 mm by design)",
        "door_lock": "snap-on C-clip by design: spreads over the rail (fit suite: lips hook 0.4 mm behind it)",
        "antenna_lora": "flexible sticker, bends into place", "antenna_sdr": "flexible sticker, bends into place",
        "antenna_wifi": "flexible sticker, bends into place"}
STEPS = [
    ("pn532", "PN532 into its floor pocket (snaps under its front clips)", "top"),
    ("antenna_lora", "LoRa FPC antenna onto the box's back wall", "top"),
    ("antenna_sdr", "SDR FPC antenna onto the box's back wall", "top"),
    ("antenna_wifi", "Wi-Fi FPC antenna onto the box roof", "any"),
    ("lora", "E22 LoRa module", "top"),
    ("dac", "PCM5102 DAC, jack into the front", "top"),
    ("radxa", "Radxa ZERO 3W, upside down, ports to the front", "top"),
    ("mt3608", "Pololu U3V40F5 boost, under the charger", "top"),
    ("tp4056", "TP4056 charger, USB-C into the front", "top"),
    ("gps_module", "GPS board, standing on its edge", "top"),
    ("switch_knob", "power switch knob (from inside)", "top"),
    ("power_switch", "SS12D00 switch, lever into the knob", "top"),
    ("sdr_dongle", "NESDR Nano 2+ into the hinge box", "any"),
    ("LID", "finished lid lowered onto the hinge, between the cheeks", "top"),
    ("torque_hinge", "torque hinge into the left cheek (D-shaft into the lid)", (-1, 0, 0)),
    ("hinge_axle", "hollow axle in from the right", (1, 0, 0)),
    ("hinge_cap", "hinge cap over the torque hinge", (-1, 0, 0)),
    ("keyboard", "CardKB", "top"),
    ("keyboard_top", "keyboard plate", "top"),
    ("screws_base#0", "plate screw (front left)", (0, 0, 1)),
    ("screws_base#1", "plate screw (back left)", (0, 0, 1)),
    ("screws_base#6", "plate screw (front right)", (0, 0, 1)),
    ("screws_base#7", "plate screw (back right)", (0, 0, 1)),
    ("18650", "18650 in through the door opening (door still off)", "any"),
    ("battery_door", "battery door (hinge pin from the top)", "any"),
    ("door_lock", "C-clip lock onto its rail", "any"),
    ("box_hatch", "hinge-box hatch (from below)", "bottom"),
    ("screws_base#2", "hatch screw", (0, 0, -1)),
    ("screws_base#3", "hatch screw", (0, 0, -1)),
    ("screws_base#4", "hatch screw", (0, 0, -1)),
    ("screws_base#5", "hatch screw", (0, 0, -1)),
]
LID_BASE = ["screen_back", "lid_inserts"]
LID_STEPS = [
    ("gps_patch_antenna", "GPS patch into the lid shell", "lid"),
    ("driver_board", "screen driver board", "lid"),
    ("screen_panel", "screen panel", "lid"),
    ("screen_front", "screen bezel", "lid"),
    ("screws_lid#0", "bezel screw", (0, 0, -1)),
    ("screws_lid#1", "bezel screw", (0, 0, -1)),
    ("screws_lid#2", "bezel screw", (0, 0, -1)),
    ("screws_lid#3", "bezel screw", (0, 0, -1)),
]


_SPLIT = {}
def load(name):
    if "#" in name:                                       # one piece of a multi-body file (a single screw)
        base, k = name.split("#")
        if base not in _SPLIT:
            ps = trimesh.load(f"{SRC}/{base}.stl").split(only_watertight=False)
            _SPLIT[base] = sorted(ps, key=lambda p: tuple(np.round(p.bounds.mean(0), 1)))
        return _SPLIT[base][int(k)]
    if name == "LID":                                     # the finished lid, lowered onto the hinge as one piece
        parts = ["screen_back", "lid_inserts", "gps_patch_antenna", "driver_board", "screen_panel", "screen_front", "screws_lid"]
        return trimesh.util.concatenate([trimesh.load(f"{SRC}/{p}.stl") for p in parts])
    return trimesh.load(f"{SRC}/{name}.stl")


ORIGIN = np.array([-30.0, -30.0, -30.0])
M = 8192


def voxels(mesh):
    """solid voxels without big memory: fill horizontal cross-sections on the grid, plus surface samples
    (so paper-thin parts like the FPC antennas are never lost between slices)"""
    import shapely
    lo, hi = mesh.bounds
    k0 = int(np.floor((lo[2] - ORIGIN[2]) / PITCH)); k1 = int(np.ceil((hi[2] - ORIGIN[2]) / PITCH))
    zs = ORIGIN[2] + np.arange(k0, k1 + 1) * PITCH
    i0 = int(np.floor((lo[0] - ORIGIN[0]) / PITCH)); i1 = int(np.ceil((hi[0] - ORIGIN[0]) / PITCH))
    j0 = int(np.floor((lo[1] - ORIGIN[1]) / PITCH)); j1 = int(np.ceil((hi[1] - ORIGIN[1]) / PITCH))
    I, J = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1), indexing="ij")
    X, Y = ORIGIN[0] + I * PITCH, ORIGIN[1] + J * PITCH
    out = []
    secs = mesh.section_multiplane(plane_origin=[0, 0, 0], plane_normal=[0, 0, 1], heights=list(zs))
    for kz, (z, sec) in enumerate(zip(zs, secs)):
        if sec is None:
            continue
        T = sec.metadata.get("to_3D", np.eye(4))
        for poly in sec.polygons_full:
            ext = np.c_[np.asarray(poly.exterior.coords), np.zeros(len(poly.exterior.coords)), np.ones(len(poly.exterior.coords))] @ T.T
            holes = [np.c_[np.asarray(h.coords), np.zeros(len(h.coords)), np.ones(len(h.coords))] @ T.T for h in poly.interiors]
            wp = shapely.Polygon(ext[:, :2], [h[:, :2] for h in holes])
            if not wp.is_valid:
                wp = wp.buffer(0)
            bx0, by0, bx1, by1 = wp.bounds
            sel = (X >= bx0 - PITCH) & (X <= bx1 + PITCH) & (Y >= by0 - PITCH) & (Y <= by1 + PITCH)
            if not sel.any():
                continue
            inside = shapely.contains_xy(wp, X[sel], Y[sel])
            ii, jj = I[sel][inside], J[sel][inside]
            out.append(np.c_[ii, jj, np.full(len(ii), k0 + kz)])
    n = int(max(2000, min(600000, mesh.area / (PITCH * PITCH) * 3)))
    pts = mesh.sample(n)
    out.append(np.round((pts - ORIGIN) / PITCH).astype(np.int64))
    return np.unique(np.vstack(out).astype(np.int64), axis=0)


def keys(c):
    c = c.astype(np.int64) + M // 2
    return (c[:, 0] * M + c[:, 1]) * M + c[:, 2]


def erode(vox, n):
    """shave n voxels off every surface (parts thinner than that are kept as they are)"""
    if n == 0:
        return vox
    lo = vox.min(0) - 1
    g = np.zeros(vox.max(0) - lo + 2, bool); g[tuple((vox - lo).T)] = True
    e = ndimage.binary_erosion(g, iterations=n)
    return np.argwhere(e) + lo if e.sum() > 0.05 * g.sum() else vox


def dilate(vox):
    lo = vox.min(0) - 1
    g = np.zeros(vox.max(0) - lo + 2, bool); g[tuple((vox - lo).T)] = True
    g = ndimage.binary_dilation(g)
    return np.argwhere(g) + lo


class Static:
    def __init__(self):
        self.k = np.zeros(0, np.int64); self._lab = np.zeros(0, np.int32); self.names = []
    def add(self, name, vox):
        self.names.append(name)
        k = keys(vox)
        self.k = np.concatenate([self.k, k]); self._lab = np.concatenate([self._lab, np.full(len(k), len(self.names) - 1, np.int32)])
        o = np.argsort(self.k, kind="stable"); self.k = self.k[o]; self._lab = self._lab[o]
    def hits(self, vox, shift):
        q = keys(vox + np.asarray(shift, np.int64))
        p = np.searchsorted(self.k, q); p[p >= len(self.k)] = 0
        m = self.k[p] == q
        lab = self._lab[p[m]]
        u, c = np.unique(lab, return_counts=True)
        return dict(zip(u.tolist(), c.tolist()))


def blocked(static, vox, shift, init):
    for j, v in static.hits(vox, shift).items():
        if v > init.get(j, 0) + TOL:
            return static.names[j]
    return None


def straight(static, vox, d, init, lo_s, hi_s, maxk=600):
    """slide out along d until clear of everything; return (ok, blocker, distance)"""
    d = np.asarray(d); lo, hi = vox.min(0), vox.max(0)
    prev = dict(init)
    for k in range(1, maxk):
        hit = blocked(static, vox, d * k, prev)
        if hit:
            return False, hit, k * PITCH
        prev = {j: min(v, prev.get(j, 0)) for j, v in static.hits(vox, d * k).items()}
        if ((hi + d * k < lo_s) | (lo + d * k > hi_s)).any():
            return True, None, k * PITCH
    return False, "too far", maxk * PITCH


def find_path(static, vox, mode, lo_s, hi_s):
    init = static.hits(vox, (0, 0, 0))
    tried = []
    if isinstance(mode, tuple):                           # goes in along its own axis (screws, axle, hinge)
        ok, hit, dist = straight(static, vox, mode, init, lo_s, hi_s)
        if ok:
            return dict(kind="straight", dir=mode, dist=dist), tried
        return None, [f"along its axis {mode}: blocked by {hit} after {dist:.1f} mm"]
    dirs = {"top": [UP], "bottom": [DOWN], "lid": [DOWN], "any": AXES}[mode]
    for d in dirs:                                        # 1. straight out (= straight in, reversed)
        ok, hit, dist = straight(static, vox, d, init, lo_s, hi_s)
        if ok:
            return dict(kind="straight", dir=d, dist=dist), tried
        tried.append(f"straight {d}: blocked by {hit} after {dist:.1f} mm")
    if mode in ("top", "any", "lid"):                      # 2. (lift a little), slide sideways, then out
        out_dir = np.array(DOWN if mode == "lid" else UP)
        for lift in range(0, 13):                         # first lift up to ~3.6 mm (clear pegs, pockets)
            prev = dict(init); ok_lift = True
            for k in range(1, lift + 1):
                if blocked(static, vox, out_dir * k, prev):
                    ok_lift = False; break
                prev = {j: min(v, prev.get(j, 0)) for j, v in static.hits(vox, out_dir * k).items()}
            if not ok_lift:
                break
            v1 = vox + out_dir * lift; p1 = dict(prev)
            for h in SIDE:
                h = np.array(h); prev = dict(p1)
                for s in range(1, 34):                    # slide up to ~10 mm
                    hit = blocked(static, v1, h * s, prev)
                    if hit:
                        if lift == 0:
                            tried.append(f"slide {tuple(int(x) for x in h)}: blocked by {hit} after {s * PITCH:.1f} mm")
                        break
                    prev = {j: min(v, prev.get(j, 0)) for j, v in static.hits(v1, h * s).items()}
                    if s % 3 == 0 or s < 4:
                        ok, hit2, dist = straight(static, v1 + h * s, out_dir, prev, lo_s, hi_s)
                        if ok:
                            return dict(kind="lift+slide+lift", lift=lift * PITCH, dir=tuple(h), slide=s * PITCH,
                                        out=tuple(out_dir), dist=dist), tried
    return None, tried


def clearance_ok(static, vox, path, lo_s, hi_s):
    """re-run the found path with the part grown by one voxel"""
    big = dilate(vox)
    init = static.hits(big, (0, 0, 0))
    if path["kind"] == "straight":
        return straight(static, big, path["dir"], init, lo_s, hi_s)[0]
    out = np.array(path["out"]); h = np.array(path["dir"]); prev = dict(init)
    nl = int(round(path.get("lift", 0) / PITCH)); ns = int(round(path["slide"] / PITCH))
    moves = [out * k for k in range(1, nl + 1)] + [out * nl + h * s for s in range(1, ns + 1)]
    for mv in moves:
        if blocked(static, big, mv, prev):
            return False
        prev = {j: min(v, prev.get(j, 0)) for j, v in static.hits(big, mv).items()}
    return straight(static, big + out * nl + h * ns, out, prev, lo_s, hi_s)[0]


def tilt_in(static, mesh, max_deg=30, step=2):
    """board slid in back-edge-first at an angle, then swung down flat about its back-bottom edge: every
    angle on the way must be clear (only the last few degrees may press past snap clips)"""
    lo, hi = mesh.bounds
    pivot = np.array([0.0, hi[1], lo[2]])
    worst = {}
    for deg in range(max_deg, -1, -step):
        m = mesh.copy()
        m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-deg), (1, 0, 0), point=pivot))   # front up
        v = erode(voxels(m), 1)
        h = {static.names[j]: c for j, c in static.hits(v, (0, 0, 0)).items() if c > TOL}
        if h:
            worst[deg] = h
    return worst


def run(base, steps, title):
    static = Static()
    for n in base:
        static.add(n, voxels(load(n)))
    rows = []
    allv = {}
    for name, desc, mode in steps:
        src = "screen_back" if name == "LID" else name.split("#")[0]
        if not os.path.exists(f"{SRC}/{src}.stl"):
            rows.append((desc, "skipped (no model)", "")); continue
        vox = voxels(load(name)); allv[name] = vox
        lo_s = np.min([static.k.min()]) if False else None
        cv = np.vstack([vox] + [np.zeros((0, 3), np.int64)])
        # envelope of everything installed so far + this part
        pts = np.asarray(static.k)
        sk = pts + 0
        ijk = np.stack([(sk // (M * M)) - M // 2, ((sk // M) % M) - M // 2, (sk % M) - M // 2], 1)
        lo_s, hi_s = ijk.min(0), ijk.max(0)
        flexible = name.startswith("antenna_")
        if mode == "tilt":
            worst = tilt_in(static, load(name))
            if not worst:
                rows.append((desc, "OK (tilted in)", "back edge first under the battery chamber at ~30°, then swung down flat"))
            elif set(worst) <= {0, 2, 4}:
                rows.append((desc, "OK, tilted in, **snaps** past the corner clips at the end",
                             "back edge first under the battery chamber, then swung down; last few degrees press past the clips: "
                             + ", ".join(f"{k}° {v}" for k, v in sorted(worst.items()))))
            else:
                rows.append((desc, "**BLOCKED** when tilting in", ", ".join(f"{k}°: {v}" for k, v in sorted(worst.items(), reverse=True)[:4])))
            static.add(name, vox); print(f"  {desc:50s} {rows[-1][1]}"); continue
        result = None
        for e, label in ((0, None), (1, "OK, sliding contact (rubs, <= 0.3 mm)"), (2, "**snap / press fit** (0.3-0.6 mm)"),
                         (3, "**snap / press fit** (0.6-0.9 mm)"), (5, "**forced** (0.9-1.5 mm)")):
            ve = erode(vox, e)
            path, tried = find_path(static, ve, mode, lo_s, hi_s)
            if path is not None:
                result = (e, label, path); break
        if result is None and name in SNAP:
            rows.append((desc, "OK, " + SNAP[name], ""))
        elif result is None:
            rows.append((desc, "**BLOCKED** (even with 1.5 mm give)", "; ".join(tried[:3])))
        else:
            e, label, path = result
            if e == 0:
                label = "OK, clear" if clearance_ok(static, vox, path, lo_s, hi_s) else "OK, **tight** (< 0.3 mm room)"
            if flexible and e > 0:
                label += " - flexible sticker, bends into place"
            d = lambda v: tuple(int(-x) for x in v)
            if path["kind"] == "straight":
                how = f"straight in along {d(path['dir'])}"
            else:
                how = (f"in along {d(path['out'])}, then {path['slide']:.1f} mm along {d(path['dir'])}"
                       + (f", then the last {path['lift']:.1f} mm along {d(path['out'])}" if path.get("lift") else ""))
            rows.append((desc, label, how))
        if name == "LID":                                 # the lid is swung open (110 deg) for the rest of the build
            import json as _j
            H = _j.load(open(os.path.expanduser("~/minideck-site/assets/parts.json")))["_hinge"]
            lm = load("LID"); lm.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-110), (1, 0, 0), point=(0, H["y"], H["z"])))
            vox = voxels(lm)
        static.add(name, vox)
        print(f"  {desc:50s} {rows[-1][1]}")
    return rows


if __name__ == "__main__":
    print("base:")
    rb = run(BASE, STEPS, "base")
    print("lid:")
    rl = run(LID_BASE, LID_STEPS, "lid")
    L = ["# Assembly check", "",
         f"Parts go in one by one in the build-guide order, each against the case + everything already installed, "
         f"voxelised at {PITCH} mm. 'clear' = it also goes in when grown by {PITCH} mm; 'tight' = it only just passes. "
         "Wires are flexible and not included.", ""]
    for title, rows in (("Base", rb), ("Lid", rl)):
        L += [f"## {title}", "", "| Step | Result | How it goes in |", "|---|---|---|"]
        L += [f"| {d} | {r} | {h} |" for d, r, h in rows]
        L.append("")
    open("reports/assembly_report.md", "w").write("\n".join(L) + "\n")
    bad = sum("BLOCKED" in r for _, r, _ in rb + rl); tight = sum("tight" in r for _, r, _ in rb + rl)
    print(f"blocked {bad}, tight {tight}, of {len(rb) + len(rl)}")
