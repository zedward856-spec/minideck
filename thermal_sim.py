"""Steady-state 3D thermal simulation of the base (lid open, as in use) on a 1 mm grid.

Every grid cell gets a material from the real part models (case plastic, PCB, chips, battery, air, ...).
Heat sources sit in the parts that make heat. Heat conducts through everything; the outside surfaces lose
heat to the room (natural convection + radiation, h_eff); the air inside is still air (conduction, slightly
enhanced). Vents add a chimney-effect airflow (from the inside air temperature, iterated), a fan adds a fixed
airflow; both remove heat from the inside air (well-mixed assumption, so a bit optimistic).

    python3 thermal_sim.py   -> thermal_report.md + previews/thermal_*.png
Numbers are estimates for COMPARING options, not lab-accurate temperatures.
"""
import os, json, numpy as np, trimesh
from scipy import sparse, ndimage
from scipy.sparse.linalg import cg, LinearOperator

SRC = "out/parts_in_place"
DX = 1.0e-3                                   # 1 mm cells
T_AMB = 25.0
H_SIDE, H_BOTTOM = 12.0, 5.0                  # W/m2K: free convection + radiation; bottom sits on a desk
K = dict(pla=0.13, petg=0.20, asa=0.17,
         air=0.07,                            # inside air: conduction + radiation across the mm gaps
         pcb=8.0, board=2.0, chip=1.0, cell=3.0, al=200.0, pad=3.0, silicone=0.2, flex=0.2, brass=110.0)
RHO_CP_AIR = 1.18 * 1005.0

# part -> material (later entries win where parts overlap)
PARTS = [("bottom", "case"), ("keyboard_top", "case"), ("box_hatch", "case"), ("battery_door", "case"),
         ("door_lock", "case"), ("switch_knob", "case"), ("hinge_cap", "case"), ("hinge_axle", "case"),
         ("keyboard", "board"), ("pn532", "board"), ("dac", "board"), ("lora", "board"), ("tp4056", "board"),
         ("mt3608", "board"), ("gps_module", "board"), ("sdr_dongle", "chip"), ("power_switch", "chip"),
         ("18650", "cell"), ("radxa", "pcb"), ("m2_hardware", "brass"),
         ("antenna_lora", "flex"), ("antenna_sdr", "flex"), ("antenna_wifi", "flex")]

# heat sources (W): typical use / heavy (SDR + Wi-Fi + CPU) / heavy while charging
SOC_BOX = (69.4, 81.4, 13.5, 25.5, 16.6, 18.3)          # RK3566 (faces down on the upside-down Radxa)
RAM_BOX = (40.8, 50.8, 11.3, 26.3, 17.5, 18.3)
WIFI_BOX = (53.4, 67.8, 8.1, 23.6, 17.4, 18.3)
SCEN = {
    "typical": dict(soc=0.8, ram=0.15, wifi=0.2, board=0.3, sdr=0.0, boost=0.35, tp=0.0, cell=0.07, gps=0.12, misc=0.25),
    "heavy": dict(soc=2.2, ram=0.3, wifi=0.6, board=0.4, sdr=1.4, boost=1.0, tp=0.0, cell=0.40, gps=0.12, misc=0.3),
    "typical+charging": dict(soc=0.8, ram=0.15, wifi=0.2, board=0.3, sdr=0.0, boost=0.35, tp=1.3, cell=0.12, gps=0.12, misc=0.25),
    "heavy+charging": dict(soc=2.2, ram=0.3, wifi=0.6, board=0.4, sdr=1.4, boost=1.0, tp=1.3, cell=0.45, gps=0.12, misc=0.3),
}


def grid():
    lo = np.array([-4.0, -4.0, -4.0]); hi = np.array([98.0, 86.0, 44.0])
    n = np.round((hi - lo) / 1.0).astype(int)
    return lo, n


