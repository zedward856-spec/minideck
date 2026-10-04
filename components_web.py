"""Real-colour component models for the promo site, each placed exactly where the case's part sits.

  official / free models (fitted onto the in-place placeholder by trying all 24 axis orientations):
      lora (Ebyte E22-900T22S, Ebyte), pn532 (Elechouse PN532 V4, Elechouse),
      gps_patch_antenna (Taoglas DSGP184B 18x18), m2_hardware + lid_inserts (CNC Kitchen M2 short, CC BY)
      radxa: coloured_radxa.py (Radxa official STEP)
  own models (real sizes / colours): 18650, gps_module (ATGM336H board), sdr_dongle (NESDR Nano 2+),
      driver_board (EHD-40P-V3), screen_panel (EP28060S), antennas
  the case's own detailed shapes, coloured by layer: tp4056, dac, mt3608

    python3 components_web.py  ->  models/coloured/<part>.glb   (case frame, closed lid)
"""
import glob, itertools, numpy as np, trimesh, pyvista as pv
from step2glb import load_coloured

SRC = "out/parts_in_place"
OUT = "models/coloured"
CAP = 2500                                        # faces per colour for the web

def hexc(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

def shrink(m, cap=CAP):
    n = len(m.faces)
    if n <= cap:
        return m
    p = pv.PolyData(m.vertices, np.c_[np.full(n, 3), m.faces].ravel()).decimate(1 - cap / n)
    return trimesh.Trimesh(p.points, p.faces.reshape(-1, 4)[:, 1:])

def save(name, parts):
    sc = trimesh.Scene()
    for i, (m, c) in enumerate(parts):
        if m is None or not len(m.faces):
            continue
        m = shrink(m)
        m.visual.face_colors = [int(c[0] * 255), int(c[1] * 255), int(c[2] * 255), 255]
        sc.add_geometry(m, geom_name=f"c{i}")
    sc.export(f"{OUT}/{name}.glb")
    print(f"{name:18s} {len(sc.geometry):2d} colours {sum(len(g.faces) for g in sc.geometry.values()):6d} faces")

def rotations():
    out = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            R = np.zeros((3, 3))
            for i, (p, s) in enumerate(zip(perm, signs)):
                R[i, p] = s
            if np.linalg.det(R) > 0:
                out.append(R)
    return out

def fit(parts, target, prefer=None, scale=False, allowed=None, seat=False):
    """best axis rotation (+ bbox-centre alignment, optional per-axis scale) of a coloured model onto the
    placeholder: by surface agreement when the placeholder is detailed, else by box size."""
    allm = trimesh.util.concatenate([m for m, _ in parts])
    S = allm.sample(2500)
    detailed = len(target.faces) > 200
    pq = trimesh.proximity.ProximityQuery(target) if detailed else None
    tc, ts = target.bounds.mean(0), np.ptp(target.bounds, 0)
    best = None
    for R in rotations():
        if allowed is not None and not allowed(R):
            continue
        v = allm.vertices @ R.T
        lo, hi = v.min(0), v.max(0)
        size = hi - lo
        k = ts / np.maximum(size, 1e-6) if scale else np.ones(3)
        off = tc - (lo + hi) / 2 * k
        if seat:                                      # rests on the placeholder's floor
            off[2] = target.bounds[0][2] - lo[2] * k[2]
        if detailed:
            P = (S @ R.T) * k + off
            score = np.mean(np.abs(pq.signed_distance(P[::5])) < 0.25) - np.abs(size * k - ts).sum() * 0.01
        else:
            score = -np.abs(size * k - ts).sum()
        if prefer is not None:
            score += prefer(R) * 1e-3
        if best is None or score > best[0]:
            best = (score, R, k, off)
    _, R, k, off = best
    out = []
    for m, c in parts:
        m = m.copy(); m.vertices = (m.vertices @ R.T) * k + off
        out.append((m, c))
    return out, best[0]

def placeholder(name):
    return trimesh.load(f"{SRC}/{name}.stl")

# ---------------------------------------------------------------- official / free models
def official():
    jobs = {
        "lora": ("models/components/ebyte_e22_900t22s/E22-xxxT22S(3D).step", None, False, None, False),
        "pn532": (glob.glob("models/components/pn532_elechouse/*.step")[0], None, False, lambda R: R[2, 2] < 0, True),
        # the patch faces the sky (out of the closed lid's top), cable side down
        "gps_patch_antenna": ("models/components/gps_patch_antenna_18x18/DSGP184B_Web.STEP",
                              lambda R: R[2, 1], False, None, False),
    }
    for name, (path, prefer, scale, allowed, seat) in jobs.items():
        parts = load_coloured(path, tol=0.05)
        if name == "pn532":                           # raw FR4 brown on the underside: the real board is red both sides
            red = (0.70, 0.09, 0.11)                  # the real board's deep red (the file's (0.95, 0.33, 0.33) reads salmon)
            parts = [(m, red if c in ((0.502, 0.251, 0.0), (0.95, 0.332, 0.325)) else c) for m, c in parts]
        placed, score = fit(parts, placeholder(name), prefer, scale, allowed, seat)
        print(f"  {name}: fit score {score:.2f}")
        save(name, placed)
    # heat-set inserts: one real insert at every insert the case has
    ins = load_coloured("models/components/heatset_insert_m2/cnckitchen_M2_Short.step", tol=0.03)
    im = trimesh.util.concatenate([m for m, _ in ins]); col = ins[0][1]
    lo, hi = im.bounds; ax = int(np.argmin(np.abs(np.ptp(im.bounds, 0) - 3.0)))   # its 3 mm axis
    for name in ("m2_hardware", "lid_inserts"):
        bodies = placeholder(name).split(only_watertight=False)
        ms = []
        for b in bodies:
            m = im.copy()
            if ax != 2:
                m.apply_transform(trimesh.geometry.align_vectors(np.eye(3)[ax], (0, 0, 1)))
            m.apply_translation(b.bounds.mean(0) - m.bounds.mean(0))
            ms.append(m)
        save(name, [(trimesh.util.concatenate(ms), col)])

# ---------------------------------------------------------------- the case's shapes, coloured by layer
def by_layer(name, pcb, comp=hexc("#151517"), metal=None, metal_sel=None):
    m = placeholder(name)
    c = m.triangles_center; n = m.face_normals
    # the board: the z band holding the most flat (horizontal) area
    flat = np.abs(n[:, 2]) > 0.95
    zs = np.round(c[flat, 2], 1); areas = m.area_faces[flat]
    zz, inv = np.unique(zs, return_inverse=True); tot = np.bincount(inv, areas)
    top2 = zz[np.argsort(-tot)[:2]]
    z0, z1 = top2.min(), top2.max()
    if z1 - z0 > 2.2 or z1 - z0 < 0.6:               # fall back to a 1.6 mm board at the most-area plane
        z0, z1 = zz[np.argmax(tot)] - 1.6, zz[np.argmax(tot)]
    board = (c[:, 2] >= z0 - 0.05) & (c[:, 2] <= z1 + 0.05)
    sel_m = metal_sel(c) if metal_sel is not None else np.zeros(len(c), bool)
    groups = [(board & ~sel_m, pcb), (~board & ~sel_m, comp)]
    if metal is not None:
        groups.append((sel_m, metal))
    save(name, [(m.submesh([np.where(g)[0]], append=True), col) for g, col in groups if g.sum()])

def layered():
    import layout as L
    pc = L.port_cutouts()
    x0, x1, z0, z1, yf = pc["charger_usbc"]
    by_layer("tp4056", hexc("#1f4fc4"), metal=hexc("#c9cacc"),
             metal_sel=lambda c: (c[:, 0] > x0 - .3) & (c[:, 0] < x1 + .3) & (c[:, 2] > z0 - .3) & (c[:, 2] < z1 + .3) & (c[:, 1] < yf + 7.6))
    jx, jz, jy = pc["jack"]
    by_layer("dac", hexc("#5b2a9e"), metal=hexc("#1a1a1c"),
             metal_sel=lambda c: (np.hypot(c[:, 0] - jx, c[:, 2] - jz) < 3.4) & (c[:, 1] < jy + 13.0))
    boost()

def boost():
    """Pololu U3V40F5: green board, black shielded inductor, the converter chip, pads along the back edge"""
    lo, hi = placeholder("mt3608").bounds; t = 1.6
    pcb = box(lo, (hi[0], hi[1], lo[2] + t)); top = lo[2] + t
    cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
    ind = box((cx - 3.9, cy - 3.9, top), (cx + 3.9, cy + 3.9, hi[2]))
    chip = box((lo[0] + 1.5, lo[1] + 1.5, top), (lo[0] + 4.5, lo[1] + 4.5, top + 1.0))
    caps = trimesh.util.concatenate([box((hi[0] - 4.0, lo[1] + 1.2 + k * 3.2, top), (hi[0] - 1.2, lo[1] + 2.8 + k * 3.2, top + 1.6)) for k in range(3)])
    pads = trimesh.util.concatenate([cyl(0.8, 0.05, 2, (lo[0] + 2.5 + k * 2.5, hi[1] - 1.2, top + 0.02), 20) for k in range(5)])
    save("mt3608", [(pcb, hexc("#1f6d3a")), (ind, hexc("#16161a")), (trimesh.util.concatenate([chip, caps]), hexc("#2a2a2c")), (pads, hexc("#d4a93a"))])

# ---------------------------------------------------------------- own models
def box(lo, hi):
    return trimesh.creation.box(bounds=[lo, hi])

def cyl(r, h, axis, centre, sections=48):
    m = trimesh.creation.cylinder(radius=r, height=h, sections=sections)
    if axis != 2:
        m.apply_transform(trimesh.geometry.align_vectors((0, 0, 1), np.eye(3)[axis]))
    m.apply_translation(centre); return m

def own():
    # 18650: blue wrap, steel ends, + button at the right end (the chamber's + contact)
    b = placeholder("18650").bounds; lo, hi = b; r = (hi[1] - lo[1]) / 2; yc, zc = (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2
    L = hi[0] - lo[0]
    wrap = cyl(r, L - 0.4, 0, ((lo[0] + hi[0]) / 2, yc, zc))        # blue wrap the full length
    neg = cyl(r - 0.35, 0.6, 0, (lo[0] + 0.3, yc, zc))
    pos = cyl(r - 1.2, 0.6, 0, (hi[0] - 1.1, yc, zc))
    btn = cyl(3.2, 0.9, 0, (hi[0] - 0.45, yc, zc))
    ring = cyl(r - 0.6, 0.15, 0, (hi[0] - 0.75, yc, zc))
    save("18650", [(wrap, hexc("#2c64c8")), (trimesh.util.concatenate([neg, pos, btn]), hexc("#c7c9cc")),
                   (ring, hexc("#f2f2f0"))])

    # ATGM336H mini board standing on its long edge: green PCB against the chamber wall (low x), silver module
    # can, gold IPEX and two small chips on the face toward the right wall; pads along its top edge
    lo, hi = placeholder("gps_module").bounds; t = 1.0
    f = lo[0] + t                                   # component face
    cy, cz = (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2
    pcb = box(lo, (f, hi[1], hi[2]))
    can = box((f, cy - 4.85, cz - 5.0 - 1.0), (f + 2.2, cy + 4.85, cz + 5.0 - 1.0))
    ipex = cyl(1.0, 1.2, 0, (f + 0.6, hi[1] - 2.4, hi[2] - 2.6), 24)
    chips = trimesh.util.concatenate([box((f, lo[1] + 1.0, lo[2] + 1.2), (f + 0.9, lo[1] + 2.6, lo[2] + 3.4)),
                                      box((f, lo[1] + 1.0, lo[2] + 4.2), (f + 0.6, lo[1] + 2.0, lo[2] + 5.6))])
    pads = trimesh.util.concatenate([box((f, lo[1] + 1.0 + k * 2.54, hi[2] - 1.6), (f + 0.04, lo[1] + 2.4 + k * 2.54, hi[2] - 0.4)) for k in range(5)])
    save("gps_module", [(pcb, hexc("#1d6b3a")), (can, hexc("#cfd2d6")), (trimesh.util.concatenate([ipex, pads]), hexc("#d4a93a")), (chips, hexc("#141416"))])

    # NESDR Nano 2+: black anodised body; the USB end (plug cut off, wired) faces the bay opening on the right,
    # the gold MCX antenna jack is on the left end
    lo, hi = placeholder("sdr_dongle").bounds
    body = box((lo[0], lo[1], lo[2]), (hi[0] - 4.0, hi[1], hi[2]))
    usb = box((hi[0] - 4.0, lo[1] + 1.2, lo[2] + 4.0), (hi[0], hi[1] - 1.2, hi[2] - 4.0))
    mcx = cyl(1.8, 3.0, 0, (lo[0] - 1.0, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2), 24)
    stripe = box((hi[0] - 9, lo[1] - 0.02, lo[2] + 3), (hi[0] - 6, hi[1] + 0.02, hi[2] - 3))
    save("sdr_dongle", [(body, hexc("#19191b")), (usb, hexc("#c9cacc")), (mcx, hexc("#d4a93a")), (stripe, hexc("#d22b2b"))])

    # EHD-40P-V3 driver: black PCB, silver mini-HDMI + USB-C on the hinge edge, gold 40-pin FPC socket, chips
    lo, hi = placeholder("driver_board").bounds; t = 1.6
    pcb = box((lo[0], lo[1], lo[2] + 0.6), (hi[0], hi[1], lo[2] + 0.6 + t))
    top = lo[2] + 0.6 + t
    hdmi = box((lo[0] + 8, hi[1] - 7.5, top), (lo[0] + 19.5, hi[1] + 0.6, top + 3.4))
    usbc = box((lo[0] + 25, hi[1] - 7.0, top), (lo[0] + 34, hi[1] + 0.4, top + 3.2))
    fpc = box((lo[0] + 6, lo[1] + 2, top), (hi[0] - 6, lo[1] + 6.5, top + 1.6))
    chip = box(((lo[0] + hi[0]) / 2 - 6, (lo[1] + hi[1]) / 2 - 6, top), ((lo[0] + hi[0]) / 2 + 6, (lo[1] + hi[1]) / 2 + 6, top + 1.2))
    small = trimesh.util.concatenate([box((lo[0] + 6 + k * 6, (lo[1] + hi[1]) / 2 + 9, top), (lo[0] + 9 + k * 6, (lo[1] + hi[1]) / 2 + 12, top + 0.8)) for k in range(4)])
    save("driver_board", [(pcb, hexc("#18191b")), (trimesh.util.concatenate([hdmi, usbc]), hexc("#c9cacc")), (fpc, hexc("#d4a93a")),
                          (trimesh.util.concatenate([chip, small]), hexc("#0c0c0d"))])

    # EP28060S panel: glossy black glass (faces the keyboard when closed), steel back, amber FPC tail
    lo, hi = placeholder("screen_panel").bounds
    glass = box(lo, (hi[0], hi[1], lo[2] + 1.2))
    back = box((lo[0] + 0.3, lo[1] + 0.3, lo[2] + 1.2), (hi[0] - 0.3, hi[1] - 0.3, hi[2]))
    fpc = box((hi[0] - 0.2, (lo[1] + hi[1]) / 2 - 9, hi[2] - 0.15), (hi[0] + 6.0, (lo[1] + hi[1]) / 2 + 9, hi[2]))
    save("screen_panel", [(glass, hexc("#05070b")), (back, hexc("#b9bcc0")), (fpc, hexc("#c98a1c"))])

    # FPC antennas: amber polyimide with a darker radiator pattern
    for name in ("antenna_lora", "antenna_wifi", "antenna_sdr"):
        lo, hi = placeholder(name).bounds; sz = hi - lo
        thin = int(np.argmin(sz))
        base = box(lo, hi)
        a = [i for i in range(3) if i != thin]
        trace_lo, trace_hi = lo.copy(), hi.copy()
        trace_lo[a[0]] += sz[a[0]] * 0.12; trace_hi[a[0]] -= sz[a[0]] * 0.12
        trace_lo[a[1]] += sz[a[1]] * 0.3; trace_hi[a[1]] -= sz[a[1]] * 0.3
        trace_lo[thin] -= 0.02; trace_hi[thin] += 0.02
        save(name, [(base, hexc("#c8901e")), (box(trace_lo, trace_hi), hexc("#7a4a0c"))])

if __name__ == "__main__":
    import os
    os.makedirs(OUT, exist_ok=True)
    official(); layered(); own()