def fill(mesh, lo, n):
    """cells whose centres are inside the mesh (horizontal cross-sections filled on the grid)"""
    import shapely
    occ = np.zeros(n, bool)
    zc = lo[2] + 0.5 + np.arange(n[2])
    xc = lo[0] + 0.5 + np.arange(n[0]); yc = lo[1] + 0.5 + np.arange(n[1])
    X, Y = np.meshgrid(xc, yc, indexing="ij")
    b = mesh.bounds
    ks = np.where((zc > b[0][2]) & (zc < b[1][2]))[0]
    if not len(ks):
        return occ
    secs = mesh.section_multiplane(plane_origin=[0, 0, 0], plane_normal=[0, 0, 1], heights=list(zc[ks]))
    for k, sec in zip(ks, secs):
        if sec is None:
            continue
        T = sec.metadata.get("to_3D", np.eye(4))
        for poly in sec.polygons_full:
            e = np.c_[np.asarray(poly.exterior.coords), np.zeros(len(poly.exterior.coords)), np.ones(len(poly.exterior.coords))] @ T.T
            hs = [np.c_[np.asarray(h.coords), np.zeros(len(h.coords)), np.ones(len(h.coords))] @ T.T for h in poly.interiors]
            wp = shapely.Polygon(e[:, :2], [h[:, :2] for h in hs])
            if not wp.is_valid:
                wp = wp.buffer(0)
            x0, y0, x1, y1 = wp.bounds
            sel = (X >= x0 - 1) & (X <= x1 + 1) & (Y >= y0 - 1) & (Y <= y1 + 1)
            if sel.any():
                ins = shapely.contains_xy(wp, X[sel], Y[sel])
                sl = occ[:, :, k]; sl[sel] |= ins
    if occ.sum() == 0:                                     # paper-thin part: mark the cells its surface passes
        p = mesh.sample(max(500, int(mesh.area * 4)))
        ijk = np.floor((p - lo) / 1.0).astype(int)
        ijk = ijk[(ijk >= 0).all(1) & (ijk < n).all(1)]
        occ[tuple(ijk.T)] = True
    return occ


def boxmask(lo, n, b):
    x0, x1, y0, y1, z0, z1 = b
    c = [lo[i] + 0.5 + np.arange(n[i]) for i in range(3)]
    mx = (c[0] >= x0) & (c[0] <= x1); my = (c[1] >= y0) & (c[1] <= y1); mz = (c[2] >= z0) & (c[2] <= z1)
    return mx[:, None, None] & my[None, :, None] & mz[None, None, :]


_CACHE = {}
def geometry():
    if "g" in _CACHE:
        return _CACHE["g"]
    lo, n = grid()
    occ = {}
    for name, mat in PARTS:
        if os.path.exists(f"{SRC}/{name}.stl"):
            occ[name] = fill(trimesh.load(f"{SRC}/{name}.stl"), lo, n)
    _CACHE["g"] = (lo, n, occ)
    return _CACHE["g"]


def solve(scen, case_mat="pla", vents=0.0, fan=0.0, pillar=False, plate=False, soc_scale=1.0, sdr_scale=1.0, t_amb=T_AMB):
    lo, n, occ = geometry()
    P = dict(SCEN[scen]); P["soc"] *= soc_scale; P["sdr"] *= sdr_scale
    k = np.full(n, np.nan)                                # nan = not a solid yet
    src = np.zeros(n)
    for name, mat in PARTS:
        if name not in occ:
            continue
        kk = K[case_mat] if mat == "case" else K[mat]
        k[occ[name]] = kk
    solid = ~np.isnan(k)
    # inside air: air not reachable from the outside (solids grown 1 cell so sub-mm gaps don't leak)
    # inside air = everything that isn't solid within the base's outer shell (the lid is open, so above the
    # base's top it is all room air); small leaks (port openings, the hollow axle) are ignored - slightly pessimistic
    shell = boxmask(lo, n, (0.0, 93.73, 0.0, 81.49, 0.0, 27.28))
    inside_air = ~solid & shell
    outside = ~solid & ~inside_air
    k[inside_air] = K["air"]
    # cooling options
    if pillar:                                            # aluminium block from the SoC down to the floor, pads at both ends
        m = boxmask(lo, n, (70.5, 80.5, 14.5, 24.5, 1.2, 16.6)) & ~solid
        k[m] = K["al"]
        k[boxmask(lo, n, (70.5, 80.5, 14.5, 24.5, 15.6, 16.6)) & m] = K["pad"]
        k[boxmask(lo, n, (70.5, 80.5, 14.5, 24.5, 1.2, 2.2)) & m] = K["pad"]
        inside_air &= ~m
    if plate:                                             # aluminium plate set into the floor under it (outside face)
        m = boxmask(lo, n, (68.0, 90.0, 4.0, 32.0, 0.0, 1.2))
        k[m & solid] = K["al"]
    # heat sources
    def put(mask, w):
        c = mask.sum()
        if c and w:
            src[mask] += w / c
    put(boxmask(lo, n, SOC_BOX) & occ["radxa"], P["soc"]) if boxmask(lo, n, SOC_BOX).any() else None
    put(boxmask(lo, n, RAM_BOX) & occ["radxa"], P["ram"])
    put(boxmask(lo, n, WIFI_BOX) & occ["radxa"], P["wifi"])
    put(occ["radxa"], P["board"])
    put(occ.get("sdr_dongle", np.zeros(n, bool)), P["sdr"])
    put(occ.get("mt3608", np.zeros(n, bool)), P["boost"] + 0.3 * (fan > 0))
    put(occ.get("tp4056", np.zeros(n, bool)), P["tp"])
    put(occ.get("18650", np.zeros(n, bool)), P["cell"])
    put(occ.get("gps_module", np.zeros(n, bool)), P["gps"])
    put(occ.get("pn532", np.zeros(n, bool)) | occ.get("lora", np.zeros(n, bool)) | occ.get("dac", np.zeros(n, bool)), P["misc"])
    unk = ~outside
    idx = -np.ones(n, np.int64); idx[unk] = np.arange(unk.sum())
    N = int(unk.sum())
    rows, cols, vals = [], [], []
    diag = np.zeros(N); rhs = src[unk].copy()
    A1 = DX * DX
    for ax in range(3):
        a = [slice(None)] * 3; b = [slice(None)] * 3
        a[ax] = slice(0, -1); b[ax] = slice(1, None)
        ka, kb = k[tuple(a)], k[tuple(b)]
        ua, ub = unk[tuple(a)], unk[tuple(b)]
        ia, ib = idx[tuple(a)], idx[tuple(b)]
        # unknown-unknown
        m = ua & ub
        g = A1 / (DX / (2 * ka[m]) + DX / (2 * kb[m]))
        rows += [ia[m], ib[m]]; cols += [ib[m], ia[m]]; vals += [-g, -g]
        np.add.at(diag, ia[m], g); np.add.at(diag, ib[m], g)
        # unknown - outside air (film): bottom-facing faces get the desk value
        for us, ks_, ii, face_down in ((ua & ~ub, ka, ia, False), (~ua & ub, kb, ib, True)):
            if not us.any():
                continue
            h = H_SIDE if not (ax == 2 and face_down) else H_BOTTOM
            g = 1.0 / (DX / (2 * ks_[us]) + 1.0 / (h * A1))
            np.add.at(diag, ii[us], g); np.add.at(rhs, ii[us], g * t_amb)
    # ventilation (vents: chimney flow from the inside air temperature; fan: fixed), iterated
    air_ids = idx[inside_air]
    vdot, T = 0.0, None
    for it in range(6):
        d = diag.copy(); r = rhs.copy()
        if (vents > 0 or fan > 0) and len(air_ids):
            g_each = RHO_CP_AIR * vdot / len(air_ids)
            d[air_ids] += g_each; r[air_ids] += g_each * t_amb
        Amat = sparse.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(N, N)) + sparse.diags(d)
        Minv = sparse.diags(1.0 / d)
        T, info = cg(Amat, r, x0=T if T is not None else np.full(N, t_amb + 10), rtol=1e-9, maxiter=60000, M=Minv)
        if not (vents > 0 or fan > 0):
            break
        t_air = T[air_ids].mean()
        a_eff = vents * 1e-6 / np.sqrt(2.0)               # inlet + outlet in series (equal areas)
        v_chimney = 0.6 * a_eff * np.sqrt(max(0.0, 2 * 9.81 * 0.015 * (t_air - t_amb) / (t_amb + 273.15))) if vents else 0.0
        vdot = fan + v_chimney
    full = np.full(n, t_amb); full[unk] = T
    res = dict(soc=float(full[boxmask(lo, n, SOC_BOX) & occ["radxa"]].max()),
               cell=float(full[occ["18650"]].max()),
               air=float(full[inside_air].mean()),
               surface=float(full[solid & ndimage.binary_dilation(outside)].max()),
               sdr=float(full[occ["sdr_dongle"]].max()) if "sdr_dongle" in occ else float("nan"),
               hot_at=[round(float(v), 0) for v in (lo + 0.5 + np.array(np.unravel_index(np.argmax(np.where(solid & ndimage.binary_dilation(outside), full, -1)), n)))],
               watts=float(src.sum()), vdot=vdot * 1000)
    return res, full


def picture(full, name, title):
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    lo, n, occ = geometry()
    kz = int(round(17.5 - lo[2]))                          # slice through the Radxa / SoC
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(full[:, :, kz].T, origin="lower", extent=[lo[0], lo[0] + n[0], lo[1], lo[1] + n[1]],
                   cmap="inferno", vmin=T_AMB, vmax=max(60, full.max()))
    ax.set_title(title); ax.set_xlabel("x (mm)"); ax.set_ylabel("y (mm)")
    plt.colorbar(im, label="°C"); os.makedirs("previews", exist_ok=True)
    fig.savefig(f"previews/thermal_{name}.png", dpi=110, bbox_inches="tight"); plt.close(fig)


if __name__ == "__main__":
    OPTIONS = [("current (PLA, sealed)", dict()),
               ("PETG case", dict(case_mat="petg")),
               ("vents 60 mm² in + out", dict(vents=60)),
               ("vents 150 mm² in + out", dict(vents=150)),
               ("Al pillar SoC → floor", dict(pillar=True)),
               ("Al pillar + Al floor plate", dict(pillar=True, plate=True)),
               ("micro blower 0.1 L/s + vents 60", dict(fan=0.1e-3, vents=60)),
               ("micro blower 0.2 L/s + vents 150", dict(fan=0.2e-3, vents=150)),
               ("pillar + plate + blower 0.1 L/s + vents 60", dict(pillar=True, plate=True, fan=0.1e-3, vents=60)),
               ("SDR switched off", dict(sdr_scale=0.0)),
               ("CPU capped (SoC 1.2 W)", dict(soc_scale=1.2 / 2.2))]
    SHORT = [OPTIONS[0], OPTIONS[5], OPTIONS[8]]
    rows = []
    for scen in ("typical", "typical+charging", "heavy", "heavy+charging"):
        for label, kw in (OPTIONS if scen == "heavy" else SHORT):
            r, full = solve(scen, **kw)
            rows.append((scen, label, r))
            print(f"{scen:16s} {label:42s} SoC {r['soc']:5.1f}  cell {r['cell']:5.1f}  SDR {r['sdr']:5.1f}  air {r['air']:5.1f}  surface {r['surface']:5.1f} at {r['hot_at']}  ({r['watts']:.1f} W, {r['vdot']:.3f} L/s)")
            if scen == "heavy" and label.startswith(("current", "pillar + plate + blower")):
                picture(full, "current" if label.startswith("current") else "best", f"{scen}: {label}  (slice z = 17.5 mm)")
    L = ["# Thermal simulation", "",
         f"Steady state, room {T_AMB} °C, lid open, deck on a desk. 3D conduction on a 1 mm grid of the real parts; outside "
         f"surfaces lose heat at h = {H_SIDE} W/m²K (sides/top) and {H_BOTTOM} W/m²K (bottom on a desk). Vents: chimney "
         "flow from the inside air temperature; fan: fixed flow. **Estimates for comparing options.**", "",
         "| Load | Option | SoC °C | Cell °C | SDR °C | Inside air °C | Hottest case surface °C | Heat (W) |", "|---|---|---|---|---|---|---|---|"]
    for scen, label, r in rows:
        L.append(f"| {scen} | {label} | {r['soc']:.0f} | {r['cell']:.0f} | {r['sdr']:.0f} | {r['air']:.0f} | {r['surface']:.0f} | {r['watts']:.1f} |")
    open("thermal_report.md", "w").write("\n".join(L) + "\n")
